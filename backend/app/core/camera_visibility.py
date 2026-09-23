"""Sichtbarkeit von Gebäude-Spalten aus didaktischen Kamerapositionen (Prio 3)."""

from __future__ import annotations

import math
from typing import Any

from app.core.iso_building import _height_at, classify_column_visibility

# Richtungen vom Gebäudezentrum zum Betrachter (Three.js: x, y-up, z).
_CAMERA_VIEWER_DIRS: dict[str, tuple[float, float, float]] = {
    "front": (0.0, 0.2, -1.0),
    "back": (0.0, 0.2, 1.0),
    "left": (-1.0, 0.2, 0.0),
    "right": (1.0, 0.2, 0.0),
    "top": (0.0, 1.0, 0.0),
    "oblique": (1.0, 1.28, -1.0),
    "front_left": (-0.75, 0.35, -0.75),
    "front_right": (0.75, 0.35, -0.75),
    "back_left": (-0.75, 0.35, 0.75),
    "back_right": (0.75, 0.35, 0.75),
}

KNOWN_CAMERAS = frozenset(_CAMERA_VIEWER_DIRS.keys())

_ORTHO_SILHOUETTE_CAMERAS = frozenset({"front", "back", "left", "right", "top"})

_ALL_FACE_NAMES = ("top", "bottom", "x_neg", "x_pos", "z_neg", "z_pos")

_SECOND_CAMERA_CANDIDATES: tuple[str, ...] = (
    "front",
    "right",
    "left",
    "front_left",
    "front_right",
    "back_left",
    "top",
)


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x / n, y / n, z / n)


def _face_normal(face: str) -> tuple[float, float, float]:
    return {
        "top": (0.0, 1.0, 0.0),
        "bottom": (0.0, -1.0, 0.0),
        "x_neg": (-1.0, 0.0, 0.0),
        "x_pos": (1.0, 0.0, 0.0),
        "z_neg": (0.0, 0.0, -1.0),
        "z_pos": (0.0, 0.0, 1.0),
        # Legacy iso-Namen
        "left": (-1.0, 0.0, 0.0),
        "right": (0.0, 0.0, -1.0),
    }.get(face, (0.0, 0.0, 0.0))


def _world_pos(x: int, y: int, z: int) -> tuple[float, float, float]:
    """Weltkoordinaten (Three.js): x, Höhe y-up, Tiefe z (matrix-Zeile)."""
    return (x + 0.5, z + 0.5, y + 0.5)


def _world_to_voxel(px: float, py: float, pz: float) -> tuple[int, int, int]:
    return (int(math.floor(px)), int(math.floor(pz)), int(math.floor(py)))


def _grid_extents(matrix: list[list[int]]) -> tuple[int, int, int]:
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    max_h = max(max(r) for r in matrix) if matrix else 0
    return cols, rows, max_h


def _inside_grid(gx: int, gy: int, gz: int, cols: int, rows: int, max_h: int) -> bool:
    return 0 <= gx < cols and 0 <= gy < rows and 0 <= gz < max_h


def _voxel_solid(matrix: list[list[int]], gx: int, gy: int, gz: int) -> bool:
    if gx < 0 or gy < 0 or gz < 0:
        return False
    if gy >= len(matrix) or gx >= len(matrix[0]):
        return False
    return gz < _height_at(matrix, gx, gy)


def _face_visible_6(matrix: list[list[int]], x: int, y: int, z: int, face: str) -> bool:
    h = _height_at(matrix, x, y)
    if z >= h:
        return False
    if face == "top":
        return z + 1 >= h
    if face == "bottom":
        return z > 0
    if face in ("x_neg", "left"):
        return z >= _height_at(matrix, x - 1, y)
    if face == "x_pos":
        return z >= _height_at(matrix, x + 1, y)
    if face in ("z_neg", "right"):
        return z >= _height_at(matrix, x, y - 1)
    if face == "z_pos":
        return z >= _height_at(matrix, x, y + 1)
    return False


def _building_center(matrix: list[list[int]]) -> tuple[float, float, float]:
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    max_h = max(max(r) for r in matrix) if matrix else 1
    return ((cols - 1) / 2.0 + 0.5, (max_h - 1) / 2.0 + 0.5, (rows - 1) / 2.0 + 0.5)


