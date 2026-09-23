"""Tests für iso_building (Gebäude-Renderer, Projektionen, Netz)."""

from app.core.iso_building import (
    build_region_paint_layout,
    classify_column_visibility,
    legacy_template_matrix,
    normalize_height_matrix,
    valid_cube_net,
)
from app.core.region_layouts import get_region_template


def test_normalize_height_matrix():
    assert normalize_height_matrix([[1, 0], [2, 1]]) is not None
    assert normalize_height_matrix([]) is None
    assert normalize_height_matrix([[99]]) is None


def test_legacy_templates_via_layout():
    tpl = get_region_template("iso_single_cube")
    assert tpl is not None
    assert len(tpl["regions"]) == 3
    ids = {r["id"] for r in tpl["regions"]}
    assert ids == {"top", "left", "right"}
    polys = {r["id"]: tuple(tuple(p) for p in r["points"]) for r in tpl["regions"]}
    assert polys["top"] != polys["right"]
    assert polys["left"] != polys["right"]


def test_iso_tower_visible_iso_faces():
    tpl = get_region_template("iso_tower_2")
    assert tpl is not None
    ids = {r["id"] for r in tpl["regions"]}
    assert ids >= {"lower_left", "lower_right", "upper_top", "upper_left", "upper_right"}
    assert len(tpl["regions"]) == 5


def test_valid_cube_net_cross():
    cross = [(0, 1), (1, 1), (2, 1), (1, 0), (1, 2), (1, 3)]
    assert valid_cube_net(cross)
    assert not valid_cube_net([(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)])


def test_valid_cube_net_asymmetric_shape():
    # Vertikaler Balken (4 Zellen) mit je einem Seiten-Zapfen an der obersten Zelle —
    # kein Kreuz, prüft die Falt-Simulation an einer unsymmetrischen Form.
    net = [(0, 0), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0)]
    assert valid_cube_net(net)


def test_valid_cube_net_rejects_2x3_block():
    # Klassische Lehrbuch-Fangfrage: 2x3-Rechteck sieht wie ein Netz aus, faltet
    # sich aber mit Überlappung — frühere Grad-Heuristik akzeptierte dies fälschlich.
    block = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
    assert not valid_cube_net(block)


def test_valid_cube_net_rejects_overlapping_offset_shape():
    # Weitere Form (kein Rechteck), die Zusammenhang + Grad-Bedingung erfüllt,
    # aber beim Falten zwei Zellen auf dieselbe Würfelfläche wirft.
    shape = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
    assert not valid_cube_net(shape)


def test_classify_column_visibility_single_cube():
    matrix = legacy_template_matrix("iso_single_cube")
    assert matrix is not None
    report = classify_column_visibility(matrix)
    assert report["all_readable"]
    assert len(report["columns"]) == 1


def test_building_paint_layout_has_face_ids():
    layout = build_region_paint_layout([[1]])
    assert any(r["id"] == "0,0,0,top" for r in layout["regions"])
