from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from datetime import datetime
import time, os
from dotenv import load_dotenv

from database import simpan_log, ambil_log, ambil_statistik, hapus_semua_log
from ml_placeholder import proses_autentikasi

load_dotenv()

app = FastAPI(
    title       = 'ECG Smart Door Lock API',
    description = 'Backend sistem autentikasi biometrik ECG',
    version     = '1.0.0'
)

templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), 'templates')
)


#Skema request dari ESP32
class ECGRequest(BaseModel):
    sinyal    : List[float]       # array nilai ADC dari Arduino
    fs        : int   = 360       # sampling rate Arduino (Hz)
    device_id : str   = 'ESP32'   # identitas perangkat

#ENDPOINT 1: Autentikasi ECG
@app.post('/auth')
async def autentikasi(request: Request, data: ECGRequest):
    """
    Endpoint utama yang dipanggil ESP32 dengan data sinyal ECG.
    Return: keputusan BUKA atau TOLAK + nama + confidence
    """
    t_start  = time.time()
    ip_device = request.client.host

    #Proses autentikasi
    hasil    = proses_autentikasi(data.sinyal, fs_asal=data.fs)

    latency  = round((time.time() - t_start) * 1000, 2)

    #Simpan ke database
    simpan_log(
        nama        = hasil['nama'],
        keputusan   = hasil['keputusan'],
        confidence  = hasil['confidence'],
        latency_ms  = latency,
        ip_device   = ip_device,
        keterangan  = hasil.get('keterangan', '')
    )

    # Print ke terminal server (untuk monitoring)
    status_icon = '✅' if hasil['keputusan'] == 'BUKA' else '❌'
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"{status_icon} {hasil['keputusan']:5} | "
          f"{hasil['nama']:20} | "
          f"conf={hasil['confidence']:.1%} | "
          f"{latency:.0f}ms | "
          f"from {ip_device}")

    return {
        'keputusan'  : hasil['keputusan'],
        'nama'       : hasil['nama'],
        'confidence' : hasil['confidence'],
        'latency_ms' : latency,
        'timestamp'  : datetime.now().isoformat()
    }

#  ENDPOINT 2: Health check — ESP32 ping dulu sebelum kirim data
@app.get('/ping')
async def ping():
    return {
        'status'     : 'online',
        'waktu'      : datetime.now().isoformat(),
        'model_ready': False   # ganti True setelah model diupload
    }

#  ENDPOINT 3: Dashboard web monitoring
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
        'tar'      : f"{stats['diterima']/stats['total']*100:.1f}%"
                     if stats['total'] > 0 else '—',
    })

#  ENDPOINT 4: API data log (opsional — untuk integrasi lain)
@app.get('/api/logs')
async def api_logs(limit: int = 20):
    logs = ambil_log(limit=limit)
    return [{
        'id'        : l.id,
        'waktu'     : l.waktu.isoformat(),
        'nama'      : l.nama,
        'keputusan' : l.keputusan,
        'confidence': l.confidence,
        'latency_ms': l.latency_ms,
    } for l in logs]


@app.get('/api/stats')
async def api_stats():
    return ambil_statistik()

#  ENDPOINT 5: Hapus semua log
@app.delete('/api/logs/clear')
async def hapus_log():
    hapus_semua_log()
    return {"status": "sukses", "pesan": "Semua data log berhasil dihapus"}