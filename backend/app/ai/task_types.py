"""Aufgabentypen für Lerneinheiten (Generierung) — Labels, Hilfen, KI-Prompts."""

from __future__ import annotations

UNIT_TASK_TYPES: list[dict] = [
    {
        "key": "mixed",
        "label": "Gemischt",
        "select_label": "Gemischt (Lerntext lesen → Quiz, Block für Block)",
        "description": "Standard für neue Themen: kurze Erklärung pro Block, danach Verständnisfragen.",
        "hint": "Mischung aus kurzem Lerntext und Quizfragen.",
    },
    {
        "key": "explain",
        "label": "Erklären",
        "select_label": "Erklären (ausführlicher Text, kaum Quiz)",
        "description": "Wenig Quiz, dafür ausführliche, didaktische Erklärung — gut zum Einstieg lesen.",
        "hint": "Schwerpunkt Erklären: ausführlicher Lerntext, nur 1–2 Kontrollfragen.",
    },
    {
        "key": "quiz",
        "label": "Quiz",
        "select_label": "Quiz (kurzer Text, viele Verständnisfragen)",
        "description": "Kurze Einleitung, dann viele Fragen — wenn das Thema schon bekannt ist.",
        "hint": "Schwerpunkt Quiz: kurze Einleitung, viele Verständnisfragen.",
    },
    {
        "key": "practice",
        "label": "Übungen",
        "select_label": "Übungen (selbst lösen, mit Lösungshinweis)",
        "description": "Aufgaben zum Selberlösen mit Lösungshinweisen — allgemein, nicht nur Mathe.",
        "hint": "Übungsaufgaben zum Selberlösen, danach Lösungshinweis im Quiz.",
    },
    {
        "key": "math",
        "label": "Rechnen",
        "select_label": "Rechnen (Mathe-Aufgaben mit Lösungsweg)",
        "description": "Rechenaufgaben mit klaren Zahlen, Schritten und Lösungsweg — Mathe-Schwerpunkt wählen.",
        "hint": "Mathematik: zahlreiche Rechenaufgaben, Zwischenschritte, Einheiten beachten, "
        "Lösungsweg kurz erklären. An den Mathe-Schwerpunkt und das Schulmaterial halten.",
    },
    {
        "key": "workbook",
        "label": "Am Heft",
        "select_label": "Am Heft (nah am Arbeitsblatt, gleiche Aufgabenarten)",
        "description": "So nah wie möglich am hochgeladenen Schulmaterial: gleiche Aufgabentypen, Formulierungen, Schwierigkeit.",
        "hint": "Orientiere dich eng am Lernmittel/Arbeitsblatt: gleiche Aufgabenarten, ähnliche Zahlen "
        "und Formulierungen wie in den Quellen. Keine neuen Themen erfinden.",
    },
    {
        "key": "review",
        "label": "Wiederholung",
        "select_label": "Wiederholung (bekannter Stoff, ähnliche Aufgaben)",
        "description": "Zu einer bestehenden Einheit: weniger Erklärung, mehr Wiederholung und ähnliche Aufgaben.",
        "hint": "Wiederholung und Festigung: kurze Auffrischung, dann viele ähnliche Aufgaben und Quizfragen "
        "zum bereits Gelernten. Kein neues Thema einführen.",
    },
    {
        "key": "exam",
        "label": "Kurzprüfung",
        "select_label": "Kurzprüfung (nur Aufgaben, keine Hilfen)",
        "description": "Prüfungsmodus: nur Aufgaben, keine Hilfen — Leistung messen.",
        "hint": "Kurzprüfung: nur Aufgaben, knappe Anweisungen, klare richtige Antworten.",
    },
    {
        "key": "vocab",
        "label": "Vokabeln",
        "select_label": "Vokabeln (Fremdsprache: Wort, Bedeutung, Beispiel)",
        "description": "Fremdsprachen: Wort, Bedeutung, Beispielsatz, Aussprache-Hinweis, Mini-Quiz.",
        "hint": "Sprachkurs/Vokabeln: Wort, Bedeutung, Beispielsatz, Mini-Quiz.",
    },
    {
        "key": "interactive",
        "label": "Lerntrainer",
        "select_label": "Lerntrainer (Karten, Check, Eingabe-Übungen, Wissens-Hub)",
        "description": "Wissenskarten, Lernkarten umdrehen, Quiz-Challenge — spielerisch mit Fortschritt.",
        "hint": (
            "Interaktiver Lerntrainer: viele Lernkarten und Quizfragen, kurze Antworten, "
            "Themenbereiche, motivierend und altersgerecht."
        ),
    },
]

