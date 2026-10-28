"""Agent configuration manager."""
import os
import json
from typing import Optional

DEFAULT_CONFIG_PATH = os.environ.get("LAB_AGENT_CONFIG", "/etc/ubuntu-lab-manager/agent.conf")
LOCAL_CONFIG_PATH = "./agent.conf"


class AgentConfig:
    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8000",
        device_id: Optional[int] = None,
        device_token: Optional[str] = None,
        hostname: Optional[str] = None,
        ca_cert_path: Optional[str] = None,
        poll_interval: int = 5,
        heartbeat_interval: int = 15,
        config_path: str = DEFAULT_CONFIG_PATH
    ):
        self.server_url = server_url.rstrip("/")
        self.device_id = device_id
        self.device_token = device_token
        self.hostname = hostname
        self.ca_cert_path = ca_cert_path
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.config_path = config_path

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AgentConfig":
        """Load configuration from file or fallback to local path."""
        target_path = path or (DEFAULT_CONFIG_PATH if os.path.exists(DEFAULT_CONFIG_PATH) else LOCAL_CONFIG_PATH)
        if not os.path.exists(target_path):
            return cls(config_path=target_path)
        
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                server_url=data.get("server_url", "http://127.0.0.1:8000"),
                device_id=data.get("device_id"),
                device_token=data.get("device_token"),
                hostname=data.get("hostname"),
                ca_cert_path=data.get("ca_cert_path"),
                poll_interval=data.get("poll_interval", 5),
                heartbeat_interval=data.get("heartbeat_interval", 15),
                config_path=target_path
            )
        except Exception:
            return cls(config_path=target_path)

    def save(self, path: Optional[str] = None):
        """Save configuration with secure file permissions (0600)."""
        target_path = path or self.config_path
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        data = {
            "server_url": self.server_url,
            "device_id": self.device_id,
            "device_token": self.device_token,
            "hostname": self.hostname,
            "ca_cert_path": self.ca_cert_path,
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        # Restrict permissions on Linux systems so only owner can read credentials
        try:
            os.chmod(target_path, 0o600)
        except Exception:
            pass
