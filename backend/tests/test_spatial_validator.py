import json

from app.core.spatial_validator import (
    build_spatial_sequence_item,
    validate_height_matrix,
    validate_spatial_sequence_config,
)
from app.core.spatial_compact import parse_spatial_sequence_items, score_spatial_sequence_answer


def test_validate_height_matrix_rejects_empty():
    assert validate_height_matrix([])


def test_build_spatial_sequence_item_deterministic():
    item = build_spatial_sequence_item([[1, 2], [2, 1]], prompt="Untersuche das Gebäude.")
    assert item["spatial_sequence"]["schema_version"] == 1
    assert not validate_spatial_sequence_config(item["spatial_sequence"])
    answer = json.loads(item["answer"])
    assert "visibility" in answer
    assert "projections" in answer


def test_parse_and_score_spatial_sequence():
    raw = parse_spatial_sequence_items(
        [
            {
                "prompt": "Ansichten",
                "height_matrix": [[1]],
            }
        ]
    )
    assert len(raw) == 1
    expected = raw[0]["answer"]
    user = expected
    assert score_spatial_sequence_answer(expected, user)["correct"]
