# ==============================================================================
# FILE: database.py
# Deskripsi: Mengatur koneksi database PostgreSQL (Supabase) / SQLite (Lokal)
#            serta menyediakan fungsi CRUD untuk log akses biometrik PPG.
# ==============================================================================

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Fungsi helper untuk mendapatkan waktu standar WIB (UTC + 7)
# Ini memastikan waktu tetap akurat meskipun server Render berada di Amerika/Eropa
def waktu_sekarang_wib():
    return datetime.utcnow() + timedelta(hours=7)

# Mengambil URL database dari Environment Variable (Render/Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Penyesuaian skema agar dikenali oleh SQLAlchemy versi terbaru
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    # Jika dijalankan secara lokal tanpa .env, otomatis membuat file SQLite lokal baru
    DATABASE_URL = 'sqlite:///ppg_logs.db'

# Inisialisasi Engine dan Session SQLAlchemy
Base = declarative_base()
engine = create_engine(
    DATABASE_URL, 
    # Parameter tambahan khusus SQLite untuk mencegah error multi-thread
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
Session = sessionmaker(bind=engine)

class LogAkses(Base):
    """
    Model Tabel Database untuk menyimpan riwayat autentikasi sistem door lock
    """
    __tablename__ = 'log_akses'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    waktu       = Column(DateTime, default=waktu_sekarang_wib)
    nama        = Column(String, default='Unknown')
    keputusan   = Column(String)           # Berisi nilai: 'BUKA' atau 'TOLAK'
    confidence  = Column(Float, default=0.0)   # Nilai probabilitas dari LightGBM
    latency_ms  = Column(Float, default=0.0)   # Kecepatan pemrosesan dalam milidetik
    ip_device   = Column(String, default='')   # IP Address dari ESP32 pengirim
    keterangan  = Column(String, default='')   # Alasan detail keputusan model

# Membuat tabel secara otomatis di Supabase/SQLite jika tabel belum terbuat
Base.metadata.create_all(engine)


def simpan_log(nama: str, keputusan: str, confidence: float = 0.0,
               latency_ms: float = 0.0, ip_device: str = '', keterangan: str = ''):
    """
    Menyimpan rekam jejak percobaan autentikasi baru ke database.
    """
    sess = Session()
    try:
        log = LogAkses(
            nama        = nama,
            keputusan   = keputusan,
            confidence  = confidence,
            latency_ms  = latency_ms,
            ip_device   = ip_device,
            keterangan  = keterangan
        )
        sess.add(log)
        sess.commit()
    except Exception as e:
        sess.rollback()
        print(f"[DATABASE ERROR] Gagal menyimpan log: {e}")
    finally:
        sess.close()


def sample_log_palsu():
    """
    Fungsi opsional untuk membersihkan atau mereset jika diperlukan
    """
    pass


def ambil_log(limit: int = 50):
    """
    Mengambil data riwayat akses terbaru untuk ditampilkan di tabel dashboard.
    """
    sess = Session()
    try:
        logs = sess.query(LogAkses)\
                   .order_by(LogAkses.waktu.desc())\
                   .limit(limit).all()
        return logs
    except Exception as e:
        print(f"[DATABASE ERROR] Gagal mengambil data log: {e}")
        return []
    finally:
        sess.close()


def ambil_statistik():
    """
    Menghitung kalkulasi data untuk widget ringkasan statistik pada dashboard.
    """
    sess = Session()
    try:
        total    = sess.query(LogAkses).count()
        diterima = sess.query(LogAkses).filter(LogAkses.keputusan == 'BUKA').count()
        ditolak  = total - diterima
        
        return {
            'total': total, 
            'diterima': diterima, 
            'ditolak': ditolak
        }
    except Exception as e:
        print(f"[DATABASE ERROR] Gagal menghitung statistik: {e}")
        return {'total': 0, 'diterima': 0, 'ditolak': 0}
    finally:
        sess.close()


def hapus_semua_log():
    """
    Menghapus seluruh isi data log (Fungsi pemeliharaan/maintenance database).
    """
    sess = Session()
    try:
        sess.query(LogAkses).delete()
        sess.commit()
        print("[DATABASE INFO] Semua log berhasil dibersihkan.")
    except Exception as e:
        sess.rollback()
        print(f"[DATABASE ERROR] Gagal menghapus log: {e}")
    finally:
        sess.close()