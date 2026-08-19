"""Passwort-Hashing mit Argon2id."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def hash_email(email: str) -> str:
    """Deterministischer Lookup-Hash für E-Mail (kein Klartext in DB)."""
    normalized = email.strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def generate_recovery_code() -> str:
    """8-stelliger Recovery-Code, gruppiert 4-4."""
    raw = secrets.token_hex(4).upper()
    return f"{raw[:4]}-{raw[4:]}"
