# 🫀 ECG Smart Door Lock Backend

Sistem autentikasi biometrik berbasis sinyal ECG (Electrocardiogram) yang terintegrasi dengan perangkat keras Arduino nano dan ESP32 serta dashboard pemantauan real-time. Proyek ini dikembangkan sebagai bagian dari Research Group Autentikasi labotarium Security Labotary (SECULAB) di Telkom University.

---

## 🚀 Tech Stack
* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)
* **Database:** [PostgreSQL](https://www.postgresql.org/) via Supabase
* **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
* **Deployment:** [Render.com](https://render.com/)

---

## 📂 Struktur Folder
* `main.py`: Entry point aplikasi dan pendefinisian API endpoints.
* `database.py`: Konfigurasi koneksi database dan skema tabel log akses.
* `ml_placeholder.py`: Modul simulasi pemrosesan sinyal sebelum model ML final siap.
* `templates/`: File HTML untuk tampilan dashboard monitoring.
* `render.yaml`: Konfigurasi Blueprint untuk deployment otomatis ke Render.

---

## 🛠️ Instalasi Lokal
1. **Clone Repositori:**
   ```bash
   git clone [https://github.com/razanhaqiyya/ecg-backend.git](https://github.com/razanhaqiyya/ecg-backend.git)
   cd ecg-backend
