# SIT-System – Scammer Identification & Validation Tool

A full-stack system that detects scam/phishing links via a **Telegram bot**, stores results in **MySQL**, and provides an **admin dashboard** for monitoring.

## Architecture

```
SIT-System/
├── backend/           FastAPI + SQLAlchemy + PyMySQL
│   ├── app/           API routes, models, detector engine
│   ├── bot/           Telegram bot (pyTelegramBotAPI, polling)
│   ├── .env           MySQL + JWT config  (DO NOT COMMIT)
│   └── .venv/         Python virtual environment
├── frontend/admin/    Static HTML/CSS/JS admin dashboard
└── run_all.ps1        One-click launcher (PowerShell)
```

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.11+   |
| XAMPP MySQL | 3306    |
| pip deps    | see `backend/requirements.txt` |

## Quick Start

1. **Start XAMPP MySQL** (port 3306).

2. **Create the database** (first time only):
   ```sql
   CREATE DATABASE IF NOT EXISTS sit_db;
   ```

3. **Install Python dependencies** (first time only):
   ```powershell
   cd SIT-System/backend
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

4. **Create environment files** (first time only):

   `backend/.env`:
   ```
   MYSQL_USER=root
   MYSQL_PASSWORD=
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_DB=sit_db
   JWT_SECRET=changeme-super-secret-key-2026
   JWT_ALGORITHM=HS256
   JWT_EXPIRE_MINUTES=480
   ```

   `backend/bot/.env`:
   ```
   TELEGRAM_BOT_TOKEN=<your-token-here>
   BACKEND_URL=http://127.0.0.1:8001
   ```

5. **Run everything** (one command):
   ```powershell
   powershell -ExecutionPolicy Bypass -File run_all.ps1
   ```
   This starts the backend, frontend server, and Telegram bot, then opens the browser.

## Default Admin Login

- **Email:** `admin@example.com`
- **Password:** `admin123`

## Security Reminders

- **Never commit `.env` files** — they contain database credentials and bot tokens.
- The `.gitignore` already excludes `backend/.env` and `backend/bot/.env`.
- Change the default admin password and JWT secret before deploying to production.
