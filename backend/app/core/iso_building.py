"""Isometrischer Gebäude-Renderer (Höhenmatrix → Flächen / Ansichten)."""

from __future__ import annotations

from collections import deque
from typing import Any

# Analog grid_fill, enger für Mobile (Referenz-App 4×4).
BUILDING_MATRIX_MIN = 1
BUILDING_MATRIX_MAX = 8
BUILDING_HEIGHT_MAX = 12

_ISO_ORIGIN_X = 210.0
_ISO_ORIGIN_Y = 250.0
_ISO_DX = 38.0
_ISO_DY = 19.0
_ISO_DZ = 38.0

_LEGACY_TEMPLATE_MATRICES: dict[str, list[list[int]]] = {
    "iso_single_cube": [[1]],
    "iso_tower_2": [[2]],
}

# Feste Flächen-IDs für bestehende region_paint-Templates (Abwärtskompatibilität).
_LEGACY_FACE_IDS: dict[str, dict[tuple[int, int, int, str], str]] = {
    "iso_single_cube": {
        (0, 0, 0, "top"): "top",
        (0, 0, 0, "left"): "left",
        (0, 0, 0, "right"): "right",
    },
    "iso_tower_2": {
        (0, 0, 0, "top"): "lower_top",
        (0, 0, 0, "left"): "lower_left",
        (0, 0, 0, "right"): "lower_right",
        (0, 0, 1, "top"): "upper_top",
        (0, 0, 1, "left"): "upper_left",
        (0, 0, 1, "right"): "upper_right",
    },
}

_FACE_NAMES = ("top", "left", "right")

_LEGACY_REGION_LABELS: dict[str, str] = {
    "top": "oben",
    "left": "links",
    "right": "rechts",
    "lower_top": "unten oben",
    "lower_left": "unten links",
    "lower_right": "unten rechts",
    "upper_top": "oben oben",
    "upper_left": "oben links",
    "upper_right": "oben rechts",
}


def iso_point(x: float, y: float, z: float) -> tuple[float, float]:
    px = _ISO_ORIGIN_X + (x - y) * _ISO_DX
    py = _ISO_ORIGIN_Y + (x + y) * _ISO_DY - z * _ISO_DZ
    return (px, py)


def normalize_height_matrix(raw: object) -> list[list[int]] | None:
    if not isinstance(raw, list) or not raw:
        return None
    rows: list[list[int]] = []
    cols: int | None = None
    for row in raw:
        if not isinstance(row, list) or not row:
            return None
        if cols is None:
            cols = len(row)
        elif len(row) != cols:
            return None
        parsed_row: list[int] = []
        for cell in row:
            try:
                h = int(cell)
            except (TypeError, ValueError):
                return None
            if h < 0 or h > BUILDING_HEIGHT_MAX:
                return None
            parsed_row.append(h)
        rows.append(parsed_row)
    if not rows or cols is None:
        return None
    if not (BUILDING_MATRIX_MIN <= len(rows) <= BUILDING_MATRIX_MAX):
        return None
    if not (BUILDING_MATRIX_MIN <= cols <= BUILDING_MATRIX_MAX):
        return None
    if not any(any(h > 0 for h in r) for r in rows):
        return None
    return rows


def _height_at(matrix: list[list[int]], x: int, y: int) -> int:
    if y < 0 or y >= len(matrix) or x < 0 or x >= len(matrix[0]):
        return 0
    return int(matrix[y][x])


def _face_polygon(x: int, y: int, z: int, face: str) -> list[tuple[float, float]]:
    if face == "top":
        return [
            iso_point(x, y, z + 1),
            iso_point(x + 1, y, z + 1),
            iso_point(x + 1, y + 1, z + 1),
            iso_point(x, y + 1, z + 1),
        ]
    if face == "left":
        return [
            iso_point(x, y, z + 1),
            iso_point(x, y + 1, z + 1),
            iso_point(x, y + 1, z),
            iso_point(x, y, z),
        ]
    if face == "right":
        return [
            iso_point(x + 1, y, z + 1),
            iso_point(x + 1, y + 1, z + 1),
            iso_point(x + 1, y + 1, z),
            iso_point(x + 1, y, z),
        ]
    raise ValueError(face)


def _face_visible(matrix: list[list[int]], x: int, y: int, z: int, face: str) -> bool:
    if face == "top":
        return z + 1 >= _height_at(matrix, x, y)
    if face == "left":
        return z >= _height_at(matrix, x - 1, y)
    if face == "right":
        return z >= _height_at(matrix, x, y - 1)
    return False


