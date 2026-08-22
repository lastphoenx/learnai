"""Strukturierte Didaktik aus Lernmittel-Quellen extrahieren und zusammenführen."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.providers import parse_json_object
from app.core.method_taxonomy import normalize_method_id
from app.core.pedagogy_labels import (
    guess_method_id,
    is_schema_placeholder,
    normalize_label,
    resolve_method_entry,
    sanitize_pedagogy_field,
)

_log = logging.getLogger(__name__)

_PEDAGOGY_JSON_MARKER = "## PEDAGOGY_JSON"
_MAX_DIGEST_CHARS = 2800


def vision_pedagogy_prompt(*, language: str) -> str:
    lang = (language or "de").strip() or "de"
    return (
        "Das ist ein Foto aus einem Lernmittel (Schulbuch, Arbeitsblatt, Heft).\n"
        "Antworte NUR mit gültigem JSON (kein Markdown, kein Fliesstext davor/danach).\n"
        "Struktur (alle Werte aus dem Bild; leere Strings wenn nichts erkennbar):\n"
        "{\n"
        '  "summary": "",\n'
        '  "is_metadata_only": false,\n'
        '  "methods": [{"label":"","when":"","example":"","id":""}],\n'
        '  "worked_examples": [{"problem":"","method_label":"","steps":[""]}],\n'
        '  "exercises": [{"ref":"","text":"","suggested_method":""}],\n'
        '  "exercise_patterns": [""],\n'
        '  "teaching_notes": [""]\n'
        "}\n"
        "Feldbedeutung:\n"
        "- summary: 2–6 Sätze zu Thema, Seiteninhalt und Lernzielen aus dem Material\n"
        "- methods[].label (Pflicht wenn Methode sichtbar): Strategie-/Lösungsweg-Name exakt wie im Heft\n"
        "- methods[].when (optional): ein Satz, wann diese Strategie passt — nur Inhalt aus dem Heft\n"
        "- methods[].example (optional): kurzes Zahlen- oder Textbeispiel aus dem Bild\n"
        "- methods[].id (optional): nur wenn im Material explizit genannt — nie erfinden\n"
        "- worked_examples: vollständige Beispiel-Lösungswege mit Zwischenschritten und method_label aus dem Heft\n"
        "- exercises: sichtbare Aufgaben mit Zahlen/Text; ref wie «Aufg. 5a» wenn vorhanden\n"
        "- exercise_patterns: erkannte Aufgabentypen in den Worten des Materials (nicht erfinden)\n"
        "- teaching_notes: konkrete didaktische Hinweise aus dem Material\n"
        "Regeln:\n"
        "- methods: alle im Bild gezeigten Lösungswege/Strategien — benenne sie so, wie das Material sie nennt.\n"
        "- KEINE Feld-Beschreibungen, Anweisungen oder Schema-Texte als Werte — nur echte Inhalte oder leere Strings.\n"
        "- is_metadata_only=true nur bei Cover, ISBN, Verlagsinfo ohne Aufgaben.\n"
        "- Bei Metadaten: methods/worked_examples/exercises leer lassen.\n"
        f"- Sprache der Texte: {lang}.\n"
    )


def encode_source_analysis(*, provider: str, model: str | None, pedagogy: dict[str, Any]) -> str:
    payload = {
        "provider": provider,
        "model": model or "",
        "pedagogy": pedagogy,
    }
    return json.dumps(payload, ensure_ascii=False)


def decode_source_analysis(raw: str | None) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    if ":" in text and not text.startswith("{"):
        provider, _, model = text.partition(":")
        return {"provider": provider, "model": model, "pedagogy": {}}
    return None


def pedagogy_from_analysis_blob(blob: bytes | None) -> dict[str, Any]:
    if not blob:
        return {}
    from app.core.crypto import decrypt_text_master

    raw = decrypt_text_master(blob)
    parsed = decode_source_analysis(raw)
    if not parsed:
        return {}
    pedagogy = parsed.get("pedagogy")
    return pedagogy if isinstance(pedagogy, dict) else {}


def parse_pedagogy_extraction(text: str) -> tuple[str, dict[str, Any]]:
    """Vision-Antwort → (Lesetext für notes, strukturiertes Pedagogy-Objekt)."""
    raw = str(text or "").strip()
    if not raw:
        return "", {}

    json_blob = _extract_json_blob(raw)
    if not json_blob:
        return raw, {}

    try:
        parsed = parse_json_object(json_blob)
    except Exception:
        _log.warning("source_pedagogy parse_fail chars=%d", len(raw))
        return raw, {}

    if not isinstance(parsed, dict):
        return raw, {}

    summary = sanitize_pedagogy_field(str(parsed.get("summary") or "").strip())
    pedagogy = _normalize_pedagogy(parsed)
    if not summary:
        summary = _fallback_summary(pedagogy)
    if not summary:
        summary = raw[:4000]

    return summary, pedagogy


def _extract_json_blob(text: str) -> str | None:
    if _PEDAGOGY_JSON_MARKER in text:
        _, _, tail = text.partition(_PEDAGOGY_JSON_MARKER)
        candidate = tail.strip()
        if candidate.startswith("{"):
            return candidate
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{[\s\S]*\}", stripped)
    return match.group(0) if match else None


def _normalize_pedagogy(parsed: dict[str, Any]) -> dict[str, Any]:
    methods = _normalize_methods(parsed.get("methods"))
    worked = _normalize_worked_examples(parsed.get("worked_examples"))
    exercises = _normalize_exercises(parsed.get("exercises"))
    patterns = _normalize_string_list(parsed.get("exercise_patterns"))
    teaching = _normalize_string_list(parsed.get("teaching_notes"))
    is_meta = bool(parsed.get("is_metadata_only"))

    return {
        "is_metadata_only": is_meta,
        "methods": methods,
        "worked_examples": worked,
        "exercises": exercises,
        "exercise_patterns": patterns,
        "teaching_notes": teaching,
    }


def _normalize_methods(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entry = resolve_method_entry(item)
        if entry:
            out.append(entry)
    return out[:12]


def _normalize_worked_examples(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        problem = sanitize_pedagogy_field(str(item.get("problem") or "").strip())
        steps = _normalize_string_list(item.get("steps"))
        if not problem and not steps:
            continue
        method_label = sanitize_pedagogy_field(
            str(item.get("method_label") or item.get("label") or "").strip()
        )
        method_id = normalize_method_id(item.get("method_id"))
        if not method_id and method_label:
            method_id = guess_method_id(method_label)
        entry: dict[str, Any] = {"problem": problem[:200], "steps": steps[:10]}
        if method_label:
            entry["method_label"] = method_label[:120]
        elif method_id:
            from app.core.method_taxonomy import METHOD_LABELS

            entry["method_label"] = METHOD_LABELS.get(method_id, method_id)
        if method_id:
            entry["method_id"] = method_id
        out.append(entry)
    return out[:10]


def _normalize_exercises(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        ref = str(item.get("ref") or "").strip()
        suggested = sanitize_pedagogy_field(str(item.get("suggested_method") or "").strip())
        entry = {"text": text[:300]}
        if ref:
            entry["ref"] = ref[:40]
        if suggested:
            entry["suggested_method"] = suggested[:120]
        out.append(entry)
    return out[:30]


def _normalize_string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = sanitize_pedagogy_field(str(item or "").strip())
        if text and not is_schema_placeholder(text):
            out.append(text[:300])
    return out[:20]


def _fallback_summary(pedagogy: dict[str, Any]) -> str:
    parts: list[str] = []
    for ex in pedagogy.get("exercises") or []:
        if isinstance(ex, dict) and ex.get("text"):
            parts.append(str(ex["text"]))
    for note in pedagogy.get("teaching_notes") or []:
        parts.append(str(note))
    return "\n".join(parts[:8]).strip()


def merge_pedagogy_profiles(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "is_metadata_only": True,
        "methods": [],
        "worked_examples": [],
        "exercises": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    seen_methods: set[str] = set()
    seen_patterns: set[str] = set()
    seen_notes: set[str] = set()
    seen_problems: set[str] = set()
    seen_exercises: set[str] = set()

    for profile in profiles:
        if not profile or profile.get("is_metadata_only"):
            continue
        merged["is_metadata_only"] = False

        for method in profile.get("methods") or []:
            if not isinstance(method, dict):
                continue
            key = normalize_label(method.get("label") or method.get("id") or "")
            if not key or key in seen_methods:
                continue
            seen_methods.add(key)
            merged["methods"].append(method)

        for example in profile.get("worked_examples") or []:
            if not isinstance(example, dict):
                continue
            key = str(example.get("problem") or "")
            if not key or key in seen_problems:
                continue
            seen_problems.add(key)
            merged["worked_examples"].append(example)

        for exercise in profile.get("exercises") or []:
            if not isinstance(exercise, dict):
                continue
            key = str(exercise.get("text") or "")
            if not key or key in seen_exercises:
                continue
            seen_exercises.add(key)
            merged["exercises"].append(exercise)

        for pattern in profile.get("exercise_patterns") or []:
            text = str(pattern or "").strip()
            if text and text not in seen_patterns:
                seen_patterns.add(text)
                merged["exercise_patterns"].append(text)

        for note in profile.get("teaching_notes") or []:
            text = str(note or "").strip()
            if text and text not in seen_notes:
                seen_notes.add(text)
                merged["teaching_notes"].append(text)

    return merged


def collect_pedagogy_from_unit_sources(sources) -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    for source in sources or []:
        profile = pedagogy_from_analysis_blob(getattr(source, "analysis_encrypted", None))
        if profile:
            profiles.append(profile)
    return merge_pedagogy_profiles(profiles)


def build_pedagogy_digest(pedagogy: dict[str, Any] | None) -> str:
    profile = pedagogy or {}
    if profile.get("is_metadata_only") or not has_pedagogy_content(profile):
        return (
            "Keine strukturierten Didaktik-Hinweise aus Quellen.\n"
            "Nutze trotzdem alle Lösungswege und Strategien, die im Materialtext vorkommen — "
            "benenne sie so, wie das Heft sie nennt."
        )

    lines: list[str] = ["Didaktik aus den hochgeladenen Quellen:"]

    methods = profile.get("methods") or []
    if methods:
        lines.append("\nLösungswege / Strategien:")
        for method in methods[:8]:
            if not isinstance(method, dict):
                continue
            label = method.get("label") or method.get("id")
            when = method.get("when") or ""
            example = method.get("example") or ""
            detail = " — ".join(part for part in (when, example) if part)
            lines.append(f"- {label}: {detail}" if detail else f"- {label}")

    patterns = profile.get("exercise_patterns") or []
    if patterns:
        lines.append("\nAufgabentypen im Heft:")
        for pattern in patterns[:8]:
            lines.append(f"- {_pattern_label(str(pattern))}")

    worked = profile.get("worked_examples") or []
    if worked:
        lines.append("\nBeispiel-Lösungswege (für Verstehen und Üben übernehmen):")
        for item in worked[:4]:
            if not isinstance(item, dict):
                continue
            problem = item.get("problem") or "Beispiel"
            steps = item.get("steps") or []
            step_text = " → ".join(str(s) for s in steps[:5])
            method_label = item.get("method_label") or item.get("label") or ""
            suffix = f" ({method_label})" if method_label else ""
            lines.append(f"- {problem}{suffix}: {step_text}" if step_text else f"- {problem}{suffix}")

    notes = profile.get("teaching_notes") or []
    if notes:
        lines.append("\nHinweise für die Lerneinheit:")
        for note in notes[:6]:
            lines.append(f"- {note}")

    exercises = profile.get("exercises") or []
    if exercises:
        lines.append("\nBeispiel-Aufgaben aus dem Material:")
        for ex in exercises[:6]:
            if not isinstance(ex, dict):
                continue
            ref = ex.get("ref")
            text = ex.get("text") or ""
            prefix = f"{ref}: " if ref else ""
            lines.append(f"- {prefix}{text}")

    digest = "\n".join(lines).strip()
    if len(digest) > _MAX_DIGEST_CHARS:
        return digest[:_MAX_DIGEST_CHARS] + "\n[… Didaktik gekürzt …]"
    return digest


def has_pedagogy_content(profile: dict[str, Any]) -> bool:
    for key in ("methods", "worked_examples", "exercises", "exercise_patterns", "teaching_notes"):
        if profile.get(key):
            return True
    return False


def _pattern_label(pattern: str) -> str:
    return str(pattern or "").replace("_", " ").strip()
