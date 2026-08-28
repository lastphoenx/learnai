"""Generische Diagramm-Beschriftung: Hotspots aus Begriffen, ohne thematische Hardcodes."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any

_LABEL_FORMATS = frozenset(
    {"label", "beschriften", "beschriftung", "zuordnen", "benennen", "markieren"}
)
_DRAW_FORMATS = frozenset(
    {"draw", "zeichnen", "zeichne", "male", "malen", "skizzieren", "skizze"}
)


def _norm(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "", raw)


def _slug_term(term: str, index: int) -> str:
    slug = _norm(term)[:32]
    return slug or f"term_{index}"


def build_label_diagram_from_terms(
    terms: list[str],
    *,
    title: str = "Fachbegriffe zuordnen",
    instruction: str | None = None,
    placements: list[dict[str, Any]] | None = None,
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

    hotspots: list[dict[str, Any]] = []
    count = min(len(unique), 8)
    for index, term in enumerate(unique[:8]):
        placed = placement_map.get(_norm(term))
        if placed:
            x, y = placed
        else:
            angle = (2 * math.pi * index / count) - math.pi / 2
            x = 0.5 + 0.34 * math.cos(angle)
            y = 0.5 + 0.34 * math.sin(angle)
        hotspots.append(
            {
                "id": _slug_term(term, index),
                "x": round(x, 3),
                "y": round(y, 3),
                "accept": [term],
            }
        )

    return {
        "template": "generic",
        "title": title[:120],
        "instruction": (
            instruction or "Tippe einen Begriff an, dann die passende Stelle auf dem Schema."
        )[:300],
        "hotspots": hotspots,
        "terms": unique[:8],
    }


def grade_label_diagram_answer(expected: str, user_answer: str) -> bool:
    try:
        expected_map = json.loads(expected)
        user_map = json.loads(user_answer)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(expected_map, dict) or not isinstance(user_map, dict):
        return False
    if set(expected_map.keys()) != set(user_map.keys()):
        return False
    for key, expected_term in expected_map.items():
        user_term = str(user_map.get(key) or "").strip()
        accepted = expected_term if isinstance(expected_term, list) else [expected_term]
        accepted_norm = {_norm(str(item)) for item in accepted if str(item).strip()}
        if _norm(user_term) not in accepted_norm:
            return False
    return True


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
