"""Didaktik-Regeln für Generierung (Lösungswege, Verstehen, Strategiewahl)."""

from __future__ import annotations

PEDAGOGY_RULES = (
    "Didaktik-Regeln (aus Quellen und Schwerpunkt):\n"
    "- Lösungswege aus dem Material sind Pflichtinhalt — nicht nur Endergebnisse.\n"
    "- Typische Wege: im Kopf, mit Notizen, Rechenstrich, schriftlich, Zerlegung, ergänzen.\n"
    "- Aufgaben wie «Wähle ein geeignetes Vorgehen» oder «Dezimalpunkt ergänzen» aus dem Heft übernehmen.\n"
    "- Bei Rechenaufgaben: passende Methode nennen oder verlangen (nicht nur die Zahl).\n"
)

PLAN_PEDAGOGY_RULES = (
    "Gliederung:\n"
    "- Mindestens eine Kategorie zu Lösungswegen / Strategiewahl (wann welche Methode?).\n"
    "- Weitere Kategorien nach Themen aus dem Material — nicht nur nach Rechenart.\n"
    "- focus je Kategorie: Lernziel inkl. erwarteter Lösungswege.\n"
)

TYPED_CARDS_PEDAGOGY_RULES = (
    "Karten nach Didaktik:\n"
    "- merk_cards: je gezeigter Strategie mindestens eine Karte; method_id Pflicht "
    "(mental|notes|numberline|written|decomposition|supplement|other).\n"
    "- mental_cards: nur Aufgaben, die wirklich im Kopf lösbar sind.\n"
    "- input_cards: Aufgabe nennt die Methode; expected_method Pflicht "
    "(mental|notes|numberline|written|decomposition|supplement); answer = Ergebnis.\n"
)

KNOWLEDGE_PEDAGOGY_RULES = (
    "Wissens-Hub (Schritt «Verstehen»):\n"
    "- Mindestens ein Eintrag pro wichtiger Lösungsstrategie aus den Quellen.\n"
    "- Ein Eintrag mit Schritt-für-Schritt-Beispiel aus worked_examples (Zwischenschritte!).\n"
    "- Ein Eintrag: «Wann welches Vorgehen?» — Entscheidungshilfe, nicht nur Regeln.\n"
    "- Ein Eintrag: typischer Fehler oder Merksatz (z. B. Komma ausrichten, Stellenwerte).\n"
    "- Verständlich wie ein Mini-Tutorial — Vorbereitung für Üben und Check.\n"
)

QUIZ_PEDAGOGY_RULES = (
    "Quiz-Didaktik:\n"
    "- Ca. 20–30 % Fragen mit question_type=method (Strategiewahl).\n"
    "- method-Fragen: options = Lösungswege; method_id der richtigen Antwort setzen.\n"
    "- Rechenfragen: question_type=calculation; explanation mit mindestens 2 Varianten.\n"
    "- Wenn im Didaktik-Block worked_examples stehen: mindestens eine Variante daraus übernehmen.\n"
    "- Bezug zu Methoden aus dem Didaktik-Block, wenn vorhanden.\n"
)


def pedagogy_context_block(digest: str) -> str:
    digest = (digest or "").strip()
    if not digest:
        return ""
    return f"{PEDAGOGY_RULES}\n{digest}\n"
