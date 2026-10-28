"""Application Configuration for Ubuntu Lab Manager."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Ubuntu Lab Manager"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    
    # Security
    SECRET_KEY: str = "ubuntu-lab-manager-lan-super-secret-key-change-in-prod-12345678"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for lab session
    
    # Server / LAN Binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite:///./lab_manager.db"
    
    # Heartbeat & Task Worker
    HEARTBEAT_TIMEOUT_SECONDS: int = 45
    TASK_MAX_ATTEMPTS: int = 3
    CREDENTIAL_TTL_SECONDS: int = 600  # 10 minutes maximum lifespan
    
    # Linux Account Safety Safeguards
    # System accounts and existing administrative user accounts that must never be modified or deleted
    PROTECTED_USERNAMES: List[str] = [
        "root", "ubuntu", "admin", "administrator", "sudo", "sys", "daemon",
        "bin", "sync", "games", "man", "lp", "mail", "news", "uucp", "proxy",
        "www-data", "backup", "list", "irc", "gnats", "nobody", "systemd-network",
        "systemd-resolve", "systemd-timesync", "messagebus", "sshd", "syslog"
    ]


settings = Settings()
