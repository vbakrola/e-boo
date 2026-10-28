"""Seed 10 realistic Ubuntu workstations and sample managed accounts for testing."""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import SessionLocal, Base, engine
from backend.app.main import seed_default_permission_profiles
from backend.app.models import Device, ManagedUser, AdminUser
from backend.app.security import hash_token, hash_password


def seed_demo_lab():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        seed_default_permission_profiles(db)

        # 1. Ensure admin account exists
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin:
            admin = AdminUser(
                username="admin",
                password_hash=hash_password("AdminPass2026!"),
                full_name="Lab Administrator",
                is_active=True
            )
            db.add(admin)
            db.commit()

        # 2. Seed 10 Ubuntu PCs
        pcs_data = [
            ("LAB-PC-01", "192.168.1.101", "student101", "Student", "online"),
            ("LAB-PC-02", "192.168.1.102", "student102", "Student", "online"),
            ("LAB-PC-03", "192.168.1.103", "student103", "Student", "online"),
            ("LAB-PC-04", "192.168.1.104", "student104", "Student", "online"),
            ("LAB-PC-05", "192.168.1.105", "student105", "Student", "online"),
            ("LAB-PC-06", "192.168.1.106", "student106", "Student", "online"),
            ("LAB-PC-07", "192.168.1.107", "student107", "Student", "online"),
            ("LAB-PC-08", "192.168.1.108", "student108", "Student", "online"),
            ("LAB-PC-09", "192.168.1.109", "student109", "Student", "online"),
            ("LAB-PC-10", "192.168.1.110", "labassistant1", "Lab Assistant", "online"),
        ]

        now = datetime.now(timezone.utc)

        for hostname, ip, username, role, status in pcs_data:
            dev = db.query(Device).filter(Device.hostname == hostname).first()
            if not dev:
                raw_token = f"dev_tok_{hostname.lower()}_secret_key"
                dev = Device(
                    hostname=hostname,
                    ip_address=ip,
                    os_version="Ubuntu 22.04.4 LTS",
                    kernel_version="5.15.0-101-generic",
                    agent_version="1.0.0",
                    status=status,
                    is_approved=True,
                    device_token_hash=hash_token(raw_token),
                    last_heartbeat_at=now,
                    enrolled_at=now
                )
                db.add(dev)
                db.commit()
                db.refresh(dev)

            # Ensure managed user
            u = db.query(ManagedUser).filter(
                ManagedUser.device_id == dev.id,
                ManagedUser.username == username
            ).first()

            if not u:
                u = ManagedUser(
                    device_id=dev.id,
                    username=username,
                    profile_name=role,
                    is_locked=False,
                    status="ACTIVE",
                    last_provisioned_at=now
                )
                db.add(u)
                db.commit()

        print("10 Ubuntu workstations and accounts successfully seeded into database!")
        print("Login credentials: admin / AdminPass2026!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_lab()
