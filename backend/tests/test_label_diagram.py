import json

from app.core.basiswissen import enrich_module_with_basiswissen, parse_basiswissen_payload
from app.core.label_diagram import build_label_diagram_from_terms, grade_label_diagram_answer
from app.core.practice_derive import collect_term_hints, derive_practice_items

CASTLE_BASISWISSEN = {
    "basiswissen": {
        "schema_version": 1,
        "focus_group": "nmg",
        "concepts": [
            {
                "id": "castle_terms",
                "kind": "vocabulary",
                "label": "Burg im Hochmittelalter",
                "parts": [
                    {"role": "bergfried", "term": "Bergfried", "hint": "Höchster Turm"},
                    {"role": "wehrgang", "term": "Wehrgang", "hint": "Gang auf der Mauer"},
                    {"role": "fallgatter", "term": "Fallgatter", "hint": "Gittern am Tor"},
                    {"role": "burggraben", "term": "Burggraben", "hint": "Wassergraben"},
                    {"role": "palas", "term": "Palas", "hint": "Wohngebäude"},
                ],
                "hint": "Die Begriffe beschreiben Teile einer mittelalterlichen Burg.",
            }
        ],
        "cloze_templates": [],
    }
}

NMG_PEDAGOGY = {
    "page_summary": "Burgen im Hochmittelalter: Aufbau und Bauteile.",
    "key_terms": [
        {"term": "Bergfried", "definition": "Höchster Turm der Burg"},
        {"term": "Wehrgang", "definition": "Gang auf der Mauer"},
        {"term": "Fallgatter", "definition": "Gittern am Tor"},
        {"term": "Burggraben", "definition": "Wassergraben um die Burg"},
        {"term": "Palas", "definition": "Wohngebäude der Burg"},
    ],
    "assignments": [
        {"ref": "1", "instruction": "Zeichne eine Burg und beschrifte die Bauteile.", "format": "zeichnen"},
        {"ref": "2", "instruction": "Ordne die Fachbegriffe dem Schema zu.", "format": "beschriften"},
    ],
    "exercise_formats": ["Zeichnen/Beschriften", "Fachbegriffe zuordnen"],
    "visual_tasks": [
        {
            "kind": "zeichnen",
            "instruction": "Zeichne eine Burg und beschrifte die wichtigsten Teile.",
            "terms": ["Bergfried", "Wehrgang", "Palas"],
        }
    ],
}

MINDMAP_PEDAGOGY = {
    "visual_tasks": [
        {
            "kind": "beschriften",
            "instruction": "Beschrifte das Mindmap mit deinen Gedanken über die Schweiz.",
            "terms": [
                "Das gefällt mir",
                "Das würde ich ändern",
                "So ist die Schweiz heute",
            ],
        }
    ],
    "exercise_formats": ["Mindmap beschriften"],
}


def test_build_label_diagram_from_terms_generic():
    diagram = build_label_diagram_from_terms(
        ["Bergfried", "Wehrgang", "Fallgatter", "Burggraben"],
        title="Fachbegriffe zuordnen",
        term_hints={"Bergfried": "Höchster Turm"},
    )
    assert diagram is not None
    assert diagram["template"] == "generic"
    assert len(diagram["hotspots"]) == 4
    assert "label" not in diagram["hotspots"][0]
    assert diagram["hotspots"][0]["hint"] == "Höchster Turm"


def test_grade_label_diagram_answer():
    expected = json.dumps({"bergfried": "Bergfried", "wehrgang": "Wehrgang"})
    user_ok = json.dumps({"bergfried": "Bergfried", "wehrgang": "wehrgang"})
    user_bad = json.dumps({"bergfried": "Palas", "wehrgang": "Wehrgang"})
    assert grade_label_diagram_answer(expected, user_ok)
    assert not grade_label_diagram_answer(expected, user_bad)


def test_derive_practice_uses_knowledge_choice_not_generic_schema():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    items = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Burgen",
        focus_group="nmg",
    )
    assert items
    assert all(i.get("answer_type") == "choice" for i in items)
    assert not any(i.get("answer_type") == "drawing" for i in items)
    assert not any(i.get("answer_type") == "label_diagram" for i in items)
    first = items[0]
    assert len(first.get("options") or []) >= 2
    assert str(first.get("answer")).isdigit()


def test_derive_practice_skips_personal_mindmap_without_placements():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    items = derive_practice_items(
        pedagogy=MINDMAP_PEDAGOGY,
        basiswissen=bw,
        category_label="Schweiz heute",
        focus_group="nmg",
    )
    assert all(i.get("answer_type") == "choice" for i in items)


def test_enrich_module_adds_choice_practice():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    content = {"knowledge": [], "cards": [], "practice": []}
    quiz = {"questions": []}
    out_content, _ = enrich_module_with_basiswissen(
        content=content,
        quiz=quiz,
        basiswissen=bw,
        question_count=6,
        category_label="Hochmittelalter: Burgen",
        pedagogy=NMG_PEDAGOGY,
    )
    types = {item.get("answer_type") for item in out_content.get("practice") or []}
    assert types == {"choice"}


def test_derive_practice_dedupes_prompts_across_modules():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    state: dict = {}
    first = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Bereich 1",
        focus_group="nmg",
        practice_state=state,
    )
    second = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Bereich 2",
        focus_group="nmg",
        practice_state=state,
    )
    assert first
    assert len(first) >= len(second)


def test_collect_term_hints_from_pedagogy():
    hints = collect_term_hints(pedagogy=NMG_PEDAGOGY, basiswissen={})
    assert hints["Bergfried"] == "Höchster Turm der Burg"
