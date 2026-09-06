"""Snapshot der beim Generieren verwendeten KI-Modelle (Phase 2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.crypto_json import decrypt_json, encrypt_json


def build_ai_run_snapshot(
    *,
    tasks: dict[str, dict[str, str]],
    stats: dict[str, Any] | None = None,
    triggered_by: str | None = None,
    status: str = "done",
) -> dict[str, Any]:
    clean_tasks: dict[str, dict[str, str]] = {}
    for key, row in (tasks or {}).items():
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip().lower()
        model = str(row.get("model") or "").strip() or "(auto)"
        if provider:
            clean_tasks[str(key)] = {"provider": provider, "model": model}
    return {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "tasks": clean_tasks,
        "stats": dict(stats or {}),
        "triggered_by": triggered_by,
    }


def last_ai_run_from_recon(recon: dict | None) -> dict[str, Any] | None:
    if not isinstance(recon, dict):
        return None
    raw = recon.get("last_ai_run")
    if not isinstance(raw, dict):
        return None
    if not raw.get("tasks"):
        return None
    return raw


def persist_last_ai_run(db, unit_id: str | uuid.UUID, snapshot: dict[str, Any] | None) -> None:
    if not snapshot or not snapshot.get("tasks"):
        return
    from app.models import LearningRecord

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == uuid.UUID(str(unit_id))).first()
    if not record:
        return
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}
    recon["last_ai_run"] = snapshot
    record.reconstruction_encrypted = encrypt_json(recon)


def resolve_generation_ai_tasks(
    target_prefs: dict,
    fallback_prefs: dict | None,
    task_type: str,
    *,
    provider_override: str | None = None,
    source_count: int = 0,
    mixed_result: dict | None = None,
) -> dict[str, dict[str, str]]:
    """Welche Provider/Modelle für einen Generierungslauf vorgesehen bzw. genutzt wurden."""
    from app.ai.catalog import resolve_task_ai_for_unit
    from app.ai.task_types import AI_TASK_FOR_UNIT

    main_key = AI_TASK_FOR_UNIT.get(str(task_type or "mixed"), "mixed")
    tasks: dict[str, dict[str, str]] = {}

    if mixed_result and str(mixed_result.get("provider") or "").strip():
        tasks[main_key] = {
            "provider": str(mixed_result["provider"]).strip().lower(),
            "model": str(mixed_result.get("model") or "").strip() or "(auto)",
        }
    else:
        provider, model = resolve_task_ai_for_unit(
            target_prefs,
            fallback_prefs,
            main_key,
            override=provider_override,
        )
        tasks[main_key] = {"provider": provider, "model": model or "(auto)"}

    if source_count > 0:
        vp, vm = resolve_task_ai_for_unit(target_prefs, fallback_prefs, "vision")
        tasks["vision"] = {"provider": vp, "model": vm or "(auto)"}

    return tasks
