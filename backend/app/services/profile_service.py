"""Lerner-Profile: KI-Einstellungen je Lerner, verwaltbar durch Eltern/Admin."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.ai.catalog import TASK_KEYS
from app.ai.model_registry import pick_external_model, validate_model
from app.models import ChildGuardian, LearningProfile, User
from app.services.audit import log_event
from app.services.crypto_json import decrypt_json, encrypt_json


class ProfileError(Exception):
    def __init__(self, message: str, code: str = "profile_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _normalize_settings(raw: dict | None) -> dict:
    data = raw if isinstance(raw, dict) else {}
    provider = str(data.get("llm_provider") or "").strip().lower()
    if provider and provider not in {"ollama", "openai", "anthropic"}:
        provider = ""
    by_task: dict[str, dict[str, str]] = {}
    raw_tasks = data.get("by_task")
    if isinstance(raw_tasks, dict):
        for key, row in raw_tasks.items():
            if key not in TASK_KEYS or not isinstance(row, dict):
                continue
            p = str(row.get("provider") or "").strip().lower()
            if p in {"", "default"}:
                p = ""
            elif p not in {"ollama", "openai", "anthropic"}:
                continue
            by_task[str(key)] = {"provider": p, "model": str(row.get("model") or "").strip()[:80]}
    return {
        "display_name": str(data.get("display_name") or "").strip()[:80],
        "llm_provider": provider,
        "llm_model": str(data.get("llm_model") or "").strip()[:80],
        "by_task": by_task,
        "default_language": str(data.get("default_language") or "de").strip()[:8] or "de",
        "target_age": str(data.get("target_age") or "").strip()[:32],
        "auto_purge_sources": bool(data.get("auto_purge_sources")),
    }


def _validate_settings(settings: dict) -> dict:
    out = _normalize_settings(settings)
    if out["llm_provider"]:
        try:
            out["llm_model"] = validate_model(out["llm_provider"], out["llm_model"], task_key="mixed")
        except ValueError as exc:
            raise ProfileError(str(exc), "invalid_model") from exc
    validated_tasks: dict[str, dict[str, str]] = {}
    for key, row in out["by_task"].items():
        provider = row.get("provider") or ""
        model = row.get("model") or ""
        if provider:
            try:
                model = validate_model(provider, model, task_key=key)
            except ValueError as exc:
                raise ProfileError(f"{key}: {exc}", "invalid_model") from exc
        validated_tasks[key] = {"provider": provider, "model": model}
    out["by_task"] = validated_tasks
    return out


def get_profile_settings(profile: LearningProfile) -> dict:
    data = decrypt_json(profile.settings_encrypted) if profile.settings_encrypted else {}
    merged = _normalize_settings(data if isinstance(data, dict) else {})
    if not merged["display_name"]:
        merged["display_name"] = profile.display_name
    return merged


def set_profile_settings(db: Session, profile: LearningProfile, settings: dict) -> dict:
    current = get_profile_settings(profile)
    incoming = _normalize_settings(settings)
    if "display_name" in settings and settings["display_name"] is not None:
        name = str(settings["display_name"]).strip()[:80]
        current["display_name"] = name
        profile.display_name = name or profile.display_name
    if "llm_provider" in settings and settings["llm_provider"] is not None:
        name = str(settings["llm_provider"]).strip().lower()
        if name in {"", "default"}:
            current["llm_provider"] = ""
        elif name not in {"ollama", "openai", "anthropic"}:
            raise ProfileError("Unbekannter KI-Provider", "bad_provider")
        else:
            current["llm_provider"] = name
    if "llm_model" in settings and settings["llm_model"] is not None:
        current["llm_model"] = str(settings["llm_model"]).strip()[:80]
    if "by_task" in settings and settings["by_task"] is not None:
        current["by_task"] = incoming["by_task"]
    for field in ("default_language", "target_age", "auto_purge_sources"):
        if field in settings and settings[field] is not None:
            current[field] = incoming[field]
    validated = _validate_settings(current)
    profile.settings_encrypted = encrypt_json(validated)
    db.flush()
    return validated


def profile_public_dict(profile: LearningProfile) -> dict:
    prefs = get_profile_settings(profile)
    return {
        "id": str(profile.id),
        "display_name": profile.display_name,
        "user_id": str(profile.user_id) if profile.user_id else None,
        "managed_by_id": str(profile.managed_by_id),
        "is_child_profile": profile.is_child_profile,
        "llm_provider": prefs.get("llm_provider") or "",
        "llm_model": prefs.get("llm_model") or "",
        "by_task": prefs.get("by_task") or {},
        "default_language": prefs.get("default_language") or "de",
        "target_age": prefs.get("target_age") or "",
        "auto_purge_sources": bool(prefs.get("auto_purge_sources")),
        "created_at": profile.created_at.isoformat(),
    }


def child_user_ids(db: Session, user: User) -> list[uuid.UUID]:
    guardian_rows = (
        db.query(ChildGuardian.child_user_id)
        .join(User, User.id == ChildGuardian.child_user_id)
        .filter(
            ChildGuardian.parent_user_id == user.id,
            User.tenant_id == user.tenant_id,
            User.is_active.is_(True),
        )
        .all()
    )
    ids = {row[0] for row in guardian_rows}
    legacy_rows = (
        db.query(User.id)
        .filter(User.tenant_id == user.tenant_id, User.parent_id == user.id, User.is_active.is_(True))
        .all()
    )
    ids.update(row[0] for row in legacy_rows)
    return list(ids)


def can_manage_profile(db: Session, actor: User, profile: LearningProfile) -> bool:
    if actor.tenant_id != profile.tenant_id:
        return False
    if actor.is_admin:
        return True
    if profile.managed_by_id == actor.id:
        return True
    if profile.user_id and profile.is_child_profile:
        if (
            db.query(ChildGuardian.id)
            .filter(
                ChildGuardian.child_user_id == profile.user_id,
                ChildGuardian.parent_user_id == actor.id,
            )
            .first()
        ):
            return True
    if profile.user_id == actor.id and not actor.is_child:
        return True
    return False


def can_view_profile_data(db: Session, actor: User, profile_id: uuid.UUID) -> bool:
    profile = db.get(LearningProfile, profile_id)
    if not profile or profile.tenant_id != actor.tenant_id:
        return False
    if can_manage_profile(db, actor, profile):
        return True
    if profile.user_id == actor.id:
        return True
    if profile.user_id:
        subject = db.get(User, profile.user_id)
        if subject and (
            subject.parent_id == actor.id
            or db.query(ChildGuardian.id)
            .filter(
                ChildGuardian.child_user_id == subject.id,
                ChildGuardian.parent_user_id == actor.id,
            )
            .first()
        ):
            return True
    return False


def accessible_profile_ids(db: Session, user: User) -> list[uuid.UUID]:
    if user.is_admin:
        rows = db.query(LearningProfile.id).filter(LearningProfile.tenant_id == user.tenant_id).all()
        return [row[0] for row in rows]
    ids: set[uuid.UUID] = set()
    if user.profile_id:
        ids.add(user.profile_id)
    managed = (
        db.query(LearningProfile.id)
        .filter(LearningProfile.tenant_id == user.tenant_id, LearningProfile.managed_by_id == user.id)
        .all()
    )
    ids.update(row[0] for row in managed)
    child_ids = child_user_ids(db, user)
    if child_ids:
        child_profiles = (
            db.query(LearningProfile.id)
            .filter(LearningProfile.tenant_id == user.tenant_id, LearningProfile.user_id.in_(child_ids))
            .all()
        )
        ids.update(row[0] for row in child_profiles)
    return list(ids)


def list_manageable_profiles(db: Session, user: User) -> list[dict]:
    ids = accessible_profile_ids(db, user)
    if not ids:
        return []
    rows = (
        db.query(LearningProfile)
        .filter(LearningProfile.id.in_(ids))
        .order_by(LearningProfile.display_name.asc())
        .all()
    )
    return [profile_public_dict(p) for p in rows if can_manage_profile(db, user, p)]


def get_profile_for_actor(db: Session, actor: User, profile_id: uuid.UUID) -> LearningProfile:
    profile = db.get(LearningProfile, profile_id)
    if not profile or profile.tenant_id != actor.tenant_id:
        raise ProfileError("Profil nicht gefunden", "not_found")
    if not can_manage_profile(db, actor, profile):
        raise ProfileError("Kein Zugriff auf dieses Profil", "forbidden")
    return profile


def create_profile(
    db: Session,
    actor: User,
    *,
    display_name: str,
    user_id: uuid.UUID | None = None,
    managed_by_id: uuid.UUID | None = None,
    is_child_profile: bool = False,
    settings: dict | None = None,
) -> LearningProfile:
    name = display_name.strip()[:80]
    if not name:
        raise ProfileError("Anzeigename fehlt", "invalid_name")
    manager = managed_by_id or actor.id
    if user_id:
        subject = db.get(User, user_id)
        if not subject or subject.tenant_id != actor.tenant_id:
            raise ProfileError("Benutzer nicht gefunden", "not_found")
    base = _normalize_settings(settings or {})
    base["display_name"] = name
    validated = _validate_settings(base)
    profile = LearningProfile(
        tenant_id=actor.tenant_id,
        display_name=name,
        settings_encrypted=encrypt_json(validated),
        managed_by_id=manager,
        user_id=user_id,
        is_child_profile=is_child_profile,
    )
    db.add(profile)
    db.flush()
    if user_id:
        subject = db.get(User, user_id)
        if subject and subject.profile_id is None:
            subject.profile_id = profile.id
    log_event(
        db,
        tenant_id=actor.tenant_id,
        actor_id=actor.id,
        action="profile.create",
        resource_type="learning_profile",
        resource_id=profile.id,
    )
    return profile


def apply_recommended_settings(db: Session, profile: LearningProfile) -> dict:
    from app.ai.catalog import catalog_public
    from app.ai.ollama_match import first_ollama_hint
    from app.ai.providers import ollama_status

    ollama_models = ollama_status().get("models") or []
    by_task: dict[str, dict[str, str]] = {}
    for item in catalog_public():
        provider = item["default_provider"]
        if provider == "ollama":
            model = first_ollama_hint(item["local"], ollama_models)
        else:
            model = pick_external_model(provider, item["external"], task_key=item["key"])
        by_task[item["key"]] = {"provider": provider, "model": model}
    return set_profile_settings(db, profile, {"by_task": by_task})


def resolve_prefs_for_profile(db: Session, profile_id: uuid.UUID | None) -> dict:
    if not profile_id:
        return {}
    profile = db.get(LearningProfile, profile_id)
    if not profile:
        return {}
    return get_profile_settings(profile)
