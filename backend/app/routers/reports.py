from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Report
from ..auth import get_current_admin

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportIn(BaseModel):
    telegram_user_id: int
    telegram_username: str | None = None
    message: str
    link: str | None = None


@router.post("")
def create_report(payload: ReportIn, db: Session = Depends(get_db)):
    """Public endpoint – used by the Telegram bot."""
    r = Report(**payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "status": r.status}


@router.get("")
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Protected – list all reports for admin dashboard."""
    rows = db.query(Report).order_by(Report.id.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "telegram_user_id": r.telegram_user_id,
            "telegram_username": r.telegram_username,
            "message": r.message,
            "link": r.link,
            "status": r.status,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]
