"""Authentication router for admin login and credentials."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import AdminUser
from backend.app.schemas import LoginRequest, TokenResponse, AdminUserOut, ChangePasswordRequest
from backend.app.security import verify_password, hash_password, create_access_token
from backend.app.auth import get_current_admin, record_audit

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(login_req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate administrator and return access JWT."""
    admin = db.query(AdminUser).filter(AdminUser.username == login_req.username.strip()).first()
    if not admin or not verify_password(login_req.password, admin.password_hash):
        record_audit(
            db, action="ADMIN_LOGIN_FAILED", entity_type="AdminUser",
            entity_id=login_req.username, request=request,
            details={"attempted_username": login_req.username}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": str(admin.id), "username": admin.username})
    
    record_audit(
        db, action="ADMIN_LOGIN_SUCCESS", entity_type="AdminUser",
        entity_id=str(admin.id), admin=admin, request=request,
        details={"username": admin.username}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=480 * 60,
        admin_user=AdminUserOut.model_validate(admin)
    )


@router.get("/me", response_model=AdminUserOut)
def get_me(admin: AdminUser = Depends(get_current_admin)):
    """Retrieve details for current logged-in administrator."""
    return AdminUserOut.model_validate(admin)


@router.post("/change-password")
def change_password(
    pwd_req: ChangePasswordRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Change password for current administrator."""
    if not verify_password(pwd_req.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    
    admin.password_hash = hash_password(pwd_req.new_password)
    db.commit()

    record_audit(
        db, action="ADMIN_PASSWORD_CHANGED", entity_type="AdminUser",
        entity_id=str(admin.id), admin=admin, request=request
    )
    return {"message": "Password changed successfully"}
