"""Fach-Schwerpunkte für Lerneinheiten (Mathe, Sprachen, MGU, …)."""

from __future__ import annotations

import re

FocusOption = dict[str, str]
FocusGroup = dict[str, object]

# Rückwärtskompatibel: bestehende math_focus-Keys bleiben unverändert.
_MATH_OPTIONS: list[FocusOption] = [
    {"key": "fractions", "label": "Bruchrechnen"},
    {"key": "decimals", "label": "Dezimalzahlen & Komma"},
    {"key": "place_value", "label": "Stellenwert / Zahlenräume"},
    {"key": "add_sub", "label": "Addition & Subtraktion"},
    {"key": "mul_div", "label": "Multiplikation & Division"},
    {"key": "geometry", "label": "Geometrie"},
    {"key": "measures", "label": "Größen & Einheiten"},
    {"key": "patterns", "label": "Reihen, Muster & Folgen"},
    {"key": "percent_ratio", "label": "Prozent, Verhältnis & Dreisatz"},
    {"key": "negative", "label": "Negative Zahlen"},
    {"key": "other", "label": "Sonstiges Mathe"},
]

_LANGUAGE_OPTIONS: list[FocusOption] = [
    {"key": "lang_vocab", "label": "Vokabular / Wortschatz"},
    {"key": "lang_verbs", "label": "Verben (Konjugation, unregelmässig)"},
    {"key": "lang_nouns_adj", "label": "Nomen, Artikel, Adjektive"},
    {"key": "lang_pronouns", "label": "Pronomen"},
    {"key": "lang_tenses_pres", "label": "Zeitformen: Präsens / Gegenwart"},
    {"key": "lang_tenses_past", "label": "Zeitformen: Präteritum / Imparfait"},
    {"key": "lang_tenses_perf", "label": "Zeitformen: Perfekt / Passé composé"},
    {"key": "lang_tenses_pqp", "label": "Zeitformen: Plusquamperfekt"},
    {"key": "lang_conditional", "label": "Konditional / Futur"},
    {"key": "lang_grammar", "label": "Grammatik allgemein"},
    {"key": "lang_reading", "label": "Leseverständnis"},
    {"key": "lang_writing", "label": "Schreiben / Ausdruck"},
]

_MGU_OPTIONS: list[FocusOption] = [
    {"key": "mgu_health", "label": "Gesundheit & Körper"},
    {"key": "mgu_nutrition", "label": "Ernährung"},
    {"key": "mgu_family", "label": "Familie & Beziehungen"},
    {"key": "mgu_economy", "label": "Wirtschaft & Konsum"},
    {"key": "mgu_civics", "label": "Politik & Demokratie"},
    {"key": "mgu_history", "label": "Geschichte"},
    {"key": "mgu_geography", "label": "Geografie (CH, Europa, Welt)"},
    {"key": "mgu_environment", "label": "Umwelt & Nachhaltigkeit"},
    {"key": "mgu_media", "label": "Medien & Information"},
    {"key": "mgu_culture", "label": "Kultur & Religion"},
]

_GERMAN_OPTIONS: list[FocusOption] = [
    {"key": "de_spelling", "label": "Rechtschreibung"},
    {"key": "de_grammar", "label": "Grammatik"},
    {"key": "de_reading", "label": "Lesen & Textverständnis"},
    {"key": "de_writing", "label": "Schreiben & Aufsatz"},
    {"key": "de_vocab", "label": "Wortschatz"},
    {"key": "de_lit", "label": "Literatur"},
]

_NATURE_OPTIONS: list[FocusOption] = [
    {"key": "nt_biology", "label": "Biologie"},
    {"key": "nt_physics", "label": "Physik"},
    {"key": "nt_chemistry", "label": "Chemie"},
    {"key": "nt_technology", "label": "Technik"},
]

SUBJECT_FOCUS_GROUPS: list[FocusGroup] = [
    {"id": "math", "label": "Mathematik", "options": _MATH_OPTIONS},
    {"id": "language", "label": "Sprachen", "options": _LANGUAGE_OPTIONS},
    {"id": "mgu", "label": "Mensch, Gesellschaft & Umwelt", "options": _MGU_OPTIONS},
    {"id": "german", "label": "Deutsch", "options": _GERMAN_OPTIONS},
    {"id": "nature", "label": "Natur & Technik", "options": _NATURE_OPTIONS},
]

