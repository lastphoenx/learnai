"""Kanoniche Fachgruppen-IDs und Rückwärtskompatibilität (mgu → nmg)."""

from __future__ import annotations

FOCUS_GROUP_ALIASES: dict[str, str] = {
    "mgu": "nmg",
}

LEGACY_FOCUS_KEY_PREFIX = "mgu_"
CANONICAL_FOCUS_KEY_PREFIX = "nmg_"


def normalize_focus_group(group: str | None) -> str:
    raw = str(group or "").strip().lower()
    if not raw:
        return "general"
    return FOCUS_GROUP_ALIASES.get(raw, raw)


def normalize_focus_key(key: str | None) -> str:
    raw = str(key or "").strip()
    if raw.startswith(LEGACY_FOCUS_KEY_PREFIX):
        return CANONICAL_FOCUS_KEY_PREFIX + raw[len(LEGACY_FOCUS_KEY_PREFIX) :]
    return raw


def is_nmg_focus(group: str | None) -> bool:
    return normalize_focus_group(group) == "nmg"
