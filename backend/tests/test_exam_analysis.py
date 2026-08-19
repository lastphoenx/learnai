"""Tests für Prüfungsanalyse-Bearbeitung und Transfer-Vergleich."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from app.services.exam_service import _normalize_analysis_payload, compute_transfer_comparison


def test_compute_transfer_transfer_gap():
    db = MagicMock()
    unit_id = uuid.uuid4()
    with patch("app.services.exam_service.learn_progress_for_unit") as prog:
        prog.return_value = {"quiz_correct": 18, "quiz_total": 20, "percent": 90}
        result = compute_transfer_comparison(db, unit_id=unit_id, score=12, max_score=20)
    assert result is not None
    assert result["quiz_percent"] == 90
    assert result["exam_percent"] == 60
    assert result["gap_percent"] == 30
    assert result["signal"] == "transfer_gap"


def test_compute_transfer_aligned():
    db = MagicMock()
    unit_id = uuid.uuid4()
    with patch("app.services.exam_service.learn_progress_for_unit") as prog:
        prog.return_value = {"quiz_correct": 9, "quiz_total": 10}
        result = compute_transfer_comparison(db, unit_id=unit_id, score=18, max_score=20)
    assert result is not None
    assert result["signal"] == "aligned"


def test_compute_transfer_no_unit():
    db = MagicMock()
    assert compute_transfer_comparison(db, unit_id=None, score=5, max_score=10) is None


def test_normalize_analysis_marks_edited():
    payload = {
        "summary": "Test",
        "gaps": ["Lücke 1"],
        "tasks": [
            {
                "index": 1,
                "description": "Aufgabe 1",
                "correct": False,
                "error_tags": ["fractions_denominator"],
            }
        ],
        "recommendations": ["Üben"],
    }
    out = _normalize_analysis_payload(payload, {"provider": "ollama", "model": "x"})
    assert out["edited_by_human"] is True
    assert out["summary"] == "Test"
    assert out["tasks"][0]["error_tags"] == ["fractions_denominator"]
    assert out["provider"] == "ollama"
