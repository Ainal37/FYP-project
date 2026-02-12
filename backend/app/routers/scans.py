"""Scan endpoints: create + list."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Scan
from ..detector import scan_link
from ..security import get_current_admin
from ..schemas import ScanRequest, ScanResponse

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanResponse)
def create_scan(
    payload: ScanRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Protected – create a scan (used by bot & admin dashboard)."""
    verdict, score, reason = scan_link(payload.link)

    s = Scan(
        telegram_user_id=payload.telegram_user_id,
        telegram_username=payload.telegram_username,
        link=payload.link,
        verdict=verdict,
        score=score,
        reason=reason,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return ScanResponse(
        id=s.id,
        link=s.link,
        verdict=s.verdict,
        score=s.score,
        reason=s.reason or "",
        telegram_user_id=s.telegram_user_id,
        telegram_username=s.telegram_username,
        created_at=str(s.created_at) if s.created_at else None,
    )


@router.get("")
def list_scans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Protected – list scans for admin dashboard."""
    rows = db.query(Scan).order_by(Scan.id.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": s.id,
            "telegram_user_id": s.telegram_user_id,
            "telegram_username": s.telegram_username,
            "link": s.link,
            "verdict": s.verdict,
            "score": s.score,
            "reason": s.reason,
            "created_at": str(s.created_at) if s.created_at else None,
        }
        for s in rows
    ]
