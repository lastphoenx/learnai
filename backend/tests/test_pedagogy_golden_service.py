"""Tests für Pedagogy Golden-Set Service."""

from __future__ import annotations

import pytest

from app.services.pedagogy_golden_service import (
    PedagogyGoldenError,
    list_pedagogy_golden_fixtures,
    pedagogy_golden_coverage,
    run_pedagogy_golden_suite,
    validate_pedagogy_fixture,
)


def test_list_pedagogy_golden_fixtures_has_bundled():
    fixtures = list_pedagogy_golden_fixtures()
    names = {row["name"] for row in fixtures}
    assert "math_decimal" in names
    assert "deutsch_grammar" in names
    assert "language_vocab" in names
    assert "mgu_geografie" in names
    assert all(row.get("ok") for row in fixtures)


def test_pedagogy_golden_coverage_complete():
    fixtures = list_pedagogy_golden_fixtures()
    coverage = pedagogy_golden_coverage(fixtures)
    assert coverage["complete"] is True
    assert not coverage["missing"]


def test_run_pedagogy_golden_suite_passes():
    result = run_pedagogy_golden_suite()
    assert result["total"] >= 5
    assert result["failed"] == 0
    assert result["coverage_complete"] is True
    assert result["ok"] is True
    assert "Golden Set:" in result["report"]
    assert "math_decimal" in result["report"]


def test_validate_pedagogy_fixture_rejects_too_few_methods():
    payload = {
        "summary": "Test",
        "methods": [{"label": "Eine", "when": "immer", "example": "1"}],
        "exercise_patterns": ["Muster"],
    }
    with pytest.raises(PedagogyGoldenError):
        validate_pedagogy_fixture(payload, min_method_labels=2)
