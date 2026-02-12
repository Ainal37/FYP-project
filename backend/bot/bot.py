"""
SIT Telegram Bot
────────────────
Scammer Identification & Validation Tool – Telegram interface.

Commands:
  /start           – Welcome message
  /scan <link>     – Scan a URL for scam indicators
  /report <link> <reason> – Report a scam
  /help            – Show available commands

The bot authenticates with the backend using admin credentials,
caches the JWT token, and refreshes automatically on expiry.
"""

import os
import sys
import re
import time
import atexit
from pathlib import Path

import requests
from dotenv import load_dotenv
import telebot
from telebot import types

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BOT_DIR = Path(__file__).resolve().parent
ENV_PATH = BOT_DIR / ".env"
LOCK_FILE = BOT_DIR / ".bot.lock"

# ──────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────
if not ENV_PATH.is_file():
    print(f"[ERROR] .env not found at: {ENV_PATH}")
    sys.exit(1)

load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001").strip()
BOT_ADMIN_EMAIL = os.getenv("BOT_ADMIN_EMAIL", "admin@example.com").strip()
BOT_ADMIN_PASSWORD = os.getenv("BOT_ADMIN_PASSWORD", "admin123").strip()

if not TELEGRAM_BOT_TOKEN:
    print("[ERROR] TELEGRAM_BOT_TOKEN is not set in .env")
    sys.exit(1)

# ──────────────────────────────────────────────
# Lock file
# ──────────────────────────────────────────────
def _acquire_lock():
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            if _pid_alive(old_pid):
                print(f"[ERROR] Another bot instance running (PID {old_pid}).")
                sys.exit(1)
            else:
                print(f"[WARN] Stale lock (PID {old_pid}). Removing.")
        except (ValueError, OSError):
            pass
    LOCK_FILE.write_text(str(os.getpid()))


def _release_lock():
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(os.getpid()):
            LOCK_FILE.unlink()
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


# ──────────────────────────────────────────────
# Backend authentication (token caching)
# ──────────────────────────────────────────────
_cached_token = None
_token_time = 0
TOKEN_LIFETIME = 6 * 3600  # refresh every 6 hours


def _get_token():
    global _cached_token, _token_time
    if _cached_token and (time.time() - _token_time) < TOKEN_LIFETIME:
        return _cached_token
    try:
        print("[SIT Bot] Authenticating with backend...")
        resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": BOT_ADMIN_EMAIL, "password": BOT_ADMIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        _cached_token = resp.json()["access_token"]
        _token_time = time.time()
        print("[SIT Bot] Authenticated OK.")
        return _cached_token
    except Exception as exc:
        print(f"[SIT Bot] Auth failed: {exc}")
        return None


def _auth_headers():
    token = _get_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_post(path: str, payload: dict) -> dict | None:
    """POST JSON to the backend with auth. Re-authenticates on 401."""
    global _cached_token, _token_time
    headers = _auth_headers()
    if not headers:
        return None
    try:
        resp = requests.post(
            f"{BACKEND_URL}{path}", json=payload, headers=headers, timeout=10
        )
        if resp.status_code == 401:
            _cached_token = None
            _token_time = 0
            headers = _auth_headers()
            if not headers:
                return None
            resp = requests.post(
                f"{BACKEND_URL}{path}", json=payload, headers=headers, timeout=10
            )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[API ERROR] {path} -> {exc}")
        return None


# ──────────────────────────────────────────────
# Bot instance
# ──────────────────────────────────────────────
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)

VERDICT_EMOJI = {"safe": "\u2705", "suspicious": "\u26a0\ufe0f", "scam": "\U0001f6a8"}


def format_scan_result(data: dict) -> str:
    emoji = VERDICT_EMOJI.get(data.get("verdict", ""), "\u2753")
    verdict = (data.get("verdict") or "unknown").upper()
    score = data.get("score", 0)
    reason = data.get("reason", "No details")
    ts = data.get("created_at", "")
    return (
        f"{emoji} <b>Verdict: {verdict}</b>\n"
        f"Score: {score}/100\n"
        f"Reasons: {reason}\n"
        f"<i>{ts}</i>"
    )


