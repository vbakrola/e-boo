"""Tests for Agent local execution, argument array enforcement, and command injection safety."""
from agent.executor import execute_task, validate_target_username


def test_agent_create_user_simulation():
    """Test CREATE_USER task simulation runs without errors."""
    task = {
        "operation": "CREATE_USER",
        "target_username": "student_sim",
        "profile": {
            "name": "Student",
            "shell": "/bin/bash",
            "create_home": True,
            "primary_group": "students"
        },
        "force_password_change": True,
        "credential_payload": {"password": "Password123#"}
    }
    success, err, details = execute_task(task, dry_run=True)
    assert success is True
    assert err is None
    assert details["action"] == "CREATE_USER"
    assert details["username"] == "student_sim"


def test_agent_lock_and_unlock_simulation():
    """Test LOCK_ACCOUNT and UNLOCK_ACCOUNT operations."""
    lock_task = {"operation": "LOCK_ACCOUNT", "target_username": "student_sim"}
    success, err, details = execute_task(lock_task, dry_run=True)
    assert success is True
    assert details["action"] == "LOCK_ACCOUNT"

    unlock_task = {"operation": "UNLOCK_ACCOUNT", "target_username": "student_sim"}
    success, err, details = execute_task(unlock_task, dry_run=True)
    assert success is True
    assert details["action"] == "UNLOCK_ACCOUNT"


def test_agent_password_reset_simulation():
    """Test RESET_PASSWORD operation."""
    reset_task = {
        "operation": "RESET_PASSWORD",
        "target_username": "student_sim",
        "credential_payload": {"password": "NewSecretPassword#"}
    }
    success, err, details = execute_task(reset_task, dry_run=True)
    assert success is True
    assert details["action"] == "RESET_PASSWORD"


def test_agent_rejects_protected_account_deletion():
    """Test executor immediately rejects deletion or modification of root/ubuntu accounts."""
    for protected in ["root", "ubuntu", "admin", "sudo"]:
        del_task = {"operation": "DELETE_USER", "target_username": protected}
        success, err, details = execute_task(del_task, dry_run=True)
        assert success is False
        assert "protected system account" in err.lower()


def test_agent_rejects_command_injection_usernames():
    """Test executor rejects shell metacharacters and command injection payloads."""
    malicious = [
        "student; reboot",
        "user$(rm -rf /)",
        "victim`id`",
        "user | cat /etc/shadow",
        "user && touch /tmp/pwn"
    ]
    for target in malicious:
        task = {"operation": "CREATE_USER", "target_username": target}
        success, err, details = execute_task(task, dry_run=True)
        assert success is False
        assert "invalid username" in err.lower()
