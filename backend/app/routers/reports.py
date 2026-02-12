"""Report endpoints: create + list with filters."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Report
from ..security import get_current_admin
from ..schemas import ReportRequest, ReportResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse)
def create_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Protected – create a report."""
    r = Report(
        telegram_user_id=payload.telegram_user_id,
        telegram_username=payload.telegram_username,
        link=payload.link,
        report_type=payload.report_type,
        description=payload.description,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return ReportResponse(
        id=r.id,
        link=r.link,
        report_type=r.report_type,
        description=r.description,
        status=r.status,
        telegram_user_id=r.telegram_user_id,
        telegram_username=r.telegram_username,
        created_at=str(r.created_at) if r.created_at else None,
    )


@router.get("")
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Protected – list reports with optional status filter."""
    q = db.query(Report)
    if status:
        q = q.filter(Report.status == status)
    rows = q.order_by(Report.id.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "telegram_user_id": r.telegram_user_id,
            "telegram_username": r.telegram_username,
            "link": r.link,
            "report_type": r.report_type,
            "description": r.description,
            "status": r.status,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]