UNIT_TASK_KEYS = frozenset(t["key"] for t in UNIT_TASK_TYPES)

# KI-Modell-Routing (Lerner-Einstellungen) — neue Typen nutzen nächstpassenden Key
AI_TASK_FOR_UNIT: dict[str, str] = {
    "mixed": "mixed",
    "explain": "explain",
    "quiz": "quiz",
    "practice": "practice",
    "math": "practice",
    "workbook": "practice",
    "review": "quiz",
    "exam": "exam",
    "vocab": "vocab",
    "interactive": "mixed",
}

MATH_FOCUS_OPTIONS: list[dict] = [
    {"key": "", "label": "— Mathe-Schwerpunkt (optional) —"},
    {"key": "fractions", "label": "Bruchrechnen"},
    {"key": "decimals", "label": "Dezimalzahlen & Komma"},
    {"key": "place_value", "label": "Stellenwert / Zahlenräume (10er, 100er, 1000er …)"},
    {"key": "add_sub", "label": "Addition & Subtraktion"},
    {"key": "mul_div", "label": "Multiplikation & Division"},
    {"key": "geometry", "label": "Geometrie (Formen, Winkel, Umfang, Fläche …)"},
    {
        "key": "measures",
        "label": "Größen & Einheiten (mm–km, ml–l, mg–t, m², ha, a …)",
    },
    {"key": "patterns", "label": "Reihen, Muster & Folgen"},
    {"key": "percent_ratio", "label": "Prozent, Verhältnis & Dreisatz"},
    {"key": "negative", "label": "Negative Zahlen"},
    {"key": "other", "label": "Sonstiges (im Auftrag genauer beschreiben)"},
]

MATH_FOCUS_HINTS: dict[str, str] = {
    "fractions": "Schwerpunkt Bruchrechnen (darstellen, erweitern, kürzen, rechnen).",
    "decimals": "Schwerpunkt Dezimalzahlen und Kommaschreibweise.",
    "place_value": "Schwerpunkt Stellenwert und Zahlenräume (Zehner, Hunderter, Tausender …).",
    "add_sub": "Schwerpunkt Addition und Subtraktion.",
    "mul_div": "Schwerpunkt Multiplikation und Division.",
    "geometry": "Schwerpunkt Geometrie.",
    "measures": "Schwerpunkt Größen und Einheiten (Länge, Masse, Volumen, Fläche, Zeit — korrekte Umrechnung).",
    "patterns": "Schwerpunkt Reihen, Muster und Folgen.",
    "percent_ratio": "Schwerpunkt Prozent, Verhältnis und Dreisatz.",
    "negative": "Schwerpunkt negative Zahlen.",
    "other": "",
}


def task_types_public() -> list[dict]:
    return UNIT_TASK_TYPES


def math_focus_public() -> list[dict]:
    return MATH_FOCUS_OPTIONS


def hint_for_task(task_key: str) -> str:
    for item in UNIT_TASK_TYPES:
        if item["key"] == task_key:
            return item["hint"]
    return UNIT_TASK_TYPES[0]["hint"]


def augment_brief(brief: str | None, *, task_key: str, math_focus: str | None) -> str:
    parts = [brief.strip() if brief else ""]
    focus = (math_focus or "").strip()
    if focus and focus in MATH_FOCUS_HINTS and MATH_FOCUS_HINTS[focus]:
        label = next((o["label"] for o in MATH_FOCUS_OPTIONS if o["key"] == focus), focus)
        parts.append(f"Mathe-Schwerpunkt: {label}. {MATH_FOCUS_HINTS[focus]}")
    return "\n\n".join(p for p in parts if p)
