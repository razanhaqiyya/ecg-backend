from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templatetering import Jinja2Templates
from pydantic import BaseModel
from typing import List
import datetime

# Pastikan file database.py Anda sudah memiliki fungsi-fungsi ini
from database import ambil_semua_log, simpan_log_akses, hapus_semua_log 
# Pastikan file ml_pipeline.py sudah siap untuk memproses model PPG
from ml_pipeline import prediksi_biometrik 

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
        return templates.TemplateResponse("dashboard.html", {"request": request, "logs": logs})
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
        # Jalankan ekstraksi fitur dan prediksi menggunakan model VGG16 + LightGBM
        nama_prediksi, nilai_confidence = prediksi_biometrik(data.sinyal)
        
        # Hitung latensi pemrosesan dalam milidetik
        waktu_selesai = datetime.datetime.now()
        latency = (waktu_selesai - waktu_mulai).total_seconds() * 1000
        
        # Tentukan keputusan berdasarkan ambang batas akurasi (misal 75%)
        if nilai_confidence >= 0.75 and nama_prediksi != "Unknown":
            keputusan = "BUKA"
            keterangan = f"Terverifikasi sebagai {nama_prediksi}"
        else:
            keputusan = "TOLAK"
            nama_prediksi = "Unknown User"
            keterangan = "Akurasi model di bawah ambang batas"
            
        # Simpan hasil pemrosesan ke database Supabase / Lokal
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
    """Endpoint baru untuk mengosongkan seluruh isi tabel log_akses"""
    try:
        hapus_semua_log()
        return {"status": "sukses", "pesan": "Seluruh riwayat akses berhasil dikosongkan!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mereset data: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)