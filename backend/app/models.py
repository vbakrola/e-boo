"""SQLAlchemy models for Ubuntu Lab Manager."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=False, default="Lab Administrator")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_login_at = Column(DateTime, nullable=True)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(128), unique=True, index=True, nullable=False)
    ip_address = Column(String(64), nullable=False)
    mac_address = Column(String(32), nullable=True)
    os_version = Column(String(128), default="Ubuntu 22.04 LTS", nullable=False)
    kernel_version = Column(String(128), nullable=True)
    agent_version = Column(String(32), default="1.0.0", nullable=False)
    status = Column(String(32), default="unknown", nullable=False)  # online, offline, unknown
    is_approved = Column(Boolean, default=True, nullable=False)
    device_token_hash = Column(String(255), unique=True, index=True, nullable=False)
    last_heartbeat_at = Column(DateTime, nullable=True)
    enrolled_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(Text, nullable=True)

    tasks = relationship("ProvisioningTask", back_populates="device", cascade="all, delete-orphan")
    managed_users = relationship("ManagedUser", back_populates="device", cascade="all, delete-orphan")


class PermissionProfile(Base):
    __tablename__ = "permission_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    shell = Column(String(64), default="/bin/bash", nullable=False)
    create_home = Column(Boolean, default=True, nullable=False)
    primary_group = Column(String(64), default="students", nullable=False)
    supplementary_groups = Column(Text, default="", nullable=False)  # comma separated e.g. "dialout,plugdev"
    sudo_policy = Column(String(32), default="none", nullable=False)  # none, restricted, admin
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ProvisioningBatch(Base):
    __tablename__ = "provisioning_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    created_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED, PARTIAL, CANCELLED
    total_tasks = Column(Integer, default=0, nullable=False)
    succeeded_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    tasks = relationship("ProvisioningTask", back_populates="batch", cascade="all, delete-orphan")


class ProvisioningTask(Base):
    __tablename__ = "provisioning_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String(36), ForeignKey("provisioning_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = Column(String(32), nullable=False)  # CREATE_USER, RESET_PASSWORD, LOCK_ACCOUNT, UNLOCK_ACCOUNT, SET_ACCOUNT_EXPIRY, DELETE_USER
    target_username = Column(String(64), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("permission_profiles.id"), nullable=True)
    force_password_change = Column(Boolean, default=False, nullable=False)
    expiry_date = Column(String(32), nullable=True)  # YYYY-MM-DD
    status = Column(String(32), default="QUEUED", nullable=False)  # QUEUED, RUNNING, SUCCEEDED, FAILED, RETRYING, CANCELLED
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    result_details_json = Column(Text, nullable=True)
    queued_at = Column(DateTime, default=utc_now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    batch = relationship("ProvisioningBatch", back_populates="tasks")
    device = relationship("Device", back_populates="tasks")
    profile = relationship("PermissionProfile")
    credential_envelope = relationship("TaskCredentialEnvelope", uselist=False, back_populates="task", cascade="all, delete-orphan")


class TaskCredentialEnvelope(Base):
    __tablename__ = "task_credential_envelopes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("provisioning_tasks.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    encrypted_payload = Column(Text, nullable=False)  # Ephemeral encrypted credential block (AES-256-GCM)
    nonce_hex = Column(String(64), nullable=False)
    auth_tag_hex = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_consumed = Column(Boolean, default=False, nullable=False)
    consumed_at = Column(DateTime, nullable=True)

    task = relationship("ProvisioningTask", back_populates="credential_envelope")


class ManagedUser(Base):
    __tablename__ = "managed_users"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String(64), nullable=False, index=True)
    profile_name = Column(String(64), default="Student", nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    expiry_date = Column(String(32), nullable=True)
    last_provisioned_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, LOCKED, EXPIRED, DELETED

    device = relationship("Device", back_populates="managed_users")

    __table_args__ = (
        Index("ix_managed_users_device_username", "device_id", "username", unique=True),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=True)
    admin_username = Column(String(64), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(128), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    token_hash = Column(String(255), nullable=False)
    label = Column(String(128), default="Lab Batch Enrollment", nullable=False)
    created_by = Column(String(64), default="admin", nullable=False)
    max_uses = Column(Integer, default=10, nullable=False)
    uses_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
