"""Seed default admin user and system settings on startup."""

from .database import SessionLocal
from .models import AdminUser, SystemSetting
from .security import hash_password


_DEFAULT_SETTINGS = {
    "system_name": "SIT Admin Panel",
    "timezone": "Asia/Kuala_Lumpur",
    "backup_schedule": "Daily 3:00 AM",
    "auto_backup": "false",
}


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

        # Seed system settings
        for key, value in _DEFAULT_SETTINGS.items():
            row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if not row:
                db.add(SystemSetting(key=key, value=value))
        db.commit()
        print("[SIT] System settings seeded.")

    except Exception as e:
        print(f"[SIT] Seed error: {e}")
        db.rollback()
    finally:
        db.close()
