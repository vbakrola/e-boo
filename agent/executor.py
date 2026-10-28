"""Agent execution engine: Safely executes validated account management operations
using argument arrays with shell=False, protected system account safelists, and secure stdin password piping.
"""
import re
import sys
import subprocess
import logging
import platform
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("lab_agent.executor")

# Protected system accounts that must never be modified, locked, or deleted
PROTECTED_USERNAMES = {
    "root", "ubuntu", "admin", "administrator", "sudo", "sys", "daemon",
    "bin", "sync", "games", "man", "lp", "mail", "news", "uucp", "proxy",
    "www-data", "backup", "list", "irc", "gnats", "nobody", "systemd-network",
    "systemd-resolve", "systemd-timesync", "messagebus", "sshd", "syslog"
}

USERNAME_REGEX = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def validate_target_username(username: str) -> Tuple[bool, Optional[str]]:
    """Strictly validate username against POSIX rules and protected accounts."""
    if not username:
        return False, "Target username cannot be empty"
    clean = username.strip().lower()
    if not USERNAME_REGEX.match(clean):
        return False, f"Invalid username '{username}': must conform to POSIX rules (lowercase, alphanumeric, dash/underscore, max 32 chars)."
    if clean in PROTECTED_USERNAMES:
        return False, f"Safety violation: '{clean}' is a protected system account and cannot be modified or deleted."
    return True, None


