"""Command-line utility to securely create or reset administrator credentials."""
import sys
import os
import argparse
import getpass

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import SessionLocal, Base, engine
from backend.app.models import AdminUser
from backend.app.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create Ubuntu Lab Manager Administrator")
    parser.add_argument("--username", help="Administrator username")
    parser.add_argument("--password", help="Administrator password (prompted if omitted)")
    parser.add_argument("--name", default="Lab Administrator", help="Full display name")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        username = args.username or input("Enter administrator username [admin]: ").strip() or "admin"
        
        # Check if username exists
        existing = db.query(AdminUser).filter(AdminUser.username == username).first()
        if existing:
            action = input(f"Admin '{username}' already exists. Reset password? [y/N]: ").strip().lower()
            if action not in ["y", "yes"]:
                print("Operation aborted.")
                return
        
        if args.password:
            password = args.password
        else:
            password = getpass.getpass("Enter administrator password (min 8 chars): ")
            confirm = getpass.getpass("Confirm administrator password: ")
            if password != confirm:
                print("Error: Passwords do not match.")
                sys.exit(1)

        if len(password) < 8:
            print("Error: Password must be at least 8 characters long.")
            sys.exit(1)

        pwd_hash = hash_password(password)

        if existing:
            existing.password_hash = pwd_hash
            existing.full_name = args.name
            existing.is_active = True
            db.commit()
            print(f"Password for administrator '{username}' updated successfully.")
        else:
            admin = AdminUser(
                username=username,
                password_hash=pwd_hash,
                full_name=args.name,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"Administrator account '{username}' created successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
