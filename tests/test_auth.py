"""Tests for Admin authentication, password hashing with Argon2id, and session handling."""
import pytest
from backend.app.security import verify_password, hash_password


def test_argon2id_hashing():
    """Verify that password hashing uses Argon2id and correctly verifies."""
    raw = "MySuperSecretPassword#2026"
    hashed = hash_password(raw)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_admin_login_success(client, admin_user):
    """Test successful admin login generates valid JWT token."""
    res = client.post("/api/v1/auth/login", json={
        "username": admin_user.username,
        "password": "AdminSecurePass2026!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["admin_user"]["username"] == admin_user.username


def test_admin_login_wrong_password(client, admin_user):
    """Test login rejection on incorrect password."""
    res = client.post("/api/v1/auth/login", json={
        "username": admin_user.username,
        "password": "IncorrectPassword123"
    })
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json()["detail"]


def test_get_me_endpoint(client, auth_headers, admin_user):
    """Test fetching authenticated admin user profile."""
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == admin_user.username
    assert data["full_name"] == admin_user.full_name


def test_unauthenticated_request_rejected(client):
    """Ensure protected routes require authorization."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_change_password(client, auth_headers, db, admin_user):
    """Test changing admin password securely."""
    res = client.post("/api/v1/auth/change-password", headers=auth_headers, json={
        "old_password": "AdminSecurePass2026!",
        "new_password": "NewAdminPass2026!#"
    })
    assert res.status_code == 200

    # Try logging in with the old password (should fail)
    fail_res = client.post("/api/v1/auth/login", json={
        "username": admin_user.username,
        "password": "AdminSecurePass2026!"
    })
    assert fail_res.status_code == 401

    # Log in with the new password (should succeed)
    succ_res = client.post("/api/v1/auth/login", json={
        "username": admin_user.username,
        "password": "NewAdminPass2026!#"
    })
    assert succ_res.status_code == 200

    # Reset back for other tests
    client.post("/api/v1/auth/change-password", headers={"Authorization": f"Bearer {succ_res.json()['access_token']}"}, json={
        "old_password": "NewAdminPass2026!#",
        "new_password": "AdminSecurePass2026!"
    })
