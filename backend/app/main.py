"""SIT Backend – FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .seed import seed_admin
from .routers import auth, scans, reports, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: auto-migrate schema if outdated, create tables, seed admin."""
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(engine)

    # Auto-detect schema changes – if 'reports' table lacks new columns, rebuild
    if inspector.has_table("reports"):
        cols = {c["name"] for c in inspector.get_columns("reports")}
        if "description" not in cols or "report_type" not in cols:
            print("[SIT] Schema outdated – rebuilding tables...")
            Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(title="SIT Backend API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(dashboard.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "SIT Backend API is running"}
