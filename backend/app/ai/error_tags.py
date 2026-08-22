"""Fehler-Muster für Schulprüfungen und App-Quiz — material-first, Taxonomie optional."""

from __future__ import annotations

from app.core.pedagogy_labels import label_in_text, normalize_label, sanitize_pedagogy_field

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

_EXAM_SCHEMA_PLACEHOLDERS = frozenset(
    {
        "snake_case",
        "konkreter fehlertyp aus der pruefung",
        "konkreter fehlertyp aus der prüfung",
        "fehlertyp in den worten der pruefung",
        "fehlertyp in den worten der prüfung",
    }
)

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
    "grammar": ("grammatik", "zeitform", "satz", "deklination", "kasus", "genus"),
    "vocabulary": ("wortschatz", "bedeutung", "synonym"),
}


def label_for_tag(tag: str) -> str:
    key = (tag or "").strip().lower()
    if not key:
        return ""
    if key in ERROR_TAG_LABELS:
        return ERROR_TAG_LABELS[key]
    if key.startswith("label:"):
        return key[6:].replace("_", " ").strip().capitalize()
    return key.replace("_", " ").strip().capitalize()


def pattern_identity(*, label: str = "", tag: str = "") -> tuple[str, str]:
    """Stabiler Schlüssel und Anzeige-Label für Aggregation."""
    clean_label = sanitize_pedagogy_field(str(label or "").strip())
    clean_tag = str(tag or "").strip().lower()
    if clean_tag in _EXAM_SCHEMA_PLACEHOLDERS or clean_tag in {"optional", ""}:
        clean_tag = ""
    if clean_label and normalize_label(clean_label) in _EXAM_SCHEMA_PLACEHOLDERS:
        clean_label = ""
    if clean_tag and clean_tag in ERROR_TAG_LABELS:
        return clean_tag, clean_label or ERROR_TAG_LABELS[clean_tag]
    if clean_label:
        norm = normalize_label(clean_label)
        return f"label:{norm}", clean_label
    if clean_tag:
        return clean_tag, label_for_tag(clean_tag)
    return "", ""


def classify_error_tag(text: str) -> str | None:
    """Optionale Zuordnung zu bekannter Taxonomie — nur wenn klar passend."""
    blob = str(text or "").lower()
    if not blob.strip():
        return None
    for tag, keywords in _QUIZ_TAG_KEYWORDS.items():
        if any(kw in blob for kw in keywords):
            return tag
    return None


def resolve_error_pattern(raw: dict) -> dict:
    """Normalisiert error_patterns[]-Zeile: label primär, tag optional."""
    label = sanitize_pedagogy_field(str(raw.get("label") or "").strip())
    tag = str(raw.get("tag") or "").strip().lower()
    if tag in _EXAM_SCHEMA_PLACEHOLDERS:
        tag = ""
    if not label and tag:
        if tag in ERROR_TAG_LABELS:
            label = ERROR_TAG_LABELS[tag]
        else:
            label = label_for_tag(tag)
    if not tag and label:
        tag = classify_error_tag(label) or ""
    key, display = pattern_identity(label=label, tag=tag)
    if not key:
        return {}
    out: dict = {"label": display[:200], "key": key}
    if tag and tag in ERROR_TAG_LABELS:
        out["tag"] = tag
    count = raw.get("count")
    if isinstance(count, int) and count >= 0:
        out["count"] = count
    examples = raw.get("examples")
    if isinstance(examples, list):
        cleaned = [sanitize_pedagogy_field(str(x)) for x in examples]
        cleaned = [x for x in cleaned if x][:5]
        if cleaned:
            out["examples"] = cleaned
    return out


def resolve_error_label(raw: str) -> str:
    """Einzelnes Fehler-Label aus Freitext oder Legacy-snake_case."""
    text = sanitize_pedagogy_field(str(raw or "").strip())
    if not text:
        return ""
    lower = text.lower()
    if lower in ERROR_TAG_LABELS:
        return ERROR_TAG_LABELS[lower]
    return text[:200]


def infer_quiz_error_tags(
    *,
    question: str = "",
    module_title: str = "",
    explanation: str = "",
    math_focus: str = "",
    material_labels: list[str] | None = None,
) -> list[str]:
    """Fehler-Schlüssel aus Quiz-Kontext — zuerst Material-Labels, dann Taxonomie-Fallback."""
    blob = " ".join([question, module_title, explanation, math_focus]).strip()
    if not blob:
        return ["method_missing"]

    keys: list[str] = []
    for material_label in material_labels or []:
        label = str(material_label or "").strip()
        if not label:
            continue
        if label_in_text(label, blob):
            key, _ = pattern_identity(label=label)
            if key and key not in keys:
                keys.append(key)
    if keys:
        return keys[:6]

    for tag, keywords in _QUIZ_TAG_KEYWORDS.items():
        if any(kw in blob.lower() for kw in keywords) and tag not in keys:
            keys.append(tag)
    if keys:
        return keys[:6]

    if any(w in blob.lower() for w in ("rechnen", "berechnen", "ergebnis", "zahl")):
        return ["calculation_error"]
    key, _ = pattern_identity(label="Lösungsweg unklar")
    return [key or "method_missing"]


def aggregate_quiz_error_tags(weaknesses: list[dict]) -> list[dict]:
    """Tags/Labels aus Schwächen zählen → [{key, tag, label, count}]."""
    counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    for item in weaknesses:
        for tag in item.get("error_tags") or []:
            key = str(tag).strip()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
            if item.get("error_label"):
                labels[key] = str(item["error_label"])
    rows: list[dict] = []
    for key, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        label = labels.get(key) or label_for_tag(key)
        row: dict = {"key": key, "label": label, "count": count}
        if key in ERROR_TAG_LABELS:
            row["tag"] = key
        rows.append(row)
    return rows


def collect_error_items_from_analysis(analysis: dict | None) -> list[dict]:
    """Alle Fehlermuster aus Analyse — [{key, label, tag?}] dedupliziert."""
    if not isinstance(analysis, dict):
        return []
    seen: set[str] = set()
    ordered: list[dict] = []
    for pattern in analysis.get("error_patterns") or []:
        if not isinstance(pattern, dict):
            continue
        resolved = resolve_error_pattern(pattern)
        key = resolved.get("key")
        if not key or key in seen:
            continue
        seen.add(key)
        item = {"key": key, "label": resolved.get("label") or label_for_tag(key)}
        if resolved.get("tag"):
            item["tag"] = resolved["tag"]
        ordered.append(item)
    for task in analysis.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for raw_label in task.get("error_labels") or []:
            label = resolve_error_label(str(raw_label))
            if not label:
                continue
            key, display = pattern_identity(label=label)
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append({"key": key, "label": display})
        for raw_tag in task.get("error_tags") or []:
            label = resolve_error_label(str(raw_tag))
            key, display = pattern_identity(label=label, tag=str(raw_tag).strip().lower())
            if not key or key in seen:
                continue
            seen.add(key)
            item = {"key": key, "label": display}
            if str(raw_tag).strip().lower() in ERROR_TAG_LABELS:
                item["tag"] = str(raw_tag).strip().lower()
            ordered.append(item)
    return ordered


def collect_tags_from_analysis(analysis: dict | None) -> list[str]:
    """Legacy: Schlüssel-Liste für Abwärtskompatibilität."""
    return [item["key"] for item in collect_error_items_from_analysis(analysis)]
