import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Mengambil URL dari .env (lokal) atau Environment Variable (Render)
# Jika tidak ditemukan, default ke SQLite agar lokal tetap bisa jalan
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Fix untuk SQLAlchemy agar mengenali skema postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    # Fallback ke SQLite jika sedang ngoding di laptop tanpa internet
    DATABASE_URL = 'sqlite:///ecg_logs.db'

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class LogAkses(Base):
    """
    Tabel untuk menyimpan setiap percobaan autentikasi
    """
    __tablename__ = 'log_akses'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    waktu       = Column(DateTime, default=datetime.now)
    nama        = Column(String,  default='Unknown')
    keputusan   = Column(String)           # BUKA atau TOLAK
    confidence  = Column(Float,  default=0.0)
    latency_ms  = Column(Float,  default=0.0)
    ip_device   = Column(String, default='')
    keterangan  = Column(String, default='')


# Buat tabel otomatis jika belum ada
Base.metadata.create_all(engine)


def simpan_log(nama, keputusan, confidence=0.0,
               latency_ms=0.0, ip_device='', keterangan=''):
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
    finally:
        sess.close()


def ambil_log(limit=50):
    sess = Session()
    try:
        logs = sess.query(LogAkses)\
                   .order_by(LogAkses.waktu.desc())\
                   .limit(limit).all()
        return logs
    finally:
        sess.close()


def ambil_statistik():
    sess = Session()
    try:
        total    = sess.query(LogAkses).count()
        diterima = sess.query(LogAkses)\
                      .filter(LogAkses.keputusan == 'BUKA').count()
        return {'total': total, 'diterima': diterima,
                'ditolak': total - diterima}
    finally:
        sess.close()
    
def hapus_semua_log():
    sess = Session()
    try:
        # Menghapus seluruh baris di dalam tabel LogAkses
        sess.query(LogAkses).delete()
        sess.commit()
    finally:
        sess.close()