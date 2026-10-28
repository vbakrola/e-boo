"""Initial schema for Ubuntu Lab Manager

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Admin Users
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_users_username', 'admin_users', ['username'], unique=True)

    # 2. Devices
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hostname', sa.String(length=128), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=False),
        sa.Column('mac_address', sa.String(length=32), nullable=True),
        sa.Column('os_version', sa.String(length=128), nullable=False),
        sa.Column('kernel_version', sa.String(length=128), nullable=True),
        sa.Column('agent_version', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('is_approved', sa.Boolean(), nullable=False),
        sa.Column('device_token_hash', sa.String(length=255), nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_devices_hostname', 'devices', ['hostname'], unique=True)
    op.create_index('ix_devices_device_token_hash', 'devices', ['device_token_hash'], unique=True)

    # 3. Permission Profiles
    op.create_table(
        'permission_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('shell', sa.String(length=64), nullable=False),
        sa.Column('create_home', sa.Boolean(), nullable=False),
        sa.Column('primary_group', sa.String(length=64), nullable=False),
        sa.Column('supplementary_groups', sa.Text(), nullable=False),
        sa.Column('sudo_policy', sa.String(length=32), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_permission_profiles_name', 'permission_profiles', ['name'], unique=True)

    # 4. Provisioning Batches
    op.create_table(
        'provisioning_batches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by_admin_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('total_tasks', sa.Integer(), nullable=False),
        sa.Column('succeeded_tasks', sa.Integer(), nullable=False),
        sa.Column('failed_tasks', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Provisioning Tasks
    op.create_table(
        'provisioning_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('batch_id', sa.String(length=36), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('operation', sa.String(length=32), nullable=False),
        sa.Column('target_username', sa.String(length=64), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('force_password_change', sa.Boolean(), nullable=False),
        sa.Column('expiry_date', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result_details_json', sa.Text(), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['provisioning_batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['permission_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_provisioning_tasks_device_id', 'provisioning_tasks', ['device_id'])
    op.create_index('ix_provisioning_tasks_batch_id', 'provisioning_tasks', ['batch_id'])

    # 6. Task Credential Envelopes
    op.create_table(
        'task_credential_envelopes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('encrypted_payload', sa.Text(), nullable=False),
        sa.Column('nonce_hex', sa.String(length=64), nullable=False),
        sa.Column('auth_tag_hex', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_consumed', sa.Boolean(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['provisioning_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_credential_envelopes_task_id', 'task_credential_envelopes', ['task_id'], unique=True)

    # 7. Managed Users
    op.create_table(
        'managed_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('profile_name', sa.String(length=64), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('expiry_date', sa.String(length=32), nullable=True),
        sa.Column('last_provisioned_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_managed_users_device_username', 'managed_users', ['device_id', 'username'], unique=True)

    # 8. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('admin_username', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=128), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. Enrollment Tokens
    op.create_table(
        'enrollment_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=128), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=False),
        sa.Column('uses_count', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_enrollment_tokens_token', 'enrollment_tokens', ['token'], unique=True)


def downgrade() -> None:
    op.drop_table('enrollment_tokens')
    op.drop_table('audit_logs')
    op.drop_table('managed_users')
    op.drop_table('task_credential_envelopes')
    op.drop_table('provisioning_tasks')
    op.drop_table('provisioning_batches')
    op.drop_table('permission_profiles')
    op.drop_table('devices')
    op.drop_table('admin_users')
