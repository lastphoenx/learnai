"""Räumlich-visuelle Aufgaben für posten_compact (Bildwahl, Karte, Raster)."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from app.core.focus_groups import normalize_focus_key

_SPATIAL_MATH_FOCUS = frozenset({"geometry", "geometry_spatial"})
_BBOX_PADDING = 0.02
_MIN_BBOX_SIZE = 0.04
GRID_COLOR_PALETTE = ("yellow", "green", "purple", "blue", "orange", "empty")
_GRID_COLOR_PALETTE = GRID_COLOR_PALETTE

SPATIAL_ANSWER_TYPES = frozenset(
    {
        "image_choice",
        "point_on_image",
        "grid_fill",
        "region_paint",
        "building_paint",
        "net_build",
        "synthetic_viewpoint",
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
        ref_matrix = None
        if validation != "derived_projection":
            from app.core.iso_building import normalize_height_matrix

            ref_matrix = normalize_height_matrix(item.get("reference_height_matrix"))
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "rows": rows,
                "cols": cols,
                "cell_type": cell_type,
                "palette": pal[:6],
                "validation": validation,
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


def parse_net_build_items(raw: object) -> list[dict[str, Any]]:
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
        if not prompt or rows < 3 or rows > 8 or cols < 3 or cols > 8:
            continue
        out.append(
            {
                "prompt": prompt[:500],
                "hint": str(item.get("hint") or "")[:300] or None,
                "rows": rows,
                "cols": cols,
                "answer": "valid_net",
            }
        )
    return out[:4]


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
        candidates: list[dict[str, str]] = []
        for c in candidates_raw:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id") or "").strip().upper()
            if cid:
                candidates.append({"id": cid[:8]})
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


def count_raw_spatial_fields(payload: dict[str, Any]) -> int:
    return (
        len(payload.get("image_choice_items") or [])
        + len(payload.get("point_on_image_items") or [])
        + len(payload.get("grid_fill_items") or [])
        + len(payload.get("region_paint_items") or [])
        + len(payload.get("building_paint_items") or [])
        + len(payload.get("net_build_items") or [])
        + len(payload.get("synthetic_viewpoint_items") or [])
    )


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
    source_ids: list[str],
    quiz_source: str = "posten_compact",
) -> list[dict[str, Any]]:
    from app.core.iso_building import build_region_paint_layout, classify_column_visibility
    from app.core.region_layouts import get_region_template

    region_paint = region_paint or []
    building_paint = building_paint or []
    net_build = net_build or []
    synthetic_viewpoint = synthetic_viewpoint or []
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
                    "height_matrix": tpl.get("height_matrix"),
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
        items.append(
            {
                "prompt": raw["prompt"],
                "hint": raw.get("hint"),
                "answer_type": "net_build",
                "answer": json.dumps("valid_net", ensure_ascii=False),
                "net_build": {"rows": raw["rows"], "cols": raw["cols"]},
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
) -> dict[str, Any]:
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


def score_net_build_answer(expected_json: str, user_text: str) -> dict[str, Any]:
    from app.core.iso_building import valid_cube_net

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
    try:
        expected = json.loads(expected_json)
    except json.JSONDecodeError:
        expected = expected_json
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
    return warnings
