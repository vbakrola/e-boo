"""Server bootstrap and database initialization script."""
import sys
import os
import argparse

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import engine, Base, SessionLocal
from backend.app.main import seed_default_permission_profiles
from backend.app.models import AdminUser, EnrollmentToken
from backend.app.security import hash_password, generate_secure_token, hash_token
from datetime import datetime, timedelta, timezone


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Ubuntu Lab Manager Server")
    parser.add_argument("--admin-user", default="admin", help="Initial admin username")
    parser.add_argument("--admin-password", default="LabAdmin2026!", help="Initial admin password")
    args = parser.parse_args()

    print("1. Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("2. Seeding default permission profiles (Student, Lab Assistant, Administrator)...")
        seed_default_permission_profiles(db)

        print(f"3. Configuring initial administrator account '{args.admin_user}'...")
        existing_admin = db.query(AdminUser).filter(AdminUser.username == args.admin_user).first()
        if not existing_admin:
            admin = AdminUser(
                username=args.admin_user,
                password_hash=hash_password(args.admin_password),
                full_name="Lab Administrator",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"   Administrator account '{args.admin_user}' successfully created.")
        else:
            print(f"   Administrator '{args.admin_user}' already exists.")

        print("4. Generating initial Lab Enrollment Token for 10 PCs...")
        existing_token = db.query(EnrollmentToken).filter(EnrollmentToken.is_active.is_(True)).first()
        if not existing_token:
            raw_token = generate_secure_token(prefix="enroll_lab_", length=32)
            token_hashed = hash_token(raw_token)
            now = datetime.now(timezone.utc)
            token_obj = EnrollmentToken(
                token=raw_token,
                token_hash=token_hashed,
                label="Initial 10-PC Lab Bootstrap",
                created_by="system",
                max_uses=15,
                uses_count=0,
                expires_at=now + timedelta(days=7),
                is_active=True,
                created_at=now
            )
            db.add(token_obj)
            db.commit()
            print(f"   Enrollment Token created: {raw_token}")
            print(f"   (Valid for 15 uses over 7 days)")
        else:
            print(f"   Active Enrollment Token already available: {existing_token.token}")

        print("\nUbuntu Lab Manager Server Setup Completed Successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
