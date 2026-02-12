# ==========================================
# SIT-System  –  One-Click Launcher
# Backend (FastAPI) + Frontend (Admin) + Telegram Bot
# ==========================================
#
# USAGE:   Right-click -> Run with PowerShell
#     or:  powershell -ExecutionPolicy Bypass -File run_all.ps1
#
# PRE-REQUISITES:
#   1. XAMPP MySQL must be running on port 3306.
#   2. Python venv at backend/.venv with all deps installed.
# ==========================================

$ErrorActionPreference = "Stop"

# ── Resolve paths (handles spaces in directory names) ──
$ROOT         = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR  = Join-Path $ROOT "backend"
$FRONTEND_DIR = Join-Path $ROOT "frontend\admin"
$BOT_DIR      = Join-Path $BACKEND_DIR "bot"
$VENV_PY      = Join-Path $BACKEND_DIR ".venv\Scripts\python.exe"
$BOT_LOCK     = Join-Path $BOT_DIR ".bot.lock"

# ── Sanity checks ──
if (-not (Test-Path $VENV_PY)) {
    Write-Host "[FAIL] Python venv not found: $VENV_PY" -ForegroundColor Red
    Write-Host "       Run:  cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   SIT-System  –  One-Click Launcher" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── Reminder: XAMPP MySQL ──
Write-Host "[REMINDER] Make sure XAMPP MySQL is running on port 3306." -ForegroundColor Yellow
Write-Host ""

# ── Pre-step: remove stale bot lock file ──
if (Test-Path $BOT_LOCK) {
    Remove-Item -LiteralPath $BOT_LOCK -Force -ErrorAction SilentlyContinue
    Write-Host "[CLEANUP] Removed stale bot lock: $BOT_LOCK" -ForegroundColor DarkGray
}

# ── 1) Start Backend (FastAPI on port 8001) ──
Write-Host "[1/3] Starting Backend (uvicorn :8001) ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location -LiteralPath '$BACKEND_DIR'; & '$VENV_PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload --log-level info"
)

# ── 2) Start Frontend static server (port 5500) ──
Write-Host "[2/3] Starting Frontend (http.server :5500) ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location -LiteralPath '$FRONTEND_DIR'; & '$VENV_PY' -m http.server 5500"
)

# ── 3) Start Telegram Bot ──
Write-Host "[3/3] Starting Telegram Bot ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location -LiteralPath '$BACKEND_DIR'; & '$VENV_PY' -u bot/bot.py"
)

# ── Wait for services to spin up ──
Write-Host ""
Write-Host "Waiting 6 seconds for services to start..." -ForegroundColor DarkGray
Start-Sleep -Seconds 6

# ── Port status check ──
Write-Host ""
Write-Host "──────────── Status Check ────────────" -ForegroundColor Cyan

function Test-Port {
    param([string]$Host_, [int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect($Host_, $Port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

$backendUp  = Test-Port "127.0.0.1" 8001
$frontendUp = Test-Port "127.0.0.1" 5500

if ($backendUp) {
    Write-Host "  Backend  (127.0.0.1:8001)  [PASS]" -ForegroundColor Green
} else {
    Write-Host "  Backend  (127.0.0.1:8001)  [FAIL] - check backend window for errors" -ForegroundColor Red
}

if ($frontendUp) {
    Write-Host "  Frontend (127.0.0.1:5500)  [PASS]" -ForegroundColor Green
} else {
    Write-Host "  Frontend (127.0.0.1:5500)  [FAIL] - check frontend window for errors" -ForegroundColor Red
}

Write-Host "  Bot      (polling mode)     [STARTED]" -ForegroundColor Green
Write-Host ""

# ── Auto-open browser tabs ──
if ($backendUp) {
    Start-Process "http://127.0.0.1:8001/docs"
}
if ($frontendUp) {
    Start-Process "http://127.0.0.1:5500/login.html"
}

# ── Summary ──
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Swagger API :  http://127.0.0.1:8001/docs"
Write-Host "  Admin Panel :  http://127.0.0.1:5500/login.html"
Write-Host "  Default login: admin@example.com / admin123"
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
