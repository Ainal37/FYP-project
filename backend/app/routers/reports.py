"""Report endpoints: create + list + detail + PATCH workflow."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models import Report
from ..security import get_current_admin
from ..schemas import ReportRequest, ReportResponse, ReportUpdate

router = APIRouter(prefix="/reports", tags=["reports"])

VALID_STATUSES = {"new", "investigating", "resolved"}


@router.post("", response_model=ReportResponse)
def create_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
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
    return _to_resp(r)


@router.get("")
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status: new/investigating/resolved"),
    search: Optional[str] = Query(None, description="Search by link or description"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(Report)
    if status and status in VALID_STATUSES:
        q = q.filter(Report.status == status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(or_(
            Report.link.ilike(pattern),
            Report.description.ilike(pattern),
        ))
    rows = q.order_by(Report.id.desc()).offset(skip).limit(limit).all()
    return [_to_dict(r) for r in rows]


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "Report not found")
    return _to_dict(r)


@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    body: ReportUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(404, "Report not found")
    if body.status is not None:
        if body.status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")
        r.status = body.status
    if body.assignee is not None:
        r.assignee = body.assignee
    if body.notes is not None:
        r.notes = body.notes
    db.commit()
    db.refresh(r)
    return _to_resp(r)


def _to_resp(r: Report) -> ReportResponse:
    return ReportResponse(
        id=r.id, link=r.link, report_type=r.report_type,
        description=r.description, status=r.status,
        assignee=r.assignee, notes=r.notes,
        telegram_user_id=r.telegram_user_id,
        telegram_username=r.telegram_username,
        created_at=str(r.created_at) if r.created_at else None,
    )


def _to_dict(r: Report) -> dict:
    return {
        "id": r.id, "telegram_user_id": r.telegram_user_id,
        "telegram_username": r.telegram_username, "link": r.link,
        "report_type": r.report_type, "description": r.description,
        "status": r.status, "assignee": r.assignee, "notes": r.notes,
        "created_at": str(r.created_at) if r.created_at else None,
    }
