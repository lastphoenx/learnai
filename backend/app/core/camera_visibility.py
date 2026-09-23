"""Sichtbarkeit von Gebäude-Spalten aus didaktischen Kamerapositionen (Prio 3)."""

from __future__ import annotations

import math
from typing import Any

from app.core.iso_building import _height_at, classify_column_visibility, normalize_height_matrix

# Richtungen vom Gebäudezentrum zum Betrachter (Three.js: x, y-up, z).
_CAMERA_VIEWER_DIRS: dict[str, tuple[float, float, float]] = {
    "front": (0.0, 0.2, -1.0),
    "back": (0.0, 0.2, 1.0),
    "left": (-1.0, 0.2, 0.0),
    "right": (1.0, 0.2, 0.0),
    "top": (0.0, 1.0, 0.0),
    "oblique": (1.0, 1.28, 1.0),
    "front_left": (-0.75, 0.35, -0.75),
    "front_right": (0.75, 0.35, -0.75),
    "back_left": (-0.75, 0.35, 0.75),
    "back_right": (0.75, 0.35, 0.75),
}

_ORTHO_SILHOUETTE_CAMERAS = frozenset({"front", "back", "left", "right", "top"})


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x / n, y / n, z / n)


def _voxel_center(x: int, y: int, z: int, gap: float = 1.02) -> tuple[float, float, float]:
    return (x * gap, z * gap + 0.47, y * gap)


def _face_normal(face: str) -> tuple[float, float, float]:
    if face == "top":
        return (0.0, 1.0, 0.0)
    if face == "left":
        return (-1.0, 0.0, 0.0)
    if face == "right":
        return (0.0, 0.0, -1.0)
    return (0.0, 0.0, 0.0)


def _world_pos(x: int, y: int, z: int) -> tuple[float, float, float]:
    """Weltkoordinaten (Three.js): x, Höhe y-up, Tiefe z (matrix-Zeile)."""
    return (x + 0.5, z + 0.5, y + 0.5)


def _world_to_voxel(px: float, py: float, pz: float) -> tuple[int, int, int]:
    return (int(math.floor(px)), int(math.floor(pz)), int(math.floor(py)))


def _voxel_solid(matrix: list[list[int]], gx: int, gy: int, gz: int) -> bool:
    if gx < 0 or gy < 0 or gz < 0:
        return False
    if gy >= len(matrix) or gx >= len(matrix[0]):
        return False
    return gz < _height_at(matrix, gx, gy)


def _face_occluded_along_view(
    matrix: list[list[int]],
    x: int,
    y: int,
    z: int,
    face: str,
    view_dir: tuple[float, float, float],
    *,
    max_steps: int = 80,
    step: float = 0.2,
) -> bool:
    """True, wenn ein anderer Würfel die Sicht von dieser Fläche zur Kamera verdeckt."""
    wx, wy, wz = _world_pos(x, y, z)
    nx, ny, nz = _face_normal(face)
    ox, oy, oz = wx + 1e-3 * nx, wy + 1e-3 * ny, wz + 1e-3 * nz
    vx, vy, vz = view_dir
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    t = step
    for _ in range(max_steps):
        px = ox + vx * t
        py = oy + vy * t
        pz = oz + vz * t
        gx, gy, gz = _world_to_voxel(px, py, pz)
        if gx < 0 or gy < 0 or gz < 0 or gy >= rows or gx >= cols:
            return False
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
    from app.core.iso_building import _face_visible

    if not _face_visible(matrix, x, y, z, face):
        return False
    nx, ny, nz = _face_normal(face)
    vx, vy, vz = view_dir
    if nx * vx + ny * vy + nz * vz <= 0.05:
        return False
    return not _face_occluded_along_view(matrix, x, y, z, face, view_dir)


def column_readable_from_camera(matrix: list[list[int]], col: int, camera: str) -> bool:
    """True, wenn die Spalte aus dieser Kamera die Höheninformation erkennbar liefert."""
    if camera in _ORTHO_SILHOUETTE_CAMERAS:
        return any(_height_at(matrix, col, y) > 0 for y in range(len(matrix)))
    view_dir = _normalize(_CAMERA_VIEWER_DIRS.get(camera, _CAMERA_VIEWER_DIRS["oblique"]))
    critical = _column_critical_top_voxel(matrix, col)
    if critical is None:
        return False
    x, y, z = critical
    for face in ("top", "left", "right"):
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
