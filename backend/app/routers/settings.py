"""System Settings, Dashboard Summary, Enrollment Tokens, and Database Backups."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db, engine
from backend.app.models import (
    Device, ManagedUser, ProvisioningTask, ProvisioningBatch, AuditLog,
    EnrollmentToken, AdminUser
)
from backend.app.schemas import (
    DashboardSummaryOut, EnrollmentTokenCreate, EnrollmentTokenOut,
    ProvisioningBatchOut, AuditLogOut
)
from backend.app.security import generate_secure_token, hash_token
from backend.app.auth import get_current_admin, record_audit
from backend.app.routers.provisioning import _format_task_out

router = APIRouter(prefix="/api/v1/settings", tags=["Settings & Summary"])


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Aggregate dashboard metrics, summary cards, and quick widgets."""
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    offline_devices = db.query(Device).filter(Device.status.in_(["offline", "unknown"])).count()
    
    total_managed_users = db.query(ManagedUser).count()
    running_tasks = db.query(ProvisioningTask).filter(ProvisioningTask.status.in_(["QUEUED", "RUNNING", "RETRYING"])).count()
    failed_tasks = db.query(ProvisioningTask).filter(ProvisioningTask.status == "FAILED").count()
    completed_tasks = db.query(ProvisioningTask).filter(ProvisioningTask.status == "SUCCEEDED").count()

    recent_batches_models = db.query(ProvisioningBatch).order_by(ProvisioningBatch.created_at.desc()).limit(5).all()
    recent_batches = []
    for b in recent_batches_models:
        tasks = db.query(ProvisioningTask).filter(ProvisioningTask.batch_id == b.id).all()
        recent_batches.append(ProvisioningBatchOut(
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

    recent_logs_models = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
    recent_audit_logs = [AuditLogOut.model_validate(log) for log in recent_logs_models]

    return DashboardSummaryOut(
        total_devices=total_devices,
        online_devices=online_devices,
        offline_devices=offline_devices,
        total_managed_users=total_managed_users,
        running_tasks=running_tasks,
        failed_tasks=failed_tasks,
        completed_tasks=completed_tasks,
        recent_batches=recent_batches,
        recent_audit_logs=recent_audit_logs
    )


@router.get("/enrollment-tokens", response_model=List[EnrollmentTokenOut])
def list_enrollment_tokens(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List device enrollment tokens."""
    tokens = db.query(EnrollmentToken).order_by(EnrollmentToken.created_at.desc()).all()
    return [EnrollmentTokenOut.model_validate(t) for t in tokens]


@router.post("/enrollment-tokens", response_model=EnrollmentTokenOut)
def create_enrollment_token(
    token_in: EnrollmentTokenCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Generate a new secure enrollment token to bootstrap and connect lab PCs."""
    raw_token = generate_secure_token(prefix="enroll_", length=32)
    token_hashed = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=token_in.expires_in_hours)

    token_obj = EnrollmentToken(
        token=raw_token,
        token_hash=token_hashed,
        label=token_in.label.strip(),
        created_by=admin.username,
        max_uses=token_in.max_uses,
        uses_count=0,
        expires_at=expires_at,
        is_active=True,
        created_at=now
    )
    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)

    record_audit(
        db, action="ENROLLMENT_TOKEN_CREATED", entity_type="EnrollmentToken",
        entity_id=str(token_obj.id), admin=admin, request=request,
        details={"label": token_obj.label, "max_uses": token_obj.max_uses}
    )

    return EnrollmentTokenOut.model_validate(token_obj)


@router.delete("/enrollment-tokens/{token_id}")
def revoke_enrollment_token(
    token_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Revoke an enrollment token."""
    token = db.query(EnrollmentToken).filter(EnrollmentToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.is_active = False
    db.commit()

    record_audit(
        db, action="ENROLLMENT_TOKEN_REVOKED", entity_type="EnrollmentToken",
        entity_id=str(token_id), admin=admin, request=request
    )
    return {"message": "Enrollment token revoked"}


@router.post("/backup-db")
def trigger_database_backup(
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Perform a safe, atomic SQLite online backup without taking the server offline.
    Saves snapshot to backups/ directory.
    """
    backup_dir = os.path.abspath("./backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"lab_manager_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # Use SQLite's safe online backup API
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_file):
        raise HTTPException(status_code=500, detail="Source SQLite database file not found")

    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(backup_path)
    with dst:
        src.backup(dst, pages=100)
    dst.close()
    src.close()

    file_size_bytes = os.path.getsize(backup_path)

    record_audit(
        db, action="DATABASE_BACKUP_CREATED", entity_type="System",
        entity_id=backup_filename, admin=admin, request=request,
        details={"filename": backup_filename, "size_bytes": file_size_bytes}
    )

    return {
        "message": "Database backup completed successfully",
        "filename": backup_filename,
        "backup_path": backup_path,
        "size_bytes": file_size_bytes,
        "created_at": timestamp
    }
