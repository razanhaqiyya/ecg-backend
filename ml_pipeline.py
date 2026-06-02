import os
import time
import numpy as np
import cv2
from scipy import signal
import joblib
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# Tentukan lokasi penyimpanan model di server Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_EXTRACTOR_PATH = os.path.join(BASE_DIR, 'models', 'vgg16_bilstm_extractor.h5')
MODEL_CLASSIFIER_PATH = os.path.join(BASE_DIR, 'models', 'lightgbm_classifier.pkl')

# Mapping output kelas keputusan
LABEL_MAPPING = {0: 'Unauthorized', 1: 'Razan', 2: 'Danar', 3: 'Zidane', 4: 'Yoga'}

# Load model secara global saat server pertama kali menyala
MODEL_READY = False
feature_extractor = None
lgbm_clf = None

if os.path.exists(MODEL_EXTRACTOR_PATH) and os.path.exists(MODEL_CLASSIFIER_PATH):
    try:
        feature_extractor = load_model(MODEL_EXTRACTOR_PATH)
        lgbm_clf = joblib.load(MODEL_CLASSIFIER_PATH)
        MODEL_READY = True
        print("[ML PIPELINE] Semua model PPG berhasil dimuat.")
    except Exception as e:
        print(f"[ML PIPELINE] Gagal memuat file model: {e}")
else:
    print("[ML PIPELINE] Peringatan: File model tidak ditemukan di folder models/.")


def normalize_signal(sig_raw):
    """Menyamakan skala amplitudo IR ratusan ribu menjadi rentang 0-1"""
    sig_array = np.array(sig_raw).reshape(-1, 1)
    scaler = MinMaxScaler()
    return scaler.fit_transform(sig_array).flatten()


def signal_to_spectrogram(sig_norm, fs):
    """Mengubah array 1D PPG menjadi gambar spektrogram RGB 224x224"""
    # Menggunakan parameter nperseg sesuai rancangan training PPG
    f, t, Zxx = signal.stft(sig_norm, fs=fs, nperseg=64, noverlap=32)
    magnitude = np.abs(Zxx)
    
    # Konversi ke skala Logaritma (Desibel)
    db_mag = 20 * np.log10(magnitude + 1e-10)
    
    # Normalisasi gambar ke skala piksel 0-255
    img = cv2.normalize(db_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    img_resized = cv2.resize(img, (224, 224))
    
    # Konversi ke 3 channel (RGB) agar sesuai dengan struktur input VGG16
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_GRAY2RGB)
    return img_rgb


def proses_autentikasi(sinyal_raw: list, fs_asal: int = 100) -> dict:
    """
    Memproses sinyal mentah dari ESP32 untuk menentukan hak akses pintu.
    """
    t_start = time.time()

    # Validasi kesiapan model di server
    if not MODEL_READY:
        return {
            'keputusan': 'TOLAK',
            'nama': 'Unknown',
            'confidence': 0.0,
            'keterangan': 'Model ML belum siap di server'
        }

    # Validasi panjang data input (Harus 540 sesuai chunk size sistem)
    if not sinyal_raw or len(sinyal_raw) != 540:
        return {
            'keputusan': 'TOLAK',
            'nama': 'Unknown',
            'confidence': 0.0,
            'keterangan': f'Panjang data tidak valid ({len(sinyal_raw)}/540 sampel)'
        }

    try:
        # Step 1: Preprocessing & Ekstraksi Matriks Spektrogram
        norm_sig = normalize_signal(sinyal_raw)
        spec_img = signal_to_spectrogram(norm_sig, fs_asal)
        
        # Step 2: Reshape ke dimensi tensor batch (1, 224, 224, 3) & Normalisasi Piksel
        input_tensor = np.expand_dims(spec_img, axis=0).astype(np.float32) / 255.0
        
        # Step 3: Ekstraksi fitur spasio-temporal lewat VGG16-BiLSTM
        extracted_features = feature_extractor.predict(input_tensor, verbose=0)
        
        # Step 4: Prediksi kelas dan kalkulasi nilai probabilitas (confidence) via LightGBM
        pred_class = lgbm_clf.predict(extracted_features)[0]
        pred_proba = lgbm_clf.predict_proba(extracted_features)[0]
        
        confidence_score = float(pred_proba[pred_class])
        nama_terprediksi = LABEL_MAPPING.get(pred_class, 'Unknown')
        
        # Step 5: Pengambilan keputusan akhir untuk Solenoid Door Lock
        # Akses hanya dibuka jika teridentifikasi sebagai tim dan memenuhi batas ambang keamanan
        if nama_terprediksi == 'Unauthorized' or confidence_score < 0.85:
            keputusan = 'TOLAK'
            if nama_terprediksi == 'Unauthorized':
                keterangan = 'Pengguna tidak dikenal (Unauthorized Dataset)'
            else:
                keterangan = f'Akurasi pengenalan di bawah ambang batas keamanan ({confidence_score:.1%})'
        else:
            keputusan = 'BUKA'
            keterangan = f'Terverifikasi sebagai {nama_terprediksi} dengan kecocokan pola {confidence_score:.1%}'

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
            'keterangan': f'Error internal pemrosesan pipeline: {str(e)}'
        }