"""RaumWerkstatt workshop_v2 — Posten-Compact-Payload durchläuft Parser + Practice."""

import json
from pathlib import Path

from app.ai.generate_posten_compact import _parse_posten_compact_payload, posten_compact_payload_to_modules

_FIXTURE = Path(__file__).parent / "fixtures" / "posten_compact_raumwerkstatt.json"


def _payload_from_fixture() -> dict:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return _parse_posten_compact_payload(
        json.dumps(raw, ensure_ascii=False),
        card_target=12,
        question_target=8,
    )


def test_raumwerkstatt_workshop_v2_parsers():
    payload = _payload_from_fixture()

    nets = payload.get("net_build_items") or []
    assert len(nets) >= 1
    assert nets[0].get("presentation") == "workshop_v2"

    grid = payload.get("grid_fill_items") or []
    assert grid and grid[0].get("presentation") == "workshop_v2"

    paint = payload.get("building_paint_items") or []
    assert paint and paint[0].get("presentation") == "workshop_v2"

    seq = payload.get("spatial_sequence_items") or []
    assert len(seq) >= 1

    sv = payload.get("synthetic_viewpoint_items") or []
    assert sv and sv[0].get("presentation") == "workshop_v2"


def test_raumwerkstatt_payload_to_practice_net_build():
    payload = _payload_from_fixture()
    modules = posten_compact_payload_to_modules(
        payload,
        title="RaumWerkstatt",
        focus_group="math",
        source_ids=[],
    )
    practice = next(m for m in modules if m["title"] == "Aufgaben")["content"].get("practice") or []
    workshops = [p for p in practice if (p.get("net_build") or {}).get("presentation") == "workshop_v2"]
    assert workshops
