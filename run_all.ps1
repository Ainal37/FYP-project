# ==========================================
# SIT-System One-Click Runner (VIVA READY)
# Backend + Frontend Admin + Telegram Bot
# ==========================================

$ErrorActionPreference = "Stop"

# Root folder = folder where this .ps1 lives
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

$BACKEND_DIR  = Join-Path $ROOT "backend"
$FRONTEND_DIR = Join-Path $ROOT "frontend\admin"

$PY   = Join-Path $BACKEND_DIR ".venv\Scripts\python.exe"
$LOCK = Join-Path $BACKEND_DIR "bot\.bot.lock"

$BACKEND_URL  = "http://127.0.0.1:8001"
$FRONTEND_URL = "http://127.0.0.1:5500/login.html"
$SWAGGER_URL  = "http://127.0.0.1:8001/docs"

function Test-Port {
  param(
    [string]$HostName = "127.0.0.1",
    [int]$Port
  )
  try {
    $r = Test-NetConnection -ComputerName $HostName -Port $Port -WarningAction SilentlyContinue
    return [bool]$r.TcpTestSucceeded
  } catch {
    return $false
  }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " SIT-System Runner (VIVA READY)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Reminder: Start XAMPP MySQL first (Apache optional)." -ForegroundColor Yellow
Write-Host "ROOT: $ROOT" -ForegroundColor DarkGray
Write-Host ""

# Check venv python exists
if (-not (Test-Path $PY)) {
  Write-Host "❌ venv python not found: $PY" -ForegroundColor Red
  Write-Host "Fix: create venv at backend\.venv and install requirements." -ForegroundColor Yellow
  exit 1
}

# 0) Clean bot lock (prevents 'already running' lock error)
if (Test-Path $LOCK) {
  Remove-Item $LOCK -Force
  Write-Host "🧹 Removed bot lock: $LOCK" -ForegroundColor DarkGray
}

# 0b) Kill ONLY the old bot process to avoid Telegram 409 conflict
# If your bot prints PID to a file, you can use that. For now we kill by commandline matching bot.py
try {
  $botProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "bot\.py" -and $_.CommandLine -match "backend\\bot" }

  foreach ($p in $botProcs) {
    Write-Host "🛑 Stopping old bot process PID $($p.ProcessId) (avoid 409)..." -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
  }
} catch {
  # ignore
}

# 1) Backend (FastAPI)
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "& { Set-Location -LiteralPath '$BACKEND_DIR'; & '$PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload --log-level info }"
)

# 2) Frontend (static server)
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "& { Set-Location -LiteralPath '$FRONTEND_DIR'; py -m http.server 5500 }"
)

# 3) Bot (Telegram polling)
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "& { Set-Location -LiteralPath '$BACKEND_DIR\bot'; & '$PY' bot.py }"
)

# Wait a bit for servers to start
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "==================== STATUS CHECK ====================" -ForegroundColor Cyan

if (Test-Port -Port 8001) {
  Write-Host "✅ Backend  (127.0.0.1:8001)  [PASS]" -ForegroundColor Green
} else {
  Write-Host "❌ Backend  (127.0.0.1:8001)  [FAIL]  -> check uvicorn window" -ForegroundColor Red
}

if (Test-Port -Port 5500) {
  Write-Host "✅ Frontend (127.0.0.1:5500)  [PASS]" -ForegroundColor Green
} else {
  Write-Host "❌ Frontend (127.0.0.1:5500)  [FAIL]  -> check http.server window" -ForegroundColor Red
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Auto-open pages
Start-Process $SWAGGER_URL
Start-Process $FRONTEND_URL

Write-Host "✅ Started: Backend(8001) + Frontend(5500) + Bot" -ForegroundColor Green
Write-Host "Open: $SWAGGER_URL" -ForegroundColor Green
Write-Host "Open: $FRONTEND_URL" -ForegroundColor Green
Write-Host ""
Write-Host "Default admin (if used): admin@example.com / admin123" -ForegroundColor DarkGray
Write-Host ""
