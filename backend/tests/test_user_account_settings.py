"""Account-Settings (Login-E-Mail, Passwort-Hilfen)."""

import base64
import os
import uuid
from unittest.mock import MagicMock

import pytest

from app.core.auth.passwords import hash_email, hash_password, verify_password
from app.core.crypto import generate_salt
from app.models import User
from app.services.user_service import (
    AuthError,
    _account_display_name,
    _login_email,
    _write_account_display_name,
    _write_login_email,
    admin_reset_password,
    assign_login_email,
    change_own_password,
)


@pytest.fixture
def env_keys(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-pytest-only-32chars!!")
    from app.config import Settings

    settings = Settings()
    monkeypatch.setattr("app.config.settings", settings)
    monkeypatch.setattr("app.core.crypto.encryption.settings", settings)


def _user(email: str = "max@example.com", *, tenant_id: uuid.UUID | None = None) -> User:
    return User(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        email_hash=hash_email(email),
        password_hash=hash_password("old-password-12"),
        encryption_salt=generate_salt(),
        encrypted_profile=None,
        is_admin=True,
    )


def test_login_email_survives_display_name_update(env_keys):
    user = _user()
    _write_login_email(user, "max@example.com")
    _write_account_display_name(user, "Max")
    assert _login_email(user) == "max@example.com"
    assert _account_display_name(user) == "Max"


def test_assign_login_email_requires_hash_match(env_keys):
    user = _user("a@b.c")
    assign_login_email(user, "a@b.c")
    assert _login_email(user) == "a@b.c"
    with pytest.raises(AuthError) as exc:
        assign_login_email(user, "wrong@b.c")
    assert exc.value.code == "invalid_email"


def test_change_own_password(env_keys):
    user = _user()
    db = MagicMock()
    change_own_password(db, user, current_password="old-password-12", new_password="new-password-12")
    assert verify_password(user.password_hash, "new-password-12")


def test_admin_reset_password_with_email(env_keys):
    actor = _user("admin@example.com")
    target = _user("child@example.com", tenant_id=actor.tenant_id)
    db = MagicMock()
    admin_reset_password(
        db,
        actor,
        target,
        new_password="fresh-password1",
        email="child@example.com",
    )
    assert _login_email(target) == "child@example.com"
    assert verify_password(target.password_hash, "fresh-password1")
