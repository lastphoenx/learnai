import json
import re

from app.core.basiswissen import enrich_module_with_basiswissen, parse_basiswissen_payload
from app.core.label_diagram import build_label_diagram_from_terms, grade_label_diagram_answer
from app.core.practice_derive import collect_term_hints, derive_practice_choice_questions, derive_practice_items

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


def test_score_label_diagram_answer_partial_feedback():
    from app.core.label_diagram import score_label_diagram_answer

    expected = json.dumps({"a": "Altsteinzeit", "b": "Antike", "c": "Neuzeit"})
    user = json.dumps({"a": "Altsteinzeit", "b": "Neuzeit", "c": "Neuzeit"})
    score = score_label_diagram_answer(expected, user)
    assert not score["correct"]
    by_id = {row["id"]: row for row in score["slots"]}
    assert by_id["a"]["correct"] is True
    assert by_id["b"]["correct"] is False
    assert by_id["b"]["expected_term"] == "Antike"
    assert by_id["b"]["user_term"] == "Neuzeit"


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


def test_derive_practice_builds_timeline_from_epoch_key_terms():
    from tests.fixtures.timeline_epochs import POSTEN_14_EPOCH_TERMS

    pedagogy = {
        "key_terms": POSTEN_14_EPOCH_TERMS,
        "exercise_patterns": ["Zeitstrahl-Beschreibung"],
        "assignments": [],
        "visual_tasks": [],
    }
    items = derive_practice_items(
        pedagogy=pedagogy,
        basiswissen={},
        category_label="Geschichte der Schweiz",
        focus_group="nmg",
    )
    diagram_items = [i for i in items if i.get("answer_type") == "label_diagram"]
    assert diagram_items
    assert diagram_items[0]["diagram"]["layout"] == "timeline"


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


def test_strip_practice_answers_keeps_choice_options():
    from app.services.learn_service import _strip_practice_answers

    out = _strip_practice_answers(
        {
            "practice": [
                {
                    "prompt": "Frage?",
                    "hint": "Tipp",
                    "answer_type": "choice",
                    "answer": "2",
                    "options": ["A", "B", "C", "D"],
                }
            ]
        }
    )
    item = out["practice"][0]
    assert item["options"] == ["A", "B", "C", "D"]
    assert "answer" not in item


def test_derive_practice_hint_does_not_leak_quiz_explanation():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    items = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Burgen",
        focus_group="nmg",
    )
    assert items
    assert not any(str(i.get("hint") or "").startswith("Richtig:") for i in items)


def test_derive_practice_uses_definition_not_tautology():
    bw = parse_basiswissen_payload(
        {
            "basiswissen": {
                "schema_version": 1,
                "focus_group": "nmg",
                "concepts": [
                    {
                        "id": "ch",
                        "label": "Solothurn gehört zur Schweiz",
                        "parts": [
                            {
                                "role": "whole",
                                "term": "Schweiz",
                                "hint": "Staat, in dem der Kanton Solothurn liegt.",
                            },
                            {
                                "role": "part",
                                "term": "Kanton Solothurn",
                                "hint": "Kanton im Nordwesten der Schweiz.",
                            },
                        ],
                        "hint": "Solothurn ist ein Kanton in der Schweiz.",
                    },
                    {
                        "id": "hr",
                        "label": "Helvetische Republik",
                        "parts": [
                            {
                                "role": "begriff",
                                "term": "Helvetische Republik",
                                "hint": "Neue Staatsform in der Schweiz nach 1798.",
                            }
                        ],
                    },
                ],
                "cloze_templates": [],
            }
        },
        focus_group="nmg",
    )
    items = derive_practice_choice_questions(bw, category_label="Schweizer Geschichte", max_count=6)
    assert items
    for item in items:
        prompt = item["q"].lower()
        assert "was bezeichnet" not in prompt
        assert "«schweiz» bei solothurn" not in prompt
        assert "passt" in prompt or "fehlt" in prompt or "ist der" in prompt
        assert len(item.get("options") or []) >= 3
        assert not any(re.match(r"^(Antwort|Begriff)\s+\d+$", o, re.I) for o in item["options"])


def test_derive_practice_dedupes_option_sets_across_modules():
    bw = parse_basiswissen_payload(CASTLE_BASISWISSEN, focus_group="nmg")
    state: dict = {}  # empty dict must still enable cross-module dedup (not falsy-check bug)
    first = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Modul A",
        focus_group="nmg",
        practice_state=state,
    )
    second = derive_practice_items(
        pedagogy=NMG_PEDAGOGY,
        basiswissen=bw,
        category_label="Modul B",
        focus_group="nmg",
        practice_state=state,
    )
    first_sets = {tuple(sorted(i["options"])) for i in first if i.get("options")}
    second_sets = {tuple(sorted(i["options"])) for i in second if i.get("options")}
    assert not first_sets.intersection(second_sets)
