"""Backup management: run (write real JSON file), download, restore (safe/full)."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminUser, AuditLog, Backup, Report, SystemSetting
from ..rbac import require_role
from ..schemas import (
    BackupResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
    BackupRunRequest,
)

router = APIRouter(prefix="/backup", tags=["backup"])
logger = logging.getLogger("sit.backup")

# Canonical backup dir: repo/backend/backups (from backend/app/routers -> backend)
ROUTER_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROUTER_DIR.parent.parent
BACKUP_DIR = BACKEND_DIR / "backups"
BACKUP_VERSION = "1.0"


def _ensure_backups_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _resolved_path_and_exists(file_path: Optional[str]) -> Tuple[str, bool]:
    if not file_path:
        return "", False
    p = Path(file_path)
    return str(p.resolve()), p.exists()


def _to_resp(b: Backup) -> BackupResponse:
    resolved_path, file_exists = _resolved_path_and_exists(b.file_path)
    return BackupResponse(
        id=b.id,
        created_by_email=b.created_by_email,
        scope_json=b.scope_json,
        status=b.status,
        file_path=b.file_path,
        created_at=str(b.created_at) if b.created_at else None,
        finished_at=str(b.finished_at) if b.finished_at else None,
        file_exists=file_exists,
        resolved_path=resolved_path,
    )


def _gather_backup_data(db: Session, scopes: List[str], created_by_email: str) -> Dict[str, Any]:
    """Build backup payload from DB by scopes. Never include plaintext passwords."""
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "meta": {
            "created_at_utc": now,
            "created_by_email": created_by_email,
            "version": BACKUP_VERSION,
            "scopes": scopes,
        },
        "system_settings": [],
        "admin_users": [],
        "reports": [],
        "audit_logs": [],
    }

    if "system_settings" in scopes:
        rows = db.query(SystemSetting).all()
        payload["system_settings"] = [
            {"key": r.key, "value": r.value} for r in rows
        ]

    if "admin_users" in scopes:
        rows = db.query(AdminUser).all()
        for r in rows:
            payload["admin_users"].append({
                "id": r.id,
                "email": r.email,
                "role": r.role,
                "created_at": str(r.created_at) if r.created_at else None,
                "password_hash": r.password_hash,  # hashed only, never plaintext
            })

    if "reports" in scopes:
        rows = db.query(Report).all()
        for r in rows:
            payload["reports"].append({
                "id": r.id,
                "telegram_user_id": r.telegram_user_id,
                "telegram_username": r.telegram_username,
                "link": r.link,
                "report_type": r.report_type,
                "description": r.description,
                "status": r.status,
                "assignee": r.assignee,
                "notes": r.notes,
                "created_at": str(r.created_at) if r.created_at else None,
            })

    if "audit_logs" in scopes:
        rows = db.query(AuditLog).all()
        for r in rows:
            payload["audit_logs"].append({
                "id": r.id,
                "actor_email": r.actor_email,
                "action": r.action,
                "target": r.target,
                "ip_address": r.ip_address,
                "detail": r.detail,
                "user_agent": r.user_agent,
                "created_at": str(r.created_at) if r.created_at else None,
            })

    return payload


def _canonical_backup_path(file_path: Optional[str]) -> Optional[Path]:
    """Resolve backup file path: absolute stored path or backend/backups/relative."""
    if not file_path:
        return None
    p = Path(file_path)
    if p.is_absolute():
        return p
    return BACKEND_DIR / file_path


@router.post("/run", response_model=BackupResponse)
def run_backup(
    body: BackupRunRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Create backup record and write real JSON file. Normalize scopes (user_data -> admin_users)."""
    scopes = list(body.scopes) if body.scopes else ["system_settings", "admin_users", "reports", "audit_logs"]
    if "user_data" in scopes:
        scopes = [s if s != "user_data" else "admin_users" for s in scopes]

    backup_dir = _ensure_backups_dir()
    ts_utc = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{ts_utc}.json"
    file_path = BACKUP_DIR / filename

    b = Backup(
        created_by_email=admin.email,
        scope_json=json.dumps(scopes),
        status="queued",
        file_path=None,
    )
    db.add(b)
    db.add(AuditLog(actor_email=admin.email, action="RUN_BACKUP", detail=json.dumps(scopes)))
    db.commit()
    db.refresh(b)

    try:
        data = _gather_backup_data(db, scopes, admin.email)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
        if not file_path.exists():
            b.status = "failed"
            b.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(500, "Backup file write did not create file on disk")
        resolved = str(file_path.resolve())
        b.file_path = resolved
        b.status = "done"
        b.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(b)
        logger.info("Backup created: dir=%s file=%s", str(backup_dir.resolve()), resolved)
    except HTTPException:
        raise
    except Exception as e:
        b.status = "failed"
        b.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(500, f"Backup write failed: {e}")

    # Update last_backup_at
    try:
        now = datetime.now(timezone.utc).isoformat()
        row = db.query(SystemSetting).filter(SystemSetting.key == "last_backup_at").first()
        if row:
            row.value = now
        else:
            db.add(SystemSetting(key="last_backup_at", value=now))
        db.commit()
    except Exception:
        db.rollback()

    resp = _to_resp(b)
    resp.file_exists = file_path.exists()
    resp.resolved_path = str(file_path.resolve())
    return resp


