"""Kleine Helfer für verschlüsselte JSON-Felder."""

import json

from app.core.crypto import decrypt_text_master, encrypt_text_master


def encrypt_json(data: dict | list | None) -> bytes | None:
    if data is None:
        return None
    return encrypt_text_master(json.dumps(data, ensure_ascii=False))


def decrypt_json(blob: bytes | None):
    if not blob:
        return None
    return json.loads(decrypt_text_master(blob))
