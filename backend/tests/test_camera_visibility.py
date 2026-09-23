from app.core.camera_visibility import (
    _ortho_ray_first_voxel_at,
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


def test_compute_visibility_ortho_right_requires_second_view():
    matrix = normalize_height_matrix([[1, 1, 1, 1]])
    assert matrix is not None
    assert compute_visibility_decision(matrix, "right") == "second_view_required"


def test_compute_visibility_ortho_front_sufficient_for_columns():
    matrix = normalize_height_matrix([[1, 0, 3], [2, 1, 0]])
    assert matrix is not None
    assert compute_visibility_decision(matrix, "front") == "one_view_sufficient"


def test_right_ortho_not_all_width_columns_readable():
    matrix = normalize_height_matrix([[1, 1, 1, 1]])
    assert matrix is not None
    report = camera_visibility_report(matrix, "right")
    assert not report["all_readable"]
    assert not any(c["readable"] for c in report["columns"])


def test_ortho_parallel_ray_hits_target_voxel():
    matrix = normalize_height_matrix([[1, 0], [0, 1]])
    assert matrix is not None
    view_dir = (1.0, 1.28, -1.0)
    hit = _ortho_ray_first_voxel_at(matrix, 0, 0, 0, view_dir)
    assert hit == (0, 0, 0)


def test_ortho_parallel_ray_through_rear_blocked_by_front():
    """Blick (1,0,-1): vorn (1,0), hinten (0,1) — Parallelstrahl zur hinteren Säule trifft vorn zuerst."""
    matrix = normalize_height_matrix([[0, 1], [1, 0]])
    assert matrix is not None
    view_dir = (1.0, 0.0, -1.0)
    hit = _ortho_ray_first_voxel_at(matrix, 0, 1, 0, view_dir)
    assert hit == (1, 0, 0)


def test_ortho_parallel_ray_to_front_corner_not_blocked_by_rear():
    matrix = normalize_height_matrix([[2, 0], [0, 1]])
    assert matrix is not None
    view_dir = (1.0, 0.0, -1.0)
    hit = _ortho_ray_first_voxel_at(matrix, 1, 1, 0, view_dir)
    assert hit == (1, 1, 0)


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
    assert decision == "second_view_required"
    assert column_readable_from_camera(matrix, 0, "front")