@router.get("")
def list_backups(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    rows = db.query(Backup).order_by(Backup.id.desc()).offset(skip).limit(limit).all()
    return [_to_resp(r) for r in rows]


@router.get("/download/{backup_id}")
def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Stream backup file as attachment. 404 if file missing."""
    b = db.query(Backup).filter(Backup.id == backup_id).first()
    if not b:
        raise HTTPException(404, "Backup not found")
    if not b.file_path:
        raise HTTPException(404, "Backup has no file (legacy or failed run)")
    full_path = _canonical_backup_path(b.file_path)
    if not full_path or not full_path.is_file():
        raise HTTPException(404, "Backup file not found on disk. It may have been deleted.")
    return FileResponse(
        full_path,
        media_type="application/json",
        filename=full_path.name,
    )


def _validate_backup_schema(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Invalid backup: root must be object")
    if "meta" not in data or not isinstance(data["meta"], dict):
        raise ValueError("Invalid backup: missing or invalid meta")
    if "system_settings" not in data:
        raise ValueError("Invalid backup: missing system_settings key")


@router.post("/restore/{backup_id}", response_model=BackupRestoreResponse)
def restore_backup(
    backup_id: int,
    body: BackupRestoreRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Restore from backup file. SAFE = system_settings only. FULL = settings + admin_users + reports + audit_logs."""
    b = db.query(Backup).filter(Backup.id == backup_id).first()
    if not b or not b.file_path:
        raise HTTPException(404, "Backup not found or has no file")
    full_path = _canonical_backup_path(b.file_path)
    if not full_path or not full_path.is_file():
        raise HTTPException(404, "Backup file not found on disk")

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(400, f"Invalid backup file: {e}")

    try:
        _validate_backup_schema(data)
    except ValueError as e:
        raise HTTPException(400, str(e))

    mode = (body.mode or "safe").lower()
    if mode not in ("safe", "full"):
        raise HTTPException(400, "mode must be 'safe' or 'full'")

    restored = {"system_settings": 0, "admin_users": 0, "reports": 0, "audit_logs": 0}

    try:
        # SAFE: system_settings only (upsert by key)
        settings_list = data.get("system_settings") or []
        for item in settings_list:
            if not isinstance(item, dict) or "key" not in item:
                continue
            key = item.get("key")
            value = item.get("value")
            row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if row:
                row.value = value
            else:
                db.add(SystemSetting(key=key, value=value))
            restored["system_settings"] += 1

        if mode == "full":
            # admin_users: upsert by email; do not overwrite password_hash with plaintext
            for item in data.get("admin_users") or []:
                if not isinstance(item, dict) or "email" not in item:
                    continue
                email = item.get("email")
                existing = db.query(AdminUser).filter(AdminUser.email == email).first()
                if existing:
                    existing.role = item.get("role", existing.role)
                    if item.get("password_hash") and len(str(item["password_hash"])) == 60:
                        existing.password_hash = item["password_hash"]
                else:
                    pw = item.get("password_hash")
                    if not pw or len(str(pw)) != 60:
                        continue  # need a hash to create
                    db.add(AdminUser(
                        email=email,
                        role=item.get("role", "admin"),
                        password_hash=pw,
                    ))
                restored["admin_users"] += 1

            # reports: upsert by id; if id exists update, else insert (avoid collision by using max id)
            existing_ids = {r.id for r in db.query(Report.id).all()}
            for item in data.get("reports") or []:
                if not isinstance(item, dict):
                    continue
                rid = item.get("id")
                if rid is not None and rid in existing_ids:
                    r = db.query(Report).filter(Report.id == rid).first()
                    if r:
                        r.telegram_user_id = item.get("telegram_user_id")
                        r.telegram_username = item.get("telegram_username")
                        r.link = item.get("link")
                        r.report_type = item.get("report_type", "scam")
                        r.description = item.get("description", "")
                        r.status = item.get("status", "new")
                        r.assignee = item.get("assignee")
                        r.notes = item.get("notes")
                else:
                    db.add(Report(
                        telegram_user_id=item.get("telegram_user_id"),
                        telegram_username=item.get("telegram_username"),
                        link=item.get("link"),
                        report_type=item.get("report_type", "scam"),
                        description=item.get("description", ""),
                        status=item.get("status", "new"),
                        assignee=item.get("assignee"),
                        notes=item.get("notes"),
                    ))
                restored["reports"] += 1

            # audit_logs: append only; insert with new id (do not overwrite)
            for item in data.get("audit_logs") or []:
                if not isinstance(item, dict) or "action" not in item:
                    continue
                db.add(AuditLog(
                    actor_email=item.get("actor_email"),
                    action=item.get("action", ""),
                    target=item.get("target"),
                    ip_address=item.get("ip_address"),
                    detail=item.get("detail"),
                    user_agent=item.get("user_agent"),
                ))
                restored["audit_logs"] += 1

        action = "BACKUP_RESTORED_SAFE" if mode == "safe" else "BACKUP_RESTORED_FULL"
        db.add(AuditLog(
            actor_email=admin.email,
            action=action,
            detail=json.dumps({"backup_id": backup_id, "mode": mode, "restored": restored}),
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Restore failed: {e}")

    return BackupRestoreResponse(ok=True, mode=mode, restored_counts=restored)
