"""Benutzer-Registrierung, Login und 2FA."""

import json
import uuid

from sqlalchemy.orm import Session, joinedload

from app.ai.catalog import TASK_KEYS
from app.ai.model_registry import validate_model
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
from app.models import ChildGuardian, LearningProfile, User
from app.services.audit import log_event
from app.services.crypto_json import decrypt_json, encrypt_json
from app.services.profile_service import create_profile, get_profile_settings, set_profile_settings


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
    account_name = display_name.strip() or email.split("@")[0]
    _write_account_display_name(user, account_name)
    create_profile(
        db,
        user,
        display_name=account_name,
        user_id=user.id,
        managed_by_id=user.id,
        is_child_profile=False,
    )
    db.refresh(user)
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
    from sqlalchemy.orm import joinedload

    tenant = get_default_tenant(db)
    user = (
        db.query(User)
        .options(
            joinedload(User.profile),
            joinedload(User.guardian_of),
            joinedload(User.guarded_by),
        )
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


def _write_account_display_name(user: User, name: str) -> None:
    user.settings_encrypted = encrypt_json({"display_name": name.strip()[:80]})


def _account_display_name(user: User) -> str:
    data = decrypt_json(user.settings_encrypted) if user.settings_encrypted else None
    if isinstance(data, dict):
        return str(data.get("display_name") or "").strip()[:80]
    return ""


def _ki_summary(by_task: dict) -> str:
    counts: dict[str, int] = {}
    for row in by_task.values():
        provider = str(row.get("provider") or "").strip().lower()
        if provider:
            counts[provider] = counts.get(provider, 0) + 1
    if not counts:
        return ""
    return " · ".join(f"{name} ({count})" for name, count in sorted(counts.items(), key=lambda x: -x[1]))


MAX_CHILD_GUARDIANS = 2


def guardian_parent_ids(db: Session, child: User) -> list[uuid.UUID]:
    rows = (
        db.query(ChildGuardian.parent_user_id)
        .filter(ChildGuardian.child_user_id == child.id)
        .order_by(ChildGuardian.created_at.asc())
        .all()
    )
    if rows:
        return [row[0] for row in rows]
    if child.parent_id:
        return [child.parent_id]
    return []


def is_guardian_of(db: Session, parent_id: uuid.UUID, child_id: uuid.UUID) -> bool:
    if (
        db.query(ChildGuardian.id)
        .filter(
            ChildGuardian.parent_user_id == parent_id,
            ChildGuardian.child_user_id == child_id,
        )
        .first()
    ):
        return True
    child = db.get(User, child_id)
    return bool(child and child.parent_id == parent_id)


def _validate_guardian_parents(
    db: Session,
    actor: User,
    parent_ids: list[uuid.UUID],
) -> list[User]:
    unique: list[uuid.UUID] = []
    for pid in parent_ids:
        if pid not in unique:
            unique.append(pid)
    if not unique or len(unique) > MAX_CHILD_GUARDIANS:
        raise AuthError("Es sind 1–2 Eltern erlaubt", "invalid_guardians")
    parents: list[User] = []
    for pid in unique:
        if not actor.is_admin and pid != actor.id:
            raise AuthError("Kein Zugriff", "forbidden")
        row = db.get(User, pid)
        if not row or row.tenant_id != actor.tenant_id or row.is_child:
            raise AuthError("Eltern-Account nicht gefunden", "not_found")
        parents.append(row)
    return parents


def set_child_guardians(db: Session, child: User, parents: list[User]) -> None:
    if not child.is_child:
        raise AuthError("Nur für Kinder-Accounts", "invalid_user")
    db.query(ChildGuardian).filter(ChildGuardian.child_user_id == child.id).delete()
    for parent in parents:
        db.add(ChildGuardian(parent_user_id=parent.id, child_user_id=child.id))
    child.parent_id = parents[0].id
    if child.profile_id:
        profile = db.get(LearningProfile, child.profile_id)
        if profile:
            profile.managed_by_id = parents[0].id
    db.flush()


def user_public_dict(user: User, *, parent_ids: list[str] | None = None) -> dict:
    prefs = get_user_settings(user)
    profile_name = ""
    if user.profile_id and user.profile:
        profile_name = user.profile.display_name
    child_count = 0
    if user.guardian_of:
        child_count = len({link.child_user_id for link in user.guardian_of})
    elif user.children:
        child_count = len(user.children)
    resolved_parent_ids = parent_ids
    if resolved_parent_ids is None:
        if user.guarded_by:
            resolved_parent_ids = [str(link.parent_user_id) for link in user.guarded_by]
        elif user.parent_id:
            resolved_parent_ids = [str(user.parent_id)]
        else:
            resolved_parent_ids = []
    return {
        "id": str(user.id),
        "is_admin": user.is_admin,
        "is_child": user.is_child,
        "parent_id": resolved_parent_ids[0] if resolved_parent_ids else None,
        "parent_ids": resolved_parent_ids,
        "profile_id": str(user.profile_id) if user.profile_id else None,
        "learner_name": profile_name,
        "child_count": child_count,
        "totp_enabled": user.totp_enabled,
        "totp_required": user.totp_required,
        "must_enroll_2fa": bool(user.totp_required and not user.totp_enabled),
        "display_name": _account_display_name(user) or profile_name,
        "llm_provider": prefs.get("llm_provider") or "",
        "llm_model": prefs.get("llm_model") or "",
        "by_task": prefs.get("by_task") or {},
        "ki_summary": _ki_summary(prefs.get("by_task") or {}),
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
    if user.profile_id and user.profile:
        prefs = get_profile_settings(user.profile)
        account = _account_display_name(user)
        if account:
            prefs = {**prefs, "display_name": account}
        return prefs
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
    if display_name is not None:
        _write_account_display_name(user, display_name)
    profile_payload: dict = {}
    if llm_provider is not None:
        name = llm_provider.strip().lower()
        if name in {"", "default"}:
            profile_payload["llm_provider"] = ""
        elif name in {"ollama", "openai", "anthropic"}:
            profile_payload["llm_provider"] = name
        else:
            raise AuthError("Unbekannter KI-Provider", "bad_provider")
    if llm_model is not None:
        profile_payload["llm_model"] = llm_model.strip()[:80]
    if by_task is not None:
        profile_payload["by_task"] = by_task
    if profile_payload and user.profile_id and user.profile:
        try:
            set_profile_settings(db, user.profile, profile_payload)
        except Exception as exc:
            from app.services.profile_service import ProfileError

            if isinstance(exc, ProfileError):
                raise AuthError(exc.message, exc.code) from exc
            raise
    elif profile_payload:
        current = get_user_settings(user)
        if llm_provider is not None:
            current["llm_provider"] = profile_payload.get("llm_provider", "")
        if llm_model is not None:
            current["llm_model"] = profile_payload.get("llm_model", "")
        if by_task is not None:
            current["by_task"] = _normalize_by_task(by_task)
            for key, row in current["by_task"].items():
                provider = row.get("provider") or ""
                model = row.get("model") or ""
                if provider:
                    try:
                        row["model"] = validate_model(provider, model, task_key=key)
                    except ValueError as err:
                        raise AuthError(str(err), "invalid_model") from err
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
        .options(
            joinedload(User.profile),
            joinedload(User.guardian_of),
            joinedload(User.guarded_by),
        )
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
        _write_account_display_name(user, display_name)
        if user.profile:
            user.profile.display_name = display_name.strip()[:80]
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


def create_child_user(
    db: Session,
    actor: User,
    *,
    display_name: str,
    email: str,
    password: str,
    parent_id: uuid.UUID | None = None,
    parent_ids: list[uuid.UUID] | None = None,
) -> User:
    if actor.is_child:
        raise AuthError("Kinder-Accounts dürfen keine Kinder anlegen", "forbidden")

    if parent_ids:
        parents = _validate_guardian_parents(db, actor, parent_ids)
    elif parent_id:
        parents = _validate_guardian_parents(db, actor, [parent_id])
    else:
        parents = _validate_guardian_parents(db, actor, [actor.id])
    primary = parents[0]

    tenant = get_default_tenant(db)
    email_h = hash_email(email)
    if db.query(User).filter(User.tenant_id == tenant.id, User.email_hash == email_h).first():
        raise AuthError("E-Mail bereits registriert", "email_taken")

    salt = generate_salt()
    enc = _encrypt_profile(display_name, password, salt, email)
    child = User(
        tenant_id=tenant.id,
        email_hash=email_h,
        password_hash=hash_password(password),
        encryption_salt=salt,
        encrypted_profile=enc,
        is_child=True,
        parent_id=primary.id,
    )
    db.add(child)
    db.flush()
    _write_account_display_name(child, display_name)
    profile = create_profile(
        db,
        actor,
        display_name=display_name.strip(),
        user_id=child.id,
        managed_by_id=primary.id,
        is_child_profile=True,
    )
    child.profile_id = profile.id
    set_child_guardians(db, child, parents)
    parent_detail = ",".join(str(p.id) for p in parents)
    log_event(
        db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        action="user.child_create",
        resource_type="user",
        resource_id=child.id,
        detail=f"parents={parent_detail}",
    )
    db.flush()
    return child


def update_child_guardians(
    db: Session,
    actor: User,
    child: User,
    parent_ids: list[uuid.UUID],
) -> User:
    if not actor.is_admin:
        raise AuthError("Nur Admins dürfen Eltern zuweisen", "forbidden")
    if not child.is_child:
        raise AuthError("Nur für Kinder-Accounts", "invalid_user")
    parents = _validate_guardian_parents(db, actor, parent_ids)
    set_child_guardians(db, child, parents)
    log_event(
        db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        action="user.child_guardians_update",
        resource_type="user",
        resource_id=child.id,
        detail=",".join(str(p.id) for p in parents),
    )
    return child
