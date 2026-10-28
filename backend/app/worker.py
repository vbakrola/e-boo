"""Background worker for task management, heartbeat monitoring, and credential lifecycle."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import Device, ProvisioningBatch, ProvisioningTask, TaskCredentialEnvelope

logger = logging.getLogger("lab_manager.worker")


async def run_worker_loop():
    """Continuous background loop running periodically within the FastAPI lifespan."""
    logger.info("Starting background task worker and device monitor loop...")
    while True:
        try:
            db = SessionLocal()
            try:
                update_device_online_statuses(db)
                process_batch_statuses(db)
                cleanup_expired_credentials(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Worker iteration error: {e}", exc_info=True)
        
        await asyncio.sleep(5)  # Tick every 5 seconds


def update_device_online_statuses(db: Session):
    """Mark devices as offline if heartbeat has timed out."""
    now = datetime.now(timezone.utc)
    timeout_threshold = now - timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)
    
    # Devices whose heartbeat is stale
    stale_devices = db.query(Device).filter(
        Device.status == "online",
        (Device.last_heartbeat_at < timeout_threshold) | (Device.last_heartbeat_at.is_(None))
    ).all()
    
    for device in stale_devices:
        device.status = "offline"
    
    if stale_devices:
        db.commit()


def process_batch_statuses(db: Session):
    """Evaluate and update parent batch status based on individual tasks."""
    now = datetime.now(timezone.utc)
    active_batches = db.query(ProvisioningBatch).filter(
        ProvisioningBatch.status.in_(["PENDING", "RUNNING"])
    ).all()

    for batch in active_batches:
        tasks = db.query(ProvisioningTask).filter(ProvisioningTask.batch_id == batch.id).all()
        if not tasks:
            continue

        total = len(tasks)
        succeeded = sum(1 for t in tasks if t.status == "SUCCEEDED")
        failed = sum(1 for t in tasks if t.status in ["FAILED", "CANCELLED"])
        running = sum(1 for t in tasks if t.status in ["RUNNING", "RETRYING"])
        queued = sum(1 for t in tasks if t.status == "QUEUED")

        batch.total_tasks = total
        batch.succeeded_tasks = succeeded
        batch.failed_tasks = failed

        if running > 0 or queued > 0:
            batch.status = "RUNNING"
        else:
            batch.completed_at = now
            if succeeded == total:
                batch.status = "COMPLETED"
            elif failed == total:
                batch.status = "FAILED"
            else:
                batch.status = "PARTIAL"

    if active_batches:
        db.commit()


def cleanup_expired_credentials(db: Session):
    """Purge expired ephemeral credential envelopes from the database."""
    now = datetime.now(timezone.utc)
    expired = db.query(TaskCredentialEnvelope).filter(
        (TaskCredentialEnvelope.expires_at < now) | (TaskCredentialEnvelope.is_consumed.is_(True))
    ).all()

    for env in expired:
        db.delete(env)
    
    if expired:
        db.commit()
