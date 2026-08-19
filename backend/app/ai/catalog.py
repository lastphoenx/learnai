"""Aufgabentypen und empfohlene Modelle (lokal vs. extern)."""

from __future__ import annotations

TASK_CATALOG: list[dict] = [
    {
        "key": "explain",
        "label": "Erklären / Lerntext",
        "why": "Fließtext, Didaktik. Lokal ist stark; Fotos der Kinder bleiben intern.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "llama3.3:70b", "gemma3:27b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "quiz",
        "label": "Quiz / Verständnis",
        "why": "Strukturierte Fragen. Lokal reicht; weniger Halluzinations-Risiko als freie Essays.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "llama3.3:70b", "mistral-small"],
        "external": ["gpt-4o-mini", "claude-sonnet-4-0", "gpt-4o"],
    },
    {
        "key": "practice",
        "label": "Übungen",
        "why": "Mathe/Deutsch-Aufgaben. Qwen ist lokal oft sehr gut; Privacy bei Kinderheften.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "llama3.3:70b", "qwen2.5:14b"],
        "external": ["gpt-4o", "claude-sonnet-4-0", "gpt-4o-mini"],
    },
    {
        "key": "mixed",
        "label": "Gemischt (Text + Quiz)",
        "why": "Standard-Einheit. Default lokal, außer du merkst Qualitätsbruch.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "llama3.3:70b", "gemma3:27b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "exam",
        "label": "Kurzprüfung",
        "why": "Noten/Leistung — Datenschutz vor Qualität. Deshalb lokal.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "llama3.3:70b", "qwen2.5:14b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "vocab",
        "label": "Vokabeln / Sprache",
        "why": "Betonung, Idiome, Beispielsätze. Text lieber extern; Vorlesen sowieso OpenAI-TTS.",
        "default_provider": "anthropic",
        "local": ["qwen2.5:32b", "llama3.3:70b", "mistral-small"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "vision",
        "label": "Fotos / OCR (Lernmittel)",
        "why": "Hefte und Arbeitsblätter — hohe Privacy. Vision lokal, außer das Modell versagt.",
        "default_provider": "ollama",
        "local": ["qwen2.5vl", "llama3.2-vision", "llava"],
        "external": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-0"],
    },
    {
        "key": "tts",
        "label": "Vorlesen / Aussprache (Ton)",
        "why": "Lokale Stimmen klingen oft falsch. OpenAI TTS ist der Default.",
        "default_provider": "openai",
        "local": ["piper", "kokoro", "xtts"],
        "external": ["tts-1-hd", "gpt-4o-mini-tts", "tts-1"],
    },
]


TASK_KEYS = {item["key"] for item in TASK_CATALOG}


def catalog_public() -> list[dict]:
    return TASK_CATALOG


def default_for(task_key: str) -> dict:
    for item in TASK_CATALOG:
        if item["key"] == task_key:
            provider = item["default_provider"]
            if provider == "ollama":
                model = ""
            else:
                model = item["external"][0]
            return {"provider": provider, "model": model}
    return {"provider": "ollama", "model": ""}


def resolve_task_ai(
    prefs: dict,
    task_key: str,
    *,
    override: str | None = None,
) -> tuple[str, str | None]:
    """Provider + optionales Modell für einen Aufgabentyp."""
    by_task = prefs.get("by_task") if isinstance(prefs.get("by_task"), dict) else {}
    row = by_task.get(task_key) if isinstance(by_task.get(task_key), dict) else {}
    recommended = default_for(task_key)
    override_name = (override or "").strip().lower()

    if override_name and override_name not in {"default", ""}:
        provider = override_name
        model = str(row.get("model") or prefs.get("llm_model") or recommended.get("model") or "").strip()
    elif str(row.get("provider") or "").strip():
        provider = str(row["provider"]).strip().lower()
        model = str(row.get("model") or "").strip()
        if not model and recommended["provider"] == provider:
            model = str(recommended.get("model") or "")
    elif task_key not in {"vision", "tts"} and str(prefs.get("llm_provider") or "").strip():
        provider = str(prefs["llm_provider"]).strip().lower()
        model = str(prefs.get("llm_model") or "").strip()
    else:
        provider = recommended["provider"]
        model = str(recommended.get("model") or "").strip()

    return provider, (model or None)
