"""Ein-Call-Generierung für Deutsch-Grammatik (Lehrbuch → kompakter Trainer)."""

from __future__ import annotations

from app.ai.prompts.interactive import SOURCE_RULES, learner_style_hint, truncate_material

COMPACT_COUNTS = {
    "understand": 12,
    "merk_cards": 10,
    "mental_cards": 14,
    "quiz": 22,
}

CASE_OPTIONS = ["Nominativ", "Genitiv", "Dativ", "Akkusativ"]

GERMAN_COMPACT_SYSTEM = (
    "Du erstellst einen kompakten Deutsch-Grammatik-Lerntrainer aus Lehrbuchmaterial. "
    "Antworte NUR mit JSON, ohne Markdown.\n"
    "Ein zusammenhängendes Ganze — keine Modul-Splitting-Logik, keine Rechenaufgaben, "
    "keine ISBN-/Cover-Fragen.\n"
    "Schema:\n"
    '{"theory":{"intro":"Mission in 1-2 Sätzen","knowledge":[{"title":"...","text":"2-4 Sätze"}],'
    '"cases":[{"name":"Nominativ","question":"Wer?","example":"Der Löwe schläft."}]},'
    '"understand":[{"sentence":"vollständiger Satz","span":"markiertes Satzglied","answer":"Nominativ",'
    '"explanation":"Frageprobe kurz","nested":{"span":"innerer Teil","answer":"Genitiv","explanation":"..."}}],'
    '"cards":[{"kind":"merk|mental","question":"...","answer":"...","tip":"optional"}],'
    '"quiz":[{"q":"Frage mit Satz","options":["Nominativ","Genitiv","Dativ","Akkusativ"],'
    '"answer":0,"explanation":"...","sentence":"vollständiger Satz","span":"markiertes Satzglied"}]}\n'
    "Regeln:\n"
    f"- Genau {COMPACT_COUNTS['understand']} understand-Aufgaben: Fall der markierten Wortgruppe bestimmen.\n"
    f"- Genau {COMPACT_COUNTS['merk_cards']} merk + {COMPACT_COUNTS['mental_cards']} mental cards "
    f"(kind merk oder mental).\n"
    f"- Genau {COMPACT_COUNTS['quiz']} Quizfragen; bei Fall-Fragen options = Nominativ, Genitiv, Dativ, Akkusativ.\n"
    "- theory.knowledge: 4–6 Einträge (Frageproben, Ersatzprobe, Signalwörter, verschachtelte Fälle).\n"
    "- theory.cases: alle vier Fälle mit Frage und Beispiel.\n"
    "- understand/quiz: sentence und span müssen exakt im Satz vorkommen; span ist das zu bestimmende Satzglied.\n"
    "- quiz: sentence und span PFLICHT; q enthält den Satz nach dem Doppelpunkt.\n"
    "- 2–3 understand/quiz mit nested (gelbe Wortgruppe + innerer Genitiv/Dativ).\n"
    "- Keine Duplikate; Beispiele aus dem Material, sonst passende Neusätze im gleichen Stoff.\n"
    "- Keine Lückentext-Antworten wie deres|derem|deren — nur klare Fall-Labels oder kurze Phrasen.\n"
    "- cards: Merkregeln und kurze Kopf-Abfragen (Frage→Fall), keine langen Freitext-Antworten.\n"
)


def build_german_compact_prompt(
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
) -> str:
    style_hint = learner_style_hint(target_age=target_age, style=style, answer_length=answer_length)
    material = truncate_material(notes)
    return (
        f"Thema/Titel: {title}\n"
        f"Auftrag: {brief or '(kein Extra-Auftrag)'}\n"
        f"Fach: {subject or 'Deutsch'}\n"
        f"Sprache: {language}\n"
        f"Zielalter: {target_age or 'offen'}\n"
        f"Schwierigkeit 1-5: {difficulty}\n"
        f"{style_hint}\n\n"
        f"{SOURCE_RULES}\n\n"
        f"Material (vollständig — nutze Inhalt und Aufgabentypen aus dem Heft):\n"
        f"{material or '(keine Quellen — nutze Titel und Auftrag)'}\n"
    )
