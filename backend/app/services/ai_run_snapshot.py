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
    pipeline: str | None = None,
) -> dict[str, Any]:
    clean_tasks: dict[str, dict[str, str]] = {}
    for key, row in (tasks or {}).items():
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip().lower()
        model = str(row.get("model") or "").strip() or "(auto)"
        if provider:
            clean_tasks[str(key)] = {"provider": provider, "model": model}
    snapshot: dict[str, Any] = {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "tasks": clean_tasks,
        "stats": dict(stats or {}),
        "triggered_by": triggered_by,
    }
    if pipeline:
        snapshot["pipeline"] = str(pipeline).strip()
    return snapshot


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
    vision_used: bool | None = None,
    vision_result: dict | None = None,
) -> dict[str, dict[str, str]]:
    """Welche Provider/Modelle in diesem Lauf tatsächlich genutzt wurden (nicht nur Profil)."""
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

    include_vision = vision_used if vision_used is not None else source_count > 0
    if include_vision:
        if vision_result and str(vision_result.get("provider") or "").strip():
            tasks["vision"] = {
                "provider": str(vision_result["provider"]).strip().lower(),
                "model": str(vision_result.get("model") or "").strip() or "(auto)",
            }
        else:
            vp, vm = resolve_task_ai_for_unit(target_prefs, fallback_prefs, "vision")
            tasks["vision"] = {"provider": vp, "model": vm or "(auto)"}

    return tasks


_PIPELINE_LABELS: dict[str, str] = {
    "multimodal": "Multimodal (1 Call, Gemischt-Modell + Bilder)",
    "text_digest": "Text-Digest (Vision → Text, dann Gemischt)",
    "multi_call": "Multi-Call (Vision-Digest + Plan/Kategorien)",
}


def format_pipeline_label(pipeline: str | None) -> str:
    key = str(pipeline or "").strip()
    if not key:
        return ""
    return _PIPELINE_LABELS.get(key, key)


def format_finished_at_zurich(iso: str | None) -> str:
    """ISO-Zeitstempel für UI in Europe/Zurich (de-CH)."""
    if not iso:
        return ""
    from zoneinfo import ZoneInfo

    try:
        raw = str(iso).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Europe/Zurich")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return ""


def format_last_ai_run_compact(last_run: dict[str, Any] | None) -> str | None:
    """Kompakte Zeile für Batch-Karten: Pipeline · Modell · Zeit."""
    if not isinstance(last_run, dict) or not last_run.get("tasks"):
        return None
    parts: list[str] = []
    pipeline = format_pipeline_label(str(last_run.get("pipeline") or ""))
    if pipeline:
        parts.append(pipeline)
    task_bits: list[str] = []
    for key in ("mixed", "vision"):
        row = last_run.get("tasks", {}).get(key)
        if isinstance(row, dict) and row.get("provider"):
            task_bits.append(f"{row['provider']}/{row.get('model') or '(auto)'}")
    if task_bits:
        parts.append(" · ".join(task_bits))
    finished = format_finished_at_zurich(str(last_run.get("finished_at") or "") or None)
    if finished:
        parts.append(finished)
    return " · ".join(parts) if parts else None


_TASK_LABELS: dict[str, str] = {
    "mixed": "Generierung",
    "vision": "Quellen (Vision)",
    "explain": "Erklären",
    "quiz": "Quiz",
    "practice": "Üben",
    "exam": "Prüfung",
    "vocab": "Vokabeln",
}


def format_ai_tasks_suffix(ai_tasks: dict | None) -> str:
    """Kompakte Modell-Zeile für Live-Fortschritt (z. B. « · openai gpt-4o | openai gpt-4o-mini»)."""
    if not isinstance(ai_tasks, dict) or not ai_tasks:
        return ""
    parts: list[str] = []
    for key in ("mixed", "vision"):
        row = ai_tasks.get(key)
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip()
        if not provider:
            continue
        model = str(row.get("model") or "").strip() or "(auto)"
        parts.append(f"{provider} {model}")
    if not parts:
        return ""
    return " · " + " | ".join(parts)


def format_ai_task_report_line(task_key: str, row: dict[str, str]) -> str:
    label = _TASK_LABELS.get(task_key, task_key)
    provider = str(row.get("provider") or "—")
    model = str(row.get("model") or "(auto)")
    return f"- **{label}:** {provider} · {model}"


def format_ai_tasks_report_section(
    tasks: dict[str, dict[str, str]] | None,
    *,
    heading: str,
) -> list[str]:
    if not isinstance(tasks, dict) or not tasks:
        return [f"_Kein {heading.lower()}._", ""]
    lines = [f"**{heading}:**"]
    for key in sorted(tasks.keys()):
        row = tasks.get(key)
        if isinstance(row, dict) and row.get("provider"):
            lines.append(format_ai_task_report_line(key, row))
    lines.append("")
    return lines


def adult_label_for_user(user) -> str:
    """Anzeigename des auslösenden Erwachsenen (User hat kein display_name-Feld)."""
    from app.services.user_service import _account_display_name

    name = (_account_display_name(user) or "").strip()
    if name:
        return name
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "display_name", None):
        name = str(profile.display_name).strip()
        if name:
            return name
    email = getattr(user, "email", None)
    if email:
        return str(email).split("@")[0]
    return "Erwachsenen"


def summarize_unit_ai_context(
    db,
    user,
    unit,
    record,
) -> dict[str, Any]:
    """Aktuelle Generierungs-KI + letzter Lauf für Admin/Report."""
    from app.ai.effective import EffectiveAiContext, effective_ai_config
    from app.ai.task_types import AI_TASK_FOR_UNIT
    from app.services.crypto_json import decrypt_json
    from app.services.profile_service import resolve_unit_ai_prefs
    from app.services.unit_service import get_trainer_options

    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}

    target_prefs, fallback_prefs = resolve_unit_ai_prefs(db, user, unit.profile_id)
    opts = get_trainer_options(recon) if unit.task_type == "interactive" else {}
    unit_override = None
    if isinstance(opts, dict):
        raw = opts.get("llm_provider")
        if isinstance(raw, str) and raw.strip():
            unit_override = raw.strip()

    child_label = None
    if unit.profile_id and getattr(unit, "profile", None):
        child_label = getattr(unit.profile, "display_name", None)

    ctx = EffectiveAiContext(
        has_unit_profile=bool(unit.profile_id),
        child_label=child_label,
        adult_label=adult_label_for_user(user),
        unit_provider_override=unit_override,
    )
    eff = effective_ai_config(target_prefs, fallback_prefs=fallback_prefs, context=ctx)
    main_key = AI_TASK_FOR_UNIT.get(str(unit.task_type or "mixed"), "mixed")
    gen_keys = [main_key]
    if unit.sources:
        gen_keys.append("vision")
    current: dict[str, dict[str, Any]] = {}
    for key in gen_keys:
        task_row = eff.get("tasks", {}).get(key)
        if not isinstance(task_row, dict):
            continue
        current[key] = {
            "provider": task_row.get("provider"),
            "model": task_row.get("effective_model") or task_row.get("profile_model") or "(auto)",
            "source": task_row.get("source"),
            "source_label": task_row.get("source_label"),
        }

    last_run = last_ai_run_from_recon(recon)
    return {
        "current": current,
        "last_run": last_run,
    }
