"""Pydantic schemas for request validation and API responses."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re

USERNAME_REGEX = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_user: "AdminUserOut"


class AdminUserOut(BaseModel):
    id: int
    username: str
    full_name: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# --- Device Schemas ---
class DeviceEnrollRequest(BaseModel):
    enrollment_token: str
    hostname: str
    ip_address: str
    mac_address: Optional[str] = None
    os_version: str = "Ubuntu 22.04 LTS"
    kernel_version: Optional[str] = None
    agent_version: str = "1.0.0"


class DeviceEnrollResponse(BaseModel):
    device_id: int
    hostname: str
    device_token: str  # Given once upon enrollment
    status: str
    server_public_cert: Optional[str] = None


class DeviceHeartbeatRequest(BaseModel):
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    os_version: Optional[str] = None
    kernel_version: Optional[str] = None
    agent_version: Optional[str] = None
    uptime_seconds: Optional[int] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None


class DeviceHeartbeatResponse(BaseModel):
    status: str
    pending_tasks_count: int
    acknowledged_at: datetime


class DeviceOut(BaseModel):
    id: int
    hostname: str
    ip_address: str
    mac_address: Optional[str] = None
    os_version: str
    kernel_version: Optional[str] = None
    agent_version: str
    status: str  # online, offline, unknown
    is_approved: bool
    last_heartbeat_at: Optional[datetime] = None
    enrolled_at: datetime
    metadata_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeviceUpdate(BaseModel):
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    is_approved: Optional[bool] = None


# --- Permission Profile Schemas ---
class PermissionProfileCreate(BaseModel):
    name: str = Field(..., max_length=64)
    description: str
    shell: str = "/bin/bash"
    create_home: bool = True
    primary_group: str = "students"
    supplementary_groups: str = ""
    sudo_policy: str = "none"  # none, restricted, admin


class PermissionProfileUpdate(BaseModel):
    description: Optional[str] = None
    shell: Optional[str] = None
    create_home: Optional[bool] = None
    primary_group: Optional[str] = None
    supplementary_groups: Optional[str] = None
    sudo_policy: Optional[str] = None


class PermissionProfileOut(BaseModel):
    id: int
    name: str
    description: str
    shell: str
    create_home: bool
    primary_group: str
    supplementary_groups: str
    sudo_policy: str
    is_system: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Provisioning Schemas ---
class BulkUserItem(BaseModel):
    hostname: str
    username: str
    initial_password: str = Field(..., min_length=6)
    role: str = "Student"  # Profile name (Student, Lab Assistant, Administrator)
    force_password_change: bool = True
    expiry_date: Optional[str] = None  # YYYY-MM-DD

    @field_validator("username")
    @classmethod
    def validate_user(cls, v: str) -> str:
        clean = v.strip().lower()
        if not USERNAME_REGEX.match(clean):
            raise ValueError(f"Invalid username '{v}'. Must start with letter/underscore and contain only lowercase letters, digits, underscores, or dashes (max 32 chars).")
        return clean


class BulkProvisionRequest(BaseModel):
    batch_name: Optional[str] = None
    items: List[BulkUserItem]


class CSVValidateRow(BaseModel):
    row_number: int
    hostname: str
    username: str
    initial_password: str
    role: str
    force_password_change: bool
    is_valid: bool
    errors: List[str]


class CSVValidateResponse(BaseModel):
    is_valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: List[CSVValidateRow]


class ProvisioningTaskOut(BaseModel):
    id: str
    batch_id: Optional[str] = None
    device_id: int
    device_hostname: Optional[str] = None
    operation: str
    target_username: str
    profile_id: Optional[int] = None
    profile_name: Optional[str] = None
    force_password_change: bool
    expiry_date: Optional[str] = None
    status: str
    attempts: int
    max_attempts: int
    error_message: Optional[str] = None
    result_details_json: Optional[str] = None
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProvisioningBatchOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str
    total_tasks: int
    succeeded_tasks: int
    failed_tasks: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    tasks: List[ProvisioningTaskOut] = []

    model_config = ConfigDict(from_attributes=True)


# --- Managed User Schemas ---
class ManagedUserOut(BaseModel):
    id: int
    device_id: int
    device_hostname: Optional[str] = None
    username: str
    profile_name: str
    is_locked: bool
    expiry_date: Optional[str] = None
    status: str
    last_provisioned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserActionRequest(BaseModel):
    operation: str  # LOCK_ACCOUNT, UNLOCK_ACCOUNT, RESET_PASSWORD, SET_ACCOUNT_EXPIRY, DELETE_USER
    new_password: Optional[str] = None
    force_password_change: Optional[bool] = False
    expiry_date: Optional[str] = None


# --- Audit & Settings Schemas ---
class AuditLogOut(BaseModel):
    id: int
    admin_id: Optional[int] = None
    admin_username: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnrollmentTokenCreate(BaseModel):
    label: str = "Lab Device Enrollment"
    max_uses: int = 10
    expires_in_hours: int = 24


class EnrollmentTokenOut(BaseModel):
    id: int
    token: str
    label: str
    created_by: str
    max_uses: int
    uses_count: int
    expires_at: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryOut(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    total_managed_users: int
    running_tasks: int
    failed_tasks: int
    completed_tasks: int
    recent_batches: List[ProvisioningBatchOut]
    recent_audit_logs: List[AuditLogOut]


class AgentTaskPollResponse(BaseModel):
    task_id: str
    operation: str
    target_username: str
    profile: Optional[Dict[str, Any]] = None
    force_password_change: bool
    expiry_date: Optional[str] = None
    credential_payload: Optional[Dict[str, Any]] = None


class AgentTaskReportRequest(BaseModel):
    task_id: str
    status: str  # SUCCEEDED or FAILED
    error_message: Optional[str] = None
    result_details: Optional[Dict[str, Any]] = None
