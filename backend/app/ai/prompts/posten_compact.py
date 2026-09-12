"""Ein-Call-Generierung für Heft-Posten (posten_compact) — Chat-HTML-Struktur."""

from __future__ import annotations

from app.ai.prompts.interactive import SOURCE_RULES, learner_style_hint, truncate_material

POSTEN_COMPACT_COUNTS = {
    "cards": 12,
    "quiz": 8,
    "facts_min": 3,
    "facts_max": 6,
}

EXAM_REVIEW_COUNTS = {
    "cards": 15,
    "quiz": 28,
    "facts_min": 4,
    "facts_max": 8,
}

_COMPACT_PRESET_COUNTS = {
    "posten_compact": POSTEN_COMPACT_COUNTS,
    "exam_review": EXAM_REVIEW_COUNTS,
}


def compact_preset_counts(preset_id: str) -> dict[str, int]:
    pid = (preset_id or "posten_compact").strip()
    return dict(_COMPACT_PRESET_COUNTS.get(pid, POSTEN_COMPACT_COUNTS))

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

EXAM_REVIEW_SYSTEM_EXTRA = (
    "Kontext: Lernzielkontrolle / Quer-Wiederholung über mehrere Posten — nicht nur ein Einzelposten.\n"
    f"- facts: {EXAM_REVIEW_COUNTS['facts_min']}-{EXAM_REVIEW_COUNTS['facts_max']} Einträge — quer durch alle Themen der Review-Seiten.\n"
    f"- cards: genau {EXAM_REVIEW_COUNTS['cards']} Karten — quer über Epochen, Personen, Orte und Begriffe.\n"
    f"- quiz: genau {EXAM_REVIEW_COUNTS['quiz']} Prüfungsfragen, je 4 Optionen, genau eine richtig.\n"
    "- timeline: optional; nur wenn ein Zeitstrahl auf den Review-Seiten vorkommt.\n"
    "- Keine Wiederholung eines einzelnen Posten-Schwerpunkts — breite Abdeckung.\n"
)


def build_compact_system_prompt(preset_id: str = "posten_compact") -> str:
    pid = (preset_id or "posten_compact").strip()
    if pid == "exam_review":
        return POSTEN_COMPACT_SYSTEM + "\n" + EXAM_REVIEW_SYSTEM_EXTRA
    return POSTEN_COMPACT_SYSTEM


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
    preset_id: str = "posten_compact",
) -> str:
    counts = compact_preset_counts(preset_id)
    cards = card_target if card_target is not None else counts["cards"]
    quiz = question_target if question_target is not None else counts["quiz"]
    style_hint = learner_style_hint(target_age=target_age, style=style, answer_length=answer_length)
    material_block = ""
    if multimodal:
        if (preset_id or "").strip() == "exam_review":
            material_block = (
                "Material: Siehe angehängte Review-/Intro-Seiten — quer durch alle behandelten Posten.\n"
                "Lies Text, Zeitstrahl, Aufgaben und Lösungen direkt vom Bild.\n"
                "Erstelle eine Lernzielkontrolle über mehrere Themen hinweg — nicht nur einen Einzelposten.\n"
                "Nutze keine erfundenen Epochen; alle Daten aus den Bildern.\n"
            )
        else:
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
    default_brief = (
        "Erstelle eine Lernzielkontrolle als Quer-Wiederholung über alle Review-Seiten."
        if (preset_id or "").strip() == "exam_review"
        else "Erstelle einen kompakten Lerntrainer für diese Doppelseite."
    )
    return (
        f"Thema/Titel: {title}\n"
        f"Auftrag: {brief or default_brief}\n"
        f"Fach: {subject or 'Schulfach'}\n"
        f"Sprache: {language}\n"
        f"Zielalter: {target_age or 'offen'}\n"
        f"Schwierigkeit 1-5: {difficulty}\n"
        f"Zielumfang: {cards} Lernkarten, {quiz} Quizfragen.\n"
        f"{style_hint}\n\n"
        f"{SOURCE_RULES}\n\n"
        f"{material_block}"
    )
