"""Bulk User Creation and Provisioning Batch management router."""
import io
import csv
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import (
    Device, PermissionProfile, ProvisioningBatch, ProvisioningTask,
    TaskCredentialEnvelope, AdminUser
)
from backend.app.schemas import (
    BulkProvisionRequest, BulkUserItem, CSVValidateResponse, CSVValidateRow,
    ProvisioningBatchOut, ProvisioningTaskOut
)
from backend.app.security import (
    validate_username, encrypt_credential_payload, sanitize_audit_details
)
from backend.app.auth import get_current_admin, record_audit

router = APIRouter(prefix="/api/v1/provisioning", tags=["Provisioning"])


def _format_task_out(t: ProvisioningTask) -> ProvisioningTaskOut:
    return ProvisioningTaskOut(
        id=t.id,
        batch_id=t.batch_id,
        device_id=t.device_id,
        device_hostname=t.device.hostname if t.device else f"Device #{t.device_id}",
        operation=t.operation,
        target_username=t.target_username,
        profile_id=t.profile_id,
        profile_name=t.profile.name if t.profile else "Custom",
        force_password_change=t.force_password_change,
        expiry_date=t.expiry_date,
        status=t.status,
        attempts=t.attempts,
        max_attempts=t.max_attempts,
        error_message=t.error_message,
        result_details_json=t.result_details_json,
        queued_at=t.queued_at,
        started_at=t.started_at,
        completed_at=t.completed_at
    )


