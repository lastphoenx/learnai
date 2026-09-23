"""Ein-Call-Generierung für Heft-Posten (posten_compact) — Chat-HTML-Struktur."""

from __future__ import annotations

import re

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


# Bei Raumgeometrie: weniger Karten/Quiz im JSON — gleiche Aufgabentypen wie im Standard-Trainer.
SPATIAL_COMPACT_CARD_CAP = 10
SPATIAL_COMPACT_QUIZ_CAP = 6


def spatial_compact_content_targets(card_target: int, question_target: int) -> tuple[int, int]:
    return min(card_target, SPATIAL_COMPACT_CARD_CAP), min(question_target, SPATIAL_COMPACT_QUIZ_CAP)


POSTEN_COMPACT_SPATIAL_EXTRA = (
    "Raumgeometrie — PFLICHT (gleiche Qualität/Schwere wie Standard-Lerntrainer, nur kürzer bei Karten/Quiz):\n"
    "posten_compact bedeutet Umfangsbegrenzung, KEINE Abschwächung der Raumaufgaben.\n"
    "- Reine Zeichenaufgaben («zeichne», «male») nicht als Quiz — stattdessen prüfbare Varianten unten.\n"
    "- image_choice_items: 1-4 Aufgaben mit Bild-Optionen. "
    'Jede Option: {"id":"A","image_ref":{"source_index":0,"x":0.1,"y":0.2,"w":0.15,"h":0.12}} '
    "(x,y,w,h relativ 0-1 zum Quellbild). answer = id der richtigen Option.\n"
    "- point_on_image_items: 1-4 Aufgaben «Fotograf-Standort». "
    'background_image_ref wie oben (bbox optional, sonst ganzes Bild). '
    'candidates: [{"id":"A","x":0.26,"y":0.44}, ...], answer = id. selection_mode: "candidate".\n'
    "- grid_fill_items: 1-3 Bauplan- oder Einfärb-Raster. "
    'rows, cols, cell_type "number" oder "color", answer als 2D-Array (null = leer). '
    "Farben nur: yellow, green, purple, blue, orange, empty.\n"
    "- building_paint_items: Würfel/Gebäude einfärben (Three.js) — height_matrix (Einzelwürfel [[1]]), "
    'colored_faces {"0,0,0,top":"yellow","0,0,0,left":"green",...}; prompt mit klaren Farben pro Fläche. '
    "Nur sichtbare Flächen in der Schrägansicht: top/left/right (oben/links/rechts) — "
    "nie front/back/bottom, nie «vordere/hintere/untere Fläche».\n"
    "- region_paint_items: nur mehrstufige Türme — template iso_tower_2; Einzelwürfel immer building_paint. "
    "Prompt: nur top/left/right benennen, nie vorne/hinten/unten.\n"
    '- grid_fill: validation "derived_projection" — answer {"height_matrix":[[...]]}; '
    "reference_height_matrix PFLICHT bei cell_type number (exact_match: Vorschau-Gebäude; derived_projection: "
    "optional, sonst height_matrix aus answer). Bei «Höhenplan ergänzen»: exact_match + reference_height_matrix "
    "+ answer als Lösungsraster; rows/cols = Matrix-Zeilen/-Spalten.\n"
    '- net_build_items: Modus «bauen» — rows/cols; KEINE freie Form-Beschreibung im prompt '
    '(wird serverseitig ersetzt). Optional target_cells [[col,row],...] (6 gültige Netz-Zellen) '
    'für eine konkrete Vorlage; sonst answer "valid_net" (beliebiges gültiges Netz). '
    'Modus «prüfen» — given_cells (6 Zellen), answer "valid"/"invalid". '
    "Quader-Netze (ungleiche Rechtecke): image_choice aus Heft-Foto, nicht net_build.\n"
    "- spatial_sequence_items: nur height_matrix + prompt (Stufen/Hilfen/Lösung werden serverseitig erzeugt); "
    "prompt = kurze generische Einleitung zum Gebäude (Thema/Kontext), KEINE Beschreibung der Schritte — "
    "wird serverseitig ersetzt. Ablauf ist immer: Gebäude in 3D ansehen → Sicht-Entscheidung → "
    "Vorder-/Rechts-/Aufsicht eintragen. Nicht «bauen», nicht «Schichten legen», nicht «Säulenhöhen prüfen» "
    "o.ä. schreiben. Optional fertiges spatial_sequence-Objekt für Experten.\n"
    "- synthetic_viewpoint_items: height_matrix; candidates mit id, label (deutsch, z. B. «Vorne …»), "
    "direction (vorne/hinten/links/rechts) und x/y (0–1) auf dem Plan (Marker in 3D); "
    "answer = id des richtigen Standpunkts — keine leeren A/B/C ohne Beschreibung.\n"
    "- PFLICHT: mindestens 2 Einträge gesamt in den spatial-Listen (zusätzlich zu cards/quiz).\n"
    "- Bevorzuge building_paint/grid_fill/image_choice aus dem Heft-Material, wenn erkennbar.\n"
)


def build_compact_system_prompt(
    preset_id: str = "posten_compact",
    *,
    spatial_geometry: bool = False,
    card_target: int | None = None,
    question_target: int | None = None,
) -> str:
    pid = (preset_id or "posten_compact").strip()
    counts = compact_preset_counts(pid)
    cards = card_target if card_target is not None else counts["cards"]
    quiz = question_target if question_target is not None else counts["quiz"]
    base = POSTEN_COMPACT_SYSTEM
    if spatial_geometry and (cards != counts["cards"] or quiz != counts["quiz"]):
        base = re.sub(
            rf"- cards: genau {POSTEN_COMPACT_COUNTS['cards']} Karten",
            f"- cards: genau {cards} Karten",
            base,
        )
        base = re.sub(
            rf"- quiz: genau {POSTEN_COMPACT_COUNTS['quiz']} Fragen",
            f"- quiz: genau {quiz} Fragen",
            base,
        )
    if pid == "exam_review":
        base = base + "\n" + EXAM_REVIEW_SYSTEM_EXTRA
    if spatial_geometry:
        base = (
            base
            + "\n- timeline: bei Raumgeometrie **weglassen** (Feld nicht setzen) — kein Zeitstrahl neben Raumaufgaben.\n"
            + '\nErweitertes Schema (PFLICHT-Felder bei Raumgeometrie, im JSON mit ausfüllen): '
            + '"image_choice_items":[],"point_on_image_items":[],"grid_fill_items":[],"region_paint_items":[],"building_paint_items":[],"net_build_items":[],"spatial_sequence_items":[],"synthetic_viewpoint_items":[]\n'
            + POSTEN_COMPACT_SPATIAL_EXTRA
        )
    return base


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
    spatial_geometry: bool = False,
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
    prompt = (
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
    if spatial_geometry:
        prompt += (
            "\nRaumgeometrie (Pflicht, volle Schwere): Mindestens 2 Einträge in "
            "image_choice_items, point_on_image_items, grid_fill_items, region_paint_items, "
            "building_paint_items, net_build_items und/oder synthetic_viewpoint_items — "
            "inhaltlich aus den Heft-Fotos, mit klaren Arbeitsanweisungen und prüfbaren answers.\n"
        )
    return prompt
