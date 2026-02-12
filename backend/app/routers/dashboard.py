from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Scan, Report

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Public stats endpoint (also used on admin dashboard)."""
    total_scans = db.query(func.count(Scan.id)).scalar() or 0
    total_reports = db.query(func.count(Report.id)).scalar() or 0

    scam = (
        db.query(func.count(Scan.id)).filter(Scan.verdict == "scam").scalar() or 0
    )
    suspicious = (
        db.query(func.count(Scan.id))
        .filter(Scan.verdict == "suspicious")
        .scalar()
        or 0
    )
    safe = (
        db.query(func.count(Scan.id)).filter(Scan.verdict == "safe").scalar() or 0
    )

    latest = db.query(Scan).order_by(Scan.id.desc()).limit(10).all()

    return {
        "total_scans": total_scans,
        "total_reports": total_reports,
        "breakdown": {"scam": scam, "suspicious": suspicious, "safe": safe},
        "latest_scans": [
            {
                "id": s.id,
                "link": s.link,
                "verdict": s.verdict,
                "score": s.score,
                "created_at": str(s.created_at) if s.created_at else None,
            }
            for s in latest
        ],
    }
