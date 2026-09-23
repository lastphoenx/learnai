"""Validierung und deterministische Aufgaben aus Höhenmatrizen (Prio 6)."""

from __future__ import annotations

import json
from typing import Any

from app.core.camera_visibility import compute_visibility_decision, second_camera_informative
from app.core.iso_building import building_projections, normalize_height_matrix


def validate_height_matrix(matrix: object) -> list[str]:
    errors: list[str] = []
    norm = normalize_height_matrix(matrix)
    if norm is None:
        errors.append("height_matrix: ungültig oder leer")
    return errors


def validate_spatial_sequence_config(config: dict[str, Any]) -> list[str]:
    errors = validate_height_matrix(config.get("height_matrix"))
    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("stages: mindestens eine Stufe nötig")
        return errors
    allowed = {"inspect", "visibility_decision", "projection_fill"}
    for i, st in enumerate(stages):
        if not isinstance(st, dict):
            errors.append(f"stages[{i}]: kein Objekt")
            continue
        t = str(st.get("type") or "")
        if t not in allowed:
            errors.append(f"stages[{i}]: unbekannter type {t!r}")
    if normalize_height_matrix(config.get("height_matrix")) is None:
        errors.append("height_matrix: ungültig")
    return errors


def spatial_sequence_quality_warnings(config: dict[str, Any]) -> list[str]:
    """Weiche QA-Hinweise (blockieren Generierung nicht)."""
    warnings: list[str] = []
    matrix = normalize_height_matrix(config.get("height_matrix"))
    if matrix is None:
        return warnings
    first_cam = "oblique"
    second_cam = "front_right"
    for st in config.get("stages") or []:
        if isinstance(st, dict) and st.get("type") == "inspect":
            first_cam = str(st.get("camera") or first_cam)
            if st.get("unlock_hint") == "show_second_camera":
                second_cam = str(st.get("camera") or second_cam)
    decision = compute_visibility_decision(matrix, first_cam)
    if decision == "second_view_required" and not second_camera_informative(matrix, first_cam, second_cam):
        warnings.append("second_camera: möglicherweise nicht informativer als erste Sicht")
    return warnings


def build_spatial_sequence_answer(matrix: list[list[int]], first_camera: str = "oblique") -> dict[str, Any]:
    return {
        "visibility": compute_visibility_decision(matrix, first_camera),
        "projections": building_projections(matrix),
    }


def build_spatial_sequence_item(
    matrix: list[list[int]],
    *,
    prompt: str,
    hint: str | None = None,
    first_camera: str = "oblique",
    second_camera: str = "front_right",
) -> dict[str, Any]:
    """Deterministische Mehrstufen-Aufgabe — KI liefert nur Matrix + Text."""
    errors = validate_height_matrix(matrix)
    if errors:
        raise ValueError("; ".join(errors))
    config: dict[str, Any] = {
        "schema_version": 1,
        "height_matrix": matrix,
        "first_camera": first_camera,
        "second_camera": second_camera,
        "stages": [
            {"type": "inspect", "camera": first_camera, "camera_locked": True},
            {"type": "visibility_decision"},
            {
                "type": "inspect",
                "camera": second_camera,
                "camera_locked": True,
                "unlock_hint": "show_second_camera",
            },
            {"type": "projection_fill", "views": ["front", "right", "top"]},
        ],
        "hints": ["show_second_camera", "show_top_view", "show_solution_overlay"],
    }
    val_errors = validate_spatial_sequence_config(config)
    answer = build_spatial_sequence_answer(matrix, first_camera)
    return {
        "prompt": prompt[:500],
        "hint": (hint or "")[:300] or None,
        "spatial_sequence": config,
        "answer": json.dumps(answer, ensure_ascii=False),
    }
