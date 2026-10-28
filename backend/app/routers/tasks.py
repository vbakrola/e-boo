"""Task progress tracking router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ProvisioningTask, AdminUser
from backend.app.schemas import ProvisioningTaskOut
from backend.app.auth import get_current_admin
from backend.app.routers.provisioning import _format_task_out

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.get("", response_model=List[ProvisioningTaskOut])
def list_tasks(
    status: Optional[str] = None,
    device_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List provisioning tasks across devices with filtering."""
    query = db.query(ProvisioningTask)
    if status:
        query = query.filter(ProvisioningTask.status == status.upper())
    if device_id:
        query = query.filter(ProvisioningTask.device_id == device_id)

    tasks = query.order_by(ProvisioningTask.queued_at.desc()).limit(limit).all()
    return [_format_task_out(t) for t in tasks]


@router.get("/{task_id}", response_model=ProvisioningTaskOut)
def get_task(
    task_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get single task details."""
    task = db.query(ProvisioningTask).filter(ProvisioningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _format_task_out(task)
