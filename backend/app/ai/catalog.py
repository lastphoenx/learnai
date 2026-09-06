"""Aufgabentypen und empfohlene Modelle (lokal vs. extern)."""

from __future__ import annotations

from app.ai.model_registry import pick_external_model
from app.ai.ollama_match import first_ollama_hint, match_ollama_hints

# Je Typ genau 3 Hints in Prioritätsreihenfolge (1. = beste Wahl in der UI).
# Lokal: möglichst volle Ollama-Tags (z. B. qwen2.5vl:7b), damit nicht qwen2.5vl:72b zuerst matcht.
TASK_CATALOG: list[dict] = [
    {
        "key": "explain",
        "label": "Erklären / Lerntext",
        "why": "Fließtext, Didaktik. Lokal ist stark; Fotos der Kinder bleiben intern.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "qwen3:32b", "llama3.3:70b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "quiz",
        "label": "Quiz / Verständnis",
        "why": "Strukturierte Fragen. Lokal reicht; weniger Halluzinations-Risiko als freie Essays.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "qwen3:32b", "qwen2.5:7b-instruct"],
        "external": ["gpt-4o-mini", "claude-sonnet-4-0", "gpt-4o"],
    },
    {
        "key": "practice",
        "label": "Übungen",
        "why": "Mathe/Deutsch-Aufgaben. Qwen ist lokal oft sehr gut; Privacy bei Kinderheften.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "qwen3:32b", "llama3.3:70b"],
        "external": ["gpt-4o", "claude-sonnet-4-0", "gpt-4o-mini"],
    },
    {
        "key": "mixed",
        "label": "Gemischt (Text + Quiz)",
        "why": "Standard-Einheit. Default lokal, außer du merkst Qualitätsbruch.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "qwen3:32b", "llama3.3:70b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "exam",
        "label": "Kurzprüfung",
        "why": "Noten/Leistung — Datenschutz vor Qualität. Deshalb lokal.",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "qwen3:32b", "llama3.3:70b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "vocab",
        "label": "Vokabeln / Sprache",
        "why": "Betonung, Idiome, Beispielsätze. Text lieber extern; Vorlesen sowieso OpenAI-TTS.",
        "default_provider": "anthropic",
        "local": ["qwen2.5:32b", "qwen3:32b", "llama3.3:70b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "vision",
        "label": "Fotos / OCR (Lernmittel)",
        "why": "Hefte und Arbeitsblätter — hohe Privacy. Kleinere Vision-Modelle zuerst (schneller, weniger Timeout).",
        "default_provider": "ollama",
        "local": ["qwen2.5vl:7b", "qwen2.5vl:32b", "qwen2.5vl:latest"],
        "external": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-0"],
    },
    {
        "key": "exam_analysis",
        "label": "Schulprüfung analysieren",
        "why": "Auswertung korrigierter Prüfungen: Fehlermuster und Empfehlungen. Fotos/OCR nutzen zusätzlich «Fotos / OCR».",
        "default_provider": "ollama",
        "local": ["qwen2.5:32b", "qwen3:32b", "llama3.3:70b"],
        "external": ["claude-sonnet-4-0", "gpt-4o", "gpt-4o-mini"],
    },
    {
        "key": "tts",
        "label": "Vorlesen / Aussprache (Ton)",
        "why": "Lokale Stimmen klingen oft falsch. OpenAI TTS ist der Default.",
        "default_provider": "openai",
        "local": ["piper", "kokoro", "xtts"],
        "external": ["tts-1-hd", "tts-1", "gpt-4o-mini-tts"],
    },
]


TASK_KEYS = {item["key"] for item in TASK_CATALOG}

# Qualitäts-Aufgaben: Kind-Profil erbt vom auslösenden Erwachsenen, wenn dort nichts gepflegt ist.
QUALITY_TASK_KEYS = frozenset({"explain", "quiz", "practice", "mixed", "vocab", "vision"})
# Leistungsdaten: strikt am Ziel-Kind-Profil, keine Vererbung.
SENSITIVE_TASK_KEYS = frozenset({"exam", "exam_analysis"})


def task_catalog_entry(task_key: str) -> dict | None:
    for item in TASK_CATALOG:
        if item["key"] == task_key:
            return item
    return None


def local_hints(task_key: str) -> list[str]:
    item = task_catalog_entry(task_key)
    return list(item["local"]) if item else []


def external_hints(task_key: str) -> list[str]:
    item = task_catalog_entry(task_key)
    return list(item["external"]) if item else []


def catalog_public() -> list[dict]:
    return TASK_CATALOG


def catalog_with_resolved(installed_ollama: list[str] | None = None) -> list[dict]:
    """Katalog + bis zu 3 aufgelöste Modellnamen je Typ (für UI/API)."""
    from app.ai.model_registry import pick_external_models
    from app.ai.providers import ollama_status

    installed = installed_ollama if installed_ollama is not None else (ollama_status().get("models") or [])
    out: list[dict] = []
    for item in TASK_CATALOG:
        row = {**item}
        row["local_resolved"] = match_ollama_hints(item["local"], installed, limit=3)
        row["external_resolved"] = pick_external_models(
            item["default_provider"],
            item["external"],
            task_key=item["key"],
            limit=3,
        )
        out.append(row)
    return out


def default_for(task_key: str, *, installed_ollama: list[str] | None = None) -> dict:
    item = task_catalog_entry(task_key)
    if not item:
        return {"provider": "ollama", "model": ""}
    provider = item["default_provider"]
    if provider == "ollama":
        if installed_ollama is None:
            from app.ai.providers import ollama_status

            installed_ollama = ollama_status().get("models") or []
        model = first_ollama_hint(item["local"], installed_ollama)
    else:
        model = pick_external_model(provider, item["external"], task_key=task_key)
    return {"provider": provider, "model": model}


def has_explicit_task_setting(prefs: dict, task_key: str) -> bool:
    """True wenn für task_key ein Provider in by_task gepflegt ist."""
    by_task = prefs.get("by_task") if isinstance(prefs.get("by_task"), dict) else {}
    row = by_task.get(task_key) if isinstance(by_task.get(task_key), dict) else {}
    return bool(str(row.get("provider") or "").strip())


def effective_prefs_for_task(
    target_prefs: dict,
    fallback_prefs: dict | None,
    task_key: str,
) -> dict:
    """Welche Profil-Einstellungen für einen Aufgabentyp gelten (Vererbung)."""
    if task_key in SENSITIVE_TASK_KEYS:
        return target_prefs
    if task_key in QUALITY_TASK_KEYS and fallback_prefs:
        if not has_explicit_task_setting(target_prefs, task_key):
            return fallback_prefs
    return target_prefs


def resolve_task_ai_for_unit(
    target_prefs: dict,
    fallback_prefs: dict | None,
    task_key: str,
    *,
    override: str | None = None,
    installed_ollama: list[str] | None = None,
) -> tuple[str, str | None]:
    """Provider/Modell mit zweistufiger Vererbung (Kind → auslösender Erwachsener → Katalog)."""
    prefs = effective_prefs_for_task(target_prefs, fallback_prefs, task_key)
    return resolve_task_ai(prefs, task_key, override=override, installed_ollama=installed_ollama)


def resolve_task_ai(
    prefs: dict,
    task_key: str,
    *,
    override: str | None = None,
    installed_ollama: list[str] | None = None,
) -> tuple[str, str | None]:
    """Provider + optionales Modell für einen Aufgabentyp."""
    by_task = prefs.get("by_task") if isinstance(prefs.get("by_task"), dict) else {}
    row = by_task.get(task_key) if isinstance(by_task.get(task_key), dict) else {}
    recommended = default_for(task_key, installed_ollama=installed_ollama)
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
