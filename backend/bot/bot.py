"""
SIT Telegram Bot – Enterprise MVP
──────────────────────────────────
Authenticates with backend, caches JWT, auto-scans URLs, /scan, /report.
"""

import os, sys, re, time, atexit
from pathlib import Path

import requests
from dotenv import load_dotenv
import telebot
from telebot import types

BOT_DIR  = Path(__file__).resolve().parent
ENV_PATH = BOT_DIR / ".env"
LOCK_FILE = BOT_DIR / ".bot.lock"

if not ENV_PATH.is_file():
    print(f"[ERROR] .env not found: {ENV_PATH}"); sys.exit(1)

load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BACKEND_URL        = os.getenv("BACKEND_URL", "http://127.0.0.1:8001").strip()
BOT_ADMIN_EMAIL    = os.getenv("BOT_ADMIN_EMAIL", "admin@example.com").strip()
BOT_ADMIN_PASSWORD = os.getenv("BOT_ADMIN_PASSWORD", "admin123").strip()

if not TELEGRAM_BOT_TOKEN:
    print("[ERROR] TELEGRAM_BOT_TOKEN not set"); sys.exit(1)

# ── Lock file ──
def _acquire_lock():
    if LOCK_FILE.exists():
        try:
            old = int(LOCK_FILE.read_text().strip())
            if _alive(old): print(f"[ERROR] Bot already running PID {old}"); sys.exit(1)
            else: print(f"[WARN] Stale lock PID {old}")
        except: pass
    LOCK_FILE.write_text(str(os.getpid()))

def _release_lock():
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(os.getpid()): LOCK_FILE.unlink()
    except: pass

def _alive(pid):
    if sys.platform == "win32":
        import ctypes; h = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
        if h: ctypes.windll.kernel32.CloseHandle(h); return True
        return False
    try: os.kill(pid, 0); return True
    except: return False

# ── Backend auth ──
_token = None; _token_ts = 0
_API_TIMEOUT = 20  # seconds (increased from 10 so slow first requests don't fail)

def _wait_for_backend(max_attempts=30):
    """Block until backend /health responds. Uses exponential backoff."""
    delays = [1, 1, 2, 2, 3, 3, 5, 5, 10]  # then 10s forever
    for attempt in range(1, max_attempts + 1):
        delay = delays[min(attempt - 1, len(delays) - 1)]
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=3)
            if r.status_code == 200:
                data = r.json()
                print(f"[Bot] Backend healthy (db={data.get('db')}, v={data.get('version')})")
                return True
        except Exception:
            pass
        print(f"[Bot] Waiting for backend... attempt {attempt}, retry in {delay}s")
        time.sleep(delay)
    print("[Bot] Backend never became healthy after max attempts")
    return False


def _get_token():
    """Authenticate with backend. Retries with backoff on failure."""
    global _token, _token_ts
    if _token and time.time() - _token_ts < 21600:
        return _token
    delays = [1, 2, 3, 5, 10]
    for attempt in range(1, 11):
        delay = delays[min(attempt - 1, len(delays) - 1)]
        try:
            r = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": BOT_ADMIN_EMAIL, "password": BOT_ADMIN_PASSWORD},
                timeout=_API_TIMEOUT,
            )
            r.raise_for_status()
            _token = r.json()["access_token"]
            _token_ts = time.time()
            print("[Bot] Auth success")
            return _token
        except Exception as e:
            print(f"[Bot] Auth failed (attempt {attempt}): {e}")
            if attempt < 10:
                print(f"[Bot] Auth retry in {delay}s...")
                time.sleep(delay)
    print("[Bot] Auth: all retries exhausted")
    return None


def api_post(path, payload):
    """POST to backend API with automatic token refresh on 401."""
    global _token, _token_ts
    t = _get_token()
    if not t:
        return None
    try:
        r = requests.post(
            f"{BACKEND_URL}{path}", json=payload,
            headers={"Authorization": f"Bearer {t}"}, timeout=_API_TIMEOUT,
        )
        if r.status_code == 401:
            _token = None; _token_ts = 0
            t = _get_token()
            if not t:
                return None
            r = requests.post(
                f"{BACKEND_URL}{path}", json=payload,
                headers={"Authorization": f"Bearer {t}"}, timeout=_API_TIMEOUT,
            )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API] {path} -> {e}")
        return None

# ── Bot ──
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")
URL_RE = re.compile(r"https?://\S+", re.I)
EMOJI = {"safe": "\u2705", "suspicious": "\u26a0\ufe0f", "scam": "\U0001f6a8"}

