"""System settings endpoints (enterprise)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SystemSetting, AuditLog
from ..security import get_current_admin
from ..rbac import require_role
from ..schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

_ALLOWED_KEYS = {"system_name", "timezone", "backup_schedule", "auto_backup"}


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(_ALLOWED_KEYS)).all()
    kv = {r.key: r.value for r in rows}
    return SettingsResponse(**kv)


@router.patch("", response_model=SettingsResponse)
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")

    for key, value in updates.items():
        if key not in _ALLOWED_KEYS:
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(SystemSetting(key=key, value=str(value)))

    db.add(AuditLog(
        actor_email=admin.email,
        action="UPDATE_SETTINGS",
        detail=str(updates),
    ))
    db.commit()

    # Return current state
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(_ALLOWED_KEYS)).all()
    kv = {r.key: r.value for r in rows}
    return SettingsResponse(**kv)
