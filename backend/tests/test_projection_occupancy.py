import json

from app.core.iso_building import projection_grids_equal, top_occupancy_grid
from app.core.spatial_compact import score_spatial_sequence_answer
from app.core.spatial_validator import build_spatial_sequence_answer


def test_top_occupancy_is_binary():
    matrix = [[2, 0], [1, 3]]
    occ = top_occupancy_grid(matrix)
    assert occ == [[1, 0], [1, 1]]


def test_score_top_accepts_marked_instead_of_height():
    matrix = [[2, 0], [1, 0]]
    expected = json.dumps(build_spatial_sequence_answer(matrix))
    user_payload = json.loads(expected)
    user_payload["projections"]["top"] = [[1, 0], [1, 0]]
    score = score_spatial_sequence_answer(expected, json.dumps(user_payload))
    assert score["correct"]


def test_projection_grids_equal_top_ignores_height_magnitude():
    assert projection_grids_equal("top", [[2]], [[1]])
    assert not projection_grids_equal("top", [[0]], [[1]])
