# 🫀 ECG Smart Door Lock: Biometric Authentication Backend

A robust, cloud-native backend system designed for biometric authentication using Electrocardiogram (ECG) signals. This project serves as the core API for an IoT-based smart door lock system, integrating hardware data acquisition (ESP32), machine learning inference, and real-time monitoring.

Developed as part of cybersecurity research at **Telkom University**.

---

## 🚀 Key Features

* **RESTful API Architecture:** High-performance endpoints built with FastAPI.
* **Real-time Biometric Processing:** Endpoint for receiving and authenticating raw ECG signal arrays.
* **Persistent Logging:** Secure storage of access attempts (Authorized vs. Unauthorized) with detailed metrics.
* **Live Dashboard:** Web-based interface for monitoring system health, access history, and performance statistics.
* **Cloud-Native Integration:** Fully deployed on Render with a permanent PostgreSQL database on Supabase.

---

## 🛠 Tech Stack

* **Language:** Python 3.11.0
* **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Database:** [PostgreSQL](https://www.postgresql.org/) via [Supabase](https://supabase.com/)
* **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
* **Server/Deployment:** [Render](https://render.com/)
* **Frontend Templating:** Jinja2

---

## 📂 Repository Structure

* `main.py`: Primary application entry point and API route definitions.
* `database.py`: Database configuration, connection pooling, and ORM models.
* `ml_placeholder.py`: Simulation module for ECG authentication logic (Placeholder for final ML model).
* `templates/`: HTML templates for the monitoring dashboard.
* `render.yaml`: Infrastructure-as-Code for automated deployment on Render.
* `requirements.txt`: Python dependency manifest.

---

## 📡 API Documentation

### 1. Authentication (`/auth`)
* **Method:** `POST`
* **Description:** Receives ECG signal data from ESP32 for user identification.
* **Payload:** Array of float values (ADC samples) and sampling rate.

### 2. System Health Check (`/ping`)
* **Method:** `GET`
* **Description:** Used by hardware to verify server availability before data transmission.

### 3. Monitoring Dashboard (`/`)
* **Method:** `GET`
* **Description:** Renders a web view displaying access logs and performance stats.

### 4. Data Management (`/api/logs/clear`)
* **Method:** `DELETE`
* **Description:** Securely flushes all records from the PostgreSQL access log table.

---

## 🗄 Database Schema: `log_akses`

The system records the following metrics for every authentication attempt:
* `id`: Primary Key (Auto-increment).
* `waktu`: Timestamp of the attempt.
* `nama`: Identified user or "Unknown".
* `keputusan`: Access decision (`BUKA` or `TOLAK`).
* `confidence`: Probability score of the ML model.
* `latency_ms`: Server-side processing time.
* `ip_device`: Originating IP address for security tracking.

---

## ⚙️ Local Setup

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/razanhaqiyya/ecg_backend.git](https://github.com/razanhaqiyya/ecg_backend.git)
    cd ecg_backend
    ```
2.  **Environment Configuration:**
    Create a `.env` file in the root directory:
    ```env
    DATABASE_URL=your_supabase_postgresql_uri
    APP_NAME=ECG Smart Door Lock
    DEBUG=true
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run Application:**
    ```bash
    uvicorn main:app --reload
    ```

---

## 👤 Author
**Razan**
Computer Engineering | Telkom University
