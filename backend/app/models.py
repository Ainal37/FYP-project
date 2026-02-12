"""SQLAlchemy ORM models."""

from sqlalchemy import Column, Integer, String, Text, BigInteger, Enum, TIMESTAMP
from sqlalchemy.sql import func
from .database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")
    created_at = Column(TIMESTAMP, server_default=func.now())


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, nullable=True)
    telegram_username = Column(String(80), nullable=True)
    link = Column(Text, nullable=False)
    verdict = Column(Enum("safe", "suspicious", "scam"), nullable=False)
    score = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, nullable=True)
    telegram_username = Column(String(80), nullable=True)
    link = Column(Text, nullable=True)
    report_type = Column(String(50), nullable=False, default="scam")
    description = Column(Text, nullable=False)
    status = Column(
        Enum("new", "investigating", "resolved"),
        nullable=False,
        default="new",
    )
    created_at = Column(TIMESTAMP, server_default=func.now())
