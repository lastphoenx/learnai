import json

from app.core.camera_visibility import choose_informative_second_camera, compute_visibility_decision
from app.core.iso_building import normalize_height_matrix
from app.core.spatial_compact import parse_spatial_sequence_items
from app.core.spatial_validator import build_spatial_sequence_item, validate_spatial_sequence_config

_ASYMMETRIC = [
    [1, 0, 3, 1],
    [2, 2, 1, 0],
    [0, 1, 2, 1],
    [1, 0, 1, 2],
]


def test_asymmetric_oblique_requires_second_view():
    matrix = normalize_height_matrix(_ASYMMETRIC)
    assert matrix is not None
    assert compute_visibility_decision(matrix, "oblique") == "second_view_required"


def test_choose_second_camera_informative_for_asymmetric():
    matrix = normalize_height_matrix(_ASYMMETRIC)
    assert matrix is not None
    second = choose_informative_second_camera(matrix, "oblique")
    assert second != "oblique"
    item = build_spatial_sequence_item(matrix, prompt="Test")
    assert not validate_spatial_sequence_config(item["spatial_sequence"])
    assert item["spatial_sequence"]["second_camera"] == second


def test_spatial_sequence_has_top_hint_stage():
    item = build_spatial_sequence_item([[1, 2], [2, 1]], prompt="x")
    stages = item["spatial_sequence"]["stages"]
    top_stages = [s for s in stages if s.get("type") == "inspect" and s.get("camera") == "top"]
    assert len(top_stages) == 1
    assert top_stages[0].get("hint_only") is True


def test_second_camera_is_hint_only_not_main_flow():
    item = build_spatial_sequence_item([[1, 2], [2, 1]], prompt="x")
    second = [
        s
        for s in item["spatial_sequence"]["stages"]
        if s.get("type") == "inspect" and s.get("unlock_hint") == "show_second_camera"
    ]
    assert len(second) == 1
    assert second[0].get("hint_only") is True


def test_parse_ignores_ki_answer_dict():
    matrix = [[1]]
    wrong_answer = {"visibility": "second_view_required", "projections": {"top": [[9]]}}
    raw = parse_spatial_sequence_items(
        [
            {
                "prompt": "p",
                "height_matrix": matrix,
                "answer": wrong_answer,
                "spatial_sequence": {
                    "stages": [
                        {"type": "inspect", "camera": "oblique"},
                        {"type": "visibility_decision"},
                        {"type": "projection_fill", "views": ["top", "front", "right"]},
                    ],
                },
            }
        ]
    )
    assert len(raw) == 1
    answer = json.loads(raw[0]["answer"])
    assert answer["visibility"] == "one_view_sufficient"
    assert answer["projections"]["top"] == [[1]]
