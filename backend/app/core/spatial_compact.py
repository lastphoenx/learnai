"""Räumlich-visuelle Aufgaben für posten_compact (Bildwahl, Karte, Raster)."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from app.core.focus_groups import normalize_focus_key
from app.core.iso_building import _grids_equal, projection_grids_equal

_SPATIAL_MATH_FOCUS = frozenset({"geometry", "geometry_spatial"})
_BBOX_PADDING = 0.02
_MIN_BBOX_SIZE = 0.04
GRID_COLOR_PALETTE = ("yellow", "green", "purple", "blue", "orange", "empty")
_GRID_COLOR_PALETTE = GRID_COLOR_PALETTE

REGION_PAINT_LEGACY_TEMPLATES = frozenset({"iso_single_cube", "iso_tower_2"})

SPATIAL_ANSWER_TYPES = frozenset(
    {
        "image_choice",
        "point_on_image",
        "grid_fill",
        "region_paint",
        "building_paint",
        "net_build",
        "synthetic_viewpoint",
        "spatial_sequence",
    }
)


def should_enable_spatial_compact_exercises(
    *,
    focus_group: str,
    math_focus: str | None,
    multimodal: bool,
) -> bool:
    if not multimodal:
        return False
    if (focus_group or "").strip().lower() != "math":
        return False
    key = normalize_focus_key(str(math_focus or ""))
    return key in _SPATIAL_MATH_FOCUS


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def parse_bbox(raw: object) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    try:
        x = float(raw.get("x", 0))
        y = float(raw.get("y", 0))
        w = float(raw.get("w", 0))
        h = float(raw.get("h", 0))
    except (TypeError, ValueError):
        return None
    if w < _MIN_BBOX_SIZE or h < _MIN_BBOX_SIZE:
        return None
    if x < 0 or y < 0 or x + w > 1.001 or y + h > 1.001:
        return None
    return {"x": _clamp01(x), "y": _clamp01(y), "w": _clamp01(w), "h": _clamp01(h)}


def normalize_bbox_with_padding(bbox: dict[str, float], *, padding: float = _BBOX_PADDING) -> dict[str, float]:
    x = bbox["x"] - padding
    y = bbox["y"] - padding
    w = bbox["w"] + 2 * padding
    h = bbox["h"] + 2 * padding
    if w > 1:
        x = max(0.0, x - (w - 1) / 2)
        w = 1.0
    if h > 1:
        y = max(0.0, y - (h - 1) / 2)
        h = 1.0
    x = _clamp01(x)
    y = _clamp01(y)
    w = min(w, 1.0 - x)
    h = min(h, 1.0 - y)
    if w < _MIN_BBOX_SIZE or h < _MIN_BBOX_SIZE:
        return dict(bbox)
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _resolve_source_id(source_ids: list[str], index: int) -> str | None:
    if not source_ids:
        return None
    if index < 0 or index >= len(source_ids):
        return source_ids[0]
    return source_ids[index]


def _parse_image_ref(
    raw: object,
    *,
    source_ids: list[str],
    default_index: int = 0,
) -> dict[str, Any] | None:
    if isinstance(raw, str):
        m = re.match(r"^src_page_(\d+)(?:#.*)?$", raw.strip())
        idx = int(m.group(1)) - 1 if m else default_index
        sid = _resolve_source_id(source_ids, idx)
        if not sid:
            return None
        return {"source_id": sid, "bbox": None}
    if not isinstance(raw, dict):
        return None
    try:
        idx = int(raw.get("source_index", default_index))
    except (TypeError, ValueError):
        idx = default_index
    sid = str(raw.get("source_id") or "").strip() or _resolve_source_id(source_ids, idx)
    if not sid:
        return None
    bbox = parse_bbox(raw.get("bbox") or raw)
    if bbox:
        bbox = normalize_bbox_with_padding(bbox)
    return {"source_id": sid, "bbox": bbox}


def parse_image_choice_items(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        options_raw = item.get("options")
        if not prompt or not isinstance(options_raw, list) or len(options_raw) < 2:
            continue
        options: list[dict[str, Any]] = []
        for opt in options_raw:
            if not isinstance(opt, dict):
                continue
            oid = str(opt.get("id") or "").strip().upper()
            if not oid:
                continue
            ref = opt.get("image_ref") or opt.get("bbox")
            if not isinstance(ref, (dict, str)):
                continue
            options.append({"id": oid[:8], "image_ref": ref})
        if len(options) < 2:
            continue
        answer = str(item.get("answer") or "").strip().upper()
        if answer not in {o["id"] for o in options}:
            continue
        entry: dict[str, Any] = {
            "prompt": prompt[:500],
            "hint": str(item.get("hint") or item.get("explanation") or "")[:300] or None,
            "options": options,
            "answer": answer,
        }
        if item.get("reference_image_ref"):
            entry["reference_image_ref"] = item.get("reference_image_ref")
        out.append(entry)
    return out[:6]


def parse_point_on_image_items(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        bg = item.get("background_image_ref")
        candidates_raw = item.get("candidates")
        if not prompt or bg is None or not isinstance(candidates_raw, list):
            continue
        candidates: list[dict[str, Any]] = []
        for c in candidates_raw:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id") or "").strip().upper()
            try:
                cx = float(c.get("x", -1))
                cy = float(c.get("y", -1))
            except (TypeError, ValueError):
                continue
            if not cid or cx < 0 or cy < 0 or cx > 1 or cy > 1:
                continue
            candidates.append({"id": cid[:8], "x": round(cx, 4), "y": round(cy, 4)})
        if len(candidates) < 2:
            continue
        answer = str(item.get("answer") or "").strip().upper()
        if answer not in {c["id"] for c in candidates}:
            continue
        mode = str(item.get("selection_mode") or "candidate").strip().lower()
        if mode not in ("candidate", "tap"):
            mode = "candidate"
        entry: dict[str, Any] = {
            "prompt": prompt[:500],
            "hint": str(item.get("hint") or "")[:300] or None,
            "background_image_ref": bg,
            "candidates": candidates,
            "answer": answer,
            "selection_mode": mode,
        }
        if item.get("reference_image_ref"):
            entry["reference_image_ref"] = item.get("reference_image_ref")
        out.append(entry)
    return out[:6]


def _parse_grid_cell(value: object, cell_type: str) -> Any:
    if value is None:
        return None
    if cell_type == "color":
        token = str(value).strip().lower()
        if token in ("", "null", "none", "-"):
            return None
        if token not in _GRID_COLOR_PALETTE:
            return None
        return token
    if cell_type == "number":
        if value is None:
            return None
        try:
            if isinstance(value, str) and value.strip() in ("", "-", "null"):
                return None
            num = int(float(value))
            if num < 0 or num > 99:
                return None
            return num
        except (TypeError, ValueError):
            return None
    return None


def parse_grid_fill_items(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        try:
            rows = int(item.get("rows", 0))
            cols = int(item.get("cols", 0))
        except (TypeError, ValueError):
            continue
        validation = str(item.get("validation") or "exact_match").strip().lower()
        if validation not in ("exact_match", "derived_projection"):
            validation = "exact_match"
        if validation == "derived_projection":
            if rows < 2 or rows > 12 or cols < 2 or cols > 12:
                continue
            cell_type = "number"
        elif not prompt or rows < 2 or rows > 12 or cols < 2 or cols > 12:
            continue
        cell_type = str(item.get("cell_type") or "number").strip().lower()
        if cell_type not in ("number", "color"):
            cell_type = "number"
        answer_raw = item.get("answer")
        if validation == "derived_projection":
            if not isinstance(answer_raw, dict):
                continue
            from app.core.iso_building import building_projections, normalize_height_matrix

            ref_matrix = normalize_height_matrix(answer_raw.get("height_matrix"))
            if ref_matrix is None:
                continue
            grid = building_projections(ref_matrix)
            if not all(k in grid for k in ("top", "front", "right")):
                continue
            answer_payload: Any = grid
        elif not isinstance(answer_raw, list) or len(answer_raw) != rows:
            continue
        else:
            grid: list[list[Any]] = []
            ok = True
            for row in answer_raw:
                if not isinstance(row, list) or len(row) != cols:
                    ok = False
                    break
                grid.append([_parse_grid_cell(cell, cell_type) for cell in row])
            if not ok:
                continue
            answer_payload = grid
        palette = item.get("palette")
        if cell_type == "color" and isinstance(palette, list):
            pal = [str(p).strip().lower() for p in palette if str(p).strip()]
            pal = [p for p in pal if p in _GRID_COLOR_PALETTE]
        else:
            pal = list(_GRID_COLOR_PALETTE)
        from app.core.iso_building import normalize_height_matrix

        ref_matrix = normalize_height_matrix(item.get("reference_height_matrix"))
        if validation == "derived_projection" and ref_matrix is None and isinstance(answer_raw, dict):
            ref_matrix = normalize_height_matrix(answer_raw.get("height_matrix"))
        if cell_type == "number" and ref_matrix is None:
            continue
        from app.core.spatial_grid_size import normalize_grid_size_hint

        grid_size_hint = normalize_grid_size_hint(item.get("grid_size_hint"))
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "rows": rows,
                "cols": cols,
                "cell_type": cell_type,
                "palette": pal[:6],
                "validation": validation,
                "grid_size_hint": grid_size_hint,
                "answer": answer_payload,
                "reference_height_matrix": ref_matrix,
            }
        )
    return out[:6]


def parse_region_paint_items(raw: object) -> list[dict[str, Any]]:
    from app.core.region_layouts import get_region_template

    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        template_id = str(item.get("template") or "").strip()
        tpl = get_region_template(template_id)
        if not prompt or not tpl:
            continue
        answer_raw = item.get("answer")
        if not isinstance(answer_raw, dict):
            continue
        region_ids = {str(r.get("id") or "") for r in tpl.get("regions") or [] if r.get("id")}
        parsed_answer: dict[str, str] = {}
        for rid in region_ids:
            if rid not in answer_raw:
                continue
            color = _parse_grid_cell(answer_raw.get(rid), "color")
            if color:
                parsed_answer[rid] = color
        if len(parsed_answer) < 1:
            continue
        palette_raw = item.get("palette")
        if isinstance(palette_raw, list):
            pal = [str(p).strip().lower() for p in palette_raw if str(p).strip()]
            pal = [p for p in pal if p in _GRID_COLOR_PALETTE and p != "empty"]
        else:
            pal = [c for c in _GRID_COLOR_PALETTE if c != "empty"][:5]
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "template": template_id,
                "answer": parsed_answer,
                "palette": pal[:6]
                if pal
                else [c for c in _GRID_COLOR_PALETTE if c != "empty"][:5],
            }
        )
    return out[:6]


def parse_building_paint_items(raw: object) -> list[dict[str, Any]]:
    from app.core.iso_building import build_region_paint_layout, normalize_height_matrix

    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        matrix = normalize_height_matrix(item.get("height_matrix"))
        if not prompt or not matrix:
            continue
        colored = item.get("colored_faces")
        if not isinstance(colored, dict) or not colored:
            answer_raw = item.get("answer")
            if isinstance(answer_raw, dict):
                colored = answer_raw
            else:
                continue
        parsed_answer: dict[str, str] = {}
        layout = build_region_paint_layout(matrix, title="Gebäude (isometrisch)")
        valid_ids = {str(r.get("id")) for r in layout.get("regions") or [] if r.get("id")}
        for key, value in colored.items():
            rid = str(key).strip()
            color = _parse_grid_cell(value, "color")
            if not rid or not color or (valid_ids and rid not in valid_ids):
                continue
            parsed_answer[rid] = color
        if not parsed_answer:
            continue
        palette_raw = item.get("palette")
        if isinstance(palette_raw, list):
            pal = [str(p).strip().lower() for p in palette_raw if str(p).strip()]
            pal = [p for p in pal if p in _GRID_COLOR_PALETTE and p != "empty"]
        else:
            pal = [c for c in _GRID_COLOR_PALETTE if c != "empty"][:5]
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "height_matrix": matrix,
                "answer": parsed_answer,
                "palette": pal[:6]
                if pal
                else [c for c in _GRID_COLOR_PALETTE if c != "empty"][:5],
            }
        )
    return out[:6]


_NET_BUILD_GENERIC_PROMPT = (
    "Baue ein gültiges Würfelnetz im {rows}×{cols}-Raster. "
    "Wähle genau sechs zusammenhängende Felder — es gibt viele richtige Lösungen."
)

_NET_ROW_ORDINAL_DE = ("ersten", "zweiten", "dritten", "vierten", "fünften", "sechsten")


def _longest_horizontal_run(cells: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
    by_row: dict[int, list[int]] = {}
    for c, r in cells:
        by_row.setdefault(r, []).append(c)
    best: list[tuple[int, int]] = []
    for r, cols_in_row in by_row.items():
        cols_sorted = sorted(cols_in_row)
        run_start = cols_sorted[0]
        prev = cols_sorted[0]
        run = [(run_start, r)]
        for c in cols_sorted[1:]:
            if c == prev + 1:
                run.append((c, r))
                prev = c
            else:
                if len(run) > len(best):
                    best = run
                run_start = c
                prev = c
                run = [(c, r)]
        if len(run) > len(best):
            best = run
    return best if len(best) >= 2 else None


def describe_net_build_target(rows: int, cols: int, cells: list[tuple[int, int]]) -> str:
    """Aufgabentext aus Koordinaten — keine frei halluzinierte Form-Beschreibung."""
    cell_set = set(cells)
    intro = f"Baue dieses Würfelnetz im {rows}×{cols}-Raster. "
    run = _longest_horizontal_run(cell_set)
    if run and len(run) == 4 and len(cell_set) == 6:
        r0 = run[0][1]
        c0 = run[0][0]
        for idx, (cx, _) in enumerate(run):
            up = (cx, r0 - 1)
            down = (cx, r0 + 1)
            if up in cell_set and down in cell_set and cell_set == set(run) | {up, down}:
                nth = _NET_ROW_ORDINAL_DE[idx] if idx < len(_NET_ROW_ORDINAL_DE) else f"{idx + 1}."
                return (
                    intro
                    + f"Verwende vier quadratische Flächen in einer waagerechten Reihe (Zeile {r0 + 1}) "
                    f"sowie je eine Fläche oberhalb und unterhalb der {nth} Fläche dieser Reihe."
                )
    parts: list[str] = []
    for c, r in sorted(cells, key=lambda x: (x[1], x[0])):
        parts.append(f"Zeile {r + 1}, Spalte {c + 1}")
    return intro + "Markiere genau diese sechs Felder: " + "; ".join(parts) + "."


def _parse_net_cell_list(raw: object) -> list[tuple[int, int]] | None:
    if not isinstance(raw, list) or not raw:
        return None
    cells: list[tuple[int, int]] = []
    for entry in raw:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            try:
                cells.append((int(entry[0]), int(entry[1])))
            except (TypeError, ValueError):
                return None
        else:
            return None
    return cells


def parse_net_build_items(raw: object) -> list[dict[str, Any]]:
    from app.core.iso_building import valid_cube_net

    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt_raw = str(item.get("prompt") or "").strip()
        try:
            rows = int(item.get("rows", 0))
            cols = int(item.get("cols", 0))
        except (TypeError, ValueError):
            continue
        if rows < 3 or rows > 8 or cols < 3 or cols > 8:
            continue
        given_cells = _parse_net_cell_list(item.get("given_cells"))
        target_cells = _parse_net_cell_list(item.get("target_cells"))
        answer_raw = item.get("answer")
        mode = "build"
        answer: Any = "valid_net"
        prompt = prompt_raw
        if given_cells and len(given_cells) == 6:
            mode = "validate"
            prompt = prompt_raw or "Ist dieses Würfelnetz gültig?"
            # Geometrie schlägt KI-Bool — Kreuz-Netze wurden fälschlich als «ungültig» gespeichert.
            answer = valid_cube_net(given_cells)
        else:
            if target_cells and len(target_cells) == 6 and valid_cube_net(target_cells):
                if not all(0 <= c < cols and 0 <= r < rows for c, r in target_cells):
                    continue
                prompt = describe_net_build_target(rows, cols, target_cells)
                answer = [[c, r] for c, r in target_cells]
            else:
                prompt = _NET_BUILD_GENERIC_PROMPT.format(rows=rows, cols=cols)
                answer = "valid_net"
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "rows": rows,
                "cols": cols,
                "mode": mode,
                "given_cells": [[c, r] for c, r in given_cells] if given_cells else None,
                "answer": answer,
            }
        )
    return out[:4]


_VIEWPOINT_DIRECTION_LABELS: dict[str, str] = {
    "vorne": "Vorne (unterhalb des Plans)",
    "front": "Vorne (unterhalb des Plans)",
    "süd": "Vorne (unterhalb des Plans)",
    "south": "Vorne (unterhalb des Plans)",
    "hinten": "Hinten (oberhalb des Plans)",
    "back": "Hinten (oberhalb des Plans)",
    "nord": "Hinten (oberhalb des Plans)",
    "north": "Hinten (oberhalb des Plans)",
    "rechts": "Rechts am Plan",
    "right": "Rechts am Plan",
    "ost": "Rechts am Plan",
    "east": "Rechts am Plan",
    "links": "Links am Plan",
    "left": "Links am Plan",
    "west": "Links am Plan",
    "oben": "Von oben (Aufsicht)",
    "top": "Von oben (Aufsicht)",
}

_VIEWPOINT_DIRECTION_XY: dict[str, tuple[float, float]] = {
    "vorne": (0.5, 0.9),
    "front": (0.5, 0.9),
    "süd": (0.5, 0.9),
    "south": (0.5, 0.9),
    "hinten": (0.5, 0.1),
    "back": (0.5, 0.1),
    "nord": (0.5, 0.1),
    "north": (0.5, 0.1),
    "rechts": (0.88, 0.5),
    "right": (0.88, 0.5),
    "ost": (0.88, 0.5),
    "east": (0.88, 0.5),
    "links": (0.12, 0.5),
    "left": (0.12, 0.5),
    "west": (0.12, 0.5),
    "oben": (0.5, 0.5),
    "top": (0.5, 0.5),
}

_VIEWPOINT_ID_FALLBACK: dict[str, tuple[str, float, float]] = {
    "A": ("Vorne (unterhalb des Plans)", 0.5, 0.9),
    "B": ("Rechts am Plan", 0.88, 0.5),
    "C": ("Hinten (oberhalb des Plans)", 0.5, 0.1),
    "D": ("Links am Plan", 0.12, 0.5),
}


def _resolve_viewpoint_candidate(raw: dict[str, Any]) -> dict[str, Any] | None:
    cid = str(raw.get("id") or "").strip().upper()
    if not cid:
        return None
    label = str(raw.get("label") or raw.get("name") or "").strip()
    direction = str(raw.get("direction") or raw.get("side") or "").strip().lower()
    if not label and direction:
        label = _VIEWPOINT_DIRECTION_LABELS.get(direction, "")
    if not label and cid in _VIEWPOINT_ID_FALLBACK:
        label = _VIEWPOINT_ID_FALLBACK[cid][0]
    if len(label) < 3:
        return None
    x = y = None
    try:
        if raw.get("x") is not None:
            x = round(_clamp01(float(raw["x"])), 4)
        if raw.get("y") is not None:
            y = round(_clamp01(float(raw["y"])), 4)
    except (TypeError, ValueError):
        pass
    if x is None or y is None:
        if direction and direction in _VIEWPOINT_DIRECTION_XY:
            x, y = _VIEWPOINT_DIRECTION_XY[direction]
        elif cid in _VIEWPOINT_ID_FALLBACK:
            _, fx, fy = _VIEWPOINT_ID_FALLBACK[cid]
            x, y = fx, fy
        else:
            x, y = 0.5, 0.5
    return {"id": cid[:8], "label": label[:120], "x": x, "y": y}


def parse_synthetic_viewpoint_items(raw: object) -> list[dict[str, Any]]:
    from app.core.iso_building import normalize_height_matrix

    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        matrix = normalize_height_matrix(item.get("height_matrix"))
        candidates_raw = item.get("candidates")
        if not prompt or not matrix or not isinstance(candidates_raw, list):
            continue
        candidates: list[dict[str, Any]] = []
        for c in candidates_raw:
            if not isinstance(c, dict):
                continue
            resolved = _resolve_viewpoint_candidate(c)
            if resolved:
                candidates.append(resolved)
        if len(candidates) < 2:
            continue
        answer = str(item.get("answer") or "").strip().upper()
        if answer not in {c["id"] for c in candidates}:
            continue
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "height_matrix": matrix,
                "candidates": candidates,
                "answer": answer,
            }
        )
    return out[:4]


def parse_spatial_sequence_items(raw: object) -> list[dict[str, Any]]:
    from app.core.iso_building import normalize_height_matrix
    from app.core.spatial_validator import (
        build_spatial_sequence_item,
        validate_spatial_sequence_config,
    )

    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        if not prompt:
            continue
        hint = str(item.get("hint") or "")[:300] or None
        matrix = normalize_height_matrix(item.get("height_matrix"))
        if matrix is None:
            continue
        seq_raw = item.get("spatial_sequence")
        if isinstance(seq_raw, dict) and seq_raw.get("stages"):
            config = dict(seq_raw)
            config["height_matrix"] = matrix
            config.setdefault("schema_version", 1)
            if validate_spatial_sequence_config(config):
                continue
            from app.core.spatial_validator import build_spatial_sequence_answer

            first = str(config.get("first_camera") or "oblique").strip().lower()
            for st in config.get("stages") or []:
                if (
                    isinstance(st, dict)
                    and st.get("type") == "inspect"
                    and not st.get("hint_only")
                    and not st.get("unlock_hint")
                ):
                    first = str(st.get("camera") or first).strip().lower()
                    break
            from app.core.spatial_validator import canonical_spatial_sequence_prompt

            ans_obj = build_spatial_sequence_answer(matrix, first)
            config["expected_visibility"] = ans_obj.get("visibility")
            answer = json.dumps(ans_obj, ensure_ascii=False)
            out.append(
                {
                    "prompt": canonical_spatial_sequence_prompt(matrix)[:500],
                    "hint": hint,
                    "spatial_sequence": config,
                    "answer": answer,
                }
            )
        else:
            try:
                built = build_spatial_sequence_item(
                    matrix,
                    prompt=prompt,
                    hint=hint,
                    first_camera=str(item.get("first_camera") or "oblique"),
                    second_camera=str(item.get("second_camera") or "front_right"),
                )
                out.append(built)
            except ValueError:
                continue
    return out[:3]


def score_spatial_sequence_answer(
    expected_json: str,
    user_text: str,
    *,
    grid_size_hint: str = "given",
) -> dict[str, Any]:
    from app.core.spatial_grid_size import GRID_SIZE_DERIVE, grid_dimensions, normalize_grid_size_hint

    size_mode = normalize_grid_size_hint(grid_size_hint)
    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    try:
        user = json.loads(user_text)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    if not isinstance(expected, dict) or not isinstance(user, dict):
        return {"correct": False, "slots": []}
    slots: list[dict[str, Any]] = []
    vis_ok = str(expected.get("visibility") or "") == str(user.get("visibility") or "")
    slots.append({"id": "visibility", "correct": vis_ok})
    all_ok = vis_ok
    exp_proj = expected.get("projections") if isinstance(expected.get("projections"), dict) else {}
    user_proj = user.get("projections") if isinstance(user.get("projections"), dict) else {}
    for key in ("top", "front", "right"):
        exp = exp_proj.get(key)
        if exp is None:
            continue
        user_g = user_proj.get(key)
        exp_dim = grid_dimensions(exp)
        user_dim = grid_dimensions(user_g)
        if size_mode == GRID_SIZE_DERIVE:
            size_ok = exp_dim is not None and exp_dim == user_dim
            slots.append(
                {
                    "id": f"{key}_size",
                    "correct": size_ok,
                    "expected_term": f"{exp_dim[0]}×{exp_dim[1]}" if exp_dim else None,
                    "user_term": f"{user_dim[0]}×{user_dim[1]}" if user_dim else None,
                }
            )
            if not size_ok:
                all_ok = False
                slots.append({"id": key, "correct": False})
                continue
        ok = projection_grids_equal(key, exp, user_g)
        if not ok:
            all_ok = False
        slots.append({"id": key, "correct": ok})
    return {"correct": all_ok and len(slots) > 1, "slots": slots}


_SPATIAL_PAYLOAD_LIST_KEYS = (
    "image_choice_items",
    "point_on_image_items",
    "grid_fill_items",
    "region_paint_items",
    "building_paint_items",
    "net_build_items",
    "synthetic_viewpoint_items",
    "spatial_sequence_items",
)


def spatial_payload_field_counts(payload: dict[str, Any]) -> dict[str, int]:
    return {key: len(payload.get(key) or []) for key in _SPATIAL_PAYLOAD_LIST_KEYS}


def count_raw_spatial_fields(payload: dict[str, Any]) -> int:
    return sum(spatial_payload_field_counts(payload).values())


def apply_spatial_fallback_to_payload(payload: dict[str, Any], *, goal: str = "") -> bool:
    """Standard-Raumübungen, wenn die KI keine spatial-Listen liefert (ohne Bild-Bbox)."""
    if count_raw_spatial_fields(payload) > 0:
        return False
    payload["building_paint_items"] = [
        {
            "prompt": (
                "Färbe den Würfel in der Schrägansicht: oben gelb, links grün, rechts blau. "
                "Du kannst das Gebäude drehen, um die Flächen zu finden."
            ),
            "hint": "Farbe wählen, dann die sichtbare Würfelfläche antippen.",
            "height_matrix": [[1]],
            "colored_faces": {
                "0,0,0,top": "yellow",
                "0,0,0,left": "green",
                "0,0,0,right": "blue",
            },
        }
    ]
    payload["net_build_items"] = [
        {
            "prompt": (
                "Lege ein gültiges Würfelnetz: wähle genau sechs zusammenhängende "
                "Quadrate im Raster (wie ein ausgeklapptes Würfelnetz)."
            ),
            "hint": "Ein Kreuz aus vier Quadraten plus je ein Quadrat oben und unten ist ein klassisches Netz.",
            "rows": 4,
            "cols": 4,
            "answer": "valid_net",
        }
    ]
    return True


def normalize_region_paint_user_answer(expected: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    """Gleicht Nutzer-Keys ab (z. B. 0,0,0,top → top bei Legacy-Templates)."""
    if not isinstance(expected, dict) or not isinstance(user, dict):
        return user
    exp_keys = {str(k) for k in expected}
    out: dict[str, Any] = {}
    for key, value in user.items():
        sk = str(key)
        if sk in exp_keys:
            out[sk] = value
            continue
        if "," in sk:
            face = sk.rsplit(",", 1)[-1].strip()
            if face in exp_keys:
                out[face] = value
                continue
        out[sk] = value
    return out


def count_spatial_practice_in_modules(modules: list[dict[str, Any]]) -> int:
    total = 0
    for mod in modules:
        if not isinstance(mod, dict):
            continue
        if str(mod.get("title") or "").strip() != "Aufgaben":
            continue
        content = mod.get("content") if isinstance(mod.get("content"), dict) else {}
        for item in content.get("practice") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("answer_type") or "") in SPATIAL_ANSWER_TYPES:
                total += 1
    return total


def spatial_raw_to_practice_items(
    *,
    image_choice: list[dict[str, Any]],
    point_on_image: list[dict[str, Any]],
    grid_fill: list[dict[str, Any]],
    region_paint: list[dict[str, Any]] | None = None,
    building_paint: list[dict[str, Any]] | None = None,
    net_build: list[dict[str, Any]] | None = None,
    synthetic_viewpoint: list[dict[str, Any]] | None = None,
    spatial_sequence: list[dict[str, Any]] | None = None,
    source_ids: list[str],
    quiz_source: str = "posten_compact",
) -> list[dict[str, Any]]:
    from app.core.iso_building import build_region_paint_layout, classify_column_visibility
    from app.core.region_layouts import get_region_template

    region_paint = region_paint or []
    building_paint = building_paint or []
    net_build = net_build or []
    synthetic_viewpoint = synthetic_viewpoint or []
    spatial_sequence = spatial_sequence or []
    items: list[dict[str, Any]] = []

    for raw in image_choice:
        options_out: list[dict[str, Any]] = []
        for opt in raw.get("options") or []:
            ir = opt.get("image_ref")
            bbox = parse_bbox(ir) if isinstance(ir, dict) else None
            if bbox:
                bbox = normalize_bbox_with_padding(bbox)
            ref = _parse_image_ref(ir, source_ids=source_ids)
            if not ref:
                continue
            if not bbox:
                bbox = ref.get("bbox")
            if not bbox:
                continue
            options_out.append({"id": opt["id"], "source_id": ref["source_id"], "bbox": bbox})
        if len(options_out) < 2:
            continue
        if raw["answer"] not in {o["id"] for o in options_out}:
            continue
        payload: dict[str, Any] = {
            "prompt": raw["prompt"],
            "hint": raw.get("hint"),
            "answer_type": "image_choice",
            "answer": raw["answer"],
            "image_choice": {"options": options_out},
            "source": quiz_source,
        }
        ref_img = raw.get("reference_image_ref")
        if ref_img:
            parsed_ref = _parse_image_ref(ref_img, source_ids=source_ids)
            if parsed_ref:
                payload["image_choice"]["reference"] = parsed_ref
        items.append(payload)

    for raw in point_on_image:
        bg = _parse_image_ref(raw.get("background_image_ref"), source_ids=source_ids)
        if not bg:
            continue
        if not bg.get("bbox"):
            bg["bbox"] = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
        poi: dict[str, Any] = {
            "background": bg,
            "candidates": raw["candidates"],
            "selection_mode": raw.get("selection_mode") or "candidate",
        }
        ref_img = raw.get("reference_image_ref")
        if ref_img:
            parsed_ref = _parse_image_ref(ref_img, source_ids=source_ids)
            if parsed_ref and parsed_ref.get("bbox"):
                poi["reference"] = parsed_ref
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "point_on_image",
                "answer": raw["answer"],
                "point_on_image": poi,
                "source": quiz_source,
            }
        )

    for raw in grid_fill:
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "grid_fill",
                "answer": json.dumps(raw["answer"], ensure_ascii=False),
                "grid_fill": {
                    "rows": raw["rows"],
                    "cols": raw["cols"],
                    "cell_type": raw["cell_type"],
                    "palette": raw.get("palette") or list(_GRID_COLOR_PALETTE),
                    "validation": raw.get("validation") or "exact_match",
                    "grid_size_hint": raw.get("grid_size_hint") or "given",
                    "reference_height_matrix": raw.get("reference_height_matrix"),
                },
                "source": quiz_source,
            }
        )

    for raw in region_paint:
        tpl = get_region_template(str(raw.get("template") or ""))
        if not tpl:
            continue
        answer_map = raw.get("answer") if isinstance(raw.get("answer"), dict) else {}
        if not answer_map:
            continue
        template_id = str(raw.get("template") or "")
        height_matrix = tpl.get("height_matrix")
        if template_id in REGION_PAINT_LEGACY_TEMPLATES:
            height_matrix = None
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "region_paint",
                "answer": json.dumps(answer_map, ensure_ascii=False),
                "region_paint": {
                    "template": raw["template"],
                    "title": tpl.get("title"),
                    "view_width": tpl.get("view_width", 400),
                    "view_height": tpl.get("view_height", 280),
                    "regions": tpl.get("regions") or [],
                    "height_matrix": height_matrix,
                    "palette": raw.get("palette") or list(_GRID_COLOR_PALETTE),
                },
                "source": quiz_source,
            }
        )

    for raw in building_paint:
        matrix = raw.get("height_matrix")
        if not isinstance(matrix, list):
            continue
        layout = build_region_paint_layout(matrix, title="Gebäude (isometrisch)")
        col_vis = classify_column_visibility(matrix)
        answer_map = raw.get("answer") if isinstance(raw.get("answer"), dict) else {}
        if not answer_map and isinstance(raw.get("colored_faces"), dict):
            answer_map = {
                str(k): str(v)
                for k, v in raw["colored_faces"].items()
                if k is not None and v is not None
            }
        if not answer_map:
            continue
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "building_paint",
                "answer": json.dumps(answer_map, ensure_ascii=False),
                "building_paint": {
                    "height_matrix": matrix,
                    "title": layout.get("title"),
                    "view_width": layout.get("view_width", 400),
                    "view_height": layout.get("view_height", 300),
                    "regions": layout.get("regions") or [],
                    "column_visibility": col_vis,
                    "palette": raw.get("palette") or list(_GRID_COLOR_PALETTE),
                },
                "source": quiz_source,
            }
        )

    for raw in net_build:
        mode = str(raw.get("mode") or "build")
        given = raw.get("given_cells")
        nb_config: dict[str, Any] = {"rows": raw["rows"], "cols": raw["cols"], "mode": mode}
        if isinstance(given, list) and given:
            nb_config["given_cells"] = given
        ans = raw.get("answer", "valid_net")
        if mode == "validate":
            answer_json = json.dumps(bool(ans), ensure_ascii=False)
        elif isinstance(ans, list):
            answer_json = json.dumps(ans, ensure_ascii=False)
        else:
            answer_json = json.dumps("valid_net", ensure_ascii=False)
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "net_build",
                "answer": answer_json,
                "net_build": nb_config,
                "source": quiz_source,
            }
        )

    for raw in synthetic_viewpoint:
        matrix = raw.get("height_matrix")
        if not isinstance(matrix, list):
            continue
        col_vis = classify_column_visibility(matrix)
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "synthetic_viewpoint",
                "answer": raw["answer"],
                "synthetic_viewpoint": {
                    "height_matrix": matrix,
                    "candidates": raw.get("candidates") or [],
                    "column_visibility": col_vis,
                },
                "source": quiz_source,
            }
        )

    for raw in spatial_sequence:
        config = raw.get("spatial_sequence")
        if not isinstance(config, dict):
            continue
        matrix = config.get("height_matrix")
        if not isinstance(matrix, list):
            continue
        if not config.get("expected_visibility"):
            try:
                ans = json.loads(str(raw.get("answer") or "{}"))
                if isinstance(ans, dict) and ans.get("visibility"):
                    config = {**config, "expected_visibility": ans["visibility"]}
            except json.JSONDecodeError:
                pass
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "spatial_sequence",
                "answer": raw.get("answer") or "{}",
                "spatial_sequence": config,
                "source": quiz_source,
            }
        )

    for row in items:
        if isinstance(row, dict) and str(row.get("answer_type") or "") in SPATIAL_ANSWER_TYPES:
            row.setdefault("practice_topic", "Raumgeometrie")
    return items


def grade_image_choice(expected: str, user_answer: str) -> bool:
    return str(expected or "").strip().upper() == str(user_answer or "").strip().upper()


def grade_point_on_image(expected: str, user_answer: str, *, item: dict[str, Any] | None = None) -> bool:
    exp = str(expected or "").strip().upper()
    user = str(user_answer or "").strip().upper()
    poi = (item or {}).get("point_on_image") if isinstance(item, dict) else None
    mode = str((poi or {}).get("selection_mode") or "candidate").lower()
    if mode == "candidate":
        return exp == user
    candidates = (poi or {}).get("candidates") if isinstance(poi, dict) else []
    if not isinstance(candidates, list):
        return exp == user
    target = next((c for c in candidates if str(c.get("id")).upper() == exp), None)
    if not target:
        return exp == user
    try:
        ux = float(json.loads(user_answer).get("x", -1)) if user_answer.startswith("{") else float(user)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    try:
        uy = float(json.loads(user_answer).get("y", -1)) if user_answer.startswith("{") else -1
    except (TypeError, ValueError, json.JSONDecodeError):
        uy = -1
    if uy < 0:
        return False
    tx, ty = float(target["x"]), float(target["y"])
    radius = tap_hit_radius(candidates)
    return math.hypot(ux - tx, uy - ty) <= radius


def tap_hit_radius(candidates: list[dict[str, Any]]) -> float:
    if len(candidates) < 2:
        return 0.06
    min_dist = 1.0
    for i, a in enumerate(candidates):
        for b in candidates[i + 1 :]:
            d = math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))
            if d > 0:
                min_dist = min(min_dist, d)
    radius = min_dist / 3.0
    return max(0.02, min(0.08, radius))


def score_grid_fill_answer(
    expected_json: str,
    user_text: str,
    *,
    validation: str = "exact_match",
    grid_size_hint: str = "given",
) -> dict[str, Any]:
    from app.core.spatial_grid_size import GRID_SIZE_DERIVE, grid_dimensions, normalize_grid_size_hint

    size_mode = normalize_grid_size_hint(grid_size_hint)
    if str(validation or "").strip().lower() == "derived_projection":
        from app.core.iso_building import score_derived_projection_answer

        return score_derived_projection_answer(expected_json, user_text)
    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    try:
        user = json.loads(user_text)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    if not isinstance(expected, list) or not isinstance(user, list):
        return {"correct": False, "slots": []}
    slots: list[dict[str, Any]] = []
    all_ok = True
    if size_mode == GRID_SIZE_DERIVE:
        exp_dim = grid_dimensions(expected)
        user_dim = grid_dimensions(user)
        size_ok = exp_dim is not None and exp_dim == user_dim
        slots.append(
            {
                "id": "grid_size",
                "row": -1,
                "col": -1,
                "correct": size_ok,
                "expected": f"{exp_dim[0]}×{exp_dim[1]}" if exp_dim else None,
                "user": f"{user_dim[0]}×{user_dim[1]}" if user_dim else None,
            }
        )
        if not size_ok:
            return {"correct": False, "slots": slots}
    for ri, exp_row in enumerate(expected):
        if not isinstance(exp_row, list):
            all_ok = False
            continue
        user_row = user[ri] if ri < len(user) and isinstance(user[ri], list) else []
        for ci, exp_cell in enumerate(exp_row):
            user_cell = user_row[ci] if ci < len(user_row) else None
            ok = exp_cell == user_cell
            if not ok:
                all_ok = False
            slots.append(
                {
                    "row": ri,
                    "col": ci,
                    "correct": ok,
                    "expected": exp_cell,
                    "user": user_cell,
                }
            )
    return {"correct": all_ok and len(slots) > 0, "slots": slots}


def net_build_validate_expected(net_build: dict[str, Any] | None) -> str | None:
    """Validate-Modus: Ja/Nein aus Geometrie der given_cells (Alteinheiten mit falscher KI-Bool)."""
    if not isinstance(net_build, dict) or str(net_build.get("mode") or "") != "validate":
        return None
    cells = _parse_net_cell_list(net_build.get("given_cells"))
    if not cells or len(cells) != 6:
        return None
    from app.core.iso_building import valid_cube_net

    return json.dumps(valid_cube_net(cells), ensure_ascii=False)


def score_net_build_answer(expected_json: str, user_text: str) -> dict[str, Any]:
    from app.core.iso_building import valid_cube_net

    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError:
        expected = expected_json
    if isinstance(expected, bool):
        exp_bool = expected
    elif str(expected).strip().lower() in ("valid", "invalid"):
        exp_bool = str(expected).strip().lower() == "valid"
    else:
        exp_bool = None
    if exp_bool is not None:
        try:
            user_val = json.loads(user_text)
        except json.JSONDecodeError:
            return {"correct": False, "slots": []}
        if isinstance(user_val, bool):
            return {"correct": user_val == exp_bool, "slots": []}
        return {"correct": False, "slots": []}

    try:
        user = json.loads(user_text)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    if not isinstance(user, list):
        return {"correct": False, "slots": []}
    cells: list[tuple[int, int]] = []
    for entry in user:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            return {"correct": False, "slots": []}
        try:
            cells.append((int(entry[0]), int(entry[1])))
        except (TypeError, ValueError):
            return {"correct": False, "slots": []}
    ok = valid_cube_net(cells)
    if not ok:
        return {"correct": False, "slots": []}
    if expected in ("valid_net", "valid", True):
        return {"correct": True, "slots": []}
    if isinstance(expected, list):
        exp_cells = {(int(a[0]), int(a[1])) for a in expected if isinstance(a, (list, tuple)) and len(a) == 2}
        return {"correct": set(cells) == exp_cells, "slots": []}
    return {"correct": True, "slots": []}


def score_region_paint_answer(expected_json: str, user_text: str) -> dict[str, Any]:
    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    try:
        user = json.loads(user_text)
    except json.JSONDecodeError:
        return {"correct": False, "slots": []}
    if not isinstance(expected, dict) or not isinstance(user, dict):
        return {"correct": False, "slots": []}
    user = normalize_region_paint_user_answer(expected, user)
    slots: list[dict[str, Any]] = []
    all_ok = True
    for rid, exp_color in expected.items():
        user_color = user.get(rid)
        ok = exp_color == user_color
        if not ok:
            all_ok = False
        slots.append(
            {
                "id": str(rid),
                "correct": ok,
                "expected_term": str(exp_color),
                "user_term": str(user_color) if user_color is not None else "",
            }
        )
    for rid in user:
        if rid not in expected:
            all_ok = False
    return {"correct": all_ok and len(slots) > 0, "slots": slots}


def validate_spatial_practice_item(item: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    at = str(item.get("answer_type") or "")
    if at == "image_choice":
        ic = item.get("image_choice")
        opts = ic.get("options") if isinstance(ic, dict) else []
        if not isinstance(opts, list) or len(opts) < 2:
            warnings.append("image_choice: zu wenige Optionen")
    elif at == "point_on_image":
        poi = item.get("point_on_image")
        if not isinstance(poi, dict):
            warnings.append("point_on_image: fehlende Konfiguration")
    elif at == "grid_fill":
        gf = item.get("grid_fill")
        if not isinstance(gf, dict):
            warnings.append("grid_fill: fehlende Konfiguration")
    elif at == "region_paint":
        rp = item.get("region_paint")
        if not isinstance(rp, dict):
            warnings.append("region_paint: fehlende Konfiguration")
    elif at == "building_paint":
        bp = item.get("building_paint")
        if not isinstance(bp, dict):
            warnings.append("building_paint: fehlende Konfiguration")
    elif at == "net_build":
        nb = item.get("net_build")
        if not isinstance(nb, dict):
            warnings.append("net_build: fehlende Konfiguration")
    elif at == "synthetic_viewpoint":
        sv = item.get("synthetic_viewpoint")
        if not isinstance(sv, dict):
            warnings.append("synthetic_viewpoint: fehlende Konfiguration")
    elif at == "spatial_sequence":
        from app.core.spatial_validator import validate_spatial_sequence_config

        ss = item.get("spatial_sequence")
        if not isinstance(ss, dict):
            warnings.append("spatial_sequence: fehlende Konfiguration")
        else:
            for err in validate_spatial_sequence_config(ss):
                warnings.append(f"spatial_sequence: {err}")
    return warnings
