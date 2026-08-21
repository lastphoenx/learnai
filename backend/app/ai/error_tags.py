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


_QUIZ_TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fractions_denominator": ("nenner", "bruch", "brüche", "bruchrechnung", "bruchteil"),
    "fractions_numerator": ("zähler",),
    "fractions_simplify": ("kürzen", "erweitern", "vereinfachen"),
    "fractions_compare": ("vergleichen", "ordnen", "größer", "kleiner"),
    "fractions_add_sub": ("addieren", "subtrahieren", "plus", "minus", "summe"),
    "fractions_mul_div": ("multiplizieren", "dividieren", "mal", "geteilt"),
    "decimals_place": ("dezimal", "kommazahl", "stellenwert", "nachkomma"),
    "decimals_round": ("runden", "gerundet"),
    "place_value": ("stellenwert", "hunderter", "zehner", "einer"),
    "unit_conversion": ("umrechnen", "einheit", "umrechnung"),
    "measures_length": ("meter", "zentimeter", "kilometer", "länge", "km", "cm", "mm"),
    "measures_mass": ("gramm", "kilogramm", "masse", "kg", "g "),
    "measures_volume": ("liter", "milliliter", "volumen", "ml"),
    "measures_area": ("quadrat", "fläche", "m²", "cm²"),
    "measures_time": ("stunde", "minute", "sekunde", "uhrzeit", "zeit"),
    "addition_carry": ("übertrag", "addition", "plus rechnen"),
    "subtraction_borrow": ("entlehnen", "subtraktion", "minus rechnen"),
    "multiplication_table": ("einmaleins", "malreihe", "multiplikation"),
    "division_remainder": ("rest", "division", "teilen"),
    "geometry_area": ("flächeninhalt", "fläche berechnen"),
    "geometry_perimeter": ("umfang", "perimeter"),
    "geometry_angle": ("winkel", "grad"),
    "percent_calc": ("prozent", "%", "prozentrechnung"),
    "ratio_proportion": ("dreisatz", "verhältnis", "proportional"),
    "negative_sign": ("negative", "vorzeichen", "minuszahl"),
    "order_of_operations": ("klammer", "punkt", "strich", "rechenreihenfolge"),
    "reading_comprehension": ("text", "leseverstehen", "absatz"),
    "spelling": ("rechtschreibung", "schreibweise"),
    "grammar": ("grammatik", "zeitform", "satz"),
    "vocabulary": ("wortschatz", "bedeutung", "synonym"),
}


def infer_quiz_error_tags(
    *,
    question: str = "",
    module_title: str = "",
    explanation: str = "",
    math_focus: str = "",
) -> list[str]:
    """Heuristische Fehler-Tags aus Quiz-Frage/Modul (analog zu Prüfungs-error_tags)."""
    blob = " ".join([question, module_title, explanation, math_focus]).lower()
    if not blob.strip():
        return ["method_missing"]
    tags: list[str] = []
    for tag, keywords in _QUIZ_TAG_KEYWORDS.items():
        if any(kw in blob for kw in keywords):
            tags.append(tag)
    if not tags:
        if any(w in blob for w in ("rechnen", "berechnen", "ergebnis", "zahl")):
            tags.append("calculation_error")
        else:
            tags.append("method_missing")
    return tags[:6]


def aggregate_quiz_error_tags(weaknesses: list[dict]) -> list[dict]:
    """Tags aus Schwächen zählen → [{tag, label, count}]."""
    counts: dict[str, int] = {}
    for item in weaknesses:
        for tag in item.get("error_tags") or []:
            key = str(tag).strip().lower()
            if key:
                counts[key] = counts.get(key, 0) + 1
    return [
        {"tag": tag, "label": label_for_tag(tag), "count": count}
        for tag, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


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
