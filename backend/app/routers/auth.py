"""Auth endpoints: login + current user."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminUser
from ..security import verify_password, create_access_token, get_current_admin
from ..schemas import LoginRequest, TokenResponse, AdminResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.email == body.email).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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
