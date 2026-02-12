# FYP-project: SIT-System – Scammer Identification & Validation Tool

Enterprise MVP for detecting, analysing, and reporting scam/phishing URLs using heuristic rules, threat intelligence (VirusTotal + URLhaus), NLP message analysis, and a Telegram bot interface.

---

## Architecture

```
SIT-System/
  backend/
    app/               FastAPI (routers, models, scoring, intel, NLP, security)
    bot/               Telegram bot (polling, authenticated)
    .venv/             Python virtual env (not committed)
    .env               Backend secrets (not committed)
    requirements.txt
  frontend/admin/      Admin dashboard (HTML/CSS/JS)
    assets/css/        style.css (grey/white enterprise theme)
    assets/js/         api.js, dashboard.js, scans.js, reports.js, login.js
  datasets/            Evaluation CSVs (scam_urls.csv, scam_messages.csv)
  evaluation/          Evaluation pipeline (evaluate.py, metrics.json)
  tests/               API tests (pytest)
  run_all.ps1          One-click launcher (Windows)
```

## Prerequisites

| Component | Notes |
|-----------|-------|
| Python 3.11+ | With pip |
| MySQL 8.x | Via XAMPP |
| XAMPP | MySQL module running |
| PowerShell 5.1+ | Windows built-in |
| Telegram Bot | Create via @BotFather |

### Optional API Keys

| Key | Purpose | Required? |
|-----|---------|-----------|
| `VIRUSTOTAL_API_KEY` | URL reputation from VirusTotal | No (graceful fallback) |
| `ALERT_CHAT_ID` | Telegram group for HIGH-threat alerts | No |

## Quick Start

```powershell
# 1. Start XAMPP MySQL
# 2. Create database
mysql -u root -e "CREATE DATABASE IF NOT EXISTS sit_db;"

# 3. Setup (one-time)
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r bot\requirements.txt

# 4. Configure .env files (see below)

# 5. Launch everything
cd ..
.\run_all.ps1
```

### backend/.env

```
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=sit_db
JWT_SECRET=changeme-super-secret-key-2026
VIRUSTOTAL_API_KEY=           # optional
```

### backend/bot/.env

```
TELEGRAM_BOT_TOKEN=<from @BotFather>
BACKEND_URL=http://127.0.0.1:8001
BOT_ADMIN_EMAIL=admin@example.com
BOT_ADMIN_PASSWORD=admin123
ALERT_CHAT_ID=                # optional: Telegram group/channel ID
```

## Default Admin

| Field | Value |
|-------|-------|
| Email | admin@example.com |
| Password | admin123 |

Auto-seeded on first startup.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/login | Public | JWT token |
| GET | /auth/me | Bearer | Current user |
| POST | /scans | Bearer | Scan URL (+ optional message) |
| GET | /scans | Bearer | List scans |
| GET | /scans/{id} | Bearer | Scan detail + breakdown |
| POST | /scans/analyze-message | Bearer | NLP message analysis |
| POST | /reports | Bearer | Create report |
| GET | /reports | Bearer | List reports |
| PATCH | /reports/{id} | Bearer | Update status/assignee/notes |
| GET | /dashboard/stats | Bearer | Dashboard data (trend, triggers, metrics) |
| GET | /evaluation/metrics | Bearer | Latest evaluation metrics |
| POST | /evaluation/run | Bearer | Run evaluation pipeline |

## Scoring Engine

| Component | Max Points | Source |
|-----------|-----------|--------|
| Heuristic rules | ~60 | URL structure, TLD, keywords, shorteners |
| Threat Intelligence | ~35 | VirusTotal, URLhaus |
| NLP message analysis | ~25 | Rule-based + optional ML |

**Threat Levels:** LOW (<25) | MED (25-54) | HIGH (>=55)

## OWASP Mapping

| Control | Implementation |
|---------|---------------|
| A01 Broken Access Control | JWT auth on all endpoints |
| A02 Cryptographic Failures | bcrypt password hashing, JWT HS256 |
| A03 Injection | SQLAlchemy ORM (parameterized queries) |
| A04 Insecure Design | Input validation, private IP rejection |
| A05 Security Misconfiguration | .env not committed, CORS configured |
| A07 XSS | Server returns JSON only, frontend escapes |
| Rate Limiting | Per-IP + per-endpoint middleware |
| Audit Logging | All mutations logged (actor, action, IP) |

## Running Tests

```powershell
cd backend
.venv\Scripts\python.exe -m pytest ../tests/ -v
```

## Running Evaluation

```powershell
# Via API
curl -X POST http://127.0.0.1:8001/evaluation/run -H "Authorization: Bearer <token>"

# Or directly
cd SIT-System
backend\.venv\Scripts\python.exe evaluation\evaluate.py
```

## Demo Flow (Viva)

1. Run `.\run_all.ps1` – backend, frontend, bot all start
2. Login at `http://127.0.0.1:5500/login.html`
3. Dashboard shows charts, triggers, metrics, live activity
4. Scan page: enter URL → see score, threat level, breakdown
5. Click a scan row → Evidence modal (copy, export PDF, create report)
6. Reports page: Kanban view, status workflow
7. Telegram: send URL to bot → auto-scan with formatted result
8. Press Ctrl+K → Command palette for quick navigation

## Security Reminders

- **NEVER** commit `.env` files
- Change `JWT_SECRET` for production
- Change default admin password after first login
- Rate limiter is in-memory (resets on restart)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MySQL connection refused | Start XAMPP MySQL, ensure `sit_db` exists |
| Schema errors after update | `DROP DATABASE sit_db; CREATE DATABASE sit_db;` |
| Telegram 409 conflict | Close old bot windows, delete `.bot.lock` |
| VirusTotal errors | Key is optional – system works without it |
| Rate limit 429 | Wait 60 seconds or restart backend |
