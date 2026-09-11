"""Zeitstrahl-Diagramme aus key_terms (historische Epochen mit Datumsbereichen)."""

from __future__ import annotations

import re
from typing import Any

_EPOCH_ROLE = re.compile(r"epoche|zeitperiode|zeitliche|period", re.I)
_EPOCH_TERM = re.compile(
    r"steinzeit|mittelalter|neuzeit|antike|r[oö]merzeit|geschichte|gegenwart|bronze|eisen",
    re.I,
)
_RANGE_AD = re.compile(
    r"(\d{1,4})\s*bis\s*(\d{1,4})(?!\s*v\.?\s*Chr)",
    re.I,
)
_RANGE_BC = re.compile(r"(\d{1,6})\s*bis\s*(\d{1,6})\s*v\.?\s*Chr", re.I)
_RANGE_AD_EXPLICIT = re.compile(r"(\d{1,4})\s*bis\s*(\d{1,4})\s*n\.?\s*Chr", re.I)
_UNTIL_BC = re.compile(r"bis\s*(\d{1,6})\s*v\.?\s*Chr", re.I)
_CENTURY_SPAN = re.compile(
    r"(\d{1,2})\.\s*Jahrhundert\s*v\.?\s*Chr\.?\s*bis\s*(\d{1,2})\.\s*Jahrhundert\s*n\.?\s*Chr",
    re.I,
)
_PRESENT = re.compile(r"bis\s*(?:zur\s+)?Gegenwart|heute|21\.\s*Jahrhundert", re.I)
_DEEP_PAST = -500_000
_PRESENT_YEAR = 2030


def _century_bc_range(century: int) -> tuple[int, int]:
    n = max(1, min(century, 50))
    return -(n * 100), -(n * 100 - 99)


def _century_ad_range(century: int) -> tuple[int, int]:
    n = max(1, min(century, 30))
    return (n - 1) * 100 + 1, n * 100


def parse_epoch_year_range(definition: str) -> tuple[int, int] | None:
    text = str(definition or "").strip()
    if not text:
        return None

    spans: list[tuple[int, int]] = []

    century_span = _CENTURY_SPAN.search(text)
    if century_span:
        spans.append(_century_bc_range(int(century_span.group(1))))
        spans.append(_century_ad_range(int(century_span.group(2))))

    for match in _RANGE_BC.finditer(text):
        a, b = int(match.group(1)), int(match.group(2))
        spans.append((-max(a, b), -min(a, b)))

    for match in _RANGE_AD_EXPLICIT.finditer(text):
        a, b = int(match.group(1)), int(match.group(2))
        spans.append((min(a, b), max(a, b)))

    for match in _RANGE_AD.finditer(text):
        fragment = text[max(0, match.start() - 8) : match.end() + 12]
        if re.search(r"v\.?\s*Chr", fragment, re.I):
            continue
        a, b = int(match.group(1)), int(match.group(2))
        if a > 2500 or b > 2500:
            continue
        spans.append((min(a, b), max(a, b)))

    until_bc = _UNTIL_BC.search(text)
    if until_bc and not _RANGE_BC.search(text):
        spans.append((_DEEP_PAST, -int(until_bc.group(1))))

    if _PRESENT.search(text):
        start_match = re.search(r"(\d{3,4})\s*bis", text)
        start = int(start_match.group(1)) if start_match else 1900
        spans.append((start, _PRESENT_YEAR))

    if not spans:
        return None

    return min(s[0] for s in spans), max(s[1] for s in spans)


def is_epoch_key_term(item: dict[str, Any]) -> bool:
    role = str(item.get("role") or "")
    term = str(item.get("term") or "")
    definition = str(item.get("definition") or "")
    parsed = parse_epoch_year_range(definition)
    if not parsed:
        return False
    if _EPOCH_ROLE.search(role):
        return True
    return bool(_EPOCH_TERM.search(term))


def detect_timeline_epochs(key_terms: list[Any]) -> list[dict[str, Any]]:
    epochs: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for item in key_terms or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "").strip()
        definition = str(item.get("definition") or "").strip()
        if not term or not definition:
            continue
        key = term.lower()
        if key in seen_terms:
            continue
        if not is_epoch_key_term(item):
            continue
        parsed = parse_epoch_year_range(definition)
        if not parsed:
            continue
        start, end = parsed
        seen_terms.add(key)
        epochs.append(
            {
                "term": term,
                "definition": definition,
                "start_year": start,
                "end_year": end,
            }
        )
    epochs.sort(key=lambda row: (row["start_year"], row["end_year"], row["term"].lower()))
    return epochs


def _timeline_instruction(pedagogy: dict[str, Any]) -> str:
    for pattern in pedagogy.get("exercise_patterns") or []:
        text = str(pattern or "").strip()
        if "zeitstrahl" in text.lower():
            return "Ordne die Epochen chronologisch auf dem Zeitstrahl zu."
    for assignment in pedagogy.get("assignments") or []:
        if not isinstance(assignment, dict):
            continue
        instruction = str(assignment.get("instruction") or "").lower()
        if "zeitstrahl" in instruction:
            return "Ordne die Epochen chronologisch auf dem Zeitstrahl zu."
    return "Ordne jeden Begriff der passenden Epoche auf dem Zeitstrahl zu."


def build_timeline_diagram_from_pedagogy(
    pedagogy: dict[str, Any],
    *,
    title: str = "Epochen auf dem Zeitstrahl",
    term_hints: dict[str, str] | None = None,
    min_epochs: int = 4,
    max_epochs: int = 10,
) -> dict[str, Any] | None:
    from app.core.label_diagram import build_label_diagram_from_terms

    epochs = detect_timeline_epochs(pedagogy.get("key_terms") or [])
    if len(epochs) < min_epochs:
        return None

    selected = epochs[:max_epochs]
    min_year = min(row["start_year"] for row in selected)
    max_year = max(row["end_year"] for row in selected)
    span = max(max_year - min_year, 1)

    placements: list[dict[str, Any]] = []
    for row in selected:
        mid = (row["start_year"] + row["end_year"]) / 2
        x = round(0.12 + 0.76 * (mid - min_year) / span, 3)
        placements.append({"term": row["term"], "x": x, "y": 0.58})

    hints = dict(term_hints or {})
    for row in selected:
        hints.setdefault(row["term"], str(row["definition"])[:160])

    terms = [row["term"] for row in selected]
    return build_label_diagram_from_terms(
        terms,
        title=title[:120],
        instruction=_timeline_instruction(pedagogy),
        placements=placements,
        term_hints=hints,
        layout="timeline",
        shuffle_terms=True,
        max_terms=max_epochs,
    )


def summarize_timeline(pedagogy: dict[str, Any]) -> dict[str, Any] | None:
    epochs = detect_timeline_epochs(pedagogy.get("key_terms") or [])
    if len(epochs) < 4:
        return None
    return {
        "epochs": len(epochs),
        "first": epochs[0]["term"],
        "last": epochs[-1]["term"],
        "year_span": [epochs[0]["start_year"], epochs[-1]["end_year"]],
    }
