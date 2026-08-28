"""Fachprofile für strukturiertes Basiswissen (Prompt-Hinweise + Fallbacks)."""

from __future__ import annotations

FOCUS_GROUP_PROMPTS: dict[str, str] = {
    "math": (
        "Mathe: Relationen mit Rollen (z. B. summand, minuend, factor, product, dividend, divisor, quotient). "
        "Typische Muster: Summand + Summand = Summe; Faktor × Faktor = Produkt; Minuend − Subtrahend = Differenz; "
        "Dividend ÷ Divisor = Quotient. Mindestens 2–4 concepts passend zum Kategoriethema."
    ),
    "german": (
        "Deutsch: Wortarten, Satzglieder, Rechtschreib- oder Grammatikregeln. "
        "Rollen z. B. subject, predicate, object, attribute. Beispielsätze auf Deutsch."
    ),
    "language": (
        "Fremdsprache: Vokabeln, Artikel, Zeitformen, typische Satzmuster. "
        "Rollen und Begriffe in der Zielsprache oder mit deutscher Übersetzung in hint."
    ),
    "mgu": (
        "MGU: Fachbegriffe mit Kurzdefinition und Bezug zum Thema (Gesellschaft, Geografie, Geschichte …). "
        "kind: definition oder vocabulary."
    ),
    "nature": (
        "Natur & Technik: Fachbegriffe, Prozesse, Einheiten. kind: definition oder relation."
    ),
}

ROLE_LABELS_DE: dict[str, str] = {
    "summand": "Summand",
    "sum": "Summe",
    "minuend": "Minuend",
    "subtrahend": "Subtrahend",
    "difference": "Differenz",
    "factor": "Faktor",
    "product": "Produkt",
    "dividend": "Dividend",
    "divisor": "Divisor",
    "quotient": "Quotient",
    "subject": "Subjekt",
    "predicate": "Prädikat",
    "object": "Objekt",
    "attribute": "Attribut",
    "term": "Begriff",
    "definition": "Definition",
}
