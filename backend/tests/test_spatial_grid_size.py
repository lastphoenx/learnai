import json

from app.core.spatial_compact import score_grid_fill_answer, score_spatial_sequence_answer
from app.core.spatial_grid_size import spatial_sequence_projection_grid_size_hint
from app.core.spatial_validator import build_spatial_sequence_item


def test_build_spatial_sequence_defaults_to_given_grid_hint():
    item = build_spatial_sequence_item([[1, 2], [2, 1]], prompt="x")
    cfg = item["spatial_sequence"]
    pf = next(s for s in cfg["stages"] if s.get("type") == "projection_fill")
    assert pf.get("grid_size_hint") == "given"
    assert cfg.get("visibility_branches")


def test_score_spatial_sequence_derive_rejects_wrong_dimensions():
    item = build_spatial_sequence_item([[2, 1], [1, 2]], prompt="x")
    expected = item["answer"]
    payload = json.loads(expected)
    user_proj = json.loads(json.dumps(payload["projections"]))
    user_proj["front"] = [[0], [0]]
    user = {"visibility": payload["visibility"], "projections": user_proj}
    score = score_spatial_sequence_answer(expected, json.dumps(user), grid_size_hint="derive")
    assert not score["correct"]
    ids = [s["id"] for s in score["slots"]]
    assert "front_size" in ids


def test_score_spatial_sequence_given_ignores_size_slots():
    item = build_spatial_sequence_item([[1]], prompt="x")
    expected = item["answer"]
    score = score_spatial_sequence_answer(expected, expected, grid_size_hint="given")
    assert score["correct"]
    assert not any(str(s.get("id", "")).endswith("_size") for s in score["slots"])


def test_score_grid_fill_derive_wrong_size():
    expected = json.dumps([[1, 0], [0, 1]])
    user = json.dumps([[1]])
    score = score_grid_fill_answer(expected, user, grid_size_hint="derive")
    assert not score["correct"]
    assert score["slots"][0]["id"] == "grid_size"


def test_spatial_sequence_projection_grid_size_hint_from_stage():
    cfg = {
        "stages": [
            {"type": "projection_fill", "views": ["front"], "grid_size_hint": "derive"},
        ]
    }
    assert spatial_sequence_projection_grid_size_hint(cfg) == "derive"
