"""Isometrische Flächen für region_paint — berechnet aus Höhenmatrizen."""

from __future__ import annotations

from typing import Any

from app.core.iso_building import build_region_paint_layout, legacy_template_matrix

_REGION_TITLES: dict[str, str] = {
    "iso_single_cube": "Würfel (isometrisch)",
    "iso_tower_2": "Zwei Würfel übereinander",
}


def get_region_template(template_id: str) -> dict[str, Any] | None:
    key = str(template_id or "").strip()
    if not key:
        return None
    matrix = legacy_template_matrix(key)
    if not matrix:
        return None
    layout = build_region_paint_layout(
        matrix,
        title=_REGION_TITLES.get(key, "Gebäude (isometrisch)"),
        legacy_template=key,
    )
    layout["template"] = key
    return layout


def list_region_template_ids() -> list[str]:
    from app.core.iso_building import list_legacy_template_ids

    return list_legacy_template_ids()
