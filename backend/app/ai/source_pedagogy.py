"""Strukturierte Didaktik aus Lernmittel-Quellen extrahieren und zusammenführen."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.ai.providers import parse_json_object
from app.core.german_pedagogy_verify import finalize_german_pedagogy_digest
from app.core.method_taxonomy import normalize_method_id
from app.core.pedagogy_labels import (
    guess_method_id,
    is_competency_heading,
    is_schema_placeholder,
    normalize_label,
    resolve_method_entry,
    sanitize_pedagogy_field,
)

_log = logging.getLogger(__name__)

_PEDAGOGY_JSON_MARKER = "## PEDAGOGY_JSON"
_MAX_DIGEST_CHARS = 8000
# Erhöhen bei Schema-/Prompt-Änderungen — alte analysis_encrypted werden neu visiert.
PEDAGOGY_ANALYSIS_VERSION = 4

_VISION_JSON_RETRY_SUFFIX = (
    "\n\nWICHTIG: Antworte NUR mit einem gültigen JSON-Objekt — kein Markdown, kein Text "
    "davor oder danach. Kompakt: höchstens 12 key_terms, 8 assignments, 6 methods, "
    "6 worked_examples."
)


@dataclass(frozen=True)
class VisionExtractResult:
    """Ergebnis einer Bild-Quellen-Extraktion (Vision + Parser)."""

    summary: str
    structured: bool = False
    ok: bool = False


def vision_pedagogy_prompt(*, language: str, focus_group: str | None = None) -> str:
    from app.ai.prompts.pedagogy_vision import vision_pedagogy_prompt as _build

    return _build(language=language, focus_group=focus_group)


def vision_pedagogy_retry_prompt(*, language: str, focus_group: str | None = None) -> str:
    return vision_pedagogy_prompt(language=language, focus_group=focus_group) + _VISION_JSON_RETRY_SUFFIX


def encode_source_analysis(
    *,
    provider: str,
    model: str | None,
    pedagogy: dict[str, Any],
    structured: bool = True,
) -> str:
    payload = {
        "provider": provider,
        "model": model or "",
        "version": PEDAGOGY_ANALYSIS_VERSION,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "structured": bool(structured),
        "pedagogy": pedagogy,
    }
    return json.dumps(payload, ensure_ascii=False)


def analysis_is_structured(parsed: dict[str, Any] | None) -> bool:
    if not isinstance(parsed, dict):
        return False
    if parsed.get("structured") is False:
        return False
    pedagogy = parsed.get("pedagogy")
    return isinstance(pedagogy, dict) and has_pedagogy_content(pedagogy)


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
    if not isinstance(pedagogy, dict):
        return {}
    return _normalize_pedagogy(pedagogy)


def analysis_version_of(parsed: dict[str, Any] | None) -> int:
    if not parsed:
        return 0
    try:
        return int(parsed.get("version") or 0)
    except (TypeError, ValueError):
        return 0


def parsed_analysis_needs_refresh(parsed: dict[str, Any] | None) -> bool:
    """True, wenn Vision erneut laufen soll (leer, oder Prompt/Parser-Version veraltet)."""
    if not parsed:
        return True
    if analysis_version_of(parsed) < PEDAGOGY_ANALYSIS_VERSION:
        return True
    pedagogy = parsed.get("pedagogy")
    if not isinstance(pedagogy, dict):
        return True
    return not has_pedagogy_content(_normalize_pedagogy(pedagogy))


def blob_needs_pedagogy_refresh(blob: bytes | None) -> bool:
    if not blob:
        return True
    from app.core.crypto import decrypt_text_master

    parsed = decode_source_analysis(decrypt_text_master(blob))
    return parsed_analysis_needs_refresh(parsed)


def blob_analysis_is_current(blob: bytes | None) -> bool:
    if not blob:
        return False
    from app.core.crypto import decrypt_text_master

    parsed = decode_source_analysis(decrypt_text_master(blob))
    return analysis_version_of(parsed) >= PEDAGOGY_ANALYSIS_VERSION


def blob_extracted_at(blob: bytes | None) -> str | None:
    if not blob:
        return None
    from app.core.crypto import decrypt_text_master

    parsed = decode_source_analysis(decrypt_text_master(blob))
    if not parsed:
        return None
    raw = str(parsed.get("extracted_at") or "").strip()
    return raw or None


def blob_analysis_is_structured(blob: bytes | None) -> bool:
    if not blob:
        return False
    from app.core.crypto import decrypt_text_master

    parsed = decode_source_analysis(decrypt_text_master(blob))
    return analysis_is_structured(parsed)


def parse_pedagogy_extraction(
    text: str,
    *,
    focus_group: str | None = None,
) -> tuple[str, dict[str, Any], bool]:
    """Vision-Antwort → (Lesetext, Pedagogy-Objekt, strukturiert parsebar)."""
    raw = str(text or "").strip()
    if not raw:
        return "", {}, False

    json_blob = _extract_json_blob(raw)
    if not json_blob:
        _log.warning("source_pedagogy no_json chars=%d", len(raw))
        return raw, {}, False

    try:
        parsed = parse_json_object(json_blob)
    except Exception:
        _log.warning("source_pedagogy parse_fail chars=%d", len(raw))
        return raw, {}, False

    if not isinstance(parsed, dict):
        _log.warning("source_pedagogy parse_not_object chars=%d", len(raw))
        return raw, {}, False

    summary = sanitize_pedagogy_field(str(parsed.get("summary") or "").strip())
    pedagogy = _finalize_pedagogy(_normalize_pedagogy(parsed), focus_group=focus_group)
    if not summary:
        summary = _fallback_summary(pedagogy)

    structured = has_pedagogy_content(pedagogy)
    if not structured:
        _log.warning("source_pedagogy empty_pedagogy chars=%d", len(raw))
    return summary, pedagogy, structured


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


_FULL_EQUATION = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*([+\-·×*:÷/x])\s*(-?\d+(?:[.,]\d+)?)\s*=\s*(-?\d+(?:[.,]\d+)?)"
)
_NUMBER_EQ_NUMBER = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*=\s*(-?\d+(?:[.,]\d+)?)"
)
_HANDWRITING_META = re.compile(
    r"kreis|striche|korrigier|handschrift|nebenrechnung|bleistift|durchgestrich",
    re.I,
)


def _parse_decimal(raw: str) -> float | None:
    try:
        return float(str(raw).replace(",", "."))
    except ValueError:
        return None


def _compute_binary(left: float, op: str, right: float) -> float | None:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op in {"·", "×", "*", "x"}:
        return left * right
    if op in {":", "÷", "/"}:
        if abs(right) < 1e-12:
            return None
        return left / right
    return None


def equation_is_arithmetically_ok(text: str) -> bool | None:
    """True/False wenn a ⊕ b = c parsebar; None wenn keine solche Gleichung."""
    matches = list(_FULL_EQUATION.finditer(str(text or "")))
    if not matches:
        return None
    any_parsed = False
    for match in matches:
        left = _parse_decimal(match.group(1))
        right = _parse_decimal(match.group(3))
        stated = _parse_decimal(match.group(4))
        if left is None or right is None or stated is None:
            continue
        computed = _compute_binary(left, match.group(2), right)
        if computed is None:
            continue
        any_parsed = True
        if abs(computed - stated) >= 1e-3:
            return False
    return True if any_parsed else None


def _lhs_missing_operator(text: str) -> bool:
    """True bei «4,602 = 240,8» (Zahl = Zahl ohne Rechenzeichen)."""
    raw = str(text or "")
    for match in _NUMBER_EQ_NUMBER.finditer(raw):
        prefix = raw[: match.start()].rstrip()
        if prefix and prefix[-1] in "+-·×*÷/x":
            continue
        return True
    return False


def _numbers_in(text: str) -> list[float]:
    out: list[float] = []
    for match in re.finditer(r"-?\d+(?:[.,]\d+)?", str(text or "")):
        parsed = _parse_decimal(match.group(0))
        if parsed is not None:
            out.append(parsed)
    return out


def _shares_number(problem: str, step: str) -> bool:
    problem_nums = _numbers_in(problem)
    step_nums = _numbers_in(step)
    if not problem_nums or not step_nums:
        return True
    for value in step_nums:
        if any(abs(value - other) < 1e-6 for other in problem_nums):
            return True
    return False


def _usable_worked_problem(problem: str) -> bool:
    if not problem or is_competency_heading(problem):
        return False
    if _lhs_missing_operator(problem):
        return False
    if len(list(_FULL_EQUATION.finditer(problem))) > 1:
        return False
    ok = equation_is_arithmetically_ok(problem)
    if ok is False:
        return False
    return True


def _usable_worked_step(problem: str, step: str) -> bool:
    if not step:
        return False
    if is_competency_heading(step):
        return False
    if equation_is_arithmetically_ok(step) is False:
        return False
    if (
        _FULL_EQUATION.search(step)
        and _FULL_EQUATION.search(problem)
        and not _shares_number(problem, step)
    ):
        return False
    return True


def _usable_example_text(text: str) -> bool:
    if not text:
        return True
    if is_competency_heading(text) or _lhs_missing_operator(text):
        return False
    return equation_is_arithmetically_ok(text) is not False


def _usable_prose_text(text: str) -> bool:
    if not text or is_competency_heading(text) or is_schema_placeholder(text):
        return False
    if _HANDWRITING_META.search(text):
        return False
    return True


def _normalize_key_terms(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        term = sanitize_pedagogy_field(str(item.get("term") or "").strip())
        if not term:
            continue
        key = normalize_label(term)
        if not key or key in seen:
            continue
        seen.add(key)
        entry: dict[str, str] = {"term": term[:80]}
        definition = sanitize_pedagogy_field(str(item.get("definition") or "").strip())
        role = sanitize_pedagogy_field(str(item.get("role") or "").strip())
        if definition:
            entry["definition"] = definition[:300]
        if role:
            entry["role"] = role[:60]
        out.append(entry)
    return out[:24]


def _normalize_assignments(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        instruction = sanitize_pedagogy_field(str(item.get("instruction") or "").strip())
        if not instruction and item.get("text"):
            instruction = sanitize_pedagogy_field(str(item.get("text") or "").strip())
        if not instruction or not _usable_prose_text(instruction):
            continue
        ref = str(item.get("ref") or "").strip()
        fmt = sanitize_pedagogy_field(str(item.get("format") or "").strip())
        entry: dict[str, str] = {"instruction": instruction[:800]}
        if ref:
            entry["ref"] = ref[:40]
        if fmt:
            entry["format"] = fmt[:60]
        out.append(entry)
    return out[:12]


def _normalize_comprehension(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        question = sanitize_pedagogy_field(str(item.get("question") or "").strip())
        answer = sanitize_pedagogy_field(str(item.get("answer") or "").strip())
        if not question or not answer:
            continue
        out.append({"question": question[:300], "answer": answer[:300]})
    return out[:8]


def _normalize_visual_tasks(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = sanitize_pedagogy_field(str(item.get("kind") or "").strip())
        instruction = sanitize_pedagogy_field(str(item.get("instruction") or "").strip())
        if not kind and not instruction:
            continue
        entry: dict[str, Any] = {}
        if kind:
            entry["kind"] = kind[:40]
        if instruction:
            entry["instruction"] = instruction[:500]
        terms = [
            sanitize_pedagogy_field(str(t).strip())
            for t in (item.get("terms") or [])
            if str(t).strip()
        ]
        if terms:
            entry["terms"] = terms[:12]
        placements: list[dict[str, Any]] = []
        for placement in item.get("placements") or []:
            if not isinstance(placement, dict):
                continue
            term = sanitize_pedagogy_field(str(placement.get("term") or "").strip())
            if not term:
                continue
            try:
                x = float(placement.get("x", 0.5))
                y = float(placement.get("y", 0.5))
            except (TypeError, ValueError):
                continue
            placements.append({"term": term[:80], "x": x, "y": y})
        if placements:
            entry["placements"] = placements[:12]
        out.append(entry)
    return out[:8]


def _finalize_pedagogy(
    pedagogy: dict[str, Any],
    *,
    focus_group: str | None = None,
) -> dict[str, Any]:
    return finalize_german_pedagogy_digest(pedagogy, focus_group=focus_group)


def _normalize_pedagogy(
    parsed: dict[str, Any],
    *,
    focus_group: str | None = None,
) -> dict[str, Any]:
    page_summary = sanitize_pedagogy_field(
        str(parsed.get("summary") or parsed.get("page_summary") or "").strip()
    )
    methods = _normalize_methods(parsed.get("methods"))
    worked = _normalize_worked_examples(parsed.get("worked_examples"))
    assignments = _normalize_assignments(parsed.get("assignments"))
    exercises = _normalize_exercises(parsed.get("exercises"))
    if not assignments and exercises:
        for ex in exercises:
            if not isinstance(ex, dict):
                continue
            text = str(ex.get("text") or "").strip()
            if text:
                assignments.append(
                    {
                        "ref": str(ex.get("ref") or "")[:40],
                        "instruction": text[:800],
                        "format": "",
                    }
                )
    patterns = _normalize_string_list(parsed.get("exercise_patterns"))
    formats = _normalize_string_list(parsed.get("exercise_formats"))
    if formats:
        for fmt in formats:
            if fmt not in patterns:
                patterns.append(fmt)
    teaching = [
        note
        for note in _normalize_string_list(parsed.get("teaching_notes"))
        if not _HANDWRITING_META.search(note)
    ]
    is_meta = bool(parsed.get("is_metadata_only"))

    result = {
        "is_metadata_only": is_meta,
        "page_summary": page_summary[:1200],
        "key_terms": _normalize_key_terms(parsed.get("key_terms")),
        "assignments": assignments,
        "exercise_formats": formats,
        "comprehension": _normalize_comprehension(parsed.get("comprehension")),
        "visual_tasks": _normalize_visual_tasks(parsed.get("visual_tasks")),
        "methods": methods,
        "worked_examples": worked,
        "exercises": exercises,
        "exercise_patterns": patterns,
        "teaching_notes": teaching,
    }
    return _finalize_pedagogy(result, focus_group=focus_group)


def _normalize_methods(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entry = resolve_method_entry(item)
        if not entry:
            continue
        example = entry.get("example") or ""
        if example and not _usable_example_text(example):
            entry = {key: value for key, value in entry.items() if key != "example"}
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
        if not _usable_worked_problem(problem):
            continue
        steps = [
            step
            for step in _normalize_string_list(item.get("steps"))
            if _usable_worked_step(problem, step)
        ]
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
        if not text or not _usable_prose_text(text):
            continue
        if _lhs_missing_operator(text):
            continue
        if equation_is_arithmetically_ok(text) is False and _FULL_EQUATION.search(text):
            continue
        ref = str(item.get("ref") or "").strip()
        suggested = sanitize_pedagogy_field(str(item.get("suggested_method") or "").strip())
        entry = {"text": text[:800]}
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
        if text and not is_schema_placeholder(text) and not is_competency_heading(text):
            out.append(text[:300])
    return out[:20]


def _fallback_summary(pedagogy: dict[str, Any]) -> str:
    if pedagogy.get("page_summary"):
        return str(pedagogy["page_summary"])
    parts: list[str] = []
    for term in pedagogy.get("key_terms") or []:
        if isinstance(term, dict) and term.get("term"):
            parts.append(str(term["term"]))
    for assignment in pedagogy.get("assignments") or []:
        if isinstance(assignment, dict) and assignment.get("instruction"):
            parts.append(str(assignment["instruction"]))
    for ex in pedagogy.get("exercises") or []:
        if isinstance(ex, dict) and ex.get("text"):
            parts.append(str(ex["text"]))
    for note in pedagogy.get("teaching_notes") or []:
        parts.append(str(note))
    return "\n".join(parts[:8]).strip()


def merge_pedagogy_profiles(
    profiles: list[dict[str, Any]],
    *,
    focus_group: str | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "is_metadata_only": True,
        "page_summary": "",
        "key_terms": [],
        "assignments": [],
        "exercise_formats": [],
        "comprehension": [],
        "visual_tasks": [],
        "methods": [],
        "worked_examples": [],
        "exercises": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    seen_methods: set[str] = set()
    seen_patterns: set[str] = set()
    seen_formats: set[str] = set()
    seen_notes: set[str] = set()
    seen_problems: set[str] = set()
    seen_exercises: set[str] = set()
    seen_terms: set[str] = set()
    seen_assignments: set[str] = set()

    for profile in profiles:
        if not profile:
            continue
        profile = _normalize_pedagogy(profile, focus_group=focus_group)
        if profile.get("is_metadata_only") or not has_pedagogy_content(profile):
            continue
        merged["is_metadata_only"] = False

        summary = str(profile.get("page_summary") or "").strip()
        if summary and not merged.get("page_summary"):
            merged["page_summary"] = summary

        for term in profile.get("key_terms") or []:
            if not isinstance(term, dict):
                continue
            key = normalize_label(term.get("term") or "")
            if not key or key in seen_terms:
                continue
            seen_terms.add(key)
            merged["key_terms"].append(term)

        for assignment in profile.get("assignments") or []:
            if not isinstance(assignment, dict):
                continue
            key = str(assignment.get("instruction") or "")
            if not key or key in seen_assignments:
                continue
            seen_assignments.add(key)
            merged["assignments"].append(assignment)

        for fmt in profile.get("exercise_formats") or []:
            text = str(fmt or "").strip()
            if text and text not in seen_formats:
                seen_formats.add(text)
                merged["exercise_formats"].append(text)

        for item in profile.get("comprehension") or []:
            if isinstance(item, dict) and item.get("question"):
                merged["comprehension"].append(item)

        for task in profile.get("visual_tasks") or []:
            if isinstance(task, dict) and (task.get("kind") or task.get("instruction")):
                merged["visual_tasks"].append(task)

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

    return _finalize_pedagogy(merged, focus_group=focus_group)


def collect_pedagogy_from_unit_sources(
    sources,
    *,
    focus_group: str | None = None,
) -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    for source in sources or []:
        profile = pedagogy_from_analysis_blob(getattr(source, "analysis_encrypted", None))
        if profile:
            profiles.append(profile)
    return merge_pedagogy_profiles(profiles, focus_group=focus_group)


def build_pedagogy_digest(pedagogy: dict[str, Any] | None) -> str:
    profile = pedagogy or {}
    if profile.get("is_metadata_only") or not has_pedagogy_content(profile):
        return (
            "Keine strukturierten Didaktik-Hinweise aus Quellen.\n"
            "Nutze trotzdem alle Lösungswege und Strategien, die im Materialtext vorkommen — "
            "benenne sie so, wie das Heft sie nennt."
        )

    lines: list[str] = ["Didaktik aus den hochgeladenen Quellen:"]

    summary = str(profile.get("page_summary") or "").strip()
    if summary:
        lines.append(f"\nSeiteninhalt:\n{summary}")

    key_terms = profile.get("key_terms") or []
    if key_terms:
        lines.append("\nFachbegriffe aus dem Material:")
        for item in key_terms[:16]:
            if not isinstance(item, dict):
                continue
            term = item.get("term") or ""
            definition = item.get("definition") or ""
            lines.append(f"- {term}: {definition}" if definition else f"- {term}")

    assignments = profile.get("assignments") or []
    if assignments:
        lines.append("\nAufträge aus dem Heft:")
        for item in assignments[:8]:
            if not isinstance(item, dict):
                continue
            ref = item.get("ref")
            instruction = item.get("instruction") or ""
            fmt = item.get("format") or ""
            prefix = f"{ref}: " if ref else ""
            suffix = f" [{fmt}]" if fmt else ""
            lines.append(f"- {prefix}{instruction}{suffix}")

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
    for key in (
        "page_summary",
        "key_terms",
        "assignments",
        "exercise_formats",
        "comprehension",
        "visual_tasks",
        "methods",
        "worked_examples",
        "exercises",
        "exercise_patterns",
        "teaching_notes",
    ):
        if profile.get(key):
            return True
    return False


def _pattern_label(pattern: str) -> str:
    return str(pattern or "").replace("_", " ").strip()
