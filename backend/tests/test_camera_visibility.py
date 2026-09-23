from app.core.camera_visibility import (
    _camera_world_origin,
    _normalize,
    _ray_first_voxel,
    _world_pos,
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


def test_ray_first_voxel_enters_from_outside_camera():
    matrix = normalize_height_matrix([[1, 0], [0, 1]])
    assert matrix is not None
    view_dir = (1.0, 1.28, -1.0)
    origin = _camera_world_origin(matrix, view_dir)
    tx, ty, tz = _world_pos(0, 0, 0)
    direction = _normalize((tx - origin[0], ty - origin[1], tz - origin[2]))
    hit = _ray_first_voxel(matrix, origin, direction)
    assert hit == (0, 0, 0)


def test_ray_to_rear_cell_hits_that_cell_not_side_column():
    """Perspektivstrahl Kamera→Ziel: (0,0)-Säule liegt nicht auf dem Weg zu (1,1,0)."""
    matrix = normalize_height_matrix([[2, 0], [0, 1]])
    assert matrix is not None
    view_dir = (1.0, 0.0, -1.0)
    origin = _camera_world_origin(matrix, view_dir)
    tx, ty, tz = _world_pos(1, 1, 0)
    direction = _normalize((tx - origin[0], ty - origin[1], tz - origin[2]))
    hit = _ray_first_voxel(matrix, origin, direction)
    assert hit == (1, 1, 0)


def test_ray_to_tall_column_top_hits_that_column():
    """Zielpunkt auf Spalte (0,0) — kein entarteter Gebäudemittelpunkt (Ecken-Diagonale)."""
    matrix = normalize_height_matrix([[2, 0], [1, 0]])
    assert matrix is not None
    view_dir = (1.0, 0.0, -1.0)
    origin = _camera_world_origin(matrix, view_dir)
    tx, ty, tz = _world_pos(0, 0, 1)
    direction = _normalize((tx - origin[0], ty - origin[1], tz - origin[2]))
    hit = _ray_first_voxel(matrix, origin, direction)
    assert hit is not None
    assert hit[0] == 0


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