def _camera_world_origin(matrix: list[list[int]], view_dir: tuple[float, float, float]) -> tuple[float, float, float]:
    cx, cy, cz = _building_center(matrix)
    span = max(len(matrix[0]), len(matrix), max(max(r) for r in matrix), 1)
    dist = span * 2.5 + 2.0
    vx, vy, vz = _normalize(view_dir)
    return (cx + vx * dist, cy + vy * dist, cz + vz * dist)


def _ray_first_voxel(
    matrix: list[list[int]],
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    *,
    max_steps: int = 512,
    step: float = 0.08,
) -> tuple[int, int, int] | None:
    """Erster fester Würfel auf dem Strahl (Kamera liegt typischerweise außerhalb des Rasters)."""
    ox, oy, oz = origin
    dx, dy, dz = _normalize(direction)
    cols, rows, max_h = _grid_extents(matrix)
    if cols == 0 or rows == 0 or max_h == 0:
        return None

    span = max(cols, rows, max_h)
    entered_bounds = False
    t = 0.0
    max_t = span * 8.0
    steps = 0
    while t <= max_t and steps < max_steps:
        px = ox + dx * t
        py = oy + dy * t
        pz = oz + dz * t
        gx, gy, gz = _world_to_voxel(px, py, pz)
        inside = _inside_grid(gx, gy, gz, cols, rows, max_h)
        if not inside:
            if entered_bounds:
                return None
            t += step
            steps += 1
            continue
        entered_bounds = True
        if _voxel_solid(matrix, gx, gy, gz):
            return (gx, gy, gz)
        t += step
        steps += 1
    return None


def _face_occluded_along_view(
    matrix: list[list[int]],
    x: int,
    y: int,
    z: int,
    face: str,
    view_dir: tuple[float, float, float],
    *,
    max_steps: int = 120,
    step: float = 0.12,
) -> bool:
    """True, wenn ein anderer Würfel die Sicht von dieser Fläche zur Kamera verdeckt."""
    wx, wy, wz = _world_pos(x, y, z)
    nx, ny, nz = _face_normal(face)
    ox, oy, oz = wx + 1e-3 * nx, wy + 1e-3 * ny, wz + 1e-3 * nz
    vx, vy, vz = view_dir
    cols, rows, max_h = _grid_extents(matrix)
    entered = False
    t = step
    for _ in range(max_steps):
        px = ox + vx * t
        py = oy + vy * t
        pz = oz + vz * t
        gx, gy, gz = _world_to_voxel(px, py, pz)
        inside = _inside_grid(gx, gy, gz, cols, rows, max_h)
        if not inside:
            if entered:
                return False
            t += step
            continue
        entered = True
        if not _voxel_solid(matrix, gx, gy, gz):
            t += step
            continue
        if (gx, gy, gz) == (x, y, z):
            t += step
            continue
        return True
    return False


def _column_critical_top_voxel(matrix: list[list[int]], col: int) -> tuple[int, int, int] | None:
    """Oberster Würfel der höchsten Stelle in dieser Spalte (didaktisch relevant)."""
    rows = len(matrix)
    heights = [_height_at(matrix, col, y) for y in range(rows)]
    max_h = max(heights) if heights else 0
    if max_h < 1:
        return None
    critical_y = next((i for i, h in enumerate(heights) if h == max_h), 0)
    return (col, critical_y, max_h - 1)


def _face_toward_camera(
    matrix: list[list[int]], x: int, y: int, z: int, face: str, view_dir: tuple[float, float, float]
) -> bool:
    if not _face_visible_6(matrix, x, y, z, face):
        return False
    nx, ny, nz = _face_normal(face)
    vx, vy, vz = view_dir
    if nx * vx + ny * vy + nz * vz <= 0.05:
        return False
    return not _face_occluded_along_view(matrix, x, y, z, face, view_dir)


