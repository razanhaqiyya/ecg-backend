# database.py — Simpan log setiap percobaan akses
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base   = declarative_base()
engine = create_engine('sqlite:///ecg_logs.db', connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)

class LogAkses(Base):
    __tablename__ = 'log_akses'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    waktu        = Column(DateTime, default=datetime.now)
    nama         = Column(String, default='Unknown')
    keputusan    = Column(String)   # BUKA atau TOLAK
    confidence   = Column(Float)
    latency_ms   = Column(Float)
    ip_esp32     = Column(String)

Base.metadata.create_all(engine)

def simpan_log(nama, keputusan, confidence, latency_ms, ip_esp32=''):
    sess = Session()
    log  = LogAkses(
        nama=nama, keputusan=keputusan,
        confidence=confidence, latency_ms=latency_ms,
        ip_esp32=ip_esp32
    )
    sess.add(log)
    sess.commit()
    sess.close()

def ambil_log(limit=50):
    sess = Session()
    logs = sess.query(LogAkses).order_by(
        LogAkses.waktu.desc()
    ).limit(limit).all()
    sess.close()
    return logs