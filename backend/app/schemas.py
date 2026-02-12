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


# ── Enterprise: Users ──
class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=255)
    role: str = "viewer"
    status: str = "active"
    password: Optional[str] = Field(None, min_length=6, max_length=128)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    status: str
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


# ── Enterprise: Notifications ──
class NotificationCreate(BaseModel):
    recipient_scope: str = "all"
    recipient_user_id: Optional[int] = None
    type: str = "info"
    title: str = Field(..., max_length=255)
    body: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    recipient_scope: str
    type: str
    title: str
    body: Optional[str] = None
    is_read: bool = False
    created_at: Optional[str] = None


# ── Enterprise: Settings ──
class SettingsResponse(BaseModel):
    system_name: Optional[str] = None
    timezone: Optional[str] = None
    backup_schedule: Optional[str] = None
    auto_backup: Optional[str] = None

class SettingsUpdate(BaseModel):
    system_name: Optional[str] = None
    timezone: Optional[str] = None
    backup_schedule: Optional[str] = None
    auto_backup: Optional[str] = None


# ── Enterprise: Security ──
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)

class TwoFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str

class TwoFAConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class Verify2FARequest(BaseModel):
    temp_token: str
    code: str = Field(..., min_length=6, max_length=6)


# ── Enterprise: Backup ──
class BackupRunRequest(BaseModel):
    scopes: List[str] = Field(default_factory=lambda: ["user_data", "reports", "system_settings", "audit_logs"])

class BackupResponse(BaseModel):
    id: int
    created_by_email: Optional[str] = None
    scope_json: Optional[str] = None
    status: str
    file_path: Optional[str] = None
    created_at: Optional[str] = None
    finished_at: Optional[str] = None
