"""Didaktik aus Quellen für API und UI."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.generate import _vision_extract_image_source
from app.ai.source_pedagogy import (
    PEDAGOGY_ANALYSIS_VERSION,
    blob_analysis_is_current,
    blob_analysis_is_structured,
    blob_extracted_at,
    build_pedagogy_digest,
    collect_pedagogy_from_unit_sources,
    has_pedagogy_content,
    pedagogy_from_analysis_blob,
)
from app.core.pedagogy_labels import sanitize_pedagogy_field
from app.models import User
from app.services.profile_service import resolve_unit_ai_prefs
from app.services.unit_service import _dec_source, _get_unit_or_404


def _pedagogy_quality(profile: dict, *, focus_group: str | None = None) -> dict:
    from app.core.focus_groups import normalize_focus_group

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
    key_terms = len(profile.get("key_terms") or [])
    assignments = len(profile.get("assignments") or [])
    group = normalize_focus_group(focus_group)

    if group == "nmg":
        if key_terms >= 4 and assignments >= 1:
            level = "good"
        elif key_terms >= 2 or assignments >= 1 or pattern_count >= 1:
            level = "partial"
        else:
            level = "low"
        return {
            "level": level,
            "method_count": method_count,
            "methods_with_when": methods_with_when,
            "worked_with_steps": worked_with_steps,
            "pattern_count": pattern_count,
            "key_term_count": key_terms,
            "assignment_count": assignments,
        }

    if method_count >= 2 and worked_with_steps >= 1 and methods_with_when >= 1:
        level = "good"
    elif method_count >= 1 or pattern_count >= 1 or key_terms >= 2:
        level = "partial"
    else:
        level = "low"
    return {
        "level": level,
        "method_count": method_count,
        "methods_with_when": methods_with_when,
        "worked_with_steps": worked_with_steps,
        "pattern_count": pattern_count,
        "key_term_count": key_terms,
        "assignment_count": assignments,
    }


def pedagogy_extract_snapshot(
    *,
    refreshed: int,
    skipped_no_file: int,
    structured_count: int = 0,
    raw_only_count: int = 0,
    quality_level: str | None = None,
) -> dict:
    if refreshed <= 0:
        status = "failed"
        message = "Keine Quelle konnte neu analysiert werden."
    elif raw_only_count > 0 and structured_count > 0:
        status = "partial"
        message = f"{structured_count} strukturiert, {raw_only_count} nur Rohtext"
        if skipped_no_file > 0:
            message += f", {skipped_no_file} ohne Bilddatei"
        message += "."
    elif raw_only_count > 0:
        status = "partial"
        message = (
            f"{refreshed} Quelle(n) neu analysiert, "
            f"{raw_only_count} nur Rohtext (kein parsebares JSON)."
        )
        if skipped_no_file > 0:
            message += f" {skipped_no_file} ohne Bilddatei."
    elif skipped_no_file > 0:
        status = "partial"
        message = f"{refreshed} Quelle(n) neu analysiert, {skipped_no_file} ohne Bilddatei."
    else:
        status = "success"
        message = f"{refreshed} Quelle(n) neu analysiert."
    snapshot = {
        "status": status,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "refreshed_sources": refreshed,
        "skipped_no_file": skipped_no_file,
        "structured_sources": structured_count,
        "raw_only_sources": raw_only_count,
    }
    if quality_level:
        snapshot["quality_level"] = quality_level
    return snapshot


def persist_last_pedagogy(db: Session, unit_id: uuid.UUID, snapshot: dict) -> None:
    from app.models import LearningRecord
    from app.services.crypto_json import decrypt_json, encrypt_json

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit_id).first()
    if not record:
        return
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}
    recon["last_pedagogy"] = snapshot
    record.reconstruction_encrypted = encrypt_json(recon)


def last_pedagogy_from_recon(recon: dict | None) -> dict | None:
    if not isinstance(recon, dict):
        return None
    snap = recon.get("last_pedagogy")
    if not isinstance(snap, dict) or not snap.get("updated_at"):
        return None
    return snap


def _last_extract_payload(
    db: Session,
    unit,
    *,
    analysis_current: bool,
    has_pedagogy: bool,
) -> dict | None:
    from app.models import LearningRecord
    from app.services.crypto_json import decrypt_json

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    snapshot = last_pedagogy_from_recon(recon if isinstance(recon, dict) else None)
    blob_times = [blob_extracted_at(source.analysis_encrypted) for source in unit.sources or []]
    blob_times = [stamp for stamp in blob_times if stamp]
    updated_at = (snapshot or {}).get("updated_at") or (max(blob_times) if blob_times else None)
    if not updated_at:
        return None
    status = str((snapshot or {}).get("status") or "success")
    if has_pedagogy and not analysis_current:
        status = "stale"
    out: dict = {
        "status": status,
        "updated_at": updated_at,
    }
    if snapshot:
        if snapshot.get("message"):
            out["message"] = snapshot["message"]
        if snapshot.get("refreshed_sources") is not None:
            out["refreshed_sources"] = snapshot["refreshed_sources"]
        if snapshot.get("skipped_no_file") is not None:
            out["skipped_no_file"] = snapshot["skipped_no_file"]
        if snapshot.get("structured_sources") is not None:
            out["structured_sources"] = snapshot["structured_sources"]
        if snapshot.get("raw_only_sources") is not None:
            out["raw_only_sources"] = snapshot["raw_only_sources"]
    return out


def get_unit_pedagogy(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    from app.ai.subject_focus import detect_focus_group

    focus_group = detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or ""))
    profile = collect_pedagogy_from_unit_sources(unit.sources, focus_group=focus_group)
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
                "structured": blob_analysis_is_structured(source.analysis_encrypted),
                "analysis_current": current,
                "method_count": len(pedagogy.get("methods") or []),
                "exercise_count": len(pedagogy.get("exercises") or []),
            }
        )
    focus_group = detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or ""))
    analysis_current = bool(analysis_blobs) and analysis_current_count == analysis_blobs
    has_pedagogy = has_pedagogy_content(profile)
    payload = {
        "has_pedagogy": has_pedagogy,
        "digest": build_pedagogy_digest(profile),
        "profile": profile,
        "quality": _pedagogy_quality(profile, focus_group=focus_group),
        "sources": by_source,
        "source_count": len(unit.sources or []),
        "can_reread": can_reread,
        "skipped_no_file": skipped_no_file,
        "analysis_current": analysis_current,
        "analysis_version": PEDAGOGY_ANALYSIS_VERSION,
        "image_count": image_count,
    }
    last_extract = _last_extract_payload(
        db, unit, analysis_current=analysis_current, has_pedagogy=has_pedagogy
    )
    if last_extract:
        payload["last_extract"] = last_extract
    return payload


def extract_unit_pedagogy(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    """Vision für alle Bildquellen erneut ausführen (ignoriert den Didaktik-Cache)."""
    unit = _get_unit_or_404(db, user, unit_id)
    target_prefs, fallback_prefs = resolve_unit_ai_prefs(db, user, unit.profile_id)
    refreshed = 0
    structured_count = 0
    raw_only_count = 0
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
            db=db,
            unit=unit,
            source=source,
            label=name,
            prefs=target_prefs,
            fallback_prefs=fallback_prefs,
        )
        if result and result.ok and not result.summary.startswith("("):
            refreshed += 1
            if result.structured:
                structured_count += 1
            else:
                raw_only_count += 1
    db.flush()
    payload = get_unit_pedagogy(db, user, unit_id)
    payload["refreshed_sources"] = refreshed
    payload["structured_sources"] = structured_count
    payload["raw_only_sources"] = raw_only_count
    payload["skipped_no_file"] = skipped_no_file
    quality_level = (payload.get("quality") or {}).get("level")
    snapshot = pedagogy_extract_snapshot(
        refreshed=refreshed,
        skipped_no_file=skipped_no_file,
        structured_count=structured_count,
        raw_only_count=raw_only_count,
        quality_level=str(quality_level) if quality_level else None,
    )
    persist_last_pedagogy(db, unit_id, snapshot)
    payload["last_extract"] = _last_extract_payload(
        db,
        unit,
        analysis_current=bool(payload.get("analysis_current")),
        has_pedagogy=bool(payload.get("has_pedagogy")),
    ) or snapshot
    return payload
