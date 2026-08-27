"""Golden-Set-Regression für generierte Lerneinheiten (ohne Live-KI)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.task_type_golden_service import (
    TaskTypeGoldenError,
    expected_task_types,
    list_task_type_golden_fixtures,
    run_task_type_golden_suite,
    task_type_golden_coverage,
    validate_task_type_fixture,
)

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "task_type_golden"
_GOLDEN_FILES = sorted(_FIXTURE_DIR.glob("*.json"))


@pytest.mark.parametrize("fixture_path", _GOLDEN_FILES, ids=lambda p: p.stem)
def test_task_type_golden_fixture(fixture_path: Path):
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    task_type = str(meta.get("task_type") or "")
    min_cards = int(meta.get("min_cards") or 8)
    min_questions = int(meta.get("min_questions") or 8)
    body = {k: v for k, v in payload.items() if k != "_meta"}
    validate_task_type_fixture(
        body,
        task_type=task_type,
        fixture_name=fixture_path.name,
        min_cards=min_cards,
        min_questions=min_questions,
    )


def test_list_task_type_golden_fixtures_has_bundled():
    fixtures = list_task_type_golden_fixtures()
    assert fixtures
    assert all(row.get("task_type") for row in fixtures)


def test_task_type_golden_coverage_complete():
    fixtures = list_task_type_golden_fixtures()
    coverage = task_type_golden_coverage(fixtures)
    assert coverage["complete"], coverage["missing"]


def test_run_task_type_golden_suite_passes():
    result = run_task_type_golden_suite()
    assert result["ok"], result["report"]


def test_expected_task_types_count():
    assert len(expected_task_types()) == 10


def test_validate_task_type_fixture_rejects_exam_with_hints():
    question = {
        "q": "Frage?",
        "options": ["A", "B", "C", "D"],
        "answer": 0,
        "hint": "nicht erlaubt",
    }
    module = {
        "title": "Prüfung",
        "content": {"text": " ".join(f"w{i}" for i in range(120))},
        "quiz": {"questions": [dict(question) for _ in range(4)]},
    }
    modules = [dict(module) for _ in range(5)]
    with pytest.raises(TaskTypeGoldenError, match="verbotenes Feld"):
        validate_task_type_fixture({"modules": modules}, task_type="exam", fixture_name="bad")
