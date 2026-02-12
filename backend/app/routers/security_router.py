"""Security endpoints: change password, 2FA setup/confirm (enterprise)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminUser, UserSecurity, AuditLog
from ..security import (
    get_current_admin, verify_password, hash_password,
    generate_totp_secret, get_totp_uri, verify_totp_code,
)
from ..schemas import (
    ChangePasswordRequest, TwoFASetupResponse, TwoFAConfirmRequest,
)

router = APIRouter(prefix="/security", tags=["security"])


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    if not verify_password(body.current_password, admin.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    admin.password_hash = hash_password(body.new_password)
    db.add(AuditLog(actor_email=admin.email, action="CHANGE_PASSWORD"))
    db.commit()
    return {"ok": True, "message": "Password changed successfully"}


@router.post("/2fa/setup", response_model=TwoFASetupResponse)
def setup_2fa(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    sec = db.query(UserSecurity).filter(UserSecurity.user_id == admin.id).first()
    if sec and sec.totp_enabled:
        raise HTTPException(400, "2FA is already enabled")

    secret = generate_totp_secret()
    uri = get_totp_uri(secret, admin.email)

    if not sec:
        sec = UserSecurity(user_id=admin.id)
        db.add(sec)
    sec.totp_secret = secret
    sec.totp_enabled = False  # Not yet confirmed
    db.commit()

    return TwoFASetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/2fa/confirm")
def confirm_2fa(
    body: TwoFAConfirmRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    sec = db.query(UserSecurity).filter(UserSecurity.user_id == admin.id).first()
    if not sec or not sec.totp_secret:
        raise HTTPException(400, "2FA setup not started. Call POST /security/2fa/setup first.")

    if not verify_totp_code(sec.totp_secret, body.code):
        raise HTTPException(400, "Invalid TOTP code. Please try again.")

    sec.totp_enabled = True
    db.add(AuditLog(actor_email=admin.email, action="ENABLE_2FA"))
    db.commit()
    return {"ok": True, "message": "2FA enabled successfully"}


@router.post("/2fa/disable")
def disable_2fa(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    sec = db.query(UserSecurity).filter(UserSecurity.user_id == admin.id).first()
    if not sec or not sec.totp_enabled:
        raise HTTPException(400, "2FA is not enabled")
    sec.totp_enabled = False
    sec.totp_secret = None
    db.add(AuditLog(actor_email=admin.email, action="DISABLE_2FA"))
    db.commit()
    return {"ok": True, "message": "2FA disabled"}


@router.get("/2fa/status")
def get_2fa_status(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    sec = db.query(UserSecurity).filter(UserSecurity.user_id == admin.id).first()
    return {
        "totp_enabled": sec.totp_enabled if sec else False,
        "mfa_required": sec.mfa_required if sec else False,
        "session_timeout_minutes": sec.session_timeout_minutes if sec else 480,
    }
