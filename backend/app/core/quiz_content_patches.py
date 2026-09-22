"""Manuelle Quiz-Korrekturen für gespeicherte Einheiten (Referenz Quiz F.MM.QQ)."""

from __future__ import annotations

import re
from typing import Any

_QUIZ_SLOT_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})$")

# Nur wenn reconcile/repair_quiz_question nicht reicht — Felder werden auf die Frage gemerged.
MANUAL_QUIZ_PATCHES: dict[str, dict[str, Any]] = {}


def parse_quiz_slot_ref(ref: str) -> tuple[str, int, int]:
    """'0036.02.07' -> ('0036', module_order=2, question_no=7)."""
    cleaned = str(ref or "").strip()
    match = _QUIZ_SLOT_RE.match(cleaned)
    if not match:
        raise ValueError(f"Ungültige Quiz-Referenz: {ref!r} (Format: 0036.02.07)")
    family = match.group(1)
    module_order = int(match.group(2))
    question_no = int(match.group(3))
    if module_order < 1 or question_no < 1:
        raise ValueError(f"Ungültige Quiz-Referenz: {ref!r}")
    return family, module_order, question_no


def apply_manual_quiz_patch(question: dict[str, Any], slot_ref: str) -> dict[str, Any]:
    patch = MANUAL_QUIZ_PATCHES.get(slot_ref)
    if not patch:
        return question
    out = dict(question)
    for key, value in patch.items():
        if key in {"answer", "explanation", "options", "q", "question_type"}:
            out[key] = value
    return out
