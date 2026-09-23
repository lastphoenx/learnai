"""Golden Würfelnetze — Parität Frontend cubeNetFold / Backend cube_net_cell_face_mapping."""

import json
from pathlib import Path

from app.core.iso_building import cube_net_cell_face_mapping, valid_cube_net

_GOLDEN = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "spatial_golden" / "nets.json"


def test_spatial_golden_nets():
    data = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    for case in data.get("cases") or []:
        cells = [tuple(p) for p in case["cells"]]
        expect = bool(case.get("valid"))
        assert valid_cube_net(cells) == expect
        if expect:
            mapping = cube_net_cell_face_mapping(cells)
            assert mapping is not None
            assert len(set(mapping.values())) == 6
