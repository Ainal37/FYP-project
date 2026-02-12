"""Backup management endpoints (enterprise)."""

import json
import time
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Backup, AuditLog
from ..rbac import require_role
from ..schemas import BackupRunRequest, BackupResponse

router = APIRouter(prefix="/backup", tags=["backup"])


@router.post("/run", response_model=BackupResponse)
def run_backup(
    body: BackupRunRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    b = Backup(
        created_by_email=admin.email,
        scope_json=json.dumps(body.scopes),
        status="done",
        file_path=f"backups/backup_{int(time.time())}.json",
    )
    db.add(b)
    db.add(AuditLog(actor_email=admin.email, action="RUN_BACKUP", detail=json.dumps(body.scopes)))
    db.commit()
    db.refresh(b)
    return _to_resp(b)


@router.get("")
def list_backups(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    rows = db.query(Backup).order_by(Backup.id.desc()).offset(skip).limit(limit).all()
    return [_to_resp(b) for b in rows]


def _to_resp(b: Backup) -> BackupResponse:
    return BackupResponse(
        id=b.id,
        created_by_email=b.created_by_email,
        scope_json=b.scope_json,
        status=b.status,
        file_path=b.file_path,
        created_at=str(b.created_at) if b.created_at else None,
        finished_at=str(b.finished_at) if b.finished_at else None,
    )
