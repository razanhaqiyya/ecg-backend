from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
import time, os
from dotenv import load_dotenv

from database import simpan_log, ambil_log, ambil_statistik
# Mengimpor pipeline pemrosesan PPG yang baru
from ml_pipeline import proses_autentikasi

load_dotenv()

app = FastAPI(
    title       = 'PPG Smart Door Lock API',
    description = 'Backend sistem autentikasi biometrik PPG berbasis MAX30102',
    version     = '2.0.0'
)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), 'templates')
)

# Mengubah nama skema ke PPG dan menyesuaikan sampling rate dasar ke 100Hz
class PPGRequest(BaseModel):
    sinyal    : List[float]       # Array nilai IR Amplitude dari MAX30102
    fs        : int   = 100       # Sampling rate sensor PPG (100 Hz)
    device_id : str   = 'ESP32'   # Identitas perangkat IoT

@app.post('/auth')
async def autentikasi(request: Request, data: PPGRequest):
    """
    Endpoint utama yang dipanggil oleh ESP32 dengan membawa data sinyal PPG jari.
    Return: keputusan BUKA atau TOLAK untuk relay Solenoid.
    """
    t_start  = time.time()
    ip_device = request.client.host

    # 1. Jalankan pemrosesan sinyal pada pipeline ML PPG
    hasil = proses_autentikasi(data.sinyal, fs_asal=data.fs)
    
    # 2. Hitung total waktu tunda pemrosesan (latency)
    latency_ms = (time.time() - t_start) * 1000

    # 3. Simpan rekam jejak akses ke database Supabase secara asinkronus
    simpan_log(
        nama        = hasil['nama'],
        keputusan   = hasil['keputusan'],
        confidence  = hasil['confidence'],
        latency_ms  = latency_ms,
        ip_device   = ip_device,
        keterangan  = hasil['keterangan']
    )

    # 4. Berikan respon balik ke ESP32 untuk aksi pada Solenoid
    return {
        'status'     : hasil['keputusan'],  # 'BUKA' atau 'TOLAK'
        'user'       : hasil['nama'],
        'confidence' : f"{hasil['confidence']:.1%}",
        'latency_ms' : round(latency_ms, 2),
        'keterangan' : hasil['keterangan']
    }

@app.get('/', response_class=HTMLResponse)
async def dashboard(request: Request):
    logs  = ambil_log(limit=50)
    stats = ambil_statistik()

    log_data = [{
        'waktu'      : l.waktu.strftime('%d/%m/%Y %H:%M:%S'),
        'nama'       : l.nama,
        'keputusan'  : l.keputusan,
        'confidence' : f"{l.confidence:.1%}",
        'latency'    : f"{l.latency_ms:.0f} ms",
        'ip'         : l.ip_device,
        'keterangan' : l.keterangan
    } for l in logs]

    return templates.TemplateResponse('dashboard.html', {
        'request'  : request,
        'logs'     : log_data,
        'total'    : stats['total'],
        'diterima' : stats['diterima'],
        'ditolak'  : stats['ditolak'],
        'tar'      : f"{stats['diterima']/stats['total']*100:.1f}%" if stats['total'] > 0 else '—',
    })