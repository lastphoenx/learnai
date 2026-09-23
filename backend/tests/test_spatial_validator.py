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
    item = build_spatial_sequence_item(
        [[1, 2], [2, 1]],
        prompt="Baue das Würfelgebäude Schritt für Schritt — wird ignoriert.",
    )
    assert item["spatial_sequence"]["schema_version"] == 1
    assert not validate_spatial_sequence_config(item["spatial_sequence"])
    answer = json.loads(item["answer"])
    assert "visibility" in answer
    assert "projections" in answer
    p = item["prompt"].lower()
    assert "baue das würfelgebäude schritt" not in p
    assert "ansicht" in p or "perspektive" in p
    assert item["spatial_sequence"].get("visibility_branches")


def test_spatial_sequence_prompt_replaces_misleading_ai_text():
    raw = parse_spatial_sequence_items(
        [
            {
                "prompt": (
                    "Baue das Stufengebäude aus dem Höhenplan. Prüfe, ob jede Säule die angegebene Höhe besitzt."
                ),
                "height_matrix": [[2, 1], [1, 2]],
            }
        ]
    )
    assert len(raw) == 1
    p = raw[0]["prompt"].lower()
    for forbidden in ("baue das", "untersten schicht", "säule", "höhenplan"):
        assert forbidden not in p
    assert "vorder-" in p or "ansicht" in p


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
