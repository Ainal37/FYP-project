"""Notification endpoints (enterprise)."""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Notification, AuditLog
from ..security import get_current_admin
from ..rbac import require_role
from ..schemas import NotificationCreate, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationResponse)
def create_notification(
    body: NotificationCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    n = Notification(
        recipient_scope=body.recipient_scope,
        recipient_user_id=body.recipient_user_id,
        type=body.type,
        title=body.title,
        body=body.body,
    )
    db.add(n)
    db.add(AuditLog(actor_email=admin.email, action="CREATE_NOTIFICATION", target=body.title))
    db.commit()
    db.refresh(n)
    return _to_resp(n)


@router.get("")
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    q = db.query(Notification)
    # Scope: show notifications targeted at "all" or matching the admin's role
    from sqlalchemy import or_
    q = q.filter(or_(
        Notification.recipient_scope == "all",
        Notification.recipient_scope == admin.role,
    ))
    if unread_only:
        q = q.filter(Notification.is_read == False)
    rows = q.order_by(Notification.id.desc()).offset(skip).limit(limit).all()
    return [_to_resp(n) for n in rows]


@router.post("/mark-read")
def mark_notifications_read(
    ids: List[int] = [],
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    if ids:
        db.query(Notification).filter(Notification.id.in_(ids)).update(
            {Notification.is_read: True}, synchronize_session=False
        )
    else:
        # Mark all as read
        from sqlalchemy import or_
        db.query(Notification).filter(
            or_(Notification.recipient_scope == "all", Notification.recipient_scope == admin.role),
            Notification.is_read == False,
        ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"ok": True}


def _to_resp(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id, recipient_scope=n.recipient_scope, type=n.type,
        title=n.title, body=n.body, is_read=n.is_read,
        created_at=str(n.created_at) if n.created_at else None,
    )