def run_cmd(args: List[str], stdin_data: Optional[str] = None) -> Tuple[int, str, str]:
    """
    Execute system commands securely:
    - Never uses shell=True
    - Arguments are passed as an explicit array
    - Passwords and secrets are passed through stdin, never argv
    """
    # Safe command logging: do NOT log stdin_data
    logger.info(f"Executing command: {' '.join(args)}")
    try:
        proc = subprocess.run(
            args,
            input=stdin_data,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return 1, "", str(e)


def user_exists(username: str) -> bool:
    """Check if a Linux user account exists using id command."""
    if platform.system() != "Linux":
        return False
    ret, _, _ = run_cmd(["id", "-u", username])
    return ret == 0


def ensure_group(group_name: str) -> bool:
    """Ensure a Linux system group exists; creates it if absent."""
    if not group_name or platform.system() != "Linux":
        return True
    ret, _, _ = run_cmd(["groupadd", "-f", group_name])
    return ret == 0


def execute_task(task_payload: Dict[str, Any], dry_run: bool = False) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Dispatch and execute an authorized operation.
    Returns (success: bool, error_message: Optional[str], details: Dict[str, Any]).
    """
    operation = task_payload.get("operation")
    username = task_payload.get("target_username", "").strip().lower()
    
    valid, err = validate_target_username(username)
    if not valid:
        return False, err, {"operation": operation, "username": username}

    # Simulation mode for testing on non-Linux environments
    is_linux = platform.system() == "Linux" and not dry_run

    if operation == "CREATE_USER":
        return _op_create_user(task_payload, username, is_linux)
    elif operation == "RESET_PASSWORD":
        return _op_reset_password(task_payload, username, is_linux)
    elif operation == "LOCK_ACCOUNT":
        return _op_lock_account(username, is_linux)
    elif operation == "UNLOCK_ACCOUNT":
        return _op_unlock_account(username, is_linux)
    elif operation == "SET_ACCOUNT_EXPIRY":
        return _op_set_expiry(task_payload, username, is_linux)
    elif operation == "DELETE_USER":
        return _op_delete_user(username, is_linux)
    else:
        return False, f"Unsupported operation: '{operation}'", {"operation": operation}


def _op_create_user(task: Dict[str, Any], username: str, is_linux: bool) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Execute CREATE_USER."""
    profile = task.get("profile") or {}
    shell = profile.get("shell", "/bin/bash")
    create_home = profile.get("create_home", True)
    primary_group = profile.get("primary_group", "students")
    supplementary_groups = profile.get("supplementary_groups", "")
    force_password_change = task.get("force_password_change", True)
    expiry_date = task.get("expiry_date")
    
    cred = task.get("credential_payload") or {}
    password = cred.get("password")

    if not is_linux:
        # Development / test mock simulation
        return True, None, {
            "action": "CREATE_USER",
            "username": username,
            "shell": shell,
            "primary_group": primary_group,
            "force_password_change": force_password_change,
            "simulated": True
        }

    # 1. Ensure primary group exists
    if primary_group:
        ensure_group(primary_group)

    # 2. Ensure supplementary groups exist
    supp_list = [g.strip() for g in supplementary_groups.split(",") if g.strip()]
    for g in supp_list:
        ensure_group(g)

    # 3. Create user account
    if not user_exists(username):
        cmd = ["useradd"]
        if create_home:
            cmd.append("-m")
        cmd.extend(["-s", shell])
        if primary_group:
            cmd.extend(["-g", primary_group])
        if supp_list:
            cmd.extend(["-G", ",".join(supp_list)])
        cmd.append(username)

        ret, stdout, stderr = run_cmd(cmd)
        if ret != 0:
            return False, f"useradd failed: {stderr or stdout}", {"returncode": ret}
    else:
        # Idempotent update of existing user groups/shell
        cmd = ["usermod", "-s", shell]
        if primary_group:
            cmd.extend(["-g", primary_group])
        if supp_list:
            cmd.extend(["-G", ",".join(supp_list)])
        cmd.append(username)
        run_cmd(cmd)

    # 4. Set initial password securely via chpasswd over stdin (never argv)
    if password:
        ret, stdout, stderr = run_cmd(["chpasswd"], stdin_data=f"{username}:{password}\n")
        if ret != 0:
            return False, f"chpasswd failed: {stderr or stdout}", {"returncode": ret}

    # 5. Enforce password change at first login
    if force_password_change:
        ret, stdout, stderr = run_cmd(["passwd", "-e", username])
        if ret != 0:
            logger.warning(f"passwd -e failed: {stderr}")

    # 6. Set account expiration date if specified (YYYY-MM-DD)
    if expiry_date:
        run_cmd(["chage", "-E", expiry_date, username])

    return True, None, {
        "action": "CREATE_USER",
        "username": username,
        "shell": shell,
        "primary_group": primary_group,
        "force_password_change": force_password_change
    }


def _op_reset_password(task: Dict[str, Any], username: str, is_linux: bool) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Execute RESET_PASSWORD."""
    cred = task.get("credential_payload") or {}
    password = cred.get("password")
    force_change = task.get("force_password_change", False)

    if not password:
        return False, "No password provided in credential envelope", {}

    if not is_linux:
        return True, None, {"action": "RESET_PASSWORD", "username": username, "simulated": True}

    if not user_exists(username):
        return False, f"User '{username}' does not exist on this machine", {}

    # Pipe new password to chpasswd via stdin
    ret, stdout, stderr = run_cmd(["chpasswd"], stdin_data=f"{username}:{password}\n")
    if ret != 0:
        return False, f"chpasswd failed: {stderr or stdout}", {"returncode": ret}

    if force_change:
        run_cmd(["passwd", "-e", username])

    return True, None, {"action": "RESET_PASSWORD", "username": username}


def _op_lock_account(username: str, is_linux: bool) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Execute LOCK_ACCOUNT."""
    if not is_linux:
        return True, None, {"action": "LOCK_ACCOUNT", "username": username, "simulated": True}

    if not user_exists(username):
        return False, f"User '{username}' does not exist", {}

    ret, stdout, stderr = run_cmd(["passwd", "-l", username])
    if ret != 0:
        return False, f"passwd -l failed: {stderr or stdout}", {"returncode": ret}
    return True, None, {"action": "LOCK_ACCOUNT", "username": username}


def _op_unlock_account(username: str, is_linux: bool) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Execute UNLOCK_ACCOUNT."""
    if not is_linux:
        return True, None, {"action": "UNLOCK_ACCOUNT", "username": username, "simulated": True}

    if not user_exists(username):
        return False, f"User '{username}' does not exist", {}

    ret, stdout, stderr = run_cmd(["passwd", "-u", username])
    if ret != 0:
        return False, f"passwd -u failed: {stderr or stdout}", {"returncode": ret}
    return True, None, {"action": "UNLOCK_ACCOUNT", "username": username}


def _op_set_expiry(task: Dict[str, Any], username: str, is_linux: bool) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Execute SET_ACCOUNT_EXPIRY."""
    expiry_date = task.get("expiry_date")
    if not expiry_date:
        return False, "Expiry date required (YYYY-MM-DD)", {}

    if not is_linux:
        return True, None, {"action": "SET_ACCOUNT_EXPIRY", "username": username, "expiry_date": expiry_date, "simulated": True}

    if not user_exists(username):
        return False, f"User '{username}' does not exist", {}

    ret, stdout, stderr = run_cmd(["chage", "-E", expiry_date, username])
    if ret != 0:
        return False, f"chage -E failed: {stderr or stdout}", {"returncode": ret}
    return True, None, {"action": "SET_ACCOUNT_EXPIRY", "username": username, "expiry_date": expiry_date}


def _op_delete_user(username: str, is_linux: bool) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Execute DELETE_USER."""
    if username in PROTECTED_USERNAMES:
        return False, f"Cannot delete protected system account '{username}'", {}

    if not is_linux:
        return True, None, {"action": "DELETE_USER", "username": username, "simulated": True}

    if not user_exists(username):
        # Account already absent, idempotent success
        return True, None, {"action": "DELETE_USER", "username": username, "note": "Already absent"}

    ret, stdout, stderr = run_cmd(["userdel", "-r", username])
    if ret != 0:
        return False, f"userdel -r failed: {stderr or stdout}", {"returncode": ret}
    return True, None, {"action": "DELETE_USER", "username": username}
