"""SIT Backend – FastAPI application entry point."""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import Base, engine, SessionLocal
from .seed import seed_admin
from .middleware import RateLimitMiddleware, AuditLogMiddleware
from .routers import (
    auth, scans, reports, dashboard, evaluation,
    users_router, notifications_router, settings_router,
    security_router, backup_router, audit_router, analytics_router,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)-18s  %(levelname)-5s  %(message)s")
logger = logging.getLogger("sit")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: auto-migrate schema if outdated, create tables, seed admin.

    Wrapped in try/except so the app starts even if MySQL is down.
    /health will report db=false until the database becomes available.
    """
    try:
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(engine)
        needs_rebuild = False

        if inspector.has_table("scans"):
            cols = {c["name"] for c in inspector.get_columns("scans")}
            if "threat_level" not in cols or "breakdown" not in cols:
                needs_rebuild = True

        if inspector.has_table("reports"):
            cols = {c["name"] for c in inspector.get_columns("reports")}
            if "description" not in cols or "assignee" not in cols:
                needs_rebuild = True

        # Check new enterprise tables
        for tbl in ("users", "user_security", "notifications", "backups", "system_settings"):
            if not inspector.has_table(tbl):
                needs_rebuild = True

        if inspector.has_table("audit_logs"):
            cols = {c["name"] for c in inspector.get_columns("audit_logs")}
            if "user_agent" not in cols:
                needs_rebuild = True

        if needs_rebuild:
            logger.info("[SIT] Schema outdated – rebuilding tables…")
            Base.metadata.drop_all(bind=engine)

        Base.metadata.create_all(bind=engine)
        seed_admin()
        logger.info("[SIT] Database ready.")
    except Exception as exc:
        logger.error("[SIT] Database unavailable at startup: %s", exc)
        logger.warning("[SIT] App will start anyway. /health will report db=false.")

    yield


app = FastAPI(
    title="SIT Backend API",
    description="Scammer Identification & Validation Tool – Enterprise MVP",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Middleware (order matters: first added = outermost) ──
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware, global_limit=120, window=60)

# ── Routers ──
app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(dashboard.router)
app.include_router(evaluation.router)
app.include_router(users_router.router)
app.include_router(notifications_router.router)
app.include_router(settings_router.router)
app.include_router(security_router.router)
app.include_router(backup_router.router)
app.include_router(audit_router.router)
app.include_router(analytics_router.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "2.0.0", "service": "SIT Backend API"}


@app.get("/health", tags=["health"])
def health_check():
    """Unauthenticated health probe – used by frontend, run_all.ps1, and bot.

    Designed to respond in <50ms even if the database is down.
    Uses the connection pool with pool_pre_ping so dead connections are recycled.
    Wrapped in a tight try/except so it never crashes.
    """
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_ok = True
        db.close()
    except Exception:
        try:
            db.close()
        except Exception:
            pass

    intel_configured = bool(os.getenv("VIRUSTOTAL_API_KEY", "").strip())

    return {
        "ok": True,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": "2.0.0",
        "db": db_ok,
        "intel": intel_configured,
    }
