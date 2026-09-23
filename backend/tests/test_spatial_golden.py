import json
from pathlib import Path

from app.core.camera_visibility import compute_visibility_decision
from app.core.iso_building import building_projections, normalize_height_matrix

# Fallback if helper missing - use inline load
_GOLDEN = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "spatial_golden" / "buildings.json"


def _cases():
    data = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    return data.get("cases") or []


def test_spatial_golden_projections_asymmetric():
    for case in _cases():
        if case.get("id") != "asymmetric_4x4":
            continue
        matrix = normalize_height_matrix(case["matrix"])
        assert matrix is not None
        views = building_projections(matrix)
        assert views["front"] == [
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [0, 0, 1, 0],
        ]
        vis = case.get("visibility_oblique")
        if vis:
            assert compute_visibility_decision(matrix, "oblique") == vis
        return
    raise AssertionError("asymmetric_4x4 case missing")
