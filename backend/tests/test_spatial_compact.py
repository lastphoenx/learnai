"""Tests für räumliche posten_compact-Aufgaben."""

import json

from app.core.region_layouts import get_region_template, list_region_template_ids
from app.core.spatial_compact import (
    apply_spatial_fallback_to_payload,
    count_spatial_practice_in_modules,
    grade_image_choice,
    grade_point_on_image,
    parse_bbox,
    parse_grid_fill_items,
    parse_image_choice_items,
    parse_net_build_items,
    parse_point_on_image_items,
    parse_building_paint_items,
    parse_region_paint_items,
    parse_synthetic_viewpoint_items,
    score_grid_fill_answer,
    score_net_build_answer,
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
                "reference_height_matrix": [[1, 2], [3, 1]],
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
    three_js_keys = json.dumps({"0,0,0,top": "green", "0,0,0,left": "yellow"})
    assert score_region_paint_answer(expected, three_js_keys)["correct"]


def test_region_paint_legacy_template_uses_svg_not_three():
    raw = parse_region_paint_items(
        [
            {
                "prompt": "oben gelb",
                "template": "iso_single_cube",
                "answer": {"top": "yellow"},
            }
        ]
    )
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        region_paint=raw,
        source_ids=[],
    )
    assert items[0]["region_paint"].get("height_matrix") is None


def test_building_paint_to_practice():
    raw = parse_building_paint_items(
        [
            {
                "prompt": "Färbe das Gebäude.",
                "height_matrix": [[1, 0], [1, 2]],
                "colored_faces": {"0,0,0,top": "green"},
            }
        ]
    )
    assert len(raw) == 1
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        region_paint=[],
        building_paint=raw,
        source_ids=[],
    )
    assert items[0]["answer_type"] == "building_paint"
    assert items[0]["building_paint"]["regions"]


def test_spatial_fallback_fills_empty_payload():
    payload: dict = {"goal": "Körper und Pläne"}
    assert apply_spatial_fallback_to_payload(payload, goal=payload["goal"])
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        building_paint=parse_building_paint_items(payload.get("building_paint_items")),
        net_build=parse_net_build_items(payload.get("net_build_items")),
        source_ids=[],
    )
    assert len(items) >= 2
    types = {i["answer_type"] for i in items}
    assert "building_paint" in types
    assert "net_build" in types


def test_parse_grid_fill_number_exact_match_requires_reference_matrix():
    rows = parse_grid_fill_items(
        [
            {
                "prompt": "Ergänze den Höhenplan.",
                "rows": 2,
                "cols": 3,
                "cell_type": "number",
                "validation": "exact_match",
                "answer": [[1, 2, 0], [1, 0, 0]],
            }
        ]
    )
    assert rows == []
    rows_ok = parse_grid_fill_items(
        [
            {
                "prompt": "Ergänze den Höhenplan.",
                "rows": 2,
                "cols": 3,
                "cell_type": "number",
                "validation": "exact_match",
                "reference_height_matrix": [[1, 2, 0], [1, 0, 0]],
                "answer": [[1, 2, 0], [1, 0, 0]],
            }
        ]
    )
    assert len(rows_ok) == 1
    assert rows_ok[0]["reference_height_matrix"] is not None


def test_parse_grid_fill_derived_projection_keeps_reference_matrix():
    rows = parse_grid_fill_items(
        [
            {
                "prompt": "Aufsicht ableiten",
                "rows": 3,
                "cols": 3,
                "validation": "derived_projection",
                "answer": {"height_matrix": [[2, 1], [1, 0]]},
            }
        ]
    )
    assert len(rows) == 1
    assert rows[0]["reference_height_matrix"] is not None


def test_net_build_answer_always_valid_net():
    raw = parse_net_build_items(
        [
            {
                "prompt": "Lege ein Würfelnetz mit vier in einer Reihe und falscher Prosa.",
                "rows": 4,
                "cols": 4,
                "answer": "valid_net",
            }
        ]
    )
    assert len(raw) == 1
    assert raw[0]["answer"] == "valid_net"
    assert "falscher Prosa" not in raw[0]["prompt"]
    assert "viele richtige Lösungen" in raw[0]["prompt"]
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        region_paint=[],
        net_build=raw,
        source_ids=[],
    )
    assert json.loads(items[0]["answer"]) == "valid_net"
    cross = json.dumps([[0, 1], [1, 1], [2, 1], [1, 0], [1, 2], [1, 3]])
    assert score_net_build_answer(items[0]["answer"], cross)["correct"]


def test_net_build_target_cells_replaces_prompt_and_scores_exact_cells():
    cross = [[0, 1], [1, 1], [2, 1], [3, 1], [2, 0], [2, 2]]
    raw = parse_net_build_items(
        [
            {
                "prompt": "Halluzinierte zweite Fläche — wird ignoriert.",
                "rows": 4,
                "cols": 4,
                "target_cells": cross,
                "answer": "valid_net",
            }
        ]
    )
    assert len(raw) == 1
    assert "dritten" in raw[0]["prompt"]
    assert "Halluzinierte" not in raw[0]["prompt"]
    assert raw[0]["answer"] == cross
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        net_build=raw,
        source_ids=[],
    )
    assert score_net_build_answer(items[0]["answer"], json.dumps(cross))["correct"]
    wrong = json.dumps([[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0]])
    assert not score_net_build_answer(items[0]["answer"], wrong)["correct"]


def test_net_build_validate_mode():
    cross = [[0, 1], [1, 1], [2, 1], [1, 0], [1, 2], [1, 3]]
    raw = parse_net_build_items(
        [
            {
                "prompt": "Prüfe das Netz.",
                "rows": 4,
                "cols": 4,
                "given_cells": cross,
                "answer": "valid",
            }
        ]
    )
    assert raw[0]["mode"] == "validate"
    assert raw[0]["answer"] is True
    items = spatial_raw_to_practice_items(
        image_choice=[],
        point_on_image=[],
        grid_fill=[],
        net_build=raw,
        source_ids=[],
    )
    assert items[0]["net_build"]["mode"] == "validate"
    assert score_net_build_answer(items[0]["answer"], json.dumps(True))["correct"]
    assert not score_net_build_answer(items[0]["answer"], json.dumps(False))["correct"]

    wrong_ai = parse_net_build_items(
        [
            {
                "prompt": "Prüfe das Netz.",
                "rows": 4,
                "cols": 4,
                "given_cells": cross,
                "answer": False,
            }
        ]
    )
    assert wrong_ai[0]["answer"] is True


def test_synthetic_viewpoint_requires_meaningful_labels():
    raw = parse_synthetic_viewpoint_items(
        [
            {
                "prompt": "Wo steht der Betrachter?",
                "height_matrix": [[1, 2], [1, 0]],
                "candidates": [
                    {"id": "A", "label": "Vorne am Plan"},
                    {"id": "B", "direction": "rechts"},
                ],
                "answer": "B",
            }
        ]
    )
    assert len(raw) == 1
    assert raw[0]["candidates"][1]["label"].startswith("Rechts")
    assert "x" in raw[0]["candidates"][0]


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
