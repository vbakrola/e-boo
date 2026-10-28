"""Pytest configuration and test database fixtures."""
import os
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-min-32-chars-long"
os.environ["DATABASE_URL"] = "sqlite:///./test_lab.db"

from backend.app.database import Base, get_db
from backend.app.main import app, seed_default_permission_profiles
from backend.app.models import AdminUser, Device, EnrollmentToken, PermissionProfile
from backend.app.security import hash_password, hash_token, generate_secure_token

# Test database engine
TEST_DB_URL = "sqlite:///./test_lab.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test tables and seed defaults."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_default_permission_profiles(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_lab.db"):
        try:
            os.remove("./test_lab.db")
        except Exception:
            pass


@pytest.fixture
def db():
    """Provide a clean database session per test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """Provide TestClient with database dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    """Seed or return active admin user."""
    admin = db.query(AdminUser).filter(AdminUser.username == "testadmin").first()
    if not admin:
        admin = AdminUser(
            username="testadmin",
            password_hash=hash_password("AdminSecurePass2026!"),
            full_name="Test Administrator",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(client, admin_user):
    """Return Authorization Bearer header for test admin."""
    res = client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "AdminSecurePass2026!"
    })
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enrollment_token(db):
    """Create a valid enrollment token."""
    raw = generate_secure_token(prefix="enroll_test_")
    token_obj = EnrollmentToken(
        token=raw,
        token_hash=hash_token(raw),
        label="Test Enrollment",
        created_by="testadmin",
        max_uses=10,
        uses_count=0,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        is_active=True
    )
    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)
    return raw


@pytest.fixture
def sample_devices(db):
    """Create 3 registered test devices: LAB-PC-01, LAB-PC-02, LAB-PC-03."""
    devices = []
    for i in range(1, 4):
        hostname = f"LAB-PC-0{i}"
        d = db.query(Device).filter(Device.hostname == hostname).first()
        if not d:
            raw_token = f"dev_tok_sample_{i}"
            d = Device(
                hostname=hostname,
                ip_address=f"192.168.1.10{i}",
                os_version="Ubuntu 22.04 LTS",
                agent_version="1.0.0",
                status="online",
                is_approved=True,
                device_token_hash=hash_token(raw_token),
                last_heartbeat_at=datetime.now(timezone.utc),
                enrolled_at=datetime.now(timezone.utc)
            )
            db.add(d)
            db.commit()
            db.refresh(d)
        devices.append(d)
    return devices
