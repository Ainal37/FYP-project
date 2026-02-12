"""Pydantic request / response schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List


# ── Auth ──
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


# ── Scans ──
class ScanRequest(BaseModel):
    link: str = Field(..., max_length=2048)
    message: Optional[str] = Field(None, max_length=5000)
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None

class ScanResponse(BaseModel):
    id: int
    link: str
    verdict: str
    score: int
    threat_level: Optional[str] = None
    reason: str
    breakdown: Optional[list] = None
    intel_summary: Optional[dict] = None
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None
    created_at: Optional[str] = None


# ── NLP ──
class MessageRequest(BaseModel):
    message: str = Field(..., max_length=5000)


# ── Reports ──
class ReportRequest(BaseModel):
    link: Optional[str] = Field(None, max_length=2048)
    report_type: str = "scam"
    description: str = Field(..., max_length=5000)
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None

class ReportResponse(BaseModel):
    id: int
    link: Optional[str] = None
    report_type: str
    description: str
    status: str
    assignee: Optional[str] = None
    notes: Optional[str] = None
    telegram_user_id: Optional[int] = None
    telegram_username: Optional[str] = None
    created_at: Optional[str] = None

class ReportUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
