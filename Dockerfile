# 1. Gunakan OS Linux dengan Python 3.11 yang ringan & stabil
FROM python:3.11-slim

# 2. Paksa install komponen OS (libgomp1 untuk LightGBM)
RUN apt-get update && \
    apt-get install -y libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# 3. Tentukan folder kerja di dalam server
WORKDIR /app

# 4. Salin daftar library dan install mesin AI-nya
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Salin seluruh sisa file kode
COPY . .

# 6. Jalankan Uvicorn menggunakan skrip Python internal agar kebal dari error karakter Railway
CMD ["python", "main.py"]