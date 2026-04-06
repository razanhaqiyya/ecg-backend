# ml_placeholder.py
# PLACEHOLDER — Digunakan sebelum model ML siap
# Nanti file ini DIGANTI dengan ml_pipeline.py yang asli
# Tidak perlu install tensorflow/lightgbm dulu

import random
import time

# Flag: ganti ke True setelah model ML diupload
MODEL_READY = False


def proses_autentikasi(sinyal_raw: list, fs_asal: int = 360) -> dict:
    """
    PLACEHOLDER FUNCTION
    Sekarang: return dummy response untuk testing
    Nanti   : diganti dengan pipeline ML asli

    Input : list float dari ESP32
    Output: dict {keputusan, nama, confidence, latency_ms}
    """

    if not MODEL_READY:
        # Mode testing — simulasi respons acak
        # Ganti logika ini sesuai kebutuhan testing

        # Cek apakah data masuk valid
        if not sinyal_raw or len(sinyal_raw) < 100:
            return {
                'keputusan'  : 'TOLAK',
                'nama'       : 'Unknown',
                'confidence' : 0.0,
                'keterangan' : 'Data sinyal terlalu pendek'
            }

        # Hitung statistik dasar sebagai validasi minimal
        import statistics
        mean_val = statistics.mean(sinyal_raw)
        std_val  = statistics.stdev(sinyal_raw) if len(sinyal_raw) > 1 else 0

        # Simulasi proses (delay kecil)
        time.sleep(0.1)

        # Return dummy — semua diterima sebagai "Test_User"
        # untuk memverifikasi alur sistem end-to-end
        return {
            'keputusan'  : 'BUKA',
            'nama'       : 'Test_User',
            'confidence' : 0.95,
            'keterangan' : f'PLACEHOLDER — {len(sinyal_raw)} sampel diterima '
                           f'(mean={mean_val:.1f}, std={std_val:.1f})'
        }

    else:
        # Nanti: import dan panggil pipeline ML asli
        # from ml_pipeline import proses_autentikasi as _proses
        # return _proses(sinyal_raw, fs_asal)
        pass