FOCUS_HINTS: dict[str, str] = {
    # Mathe
    "fractions": "Schwerpunkt Bruchrechnen (darstellen, erweitern, kürzen, rechnen).",
    "decimals": "Schwerpunkt Dezimalzahlen und Kommaschreibweise.",
    "place_value": "Schwerpunkt Stellenwert und Zahlenräume.",
    "add_sub": "Schwerpunkt Addition und Subtraktion.",
    "mul_div": "Schwerpunkt Multiplikation und Division.",
    "geometry": "Schwerpunkt Geometrie.",
    "measures": "Schwerpunkt Größen und Einheiten.",
    "patterns": "Schwerpunkt Reihen, Muster und Folgen.",
    "percent_ratio": "Schwerpunkt Prozent, Verhältnis und Dreisatz.",
    "negative": "Schwerpunkt negative Zahlen.",
    "other": "",
    # Sprachen
    "lang_vocab": "Schwerpunkt Wortschatz und Vokabeln.",
    "lang_verbs": "Schwerpunkt Verben: Konjugation, unregelmässige Formen.",
    "lang_nouns_adj": "Schwerpunkt Nomen, Artikel und Adjektive.",
    "lang_pronouns": "Schwerpunkt Pronomen.",
    "lang_tenses_pres": "Schwerpunkt Präsens / Gegenwart.",
    "lang_tenses_past": "Schwerpunkt Präteritum / Imparfait.",
    "lang_tenses_perf": "Schwerpunkt Perfekt / Passé composé.",
    "lang_tenses_pqp": "Schwerpunkt Plusquamperfekt.",
    "lang_conditional": "Schwerpunkt Konditional und Futur.",
    "lang_grammar": "Schwerpunkt Grammatik.",
    "lang_reading": "Schwerpunkt Leseverständnis.",
    "lang_writing": "Schwerpunkt schriftlicher Ausdruck.",
    # MGU
    "mgu_health": "Schwerpunkt Gesundheit und Körper.",
    "mgu_nutrition": "Schwerpunkt Ernährung.",
    "mgu_family": "Schwerpunkt Familie und soziale Beziehungen.",
    "mgu_economy": "Schwerpunkt Wirtschaft und Konsum.",
    "mgu_civics": "Schwerpunkt Politik und Demokratie.",
    "mgu_history": "Schwerpunkt Geschichte.",
    "mgu_geography": "Schwerpunkt Geografie.",
    "mgu_environment": "Schwerpunkt Umwelt und Nachhaltigkeit.",
    "mgu_media": "Schwerpunkt Medien und Information.",
    "mgu_culture": "Schwerpunkt Kultur und Religion.",
    # Deutsch
    "de_spelling": "Schwerpunkt Rechtschreibung.",
    "de_grammar": "Schwerpunkt Grammatik.",
    "de_reading": "Schwerpunkt Lesen und Textverständnis.",
    "de_writing": "Schwerpunkt Schreiben.",
    "de_vocab": "Schwerpunkt Wortschatz.",
    "de_lit": "Schwerpunkt Literatur.",
    # Natur & Technik
    "nt_biology": "Schwerpunkt Biologie.",
    "nt_physics": "Schwerpunkt Physik.",
    "nt_chemistry": "Schwerpunkt Chemie.",
    "nt_technology": "Schwerpunkt Technik.",
}

_GROUP_BY_ID = {str(g["id"]): g for g in SUBJECT_FOCUS_GROUPS}

_ALL_OPTIONS: list[FocusOption] = []
for _group in SUBJECT_FOCUS_GROUPS:
    for _opt in _group["options"]:  # type: ignore[union-attr]
        _ALL_OPTIONS.append(_opt)

_FOCUS_LABELS = {o["key"]: o["label"] for o in _ALL_OPTIONS if o["key"]}


def focus_label(key: str | None) -> str | None:
    if not key:
        return None
    return _FOCUS_LABELS.get(key, key)


def focus_hint(key: str | None) -> str:
    if not key:
        return ""
    return FOCUS_HINTS.get(key, "")


def detect_focus_group(*, subject: str | None, task_type: str) -> str | None:
    if task_type == "vocab":
        return "language"
    if task_type == "math":
        return "math"
    text = (subject or "").lower()
    if not text.strip():
        return None
    if re.search(r"mathe|math|rechnen|arith", text):
        return "math"
    if re.search(
        r"franz|engl|ital|fremdsprach|sprach|langue|english|french|vocab",
        text,
    ):
        return "language"
    if re.search(r"deutsch(?!\s*als\s*fremd)", text) or text.strip() == "de":
        return "german"
    if re.search(r"mensch|gesellschaft|umwelt|\bmgu\b|räume.*zeit|rzg", text):
        return "mgu"
    if re.search(r"natur.*technik|\bn&t\b|biologie|physik|chemie", text):
        return "nature"
    return None


def focus_options_for_group(group_id: str | None) -> list[FocusOption]:
    if not group_id or group_id not in _GROUP_BY_ID:
        return []
    return list(_GROUP_BY_ID[group_id]["options"])  # type: ignore[arg-type]


def focus_groups_public() -> list[dict]:
    return [
        {"id": g["id"], "label": g["label"], "options": g["options"]}
        for g in SUBJECT_FOCUS_GROUPS
    ]


def all_focus_options_flat() -> list[FocusOption]:
    """Flache Liste für API-Rückwärtskompatibilität (math_focus)."""
    return [{"key": "", "label": "— Schwerpunkt (optional) —"}, *_ALL_OPTIONS]
