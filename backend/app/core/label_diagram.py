"""Generische Diagramm-Beschriftung: Hotspots aus Begriffen, ohne thematische Hardcodes."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from typing import Any

_POSITION_HINTS = (
    "oben",
    "rechts oben",
    "rechts",
    "rechts unten",
    "unten",
    "links unten",
    "links",
    "links oben",
)

_LABEL_FORMATS = frozenset(
    {"label", "beschriften", "beschriftung", "zuordnen", "benennen", "markieren"}
)
_DRAW_FORMATS = frozenset(
    {"draw", "zeichnen", "zeichne", "male", "malen", "skizzieren", "skizze"}
)

_LAYOUTS = frozenset({"radial", "timeline", "pyramid"})


def _norm(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "", raw)


def _slug_term(term: str, index: int) -> str:
    slug = _norm(term)[:32]
    return slug or f"term_{index}"


def _stable_shuffle(items: list[str], *, salt: str) -> list[str]:
    return sorted(items, key=lambda item: hashlib.sha256(f"{salt}:{item}".encode()).hexdigest())


def _looks_like_position_hint(text: str) -> bool:
    normalized = _norm(text)
    if not normalized:
        return True
    return normalized in {_norm(h) for h in _POSITION_HINTS}


def _semantic_hint(term: str, term_hints: dict[str, str] | None) -> str | None:
    if not term_hints:
        return None
    direct = term_hints.get(term)
    if direct and not _looks_like_position_hint(direct):
        return direct.strip()[:160]
    for key, value in term_hints.items():
        if _norm(key) == _norm(term) and value and not _looks_like_position_hint(value):
            return str(value).strip()[:160]
    return None


def _layout_coords(index: int, count: int, *, layout: str) -> tuple[float, float]:
    if layout == "timeline":
        if count <= 1:
            return 0.5, 0.5
        x = 0.1 + (0.8 * index / max(1, count - 1))
        y = 0.4 if index % 2 == 0 else 0.72
        return round(x, 3), round(y, 3)
    if layout == "pyramid":
        rows = max(1, int(math.ceil(math.sqrt(count))))
        row = index // rows
        col = index % rows
        row_count = min(rows, count - row * rows)
        if row_count <= 0:
            row_count = 1
        x = 0.5 + (col - (row_count - 1) / 2) * 0.22
        y = 0.22 + row * 0.2
        return round(max(0.1, min(0.9, x)), 3), round(max(0.12, min(0.88, y)), 3)
    angle = (2 * math.pi * index / max(1, count)) - math.pi / 2
    x = 0.5 + 0.34 * math.cos(angle)
    y = 0.5 + 0.34 * math.sin(angle)
    return round(x, 3), round(y, 3)


def build_label_diagram_from_terms(
    terms: list[str],
    *,
    title: str = "Fachbegriffe zuordnen",
    instruction: str | None = None,
    placements: list[dict[str, Any]] | None = None,
    term_hints: dict[str, str] | None = None,
    layout: str = "radial",
    shuffle_terms: bool = True,
    max_terms: int = 8,
) -> dict[str, Any] | None:
    unique: list[str] = []
    seen: set[str] = set()
    for term in terms:
        text = str(term or "").strip()
        key = _norm(text)
        if text and key not in seen:
            seen.add(key)
            unique.append(text)
    if len(unique) < 3:
        return None

    layout_name = layout if layout in _LAYOUTS else "radial"
    placement_map: dict[str, tuple[float, float]] = {}
    if placements:
        for item in placements:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            if not term:
                continue
            try:
                x = float(item.get("x", 0.5))
                y = float(item.get("y", 0.5))
            except (TypeError, ValueError):
                continue
            placement_map[_norm(term)] = (max(0.08, min(0.92, x)), max(0.08, min(0.92, y)))

    working = unique[: max(3, max_terms)]
    count = len(working)
    hotspots: list[dict[str, Any]] = []
    for index, term in enumerate(working):
        placed = placement_map.get(_norm(term))
        if placed:
            x, y = placed
        else:
            x, y = _layout_coords(index, count, layout=layout_name)
        hint = _semantic_hint(term, term_hints)
        hotspots.append(
            {
                "id": _slug_term(term, index),
                "x": x,
                "y": y,
                "accept": [term],
                "hint": hint,
            }
        )

    display_terms = _stable_shuffle(working, salt=title) if shuffle_terms else list(working)

    return {
        "template": "generic",
        "layout": layout_name,
        "title": title[:120],
        "instruction": (
            instruction
            or "Ordne jeden Begriff der passenden Stelle zu. Fahre mit der Maus über ein Fragezeichen für einen Hinweis."
        )[:300],
        "hotspots": hotspots,
        "terms": display_terms,
    }


def grade_label_diagram_answer(expected: str, user_answer: str) -> bool:
    return bool(score_label_diagram_answer(expected, user_answer)["correct"])


def score_label_diagram_answer(expected: str, user_answer: str) -> dict[str, Any]:
    """Bewertet Zuordnungen pro Hotspot — für partielles Lern-Feedback."""
    empty: dict[str, Any] = {"correct": False, "slots": []}
    try:
        expected_map = json.loads(expected)
        user_map = json.loads(user_answer)
    except (json.JSONDecodeError, TypeError):
        return empty
    if not isinstance(expected_map, dict) or not isinstance(user_map, dict):
        return empty

    slots: list[dict[str, Any]] = []
    all_correct = True
    for key, expected_term in expected_map.items():
        user_term = str(user_map.get(key) or "").strip()
        accepted = expected_term if isinstance(expected_term, list) else [expected_term]
        accepted_norm = {_norm(str(item)) for item in accepted if str(item).strip()}
        expected_label = str(accepted[0] if accepted else expected_term).strip()
        slot_ok = bool(user_term) and _norm(user_term) in accepted_norm
        if not slot_ok:
            all_correct = False
        slots.append(
            {
                "id": str(key),
                "correct": slot_ok,
                "expected_term": expected_label,
                "user_term": user_term or None,
            }
        )
    return {"correct": all_correct, "slots": slots}


def normalize_task_format(raw: str | None) -> str:
    return _norm(str(raw or ""))


def is_label_format(fmt: str) -> bool:
    normalized = normalize_task_format(fmt)
    if not normalized:
        return False
    return normalized in _LABEL_FORMATS or any(token in normalized for token in _LABEL_FORMATS)


def is_draw_format(fmt: str) -> bool:
    normalized = normalize_task_format(fmt)
    if not normalized:
        return False
    return normalized in _DRAW_FORMATS or any(token in normalized for token in _DRAW_FORMATS)
