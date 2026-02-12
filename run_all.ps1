# ==========================================
# SIT-System One-Click Runner (VIVA READY)
# Backend + Frontend Admin + Telegram Bot
# ==========================================

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

$BACKEND_DIR  = Join-Path $ROOT "backend"
$FRONTEND_DIR = Join-Path $ROOT "frontend\admin"

$PY   = Join-Path $BACKEND_DIR ".venv\Scripts\python.exe"
$LOCK = Join-Path $BACKEND_DIR "bot\.bot.lock"

function Test-PortFast {
  param([string]$HostName="127.0.0.1",[int]$Port,[int]$TimeoutMs=500)
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($HostName, $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    if (-not $ok) { $client.Close(); return $false }
    $client.EndConnect($iar); $client.Close(); return $true
  } catch { return $false }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " SIT-System Runner (VIVA READY)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Reminder: Start XAMPP MySQL first (Apache optional)." -ForegroundColor Yellow
Write-Host "ROOT: $ROOT" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path $PY)) {
  Write-Host "❌ venv python not found: $PY" -ForegroundColor Red
  Write-Host "Fix: create venv at backend\.venv and install requirements." -ForegroundColor Yellow
  exit 1
}

# Remove bot lock
if (Test-Path $LOCK) {
  Remove-Item $LOCK -Force
  Write-Host "🧹 Removed bot lock: $LOCK" -ForegroundColor DarkGray
}

# Kill old bot only (avoid Telegram 409)
try {
  $botProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "bot\.py" -and $_.CommandLine -match "backend\\bot" }
  foreach ($p in $botProcs) {
    Write-Host "🛑 Stopping old bot PID $($p.ProcessId)..." -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
  }
} catch {}

# 1) Backend
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "& { Set-Location -LiteralPath '$BACKEND_DIR'; & '$PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload --log-level info }"
)

# 2) Frontend server
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "& { Set-Location -LiteralPath '$FRONTEND_DIR'; py -m http.server 5500 }"
)

# 3) Bot
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "& { Set-Location -LiteralPath '$BACKEND_DIR\bot'; & '$PY' bot.py }"
)

Start-Sleep -Seconds 2

Write-Host "==================== STATUS CHECK ====================" -ForegroundColor Cyan
if (Test-PortFast -Port 8001) { Write-Host "✅ Backend  (127.0.0.1:8001) [PASS]" -ForegroundColor Green }
else { Write-Host "❌ Backend  (127.0.0.1:8001) [FAIL]" -ForegroundColor Red }

if (Test-PortFast -Port 5500) { Write-Host "✅ Frontend (127.0.0.1:5500) [PASS]" -ForegroundColor Green }
else { Write-Host "❌ Frontend (127.0.0.1:5500) [FAIL]" -ForegroundColor Red }
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

Start-Process "http://127.0.0.1:8001/docs"
Start-Process "http://127.0.0.1:5500/login.html"

Write-Host "✅ Started: Backend(8001) + Frontend(5500) + Bot" -ForegroundColor Green
Write-Host "Notes: To stop everything, close the spawned PowerShell windows." -ForegroundColor DarkGray
Write-Host ""
