"""Ein-Call-Generierung für Heft-Posten (posten_compact) — Chat-HTML-Struktur."""

from __future__ import annotations

from app.ai.prompts.interactive import SOURCE_RULES, learner_style_hint, truncate_material

POSTEN_COMPACT_COUNTS = {
    "cards": 12,
    "quiz": 8,
    "facts_min": 3,
    "facts_max": 6,
}

POSTEN_COMPACT_SYSTEM = (
    "Du erstellst einen kompakten Lerntrainer aus Heft-/Arbeitsblatt-Fotos oder -Text. "
    "Antworte NUR mit JSON, ohne Markdown.\n"
    "Ein zusammenhängendes Ganze — kein Modul-Splitting, keine Meta-Kategorie «Lösungswege».\n"
    "Schema:\n"
    '{"goal":"Lernziel Du-Form 1-2 Sätze",'
    '"facts":[{"title":"Kurztitel","text":"2-4 Sätze aus dem Material"}],'
    '"cards":[{"question":"echte Wissensfrage","answer":"kurze Antwort","tip":"optional"}],'
    '"quiz":[{"q":"Frage","options":["A","B","C","D"],"answer":0,"explanation":"1 Satz"}],'
    '"timeline":{"title":"Epochen auf dem Zeitstrahl","slots":[{"label":"Epoche","hint":"Datumsbereich"}]}}\n'
    "Regeln:\n"
    f"- facts: {POSTEN_COMPACT_COUNTS['facts_min']}-{POSTEN_COMPACT_COUNTS['facts_max']} Einträge — Kernwissen des Postens.\n"
    f"- cards: genau {POSTEN_COMPACT_COUNTS['cards']} Karten — aktives Erinnern, keine Tautologie.\n"
    f"- quiz: genau {POSTEN_COMPACT_COUNTS['quiz']} Fragen, je 4 Optionen, genau eine richtig.\n"
    "- timeline: optional nur bei Zeitstrahl/Epochen im Material; mindestens 4 slots wenn gesetzt.\n"
    "- Vermeide «Was bedeutet «X»?» — stattdessen aktive Wissensfragen wie «Wer untersucht …?» oder «Welche Zeitspanne …?».\n"
    "- Keine Datums-Zeiträume oder einzelnen Jahreszahlen als Begriff X in Karten.\n"
    "- Keine Begriffe wie «Einleitung lesen», «Lineal unterstreichen», «Form prüfen» als Karten.\n"
    "- Antwort darf den Begriff nicht nur wiederholen («Fundstücke: Fundstücke» verboten).\n"
    "- Zahlen und Datumsangaben exakt wie im Heft — nicht kürzen oder abschneiden.\n"
    "- Keine Duplikate über cards und quiz.\n"
    "- Kein ISBN/Buchcover-Meta.\n"
    "- quiz.answer ist 0-basierter Index der richtigen Option.\n"
)


def build_posten_compact_prompt(
    *,
    title: str,
    brief: str,
    subject: str | None,
    language: str,
    target_age: str | None,
    difficulty: int,
    style: str,
    answer_length: str,
    notes: str,
    multimodal: bool = False,
    card_target: int | None = None,
    question_target: int | None = None,
) -> str:
    cards = card_target if card_target is not None else POSTEN_COMPACT_COUNTS["cards"]
    quiz = question_target if question_target is not None else POSTEN_COMPACT_COUNTS["quiz"]
    style_hint = learner_style_hint(target_age=target_age, style=style, answer_length=answer_length)
    material_block = ""
    if multimodal:
        material_block = (
            "Material: Siehe angehängte Heft-Fotos — lies Text, Zeitstrahl, Aufgaben und Lösungen direkt vom Bild.\n"
            "Nutze keine erfundenen Epochen; alle Daten aus den Bildern.\n"
        )
    else:
        material = truncate_material(notes)
        material_block = (
            f"Material (Text aus Quellen — nutze Inhalt exakt):\n"
            f"{material or '(keine Quellen — nutze Titel und Auftrag)'}\n"
        )
    return (
        f"Thema/Titel: {title}\n"
        f"Auftrag: {brief or 'Erstelle einen kompakten Lerntrainer für diese Doppelseite.'}\n"
        f"Fach: {subject or 'Schulfach'}\n"
        f"Sprache: {language}\n"
        f"Zielalter: {target_age or 'offen'}\n"
        f"Schwierigkeit 1-5: {difficulty}\n"
        f"Zielumfang: {cards} Lernkarten, {quiz} Quizfragen.\n"
        f"{style_hint}\n\n"
        f"{SOURCE_RULES}\n\n"
        f"{material_block}"
    )
