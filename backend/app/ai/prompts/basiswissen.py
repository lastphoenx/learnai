"""Prompts für strukturiertes Basiswissen (Fachbegriffe, Lückentexte)."""

from __future__ import annotations

from app.core.basiswissen_profiles import FOCUS_GROUP_PROMPTS
from app.ai.prompts.interactive import truncate_context

BASISWISSEN_SYSTEM = (
    "Du extrahierst prüfungsrelevantes Basiswissen als strukturiertes JSON für Schüler. "
    "Antworte NUR mit JSON.\n"
    'Schema: {"basiswissen":{"schema_version":1,"focus_group":"math|german|language|mgu|nature|general",'
    '"concepts":[{"id":"slug","kind":"relation|definition|rule|vocabulary","label":"Thema",'
    '"parts":[{"role":"factor","term":"Faktor","aliases":["Faktor"]}],'
    '"pattern":"Faktor × Faktor = Produkt","example":"3 × 4 = 12",'
    '"hint":"Kurze didaktische Erklärung in 1-2 Sätzen"}],'
    '"cloze_templates":[{"id":"slug","concept_id":"slug","sentence":"Bei der Multiplikation heißt das Ergebnis ___.",'
    '"answers":["Produkt"],"blank_roles":["product"]}]}}\n'
    "Regeln:\n"
    "- 3 bis 8 concepts, thematisch passend zur Kategorie (nicht generisches Schulwissen von anderen Fächern).\n"
    "- 4 bis 10 cloze_templates mit mindestens einem ___ pro Satz; answers-Länge = Anzahl Lücken (oder eine Antwort für alle gleichen Lücken).\n"
    "- pattern zeigt die Relation verständlich (Wörter, nicht nur Symbole).\n"
    "- hint erklärt warum/wann der Begriff wichtig ist — nicht nur die Aufgabe wiederholen.\n"
    "- Keine Quiz-Spoiler aus dem Check; Fachbegriffe und Merksätze sind erlaubt.\n"
    "- Sprache: Deutsch, altersgerecht.\n"
)


def build_basiswissen_prompt(
    *,
    context: str,
    category_name: str,
    category_focus: str,
    focus_group: str,
    knowledge_items: list[dict],
    card_summaries: list[str],
) -> str:
    group_hint = FOCUS_GROUP_PROMPTS.get(focus_group, FOCUS_GROUP_PROMPTS.get("math", ""))
    knowledge_lines = [
        f"- {item.get('title', '')}: {str(item.get('text', ''))[:200]}"
        for item in knowledge_items[:6]
        if isinstance(item, dict)
    ]
    cards_block = "\n".join(f"- {line}" for line in card_summaries[:8]) or "(keine)"
    knowledge_block = "\n".join(knowledge_lines) or "(kein Wissens-Hub)"
    return truncate_context(
        f"{context}\n\n"
        f"Kategorie: {category_name}\n"
        f"Schwerpunkt: {category_focus or '(allgemein)'}\n"
        f"Fachgruppe: {focus_group}\n"
        f"Fachregeln: {group_hint}\n\n"
        f"Bereits generierter Wissens-Hub:\n{knowledge_block}\n\n"
        f"Lernkarten (Auszug):\n{cards_block}\n\n"
        "Erstelle basiswissen passend zu dieser Kategorie. "
        "cloze_templates sollen typische Prüfungs-Lückentexte abbilden (Begriffe zuordnen).",
        max_chars=16000,
    )
