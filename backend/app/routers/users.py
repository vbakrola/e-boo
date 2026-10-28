"""User Management router for viewing, locking, unlocking, resetting, and deleting accounts."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import ManagedUser, Device, ProvisioningTask, TaskCredentialEnvelope, AdminUser
from backend.app.schemas import ManagedUserOut, UserActionRequest
from backend.app.security import validate_username, encrypt_credential_payload
from backend.app.auth import get_current_admin, record_audit

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])


@router.get("", response_model=List[ManagedUserOut])
def list_managed_users(
    device_id: Optional[int] = None,
    username: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all managed Linux users across registered Ubuntu PCs."""
    query = db.query(ManagedUser)
    if device_id:
        query = query.filter(ManagedUser.device_id == device_id)
    if username:
        query = query.filter(ManagedUser.username.ilike(f"%{username.strip()}%"))
    
    users = query.order_by(ManagedUser.username.asc()).all()
    out = []
    for u in users:
        out.append(ManagedUserOut(
            id=u.id,
            device_id=u.device_id,
            device_hostname=u.device.hostname if u.device else f"Device #{u.device_id}",
            username=u.username,
            profile_name=u.profile_name,
            is_locked=u.is_locked,
            expiry_date=u.expiry_date,
            status=u.status,
            last_provisioned_at=u.last_provisioned_at
        ))
    return out


@router.post("/{user_id}/action")
def trigger_user_action(
    user_id: int,
    action_req: UserActionRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Queue an account management task (LOCK_ACCOUNT, UNLOCK_ACCOUNT, RESET_PASSWORD, SET_ACCOUNT_EXPIRY, DELETE_USER)
    with strict system account protections.
    """
    managed_user = db.query(ManagedUser).filter(ManagedUser.id == user_id).first()
    if not managed_user:
        raise HTTPException(status_code=404, detail="Managed user not found")

    target_username = managed_user.username.strip().lower()

    # Safety check: Protect existing system administrator and core system accounts
    if target_username in settings.PROTECTED_USERNAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Safety restriction: Modifying protected system account '{target_username}' is forbidden."
        )

    allowed_operations = {
        "LOCK_ACCOUNT", "UNLOCK_ACCOUNT", "RESET_PASSWORD", "SET_ACCOUNT_EXPIRY", "DELETE_USER"
    }
    op = action_req.operation.upper()
    if op not in allowed_operations:
        raise HTTPException(status_code=400, detail=f"Invalid operation. Must be one of: {', '.join(allowed_operations)}")

    now = datetime.now(timezone.utc)
    task_id = str(uuid.uuid4())
    task = ProvisioningTask(
        id=task_id,
        device_id=managed_user.device_id,
        operation=op,
        target_username=target_username,
        force_password_change=action_req.force_password_change or False,
        expiry_date=action_req.expiry_date,
        status="QUEUED",
        attempts=0,
        max_attempts=settings.TASK_MAX_ATTEMPTS,
        queued_at=now
    )
    db.add(task)
    db.flush()

    # If resetting password, attach encrypted credential envelope
    if op == "RESET_PASSWORD":
        if not action_req.new_password or len(action_req.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters long")
        
        cipher_b64, nonce_hex, tag_hex = encrypt_credential_payload({
            "password": action_req.new_password,
            "username": target_username
        })
        envelope = TaskCredentialEnvelope(
            id=str(uuid.uuid4()),
            task_id=task.id,
            encrypted_payload=cipher_b64,
            nonce_hex=nonce_hex,
            auth_tag_hex=tag_hex,
            expires_at=now + timedelta(seconds=settings.CREDENTIAL_TTL_SECONDS),
            is_consumed=False
        )
        db.add(envelope)

    db.commit()

    record_audit(
        db, action=f"USER_ACTION_{op}", entity_type="ManagedUser",
        entity_id=str(managed_user.id), admin=admin, request=request,
        details={
            "operation": op,
            "username": target_username,
            "device_id": managed_user.device_id,
            "device_hostname": managed_user.device.hostname if managed_user.device else None
        }
    )

    return {
        "message": f"Action '{op}' queued for user '{target_username}' on PC '{managed_user.device.hostname if managed_user.device else managed_user.device_id}'",
        "task_id": task.id
    }
