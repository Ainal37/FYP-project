"""SIT Backend – FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .seed import seed_admin
from .middleware import RateLimitMiddleware, AuditLogMiddleware
from .routers import auth, scans, reports, dashboard, evaluation

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)-18s  %(levelname)-5s  %(message)s")
logger = logging.getLogger("sit")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: auto-migrate schema if outdated, create tables, seed admin."""
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

    if needs_rebuild:
        logger.info("[SIT] Schema outdated – rebuilding tables…")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    seed_admin()
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


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "2.0.0", "service": "SIT Backend API"}
