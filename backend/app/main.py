from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import AdminUser
from .auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_admin,
)
from .routers import scans, dashboard, reports


# ---------------------------------------------------------------------------
# Lifespan: create tables + seed default admin
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    _seed_admin()
    yield
    # Shutdown – nothing needed


def _seed_admin():
    from .database import SessionLocal

    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.email == "admin@example.com").first()
        if not existing:
            admin = AdminUser(
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("[SIT] Default admin seeded: admin@example.com / admin123")
        else:
            print("[SIT] Default admin already exists.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="SIT Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include existing routers
app.include_router(scans.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login", tags=["auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.email == body.email).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": admin.email, "role": admin.role})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", tags=["auth"])
def me(admin: AdminUser = Depends(get_current_admin)):
    return {
        "id": admin.id,
        "email": admin.email,
        "role": admin.role,
        "created_at": str(admin.created_at) if admin.created_at else None,
    }


@app.get("/")
def root():
    return {"status": "ok", "message": "SIT Backend API is running"}
