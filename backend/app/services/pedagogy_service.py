"""Didaktik aus Quellen für API und UI."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.ai.generate import _vision_extract_image_source
from app.ai.source_pedagogy import (
    PEDAGOGY_ANALYSIS_VERSION,
    blob_analysis_is_current,
    build_pedagogy_digest,
    collect_pedagogy_from_unit_sources,
    has_pedagogy_content,
    pedagogy_from_analysis_blob,
)
from app.core.pedagogy_labels import sanitize_pedagogy_field
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
    methods_with_when = sum(
        1
        for item in methods
        if isinstance(item, dict) and sanitize_pedagogy_field(str(item.get("when") or ""))
    )
    patterns = profile.get("exercise_patterns") or []
    method_count = len(methods) if isinstance(methods, list) else 0
    pattern_count = len(patterns) if isinstance(patterns, list) else 0
    if method_count >= 2 and worked_with_steps >= 1 and methods_with_when >= 1:
        level = "good"
    elif method_count >= 1 or pattern_count >= 1:
        level = "partial"
    else:
        level = "low"
    return {
        "level": level,
        "method_count": method_count,
        "methods_with_when": methods_with_when,
        "worked_with_steps": worked_with_steps,
        "pattern_count": pattern_count,
    }


def get_unit_pedagogy(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    profile = collect_pedagogy_from_unit_sources(unit.sources)
    by_source: list[dict] = []
    image_count = 0
    can_reread = 0
    skipped_no_file = 0
    analysis_blobs = 0
    analysis_current_count = 0
    for source in unit.sources or []:
        pedagogy = pedagogy_from_analysis_blob(source.analysis_encrypted)
        meta = _dec_source(source)
        current = source.kind != "image" or blob_analysis_is_current(source.analysis_encrypted)
        if source.kind == "image":
            image_count += 1
            if source.storage_path and source.purged_at is None:
                can_reread += 1
            else:
                skipped_no_file += 1
            if source.analysis_encrypted:
                analysis_blobs += 1
                if current:
                    analysis_current_count += 1
        by_source.append(
            {
                **meta,
                "has_pedagogy": has_pedagogy_content(pedagogy),
                "analysis_current": current,
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
        "can_reread": can_reread,
        "skipped_no_file": skipped_no_file,
        "analysis_current": bool(analysis_blobs) and analysis_current_count == analysis_blobs,
        "analysis_version": PEDAGOGY_ANALYSIS_VERSION,
        "image_count": image_count,
    }


def extract_unit_pedagogy(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    """Vision für alle Bildquellen erneut ausführen (ignoriert den Didaktik-Cache)."""
    unit = _get_unit_or_404(db, user, unit_id)
    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)
    refreshed = 0
    skipped_no_file = 0
    for source in unit.sources or []:
        if source.kind != "image":
            continue
        if not source.storage_path or source.purged_at is not None:
            skipped_no_file += 1
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
    payload["skipped_no_file"] = skipped_no_file
    return payload
