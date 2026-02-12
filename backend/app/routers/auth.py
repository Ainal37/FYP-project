"""Auth endpoints: login + 2FA verify + current user."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminUser, UserSecurity
from ..security import (
    verify_password, create_access_token, get_current_admin,
    decode_token, verify_totp_code,
)
from ..schemas import LoginRequest, TokenResponse, AdminResponse, Verify2FARequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.email == body.email).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if 2FA is required
    sec = db.query(UserSecurity).filter(UserSecurity.user_id == admin.id).first()
    if sec and (sec.totp_enabled or sec.mfa_required) and sec.totp_secret:
        temp_token = create_access_token(
            {"sub": admin.email, "role": admin.role, "2fa_pending": True},
            expires_minutes=5,
        )
        return {"requires_2fa": True, "temp_token": temp_token}

    token = create_access_token({"sub": admin.email, "role": admin.role})
    return TokenResponse(access_token=token)


@router.post("/verify-2fa", response_model=TokenResponse)
def verify_2fa(body: Verify2FARequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.temp_token)
    except Exception:
        raise HTTPException(401, "Invalid or expired temp token")

    if not payload.get("2fa_pending"):
        raise HTTPException(400, "Not a 2FA pending token")

    email = payload.get("sub")
    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not admin:
        raise HTTPException(401, "User not found")

    sec = db.query(UserSecurity).filter(UserSecurity.user_id == admin.id).first()
    if not sec or not sec.totp_secret:
        raise HTTPException(400, "2FA not configured")

    if not verify_totp_code(sec.totp_secret, body.code):
        raise HTTPException(401, "Invalid 2FA code")

    token = create_access_token({"sub": admin.email, "role": admin.role})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AdminResponse)
def me(admin: AdminUser = Depends(get_current_admin)):
    return AdminResponse(
        id=admin.id,
        email=admin.email,
        role=admin.role,
        created_at=str(admin.created_at) if admin.created_at else None,
    )
