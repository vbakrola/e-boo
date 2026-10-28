"""Hardware and OS vital diagnostics collector using Python standard library."""
import os
import re
import socket
import platform
import shutil
import uuid
from typing import Dict, Any


def get_lan_ip() -> str:
    """Determine the primary LAN IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually establish internet connection, just selects routing interface
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_mac_address() -> str:
    """Format local MAC address."""
    try:
        raw_mac = hex(uuid.getnode())[2:].zfill(12)
        return ":".join(re.findall("..", raw_mac))
    except Exception:
        return "00:00:00:00:00:00"


def get_os_version() -> str:
    """Read human-readable OS name and version from /etc/os-release on Ubuntu/Linux."""
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return f"{platform.system()} {platform.release()}"


def get_uptime_seconds() -> int:
    """Parse system uptime in seconds from /proc/uptime if available."""
    if os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", "r") as f:
                return int(float(f.readline().split()[0]))
        except Exception:
            pass
    return 0


def get_disk_percent() -> float:
    """Calculate root filesystem disk space used percentage."""
    try:
        usage = shutil.disk_usage("/")
        return round((usage.used / usage.total) * 100, 1)
    except Exception:
        return 0.0


def collect_system_vitals() -> Dict[str, Any]:
    """Collect system summary payload for regular agent heartbeat."""
    return {
        "hostname": socket.gethostname(),
        "ip_address": get_lan_ip(),
        "mac_address": get_mac_address(),
        "os_version": get_os_version(),
        "kernel_version": platform.release(),
        "uptime_seconds": get_uptime_seconds(),
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "disk_percent": get_disk_percent()
    }