def iter_visible_faces(matrix: list[list[int]]) -> list[tuple[int, int, int, str]]:
    out: list[tuple[int, int, int, str]] = []
    rows = len(matrix)
    cols = len(matrix[0])
    for y in range(rows - 1, -1, -1):
        for x in range(cols):
            h = _height_at(matrix, x, y)
            for z in range(h):
                for face in _FACE_NAMES:
                    if _face_visible(matrix, x, y, z, face):
                        out.append((x, y, z, face))
    return out


def face_id(x: int, y: int, z: int, face: str) -> str:
    return f"{x},{y},{z},{face}"


def resolve_region_id(
    x: int, y: int, z: int, face: str, *, legacy_template: str | None = None
) -> str:
    if legacy_template:
        mapped = _LEGACY_FACE_IDS.get(legacy_template, {}).get((x, y, z, face))
        if mapped:
            return mapped
    return face_id(x, y, z, face)


def _normalize_polygons(
    polygons: list[list[tuple[float, float]]],
    *,
    view_width: float = 400.0,
    view_height: float = 300.0,
    padding: float = 24.0,
) -> tuple[list[list[list[float]]], float, float]:
    if not polygons:
        return [], view_width, view_height
    xs = [p[0] for poly in polygons for p in poly]
    ys = [p[1] for poly in polygons for p in poly]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    inner_w = view_width - 2 * padding
    inner_h = view_height - 2 * padding
    scale = min(inner_w / span_x, inner_h / span_y)
    out: list[list[list[float]]] = []
    for poly in polygons:
        norm: list[list[float]] = []
        for px, py in poly:
            nx = (px - min_x) * scale + padding
            ny = (py - min_y) * scale + padding
            norm.append([round(nx / view_width, 4), round(ny / view_height, 4)])
        out.append(norm)
    return out, view_width, view_height


def build_region_paint_layout(
    matrix: list[list[int]],
    *,
    title: str = "Gebäude (isometrisch)",
    legacy_template: str | None = None,
) -> dict[str, Any]:
    faces = iter_visible_faces(matrix)
    polys = [_face_polygon(x, y, z, face) for x, y, z, face in faces]
    normalized, vw, vh = _normalize_polygons(polys)
    regions: list[dict[str, Any]] = []
    for (x, y, z, face), points in zip(faces, normalized, strict=True):
        rid = resolve_region_id(x, y, z, face, legacy_template=legacy_template)
        if legacy_template and rid in _LEGACY_REGION_LABELS:
            label = _LEGACY_REGION_LABELS[rid]
        else:
            label = f"{face} ({x},{y},{z})"
        regions.append(
            {
                "id": rid,
                "label": label,
                "points": points,
            }
        )
    return {
        "title": title,
        "view_width": int(vw),
        "view_height": int(vh),
        "regions": regions,
        "height_matrix": matrix,
    }


def list_legacy_template_ids() -> list[str]:
    return sorted(_LEGACY_TEMPLATE_MATRICES.keys())


def legacy_template_matrix(template_id: str) -> list[list[int]] | None:
    key = str(template_id or "").strip()
    raw = _LEGACY_TEMPLATE_MATRICES.get(key)
    if not raw:
        return None
    return normalize_height_matrix(raw)


def building_projections(matrix: list[list[int]]) -> dict[str, list[list[int]]]:
    """Front (von +y), Right (von +x), Top — abgeleitete 2D-Höhenraster."""
    rows = len(matrix)
    cols = len(matrix[0])
    max_h = max(max(r) for r in matrix)

    top: list[list[int]] = [[0 for _ in range(cols)] for _ in range(rows)]
    for y in range(rows):
        for x in range(cols):
            top[y][x] = _height_at(matrix, x, y)

    front: list[list[int]] = [[0 for _ in range(cols)] for _ in range(max_h)]
    for x in range(cols):
        col_heights = [_height_at(matrix, x, y) for y in range(rows)]
        for zi in range(max_h):
            front[zi][x] = col_heights[zi] if zi < len(col_heights) else 0

    right: list[list[int]] = [[0 for _ in range(rows)] for _ in range(max_h)]
    for y in range(rows):
        row_heights = [_height_at(matrix, x, y) for x in range(cols)]
        for zi in range(max_h):
            right[zi][y] = row_heights[zi] if zi < len(row_heights) else 0

    return {"top": top, "front": front, "right": right}


def _grids_equal(a: object, b: object) -> bool:
    if not isinstance(a, list) or not isinstance(b, list):
        return False
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b, strict=False):
        if not isinstance(ra, list) or not isinstance(rb, list) or len(ra) != len(rb):
            return False
        for ca, cb in zip(ra, rb, strict=False):
            if ca != cb:
                return False
    return True


