"""Aufgelöste KI-Konfiguration: Profil + Katalog-Fallbacks (Diagnose)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.catalog import (
    QUALITY_TASK_KEYS,
    TASK_KEYS,
    catalog_with_resolved,
    default_for,
    has_explicit_task_setting,
    local_hints,
    resolve_task_ai,
)
from app.ai.ollama_match import first_ollama_hint, match_ollama_hints
from app.ai.providers import ollama_status
from app.config import settings


UNIT_GENERATE_TASKS = ("vision", "mixed")


@dataclass(frozen=True)
class EffectiveAiContext:
    has_unit_profile: bool = False
    child_label: str | None = None
    adult_label: str | None = None
    unit_provider_override: str | None = None


def task_setting_source(
    *,
    target_prefs: dict,
    fallback_prefs: dict | None,
    task_key: str,
    ctx: EffectiveAiContext | None = None,
) -> tuple[str, str]:
    """Liefert (source_key, source_label) für die Herkunft einer Task-Einstellung."""
    ctx = ctx or EffectiveAiContext()
    child_label = (ctx.child_label or "Kind").strip() or "Kind"
    adult_label = (ctx.adult_label or "Erwachsenen").strip() or "Erwachsenen"
    target = target_prefs if isinstance(target_prefs, dict) else {}
    fallback = fallback_prefs if isinstance(fallback_prefs, dict) else None

    override = (ctx.unit_provider_override or "").strip().lower()
    if override and task_key == "mixed":
        return "unit", f"Einheit (Provider {override})"

    inherited = (
        fallback is not None
        and task_key in QUALITY_TASK_KEYS
        and not has_explicit_task_setting(target, task_key)
    )
    if inherited:
        if has_explicit_task_setting(fallback, task_key):
            return "adult", f"Vererbt von {adult_label}"
        if str(fallback.get("llm_provider") or "").strip():
            return "adult", f"Vererbt von {adult_label} (Standard)"
        return "catalog", "Katalog-Empfehlung"

    if has_explicit_task_setting(target, task_key):
        if ctx.has_unit_profile:
            return "child", f"Profil {child_label}"
        return "adult", f"{adult_label} (Aufgabe)"

    if task_key not in {"vision", "tts"} and str(target.get("llm_provider") or "").strip():
        if ctx.has_unit_profile:
            return "child", f"Profil {child_label} (Standard)"
        return "adult", f"{adult_label} (Standard)"

    if not target and not fallback:
        return "catalog", "Katalog / Server"

    return "catalog", "Katalog-Empfehlung"


def _effective_model(provider: str, model: str | None, task_key: str, installed: list[str]) -> str:
    name = (model or "").strip()
    if name:
        return name
    if provider == "ollama":
        if task_key == "vision" and settings.ollama_vision_model.strip():
            return settings.ollama_vision_model.strip()
        if task_key != "vision" and task_key != "tts" and settings.ollama_model.strip():
            return settings.ollama_model.strip()
        auto = first_ollama_hint(local_hints(task_key), installed)
        if auto:
            return f"{auto} (Katalog)"
        return "(auto — kein passendes Ollama-Modell)"
    rec = default_for(task_key, installed_ollama=installed)
    return rec.get("model") or "(leer)"


def effective_ai_config(
    prefs: dict | None,
    *,
    fallback_prefs: dict | None = None,
    context: EffectiveAiContext | None = None,
) -> dict:
    prefs = prefs if isinstance(prefs, dict) else {}
    ollama = ollama_status()
    installed = ollama.get("models") or []
    tasks: dict[str, dict] = {}
    unit_override = (context.unit_provider_override if context else None) or None
    for task_key in sorted(TASK_KEYS):
        task_override = unit_override if task_key == "mixed" else None
        if fallback_prefs is not None:
            from app.ai.catalog import resolve_task_ai_for_unit

            provider, model = resolve_task_ai_for_unit(
                prefs,
                fallback_prefs,
                task_key,
                installed_ollama=installed,
                override=task_override,
            )
            source_key, source_label = task_setting_source(
                target_prefs=prefs,
                fallback_prefs=fallback_prefs,
                task_key=task_key,
                ctx=context,
            )
        else:
            provider, model = resolve_task_ai(
                prefs,
                task_key,
                installed_ollama=installed,
                override=task_override,
            )
            source_key, source_label = task_setting_source(
                target_prefs=prefs,
                fallback_prefs=None,
                task_key=task_key,
                ctx=EffectiveAiContext(
                    has_unit_profile=context.has_unit_profile if context else False,
                    child_label=context.child_label if context else None,
                    adult_label=(context.adult_label if context else None),
                    unit_provider_override=unit_override,
                ),
            )
        eff_model = _effective_model(provider, model, task_key, installed)
        env_backed = not (model or "").strip() and provider == "ollama" and (
            (task_key == "vision" and settings.ollama_vision_model.strip())
            or (task_key not in {"vision", "tts"} and settings.ollama_model.strip())
        )
        if env_backed and source_key == "catalog":
            source_key, source_label = "env", "Server (.env)"
        tasks[task_key] = {
            "provider": provider,
            "profile_model": model or None,
            "effective_model": eff_model,
            "source": source_key,
            "source_label": source_label,
            "recommended": match_ollama_hints(local_hints(task_key), installed, limit=3)
            if provider == "ollama"
            else [],
        }
    unit_generate = {key: tasks[key] for key in UNIT_GENERATE_TASKS if key in tasks}
    inheritance: dict[str, Any] | None = None
    if context and (context.has_unit_profile or fallback_prefs):
        inheritance = {
            "has_unit_profile": context.has_unit_profile,
            "child_label": context.child_label,
            "adult_label": context.adult_label,
            "unit_provider_override": context.unit_provider_override,
        }
    return {
        "env": {
            "llm_provider": settings.llm_provider,
            "ollama_url": settings.ollama_url,
            "ollama_model": settings.ollama_model or None,
            "ollama_vision_model": settings.ollama_vision_model or None,
            "ollama_chat_timeout_sec": settings.ollama_chat_timeout_sec,
            "ollama_vision_timeout_sec": settings.ollama_vision_timeout_sec,
        },
        "ollama": {
            "ok": ollama.get("ok"),
            "url": ollama.get("url"),
            "model_count": len(installed),
            "error": ollama.get("error"),
        },
        "profile": {
            "llm_provider": prefs.get("llm_provider") or None,
            "llm_model": prefs.get("llm_model") or None,
            "by_task": prefs.get("by_task") or {},
        },
        "task_catalog": catalog_with_resolved(installed),
        "tasks": tasks,
        "unit_generate": unit_generate,
        "inheritance": inheritance,
    }
