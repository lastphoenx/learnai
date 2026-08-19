"""Schlüsselableitung für passwort-geschützte (SECRET) Daten."""

import hashlib
import hmac
import secrets

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.config import settings

_SALT_BYTES = 32
_KEY_BYTES = 32


def generate_salt() -> bytes:
    return secrets.token_bytes(_SALT_BYTES)


def derive_user_key(password: str, salt: bytes, email: str) -> bytes:
    """
    Leitet einen 256-Bit-Verschlüsselungsschlüssel aus Passwort ab.
    Salt ist pro User zufällig; Email wird als zusätzlicher Kontext eingemischt.
  """
    context = hashlib.sha256(email.strip().lower().encode()).digest()
    combined_salt = hmac.new(salt, context, hashlib.sha256).digest()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=combined_salt,
        iterations=settings.pbkdf2_iterations,
    )
    return kdf.derive(password.encode("utf-8"))
