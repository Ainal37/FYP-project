# FYP-project: SIT-System – Scammer Identification & Validation Tool

A full-stack scam/phishing link detection system featuring a **FastAPI backend**, **MySQL database**, **Telegram bot**, and an **HTML/CSS/JS admin dashboard**.

---

## Architecture

```
SIT-System/
  backend/
    app/          → FastAPI application (models, routers, detector, auth)
    bot/          → Telegram bot (polling mode)
    .venv/        → Python virtual environment (not committed)
    .env          → Backend secrets (not committed)
    requirements.txt
  frontend/
    admin/        → Admin dashboard (login, dashboard, scans, reports)
      assets/
        css/      → style.css
        js/       → api.js, login.js, dashboard.js, scans.js, reports.js
  run_all.ps1     → One-click launcher (Windows)
  .gitignore
  README.md
```

## Prerequisites

| Component     | Version / Notes                    |
|---------------|------------------------------------|
| Python        | 3.11+                              |
| MySQL         | 8.x via XAMPP                      |
| XAMPP         | With MySQL module running          |
| pip           | Bundled with Python                |
| PowerShell    | 5.1+ (Windows built-in)           |
| Telegram Bot  | Create via @BotFather              |

## Quick Start

1. **Start XAMPP MySQL** and create the database:

   ```sql
   CREATE DATABASE IF NOT EXISTS sit_db;
   ```

2. **Create virtual environment** (one-time):

   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m pip install -r bot\requirements.txt
   ```

3. **Configure environment files** (one-time):

   `backend/.env`:
   ```
   MYSQL_USER=root
   MYSQL_PASSWORD=
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_DB=sit_db
   JWT_SECRET=supersecretkey
   ```

   `backend/bot/.env`:
   ```
   TELEGRAM_BOT_TOKEN=<your-token-from-botfather>
   BACKEND_URL=http://127.0.0.1:8001
   BOT_ADMIN_EMAIL=admin@example.com
   BOT_ADMIN_PASSWORD=admin123
   ```

4. **Launch everything**:

   ```powershell
   .\run_all.ps1
   ```

   This starts the backend (port 8001), frontend (port 5500), and the Telegram bot. It also opens Swagger docs and the admin login page automatically.

## Default Admin Login

| Field    | Value              |
|----------|--------------------|
| Email    | admin@example.com  |
| Password | admin123           |

The default admin is auto-seeded on first startup if it does not already exist.

## API Endpoints

| Method | Path              | Auth     | Description                |
|--------|-------------------|----------|----------------------------|
| POST   | /auth/login       | Public   | Get JWT access token       |
| GET    | /auth/me          | Bearer   | Current user info          |
| POST   | /scans            | Bearer   | Scan a link                |
| GET    | /scans            | Bearer   | List scans                 |
| POST   | /reports          | Bearer   | Submit a report            |
| GET    | /reports          | Bearer   | List reports               |
| GET    | /dashboard/stats  | Bearer   | Dashboard statistics       |

## Telegram Bot Commands

| Command               | Description                      |
|-----------------------|----------------------------------|
| /start                | Welcome message                  |
| /scan \<link\>        | Scan a URL                       |
| /report \<link\> \<reason\> | Report a scam link         |
| /help                 | Show help                        |
| *(paste any URL)*     | Auto-scan                        |

## Security Reminders

- **NEVER** commit `.env` files – they contain tokens and secrets.
- Both `backend/.env` and `backend/bot/.env` are listed in `.gitignore`.
- Change `JWT_SECRET` to a strong random value for production.
- Change the default admin password after first login in production.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MySQL connection refused | Start XAMPP MySQL, ensure `sit_db` exists |
| Column/schema errors | Drop and recreate: `DROP DATABASE sit_db; CREATE DATABASE sit_db;` then restart |
| Telegram 409 conflict | Close duplicate bot windows, delete `.bot.lock`, restart |
| Port already in use | Kill the process using the port or change port in run_all.ps1 |
