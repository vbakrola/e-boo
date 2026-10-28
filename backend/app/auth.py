"""Authentication and authorization dependencies for FastAPI."""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AdminUser, Device, AuditLog
from backend.app.security import decode_access_token, hash_token, sanitize_audit_details

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_admin(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Validate JWT token and return authenticated admin user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token",
        )
    admin = db.query(AdminUser).filter(AdminUser.id == int(admin_id)).first()
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or deleted",
        )
    return admin


def get_authenticated_device(
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db)
) -> Device:
    """Validate agent's device token and return matching registered device."""
    if not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-Token header",
        )
    token_hashed = hash_token(x_device_token)
    device = db.query(Device).filter(Device.device_token_hash == token_hashed).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
        )
    if not device.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is awaiting administrator approval",
        )
    return device


def record_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    admin: Optional[AdminUser] = None,
    request: Optional[Request] = None,
    details: Optional[dict] = None
) -> AuditLog:
    """Helper to record audit trail entries with secret redaction."""
    ip_addr = request.client.host if (request and request.client) else None
    user_agent = request.headers.get("user-agent") if request else None
    
    clean_details = sanitize_audit_details(details) if details else {}
    
    log_entry = AuditLog(
        admin_id=admin.id if admin else None,
        admin_username=admin.username if admin else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        ip_address=ip_addr,
        user_agent=user_agent[:255] if user_agent else None,
        details_json=json.dumps(clean_details) if clean_details else None,
        created_at=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()
    return log_entry
