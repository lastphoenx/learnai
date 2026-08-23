"""Tests für Pedagogy Golden-Set Service."""

from __future__ import annotations

import json

import pytest

from app.services.pedagogy_golden_service import (
    PedagogyGoldenError,
    list_pedagogy_golden_fixtures,
    run_pedagogy_golden_suite,
    save_pedagogy_golden_fixture,
    validate_pedagogy_fixture,
)


def test_list_pedagogy_golden_fixtures_has_bundled():
    fixtures = list_pedagogy_golden_fixtures()
    names = {row["name"] for row in fixtures}
    assert "math_decimal" in names
    assert "deutsch_grammar" in names
    assert all(row.get("ok") for row in fixtures)


def test_run_pedagogy_golden_suite_passes():
    result = run_pedagogy_golden_suite()
    assert result["total"] >= 3
    assert result["failed"] == 0


def test_validate_pedagogy_fixture_rejects_too_few_methods():
    payload = {
        "summary": "Test",
        "methods": [{"label": "Eine", "when": "immer", "example": "1"}],
        "exercise_patterns": ["Muster"],
    }
    with pytest.raises(PedagogyGoldenError):
        validate_pedagogy_fixture(payload, min_method_labels=2)


def test_save_custom_fixture_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.pedagogy_golden_service._custom_dir",
        lambda: tmp_path,
    )
    payload = {
        "summary": "Sandbox",
        "methods": [
            {"label": "A", "when": "wenn", "example": "1"},
            {"label": "B", "when": "wenn", "example": "2"},
        ],
        "exercise_patterns": ["Typ"],
    }
    saved = save_pedagogy_golden_fixture("sandbox_test", payload, subject_hint="Test")
    assert saved["name"] == "sandbox_test"
    assert saved["editable"] is True
    on_disk = json.loads((tmp_path / "sandbox_test.json").read_text(encoding="utf-8"))
    assert on_disk["_meta"]["subject_hint"] == "Test"