def fmt(d):
    e = EMOJI.get(d.get("verdict",""), "\u2753")
    tl = d.get("threat_level", "")
    score = d.get("score", 0)
    verdict = d.get("verdict", "?").upper()
    reason = d.get("reason", "N/A")[:300]
    ts = d.get("created_at", "")

    if tl == "HIGH":
        bar = "\u2588" * min(score // 5, 20)
        return (
            f"\U0001f6a8\U0001f6a8\U0001f6a8 <b>HIGH THREAT DETECTED</b> \U0001f6a8\U0001f6a8\U0001f6a8\n"
            f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            f"\u26a0\ufe0f <b>Verdict:</b> {verdict}\n"
            f"\U0001f4ca <b>Score:</b> {score}/100  [{bar}]\n"
            f"\U0001f534 <b>Threat Level:</b> {tl}\n"
            f"\U0001f50d <b>Reasons:</b> {reason}\n"
            f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            f"\u26d4 <b>DO NOT visit this URL.</b>\n"
            f"<i>{ts}</i>"
        )

    return (f"{e} <b>Verdict: {verdict}</b>\n"
            f"Threat Level: {tl}\n"
            f"Score: {score}/100\n"
            f"Reasons: {reason}\n"
            f"<i>{ts}</i>")

@bot.message_handler(commands=["start"])
def cmd_start(m):
    bot.send_message(m.chat.id,
        "<b>Welcome to SIT Bot!</b>\n\n"
        "/scan <code>&lt;url&gt;</code> \u2013 Scan a URL\n"
        "/report <code>&lt;url&gt; &lt;reason&gt;</code> \u2013 Report\n"
        "/help \u2013 Help\n\n"
        "Or paste any URL to auto-scan!")

@bot.message_handler(commands=["help"])
def cmd_help(m):
    bot.send_message(m.chat.id,
        "<b>SIT Bot</b>\n"
        "/scan &lt;url&gt; \u2013 Analyse URL\n"
        "/report &lt;url&gt; &lt;reason&gt; \u2013 Report scam\n"
        "Paste a URL \u2013 Auto-scan")

@bot.message_handler(commands=["scan"])
def cmd_scan(m):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(m, "Usage: /scan &lt;url&gt;"); return
    link = parts[1].strip()
    if not re.match(r"^https?://", link, re.I): link = "http://" + link
    bot.send_chat_action(m.chat.id, "typing")
    msg_text = m.text if len(m.text) > len(link) + 10 else None
    d = api_post("/scans", {"telegram_user_id": m.from_user.id, "telegram_username": m.from_user.username, "link": link, "message": msg_text})
    if not d: bot.reply_to(m, "Backend unreachable."); return
    bot.reply_to(m, fmt(d))

@bot.message_handler(commands=["report"])
def cmd_report(m):
    parts = m.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(m, "Usage: /report &lt;url&gt; &lt;reason&gt;"); return
    link, reason = parts[1].strip(), parts[2].strip()
    if not re.match(r"^https?://", link, re.I): link = "http://" + link
    bot.send_chat_action(m.chat.id, "typing")
    d = api_post("/reports", {"telegram_user_id": m.from_user.id, "telegram_username": m.from_user.username, "link": link, "report_type": "scam", "description": reason})
    if not d: bot.reply_to(m, "Could not submit."); return
    bot.reply_to(m, f"\u2705 <b>Report #{d['id']}</b> submitted ({d['status']})")

@bot.message_handler(func=lambda m: m.text and URL_RE.search(m.text))
def auto_scan(m):
    link = URL_RE.search(m.text).group(0)
    bot.send_chat_action(m.chat.id, "typing")
    d = api_post("/scans", {"telegram_user_id": m.from_user.id, "telegram_username": m.from_user.username, "link": link, "message": m.text})
    if not d: bot.reply_to(m, "Backend unreachable."); return
    bot.reply_to(m, "Auto-scan:\n\n" + fmt(d))

if __name__ == "__main__":
    _acquire_lock(); atexit.register(_release_lock)
    print("[Bot] Removing webhook..."); bot.remove_webhook()
    print(f"[Bot] Backend: {BACKEND_URL}  PID: {os.getpid()}")

    # Wait for backend to be healthy before trying to authenticate
    _wait_for_backend(max_attempts=30)

    t = _get_token()
    if not t:
        print("[Bot] WARNING: Auth failed, but starting polling anyway (will retry on each request)")
    else:
        print("[Bot] Auth: OK")

    print("[Bot] Polling...")
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=25)
    except KeyboardInterrupt:
        print("\n[Bot] Stopped.")
    finally:
        _release_lock()
