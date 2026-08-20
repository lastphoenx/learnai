"""Tests für Trainer-Export und Spaced Repetition."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import FlashcardProgress
from app.services.learn_service import _apply_spaced_schedule, _flashcard_is_due
from app.services.trainer_export_service import _bio_ranger_block, EXPORT_FORMAT


def test_bio_ranger_block_shape():
    modules = [
        {
            "title": "Test",
            "content": {
                "cards": [{"question": "Q?", "answer": "A.", "tip": "Tipp"}],
                "knowledge": [],
            },
            "quiz": {
                "questions": [
                    {
                        "q": "Quiz?",
                        "options": ["A", "B", "C", "D"],
                        "answer": 0,
                        "explanation": "Weil A",
                    }
                ]
            },
        }
    ]
    block = _bio_ranger_block(modules, title="Bruchrechnen")
    assert block["title"] == "Bruchrechnen"
    assert block["cards"][0]["q"] == "Q?"
    assert block["questions"][0]["answer"] == 0
    assert block["tips"] == ["Tipp"]


def test_spaced_schedule_known_doubles_interval():
    row = FlashcardProgress(status="known", interval_days=3)
    now = datetime.now(timezone.utc)
    _apply_spaced_schedule(row, "known", now)
    assert row.interval_days == 6
    assert row.next_review_at == now + timedelta(days=6)


def test_flashcard_is_due_when_known_and_future_review():
    now = datetime.now(timezone.utc)
    row = FlashcardProgress(
        status="known",
        next_review_at=now + timedelta(days=3),
        interval_days=3,
    )
    assert _flashcard_is_due(row, now=now) is False


def test_export_format_constant():
    assert EXPORT_FORMAT == "learnai-trainer-v1"
