"""Benutzer-Registrierung, Login und 2FA."""

import json

from sqlalchemy.orm import Session

from app.ai.catalog import TASK_KEYS
from app.core.auth.challenges import consume_login_challenge, create_login_challenge
from app.core.auth.passwords import hash_email, hash_password, verify_password
from app.core.auth.recovery import generate_recovery_codes, verify_and_consume_recovery_code
from app.core.auth.totp import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    provisioning_uri,
    verify_totp,
)
from app.core.crypto import derive_user_key, encrypt_text, generate_salt
from app.core.tenant import get_default_tenant
from app.models import User
from app.services.audit import log_event
from app.services.crypto_json import decrypt_json, encrypt_json


class AuthError(Exception):
    def __init__(self, message: str, code: str = "auth_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _encrypt_profile(display_name: str, password: str, salt: bytes, email: str) -> bytes:
    key = derive_user_key(password, salt, email)
    payload = json.dumps({"display_name": display_name}).encode("utf-8")
    return encrypt_text(payload.decode("utf-8"), key)


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str = "",
    is_admin: bool = False,
) -> User:
    tenant = get_default_tenant(db)
    email_h = hash_email(email)
    if (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.email_hash == email_h)
        .first()
    ):
        raise AuthError("E-Mail bereits registriert", "email_taken")

    salt = generate_salt()
    profile = _encrypt_profile(display_name or email.split("@")[0], password, salt, email)
    user = User(
        tenant_id=tenant.id,
        email_hash=email_h,
        password_hash=hash_password(password),
        encryption_salt=salt,
        encrypted_profile=profile,
        is_admin=is_admin,
    )
    db.add(user)
    db.flush()
    if display_name.strip() or email:
        update_user_settings(db, user, display_name=display_name.strip() or email.split("@")[0])
    log_event(
        db,
        tenant_id=tenant.id,
        actor_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=user.id,
    )
    return user


def authenticate_password(db: Session, email: str, password: str) -> User:
    tenant = get_default_tenant(db)
    user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.email_hash == hash_email(email))
        .first()
    )
    if not user or not user.is_active:
        raise AuthError("Ungültige Anmeldedaten", "invalid_credentials")
    if not verify_password(user.password_hash, password):
        raise AuthError("Ungültige Anmeldedaten", "invalid_credentials")
    return user


def start_2fa_challenge(db: Session, user: User) -> str:
    return create_login_challenge(db, user.id)


def complete_2fa_login(
    db: Session,
    challenge_token: str,
    *,
    totp_code: str | None = None,
    recovery_code: str | None = None,
) -> User:
    challenge = consume_login_challenge(db, challenge_token)
    if not challenge:
        raise AuthError("2FA-Challenge ungültig oder abgelaufen", "invalid_challenge")

    user = db.get(User, challenge.user_id)
    if not user or not user.is_active or not user.totp_enabled:
        raise AuthError("Benutzer ungültig", "invalid_user")

    verified = False
    if totp_code and user.totp_secret_encrypted:
        secret = decrypt_totp_secret(user.totp_secret_encrypted)
        verified = verify_totp(secret, totp_code)
    elif recovery_code:
        verified = verify_and_consume_recovery_code(db, user.id, recovery_code)

    if not verified:
        raise AuthError("Ungültiger 2FA- oder Recovery-Code", "invalid_2fa")

    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="auth.2fa_success",
        resource_type="user",
        resource_id=user.id,
    )
    return user


def setup_totp(db: Session, user: User, email: str) -> tuple[str, str]:
    if user.totp_enabled:
        raise AuthError("2FA ist bereits aktiv", "totp_already_enabled")
    secret = generate_totp_secret()
    user.totp_secret_encrypted = encrypt_totp_secret(secret)
    db.flush()
    return secret, provisioning_uri(secret, email)


