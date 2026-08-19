import base64
import os

import pytest

from app.core.auth import hash_email, hash_password, verify_password
from app.core.crypto import (
    DataClassification,
    decrypt_text,
    decrypt_text_master,
    derive_user_key,
    encrypt_text,
    encrypt_text_master,
    generate_salt,
)


@pytest.fixture
def master_key_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", key)
    # Settings-Cache zurücksetzen
    from app.config import Settings

    monkeypatch.setattr("app.config.settings", Settings())
    monkeypatch.setattr("app.core.crypto.encryption.settings", Settings())


def test_password_hash_roundtrip():
    hashed = hash_password("SicheresPasswort123!")
    assert verify_password(hashed, "SicheresPasswort123!")
    assert not verify_password(hashed, "falsch")


def test_email_hash_deterministic():
    assert hash_email("User@Example.com") == hash_email("user@example.com")


def test_user_key_derivation_deterministic():
    salt = generate_salt()
    k1 = derive_user_key("pass", salt, "a@b.c")
    k2 = derive_user_key("pass", salt, "a@b.c")
    k3 = derive_user_key("other", salt, "a@b.c")
    assert k1 == k2
    assert k1 != k3


def test_master_key_encrypt_roundtrip(master_key_env):
    blob = encrypt_text_master("Projekt Alpha")
    assert decrypt_text_master(blob) == "Projekt Alpha"


def test_user_key_encrypt_roundtrip():
    salt = generate_salt()
    key = derive_user_key("geheim", salt, "user@test.local")
    blob = encrypt_text("Profildaten", key)
    assert decrypt_text(blob, key) == "Profildaten"


def test_classification_levels():
    assert DataClassification.PUBLIC.requires_master_key is False
    assert DataClassification.INTERNAL.requires_master_key is True
    assert DataClassification.SECRET.requires_user_key is True
