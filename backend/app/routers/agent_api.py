"""Agent-facing API: Device enrollment, heartbeats, task dispatch, and result reporting."""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    Device, EnrollmentToken, ProvisioningTask, TaskCredentialEnvelope, ManagedUser
)
from backend.app.schemas import (
    DeviceEnrollRequest, DeviceEnrollResponse, DeviceHeartbeatRequest,
    DeviceHeartbeatResponse, AgentTaskReportRequest
)
from backend.app.security import (
    generate_secure_token, hash_token, decrypt_credential_payload, sanitize_audit_details
)
from backend.app.auth import get_authenticated_device, record_audit

router = APIRouter(prefix="/api/v1/agent", tags=["Agent API"])


@router.post("/enroll", response_model=DeviceEnrollResponse)
def enroll_device(
    enroll_req: DeviceEnrollRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Enroll an Ubuntu PC agent into the central management server.
    Consumes an authorized enrollment token and issues a permanent high-entropy device token.
    """
    token_hashed = hash_token(enroll_req.enrollment_token.strip())
    enrollment = db.query(EnrollmentToken).filter(
        EnrollmentToken.token_hash == token_hashed,
        EnrollmentToken.is_active.is_(True)
    ).first()

    now = datetime.now(timezone.utc)
    if not enrollment:
        raise HTTPException(status_code=401, detail="Invalid enrollment token")

    # SQLite timezone normalization
    token_expiry = enrollment.expires_at
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)

    if token_expiry < now:
        enrollment.is_active = False
        db.commit()
        raise HTTPException(status_code=401, detail="Enrollment token has expired")

    if enrollment.uses_count >= enrollment.max_uses:
        enrollment.is_active = False
        db.commit()
        raise HTTPException(status_code=401, detail="Enrollment token usage limit reached")

    # Increment token uses
    enrollment.uses_count += 1
    if enrollment.uses_count >= enrollment.max_uses:
        enrollment.is_active = False

    clean_hostname = enroll_req.hostname.strip()
    raw_device_token = generate_secure_token(prefix="dev_tok_", length=36)
    dev_token_hash = hash_token(raw_device_token)

    # Check if device with this hostname exists (e.g. re-enrollment after reinstall)
    device = db.query(Device).filter(Device.hostname == clean_hostname).first()
    if not device:
        device = Device(
            hostname=clean_hostname,
            ip_address=enroll_req.ip_address.strip(),
            mac_address=enroll_req.mac_address,
            os_version=enroll_req.os_version,
            kernel_version=enroll_req.kernel_version,
            agent_version=enroll_req.agent_version,
            status="online",
            is_approved=True,
            device_token_hash=dev_token_hash,
            last_heartbeat_at=now,
            enrolled_at=now
        )
        db.add(device)
    else:
        # Re-enroll existing host
        device.ip_address = enroll_req.ip_address.strip()
        device.mac_address = enroll_req.mac_address or device.mac_address
        device.os_version = enroll_req.os_version or device.os_version
        device.kernel_version = enroll_req.kernel_version or device.kernel_version
        device.agent_version = enroll_req.agent_version or device.agent_version
        device.status = "online"
        device.device_token_hash = dev_token_hash
        device.last_heartbeat_at = now

    db.commit()
    db.refresh(device)

    record_audit(
        db, action="DEVICE_ENROLLED", entity_type="Device",
        entity_id=str(device.id), request=request,
        details={"hostname": device.hostname, "ip": device.ip_address}
    )

    return DeviceEnrollResponse(
        device_id=device.id,
        hostname=device.hostname,
        device_token=raw_device_token,
        status="approved"
    )


@router.post("/heartbeat", response_model=DeviceHeartbeatResponse)
def device_heartbeat(
    heartbeat: DeviceHeartbeatRequest,
    device: Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db)
):
    """
    Process regular agent heartbeat, update system vitals and status,
    and notify agent if pending operations exist.
    """
    now = datetime.now(timezone.utc)
    device.status = "online"
    device.last_heartbeat_at = now

    if heartbeat.ip_address:
        device.ip_address = heartbeat.ip_address
    if heartbeat.os_version:
        device.os_version = heartbeat.os_version
    if heartbeat.kernel_version:
        device.kernel_version = heartbeat.kernel_version
    if heartbeat.agent_version:
        device.agent_version = heartbeat.agent_version

    # Collect vitals into metadata_json
    vitals = {
        "uptime_seconds": heartbeat.uptime_seconds,
        "cpu_percent": heartbeat.cpu_percent,
        "memory_percent": heartbeat.memory_percent,
        "disk_percent": heartbeat.disk_percent,
        "updated_at": now.isoformat()
    }
    device.metadata_json = json.dumps(vitals)

    # Check for pending queued tasks for this device
    pending_count = db.query(ProvisioningTask).filter(
        ProvisioningTask.device_id == device.id,
        ProvisioningTask.status.in_(["QUEUED", "RETRYING"])
    ).count()

    db.commit()

    return DeviceHeartbeatResponse(
        status="acknowledged",
        pending_tasks_count=pending_count,
        acknowledged_at=now
    )


@router.get("/tasks/poll")
def poll_pending_task(
    device: Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db)
):
    """
    Poll next queued task for this device.
    Delivers ephemeral credentials and immediately wipes them from persistent storage.
    """
    task = db.query(ProvisioningTask).filter(
        ProvisioningTask.device_id == device.id,
        ProvisioningTask.status.in_(["QUEUED", "RETRYING"])
    ).order_by(ProvisioningTask.queued_at.asc()).first()

    if not task:
        return {"task": None}

    now = datetime.now(timezone.utc)
    task.status = "RUNNING"
    task.started_at = now
    task.attempts += 1

    profile_dict = None
    if task.profile:
        profile_dict = {
            "name": task.profile.name,
            "shell": task.profile.shell,
            "create_home": task.profile.create_home,
            "primary_group": task.profile.primary_group,
            "supplementary_groups": task.profile.supplementary_groups,
            "sudo_policy": task.profile.sudo_policy
        }

    # Retrieve and decrypt ephemeral credential if present
    credential_payload = None
    envelope = db.query(TaskCredentialEnvelope).filter(
        TaskCredentialEnvelope.task_id == task.id,
        TaskCredentialEnvelope.is_consumed.is_(False)
    ).first()

    if envelope:
        # SQLite timezone normalization
        env_expiry = envelope.expires_at
        if env_expiry.tzinfo is None:
            env_expiry = env_expiry.replace(tzinfo=timezone.utc)

        if env_expiry >= now:
            credential_payload = decrypt_credential_payload(
                envelope.encrypted_payload,
                envelope.nonce_hex,
                envelope.auth_tag_hex
            )
        # Wipe credential envelope immediately after delivery
        envelope.is_consumed = True
        envelope.consumed_at = now
        db.delete(envelope)

    db.commit()

    return {
        "task": {
            "task_id": task.id,
            "operation": task.operation,
            "target_username": task.target_username,
            "profile": profile_dict,
            "force_password_change": task.force_password_change,
            "expiry_date": task.expiry_date,
            "credential_payload": credential_payload
        }
    }


@router.post("/tasks/report")
def report_task_result(
    report: AgentTaskReportRequest,
    request: Request,
    device: Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db)
):
    """
    Agent reports the result of local execution.
    Updates task status and local managed user database state.
    """
    task = db.query(ProvisioningTask).filter(
        ProvisioningTask.id == report.task_id,
        ProvisioningTask.device_id == device.id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found or device mismatch")

    now = datetime.now(timezone.utc)
    task.completed_at = now

    sanitized_details = sanitize_audit_details(report.result_details or {})

    if report.status.upper() == "SUCCEEDED":
        task.status = "SUCCEEDED"
        task.error_message = None
        task.result_details_json = json.dumps(sanitized_details)

        # Update ManagedUser registry
        user_record = db.query(ManagedUser).filter(
            ManagedUser.device_id == device.id,
            ManagedUser.username == task.target_username
        ).first()

        profile_name = task.profile.name if task.profile else "Custom"

        if task.operation == "CREATE_USER":
            if not user_record:
                user_record = ManagedUser(
                    device_id=device.id,
                    username=task.target_username,
                    profile_name=profile_name,
                    is_locked=False,
                    expiry_date=task.expiry_date,
                    status="ACTIVE",
                    last_provisioned_at=now
                )
                db.add(user_record)
            else:
                user_record.profile_name = profile_name
                user_record.is_locked = False
                user_record.expiry_date = task.expiry_date
                user_record.status = "ACTIVE"
                user_record.last_provisioned_at = now

        elif task.operation == "LOCK_ACCOUNT":
            if user_record:
                user_record.is_locked = True
                user_record.status = "LOCKED"

        elif task.operation == "UNLOCK_ACCOUNT":
            if user_record:
                user_record.is_locked = False
                user_record.status = "ACTIVE"

        elif task.operation == "SET_ACCOUNT_EXPIRY":
            if user_record:
                user_record.expiry_date = task.expiry_date

        elif task.operation == "DELETE_USER":
            if user_record:
                db.delete(user_record)

    else:
        # Task failed locally on the Ubuntu PC
        task.error_message = report.error_message or "Agent execution failed"
        task.result_details_json = json.dumps(sanitized_details)
        if task.attempts < task.max_attempts:
            task.status = "RETRYING"
        else:
            task.status = "FAILED"

    db.commit()

    record_audit(
        db, action=f"AGENT_TASK_{task.status}", entity_type="ProvisioningTask",
        entity_id=task.id, request=request,
        details={
            "hostname": device.hostname,
            "operation": task.operation,
            "target_username": task.target_username,
            "status": task.status
        }
    )

    return {"status": "recorded", "task_status": task.status}
