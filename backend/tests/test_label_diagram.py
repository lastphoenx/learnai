import json

from app.core.basiswissen import enrich_module_with_basiswissen, parse_basiswissen_payload
from app.core.label_diagram import build_label_diagram_from_terms, grade_label_diagram_answer
from app.core.practice_derive import derive_practice_items

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
                    {"role": "bergfried", "term": "Bergfried"},
                    {"role": "wehrgang", "term": "Wehrgang"},
                    {"role": "fallgatter", "term": "Fallgatter"},
                    {"role": "burggraben", "term": "Burggraben"},
                    {"role": "palas", "term": "Palas"},
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


def test_build_label_diagram_from_terms_generic():
    diagram = build_label_diagram_from_terms(
        ["Bergfried", "Wehrgang", "Fallgatter", "Burggraben"],
        title="Fachbegriffe zuordnen",
    )
    assert diagram is not None
    assert diagram["template"] == "generic"
    assert len(diagram["hotspots"]) == 4
    assert diagram["hotspots"][0]["x"] == round(diagram["hotspots"][0]["x"], 3)


def test_grade_label_diagram_answer():
    expected = json.dumps({"bergfried": "Bergfried", "wehrgang": "Wehrgang"})
    user_ok = json.dumps({"bergfried": "Bergfried", "wehrgang": "wehrgang"})
    user_bad = json.dumps({"bergfried": "Palas", "wehrgang": "Wehrgang"})
    assert grade_label_diagram_answer(expected, user_ok)
    assert not grade_label_diagram_answer(expected, user_bad)


def test_derive_practice_items_from_pedagogy_and_basiswissen():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    items = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Burgen",
        focus_group="nmg",
    )
    types = {item.get("answer_type") for item in items}
    assert "label_diagram" in types
    assert "drawing" in types
    assert all(item.get("diagram", {}).get("template") != "castle" for item in items if item.get("diagram"))


def test_enrich_module_adds_generic_practice():
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
    assert "label_diagram" in types
    assert "drawing" in types
    for item in out_content.get("practice") or []:
        diagram = item.get("diagram")
        if isinstance(diagram, dict):
            assert diagram.get("template") == "generic"
