"""Tests für Pedagogy Golden-Set Service."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.pedagogy_golden_service import (
    PedagogyGoldenError,
    list_pedagogy_golden_fixtures,
    run_pedagogy_golden_suite,
    save_pedagogy_golden_fixture,
    validate_pedagogy_fixture,
)


@pytest.fixture
def pedagogy_golden_uploads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """CI hat kein beschreibbares /app/uploads — Tests nutzen tmp_path."""
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr("app.services.pedagogy_golden_service.upload_dir", lambda: uploads)
    return uploads


@pytest.mark.usefixtures("pedagogy_golden_uploads")
def test_list_pedagogy_golden_fixtures_has_bundled():
    fixtures = list_pedagogy_golden_fixtures()
    names = {row["name"] for row in fixtures}
    assert "math_decimal" in names
    assert "deutsch_grammar" in names
    assert all(row.get("ok") for row in fixtures)


@pytest.mark.usefixtures("pedagogy_golden_uploads")
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


def test_save_custom_fixture_roundtrip(pedagogy_golden_uploads: Path):
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
    custom_dir = pedagogy_golden_uploads / "pedagogy_golden"
    on_disk = json.loads((custom_dir / "sandbox_test.json").read_text(encoding="utf-8"))
    assert on_disk["_meta"]["subject_hint"] == "Test"
