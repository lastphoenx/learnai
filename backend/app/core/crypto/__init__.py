"""Zentrale Crypto-Fassade – ein Einstiegspunkt für alle Verschlüsselungsoperationen."""

from app.core.crypto.classification import DataClassification, classification_label
from app.core.crypto.encryption import (
    CryptoError,
    decrypt,
    decrypt_text,
    decrypt_text_master,
    decrypt_with_master_key,
    encrypt,
    encrypt_text,
    encrypt_text_master,
    encrypt_with_master_key,
    generate_master_key_b64,
)
from app.core.crypto.key_derivation import derive_user_key, generate_salt

__all__ = [
    "CryptoError",
    "DataClassification",
    "classification_label",
    "decrypt",
    "decrypt_text",
    "decrypt_text_master",
    "decrypt_with_master_key",
    "derive_user_key",
    "encrypt",
    "encrypt_text",
    "encrypt_text_master",
    "encrypt_with_master_key",
    "generate_master_key_b64",
    "generate_salt",
]
