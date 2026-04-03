# main.py — FastAPI server utama
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
import time, os
from datetime import datetime

from ml_pipeline import proses_autentikasi
from database import simpan_log, ambil_log

app       = FastAPI(title='ECG Smart Door Lock API')
templates = Jinja2Templates(directory='templates')

# ── Model request dari ESP32 ──────────────────────────────────
class ECGRequest(BaseModel):
    sinyal   : List[float]   # array nilai ADC
    fs       : int = 360     # sampling rate Arduino (default 360 Hz)
    device_id: str = 'ESP32_01'

# ── Endpoint utama: autentikasi ECG ───────────────────────────
@app.post('/auth')
async def autentikasi(req: Request, data: ECGRequest):
    t_start = time.time()

    hasil = proses_autentikasi(data.sinyal, fs_asal=data.fs)

    latency = round((time.time() - t_start) * 1000, 2)

    # Simpan ke database
    simpan_log(
        nama       = hasil['nama'],
        keputusan  = hasil['keputusan'],
        confidence = hasil['confidence'],
        latency_ms = latency,
        ip_esp32   = req.client.host
    )

    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"{hasil['keputusan']} | {hasil['nama']} | "
          f"conf={hasil['confidence']:.3f} | {latency}ms")

    return {
        'keputusan' : hasil['keputusan'],
        'nama'      : hasil['nama'],
        'confidence': hasil['confidence'],
        'latency_ms': latency
    }

# ── Endpoint health check (ESP32 bisa ping dulu) ─────────────
@app.get('/ping')
async def ping():
    return {'status': 'online', 'waktu': datetime.now().isoformat()}

# ── Dashboard web monitoring ──────────────────────────────────
@app.get('/', response_class=HTMLResponse)
async def dashboard(request: Request):
    logs = ambil_log(limit=50)
    log_data = [{
        'waktu'     : l.waktu.strftime('%d/%m %H:%M:%S'),
        'nama'      : l.nama,
        'keputusan' : l.keputusan,
        'confidence': f"{l.confidence:.1%}",
        'latency'   : f"{l.latency_ms:.0f}ms"
    } for l in logs]

    total   = len(log_data)
    diterima = sum(1 for l in log_data if l['keputusan']=='BUKA')
    ditolak  = total - diterima

    return templates.TemplateResponse('dashboard.html', {
        'request'  : request,
        'logs'     : log_data,
        'total'    : total,
        'diterima' : diterima,
        'ditolak'  : ditolak,
    })

    if __name__ == '__main__':
        import uvicorn
        import os
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run("main:app", host="0.0.0.0", port=port)