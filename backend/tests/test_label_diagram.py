import json

from app.core.basiswissen import enrich_module_with_basiswissen, parse_basiswissen_payload
from app.core.label_diagram import (
    build_label_diagram,
    derive_drawing_practice_item,
    derive_label_practice_items,
    detect_diagram_template,
    grade_label_diagram_answer,
)

CASTLE_BASISWISSEN = {
    "basiswissen": {
        "schema_version": 1,
        "focus_group": "mgu",
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


def test_detect_castle_diagram_template():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="mgu")
    assert detect_diagram_template(bw["concepts"], category_label="Burgen") == "castle"


def test_build_label_diagram_from_castle_terms():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="mgu")
    diagram = build_label_diagram(bw["concepts"], template="castle", title="Burg beschriften")
    assert diagram is not None
    assert len(diagram["hotspots"]) >= 3
    assert "Bergfried" in diagram["terms"]


def test_grade_label_diagram_answer():
    expected = json.dumps({"bergfried": "Bergfried", "wehrgang": "Wehrgang"})
    user_ok = json.dumps({"bergfried": "Bergfried", "wehrgang": "wehrgang"})
    user_bad = json.dumps({"bergfried": "Palas", "wehrgang": "Wehrgang"})
    assert grade_label_diagram_answer(expected, user_ok)
    assert not grade_label_diagram_answer(expected, user_bad)


def test_derive_label_and_drawing_practice_items():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="mgu")
    label_items = derive_label_practice_items(bw, category_label="Burgen")
    drawing = derive_drawing_practice_item(bw, category_label="Burgen")
    assert label_items
    assert label_items[0]["answer_type"] == "label_diagram"
    assert drawing is not None
    assert drawing["answer_type"] == "drawing"


def test_enrich_module_adds_label_practice_for_castle():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="mgu")
    content = {"knowledge": [], "cards": [], "practice": []}
    quiz = {"questions": []}
    out_content, _ = enrich_module_with_basiswissen(
        content=content,
        quiz=quiz,
        basiswissen=bw,
        question_count=6,
        category_label="Hochmittelalter: Burgen",
    )
    types = {item.get("answer_type") for item in out_content.get("practice") or []}
    assert "label_diagram" in types
    assert "drawing" in types
