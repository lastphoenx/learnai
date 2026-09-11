"""Tests für visual_tasks-Filter (Vision-Hygiene)."""

from app.core.visual_task_filters import (
    filter_visual_task_entry,
    has_degenerate_placements,
    is_unusable_visual_instruction,
)
from app.ai.source_pedagogy import parse_pedagogy_extraction
import json


def test_is_unusable_visual_instruction_blocks_creative_draw():
    assert is_unusable_visual_instruction("Zeichne hier dein Symbol für die Gegenwart!")
    assert is_unusable_visual_instruction("Einen Gegenstand, der typisch für das 21. Jahrhundert ist")
    assert not is_unusable_visual_instruction("Beschrifte die Teile der Burg am Schema.")


def test_has_degenerate_placements():
    assert has_degenerate_placements(
        [
            {"term": "Zürich", "x": 0.5, "y": 0.5},
            {"term": "Grossmünster", "x": 0.5, "y": 0.5},
        ]
    )
    assert not has_degenerate_placements(
        [
            {"term": "A", "x": 0.2, "y": 0.5},
            {"term": "B", "x": 0.8, "y": 0.5},
        ]
    )


def test_filter_visual_task_entry():
    assert filter_visual_task_entry(
        {"kind": "draw", "instruction": "Zeichne dein Symbol für die Gegenwart!", "terms": ["Gegenwart"]}
    ) is None
    filtered = filter_visual_task_entry(
        {
            "kind": "label",
            "instruction": "Beschrifte das Bild.",
            "terms": ["A", "B"],
            "placements": [
                {"term": "A", "x": 0.5, "y": 0.5},
                {"term": "B", "x": 0.5, "y": 0.5},
            ],
        }
    )
    assert filtered is not None
    assert "placements" not in filtered


def test_parse_pedagogy_filters_unusable_visual_tasks():
    payload = {
        "summary": "Zeitstrahl und Gegenwart.",
        "key_terms": [{"term": "Altsteinzeit", "definition": "bis 9500 v. Chr.", "role": "Zeitperiode"}],
        "assignments": [],
        "visual_tasks": [
            {
                "kind": "draw",
                "instruction": "Zeichne hier dein Symbol für die Gegenwart!",
                "terms": ["Gegenwart"],
                "placements": [{"term": "Gegenwart", "x": 0.75, "y": 0.8}],
            },
            {
                "kind": "label",
                "instruction": "Beschrifte Epochen.",
                "terms": ["A", "B", "C"],
                "placements": [
                    {"term": "A", "x": 0.2, "y": 0.5},
                    {"term": "B", "x": 0.5, "y": 0.5},
                    {"term": "C", "x": 0.8, "y": 0.5},
                ],
            },
        ],
    }
    _summary, pedagogy, structured = parse_pedagogy_extraction(json.dumps(payload))
    assert structured is True
    tasks = pedagogy.get("visual_tasks") or []
    assert len(tasks) == 1
    assert tasks[0]["kind"] == "label"
