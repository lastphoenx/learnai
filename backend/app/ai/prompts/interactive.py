"""Prompts für interaktiven Lerntrainer (Plan → Karten → Quiz)."""

from __future__ import annotations

from app.ai.prompts.pedagogy import (
    KNOWLEDGE_PEDAGOGY_RULES,
    PLAN_PEDAGOGY_RULES,
    QUIZ_PEDAGOGY_RULES,
    TYPED_CARDS_PEDAGOGY_RULES,
    pedagogy_context_block,
)

SOURCE_RULES = (
    "Quellen-Regeln:\n"
    "- Buchcover, ISBN, Rückseite, Verlagsinfo: höchstens Hintergrund — KEIN eigenes Modul, KEIN ISBN-Quiz.\n"
    "- Arbeitsblatt/Heft-Fotos: Kerninhalt — alle Aufgabentypen und Rechenwege aufgreifen.\n"
    "- Mehrere Quellen zum gleichen Thema zusammenführen; nicht 1 Quelle = 1 Modul.\n"
)

PLAN_SYSTEM = (
    "Du planst einen interaktiven Lerntrainer. Antworte NUR mit JSON, ohne Markdown.\n"
    'Schema: {"categories":[{"name":"Themenbereich","focus":"1 Satz Lernziel","cards":10,"questions":10}]}\n'
    "5 bis 6 Kategorien, cards und questions pro Kategorie so verteilen, dass die Summen "
    "den Vorgaben entsprechen. Logische Reihenfolge von leicht nach schwer.\n"
    f"{PLAN_PEDAGOGY_RULES}"
)

CARDS_SYSTEM = (
    "Du schreibst Lernkarten für einen Lerntrainer. Antworte NUR mit JSON.\n"
    'Schema: {"cards":[{"question":"...","answer":"...","tip":"..."}]}\n'
    "Regeln:\n"
    "- Genau die geforderte Anzahl Karten.\n"
    "- question: max. 18 Wörter, ein Lernpunkt pro Karte.\n"
    "- answer: 1–3 kurze Sätze.\n"
    "- tip: optionaler Merkhinweis, max. 1 Satz.\n"
    "- Keine Duplikate, kein ISBN/Buchcover-Meta, aktives Erinnern."
)

TYPED_CARDS_SYSTEM = (
    "Du schreibst drei Arten Lernkarten für einen Lerntrainer. Antworte NUR mit JSON.\n"
    'Schema: {"merk_cards":[{"question":"...","answer":"...","tip":"...","method_id":"mental|notes|numberline|written|decomposition|supplement|other"}],'
    '"mental_cards":[{"question":"...","answer":"...","tip":"..."}],'
    '"input_cards":[{"question":"...","answer":"...","tip":"...","expected_method":"mental|notes|numberline|written|decomposition|supplement"}]}\n'
    "Regeln:\n"
    "- merk_cards: Merkregeln, typische Fehler, Lösungswege — KEINE reine Kopfrechnung.\n"
    "- mental_cards: kurze Kopf-Rechnaufgaben (Frage → Antwort), 1 Schritt im Kopf.\n"
    "- input_cards: Rechenaufgaben zum Eintippen; answer = exaktes Ergebnis (Zahl).\n"
    "- Genau die geforderten Anzahlen pro Typ.\n"
    "- Keine Duplikate zwischen den Typen und zu bereits verwendeten Fragen.\n"
    "- Kein ISBN/Buchcover-Meta.\n"
    f"{TYPED_CARDS_PEDAGOGY_RULES}"
)

QUIZ_SYSTEM = (
    "Du schreibst Quizfragen für einen Lerntrainer. Antworte NUR mit JSON.\n"
    'Schema: {"questions":[{"q":"...","options":["A","B","C","D"],"answer":0,'
    '"explanation":"...","question_type":"calculation|method","method_id":"optional"}]}\n'
    "Regeln:\n"
    "- Genau die geforderte Anzahl Fragen.\n"
    "- Je 4 plausible Optionen, answer = 0-basierter Index.\n"
    "- explanation: Bei question_type=calculation mindestens zwei Lösungswege als "
    "'Variante 1 (...)' und 'Variante 2 (...)' (z. B. Reihen + Zerlegung/Komma verschieben/untereinander). "
    "Bezug zu bereits Gelerntem (Einmaleins-Reihen) wo sinnvoll.\n"
    "- Bei question_type=method: kurze Begründung der Strategiewahl, keine Rechenvarianten.\n"
    "- Bei Zahlenantworten: answer-Index muss exakt zur explanation passen; Optionen auch numerisch verschieden (nicht 10 und 10.0).\n"
    "- Keine Trivialfragen, keine Scherzantworten.\n"
    f"{QUIZ_PEDAGOGY_RULES}"
)