@router.post("/validate-csv", response_model=CSVValidateResponse)
async def validate_csv(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Validate uploaded CSV file before submission, providing row-level diagnostics."""
    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")  # handle UTF-8 with BOM if present
    except Exception:
        raise HTTPException(status_code=400, detail="File must be a valid UTF-8 encoded CSV text file.")

    reader = csv.DictReader(io.StringIO(decoded))
    required_cols = {"hostname", "username", "initial_password", "role", "force_password_change"}
    if not reader.fieldnames or not required_cols.issubset({col.strip() for col in reader.fieldnames}):
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns. Must contain: {', '.join(required_cols)}"
        )

    # Preload existing devices and profiles for fast lookup
    all_devices = {d.hostname.lower(): d for d in db.query(Device).all()}
    all_profiles = {p.name.lower(): p for p in db.query(PermissionProfile).all()}

    rows_result: List[CSVValidateRow] = []
    row_num = 1
    total_valid = 0

    for raw_row in reader:
        row_num += 1
        # Normalize keys
        row = {k.strip(): v.strip() for k, v in raw_row.items() if k}
        hostname = row.get("hostname", "")
        username = row.get("username", "")
        initial_password = row.get("initial_password", "")
        role = row.get("role", "Student")
        force_pw_raw = row.get("force_password_change", "true").lower()
        force_pw = force_pw_raw in ["true", "1", "yes", "t"]

        row_errors: List[str] = []

        # Validate Hostname
        if not hostname:
            row_errors.append("Hostname is required")
        elif hostname.lower() not in all_devices:
            row_errors.append(f"Device '{hostname}' is not registered in the system")

        # Validate Username
        valid_u, u_err = validate_username(username)
        if not valid_u:
            row_errors.append(u_err or "Invalid username")

        # Validate Password
        if len(initial_password) < 6:
            row_errors.append("Password must be at least 6 characters long")

        # Validate Role
        if role.lower() not in all_profiles:
            row_errors.append(f"Permission profile '{role}' does not exist")

        is_valid = len(row_errors) == 0
        if is_valid:
            total_valid += 1

        rows_result.append(CSVValidateRow(
            row_number=row_num,
            hostname=hostname,
            username=username,
            initial_password="[MASKED]" if initial_password else "",
            role=role,
            force_password_change=force_pw,
            is_valid=is_valid,
            errors=row_errors
        ))

    total_rows = len(rows_result)
    return CSVValidateResponse(
        is_valid=(total_valid == total_rows and total_rows > 0),
        total_rows=total_rows,
        valid_rows=total_valid,
        invalid_rows=total_rows - total_valid,
        rows=rows_result
    )


@router.post("/bulk", response_model=ProvisioningBatchOut, status_code=status.HTTP_201_CREATED)
def create_bulk_provisioning_batch(
    req: BulkProvisionRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Queue bulk user provisioning across selected Ubuntu PCs.
    Each PC receives an independent, authenticated task with an ephemeral encrypted credential envelope.
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="No provisioning items provided")

    all_devices = {d.hostname.lower(): d for d in db.query(Device).all()}
    all_profiles = {p.name.lower(): p for p in db.query(PermissionProfile).all()}

    # Validation pass
    validated_tasks_data = []
    for idx, item in enumerate(req.items):
        device = all_devices.get(item.hostname.strip().lower())
        if not device:
            raise HTTPException(status_code=400, detail=f"Row {idx+1}: Device '{item.hostname}' is not enrolled")
        
        valid_u, u_err = validate_username(item.username)
        if not valid_u:
            raise HTTPException(status_code=400, detail=f"Row {idx+1}: {u_err}")
        
        if len(item.initial_password) < 6:
            raise HTTPException(status_code=400, detail=f"Row {idx+1}: Password must be at least 6 characters")

        profile = all_profiles.get(item.role.strip().lower())
        if not profile:
            raise HTTPException(status_code=400, detail=f"Row {idx+1}: Profile '{item.role}' not found")

        validated_tasks_data.append((item, device, profile))

    now = datetime.now(timezone.utc)
    batch_name = req.batch_name.strip() if req.batch_name else f"Batch-{now.strftime('%Y%m%d-%H%M%S')}"

    # Create Batch
    batch = ProvisioningBatch(
        id=str(uuid.uuid4()),
        name=batch_name,
        created_by_admin_id=admin.id,
        status="PENDING",
        total_tasks=len(validated_tasks_data),
        succeeded_tasks=0,
        failed_tasks=0,
        created_at=now
    )
    db.add(batch)
    db.flush()

    tasks_out = []
    envelope_ttl = now + timedelta(seconds=settings.CREDENTIAL_TTL_SECONDS)

    for item, device, profile in validated_tasks_data:
        task_id = str(uuid.uuid4())
        task = ProvisioningTask(
            id=task_id,
            batch_id=batch.id,
            device_id=device.id,
            operation="CREATE_USER",
            target_username=item.username.strip().lower(),
            profile_id=profile.id,
            force_password_change=item.force_password_change,
            expiry_date=item.expiry_date,
            status="QUEUED",
            attempts=0,
            max_attempts=settings.TASK_MAX_ATTEMPTS,
            queued_at=now
        )
        db.add(task)
        db.flush()

        # Encrypt the initial password in an ephemeral envelope
        cipher_b64, nonce_hex, tag_hex = encrypt_credential_payload({
            "password": item.initial_password,
            "username": task.target_username
        })

        envelope = TaskCredentialEnvelope(
            id=str(uuid.uuid4()),
            task_id=task.id,
            encrypted_payload=cipher_b64,
            nonce_hex=nonce_hex,
            auth_tag_hex=tag_hex,
            expires_at=envelope_ttl,
            is_consumed=False
        )
        db.add(envelope)
        tasks_out.append(task)

    db.commit()
    db.refresh(batch)

    record_audit(
        db, action="BULK_PROVISIONING_STARTED", entity_type="ProvisioningBatch",
        entity_id=batch.id, admin=admin, request=request,
        details={
            "batch_name": batch.name,
            "total_accounts": len(validated_tasks_data),
            "target_devices": list(set(d.hostname for _, d, _ in validated_tasks_data))
        }
    )

    return ProvisioningBatchOut(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        status=batch.status,
        total_tasks=batch.total_tasks,
        succeeded_tasks=batch.succeeded_tasks,
        failed_tasks=batch.failed_tasks,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        tasks=[_format_task_out(t) for t in tasks_out]
    )


@router.get("/batches", response_model=List[ProvisioningBatchOut])
def list_batches(
    limit: int = 20,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List recent provisioning batches with overall progress."""
    batches = db.query(ProvisioningBatch).order_by(ProvisioningBatch.created_at.desc()).limit(limit).all()
    out = []
    for b in batches:
        tasks = db.query(ProvisioningTask).filter(ProvisioningTask.batch_id == b.id).all()
        out.append(ProvisioningBatchOut(
            id=b.id,
            name=b.name,
            description=b.description,
            status=b.status,
            total_tasks=b.total_tasks,
            succeeded_tasks=b.succeeded_tasks,
            failed_tasks=b.failed_tasks,
            created_at=b.created_at,
            completed_at=b.completed_at,
            tasks=[_format_task_out(t) for t in tasks]
        ))
    return out


@router.get("/batches/{batch_id}", response_model=ProvisioningBatchOut)
def get_batch(
    batch_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get single batch with task progress per PC."""
    batch = db.query(ProvisioningBatch).filter(ProvisioningBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    tasks = db.query(ProvisioningTask).filter(ProvisioningTask.batch_id == batch.id).all()
    return ProvisioningBatchOut(
        id=batch.id,
        name=batch.name,
        description=batch.description,
        status=batch.status,
        total_tasks=batch.total_tasks,
        succeeded_tasks=batch.succeeded_tasks,
        failed_tasks=batch.failed_tasks,
        created_at=batch.created_at,
        completed_at=batch.completed_at,
        tasks=[_format_task_out(t) for t in tasks]
    )


@router.post("/tasks/{task_id}/retry")
def retry_task(
    task_id: str,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Safely retry a failed provisioning task."""
    task = db.query(ProvisioningTask).filter(ProvisioningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ["FAILED", "RETRYING"]:
        raise HTTPException(status_code=400, detail=f"Cannot retry task in status '{task.status}'")

    task.status = "QUEUED"
    task.error_message = None
    task.queued_at = datetime.now(timezone.utc)
    task.attempts = 0

    # If the credential envelope is expired or consumed, extend TTL
    if task.credential_envelope:
        task.credential_envelope.expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.CREDENTIAL_TTL_SECONDS)
        task.credential_envelope.is_consumed = False

    # Also update batch status to RUNNING if it had finished as FAILED or PARTIAL
    if task.batch:
        task.batch.status = "RUNNING"
        task.batch.completed_at = None

    db.commit()

    record_audit(
        db, action="TASK_RETRIED", entity_type="ProvisioningTask",
        entity_id=task.id, admin=admin, request=request,
        details={"target_username": task.target_username, "device_id": task.device_id}
    )

    return {"message": "Task requeued for execution"}


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancel a queued provisioning task."""
    task = db.query(ProvisioningTask).filter(ProvisioningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in ["SUCCEEDED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task already '{task.status}'")

    task.status = "CANCELLED"
    task.completed_at = datetime.now(timezone.utc)

    # Purge any credential envelope immediately
    if task.credential_envelope:
        db.delete(task.credential_envelope)

    db.commit()

    record_audit(
        db, action="TASK_CANCELLED", entity_type="ProvisioningTask",
        entity_id=task.id, admin=admin, request=request,
        details={"target_username": task.target_username, "device_id": task.device_id}
    )

    return {"message": "Task cancelled"}
