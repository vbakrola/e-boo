"""Security module: Argon2id password hashing, AES-256-GCM envelope encryption,
JWT tokens, and POSIX input sanitization / validation.
"""
import re
import os
import json
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import jwt

from backend.app.config import settings

# Initialize Argon2id hasher with secure parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16
)

# POSIX username regex standard: begins with lowercase letter or underscore, 
# followed by lowercase alphanumeric, underscore, or dash, max 32 chars.
USERNAME_REGEX = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def hash_password(plain_password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def hash_token(token: str) -> str:
    """Compute a SHA-256 hash for device API tokens or enrollment tokens for safe storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(prefix: str = "tok_", length: int = 32) -> str:
    """Generate a high-entropy random URL-safe token."""
    return f"{prefix}{secrets.token_urlsafe(length)}"


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """Strictly validate username against POSIX rules and protected account safelist."""
    if not username:
        return False, "Username cannot be empty"
    
    clean_username = username.strip()
    if not USERNAME_REGEX.match(clean_username):
        return False, "Invalid username. Must start with a lowercase letter or underscore, containing only lowercase letters, digits, underscores, or dashes (max 32 characters)."
    
    if clean_username.lower() in settings.PROTECTED_USERNAMES:
        return False, f"Username '{clean_username}' is a protected system account and cannot be modified or managed."
    
    return True, None


# AES-256-GCM Ephemeral Credential Envelopes
def _derive_master_aes_key() -> bytes:
    """Derive a 256-bit key from the application secret key using SHA-256."""
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def encrypt_credential_payload(payload_dict: Dict[str, Any]) -> tuple[str, str, str]:
    """
    Encrypt ephemeral credential using AES-256-GCM.
    Returns (ciphertext_b64, nonce_hex, tag_hex).
    Note: AESGCM automatically appends the 16-byte authentication tag to the ciphertext.
    """
    key = _derive_master_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit recommended nonce for GCM
    data_bytes = json.dumps(payload_dict).encode("utf-8")
    
    # Encrypt (ciphertext includes auth tag at the end)
    ciphertext_with_tag = aesgcm.encrypt(nonce, data_bytes, None)
    
    ciphertext = ciphertext_with_tag[:-16]
    auth_tag = ciphertext_with_tag[-16:]
    
    return (
        base64.b64encode(ciphertext).decode("ascii"),
        nonce.hex(),
        auth_tag.hex()
    )


def decrypt_credential_payload(ciphertext_b64: str, nonce_hex: str, tag_hex: str) -> Optional[Dict[str, Any]]:
    """
    Decrypt ephemeral credential using AES-256-GCM.
    Returns the parsed dictionary payload, or None if authentication fails.
    """
    try:
        key = _derive_master_aes_key()
        aesgcm = AESGCM(key)
        nonce = bytes.fromhex(nonce_hex)
        tag = bytes.fromhex(tag_hex)
        ciphertext = base64.b64decode(ciphertext_b64.encode("ascii"))
        
        # Combine ciphertext and tag
        full_ciphertext = ciphertext + tag
        decrypted_bytes = aesgcm.decrypt(nonce, full_ciphertext, None)
        return json.loads(decrypted_bytes.decode("utf-8"))
    except Exception:
        return None


def sanitize_audit_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize any dictionary to redact passwords or confidential credentials."""
    sensitive_keys = {"password", "initial_password", "new_password", "credential", "secret", "token"}
    sanitized = {}
    for k, v in details.items():
        if any(sens in k.lower() for sens in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_details(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_audit_details(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized
