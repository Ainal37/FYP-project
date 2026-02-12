"""Heuristic scam/phishing link scanner."""

import re
from urllib.parse import urlparse

SHORTENERS = {
    "bit.ly", "t.co", "tinyurl.com", "goo.gl", "is.gd",
    "cutt.ly", "ow.ly", "buff.ly", "rb.gy", "shorturl.at",
}

KEYWORDS = [
    "login", "verify", "update", "secure", "bank", "wallet",
    "claim", "free", "bonus", "gift", "prize", "password",
    "confirm", "suspend", "account", "urgent",
]


def scan_link(link: str):
    """Return (verdict, score, reason_string)."""
    link = link.strip()
    if not re.match(r"^https?://", link):
        link = "http://" + link

    p = urlparse(link)
    host = (p.netloc or "").lower()
    scheme = (p.scheme or "").lower()

    score = 0
    reasons = []

    # HTTPS missing
    if scheme != "https":
        score += 10
        reasons.append("HTTPS missing")

    # URL shortener
    if host in SHORTENERS:
        score += 25
        reasons.append("URL shortener detected")

    # IP address as domain
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}(:\d+)?$", host):
        score += 35
        reasons.append("IP address used as domain")

    # Suspicious keywords in path/query
    text = (p.path + " " + (p.query or "")).lower()
    hits = [k for k in KEYWORDS if k in text]
    if hits:
        score += min(30, 5 * len(hits))
        reasons.append("Suspicious keywords: " + ", ".join(hits[:6]))

    # Too many subdomains
    if host.count(".") >= 3:
        score += 15
        reasons.append("Too many subdomains")

    # URL too long
    if len(link) > 120:
        score += 10
        reasons.append("URL too long")

    # Clamp
    score = min(score, 100)

    if score >= 70:
        verdict = "scam"
    elif score >= 35:
        verdict = "suspicious"
    else:
        verdict = "safe"

    reason = "; ".join(reasons) if reasons else "No obvious red flags"
    return verdict, score, reason
