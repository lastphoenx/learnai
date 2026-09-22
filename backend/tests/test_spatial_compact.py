"""Tests für räumliche posten_compact-Aufgaben."""

import json

from app.core.region_layouts import get_region_template, list_region_template_ids
from app.core.spatial_compact import (
    count_spatial_practice_in_modules,
    grade_image_choice,
    grade_point_on_image,
    parse_bbox,
    parse_grid_fill_items,
    parse_image_choice_items,
    parse_point_on_image_items,
    parse_region_paint_items,
    score_grid_fill_answer,
    score_region_paint_answer,
    should_enable_spatial_compact_exercises,
    spatial_raw_to_practice_items,
    tap_hit_radius,
)


def test_should_enable_spatial_compact():
    assert should_enable_spatial_compact_exercises(
        focus_group="math", math_focus="geometry_spatial", multimodal=True
    )
    assert should_enable_spatial_compact_exercises(
        focus_group="math", math_focus="geometry", multimodal=True
    )
    assert not should_enable_spatial_compact_exercises(
        focus_group="math", math_focus="decimals", multimodal=True
    )
    assert not should_enable_spatial_compact_exercises(
        focus_group="math", math_focus="geometry", multimodal=False
    )


def test_parse_bbox_and_padding():
    bbox = parse_bbox({"x": 0.1, "y": 0.2, "w": 0.2, "h": 0.15})
    assert bbox is not None
    assert parse_bbox({"x": 0, "y": 0, "w": 0.01, "h": 0.5}) is None


def test_image_choice_to_practice():
    raw = parse_image_choice_items(
        [
            {
                "prompt": "Welcher Bauplan?",
                "options": [
                    {"id": "A", "image_ref": {"source_index": 0, "x": 0.1, "y": 0.2, "w": 0.15, "h": 0.12}},
                    {"id": "B", "image_ref": {"source_index": 0, "x": 0.3, "y": 0.2, "w": 0.15, "h": 0.12}},
                ],
                "answer": "B",
            }
        ]
    )
    items = spatial_raw_to_practice_items(
        image_choice=raw,
        point_on_image=[],
        grid_fill=[],
        source_ids=["src-uuid-1"],
    )
    assert len(items) == 1
    assert items[0]["answer_type"] == "image_choice"
    assert items[0]["answer"] == "B"
    assert len(items[0]["image_choice"]["options"]) == 2


def test_point_on_image_candidate_grade():
    item = {
        "point_on_image": {
            "selection_mode": "candidate",
            "candidates": [{"id": "A", "x": 0.2, "y": 0.3}, {"id": "B", "x": 0.8, "y": 0.7}],
        }
    }
    assert grade_point_on_image("B", "B", item=item)
    assert not grade_point_on_image("B", "A", item=item)


def test_grid_fill_score():
    expected = json.dumps([[4, 2], [1, None]])
    user_ok = json.dumps([[4, 2], [1, None]])
    user_bad = json.dumps([[4, 3], [1, None]])
    assert score_grid_fill_answer(expected, user_ok)["correct"]
    assert not score_grid_fill_answer(expected, user_bad)["correct"]


def test_parse_grid_fill_items():
    rows = parse_grid_fill_items(
        [
            {
                "prompt": "Bauplan",
                "rows": 2,
                "cols": 2,
                "cell_type": "number",
                "answer": [[1, 2], [3, None]],
            }
        ]
    )
    assert len(rows) == 1
    assert rows[0]["rows"] == 2


def test_tap_hit_radius_bounded():
    candidates = [{"id": "A", "x": 0.1, "y": 0.1}, {"id": "B", "x": 0.5, "y": 0.1}]
    r = tap_hit_radius(candidates)
    assert 0.02 <= r <= 0.08


def test_grade_image_choice():
    assert grade_image_choice("a", "A")


def test_region_templates_exist():
    ids = list_region_template_ids()
    assert "iso_single_cube" in ids
    assert get_region_template("iso_single_cube") is not None


def test_region_paint_parse_and_practice():
    raw = parse_region_paint_items(
        [
            {
                "prompt": "Färbe die Flächen.",
                "template": "iso_single_cube",
                "answer": {"top": "green", "left": "purple"},
            }
        ]
    )
    assert len(raw) == 1
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        region_paint=raw,
        source_ids=[],
    )
    assert len(items) == 1
    assert items[0]["answer_type"] == "region_paint"
    assert len(items[0]["region_paint"]["regions"]) == 3


def test_score_region_paint_answer():
    expected = json.dumps({"top": "green", "left": "yellow"})
    ok = json.dumps({"top": "green", "left": "yellow"})
    bad = json.dumps({"top": "green", "left": "purple"})
    assert score_region_paint_answer(expected, ok)["correct"]
    assert not score_region_paint_answer(expected, bad)["correct"]


def test_count_spatial_practice_in_modules():
    modules = [
        {
            "title": "Aufgaben",
            "content": {
                "practice": [
                    {"answer_type": "choice"},
                    {"answer_type": "region_paint"},
                ]
            },
        }
    ]
    assert count_spatial_practice_in_modules(modules) == 1
