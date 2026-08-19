"""TOTP (2FA) – Secret-Generierung und Verifikation."""

import pyotp

from app.core.crypto import decrypt_with_master_key, encrypt_with_master_key

APP_NAME = "LearnAI"


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def encrypt_totp_secret(secret: str) -> bytes:
    return encrypt_with_master_key(secret.encode("utf-8"))


def decrypt_totp_secret(blob: bytes) -> str:
    return decrypt_with_master_key(blob).decode("utf-8")


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=APP_NAME)


def verify_totp(secret: str, code: str) -> bool:
    if not code or not code.strip().isdigit():
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