def confirm_totp(db: Session, user: User, code: str, email: str) -> list[str]:
    if user.totp_enabled:
        raise AuthError("2FA ist bereits aktiv", "totp_already_enabled")
    if not user.totp_secret_encrypted:
        raise AuthError("2FA-Setup nicht gestartet", "totp_not_started")

    secret = decrypt_totp_secret(user.totp_secret_encrypted)
    if not verify_totp(secret, code):
        raise AuthError("Ungültiger TOTP-Code", "invalid_totp")

    user.totp_enabled = True
    # Alte Recovery-Codes ersetzen
    for old in list(user.recovery_codes):
        db.delete(old)
    codes = generate_recovery_codes(db, user.id)
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="auth.2fa_enabled",
        resource_type="user",
        resource_id=user.id,
    )
    return codes


def user_public_dict(user: User) -> dict:
    prefs = get_user_settings(user)
    return {
        "id": str(user.id),
        "is_admin": user.is_admin,
        "totp_enabled": user.totp_enabled,
        "totp_required": user.totp_required,
        "must_enroll_2fa": bool(user.totp_required and not user.totp_enabled),
        "display_name": prefs.get("display_name") or "",
        "llm_provider": prefs.get("llm_provider") or "",
        "llm_model": prefs.get("llm_model") or "",
        "by_task": prefs.get("by_task") or {},
    }


def _normalize_by_task(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for key, row in raw.items():
        if key not in TASK_KEYS or not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip().lower()
        if provider in {"", "default"}:
            provider = ""
        elif provider not in {"ollama", "openai", "anthropic"}:
            continue
        out[str(key)] = {"provider": provider, "model": str(row.get("model") or "").strip()[:80]}
    return out


def get_user_settings(user: User) -> dict:
    data = decrypt_json(user.settings_encrypted) if user.settings_encrypted else None
    if not isinstance(data, dict):
        data = {}
    provider = str(data.get("llm_provider") or "").strip().lower()
    if provider and provider not in {"ollama", "openai", "anthropic"}:
        provider = ""
    return {
        "display_name": str(data.get("display_name") or "").strip()[:80],
        "llm_provider": provider,
        "llm_model": str(data.get("llm_model") or "").strip()[:80],
        "by_task": _normalize_by_task(data.get("by_task")),
    }


def update_user_settings(
    db: Session,
    user: User,
    *,
    display_name: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    by_task: dict | None = None,
) -> dict:
    current = get_user_settings(user)
    if display_name is not None:
        current["display_name"] = display_name.strip()[:80]
    if llm_provider is not None:
        name = llm_provider.strip().lower()
        if name in {"", "default"}:
            current["llm_provider"] = ""
        elif name in {"ollama", "openai", "anthropic"}:
            current["llm_provider"] = name
        else:
            raise AuthError("Unbekannter KI-Provider", "bad_provider")
    if llm_model is not None:
        current["llm_model"] = llm_model.strip()[:80]
    if by_task is not None:
        current["by_task"] = _normalize_by_task(by_task)
    user.settings_encrypted = encrypt_json(current)
    db.flush()
    return get_user_settings(user)


def set_totp_required(db: Session, actor: User, target: User, required: bool) -> User:
    if actor.tenant_id != target.tenant_id:
        raise AuthError("Benutzer nicht gefunden", "not_found")
    target.totp_required = required
    log_event(
        db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        action="auth.totp_required_set",
        resource_type="user",
        resource_id=target.id,
        detail="on" if required else "off",
    )
    return target


def list_users_admin(db: Session, actor: User) -> list[dict]:
    rows = (
        db.query(User)
        .filter(User.tenant_id == actor.tenant_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return [
        {
            **user_public_dict(u),
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


def admin_create_user(
    db: Session,
    actor: User,
    *,
    email: str,
    password: str,
    display_name: str = "",
    is_admin: bool = False,
    totp_required: bool = False,
) -> User:
    user = register_user(
        db,
        email=email,
        password=password,
        display_name=display_name,
        is_admin=is_admin,
    )
    user.totp_required = totp_required
    if display_name.strip():
        update_user_settings(db, user, display_name=display_name)
    log_event(
        db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        action="user.admin_create",
        resource_type="user",
        resource_id=user.id,
    )
    db.flush()
    return user
