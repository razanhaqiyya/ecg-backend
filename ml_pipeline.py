import os
import time
import numpy as np
import cv2
from scipy import signal
import joblib
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_EXTRACTOR_PATH = os.path.join(BASE_DIR, 'models', 'vgg16_bilstm_extractor.h5')
MODEL_CLASSIFIER_PATH = os.path.join(BASE_DIR, 'models', 'lightgbm_classifier.pkl')

LABEL_MAPPING = {0: 'Unauthorized', 1: 'Razan', 2: 'Danar', 3:  'Yoga'}

MODEL_READY = False
feature_extractor = None
lgbm_clf = None

# Variabel baru untuk melacak error secara presisi
ALASAN_ERROR_MODEL = "Belum diinisialisasi"

if os.path.exists(MODEL_EXTRACTOR_PATH) and os.path.exists(MODEL_CLASSIFIER_PATH):
    try:
        feature_extractor = load_model(MODEL_EXTRACTOR_PATH)
        lgbm_clf = joblib.load(MODEL_CLASSIFIER_PATH)
        MODEL_READY = True
        ALASAN_ERROR_MODEL = "Model siap"
        print("[ML PIPELINE] Semua model PPG berhasil dimuat.")
    except Exception as e:
        ALASAN_ERROR_MODEL = f"GAGAL LOAD (Beda Versi TF/Keras): {str(e)}"
        print(f"[ML PIPELINE] Gagal memuat file model: {e}")
else:
    ALASAN_ERROR_MODEL = f"FILE HILANG: Tidak ditemukan di path {MODEL_EXTRACTOR_PATH}"
    print(f"[ML PIPELINE] Peringatan: {ALASAN_ERROR_MODEL}")


def normalize_signal(sig_raw):
    sig_array = np.array(sig_raw).reshape(-1, 1)
    scaler = MinMaxScaler()
    return scaler.fit_transform(sig_array).flatten()

def signal_to_spectrogram(sig_norm, fs):
    f, t, Zxx = signal.stft(sig_norm, fs=fs, nperseg=64, noverlap=32)
    magnitude = np.abs(Zxx)
    db_mag = 20 * np.log10(magnitude + 1e-10)
    img = cv2.normalize(db_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    img_resized = cv2.resize(img, (224, 224))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_GRAY2RGB)
    return img_rgb

def proses_autentikasi(sinyal_raw: list, fs_asal: int = 100) -> dict:
    t_start = time.time()

    # Perubahan di sini: Mengirim pesan error spesifik ke dashboard
    if not MODEL_READY:
        return {
            'keputusan': 'TOLAK',
            'nama': 'Unknown',
            'confidence': 0.0,
            'keterangan': f"AI ERROR: {ALASAN_ERROR_MODEL}"
        }

    if not sinyal_raw or len(sinyal_raw) != 540:
        return {
            'keputusan': 'TOLAK',
            'nama': 'Unknown',
            'confidence': 0.0,
            'keterangan': f'Panjang data tidak valid ({len(sinyal_raw)}/540 sampel)'
        }

    try:
        norm_sig = normalize_signal(sinyal_raw)
        spec_img = signal_to_spectrogram(norm_sig, fs_asal)
        input_tensor = np.expand_dims(spec_img, axis=0).astype(np.float32) / 255.0
        
        extracted_features = feature_extractor.predict(input_tensor, verbose=0)
        pred_class = lgbm_clf.predict(extracted_features)[0]
        pred_proba = lgbm_clf.predict_proba(extracted_features)[0]
        
        confidence_score = float(pred_proba[pred_class])
        nama_terprediksi = LABEL_MAPPING.get(pred_class, 'Unknown')
        
        if nama_terprediksi == 'Unauthorized' or confidence_score < 0.85:
            keputusan = 'TOLAK'
            if nama_terprediksi == 'Unauthorized':
                keterangan = 'Pengguna tidak dikenal'
            else:
                keterangan = f'Akurasi di bawah standar ({confidence_score:.1%})'
        else:
            keputusan = 'BUKA'
            keterangan = f'Terverifikasi {nama_terprediksi} ({confidence_score:.1%})'

        return {
            'keputusan': keputusan,
            'nama': nama_terprediksi,
            'confidence': confidence_score,
            'keterangan': keterangan
        }

    except Exception as e:
        return {
            'keputusan': 'TOLAK',
            'nama': 'Unknown',
            'confidence': 0.0,
            'keterangan': f'Error Proses Fungsi: {str(e)}'
        }