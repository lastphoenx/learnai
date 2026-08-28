"""Fach-Schwerpunkte für Lerneinheiten (Mathe, Sprachen, NMG, …)."""

from __future__ import annotations

import re

from app.core.focus_groups import normalize_focus_group, normalize_focus_key

FocusOption = dict[str, str]
FocusGroup = dict[str, object]

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

_NMG_OPTIONS: list[FocusOption] = [
    {"key": "nmg_nature", "label": "Natur & Umwelt"},
    {"key": "nmg_health", "label": "Gesundheit & Körper"},
    {"key": "nmg_nutrition", "label": "Ernährung"},
    {"key": "nmg_family", "label": "Familie & Beziehungen"},
    {"key": "nmg_economy", "label": "Wirtschaft & Konsum"},
    {"key": "nmg_civics", "label": "Politik & Demokratie"},
    {"key": "nmg_history", "label": "Geschichte"},
    {"key": "nmg_geography", "label": "Geografie (CH, Europa, Welt)"},
    {"key": "nmg_media", "label": "Medien & Information"},
    {"key": "nmg_culture", "label": "Kultur & Religion"},
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
    {"id": "nmg", "label": "NMG (Natur, Mensch, Gesellschaft)", "options": _NMG_OPTIONS},
    {"id": "german", "label": "Deutsch", "options": _GERMAN_OPTIONS},
    {"id": "nature", "label": "Natur & Technik", "options": _NATURE_OPTIONS},
]

FOCUS_HINTS: dict[str, str] = {
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
    "nmg_nature": "Schwerpunkt Natur und Umwelt.",
    "nmg_health": "Schwerpunkt Gesundheit und Körper.",
    "nmg_nutrition": "Schwerpunkt Ernährung.",
    "nmg_family": "Schwerpunkt Familie und soziale Beziehungen.",
    "nmg_economy": "Schwerpunkt Wirtschaft und Konsum.",
    "nmg_civics": "Schwerpunkt Politik und Demokratie.",
    "nmg_history": "Schwerpunkt Geschichte.",
    "nmg_geography": "Schwerpunkt Geografie.",
    "nmg_media": "Schwerpunkt Medien und Information.",
    "nmg_culture": "Schwerpunkt Kultur und Religion.",
    "de_spelling": "Schwerpunkt Rechtschreibung.",
    "de_grammar": "Schwerpunkt Grammatik.",
    "de_reading": "Schwerpunkt Lesen und Textverständnis.",
    "de_writing": "Schwerpunkt Schreiben.",
    "de_vocab": "Schwerpunkt Wortschatz.",
    "de_lit": "Schwerpunkt Literatur.",
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
# Legacy mgu_* keys → gleiche Labels
for _key, _label in list(_FOCUS_LABELS.items()):
    if _key.startswith("nmg_"):
        _FOCUS_LABELS["mgu_" + _key[4:]] = _label


def focus_label(key: str | None) -> str | None:
    if not key:
        return None
    normalized = normalize_focus_key(key)
    return _FOCUS_LABELS.get(normalized, _FOCUS_LABELS.get(key, key))


def focus_hint(key: str | None) -> str:
    if not key:
        return ""
    normalized = normalize_focus_key(key)
    return FOCUS_HINTS.get(normalized, FOCUS_HINTS.get(str(key or ""), ""))


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
    if re.search(
        r"\bnmg\b|natur.*mensch.*gesellschaft|mensch.*natur.*gesellschaft|"
        r"mensch|gesellschaft|umwelt|\bmgu\b|räume.*zeit|rzg",
        text,
    ):
        return "nmg"
    if re.search(r"natur.*technik|\bn&t\b|biologie|physik|chemie", text):
        return "nature"
    return None


def focus_options_for_group(group_id: str | None) -> list[FocusOption]:
    canonical = normalize_focus_group(group_id)
    if not canonical or canonical not in _GROUP_BY_ID:
        return []
    return list(_GROUP_BY_ID[canonical]["options"])  # type: ignore[arg-type]


def focus_groups_public() -> list[dict]:
    return [
        {"id": g["id"], "label": g["label"], "options": g["options"]}
        for g in SUBJECT_FOCUS_GROUPS
    ]


def all_focus_options_flat() -> list[FocusOption]:
    """Flache Liste für API-Rückwärtskompatibilität (math_focus)."""
    return [{"key": "", "label": "— Schwerpunkt (optional) —"}, *_ALL_OPTIONS]
