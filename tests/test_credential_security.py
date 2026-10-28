"""Tests for Ephemeral Credential Envelopes, AES-256-GCM encryption, and secret redaction."""
from backend.app.security import (
    encrypt_credential_payload, decrypt_credential_payload, sanitize_audit_details
)
from backend.app.models import ProvisioningTask, AuditLog


def test_aes_256_gcm_envelope_encryption_roundtrip():
    """Verify AES-256-GCM encryption and decryption of credentials."""
    payload = {"username": "student101", "password": "SecretP@ssword2026!"}
    cipher_b64, nonce_hex, tag_hex = encrypt_credential_payload(payload)

    # Decrypt
    decrypted = decrypt_credential_payload(cipher_b64, nonce_hex, tag_hex)
    assert decrypted == payload

    # Tampered tag should fail decryption
    tampered_tag = "0" * 32
    failed = decrypt_credential_payload(cipher_b64, nonce_hex, tampered_tag)
    assert failed is None


def test_secret_redaction_in_audit_details():
    """Verify passwords, tokens, and credentials are automatically redacted in audit logs."""
    raw_details = {
        "username": "student101",
        "initial_password": "PlaintextPassword!",
        "new_password": "NewSecretPassword!",
        "token": "tok_abcdef12345",
        "nested": {
            "user_credential": "super_secret_value",
            "safe_field": "192.168.1.101"
        }
    }
    sanitized = sanitize_audit_details(raw_details)

    assert sanitized["username"] == "student101"
    assert sanitized["initial_password"] == "[REDACTED]"
    assert sanitized["new_password"] == "[REDACTED]"
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["nested"]["user_credential"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == "192.168.1.101"


def test_no_plaintext_passwords_stored_in_database(client, auth_headers, sample_devices, db):
    """Ensure no plaintext passwords exist in ProvisioningTask, AuditLog, or Device tables."""
    client.post("/api/v1/provisioning/bulk", headers=auth_headers, json={
        "batch_name": "Redaction-Check",
        "items": [{
            "hostname": "LAB-PC-01",
            "username": "student_redact",
            "initial_password": "SuperSecretRedactedPass999!",
            "role": "Student",
            "force_password_change": True
        }]
    })

    # Check ProvisioningTask records
    tasks = db.query(ProvisioningTask).all()
    for t in tasks:
        # None of the task fields should contain the secret password
        assert "SuperSecretRedactedPass999!" not in str(t.target_username)
        assert "SuperSecretRedactedPass999!" not in str(t.error_message or "")
        assert "SuperSecretRedactedPass999!" not in str(t.result_details_json or "")

    # Check AuditLog records
    logs = db.query(AuditLog).all()
    for log in logs:
        assert "SuperSecretRedactedPass999!" not in str(log.details_json or "")
