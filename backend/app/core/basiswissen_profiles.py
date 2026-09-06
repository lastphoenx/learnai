"""Fachprofile für strukturiertes Basiswissen (Prompt-Hinweise + Fallbacks)."""

from __future__ import annotations

FOCUS_GROUP_PROMPTS: dict[str, str] = {
    "math": (
        "Mathe: Relationen mit Rollen (z. B. summand, minuend, factor, product, dividend, divisor, quotient). "
        "Typische Muster: Summand + Summand = Summe; Faktor × Faktor = Produkt; Minuend − Subtrahend = Differenz; "
        "Dividend ÷ Divisor = Quotient. Mindestens 2–4 concepts passend zum Kategoriethema."
    ),
    "german": (
        "Deutsch: Wortarten, Satzglieder, Kasus/Deklination, Rechtschreib- oder Grammatikregeln. "
        "Rollen z. B. subject, predicate, object, attribute, nominativ, genitiv, dativ, akkusativ, preposition. "
        "Bei Deklinations-Lückentexten: cloze_templates.grammar.blanks mit case, gender, number, "
        "determiner_type (der-word|ein-word), determiner_stem, adjective_stem, lemma, part (ending|word). "
        "Antworten werden serverseitig aus Regeln berechnet — Metadata muss stimmen. "
        "Ersatzprobe: nur mit maskulinen Nomen, wenn Nominativ vs. Akkusativ gezeigt werden soll "
        "(er/ihn); Neutrum (es/es) und Feminin (sie/sie) beweisen den Fall nicht."
    ),
    "language": (
        "Fremdsprache: Vokabeln, Artikel, Zeitformen, typische Satzmuster. "
        "Rollen und Begriffe in der Zielsprache oder mit deutscher Übersetzung in hint."
    ),
    "nmg": (
        "NMG (Natur, Mensch, Gesellschaft): Fachbegriffe mit Kurzdefinition und Bezug zum Thema "
        "(Geschichte, Geografie, Gesellschaft, Umwelt …). "
        "kind: definition, vocabulary oder relation."
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
    "nominativ": "Nominativ",
    "genitiv": "Genitiv",
    "dativ": "Dativ",
    "akkusativ": "Akkusativ",
    "preposition": "Präposition",
    "term": "Begriff",
    "definition": "Definition",
}
