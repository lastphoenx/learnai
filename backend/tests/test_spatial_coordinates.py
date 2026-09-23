"""Raumvertrag und orthographische Ansichten (Golden-Matrizen)."""

from app.core.iso_building import building_projections, score_derived_projection_answer
from app.core.spatial_coordinates import FRONT_ROW, spatial_coordinate_system


def test_spatial_coordinate_system_contract():
    sys = spatial_coordinate_system()
    assert sys["front_row"] == FRONT_ROW == 0
    assert sys["x_direction"] == "left-to-right"


def test_building_projections_single_cube():
    matrix = [[1]]
    views = building_projections(matrix)
    assert views["top"] == [[1]]
    assert views["front"] == [[1]]
    assert views["right"] == [[1]]


def test_building_projections_asymmetric_4x4():
    matrix = [
        [1, 0, 3, 1],
        [2, 2, 1, 0],
        [0, 1, 2, 1],
        [1, 0, 1, 2],
    ]
    views = building_projections(matrix)
    assert views["top"] == matrix
    assert views["front"] == [
        [1, 1, 1, 1],
        [1, 1, 1, 1],
        [0, 0, 1, 0],
    ]
    assert views["right"] == [
        [1, 1, 1, 1],
        [1, 1, 1, 1],
        [1, 0, 0, 0],
    ]


def test_building_projections_front_uses_column_max_not_depth_slice():
    """Zwei Stapel in einer Spalte — Vorderansicht = max, nicht y=0 und y=1 getrennt."""
    matrix = [[1, 0], [3, 0]]
    views = building_projections(matrix)
    assert views["front"] == [[1, 0], [1, 0], [1, 0]]


def test_score_derived_projection_against_fixed_expected():
    matrix = [[1, 0], [2, 1]]
    expected = building_projections(matrix)
    import json

    assert score_derived_projection_answer(json.dumps(expected), json.dumps(matrix))["correct"]
