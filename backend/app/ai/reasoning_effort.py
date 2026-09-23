"""OpenAI Reasoning-Modelle: optionaler reasoning_effort (low / medium / high)."""

from __future__ import annotations

REASONING_EFFORT_VALUES = frozenset({"low", "medium", "high"})


def normalize_reasoning_effort(raw: object) -> str:
    value = str(raw or "").strip().lower()
    if value in REASONING_EFFORT_VALUES:
        return value
    return ""


def is_reasoning_family(model: str) -> bool:
    import re

    return bool(re.match(r"^(o\d|gpt-5)", (model or "").strip().lower()))
