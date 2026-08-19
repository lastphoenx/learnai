"""Fehler-Tags für Schulprüfungs-Analyse (snake_case → deutsches Label)."""

from __future__ import annotations

ERROR_TAG_LABELS: dict[str, str] = {
    "fractions_denominator": "Brüche: Nenner verwechselt",
    "fractions_numerator": "Brüche: Zähler verwechselt",
    "fractions_simplify": "Brüche: Kürzen/Erweitern",
    "fractions_compare": "Brüche: Vergleichen/Ordnen",
    "fractions_add_sub": "Brüche: Addieren/Subtrahieren",
    "fractions_mul_div": "Brüche: Multiplizieren/Dividieren",
    "decimals_place": "Dezimalzahlen: Stellenwert",
    "decimals_round": "Dezimalzahlen: Runden",
    "place_value": "Stellenwert verwechselt",
    "unit_conversion": "Einheiten-Umrechnung",
    "measures_length": "Längenangaben",
    "measures_mass": "Massenangaben",
    "measures_volume": "Volumenangaben",
    "measures_area": "Flächenangaben",
    "measures_time": "Zeitangaben",
    "addition_carry": "Addition: Übertrag",
    "subtraction_borrow": "Subtraktion: Entlehnen",
    "multiplication_table": "Einmaleins / Malreihen",
    "division_remainder": "Division: Rest",
    "geometry_area": "Geometrie: Fläche",
    "geometry_perimeter": "Geometrie: Umfang",
    "geometry_angle": "Geometrie: Winkel",
    "percent_calc": "Prozentrechnung",
    "ratio_proportion": "Verhältnis / Dreisatz",
    "negative_sign": "Negative Zahlen: Vorzeichen",
    "order_of_operations": "Rechenreihenfolge",
    "reading_comprehension": "Textverständnis",
    "spelling": "Rechtschreibung",
    "grammar": "Grammatik",
    "vocabulary": "Wortschatz",
    "careless_error": "Flüchtigkeitsfehler",
    "method_missing": "Lösungsweg fehlt",
    "calculation_error": "Rechenfehler",
}


def label_for_tag(tag: str) -> str:
    key = (tag or "").strip().lower()
    if not key:
        return ""
    if key in ERROR_TAG_LABELS:
        return ERROR_TAG_LABELS[key]
    return key.replace("_", " ").capitalize()


def collect_tags_from_analysis(analysis: dict | None) -> list[str]:
    """Alle Tags aus error_patterns und tasks[].error_tags sammeln."""
    if not isinstance(analysis, dict):
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for pattern in analysis.get("error_patterns") or []:
        if not isinstance(pattern, dict):
            continue
        tag = str(pattern.get("tag") or "").strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    for task in analysis.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for raw in task.get("error_tags") or []:
            tag = str(raw).strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                ordered.append(tag)
    return ordered
