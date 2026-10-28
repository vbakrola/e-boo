"""Audit logging router for system traceability and security inspection."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AuditLog, AdminUser
from backend.app.schemas import AuditLogOut
from backend.app.auth import get_current_admin

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogOut])
def list_audit_logs(
    action: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retrieve audit trail logs in reverse chronological order."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [AuditLogOut.model_validate(log) for log in logs]
