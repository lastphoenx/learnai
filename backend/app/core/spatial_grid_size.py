"""Rastergrösse: vorgegeben vs. selbst wählen (spatial_sequence, grid_fill)."""

from __future__ import annotations

from typing import Any

GRID_SIZE_GIVEN = "given"
GRID_SIZE_DERIVE = "derive"


def normalize_grid_size_hint(raw: object) -> str:
    value = str(raw or GRID_SIZE_GIVEN).strip().lower()
    if value in (GRID_SIZE_GIVEN, GRID_SIZE_DERIVE):
        return value
    return GRID_SIZE_GIVEN


def spatial_sequence_projection_grid_size_hint(config: dict[str, Any] | None) -> str:
    if not isinstance(config, dict):
        return GRID_SIZE_GIVEN
    for st in config.get("stages") or []:
        if not isinstance(st, dict):
            continue
        if str(st.get("type") or "") == "projection_fill":
            return normalize_grid_size_hint(st.get("grid_size_hint"))
    return normalize_grid_size_hint(config.get("grid_size_hint"))


def grid_dimensions(grid: object) -> tuple[int, int] | None:
    if not isinstance(grid, list) or not grid:
        return None
    first = grid[0]
    if not isinstance(first, list):
        return None
    return len(grid), len(first)
