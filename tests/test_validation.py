"""Tests for POSIX username validation and command injection prevention."""
import pytest
from backend.app.security import validate_username
from agent.executor import validate_target_username


@pytest.mark.parametrize("valid_name", [
    "student101",
    "student102",
    "labassistant1",
    "john_doe",
    "alice-bob",
    "_service",
    "user12345"
])
def test_valid_posix_usernames(valid_name):
    """Test standard valid POSIX usernames pass validation."""
    valid, err = validate_username(valid_name)
    assert valid is True
    assert err is None

    agent_valid, agent_err = validate_target_username(valid_name)
    assert agent_valid is True
    assert agent_err is None


@pytest.mark.parametrize("invalid_name,expected_reason", [
    ("", "empty"),
    ("123student", "Invalid username"),   # starts with digit
    ("Student101", "Invalid username"),   # uppercase letter
    ("student 101", "Invalid username"),  # space
    ("student@domain", "Invalid username"),# @ symbol
    ("student; rm -rf /", "Invalid username"), # command injection
    ("user`whoami`", "Invalid username"), # backtick injection
    ("user$(id)", "Invalid username"),    # subshell injection
    ("a" * 35, "Invalid username")        # exceeds 32 chars
])
def test_invalid_posix_usernames(invalid_name, expected_reason):
    """Test malformed and malicious username patterns are rejected."""
    valid, err = validate_username(invalid_name)
    assert valid is False
    assert expected_reason.lower() in err.lower()


@pytest.mark.parametrize("protected_account", [
    "root",
    "ubuntu",
    "admin",
    "administrator",
    "sudo",
    "daemon",
    "sys",
    "bin",
    "nobody",
    "sshd"
])
def test_protected_system_accounts_rejected(protected_account):
    """Ensure built-in and system administrator accounts can never be created, modified, or deleted."""
    valid, err = validate_username(protected_account)
    assert valid is False
    assert "protected system account" in err.lower()

    agent_valid, agent_err = validate_target_username(protected_account)
    assert agent_valid is False
    assert "protected system account" in agent_err.lower()