KNOWLEDGE_SYSTEM = (
    "Du schreibst didaktisches Kernwissen für Schüler (Schritt «Verstehen» vor Üben und Check). "
    "Antworte NUR mit JSON.\n"
    'Schema: {"knowledge":[{"title":"Kurztitel","text":"2-4 Sätze"}]}\n'
    "Regeln:\n"
    "- Genau 4 bis 5 Einträge.\n"
    "- Abdeckung: Kernregel/Konzept, Schritt-für-Schritt-Vorgehen, konkretes Mini-Beispiel mit Rechenweg, "
    "typischer Fehler oder Merksatz, optional Bezug zum Alltag.\n"
    "- Kurze Sätze, altersgerecht, verständlich — wie ein Mini-Tutorial, nicht wie eine Karteikarte.\n"
    "- Ergänze die Lernkarten didaktisch; wiederhole sie nicht wörtlich.\n"
    "- Keine Quiz-Spoiler, kein ISBN/Buchcover-Meta.\n"
    f"{KNOWLEDGE_PEDAGOGY_RULES}"
)


def learner_style_hint(*, target_age: str | None, style: str, answer_length: str) -> str:
    age = (target_age or "").strip()
    parts = []
    if age:
        if age.isdigit() and int(age) <= 9:
            parts.append("Sehr kurze Sätze, ein Gedanke pro Satz, Fachbegriffe sofort erklären.")
        elif age.isdigit() and int(age) <= 13:
            parts.append("Klare Alltagssprache, Fachbegriffe kurz erklären, Beispiele aus dem Alltag.")
        else:
            parts.append("Sachlich-didaktisch, präzise Formulierungen.")
    style_map = {
        "playful": "Ton: motivierend und leicht spielerisch, aber fachlich korrekt.",
        "factual": "Ton: sachlich und knapp.",
        "balanced": "Ton: freundlich und ausgewogen.",
    }
    parts.append(style_map.get(style, style_map["balanced"]))
    if answer_length == "short":
        parts.append("Antworten kurz halten.")
    elif answer_length == "long":
        parts.append("Antworten dürfen etwas ausführlicher sein.")
    return " ".join(parts)


def truncate_material(notes: str, max_chars: int = 48000) -> str:
    if len(notes) <= max_chars:
        return notes
    return notes[:max_chars] + "\n\n[… Material gekürzt — wichtigste Quellen stehen oben …]\n"


def truncate_context(context: str, max_chars: int = 14000, *, pedagogy_digest: str = "") -> str:
    if pedagogy_digest and "Didaktik-Regeln" not in context and "Didaktik aus den" not in context:
        digest_block = pedagogy_context_block(pedagogy_digest)
        budget = max(4000, max_chars - len(digest_block))
        if len(context) <= budget:
            return digest_block + context
        trimmed = context[:budget] + "\n\n[… Kontext gekürzt für diese Teilaufgabe …]\n"
        return digest_block + trimmed
    if len(context) <= max_chars:
        return context
    return context[:max_chars] + "\n\n[… Kontext gekürzt für diese Teilaufgabe …]\n"


def _context_block(
    *,
    title: str,
    brief: str,
    subject: str | None,
    math_focus: str | None,
    language: str,
    target_age: str | None,
    difficulty: int,
    style: str,
    answer_length: str,
    notes: str,
    pedagogy_digest: str = "",
) -> str:
    pedagogy = pedagogy_context_block(pedagogy_digest)
    return (
        f"Thema/Titel: {title}\n"
        f"Auftrag: {brief or '(kein Extra-Auftrag)'}\n"
        f"Fach: {subject or 'offen'}\n"
        + (f"Mathe-Schwerpunkt: {math_focus}\n" if math_focus else "")
        + f"Sprache: {language}\n"
        f"Zielalter: {target_age or 'offen'}\n"
        f"Schwierigkeit 1-5: {difficulty}\n"
        f"{learner_style_hint(target_age=target_age, style=style, answer_length=answer_length)}\n\n"
        f"{SOURCE_RULES}\n\n"
        + (f"{pedagogy}\n" if pedagogy else "")
        + f"Material:\n{notes or '(keine Quellen — nutze Titel und Auftrag)'}\n"
    )


