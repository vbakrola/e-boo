"""Permission Profiles router for managing Linux account role templates."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import PermissionProfile, AdminUser
from backend.app.schemas import (
    PermissionProfileCreate, PermissionProfileUpdate, PermissionProfileOut
)
from backend.app.auth import get_current_admin, record_audit

router = APIRouter(prefix="/api/v1/profiles", tags=["Permission Profiles"])


@router.get("", response_model=List[PermissionProfileOut])
def list_profiles(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all available permission profiles."""
    profiles = db.query(PermissionProfile).order_by(PermissionProfile.id.asc()).all()
    return [PermissionProfileOut.model_validate(p) for p in profiles]


@router.post("", response_model=PermissionProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_in: PermissionProfileCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new custom permission profile."""
    existing = db.query(PermissionProfile).filter(PermissionProfile.name == profile_in.name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Profile '{profile_in.name}' already exists")

    # Safety check on sudo_policy: only allowed values
    if profile_in.sudo_policy not in ["none", "restricted", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid sudo_policy. Must be 'none', 'restricted', or 'admin'.")

    profile = PermissionProfile(
        name=profile_in.name.strip(),
        description=profile_in.description.strip(),
        shell=profile_in.shell.strip(),
        create_home=profile_in.create_home,
        primary_group=profile_in.primary_group.strip(),
        supplementary_groups=profile_in.supplementary_groups.strip(),
        sudo_policy=profile_in.sudo_policy,
        is_system=False
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    record_audit(
        db, action="PROFILE_CREATED", entity_type="PermissionProfile",
        entity_id=str(profile.id), admin=admin, request=request,
        details={"name": profile.name, "sudo_policy": profile.sudo_policy}
    )

    return PermissionProfileOut.model_validate(profile)


@router.put("/{profile_id}", response_model=PermissionProfileOut)
def update_profile(
    profile_id: int,
    profile_update: PermissionProfileUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update an existing permission profile (cannot modify core system profiles' name)."""
    profile = db.query(PermissionProfile).filter(PermissionProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Permission profile not found")

    if profile_update.description is not None:
        profile.description = profile_update.description.strip()
    if profile_update.shell is not None:
        profile.shell = profile_update.shell.strip()
    if profile_update.create_home is not None:
        profile.create_home = profile_update.create_home
    if profile_update.primary_group is not None:
        profile.primary_group = profile_update.primary_group.strip()
    if profile_update.supplementary_groups is not None:
        profile.supplementary_groups = profile_update.supplementary_groups.strip()
    if profile_update.sudo_policy is not None:
        if profile_update.sudo_policy not in ["none", "restricted", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid sudo_policy")
        profile.sudo_policy = profile_update.sudo_policy

    db.commit()
    db.refresh(profile)

    record_audit(
        db, action="PROFILE_UPDATED", entity_type="PermissionProfile",
        entity_id=str(profile.id), admin=admin, request=request,
        details={"name": profile.name}
    )

    return PermissionProfileOut.model_validate(profile)


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a custom permission profile. System profiles cannot be deleted."""
    profile = db.query(PermissionProfile).filter(PermissionProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Permission profile not found")
    if profile.is_system:
        raise HTTPException(status_code=400, detail="Built-in system profiles (Student, Lab Assistant, Administrator) cannot be deleted.")

    name = profile.name
    db.delete(profile)
    db.commit()

    record_audit(
        db, action="PROFILE_DELETED", entity_type="PermissionProfile",
        entity_id=str(profile_id), admin=admin, request=request,
        details={"name": name}
    )

    return {"message": f"Profile '{name}' deleted successfully"}
