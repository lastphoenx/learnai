"""Aufgelöste KI-Konfiguration: Profil + Katalog-Fallbacks (Diagnose)."""

from __future__ import annotations

from app.ai.catalog import TASK_KEYS, catalog_with_resolved, default_for, local_hints, resolve_task_ai
from app.ai.ollama_match import first_ollama_hint, match_ollama_hints
from app.ai.providers import ollama_status
from app.config import settings


UNIT_GENERATE_TASKS = ("vision", "mixed")


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
) -> dict:
    prefs = prefs if isinstance(prefs, dict) else {}
    ollama = ollama_status()
    installed = ollama.get("models") or []
    tasks: dict[str, dict] = {}
    for task_key in sorted(TASK_KEYS):
        if fallback_prefs is not None:
            from app.ai.catalog import resolve_task_ai_for_unit

            provider, model = resolve_task_ai_for_unit(
                prefs, fallback_prefs, task_key, installed_ollama=installed
            )
        else:
            provider, model = resolve_task_ai(prefs, task_key, installed_ollama=installed)
        tasks[task_key] = {
            "provider": provider,
            "profile_model": model or None,
            "effective_model": _effective_model(provider, model, task_key, installed),
            "recommended": match_ollama_hints(local_hints(task_key), installed, limit=3)
            if provider == "ollama"
            else [],
        }
    unit_generate = {key: tasks[key] for key in UNIT_GENERATE_TASKS if key in tasks}
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
    }
