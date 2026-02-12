"""Pydantic request / response schemas."""

from pydantic import BaseModel
from typing import Optional, List


# ── Auth ──────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: Optional[str] = None


# ── Scans ─────────────────────────────────────
class ScanRequest(BaseModel):
    link: str
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None


class ScanResponse(BaseModel):
    id: int
    link: str
    verdict: str
    score: int
    reason: str
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None
    created_at: Optional[str] = None


# ── Reports ───────────────────────────────────
class ReportRequest(BaseModel):
    link: Optional[str] = None
    report_type: str = "scam"
    description: str
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    link: Optional[str] = None
    report_type: str
    description: str
    status: str
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None
    created_at: Optional[str] = None


# ── Dashboard ─────────────────────────────────
class DashboardStats(BaseModel):
    total_scans: int
    total_reports: int
    breakdown: dict
    latest_scans: List[dict]
    latest_reports: List[dict]
