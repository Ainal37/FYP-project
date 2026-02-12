"""
SIT Telegram Bot
─────────────────
Scammer Identification & Validation Tool – Telegram interface.

Commands:
  /start        – Welcome message
  /scan <link>  – Scan a URL for scam indicators
  /report       – Start a guided report flow
  /help         – Show available commands

HOW TO RUN:
  1. Make sure no other bot instance is running:
       - Close any other terminal running bot.py
       - On Windows:  tasklist | findstr python
       - On Linux:    ps aux | grep bot.py
  2. If you previously set a webhook, this script removes it automatically.
  3. Start the backend first:
       cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8001
  4. Then run this bot:
       cd backend/bot && python bot.py
"""

import os
import sys
import re
import atexit
from pathlib import Path

import requests
from dotenv import load_dotenv
import telebot
from telebot import types

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BOT_DIR = Path(__file__).resolve().parent          # backend/bot/
ENV_PATH = BOT_DIR / ".env"                        # backend/bot/.env
LOCK_FILE = BOT_DIR / ".bot.lock"                  # backend/bot/.bot.lock

# ──────────────────────────────────────────────
# Environment – single source: backend/bot/.env
# ──────────────────────────────────────────────
if not ENV_PATH.is_file():
    print(f"[ERROR] .env not found at: {ENV_PATH}")
    print("        Create backend/bot/.env with TELEGRAM_BOT_TOKEN and BACKEND_URL.")
    sys.exit(1)

load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001").strip()

if not TELEGRAM_BOT_TOKEN:
    print("[ERROR] TELEGRAM_BOT_TOKEN is not set in .env")
    print(f"        Checked: {ENV_PATH}")
    sys.exit(1)

# ──────────────────────────────────────────────
# Lock file – prevent duplicate polling instances
# ──────────────────────────────────────────────
def _acquire_lock():
    """Create a lock file with our PID. Exit if another instance is alive."""
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            # Check if that PID is still running
            if _pid_alive(old_pid):
                print(f"[ERROR] Another bot instance is already running (PID {old_pid}).")
                print("        Stop it first, then retry.")
                print(f"        Lock file: {LOCK_FILE}")
                sys.exit(1)
            else:
                # Stale lock – previous process died
                print(f"[WARN]  Stale lock found (PID {old_pid} is dead). Removing.")
        except (ValueError, OSError):
            pass  # Corrupt lock file – overwrite it

    LOCK_FILE.write_text(str(os.getpid()))


def _release_lock():
    """Remove the lock file on exit."""
    try:
        if LOCK_FILE.exists():
            stored = LOCK_FILE.read_text().strip()
            if stored == str(os.getpid()):
                LOCK_FILE.unlink()
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    """Check whether a process with the given PID is running."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
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
# Bot instance
# ──────────────────────────────────────────────
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# Temp store for multi-step /report flow  {chat_id: dict}
report_sessions = {}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)

VERDICT_EMOJI = {
    "safe": "✅",
    "suspicious": "⚠️",
    "scam": "🚨",
}


def api_post(path: str, payload: dict) -> dict | None:
    """POST JSON to the backend and return the parsed response, or None on failure."""
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"[API ERROR] {path} -> {exc}")
        return None


# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    bot.send_message(
        message.chat.id,
        "<b>Welcome to SIT Bot!</b>\n\n"
        "I can help you identify scam links and report suspicious activity.\n\n"
        "Commands:\n"
        "/scan <code>&lt;link&gt;</code> – Scan a URL\n"
        "/report – Report a scammer\n"
        "/help – Show help",
    )


# ──────────────────────────────────────────────
# /help
# ──────────────────────────────────────────────
@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    bot.send_message(
        message.chat.id,
        "<b>SIT Bot – Help</b>\n\n"
        "/scan <code>&lt;link&gt;</code>\n"
        "  Analyse a URL and get a safety verdict.\n\n"
        "/report\n"
        "  Submit a scam report (guided flow).\n\n"
        "/start\n"
        "  Show the welcome message.",
    )


# ──────────────────────────────────────────────
# /scan
# ──────────────────────────────────────────────
@bot.message_handler(commands=["scan"])
def cmd_scan(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /scan <code>&lt;link&gt;</code>\n\nExample:\n/scan https://bit.ly/free-prize")
        return

    link = parts[1].strip()

    # Ensure it looks like a URL
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

    emoji = VERDICT_EMOJI.get(data["verdict"], "?")
    bot.reply_to(
        message,
        f"{emoji} <b>Verdict:</b> {data['verdict'].upper()}\n"
        f"<b>Score:</b> {data['score']} / 100\n"
        f"<b>Reason:</b> {data['reason']}",
    )


# ──────────────────────────────────────────────
# /report  (guided multi-step flow)
# ──────────────────────────────────────────────
@bot.message_handler(commands=["report"])
def cmd_report(message: types.Message):
    chat_id = message.chat.id
    report_sessions[chat_id] = {
        "step": "message",
        "user_id": message.from_user.id,
        "username": message.from_user.username,
    }
    bot.send_message(chat_id, "<b>Report a scammer</b>\n\nPlease describe the scam or suspicious activity:")
    bot.register_next_step_handler(message, report_step_message)


def report_step_message(message: types.Message):
    chat_id = message.chat.id
    session = report_sessions.get(chat_id)
    if not session:
        return

    session["message_text"] = message.text.strip()
    session["step"] = "link"
    bot.send_message(chat_id, "Now paste the suspicious link (or type <b>skip</b> if none):")
    bot.register_next_step_handler(message, report_step_link)


def report_step_link(message: types.Message):
    chat_id = message.chat.id
    session = report_sessions.get(chat_id)
    if not session:
        return

    text = message.text.strip()
    link = None if text.lower() == "skip" else text

    bot.send_chat_action(chat_id, "typing")

    data = api_post("/reports", {
        "telegram_user_id": session["user_id"],
        "telegram_username": session.get("username"),
        "message": session["message_text"],
        "link": link,
    })

    report_sessions.pop(chat_id, None)

    if data is None:
        bot.send_message(chat_id, "Could not submit the report. Please try again later.")
        return

    bot.send_message(
        chat_id,
        f"<b>Report submitted!</b>\n"
        f"Report ID: <code>{data['id']}</code>\n"
        f"Status: {data['status']}",
    )


# ──────────────────────────────────────────────
# Catch-all: auto-scan if user sends a bare URL
# ──────────────────────────────────────────────
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

    emoji = VERDICT_EMOJI.get(data["verdict"], "?")
    bot.reply_to(
        message,
        f"Auto-scan detected a link!\n\n"
        f"{emoji} <b>Verdict:</b> {data['verdict'].upper()}\n"
        f"<b>Score:</b> {data['score']} / 100\n"
        f"<b>Reason:</b> {data['reason']}",
    )


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Acquire lock – exit if another instance is running
    _acquire_lock()
    atexit.register(_release_lock)

    # 2. Remove any existing webhook so polling doesn't conflict
    print("[SIT Bot] Removing any existing webhook...")
    bot.remove_webhook()

    # 3. Start
    print(f"[SIT Bot] .env loaded from: {ENV_PATH}")
    print(f"[SIT Bot] Backend: {BACKEND_URL}")
    print(f"[SIT Bot] PID: {os.getpid()}")
    print("[SIT Bot] Bot started. Polling for messages...")

    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=25)
    except KeyboardInterrupt:
        print("\n[SIT Bot] Stopped by user.")
    finally:
        _release_lock()