def score_derived_projection_answer(expected_json: str, user_text: str) -> dict[str, Any]:
    import json

    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    try:
        user_grid = json.loads(user_text)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    matrix = normalize_height_matrix(user_grid)
    if matrix is None or not isinstance(expected, dict):
        return {"correct": False, "slots": []}
    derived = building_projections(matrix)
    slots: list[dict[str, Any]] = []
    all_ok = True
    for key in ("top", "front", "right"):
        exp = expected.get(key)
        if exp is None:
            continue
        ok = _grids_equal(derived.get(key), exp)
        if not ok:
            all_ok = False
        slots.append({"id": key, "correct": ok, "expected_term": key, "user_term": key})
    return {"correct": all_ok and len(slots) > 0, "slots": slots}


# --- Würfelnetz-Validator (6 Zellen, Topologie) ---

_NET_DIRS = {
    "N": (0, -1),
    "S": (0, 1),
    "E": (1, 0),
    "W": (-1, 0),
}

def _net_cells_connected(cells: list[tuple[int, int]]) -> bool:
    cell_set = set(cells)
    if len(cell_set) != len(cells):
        return False
    start = cells[0]
    seen = {start}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in _NET_DIRS.values():
            n = (cx + dx, cy + dy)
            if n in cell_set and n not in seen:
                seen.add(n)
                queue.append(n)
    return len(seen) == len(cells)


def classify_column_visibility(matrix: list[list[int]]) -> dict[str, Any]:
    """Prüft, ob jede Spalte aus der Standard-Schrägansicht lesbar ist."""
    cols = len(matrix[0])
    visible = {face_id(x, y, z, face) for x, y, z, face in iter_visible_faces(matrix)}
    columns: list[dict[str, Any]] = []
    for col in range(cols):
        heights = [int(matrix[y][col]) for y in range(len(matrix))]
        max_h = max(heights) if heights else 0
        critical_y = next((i for i, h in enumerate(heights) if h == max_h), 0)
        z_top = max(0, max_h - 1)
        readable = max_h < 1 or any(
            face_id(col, critical_y, z_top, face) in visible for face in _FACE_NAMES
        )
        columns.append(
            {
                "col": col,
                "label": chr(65 + col),
                "readable": readable,
                "max_height": max_h,
                "critical_depth_y": critical_y + 1,
            }
        )
    return {
        "all_readable": all(c["readable"] for c in columns),
        "columns": columns,
    }


Vec3 = tuple[int, int, int]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Vec3, b: Vec3) -> int:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vec3, k: int) -> Vec3:
    return (a[0] * k, a[1] * k, a[2] * k)


def _rotate90(v: Vec3, axis: Vec3) -> Vec3:
    """90°-Drehung von v um die (Einheits-)Achse axis (Rodrigues bei theta=90°, exakt in Ganzzahlen)."""
    return _add(_cross(axis, v), _scale(axis, _dot(axis, v)))


def valid_cube_net(cells: list[tuple[int, int]]) -> bool:
    """6 Netz-Zellen per Falt-Simulation prüfen — echtes Würfelnetz, nicht nur Zusammenhang/Form.

    Klappt jede Zelle in 3D auf (Normalen-Vektor + lokale Achsen, Drehung um die
    gemeinsame Kante), gültig nur wenn alle 6 Zellen auf sechs verschiedene
    Würfelflächen (Normalen) fallen — ohne Überlappung. Erkennt z. B. den
    klassischen 2×3-Rechteck-Block als ungültig, den die frühere
    Grad-Heuristik fälschlich akzeptierte.
    """
    if len(cells) != 6:
        return False
    cell_set = set(cells)
    if len(cell_set) != 6:
        return False
    if not _net_cells_connected(cells):
        return False
    start = cells[0]
    # Frame je Zelle: (Normale nach aussen, lokale Ost-Achse, lokale Süd-Achse) in 3D.
    frames: dict[tuple[int, int], tuple[Vec3, Vec3, Vec3]] = {
        start: ((0, 0, 1), (1, 0, 0), (0, 1, 0))
    }
    face_of: dict[tuple[int, int], Vec3] = {start: (0, 0, 1)}
    seen = {start}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        cx, cy = queue.popleft()
        normal, ex, ey = frames[(cx, cy)]
        for dx, dy in _NET_DIRS.values():
            n = (cx + dx, cy + dy)
            if n not in cell_set or n in seen:
                continue
            travel = _add(_scale(ex, dx), _scale(ey, dy))
            axis = _cross(normal, travel)
            new_normal = _rotate90(normal, axis)
            frames[n] = (new_normal, _rotate90(ex, axis), _rotate90(ey, axis))
            face_of[n] = new_normal
            seen.add(n)
            queue.append(n)
    if len(seen) != 6:
        return False
    return len(set(face_of.values())) == 6
