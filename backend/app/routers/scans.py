"""Scan endpoints: create + list + detail + analyze-message."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Scan
from ..scoring import compute_risk_score
from ..alerts import send_high_threat_alert
from ..validators import validate_url, validate_message
from ..security import get_current_admin
from ..schemas import ScanRequest, ScanResponse, MessageRequest
from ..nlp import analyze_message

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanResponse)
def create_scan(
    payload: ScanRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    link = validate_url(payload.link)
    msg = payload.message.strip() if payload.message else None

    result = compute_risk_score(link, message=msg)

    s = Scan(
        telegram_user_id=payload.telegram_user_id,
        telegram_username=payload.telegram_username,
        link=link,
        verdict=result["verdict"],
        score=result["score"],
        threat_level=result["threat_level"],
        reason=result["reason"][:2000],
        breakdown=json.dumps(result["breakdown"]),
        intel_summary=json.dumps(result.get("intel_summary", {})),
        message=msg,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    # Alert on HIGH threat
    if result["threat_level"] == "HIGH":
        send_high_threat_alert({
            "id": s.id, "link": s.link, "score": s.score,
            "threat_level": s.threat_level, "reason": s.reason,
        })

    return _scan_to_response(s, result["breakdown"])


@router.get("")
def list_scans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Search by link text"),
    verdict: Optional[str] = Query(None, description="Filter by verdict: safe/suspicious/scam"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level: LOW/MED/HIGH"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(Scan)
    if search:
        q = q.filter(Scan.link.ilike(f"%{search}%"))
    if verdict and verdict in ("safe", "suspicious", "scam"):
        q = q.filter(Scan.verdict == verdict)
    if threat_level and threat_level in ("LOW", "MED", "HIGH"):
        q = q.filter(Scan.threat_level == threat_level)
    rows = q.order_by(Scan.id.desc()).offset(skip).limit(limit).all()
    return [_scan_to_dict(s) for s in rows]


@router.get("/{scan_id}")
def get_scan(scan_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    s = db.query(Scan).filter(Scan.id == scan_id).first()
    if not s:
        raise HTTPException(404, "Scan not found")
    return _scan_to_dict(s)


@router.post("/analyze-message")
def analyze_message_endpoint(body: MessageRequest, admin=Depends(get_current_admin)):
    text = validate_message(body.message)
    return analyze_message(text)


def _scan_to_response(s: Scan, breakdown=None) -> ScanResponse:
    bd = breakdown
    if bd is None and s.breakdown:
        try:
            bd = json.loads(s.breakdown)
        except Exception:
            bd = []
    intel = {}
    if s.intel_summary:
        try:
            intel = json.loads(s.intel_summary)
        except Exception:
            pass
    return ScanResponse(
        id=s.id, link=s.link, verdict=s.verdict, score=s.score,
        threat_level=s.threat_level, reason=s.reason or "",
        breakdown=bd, intel_summary=intel,
        telegram_user_id=s.telegram_user_id,
        telegram_username=s.telegram_username,
        created_at=str(s.created_at) if s.created_at else None,
    )


def _scan_to_dict(s: Scan) -> dict:
    bd = []
    if s.breakdown:
        try:
            bd = json.loads(s.breakdown)
        except Exception:
            pass
    intel = {}
    if s.intel_summary:
        try:
            intel = json.loads(s.intel_summary)
        except Exception:
            pass
    return {
        "id": s.id,
        "telegram_user_id": s.telegram_user_id,
        "telegram_username": s.telegram_username,
        "link": s.link,
        "verdict": s.verdict,
        "score": s.score,
        "threat_level": s.threat_level,
        "reason": s.reason,
        "breakdown": bd,
        "intel_summary": intel,
        "message": s.message,
        "created_at": str(s.created_at) if s.created_at else None,
    }
