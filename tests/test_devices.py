"""Tests for Device enrollment, agent authentication, and heartbeat tracking."""
from datetime import datetime, timedelta, timezone
from backend.app.models import Device
from backend.app.worker import update_device_online_statuses


def test_device_enrollment_success(client, enrollment_token):
    """Test device registers with valid enrollment token and gets unique device token."""
    res = client.post("/api/v1/agent/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "LAB-PC-99",
        "ip_address": "192.168.1.199",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "os_version": "Ubuntu 22.04.4 LTS",
        "kernel_version": "5.15.0-101-generic",
        "agent_version": "1.0.0"
    })
    assert res.status_code == 200
    data = res.json()
    assert "device_id" in data
    assert "device_token" in data
    assert data["hostname"] == "LAB-PC-99"
    assert data["device_token"].startswith("dev_tok_")


def test_device_enrollment_invalid_token(client):
    """Test device enrollment fails with invalid token."""
    res = client.post("/api/v1/agent/enroll", json={
        "enrollment_token": "fake_invalid_token_123",
        "hostname": "LAB-PC-01",
        "ip_address": "192.168.1.101"
    })
    assert res.status_code == 401
    assert "Invalid enrollment token" in res.json()["detail"]


def test_device_heartbeat_updates_status(client, enrollment_token):
    """Test device heartbeat updates last_heartbeat_at and reports vitals."""
    # Enroll device
    enroll_res = client.post("/api/v1/agent/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "LAB-PC-88",
        "ip_address": "192.168.1.188"
    })
    dev_token = enroll_res.json()["device_token"]

    # Send heartbeat
    hb_res = client.post(
        "/api/v1/agent/heartbeat",
        headers={"X-Device-Token": dev_token},
        json={
            "ip_address": "192.168.1.188",
            "uptime_seconds": 3600,
            "cpu_percent": 12.5,
            "memory_percent": 45.0,
            "disk_percent": 30.2
        }
    )
    assert hb_res.status_code == 200
    data = hb_res.json()
    assert data["status"] == "acknowledged"
    assert "acknowledged_at" in data


def test_heartbeat_timeout_marks_device_offline(db):
    """Test that worker marks device offline if heartbeat is older than timeout."""
    # Create device with stale heartbeat
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    device = Device(
        hostname="LAB-PC-STALE",
        ip_address="192.168.1.150",
        os_version="Ubuntu 22.04 LTS",
        agent_version="1.0.0",
        status="online",
        is_approved=True,
        device_token_hash="dummy_hash_stale",
        last_heartbeat_at=stale_time,
        enrolled_at=stale_time
    )
    db.add(device)
    db.commit()

    # Run worker check
    update_device_online_statuses(db)

    db.refresh(device)
    assert device.status == "offline"


def test_list_and_update_devices(client, auth_headers, sample_devices):
    """Test listing devices and modifying device hostname/IP from admin dashboard."""
    res = client.get("/api/v1/devices", headers=auth_headers)
    assert res.status_code == 200
    devices = res.json()
    assert len(devices) >= 3

    target = sample_devices[0]
    update_res = client.patch(
        f"/api/v1/devices/{target.id}",
        headers=auth_headers,
        json={"ip_address": "192.168.1.222"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["ip_address"] == "192.168.1.222"
