"""Freigabe von Lerneinheiten für Kinder — gekoppelt an Didaktik-Qualität."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import LearningUnit, User
from app.services.unit_service import UnitError, _get_unit_or_404


def unit_targets_child_learner(unit: LearningUnit) -> bool:
    profile = unit.profile
    return bool(unit.profile_id and profile and profile.is_child_profile)


def is_released_to_learners(unit: LearningUnit) -> bool:
    return unit.learner_released_at is not None


def assert_child_can_access_unit(user: User, unit: LearningUnit) -> None:
    if not user.is_child:
        return
    if not is_released_to_learners(unit):
        raise UnitError("Diese Einheit ist noch nicht freigegeben", "not_released")


def pedagogy_quality_level_for_unit(db: Session, unit: LearningUnit) -> str | None:
    from app.ai.source_pedagogy import collect_pedagogy_from_unit_sources
    from app.ai.subject_focus import detect_focus_group
    from app.services.pedagogy_service import _pedagogy_quality

    focus_group = detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or ""))
    profile = collect_pedagogy_from_unit_sources(unit.sources or [], focus_group=focus_group)
    return _pedagogy_quality(profile, focus_group=focus_group).get("level")


def sync_learner_release_from_quality(
    db: Session,
    unit: LearningUnit,
    quality_level: str | None,
) -> None:
    """Bei «good» auto-freigeben; bei partial/low auto-Freigabe zurücknehmen (manual bleibt)."""
    if not unit_targets_child_learner(unit):
        return
    level = str(quality_level or "").strip().lower()
    if level == "good":
        if unit.learner_release_mode != "manual":
            unit.learner_released_at = datetime.now(timezone.utc)
            unit.learner_release_mode = "auto"
    elif level in {"partial", "low"}:
        if unit.learner_release_mode != "manual":
            unit.learner_released_at = None
            unit.learner_release_mode = None
    db.flush()


def sync_learner_release_for_unit(db: Session, unit: LearningUnit) -> str | None:
    level = pedagogy_quality_level_for_unit(db, unit)
    sync_learner_release_from_quality(db, unit, level)
    return level


def attach_learner_release_fields(row: dict, unit: LearningUnit, *, quality_level: str | None = None) -> None:
    targets_child = unit_targets_child_learner(unit)
    released = is_released_to_learners(unit)
    row["learner_release"] = {
        "targets_child": targets_child,
        "released": released,
        "released_at": unit.learner_released_at.isoformat() if unit.learner_released_at else None,
        "mode": unit.learner_release_mode,
        "quality_level": quality_level,
        "auto_release_eligible": quality_level == "good",
        "pending": targets_child and not released,
    }


def set_unit_learner_release(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    released: bool,
) -> dict:
    if user.is_child:
        raise UnitError("Nur für Eltern-Accounts", "forbidden")
    unit = _get_unit_or_404(db, user, unit_id)
    if not unit_targets_child_learner(unit):
        raise UnitError("Freigabe gilt nur für Einheiten mit Kind-Profil", "invalid_profile")
    if released:
        unit.learner_released_at = datetime.now(timezone.utc)
        unit.learner_release_mode = "manual"
    else:
        unit.learner_released_at = None
        unit.learner_release_mode = None
    db.flush()
    from app.services.unit_service import get_unit

    return get_unit(db, user, unit_id)
