"""Tests for Task lifecycle, agent polling, reporting, batch reconciliation, and retry behavior."""
from backend.app.worker import process_batch_statuses
from backend.app.models import ProvisioningTask, TaskCredentialEnvelope


def test_agent_task_poll_and_report_lifecycle(client, auth_headers, enrollment_token, db):
    """Test full cycle: bulk queue -> agent poll -> agent report -> managed user updated."""
    # 1. Enroll device
    enroll_res = client.post("/api/v1/agent/enroll", json={
        "enrollment_token": enrollment_token,
        "hostname": "LAB-PC-TASK-TEST",
        "ip_address": "192.168.1.177"
    })
    dev_token = enroll_res.json()["device_token"]
    dev_id = enroll_res.json()["device_id"]

    # 2. Queue bulk provisioning task
    batch_res = client.post("/api/v1/provisioning/bulk", headers=auth_headers, json={
        "batch_name": "Lifecycle-Test-Batch",
        "items": [{
            "hostname": "LAB-PC-TASK-TEST",
            "username": "student_cycle",
            "initial_password": "CyclePassword123#",
            "role": "Student",
            "force_password_change": True
        }]
    })
    assert batch_res.status_code == 201
    batch_id = batch_res.json()["id"]
    task_id = batch_res.json()["tasks"][0]["id"]

    # 3. Agent polls task
    poll_res = client.get("/api/v1/agent/tasks/poll", headers={"X-Device-Token": dev_token})
    assert poll_res.status_code == 200
    task_data = poll_res.json()["task"]
    assert task_data is not None
    assert task_data["task_id"] == task_id
    assert task_data["target_username"] == "student_cycle"
    assert task_data["credential_payload"]["password"] == "CyclePassword123#"

    # 4. Check that credential envelope was wiped from database upon polling
    env = db.query(TaskCredentialEnvelope).filter(TaskCredentialEnvelope.task_id == task_id).first()
    assert env is None  # Deleted immediately

    # 5. Agent reports execution success
    report_res = client.post(
        "/api/v1/agent/tasks/report",
        headers={"X-Device-Token": dev_token},
        json={
            "task_id": task_id,
            "status": "SUCCEEDED",
            "result_details": {"username": "student_cycle", "home": "/home/student_cycle"}
        }
    )
    assert report_res.status_code == 200

    # 6. Run worker batch status processing
    process_batch_statuses(db)

    # 7. Check batch status
    batch_detail = client.get(f"/api/v1/provisioning/batches/{batch_id}", headers=auth_headers).json()
    assert batch_detail["status"] == "COMPLETED"
    assert batch_detail["succeeded_tasks"] == 1


def test_task_retry_after_failure(client, auth_headers, sample_devices, db):
    """Test that a failed task can be safely retried."""
    # Queue task
    res = client.post("/api/v1/provisioning/bulk", headers=auth_headers, json={
        "batch_name": "Retry-Test-Batch",
        "items": [{
            "hostname": "LAB-PC-01",
            "username": "student_retry",
            "initial_password": "RetryPassword123#",
            "role": "Student",
            "force_password_change": True
        }]
    })
    task_id = res.json()["tasks"][0]["id"]

    # Force task to FAILED
    task = db.query(ProvisioningTask).filter(ProvisioningTask.id == task_id).first()
    task.status = "FAILED"
    task.error_message = "PC network socket dropped"
    db.commit()

    # Admin retries task
    retry_res = client.post(f"/api/v1/provisioning/tasks/{task_id}/retry", headers=auth_headers)
    assert retry_res.status_code == 200

    db.refresh(task)
    assert task.status == "QUEUED"
    assert task.error_message is None
