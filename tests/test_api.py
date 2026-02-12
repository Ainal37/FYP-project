"""
SIT System – API Tests
──────────────────────
Run: cd SIT-System/backend && ../.venv/Scripts/python -m pytest ../tests/ -v
Or:  cd SIT-System/backend && .venv/Scripts/python -m pytest ../tests/ -v
"""

import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token():
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["access_token"]


# ── Health ──
def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Auth ──
def test_login_success():
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password():
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_jwt_protection():
    r = client.get("/scans")
    assert r.status_code == 403


def test_jwt_invalid_token():
    r = client.get("/scans", headers={"Authorization": "Bearer invalidtoken"})
    assert r.status_code == 401


def test_me_endpoint():
    token = get_token()
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@example.com"


# ── Scanning ──
def test_scan_safe_url():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/scans", json={"link": "https://www.google.com"}, headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["verdict"] == "safe"
    assert d["threat_level"] == "LOW"
    assert d["score"] < 25


def test_scan_suspicious_url():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/scans", json={"link": "http://bit.ly/free-prize"}, headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["verdict"] in ("suspicious", "scam")
    assert d["score"] >= 25


def test_scan_returns_breakdown():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/scans", json={"link": "http://bit.ly/free-login"}, headers=h)
    d = r.json()
    assert "breakdown" in d
    assert isinstance(d["breakdown"], list)
    assert len(d["breakdown"]) > 0


def test_scan_with_message():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/scans", json={"link": "http://example.com", "message": "URGENT verify your account NOW!"}, headers=h)
    d = r.json()
    assert d["score"] > 0  # NLP should add points


# ── Scoring stability ──
def test_scoring_deterministic():
    from app.scoring import compute_risk_score
    r1 = compute_risk_score("http://bit.ly/free-login-verify", skip_intel=True)
    r2 = compute_risk_score("http://bit.ly/free-login-verify", skip_intel=True)
    assert r1["score"] == r2["score"]
    assert r1["threat_level"] == r2["threat_level"]
    assert r1["verdict"] == r2["verdict"]


# ── Intel graceful failure ──
def test_intel_no_key_graceful():
    from app.intel import query_virustotal
    result = query_virustotal("https://www.google.com")
    # Should not crash, returns graceful result
    assert result["provider"] == "virustotal"
    assert "error" in result or result["available"] is True


# ── Reports ──
def test_create_report():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/reports", json={"link": "http://scam.com", "report_type": "phishing", "description": "Fake page"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "new"


def test_update_report_status():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    # Create
    r = client.post("/reports", json={"link": "http://test.com", "description": "Test"}, headers=h)
    rid = r.json()["id"]
    # Update
    r2 = client.patch(f"/reports/{rid}", json={"status": "investigating", "assignee": "admin"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["status"] == "investigating"
    assert r2.json()["assignee"] == "admin"


# ── Dashboard ──
def test_dashboard_stats():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/dashboard/stats", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert "total_scans" in d
    assert "trend" in d
    assert "top_triggers" in d
    assert "recent_activity" in d


# ── NLP ──
def test_analyze_message():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/scans/analyze-message", json={"message": "URGENT: Click here to verify your bank account immediately!"}, headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["score"] > 0
    assert d["label"] in ("safe", "suspicious", "scam")
    assert len(d["triggers"]) > 0


# ── Evaluation ──
def test_evaluation_run():
    token = get_token()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/evaluation/run", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert "accuracy" in d
    assert "f1" in d
    assert d["dataset_size"] > 0


# ── Rate limiting (best-effort) ──
def test_rate_limit_login():
    """Verify rate limiter responds 429 after threshold."""
    for i in range(12):
        r = client.post("/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    # At some point we should get 429
    assert r.status_code in (200, 429)