def _column_center_ray_readable(
    matrix: list[list[int]], col: int, view_dir: tuple[float, float, float]
) -> bool:
    critical = _column_critical_top_voxel(matrix, col)
    if critical is None:
        return False
    x, y, z = critical
    origin = _camera_world_origin(matrix, view_dir)
    tx, ty, tz = _world_pos(x, y, z)
    hit = _ray_first_voxel(matrix, origin, (tx - origin[0], ty - origin[1], tz - origin[2]))
    return hit == critical


def _ortho_column_readable(matrix: list[list[int]], col: int, camera: str) -> bool:
    """Orthographische Lesbarkeit der Spalten-Maximalhöhe (nicht volle 3D-Rekonstruktion)."""
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    if not any(_height_at(matrix, col, y) > 0 for y in range(rows)):
        return False
    cam = camera.strip().lower()
    if cam in ("front", "back"):
        return True
    if cam == "top":
        return True
    if cam in ("right", "left") and cols <= 1:
        return True
    return False


def column_readable_from_camera(matrix: list[list[int]], col: int, camera: str) -> bool:
    """True, wenn die Spalten-Maximalhöhe aus dieser Kamera erkennbar ist."""
    cam = (camera or "oblique").strip().lower()
    if cam in _ORTHO_SILHOUETTE_CAMERAS:
        return _ortho_column_readable(matrix, col, cam)
    view_dir = _normalize(_CAMERA_VIEWER_DIRS.get(cam, _CAMERA_VIEWER_DIRS["oblique"]))
    if _column_center_ray_readable(matrix, col, view_dir):
        return True
    critical = _column_critical_top_voxel(matrix, col)
    if critical is None:
        return False
    x, y, z = critical
    for face in _ALL_FACE_NAMES:
        if _face_toward_camera(matrix, x, y, z, face, view_dir):
            return True
    return False


def camera_visibility_report(matrix: list[list[int]], camera: str) -> dict[str, Any]:
    cols = len(matrix[0]) if matrix else 0
    columns = []
    for c in range(cols):
        columns.append(
            {
                "col": c,
                "label": chr(65 + c) if c < 26 else str(c),
                "readable": column_readable_from_camera(matrix, c, camera),
            }
        )
    return {
        "camera": camera,
        "all_readable": all(c["readable"] for c in columns),
        "columns": columns,
    }


def compute_visibility_decision(matrix: list[list[int]], first_camera: str) -> str:
    """«one_view_sufficient» oder «second_view_required» für die erste (oft schräge) Sicht."""
    cam = (first_camera or "oblique").strip().lower()
    if cam in _ORTHO_SILHOUETTE_CAMERAS:
        return "one_view_sufficient"
    iso = classify_column_visibility(matrix)
    if not iso.get("all_readable"):
        return "second_view_required"
    report = camera_visibility_report(matrix, cam)
    if report["all_readable"]:
        return "one_view_sufficient"
    return "second_view_required"


def second_camera_informative(matrix: list[list[int]], first: str, second: str) -> bool:
    """Zweite Kamera soll mindestens eine zuvor verdeckte Spalte lesbar machen."""
    r1 = camera_visibility_report(matrix, first)
    r2 = camera_visibility_report(matrix, second)
    if r2["all_readable"]:
        return True
    for c1, c2 in zip(r1["columns"], r2["columns"], strict=False):
        if not c1["readable"] and c2["readable"]:
            return True
    return False


def choose_informative_second_camera(matrix: list[list[int]], first: str) -> str:
    """Kamera mit maximal neu lesbaren Spalten nach der ersten Sicht."""
    first = (first or "oblique").strip().lower()
    r1 = camera_visibility_report(matrix, first)
    best = "front_right"
    best_score = -1
    for cam in _SECOND_CAMERA_CANDIDATES:
        if cam == first:
            continue
        if not second_camera_informative(matrix, first, cam):
            continue
        r2 = camera_visibility_report(matrix, cam)
        newly = sum(
            1
            for c1, c2 in zip(r1["columns"], r2["columns"], strict=False)
            if not c1["readable"] and c2["readable"]
        )
        readable = sum(1 for c in r2["columns"] if c["readable"])
        score = newly * 100 + readable
        if score > best_score:
            best_score = score
            best = cam
    if best_score < 0:
        return "front"
    return best
