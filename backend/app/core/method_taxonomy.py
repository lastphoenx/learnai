"""Lösungswege / Rechenstrategien — Taxonomie für Generierung, Analyse und Bewertung."""

from __future__ import annotations

import re

METHOD_IDS = frozenset(
    {
        "mental",
        "notes",
        "numberline",
        "written",
        "decomposition",
        "supplement",
        "method_choice",
        "other",
    }
)

METHOD_LABELS: dict[str, str] = {
    "mental": "Im Kopf",
    "notes": "Mit Notizen",
    "numberline": "Rechenstrich",
    "written": "Schriftlich",
    "decomposition": "Zerlegung",
    "supplement": "Ergänzen",
    "method_choice": "Strategiewahl",
    "other": "Sonstiges",
}

METHOD_HINTS: dict[str, tuple[str, ...]] = {
    "mental": ("kopf", "im kopf", "kopfrechn"),
    "notes": ("notiz", "notiere", "zwischenschritt", "aufschreib"),
    "numberline": ("rechenstrich", "zahlengerade", "sprung", "bogen"),
    "written": ("schriftlich", "untereinander", "spalte", "stellenwert", "komma ausricht"),
    "decomposition": ("zerleg", "aufteil", "teile in", "splitt"),
    "supplement": ("ergänz", "zähle hoch", "differenz", "fehlend"),
    "method_choice": ("vorgehen", "methode", "strategie", "wie würdest"),
}

_CLASSIFY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("method_choice", re.compile(r"welches?\s+(vorgehen|methode)|geeignet(es)?\s+vorgehen|strategie\s+wählen", re.I)),
    ("mental", re.compile(r"\bim\s+kopf\b|kopfrechn", re.I)),
    ("notes", re.compile(r"mit\s+notiz|notiere\s+(deine|meine)\s+rechenschritt", re.I)),
    ("numberline", re.compile(r"rechenstrich|zahlengerade", re.I)),
    ("written", re.compile(r"schriftlich|untereinander\s+stehen|spalten", re.I)),
    ("decomposition", re.compile(r"zerleg|aufteil", re.I)),
    ("supplement", re.compile(r"ergänz|zähle\s+hoch", re.I)),
]


def normalize_method_id(value: str | None) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    if raw in METHOD_IDS:
        return raw
    aliases = {
        "kopf": "mental",
        "head": "mental",
        "notizen": "notes",
        "rechenstrich": "numberline",
        "schriftlich": "written",
        "zerlegung": "decomposition",
        "ergaenzen": "supplement",
        "ergänzen": "supplement",
    }
    return aliases.get(raw)


def classify_method(text: str, *, kind: str | None = None) -> str:
    lower = str(text or "").lower()
    if kind == "merk":
        for method_id, pattern in _CLASSIFY_PATTERNS:
            if method_id == "method_choice":
                continue
            if pattern.search(lower):
                return method_id
        if re.search(r"vorgehen|strategie|wann\s+welch", lower):
            return "method_choice"
        return "other"
    if kind == "mental":
        return "mental"
    if kind == "input":
        for method_id, pattern in _CLASSIFY_PATTERNS:
            if method_id == "method_choice":
                continue
            if pattern.search(lower):
                return method_id
        return "other"
    for method_id, pattern in _CLASSIFY_PATTERNS:
        if pattern.search(lower):
            return method_id
    return "other"


def method_label(method_id: str | None) -> str:
    key = normalize_method_id(method_id) or str(method_id or "other")
    return METHOD_LABELS.get(key, METHOD_LABELS["other"])
