# database.py
# Menyimpan setiap percobaan akses ke database SQLite
# SQLite tidak perlu install apapun — sudah built-in Python

from sqlalchemy import (create_engine, Column, Integer,
                        String, Float, DateTime)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base    = declarative_base()
engine  = create_engine(
    'sqlite:///ecg_logs.db',
    connect_args={'check_same_thread': False}
)
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