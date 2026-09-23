"""Einheitlicher Raumvertrag für Höhenmatrix, Three.js und Ansichten.

Alle Module (iso_building, spatial_compact, Frontend spatialCoordinates) beziehen sich auf:

- matrix[row][col] = matrix[y][x] — Zeile 0 = **vorne** (niedriges y / niedriges gy im 3D-Modell).
- x wächst von links nach rechts (Spalte 0 = links).
- z (gz) = Würfelhöhe von unten nach oben (Wert in der Zelle = Anzahl übereinanderliegender Würfel).

Three.js (VoxelBuilding): position (gx * GAP, gz * GAP, gy * GAP) im lokalen Gebäude-Group,
nach Zentrierung: Vorne ≈ negative Welt-Z-Richtung vom Betrachter aus «von vorne».

Orthographische Lehrbuch-Ansichten (building_projections):
- top: Grundriss mit Höhenzahlen pro Feld.
- front: Blick von vorne (−y / −Z); pro Spalte x die Silhouettenhöhe max_y matrix[y][x].
- right: Blick von rechts (+x); pro Tiefe y die Silhouettenhöhe max_x matrix[y][x].
"""

from __future__ import annotations

from typing import TypedDict

FRONT_ROW: int = 0

SPATIAL_COORDINATE_SYSTEM: dict[str, str] = {
    "front_row": "0",
    "x_direction": "left-to-right",
    "y_direction": "front-to-back",
    "z_direction": "bottom-to-top",
}


class SpatialCoordinateSystem(TypedDict):
    front_row: int
    x_direction: str
    y_direction: str
    z_direction: str


def spatial_coordinate_system() -> SpatialCoordinateSystem:
    return {
        "front_row": FRONT_ROW,
        "x_direction": "left-to-right",
        "y_direction": "front-to-back",
        "z_direction": "bottom-to-top",
    }
