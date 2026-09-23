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
from app.core.iso_building import building_projections, normalize_height_matrix, top_occupancy_grid


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
            hint = st.get("grid_size_hint")
            if hint is not None and str(hint).strip():
                from app.core.spatial_grid_size import GRID_SIZE_DERIVE, GRID_SIZE_GIVEN

                if str(hint).strip().lower() not in (GRID_SIZE_GIVEN, GRID_SIZE_DERIVE):
                    errors.append(f"stages[{i}]: grid_size_hint muss given oder derive sein")

    if not saw_decision:
        errors.append("stages: visibility_decision fehlt")
    if not saw_projection and not config.get("visibility_branches"):
        errors.append("stages: projection_fill fehlt")

    branches = config.get("visibility_branches")
    if isinstance(branches, dict):
        for key in ("one_view_sufficient", "second_view_required"):
            branch = branches.get(key)
            if not isinstance(branch, dict):
                errors.append(f"visibility_branches.{key}: fehlt")
                continue
            b_stages = branch.get("stages")
            if not isinstance(b_stages, list) or not any(
                isinstance(s, dict) and s.get("type") == "projection_fill" for s in b_stages
            ):
                errors.append(f"visibility_branches.{key}: projection_fill fehlt")

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

    exp_vis = config.get("expected_visibility")
    if exp_vis is not None and str(exp_vis).strip():
        exp_s = str(exp_vis).strip()
        if exp_s not in ("one_view_sufficient", "second_view_required"):
            errors.append("expected_visibility: ungültiger Wert")
        elif exp_s != decision:
            errors.append("expected_visibility: widerspricht Sichtbarkeits-Entscheid")

    return errors


def spatial_sequence_quality_warnings(config: dict[str, Any]) -> list[str]:
    """Weiche QA-Hinweise (blockieren Generierung nicht)."""
    warnings: list[str] = []
    matrix = normalize_height_matrix(config.get("height_matrix"))
    if matrix is None:
        return warnings
    first_cam = str(config.get("first_camera") or "oblique").strip().lower()
    second_cam = str(config.get("second_camera") or "front_right").strip().lower()
    optimal = choose_informative_second_camera(matrix, first_cam)
    if optimal != second_cam:
        warnings.append(f"second_camera: {second_cam!r} — optimal wäre {optimal!r}")
    return warnings


def canonical_spatial_sequence_prompt(matrix: list[list[int]]) -> str:
    """Anzeige-Text — KI-Prompt wird beim Parsen ignoriert (wie net_build)."""
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    return (
        f"Du betrachtest ein Würfelgebäude ({rows}×{cols} Grundriss). "
        "Reicht die erste Ansicht, um alle nötigen Informationen für die drei Orthogonalansichten "
        "(Vorne, Rechts, Aufsicht) zu erkennen — oder brauchst du zwingend eine zweite Perspektive?"
    )


def build_spatial_sequence_answer(matrix: list[list[int]], first_camera: str = "oblique") -> dict[str, Any]:
    projections = building_projections(matrix)
    projections["top"] = top_occupancy_grid(matrix)
    return {
        "visibility": compute_visibility_decision(matrix, first_camera),
        "projections": projections,
    }


def build_spatial_sequence_item(
    matrix: list[list[int]],
    *,
    prompt: str,
    hint: str | None = None,
    first_camera: str = "oblique",
    second_camera: str | None = None,
    grid_size_hint: str = "given",
) -> dict[str, Any]:
    """Deterministische Mehrstufen-Aufgabe — KI liefert nur Matrix + Text."""
    from app.core.spatial_grid_size import normalize_grid_size_hint

    errors = validate_height_matrix(matrix)
    if errors:
        raise ValueError("; ".join(errors))
    first_camera = (first_camera or "oblique").strip().lower()
    second = (second_camera or choose_informative_second_camera(matrix, first_camera)).strip().lower()
    grid_hint = normalize_grid_size_hint(grid_size_hint)
    projection_fill = {
        "type": "projection_fill",
        "views": ["front", "right", "top"],
        "grid_size_hint": grid_hint,
    }
    top_hint = {
        "type": "inspect",
        "camera": "top",
        "camera_locked": True,
        "hint_only": True,
        "unlock_hint": "show_top_view",
    }
    stages_prefix = [
        {"type": "inspect", "camera": first_camera, "camera_locked": True},
        {"type": "visibility_decision"},
    ]
    branch_one = {
        "stages": [projection_fill, top_hint],
        "hints": ["show_top_view", "show_solution_overlay"],
    }
    branch_second = {
        "stages": [
            {"type": "inspect", "camera": second, "camera_locked": True},
            projection_fill,
            top_hint,
        ],
        "hints": ["show_top_view", "show_solution_overlay"],
    }
    legacy_stages = stages_prefix + branch_second["stages"]
    config: dict[str, Any] = {
        "schema_version": 1,
        "height_matrix": matrix,
        "first_camera": first_camera,
        "second_camera": second,
        "stages_prefix": stages_prefix,
        "visibility_branches": {
            "one_view_sufficient": branch_one,
            "second_view_required": branch_second,
        },
        "stages": legacy_stages,
        "hints": ["show_second_camera", "show_top_view", "show_solution_overlay"],
    }
    val_errors = validate_spatial_sequence_config(config)
    if val_errors:
        raise ValueError("; ".join(val_errors))
    answer = build_spatial_sequence_answer(matrix, first_camera)
    config["expected_visibility"] = answer["visibility"]
    display_prompt = canonical_spatial_sequence_prompt(matrix)
    return {
        "prompt": display_prompt[:500],
        "hint": (hint or "")[:300] or None,
        "spatial_sequence": config,
        "answer": json.dumps(answer, ensure_ascii=False),
    }
