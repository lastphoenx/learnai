from app.core.camera_visibility import (
    camera_visibility_report,
    column_readable_from_camera,
    compute_visibility_decision,
)
from app.core.iso_building import normalize_height_matrix


def test_front_camera_reads_all_columns():
    matrix = normalize_height_matrix([[1, 0, 3], [2, 1, 0]])
    assert matrix is not None
    report = camera_visibility_report(matrix, "front")
    assert report["all_readable"]


def test_oblique_may_require_second_view_on_asymmetric():
    matrix = normalize_height_matrix(
        [
            [1, 0, 3, 1],
            [2, 2, 1, 0],
            [0, 1, 2, 1],
            [1, 0, 1, 2],
        ]
    )
    assert matrix is not None
    decision = compute_visibility_decision(matrix, "oblique")
    assert decision in ("one_view_sufficient", "second_view_required")
    assert column_readable_from_camera(matrix, 0, "front")
