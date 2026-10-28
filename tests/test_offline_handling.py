"""Tests for Offline Device handling: verifying offline devices do not block others."""
from backend.app.models import Device, ProvisioningTask
from backend.app.worker import process_batch_statuses


def test_offline_device_does_not_block_online_devices(client, auth_headers, enrollment_token, db):
    """
    Test scenario: 2 devices in batch.
    - PC-01 is online and executes task.
    - PC-02 is offline and does not poll.
    Verify: PC-01 task SUCCEEDS immediately; PC-02 task remains QUEUED without blocking.
    """
    # 1. Enroll PC-01 (online)
    res1 = client.post("/api/v1/agent/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "LAB-PC-ONLINE",
        "ip_address": "192.168.1.10"
    })
    token1 = res1.json()["device_token"]

    # 2. Enroll PC-02 (offline)
    res2 = client.post("/api/v1/agent/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "LAB-PC-OFFLINE",
        "ip_address": "192.168.1.11"
    })
    token2 = res2.json()["device_token"]
    dev2_id = res2.json()["device_id"]

    # Mark PC-02 as offline
    pc2 = db.query(Device).filter(Device.id == dev2_id).first()
    pc2.status = "offline"
    db.commit()

    # 3. Create batch for both PCs
    batch_res = client.post("/api/v1/provisioning/bulk", headers=auth_headers, json={
        "batch_name": "Mixed-Status-Batch",
        "items": [
            {
                "hostname": "LAB-PC-ONLINE",
                "username": "student_online",
                "initial_password": "OnlinePass123#",
                "role": "Student",
                "force_password_change": True
            },
            {
                "hostname": "LAB-PC-OFFLINE",
                "username": "student_offline",
                "initial_password": "OfflinePass123#",
                "role": "Student",
                "force_password_change": True
            }
        ]
    })
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]
    tasks = batch_res.json()["tasks"]
    task_online = next(t for t in tasks if t["device_hostname"] == "LAB-PC-ONLINE")
    task_offline = next(t for t in tasks if t["device_hostname"] == "LAB-PC-OFFLINE")

    # 4. Online PC polls and executes its task
    poll_res = client.get("/api/v1/agent/tasks/poll", headers={"X-Device-Token": token1})
    assert poll_res.status_code == 200
    assert poll_res.json()["task"]["task_id"] == task_online["id"]

    # Report online success
    client.post(
        "/api/v1/agent/tasks/report",
        headers={"X-Device-Token": token1},
        json={"task_id": task_online["id"], "status": "SUCCEEDED"}
    )

    # 5. Verify database states:
    t_online_db = db.query(ProvisioningTask).filter(ProvisioningTask.id == task_online["id"]).first()
    t_offline_db = db.query(ProvisioningTask).filter(ProvisioningTask.id == task_offline["id"]).first()

    assert t_online_db.status == "SUCCEEDED"
    assert t_offline_db.status == "QUEUED"  # Ready to be executed once PC comes online!

    # 6. When the offline PC eventually boots up and connects, it executes its queued task
    pc2.status = "online"
    db.commit()

    poll2_res = client.get("/api/v1/agent/tasks/poll", headers={"X-Device-Token": token2})
    assert poll2_res.status_code == 200
    assert poll2_res.json()["task"]["task_id"] == task_offline["id"]

    # Report completion
    client.post(
        "/api/v1/agent/tasks/report",
        headers={"X-Device-Token": token2},
        json={"task_id": task_offline["id"], "status": "SUCCEEDED"}
    )

    process_batch_statuses(db)
    batch_detail = client.get(f"/api/v1/provisioning/batches/{batch_id}", headers=auth_headers).json()
    assert batch_detail["status"] == "COMPLETED"
    assert batch_detail["succeeded_tasks"] == 2
