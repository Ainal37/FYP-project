"""Seed default admin user on startup."""

from .database import SessionLocal
from .models import AdminUser
from .security import hash_password


def seed_admin():
    db = SessionLocal()
    try:
        existing = (
            db.query(AdminUser)
            .filter(AdminUser.email == "admin@example.com")
            .first()
        )
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
    except Exception as e:
        print(f"[SIT] Seed error: {e}")
        db.rollback()
    finally:
        db.close()
