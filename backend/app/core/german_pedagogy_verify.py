"""Deterministische Didaktik-QA für Deutsch-Grammatik (Digest-Schicht).

Repariert und prüft Fachbegriffe, Methoden und Beispiele aus source_pedagogy —
analog zu grammar_verify für Cloze-Antworten.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.focus_groups import normalize_focus_group
from app.core.pedagogy_labels import is_schema_placeholder, normalize_label
from app.core.german_prepositions import (
    genitive_preposition_reference_text,
    sentence_has_genitive_preposition,
    text_lists_wrong_genitive_prepositions,
)
from app.core.german_pronouns import ersatzprobe_example_is_useful

CASE_REFERENCE: dict[str, dict[str, str]] = {
    "nom": {"frage": "Wer oder was?", "funktion": "Subjekt"},
    "gen": {"frage": "Wessen?", "funktion": "Besitz oder Zugehörigkeit"},
    "dat": {"frage": "Wem?", "funktion": "indirektes Objekt"},
    "acc": {"frage": "Wen oder was?", "funktion": "direktes Objekt"},
}

_CASE_TERM_TO_KEY: dict[str, str] = {
    "nominativ": "nom",
    "genitiv": "gen",
    "dativ": "dat",
    "akkusativ": "acc",
}

_CASE_FORMAT_BLOCKLIST: frozenset[str] = frozenset(
    {"nominativ", "genitiv", "dativ", "akkusativ", "nom", "gen", "dat", "acc", "akk"}
)

_GRAMMAR_TOPIC_HINTS: frozenset[str] = frozenset(
    {
        "kasus",
        "fall",
        "deklination",
        "nominativ",
        "genitiv",
        "dativ",
        "akkusativ",
        "satzglied",
        "wortart",
    }
)

_GENITIVE_PREP_METHOD = re.compile(r"genitiv.*praeposition|praeposition.*genitiv", re.I)
_ERSATZPROBE_ARROW = re.compile(r"\s*[→\->]+\s*")
_W_QUESTION_MARKERS = ("wer oder was", "wessen", "wem", "wen oder was")


def pedagogy_should_apply_german_digest(
    pedagogy: dict[str, Any] | None,
    *,
    focus_group: str | None = None,
) -> bool:
    group = normalize_focus_group(focus_group)
    if group == "german":
        return True
    if not isinstance(pedagogy, dict):
        return False
    for term in pedagogy.get("key_terms") or []:
        if not isinstance(term, dict):
            continue
        blob = normalize_label(f"{term.get('term', '')} {term.get('definition', '')}")
        if any(hint in blob for hint in _GRAMMAR_TOPIC_HINTS):
            return True
    blob = normalize_label(str(pedagogy.get("page_summary") or ""))
    return any(hint in blob for hint in _GRAMMAR_TOPIC_HINTS)


def case_reference_definition(case_key: str) -> str:
    ref = CASE_REFERENCE.get(case_key, {})
    frage = ref.get("frage") or "?"
    funktion = ref.get("funktion") or ""
    return f"{frage} — {funktion}" if funktion else frage


def is_circular_case_definition(term: str, definition: str) -> bool:
    case_key = _CASE_TERM_TO_KEY.get(normalize_label(term))
    if not case_key:
        return False
    norm_def = normalize_label(definition)
    if not norm_def:
        return False
    term_norm = normalize_label(term)
    if term_norm not in norm_def:
        return False
    return not any(marker in norm_def for marker in _W_QUESTION_MARKERS)


def _method_label_is_genitive_preposition(label: str) -> bool:
    return bool(_GENITIVE_PREP_METHOD.search(normalize_label(label)))


_DETERMINERS = frozenset({"das", "die", "der", "ein", "eine", "einem", "einen", "einer", "eines"})
_GENITIVE_ARTICLE_MARKERS = frozenset(
    {"des", "eines", "einer", "vom", "beim", "am", "im", "zum", "zur", "dem", "den"}
)
_CASE_TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def text_has_noun_noun_without_genitive_marker(text: str) -> bool:
    """Artikel + zwei grossgeschriebene Wörter ohne Genitiv-Marker dazwischen.

    Nutzt Original-Grossschreibung (nicht normalize_label): deutsche Nomen sind
    gross, Verben/Adjektive klein — «Das Fell Affen» trifft, «Das Fell gefällt» nicht.
    """
    tokens = _CASE_TOKEN_RE.findall(str(text or ""))
    for i, tok in enumerate(tokens):
        if tok.lower() not in _DETERMINERS:
            continue
        capitalized: list[str] = []
        for j in range(i + 1, min(i + 6, len(tokens))):
            word = tokens[j]
            lower = word.lower()
            if lower in _GENITIVE_ARTICLE_MARKERS:
                break
            if word[:1].isupper() and len(word) >= 3:
                capitalized.append(word)
                if len(capitalized) >= 2:
                    return True
                continue
            if capitalized:
                # Nach dem ersten Nomen folgt Kleinbuchstabe → Verb/Adj, kein Nomen-Nomen.
                break
    return False


def _fragments_share_anchor(left: str, right: str) -> bool:
    left_norm = normalize_label(left)
    right_norm = normalize_label(right)
    if len(left_norm) >= 12 and left_norm in right_norm:
        return True
    if len(right_norm) >= 12 and right_norm in left_norm:
        return True
    left_tokens = {t for t in left_norm.split() if len(t) >= 4}
    right_tokens = {t for t in right_norm.split() if len(t) >= 4}
    return bool(left_tokens & right_tokens)


def _looks_like_ersatzprobe(example: dict[str, Any]) -> bool:
    label = normalize_label(str(example.get("method_label") or example.get("label") or ""))
    if "ersatzprobe" in label:
        return True
    blob = normalize_label(
        " ".join(
            [
                str(example.get("problem") or ""),
                *(str(s) for s in (example.get("steps") or []) if isinstance(example.get("steps"), list)),
            ]
        )
    )
    return "ersatzprobe" in blob


def worked_example_is_coherent(example: dict[str, Any]) -> bool:
    problem = str(example.get("problem") or "")
    steps = example.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    text = " ".join([problem, *(str(s) for s in steps)])
    if not text.strip():
        return False
    for step in steps:
        step_text = str(step or "")
        if "→" not in step_text and "->" not in step_text:
            continue
        parts = _ERSATZPROBE_ARROW.split(step_text)
        if len(parts) < 2:
            continue
        if not _fragments_share_anchor(parts[0], parts[-1]):
            return False
    if text_has_noun_noun_without_genitive_marker(text):
        return False
    if _looks_like_ersatzprobe(example) and not ersatzprobe_example_is_useful(example, text=text):
        return False
    return True


def filter_exercise_type_list(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        text = str(raw or "").strip()
        if not text or is_schema_placeholder(text):
            continue
        key = normalize_label(text)
        if key in _CASE_FORMAT_BLOCKLIST:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def repair_key_terms(key_terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for raw in key_terms:
        if not isinstance(raw, dict):
            continue
        term = str(raw.get("term") or "").strip()
        if not term:
            continue
        entry = dict(raw)
        definition = str(raw.get("definition") or "").strip()
        case_key = _CASE_TERM_TO_KEY.get(normalize_label(term))
        if case_key and (not definition or is_circular_case_definition(term, definition)):
            entry["definition"] = case_reference_definition(case_key)
        repaired.append(entry)
    return repaired


def _sanitize_genitive_preposition_field(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return cleaned
    wrong = text_lists_wrong_genitive_prepositions(cleaned)
    if wrong:
        return genitive_preposition_reference_text()
    return cleaned


def repair_methods(methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for raw in methods:
        if not isinstance(raw, dict):
            continue
        entry = dict(raw)
        label = str(entry.get("label") or "")
        when = _sanitize_genitive_preposition_field(str(entry.get("when") or ""))
        example = _sanitize_genitive_preposition_field(str(entry.get("example") or ""))
        entry["when"] = when
        entry["example"] = example
        if "ersatzprobe" in normalize_label(label) and example:
            if not ersatzprobe_example_is_useful(entry, text=example):
                entry["example"] = ""
        if _method_label_is_genitive_preposition(label):
            blob = " ".join(
                filter(
                    None,
                    [
                        str(entry.get("problem") or ""),
                        entry.get("example") or "",
                        when,
                    ],
                )
            )
            if blob and not sentence_has_genitive_preposition(blob):
                entry["label"] = "Genitivattribut"
        if entry.get("label") or entry.get("when") or entry.get("example"):
            repaired.append(entry)
    return repaired


def repair_worked_examples(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for raw in examples:
        if not isinstance(raw, dict):
            continue
        entry = dict(raw)
        label = str(entry.get("method_label") or entry.get("label") or "")
        problem = str(entry.get("problem") or "")
        steps = entry.get("steps") if isinstance(entry.get("steps"), list) else []
        blob = " ".join([problem, *(str(s) for s in steps)])
        if _method_label_is_genitive_preposition(label) and blob and not sentence_has_genitive_preposition(blob):
            entry["method_label"] = "Genitivattribut"
        if worked_example_is_coherent(entry):
            repaired.append(entry)
    return repaired


def repair_teaching_notes(notes: list[str]) -> list[str]:
    out: list[str] = []
    for raw in notes:
        text = str(raw or "").strip()
        if not text:
            continue
        out.append(_sanitize_genitive_preposition_field(text))
    return out


def finalize_german_pedagogy_digest(
    pedagogy: dict[str, Any],
    *,
    focus_group: str | None = None,
) -> dict[str, Any]:
    if not pedagogy_should_apply_german_digest(pedagogy, focus_group=focus_group):
        return pedagogy
    out = dict(pedagogy)
    out["key_terms"] = repair_key_terms(out.get("key_terms") or [])
    out["exercise_formats"] = filter_exercise_type_list(out.get("exercise_formats") or [])
    out["exercise_patterns"] = filter_exercise_type_list(out.get("exercise_patterns") or [])
    out["methods"] = repair_methods(out.get("methods") or [])
    out["worked_examples"] = repair_worked_examples(out.get("worked_examples") or [])
    out["teaching_notes"] = repair_teaching_notes(out.get("teaching_notes") or [])
    return out


def format_german_pedagogy_report_section(warnings: list[dict[str, str]]) -> list[str]:
    if not warnings:
        return ["_Keine Deutsch-Didaktik-Prüfungen (Fachgruppe nicht «german» oder kein Grammatik-Material)._", ""]
    lines = ["**Didaktik-Digest (Deutsch-Grammatik)**"]
    for item in warnings:
        mark = {"ok": "✓", "warn": "⚠", "info": "·"}.get(str(item.get("level")), "-")
        lines.append(f"- {mark} [{item.get('ref')}] {item.get('message')}")
    lines.append("")
    return lines


def verify_german_pedagogy_digest(
    pedagogy: dict[str, Any],
    *,
    focus_group: str | None = None,
) -> list[dict[str, str]]:
    if not pedagogy_should_apply_german_digest(pedagogy, focus_group=focus_group):
        return []
    warnings: list[dict[str, str]] = []
    for term in pedagogy.get("key_terms") or []:
        if not isinstance(term, dict):
            continue
        name = str(term.get("term") or "")
        definition = str(term.get("definition") or "")
        case_key = _CASE_TERM_TO_KEY.get(normalize_label(name))
        if case_key and is_circular_case_definition(name, definition):
            warnings.append(
                {
                    "kind": "case_definition",
                    "level": "warn",
                    "ref": f"term:{name}",
                    "message": f"Zirkuläre Kasus-Definition für «{name}»",
                }
            )
        elif case_key and CASE_REFERENCE[case_key]["frage"].split()[0] in normalize_label(definition):
            warnings.append(
                {
                    "kind": "case_definition",
                    "level": "ok",
                    "ref": f"term:{name}",
                    "message": f"«{name}»: Referenzdefinition mit W-Frage",
                }
            )
    for index, method in enumerate(pedagogy.get("methods") or [], start=1):
        if not isinstance(method, dict):
            continue
        blob = " ".join(
            str(method.get(key) or "") for key in ("label", "when", "example")
        )
        wrong = text_lists_wrong_genitive_prepositions(blob)
        if wrong:
            warnings.append(
                {
                    "kind": "preposition_case",
                    "level": "warn",
                    "ref": f"method:{index}",
                    "message": f"Falsche Genitiv-Präpositionen: {', '.join(wrong)}",
                }
            )
    for fmt in pedagogy.get("exercise_formats") or []:
        if normalize_label(str(fmt)) in _CASE_FORMAT_BLOCKLIST:
            warnings.append(
                {
                    "kind": "exercise_format",
                    "level": "warn",
                    "ref": "exercise_formats",
                    "message": f"Fall «{fmt}» fälschlich als Aufgabentyp",
                }
            )
    for index, example in enumerate(pedagogy.get("worked_examples") or [], start=1):
        if isinstance(example, dict) and not worked_example_is_coherent(example):
            warnings.append(
                {
                    "kind": "worked_example",
                    "level": "warn",
                    "ref": f"example:{index}",
                    "message": "Zusammengeklebtes oder grammatisch kaputtes Beispiel",
                }
            )
    return warnings
