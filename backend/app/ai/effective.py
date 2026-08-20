"""Aufgelöste KI-Konfiguration: Profil + .env-Fallbacks (Diagnose)."""

from __future__ import annotations

from app.ai.catalog import TASK_KEYS, resolve_task_ai
from app.ai.providers import ollama_status
from app.config import settings

# Für Einheiten-Generierung relevant
UNIT_GENERATE_TASKS = ("vision", "mixed")


def _effective_model(provider: str, model: str | None, task_key: str) -> str:
    name = (model or "").strip()
    if name:
        return name
    if provider != "ollama":
        return name
    if task_key == "vision":
        if settings.ollama_vision_model.strip():
            return settings.ollama_vision_model.strip()
        status = ollama_status()
        for hint in ("qwen2.5vl", "llava", "vision", "llama3.2-vision"):
            for om in status.get("models") or []:
                if hint in om.lower():
                    return f"{om} (auto)"
        return "(auto — kein Vision-Modell auf Ollama)"
    if task_key != "tts" and settings.ollama_model.strip():
        return settings.ollama_model.strip()
    return "(leer)"


def effective_ai_config(prefs: dict | None) -> dict:
    """Profil-Einstellungen + effektive Provider/Modelle je Aufgabentyp."""
    prefs = prefs if isinstance(prefs, dict) else {}
    ollama = ollama_status()
    tasks: dict[str, dict] = {}
    for task_key in sorted(TASK_KEYS):
        provider, model = resolve_task_ai(prefs, task_key)
        tasks[task_key] = {
            "provider": provider,
            "profile_model": model or None,
            "effective_model": _effective_model(provider, model, task_key),
        }
    unit_generate = {
        key: tasks[key]
        for key in UNIT_GENERATE_TASKS
        if key in tasks
    }
    return {
        "env": {
            "llm_provider": settings.llm_provider,
            "ollama_url": settings.ollama_url,
            "ollama_model": settings.ollama_model,
            "ollama_vision_model": settings.ollama_vision_model or None,
            "ollama_chat_timeout_sec": settings.ollama_chat_timeout_sec,
            "ollama_vision_timeout_sec": settings.ollama_vision_timeout_sec,
        },
        "ollama": {
            "ok": ollama.get("ok"),
            "url": ollama.get("url"),
            "model_count": len(ollama.get("models") or []),
            "error": ollama.get("error"),
        },
        "profile": {
            "llm_provider": prefs.get("llm_provider") or None,
            "llm_model": prefs.get("llm_model") or None,
            "by_task": prefs.get("by_task") or {},
        },
        "tasks": tasks,
        "unit_generate": unit_generate,
    }
