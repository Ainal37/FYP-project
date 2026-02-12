import re
from urllib.parse import urlparse

SHORTENERS = {"bit.ly","t.co","tinyurl.com","goo.gl","is.gd","cutt.ly"}
KEYWORDS = ["login","verify","update","secure","bank","wallet","claim","free","bonus","gift"]

def scan_link(link: str):
    link = link.strip()
    if not re.match(r"^https?://", link):
        link = "http://" + link

    p = urlparse(link)
    host = (p.netloc or "").lower()

    score = 0
    reasons = []

    if host in SHORTENERS:
        score += 25
        reasons.append("URL shortener detected")

    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        score += 35
        reasons.append("IP used as domain")

    text = (p.path + " " + (p.query or "")).lower()
    hits = [k for k in KEYWORDS if k in text]
    if hits:
        score += min(30, 5 * len(hits))
        reasons.append("Suspicious keywords: " + ", ".join(hits[:6]))

    if host.count(".") >= 3:
        score += 15
        reasons.append("Too many subdomains")

    if len(link) > 120:
        score += 10
        reasons.append("URL too long")

    if score >= 70:
        verdict = "scam"
    elif score >= 35:
        verdict = "suspicious"
    else:
        verdict = "safe"

    reason = "; ".join(reasons) if reasons else "No obvious red flags"
    return verdict, score, reason
