"""Validierung und deterministische Aufgaben aus Höhenmatrizen (Prio 6)."""

from __future__ import annotations

import json
from typing import Any

from app.core.camera_visibility import (
    KNOWN_CAMERAS,
    choose_informative_second_camera,
    compute_visibility_decision,
    second_camera_informative,
)
from app.core.iso_building import building_projections, normalize_height_matrix


def validate_height_matrix(matrix: object) -> list[str]:
    errors: list[str] = []
    norm = normalize_height_matrix(matrix)
    if norm is None:
        errors.append("height_matrix: ungültig oder leer")
    return errors


def _stage_camera_name(st: dict[str, Any]) -> str | None:
    if st.get("type") != "inspect":
        return None
    cam = str(st.get("camera") or "").strip().lower()
    return cam or None


def validate_spatial_sequence_config(config: dict[str, Any]) -> list[str]:
    errors = validate_height_matrix(config.get("height_matrix"))
    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("stages: mindestens eine Stufe nötig")
        return errors

    allowed_types = {"inspect", "visibility_decision", "projection_fill"}
    saw_decision = False
    saw_projection = False
    saw_primary_inspect = False

    for i, st in enumerate(stages):
        if not isinstance(st, dict):
            errors.append(f"stages[{i}]: kein Objekt")
            continue
        t = str(st.get("type") or "")
        if t not in allowed_types:
            errors.append(f"stages[{i}]: unbekannter type {t!r}")
            continue
        if t == "inspect":
            cam = _stage_camera_name(st)
            if not cam:
                errors.append(f"stages[{i}]: inspect ohne camera")
            elif cam not in KNOWN_CAMERAS:
                errors.append(f"stages[{i}]: unbekannte camera {cam!r}")
            if not st.get("hint_only") and st.get("unlock_hint") != "show_second_camera":
                saw_primary_inspect = True
        if t == "visibility_decision":
            if not saw_primary_inspect:
                errors.append("stages: visibility_decision vor erster inspect")
            saw_decision = True
        if t == "projection_fill":
            saw_projection = True
            views = st.get("views")
            if not isinstance(views, list) or not views:
                errors.append(f"stages[{i}]: projection_fill ohne views")

    if not saw_decision:
        errors.append("stages: visibility_decision fehlt")
    if not saw_projection:
        errors.append("stages: projection_fill fehlt")

    matrix = normalize_height_matrix(config.get("height_matrix"))
    if matrix is None:
        errors.append("height_matrix: ungültig")
        return errors

    first_cam = str(config.get("first_camera") or "oblique").strip().lower()
    second_cam = str(config.get("second_camera") or "front_right").strip().lower()
    for st in stages:
        if not isinstance(st, dict) or st.get("type") != "inspect":
            continue
        cam = _stage_camera_name(st)
        if not cam:
            continue
        if st.get("unlock_hint") == "show_second_camera":
            second_cam = cam
    if first_cam not in KNOWN_CAMERAS:
        errors.append(f"first_camera: unbekannt {first_cam!r}")
    if second_cam not in KNOWN_CAMERAS:
        errors.append(f"second_camera: unbekannt {second_cam!r}")

    decision = compute_visibility_decision(matrix, first_cam)
    if decision == "second_view_required" and not second_camera_informative(matrix, first_cam, second_cam):
        errors.append("second_camera: nicht informativ für diese Matrix")

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
            if st.get("hint_only"):
                continue
            cam = str(st.get("camera") or first_cam)
            if st.get("unlock_hint") == "show_second_camera":
                second_cam = cam
            elif not st.get("unlock_hint"):
                first_cam = cam
    optimal = choose_informative_second_camera(matrix, first_cam)
    if optimal != second_cam:
        warnings.append(f"second_camera: {second_cam!r} — optimal wäre {optimal!r}")
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
    second_camera: str | None = None,
) -> dict[str, Any]:
    """Deterministische Mehrstufen-Aufgabe — KI liefert nur Matrix + Text."""
    errors = validate_height_matrix(matrix)
    if errors:
        raise ValueError("; ".join(errors))
    first_camera = (first_camera or "oblique").strip().lower()
    second = (second_camera or choose_informative_second_camera(matrix, first_camera)).strip().lower()
    config: dict[str, Any] = {
        "schema_version": 1,
        "height_matrix": matrix,
        "first_camera": first_camera,
        "second_camera": second,
        "stages": [
            {"type": "inspect", "camera": first_camera, "camera_locked": True},
            {"type": "visibility_decision"},
            {
                "type": "inspect",
                "camera": second,
                "camera_locked": True,
                "hint_only": True,
                "unlock_hint": "show_second_camera",
            },
            {"type": "projection_fill", "views": ["front", "right", "top"]},
            {
                "type": "inspect",
                "camera": "top",
                "camera_locked": True,
                "hint_only": True,
                "unlock_hint": "show_top_view",
            },
        ],
        "hints": ["show_second_camera", "show_top_view", "show_solution_overlay"],
    }
    val_errors = validate_spatial_sequence_config(config)
    if val_errors:
        raise ValueError("; ".join(val_errors))
    answer = build_spatial_sequence_answer(matrix, first_camera)
    return {
        "prompt": prompt[:500],
        "hint": (hint or "")[:300] or None,
        "spatial_sequence": config,
        "answer": json.dumps(answer, ensure_ascii=False),
    }
