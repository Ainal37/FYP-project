# ============================================================
#  SIT-System  –  One-Click Launcher (Windows PowerShell)
# ============================================================
#
#  Starts: Backend (uvicorn :8001) + Frontend (:5500) + Bot
#  Prerequisites: XAMPP MySQL running, sit_db created
# ============================================================

$ErrorActionPreference = "Stop"

# ── Resolve project root (handles spaces in path) ──
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $ROOT

$BACKEND  = Join-Path $ROOT "backend"
$FRONTEND = Join-Path $ROOT "frontend\admin"
$VENV_PY  = Join-Path $BACKEND ".venv\Scripts\python.exe"
$BOT_DIR  = Join-Path $BACKEND "bot"
$BOT_LOCK = Join-Path $BOT_DIR ".bot.lock"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SIT-System  –  Starting ALL services  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 0. Reminder ──
Write-Host "[REMINDER] Make sure XAMPP MySQL is running and 'sit_db' database exists." -ForegroundColor Yellow
Write-Host ""

# ── 1. Kill old bot processes to avoid Telegram 409 ──
Write-Host "[1/5] Cleaning up old bot processes..." -ForegroundColor Gray
try {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*bot.py*" } |
        ForEach-Object {
            Write-Host "       Killing old bot PID $($_.ProcessId)" -ForegroundColor DarkYellow
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
} catch { }

if (Test-Path -LiteralPath $BOT_LOCK) {
    Remove-Item -LiteralPath $BOT_LOCK -Force -ErrorAction SilentlyContinue
    Write-Host "       Removed stale .bot.lock" -ForegroundColor DarkYellow
}
Start-Sleep -Seconds 1

# ── 2. Start Backend (uvicorn) ──
Write-Host "[2/5] Starting Backend on 127.0.0.1:8001..." -ForegroundColor Green
$backendCmd = "Set-Location -LiteralPath '$BACKEND'; & '$VENV_PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# ── 3. Start Frontend (http.server) ──
Write-Host "[3/5] Starting Frontend on 127.0.0.1:5500..." -ForegroundColor Green
$frontendCmd = "Set-Location -LiteralPath '$FRONTEND'; & '$VENV_PY' -m http.server 5500 --bind 127.0.0.1; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# ── 4. Start Telegram Bot ──
Write-Host "[4/5] Starting Telegram Bot (polling)..." -ForegroundColor Green
Start-Sleep -Seconds 3
$botCmd = "Set-Location -LiteralPath '$BOT_DIR'; & '$VENV_PY' -u bot.py; Read-Host 'Press Enter to close'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $botCmd

# ── 5. Wait and check ports ──
Write-Host "[5/5] Waiting for services to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

function Test-Port {
    param([string]$H, [int]$P)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $ar  = $tcp.BeginConnect($H, $P, $null, $null)
        $ok  = $ar.AsyncWaitHandle.WaitOne(2000)
        if ($ok) { $tcp.EndConnect($ar) }
        $tcp.Close()
        return $ok
    } catch { return $false }
}

$be = Test-Port "127.0.0.1" 8001
$fe = Test-Port "127.0.0.1" 5500

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "           STATUS SUMMARY               " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($be) { Write-Host "  Backend  (8001) : PASS" -ForegroundColor Green }
else     { Write-Host "  Backend  (8001) : FAIL" -ForegroundColor Red   }

if ($fe) { Write-Host "  Frontend (5500) : PASS" -ForegroundColor Green }
else     { Write-Host "  Frontend (5500) : FAIL" -ForegroundColor Red   }

Write-Host "  Bot              : Started (check its window)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 6. Open browser tabs ──
Write-Host "Opening browser..." -ForegroundColor Gray
Start-Process "http://127.0.0.1:8001/docs"
Start-Process "http://127.0.0.1:5500/login.html"

Write-Host ""
Write-Host "Default admin: admin@example.com / admin123" -ForegroundColor Magenta
Write-Host "Swagger docs:  http://127.0.0.1:8001/docs" -ForegroundColor Magenta
Write-Host "Admin panel:   http://127.0.0.1:5500/login.html" -ForegroundColor Magenta
Write-Host ""
Write-Host "To stop all services, close the spawned PowerShell windows." -ForegroundColor DarkGray
