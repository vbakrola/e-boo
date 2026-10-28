"""Device management router for listing, inspecting, and managing lab PCs."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Device, AdminUser
from backend.app.schemas import DeviceOut, DeviceUpdate
from backend.app.auth import get_current_admin, record_audit

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceOut])
def list_devices(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all registered Ubuntu lab PCs with real-time status."""
    devices = db.query(Device).order_by(Device.hostname.asc()).all()
    return [DeviceOut.model_validate(d) for d in devices]


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get single device details."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceOut.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update device configuration (hostname, IP address, approval status)."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device_update.hostname is not None:
        existing = db.query(Device).filter(Device.hostname == device_update.hostname, Device.id != device_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Hostname '{device_update.hostname}' is already in use")
        device.hostname = device_update.hostname.strip()

    if device_update.ip_address is not None:
        device.ip_address = device_update.ip_address.strip()

    if device_update.is_approved is not None:
        device.is_approved = device_update.is_approved

    db.commit()
    db.refresh(device)

    record_audit(
        db, action="DEVICE_UPDATED", entity_type="Device",
        entity_id=str(device.id), admin=admin, request=request,
        details={"hostname": device.hostname, "ip_address": device.ip_address, "is_approved": device.is_approved}
    )

    return DeviceOut.model_validate(device)


@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Deregister and remove a device from the lab manager."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    hostname = device.hostname
    db.delete(device)
    db.commit()

    record_audit(
        db, action="DEVICE_REMOVED", entity_type="Device",
        entity_id=str(device_id), admin=admin, request=request,
        details={"hostname": hostname}
    )

    return {"message": f"Device '{hostname}' deregistered successfully"}
