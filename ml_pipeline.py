# ml_pipeline.py — Semua proses ML ada di sini
import numpy as np
import cv2, pywt, json, joblib
import tensorflow as tf
import lightgbm as lgb
from scipy.signal import stft, find_peaks, welch, resample_poly

# ── Konstanta ─────────────────────────────────────────────────
SAMPLING_RATE = 500
CHUNK_SIZE    = 750
IMG_SIZE      = (128, 128)
NPERSEG       = 128

# ── Load semua model (dipanggil sekali saat server start) ─────
print("🔄 Loading ML models...")

feature_extractor = tf.saved_model.load('models/ecg_feature_extractor')
lgbm_model        = lgb.Booster(model_file='models/model_lightgbm.txt')

threshold_data = json.load(open('models/threshold.json'))
THRESHOLD      = np.array(threshold_data['threshold'])
NUM_CLASSES    = threshold_data['num_classes']

scaler_data    = json.load(open('models/scaler_hrv.json'))
SCALER_MEAN    = np.array(scaler_data['mean'])
SCALER_SCALE   = np.array(scaler_data['scale'])

LABEL_MAP      = json.load(open('models/label_map.json'))

print(f"✅ Models loaded — {NUM_CLASSES} kelas")


# ── Fungsi preprocessing (sama persis dengan training) ────────
def normalisasi_sinyal(sinyal):
    x_min, x_max = np.min(sinyal), np.max(sinyal)
    if x_max - x_min == 0:
        return sinyal
    return (sinyal - x_min) / (x_max - x_min)

def hapus_noise_dwt(sinyal, wavelet='db1', level=4):
    coeffs    = pywt.wavedec(sinyal, wavelet, level=level)
    coeffs[0] = np.zeros_like(coeffs[0])
    bersih    = pywt.waverec(coeffs, wavelet)
    return bersih[:len(sinyal)]

def sinyal_ke_spektrogram(sinyal):
    f, t, Zxx = stft(sinyal, fs=SAMPLING_RATE, nperseg=NPERSEG)
    mag = np.abs(Zxx)
    if mag.max() > 0:
        mag = (mag / mag.max() * 255).astype(np.uint8)
    img     = cv2.resize(mag, IMG_SIZE)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    return img_rgb.astype(np.float32) / 255.0

def ekstrak_fitur_hrv(sinyal, fs=500):
    try:
        sn = (sinyal - np.mean(sinyal)) / (np.std(sinyal) + 1e-8)
        peaks, _ = find_peaks(sn,
                              height=np.percentile(sn, 60),
                              distance=int(0.3*fs),
                              prominence=0.3)
        if len(peaks) < 3:
            return np.zeros(7, dtype=np.float32)
        rr      = np.diff(peaks) / fs
        rr      = rr[(rr > 0.3) & (rr < 2.0)]
        if len(rr) < 2:
            return np.zeros(7, dtype=np.float32)
        sdnn    = np.std(rr) * 1000.0
        rr_d    = np.diff(rr)
        rmssd   = np.sqrt(np.mean(rr_d**2)) * 1000.0
        pnn50   = np.sum(np.abs(rr_d) > 0.050) / max(len(rr_d), 1)
        mean_hr = 60.0 / np.mean(rr)
        lf_p = hf_p = lf_hf = 0.0
        if len(rr) >= 8:
            t_rr  = np.cumsum(rr) - np.cumsum(rr)[0]
            t_uni = np.arange(0, t_rr[-1], 0.25)
            if len(t_uni) >= 8:
                rr_re    = np.interp(t_uni, t_rr, rr)
                npw      = min(len(rr_re), 64)
                frq, psd = welch(rr_re, fs=4.0, nperseg=npw)
                lf_m     = (frq >= 0.04) & (frq < 0.15)
                hf_m     = (frq >= 0.15) & (frq <= 0.40)
                lf_p  = float(np.trapz(psd[lf_m], frq[lf_m])) if np.any(lf_m) else 0.0
                hf_p  = float(np.trapz(psd[hf_m], frq[hf_m])) if np.any(hf_m) else 0.0
                lf_hf = lf_p / (hf_p + 1e-10)
        return np.array([sdnn, rmssd, pnn50, mean_hr, lf_p, hf_p, lf_hf],
                        dtype=np.float32)
    except:
        return np.zeros(7, dtype=np.float32)


# ── Fungsi utama autentikasi ───────────────────────────────────
def proses_autentikasi(sinyal_raw: list, fs_asal: int = 360) -> dict:
    """
    Input : list float dari ESP32 (sampel ADC mentah)
    Output: dict {keputusan, nama, confidence, label_idx}
    """
    sinyal = np.array(sinyal_raw, dtype=np.float32)

    # Resample jika sampling rate Arduino berbeda dari 500 Hz
    if fs_asal != SAMPLING_RATE:
        sinyal = resample_poly(sinyal, up=SAMPLING_RATE, down=fs_asal)

    # Pastikan panjang tepat 750
    if len(sinyal) >= CHUNK_SIZE:
        sinyal = sinyal[:CHUNK_SIZE]
    else:
        sinyal = np.pad(sinyal, (0, CHUNK_SIZE - len(sinyal)))

    # Preprocessing
    norm   = normalisasi_sinyal(sinyal.astype(np.float32))
    bersih = hapus_noise_dwt(norm)

    # Cek kualitas sinyal
    if np.std(bersih) < 0.02:
        return {
            'keputusan': 'TOLAK',
            'nama': 'Unknown',
            'confidence': 0.0,
            'alasan': 'Sinyal terlalu lemah — cek elektroda'
        }

    # Ekstrak fitur VGG16 + BiLSTM (256 dim)
    spek      = sinyal_ke_spektrogram(bersih)
    spek_4d   = spek[np.newaxis, ...]  # (1, 128, 128, 3)
    spek_tf   = tf.constant(spek_4d)
    bilstm_f  = feature_extractor(spek_tf).numpy()  # (1, 256)

    # Ekstrak + normalisasi fitur HRV (7 dim)
    hrv_raw   = ekstrak_fitur_hrv(bersih)
    hrv_scaled = (hrv_raw - SCALER_MEAN) / (SCALER_SCALE + 1e-8)

    # Gabungkan 256 + 7 = 263 dim
    combined  = np.hstack([bilstm_f, hrv_scaled.reshape(1, -1)])

    # LightGBM predict
    proba     = lgbm_model.predict(combined)[0]

    # Apply threshold per kelas
    kandidat  = [k for k in range(NUM_CLASSES)
                 if proba[k] >= THRESHOLD[k]]

    if len(kandidat) == 0:
        label_idx = int(np.argmax(proba))
    elif len(kandidat) == 1:
        label_idx = kandidat[0]
    else:
        label_idx = max(kandidat, key=lambda k: proba[k])

    confidence  = float(proba[label_idx])
    nama        = LABEL_MAP.get(str(label_idx), f'Person_{label_idx+1:02d}')
    keputusan   = 'BUKA' if len(kandidat) > 0 else 'TOLAK'

    return {
        'keputusan' : keputusan,
        'nama'      : nama,
        'confidence': round(confidence, 4),
        'label_idx' : label_idx,
        'alasan'    : 'OK'
    }