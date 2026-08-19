"""AES-256-GCM Verschlüsselung für serverseitige und user-spezifische Daten."""

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

_NONCE_BYTES = 12
_KEY_BYTES = 32


class CryptoError(Exception):
    pass


def _decode_master_key() -> bytes:
    raw = settings.encryption_master_key.strip()
    if not raw:
        raise CryptoError("ENCRYPTION_MASTER_KEY ist nicht gesetzt")
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise CryptoError("ENCRYPTION_MASTER_KEY ist kein gültiges Base64") from exc
    if len(key) != _KEY_BYTES:
        raise CryptoError(f"ENCRYPTION_MASTER_KEY muss {_KEY_BYTES} Bytes sein")
    return key


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """Gibt nonce || ciphertext+tag zurück."""
    if len(key) != _KEY_BYTES:
        raise CryptoError("Schlüssel muss 32 Bytes lang sein")
    nonce = secrets.token_bytes(_NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt(blob: bytes, key: bytes) -> bytes:
    if len(blob) < _NONCE_BYTES + 16:
        raise CryptoError("Ungültiger verschlüsselter Blob")
    nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def encrypt_with_master_key(plaintext: bytes) -> bytes:
    return encrypt(plaintext, _decode_master_key())


def decrypt_with_master_key(blob: bytes) -> bytes:
    return decrypt(blob, _decode_master_key())


def encrypt_text(plaintext: str, key: bytes) -> bytes:
    return encrypt(plaintext.encode("utf-8"), key)


def decrypt_text(blob: bytes, key: bytes) -> str:
    return decrypt(blob, key).decode("utf-8")


def encrypt_text_master(plaintext: str) -> bytes:
    return encrypt_with_master_key(plaintext.encode("utf-8"))


def decrypt_text_master(blob: bytes) -> str:
    return decrypt_with_master_key(blob).decode("utf-8")


def generate_master_key_b64() -> str:
    return base64.b64encode(os.urandom(_KEY_BYTES)).decode("ascii")
