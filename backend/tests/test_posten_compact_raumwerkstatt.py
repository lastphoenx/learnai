"""RaumWerkstatt workshop_v2 — Posten-Compact-Payload durchläuft Parser + Practice."""

import json
from pathlib import Path

from app.ai.generate_posten_compact import _parse_posten_compact_payload, posten_compact_payload_to_modules
from app.core.spatial_compact import (
    parse_building_paint_items,
    parse_grid_fill_items,
    parse_net_build_items,
    parse_synthetic_viewpoint_items,
    parse_spatial_sequence_items,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "posten_compact_raumwerkstatt.json"


def test_raumwerkstatt_workshop_v2_parsers():
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    payload = _parse_posten_compact_payload(
        json.dumps(raw, ensure_ascii=False),
        card_target=12,
        question_target=8,
    )
    nets = parse_net_build_items(payload.get("net_build_items"))
    assert len(nets) >= 1
    assert nets[0].get("presentation") == "workshop_v2"

    grid = parse_grid_fill_items(payload.get("grid_fill_items"))
    assert grid and grid[0].get("presentation") == "workshop_v2"

    paint = parse_building_paint_items(payload.get("building_paint_items"))
    assert paint and paint[0].get("presentation") == "workshop_v2"

    seq = parse_spatial_sequence_items(payload.get("spatial_sequence_items"))
    assert len(seq) >= 1

    sv = parse_synthetic_viewpoint_items(payload.get("synthetic_viewpoint_items"))
    assert sv and sv[0].get("presentation") == "workshop_v2"


def test_raumwerkstatt_payload_to_practice_net_build():
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    payload = _parse_posten_compact_payload(
        json.dumps(raw, ensure_ascii=False),
        card_target=12,
        question_target=8,
    )
    modules = posten_compact_payload_to_modules(
        payload,
        title="RaumWerkstatt",
        focus_group="math",
        source_ids=[],
    )
    practice = next(m for m in modules if m["title"] == "Aufgaben")["content"].get("practice") or []
    workshops = [p for p in practice if (p.get("net_build") or {}).get("presentation") == "workshop_v2"]
    assert workshops
