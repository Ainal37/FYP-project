# ============================================================
#  SIT-System – One-Click Launcher (Windows PowerShell)
# ============================================================
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $ROOT

$BACKEND  = Join-Path $ROOT "backend"
$FRONTEND = Join-Path $ROOT "frontend\admin"
$VENV_PY  = Join-Path $BACKEND ".venv\Scripts\python.exe"
$BOT_DIR  = Join-Path $BACKEND "bot"
$BOT_LOCK = Join-Path $BOT_DIR ".bot.lock"

Write-Host ""
Write-Host "======================================" -ForegroundColor DarkGray
Write-Host "  SIT-System  v2.0  –  Starting...   " -ForegroundColor White
Write-Host "======================================" -ForegroundColor DarkGray
Write-Host ""
Write-Host "[REMINDER] Start XAMPP MySQL + ensure 'sit_db' exists." -ForegroundColor Yellow
Write-Host ""

# 1. Kill old bot
Write-Host "[1/5] Cleaning up old processes..." -ForegroundColor Gray
try {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*bot.py*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}
if (Test-Path -LiteralPath $BOT_LOCK) { Remove-Item -LiteralPath $BOT_LOCK -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# 2. Backend
Write-Host "[2/5] Starting Backend :8001..." -ForegroundColor White
$beCmd = "Set-Location -LiteralPath '$BACKEND'; & '$VENV_PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload; Read-Host 'Press Enter'"
Start-Process powershell -ArgumentList "-NoExit","-Command",$beCmd

# 3. Frontend
Write-Host "[3/5] Starting Frontend :5500..." -ForegroundColor White
$feCmd = "Set-Location -LiteralPath '$FRONTEND'; & '$VENV_PY' -m http.server 5500 --bind 127.0.0.1; Read-Host 'Press Enter'"
Start-Process powershell -ArgumentList "-NoExit","-Command",$feCmd

# 4. Bot
Write-Host "[4/5] Starting Bot (3s delay)..." -ForegroundColor White
Start-Sleep -Seconds 3
$botCmd = "Set-Location -LiteralPath '$BOT_DIR'; & '$VENV_PY' -u bot.py; Read-Host 'Press Enter'"
Start-Process powershell -ArgumentList "-NoExit","-Command",$botCmd

# 5. Status
Write-Host "[5/5] Checking ports..." -ForegroundColor Gray
Start-Sleep -Seconds 5

function Test-Port { param([string]$H,[int]$P)
    try { $t=New-Object System.Net.Sockets.TcpClient; $a=$t.BeginConnect($H,$P,$null,$null); $ok=$a.AsyncWaitHandle.WaitOne(2000); if($ok){$t.EndConnect($a)}; $t.Close(); return $ok } catch { return $false }
}
$be = Test-Port "127.0.0.1" 8001; $fe = Test-Port "127.0.0.1" 5500

Write-Host ""
Write-Host "======================================" -ForegroundColor DarkGray
if ($be) { Write-Host "  Backend  (8001) : OK" -ForegroundColor Green } else { Write-Host "  Backend  (8001) : FAIL" -ForegroundColor Red }
if ($fe) { Write-Host "  Frontend (5500) : OK" -ForegroundColor Green } else { Write-Host "  Frontend (5500) : FAIL" -ForegroundColor Red }
Write-Host "  Bot              : Started" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor DarkGray
Write-Host ""

Start-Process "http://127.0.0.1:8001/docs"
Start-Process "http://127.0.0.1:5500/login.html"

Write-Host "Admin: admin@example.com / admin123" -ForegroundColor White
Write-Host "Swagger: http://127.0.0.1:8001/docs" -ForegroundColor Gray
Write-Host "Panel:   http://127.0.0.1:5500/login.html" -ForegroundColor Gray
Write-Host ""
