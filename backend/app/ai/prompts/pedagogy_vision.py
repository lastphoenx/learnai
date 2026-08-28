"""Vision-Prompts für Didaktik-Extraktion — Kernschema + fachliche Overlays."""

from __future__ import annotations

from app.core.focus_groups import normalize_focus_group

_CORE_SCHEMA = (
    "{\n"
    '  "summary": "",\n'
    '  "is_metadata_only": false,\n'
    '  "key_terms": [{"term":"","definition":"","role":""}],\n'
    '  "assignments": [{"ref":"","instruction":"","format":""}],\n'
    '  "exercise_formats": [""],\n'
    '  "comprehension": [{"question":"","answer":""}],\n'
    '  "visual_tasks": [{"kind":"","instruction":"","terms":[""],"placements":[{"term":"","x":0.5,"y":0.5}]}],\n'
    '  "methods": [{"label":"","when":"","example":"","id":""}],\n'
    '  "worked_examples": [{"problem":"","method_label":"","steps":[""]}],\n'
    '  "exercises": [{"ref":"","text":"","suggested_method":""}],\n'
    '  "exercise_patterns": [""],\n'
    '  "teaching_notes": [""]\n'
    "}\n"
)

_CORE_RULES = (
    "Feldbedeutung (generisch, alle Fächer):\n"
    "- summary: 2–6 Sätze zu Thema, Seiteninhalt und Lernzielen\n"
    "- key_terms: Fachbegriffe aus dem Material mit kurzer Bedeutung (Pflicht wenn Begriffe im Text)\n"
    "- assignments: sichtbare Aufträge/Aufgaben (ref z. B. «Auftrag 1», instruction vollständig, format z. B. lesen|zeichnen|beschriften|zuordnen|rechnen)\n"
    "- exercise_formats: Aufgabentypen in Worten des Materials (Zeichnen, Beschriften, …)\n"
    "- comprehension: Titelfragen oder Verständnisfragen mit Antwort aus dem Text\n"
    "- visual_tasks: Bild-/Zeichenaufgaben (kind: label|draw|color|map; terms; placements optional mit x,y 0–1)\n"
    "- teaching_notes: konkrete didaktische Hinweise\n"
    "Regeln:\n"
    "- Nur gedruckter Inhalt — keine Handschrift, Kreise, Korrekturen des Kindes.\n"
    "- assignments.instruction vollständig übernehmen, nicht mitten im Satz abbrechen.\n"
    "- key_terms aus Einleitungstext, Legenden, Beschriftungen im Material.\n"
    "- KEINE Schema-Platzhalter als Werte.\n"
    "- is_metadata_only=true nur bei Cover/ISBN ohne Aufgaben.\n"
)

_PROFILE_OVERLAYS: dict[str, str] = {
    "math": (
        "Mathe-Zusatz:\n"
        "- methods: benannte Lösungswege/Strategien exakt wie im Heft.\n"
        "- worked_examples: Rechenbeispiele mit Zwischenschritten.\n"
        "- Malpunkt (·/×) nie als Dezimalpunkt lesen.\n"
    ),
    "nmg": (
        "NMG-Zusatz (Natur, Mensch, Gesellschaft):\n"
        "- key_terms und assignments haben Priorität — mindestens alle Fachbegriffe und Aufträge aus dem Heft.\n"
        "- exercise_formats typisch: Lesen, Zeichnen, Beschriften, Zuordnen, Karte bearbeiten.\n"
        "- visual_tasks bei Zeichen-/Beschriftungsaufgaben (kind draw oder label).\n"
        "- methods nur wenn explizite Strategien genannt — sonst leer lassen.\n"
    ),
    "german": (
        "Deutsch-Zusatz:\n"
        "- key_terms: Wortarten, Satzglieder, Rechtschreibregeln.\n"
        "- comprehension: Grammatik- oder Textverständnisfragen.\n"
    ),
    "language": (
        "Sprachen-Zusatz:\n"
        "- key_terms: Vokabeln, Zeitformen, Satzmuster.\n"
    ),
    "nature": (
        "Natur & Technik-Zusatz:\n"
        "- key_terms: Fachbegriffe, Prozesse, Einheiten.\n"
        "- visual_tasks bei Diagrammen oder Skizzen.\n"
    ),
    "general": (
        "Allgemein:\n"
        "- Alle sichtbaren Aufträge und Fachbegriffe strukturiert erfassen.\n"
    ),
}


def vision_pedagogy_prompt(*, language: str, focus_group: str | None = None) -> str:
    lang = (language or "de").strip() or "de"
    group = normalize_focus_group(focus_group)
    overlay = _PROFILE_OVERLAYS.get(group, _PROFILE_OVERLAYS["general"])
    return (
        "Das ist ein Foto aus einem Lernmittel (Schulbuch, Arbeitsblatt, Heft).\n"
        "Antworte NUR mit gültigem JSON (kein Markdown).\n"
        f"Struktur:\n{_CORE_SCHEMA}"
        f"{_CORE_RULES}\n"
        f"{overlay}\n"
        "- exercises: Legacy-Feld — gleicher Inhalt wie assignments.instruction in text, wenn assignments leer.\n"
        "- Keine Kapitel-Überschriften «Du kannst …» als methods.\n"
        f"- Sprache: {lang}.\n"
    )
