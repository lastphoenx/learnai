"""Didaktik-Regeln für Generierung (Lösungswege, Verstehen, Strategiewahl)."""

from __future__ import annotations

PEDAGOGY_RULES = (
    "Didaktik-Regeln (aus Quellen und Schwerpunkt):\n"
    "- Lösungswege aus dem Material sind Pflichtinhalt — nicht nur Endergebnisse.\n"
    "- Benenne Strategien so, wie sie im Didaktik-Block / Heft stehen (Freitext-Labels).\n"
    "- Aufgabentypen und Übungsformate aus dem Material übernehmen, nicht durch feste Kategorien ersetzen.\n"
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
    "- merk_cards: je gezeigter Strategie aus dem Didaktik-Block mindestens eine Karte.\n"
    "- method_label: Bezeichnung aus dem Heft (Pflicht, wenn Strategie aus dem Material).\n"
    "- method_id: optional, nur für UI-Gruppierung — nie erfinden, wenn keine passt.\n"
    "- mental_cards: kurze direkte Abfragen ohne Hilfsmittel.\n"
    "- input_cards: passend zum Aufgabentyp (numeric, short_text oder cloze); method_label optional.\n"
)

KNOWLEDGE_PEDAGOGY_RULES = (
    "Wissens-Hub (Schritt «Verstehen»):\n"
    "- Mindestens ein Eintrag pro wichtiger Lösungsstrategie aus den Quellen.\n"
    "- Ein Eintrag mit Schritt-für-Schritt-Beispiel aus worked_examples (Zwischenschritte!).\n"
    "- Ein Eintrag: «Wann welches Vorgehen?» — Entscheidungshilfe, nicht nur Regeln.\n"
    "- Ein Eintrag: typischer Fehler oder Merksatz aus dem Material.\n"
    "- Verständlich wie ein Mini-Tutorial — Vorbereitung für Üben und Check.\n"
)

QUIZ_PEDAGOGY_RULES = (
    "Quiz-Didaktik:\n"
    "- Ca. 20–30 % Fragen mit question_type=method (Strategiewahl).\n"
    "- method-Fragen: options = Lösungswege aus dem Didaktik-Block (Heft-Wortlaut).\n"
    "- Rechenfragen: question_type=calculation; explanation mit mindestens 2 Varianten.\n"
    "- Wenn im Didaktik-Block worked_examples stehen: mindestens eine Variante daraus übernehmen.\n"
    "- Bezug zu Methoden-Labels aus dem Didaktik-Block, wenn vorhanden.\n"
)


def pedagogy_context_block(digest: str) -> str:
    digest = (digest or "").strip()
    if not digest:
        return ""
    return f"{PEDAGOGY_RULES}\n{digest}\n"
