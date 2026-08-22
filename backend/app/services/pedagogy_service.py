"""Didaktik aus Quellen für API und UI."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.ai.generate import _vision_extract_image_source
from app.ai.source_pedagogy import (
    build_pedagogy_digest,
    collect_pedagogy_from_unit_sources,
    has_pedagogy_content,
    pedagogy_from_analysis_blob,
)
from app.models import User
from app.services.profile_service import resolve_prefs_for_profile
from app.services.unit_service import _dec_source, _get_unit_or_404
from app.services.user_service import get_user_settings


def _pedagogy_quality(profile: dict) -> dict:
    methods = profile.get("methods") or []
    worked = profile.get("worked_examples") or []
    worked_with_steps = sum(
        1
        for item in worked
        if isinstance(item, dict) and isinstance(item.get("steps"), list) and item.get("steps")
    )
    patterns = profile.get("exercise_patterns") or []
    method_count = len(methods) if isinstance(methods, list) else 0
    pattern_count = len(patterns) if isinstance(patterns, list) else 0
    if method_count >= 2 and worked_with_steps >= 1:
        level = "good"
    elif method_count >= 1 or pattern_count >= 1:
        level = "partial"
    else:
        level = "low"
    return {
        "level": level,
        "method_count": method_count,
        "worked_with_steps": worked_with_steps,
        "pattern_count": pattern_count,
    }


def get_unit_pedagogy(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    profile = collect_pedagogy_from_unit_sources(unit.sources)
    by_source: list[dict] = []
    for source in unit.sources or []:
        pedagogy = pedagogy_from_analysis_blob(source.analysis_encrypted)
        meta = _dec_source(source)
        by_source.append(
            {
                **meta,
                "has_pedagogy": has_pedagogy_content(pedagogy),
                "method_count": len(pedagogy.get("methods") or []),
                "exercise_count": len(pedagogy.get("exercises") or []),
            }
        )
    return {
        "has_pedagogy": has_pedagogy_content(profile),
        "digest": build_pedagogy_digest(profile),
        "profile": profile,
        "quality": _pedagogy_quality(profile),
        "sources": by_source,
        "source_count": len(unit.sources or []),
    }


def extract_unit_pedagogy(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)
    refreshed = 0
    for source in unit.sources or []:
        if source.kind != "image" or not source.storage_path or source.purged_at is not None:
            continue
        from app.core.crypto import decrypt_text_master

        name = (
            decrypt_text_master(source.original_name_encrypted)
            if source.original_name_encrypted
            else "image"
        )
        result = _vision_extract_image_source(
            db=db, unit=unit, source=source, label=name, prefs=prefs
        )
        if result and not str(result).startswith("("):
            refreshed += 1
    db.flush()
    payload = get_unit_pedagogy(db, user, unit_id)
    payload["refreshed_sources"] = refreshed
    return payload
