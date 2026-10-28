"""Tests for Permission Profiles and role-based policies."""
from backend.app.models import PermissionProfile


def test_default_profiles_seeded(client, auth_headers, db):
    """Ensure default profiles (Student, Lab Assistant, Administrator) are properly initialized."""
    res = client.get("/api/v1/profiles", headers=auth_headers)
    assert res.status_code == 200
    profiles = {p["name"]: p for p in res.json()}

    assert "Student" in profiles
    assert "Lab Assistant" in profiles
    assert "Administrator" in profiles

    student = profiles["Student"]
    assert student["sudo_policy"] == "none"
    assert student["shell"] == "/bin/bash"
    assert student["create_home"] is True
    assert student["is_system"] is True

    lab_asst = profiles["Lab Assistant"]
    assert lab_asst["sudo_policy"] == "none"

    admin_prof = profiles["Administrator"]
    assert admin_prof["sudo_policy"] == "restricted"


def test_cannot_delete_system_profile(client, auth_headers, db):
    """Ensure built-in system profiles cannot be deleted."""
    student_profile = db.query(PermissionProfile).filter(PermissionProfile.name == "Student").first()
    assert student_profile is not None

    res = client.delete(f"/api/v1/profiles/{student_profile.id}", headers=auth_headers)
    assert res.status_code == 400
    assert "cannot be deleted" in res.json()["detail"]


def test_create_and_delete_custom_profile(client, auth_headers):
    """Test creating and deleting a custom permission profile."""
    create_res = client.post("/api/v1/profiles", headers=auth_headers, json={
        "name": "Guest Researcher",
        "description": "Temporary profile for guest research visits",
        "shell": "/bin/bash",
        "create_home": True,
        "primary_group": "researchers",
        "supplementary_groups": "dialout",
        "sudo_policy": "none"
    })
    assert create_res.status_code == 201
    profile_id = create_res.json()["id"]

    # Delete custom profile
    del_res = client.delete(f"/api/v1/profiles/{profile_id}", headers=auth_headers)
    assert del_res.status_code == 200