# ── /start ──
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    bot.send_message(
        message.chat.id,
        "<b>Welcome to SIT Bot!</b>\n\n"
        "I detect scam links and help report suspicious activity.\n\n"
        "<b>Commands:</b>\n"
        "/scan <code>&lt;link&gt;</code> \u2013 Scan a URL\n"
        "/report <code>&lt;link&gt; &lt;reason&gt;</code> \u2013 Report a scam\n"
        "/help \u2013 Show help\n\n"
        "Or just send me any URL and I'll scan it automatically!",
    )


# ── /help ──
@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    bot.send_message(
        message.chat.id,
        "<b>SIT Bot \u2013 Help</b>\n\n"
        "/scan <code>&lt;link&gt;</code>\n"
        "  Analyse a URL for scam indicators.\n\n"
        "/report <code>&lt;link&gt; &lt;reason&gt;</code>\n"
        "  Report a suspicious link with a reason.\n\n"
        "You can also just paste a URL and I'll scan it.",
    )


# ── /scan ──
@bot.message_handler(commands=["scan"])
def cmd_scan(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(
            message,
            "Usage: /scan <code>&lt;link&gt;</code>\n\nExample:\n/scan https://bit.ly/free-prize",
        )
        return

    link = parts[1].strip()
    if not re.match(r"^https?://", link, re.IGNORECASE):
        link = "http://" + link

    bot.send_chat_action(message.chat.id, "typing")
    data = api_post("/scans", {
        "telegram_user_id": message.from_user.id,
        "telegram_username": message.from_user.username,
        "link": link,
    })

    if data is None:
        bot.reply_to(message, "Could not reach the backend. Please try again later.")
        return
    bot.reply_to(message, format_scan_result(data))


# ── /report ──
@bot.message_handler(commands=["report"])
def cmd_report(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(
            message,
            "Usage: /report <code>&lt;link&gt; &lt;reason&gt;</code>\n\n"
            "Example:\n/report https://scam.site Phishing page pretending to be a bank",
        )
        return

    link = parts[1].strip()
    reason = parts[2].strip()
    if not re.match(r"^https?://", link, re.IGNORECASE):
        link = "http://" + link

    bot.send_chat_action(message.chat.id, "typing")
    data = api_post("/reports", {
        "telegram_user_id": message.from_user.id,
        "telegram_username": message.from_user.username,
        "link": link,
        "report_type": "scam",
        "description": reason,
    })

    if data is None:
        bot.reply_to(message, "Could not submit the report. Please try again later.")
        return
    bot.reply_to(
        message,
        f"\u2705 <b>Report submitted!</b>\n"
        f"Report ID: <code>{data['id']}</code>\n"
        f"Status: {data['status']}",
    )


# ── Auto-scan bare URLs ──
@bot.message_handler(func=lambda m: m.text and URL_REGEX.search(m.text))
def auto_scan_url(message: types.Message):
    match = URL_REGEX.search(message.text)
    if not match:
        return
    link = match.group(0)

    bot.send_chat_action(message.chat.id, "typing")
    data = api_post("/scans", {
        "telegram_user_id": message.from_user.id,
        "telegram_username": message.from_user.username,
        "link": link,
    })

    if data is None:
        bot.reply_to(message, "Could not reach the backend.")
        return
    bot.reply_to(message, "Auto-scan detected a link!\n\n" + format_scan_result(data))


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    _acquire_lock()
    atexit.register(_release_lock)

    print("[SIT Bot] Removing any existing webhook...")
    bot.remove_webhook()

    print(f"[SIT Bot] .env loaded from: {ENV_PATH}")
    print(f"[SIT Bot] Backend: {BACKEND_URL}")
    print(f"[SIT Bot] PID: {os.getpid()}")

    # Pre-authenticate
    token = _get_token()
    if token:
        print("[SIT Bot] Backend auth: OK")
    else:
        print("[SIT Bot] Backend auth: FAILED (will retry on first request)")

    print("[SIT Bot] Bot started. Polling for messages...")
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=25)
    except KeyboardInterrupt:
        print("\n[SIT Bot] Stopped by user.")
    finally:
        _release_lock()
