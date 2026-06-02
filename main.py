from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates # <-- TYPO SUDAH DIPERBAIKI DI SINI
from pydantic import BaseModel
from typing import List
import datetime

# Impor dari file lokal Anda
from database import ambil_semua_log, simpan_log_akses, hapus_semua_log
from ml_pipeline import proses_autentikasi 

app = FastAPI(title="PPG Biometric Authentication System")
templates = Jinja2Templates(directory="templates")

# Skema data yang dikirim oleh ESP32
class DataPPG(BaseModel):
    sinyal: List[int]
    fs: int

def waktu_sekarang_wib():
    """Mengembalikan waktu saat ini dalam format WIB (UTC+7)"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))

@app.get("/", response_class=HTMLResponse)
async def halaman_dashboard(request: Request):
    """Menampilkan halaman utama monitoring log akses"""
    try:
        logs = ambil_semua_log()
        
        # Menghitung statistik untuk dikirim ke Chart.js di frontend
        total_akses = len(logs)
        # Menyesuaikan akses dictionary/object berdasarkan format return database.py Anda
        # Kita gunakan dict.get() jika logs adalah list of dicts, atau attribute jika list of objects
        diterima = sum(1 for log in logs if (log['keputusan'] if isinstance(log, dict) else log.keputusan) == 'BUKA')
        ditolak = total_akses - diterima
        
        if total_akses > 0:
            tar_persen = f"{(diterima / total_akses) * 100:.1f}%"
        else:
            tar_persen = "0%"

        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "logs": logs,
            "total": total_akses,
            "diterima": diterima,
            "ditolak": ditolak,
            "tar": tar_persen
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat dashboard: {str(e)}")

@app.post("/auth")
async def otentikasi_perangkat(data: DataPPG, request: Request):
    """Menerima 540 data sinyal dari ESP32 untuk diproses oleh AI"""
    waktu_mulai = datetime.datetime.now()
    ip_client = request.client.host
    
    if len(data.sinyal) != 540:
        raise HTTPException(status_code=400, detail="Jumlah data sinyal harus tepat 540")
        
    try:
        # Jalankan pipeline pemrosesan lengkap dari ml_pipeline.py
        hasil = proses_autentikasi(data.sinyal)
        
        # Hitung latensi
        waktu_selesai = datetime.datetime.now()
        latency = (waktu_selesai - waktu_mulai).total_seconds() * 1000
        
        # Ambil data dari dictionary hasil ml_pipeline
        keputusan = hasil['keputusan']
        nama_prediksi = hasil['nama']
        keterangan = hasil['keterangan']
        nilai_confidence = hasil['confidence']
            
        # Simpan hasil pemrosesan ke database
        data_log = {
            "waktu": waktu_sekarang_wib(),
            "nama": nama_prediksi,
            "keputusan": keputusan,
            "confidence": float(nilai_confidence),
            "latency_ms": float(latency),
            "ip_device": ip_client,
            "keterangan": keterangan
        }
        simpan_log_akses(data_log)
        
        return {"status": keputusan, "user": nama_prediksi}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error pemrosesan server: {str(e)}")

@app.delete("/reset-log")
async def reset_log():
    """Endpoint untuk mengosongkan seluruh isi tabel log_akses"""
    try:
        hapus_semua_log()
        return {"status": "sukses", "pesan": "Seluruh riwayat akses berhasil dikosongkan!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mereset data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)