def build_interactive_plan_prompt(
    *,
    title: str,
    brief: str,
    subject: str | None,
    math_focus: str | None,
    language: str,
    target_age: str | None,
    difficulty: int,
    style: str,
    answer_length: str,
    notes: str,
    card_target: int,
    question_target: int,
    pedagogy_digest: str = "",
) -> str:
    return (
        _context_block(
            title=title,
            brief=brief,
            subject=subject,
            math_focus=math_focus,
            language=language,
            target_age=target_age,
            difficulty=difficulty,
            style=style,
            answer_length=answer_length,
            notes=truncate_material(notes),
            pedagogy_digest=pedagogy_digest,
        )
        + f"\nZiel: {card_target} Lernkarten und {question_target} Quizfragen gesamt.\n"
        "Verteile cards/questions sinnvoll auf 5–6 Kategorien."
    )


def build_interactive_typed_cards_prompt(
    *,
    context: str,
    category_name: str,
    category_focus: str,
    merk_count: int,
    mental_count: int,
    input_count: int,
    existing_questions: list[str],
) -> str:
    avoid = ""
    if existing_questions:
        sample = existing_questions[:12]
        avoid = "\nBereits verwendete Fragen (nicht wiederholen):\n" + "\n".join(f"- {q}" for q in sample)
    return (
        f"{context}\n\n"
        f"Kategorie: {category_name}\n"
        f"Lernziel: {category_focus}\n"
        f"Erzeuge genau {merk_count} merk_cards, {mental_count} mental_cards und {input_count} input_cards als JSON.\n"
        f"{avoid}"
    )


def build_interactive_card_prompt(
    *,
    context: str,
    category_name: str,
    category_focus: str,
    count: int,
    existing_questions: list[str],
) -> str:
    avoid = ""
    if existing_questions:
        sample = existing_questions[:8]
        avoid = "\nBereits verwendete Kartenfragen (nicht wiederholen):\n" + "\n".join(f"- {q}" for q in sample)
    return (
        f"{context}\n\n"
        f"Kategorie: {category_name}\n"
        f"Lernziel: {category_focus}\n"
        f"Erzeuge genau {count} Lernkarten als JSON.\n"
        f"{avoid}"
    )


def build_interactive_knowledge_prompt(
    *,
    context: str,
    category_name: str,
    category_focus: str,
    card_summaries: list[str],
) -> str:
    cards_hint = ""
    if card_summaries:
        cards_hint = "\nLernkarten dieser Kategorie (nur als Kontext, nicht wiederholen):\n" + "\n".join(
            f"- {s}" for s in card_summaries[:10]
        )
    return (
        f"{context}\n\n"
        f"Kategorie: {category_name}\n"
        f"Lernziel: {category_focus}\n"
        f"Erzeuge 4 bis 5 Wissens-Einträge als JSON für den Wissens-Hub (Schritt «Verstehen»).\n"
        f"{cards_hint}"
    )


def build_interactive_quiz_prompt(
    *,
    context: str,
    category_name: str,
    category_focus: str,
    count: int,
    card_summaries: list[str],
    existing_questions: list[str],
) -> str:
    cards_hint = ""
    if card_summaries:
        cards_hint = "\nLernkarten dieser Kategorie:\n" + "\n".join(f"- {s}" for s in card_summaries[:12])
    avoid = ""
    if existing_questions:
        sample = existing_questions[:12]
        avoid = (
            "\nBereits verwendete Fragen (Karten oder Quiz — nicht wiederholen):\n"
            + "\n".join(f"- {q}" for q in sample)
        )
    return (
        f"{context}\n\n"
        f"Kategorie: {category_name}\n"
        f"Lernziel: {category_focus}\n"
        f"Erzeuge genau {count} Quizfragen als JSON.\n"
        f"{cards_hint}"
        f"{avoid}"
    )
