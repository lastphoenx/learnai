"""Strategie-Trends aus Quiz und Trainer."""

from __future__ import annotations

import uuid
from collections import defaultdict
from unittest.mock import MagicMock, patch

from app.services.strategy_insights_service import _record_strategy_stats, strategy_trends_for_profile


def test_record_strategy_stats_trainer_attempts():
    strategy_meta: dict[str, dict] = defaultdict(
        lambda: {
            "label": "",
            "attempts": 0,
            "correct": 0,
            "unit_ids": set(),
            "sources": set(),
        }
    )
    module = MagicMock()
    module.id = uuid.uuid4()
    module.order_index = 0
    module.title_encrypted = b"x"
    module.quiz_encrypted = b"x"

    unit = MagicMock()
    unit.id = uuid.uuid4()
    unit.modules = [module]

    stats = {
        "learn": {
            "modules": {
                str(module.id): {
                    "card_input_answers": [
                        {"method_label": "Ersatzprobe", "correct": False},
                        {"method_label": "Ersatzprobe", "correct": True},
                    ],
                    "answers": [],
                }
            }
        }
    }

    with patch("app.services.strategy_insights_service.decrypt_text_master", return_value="Modul"):
        with patch("app.services.strategy_insights_service.decrypt_json", return_value={"questions": []}):
            _record_strategy_stats(
                stats,
                unit=unit,
                material_labels=["Ersatzprobe"],
                strategy_meta=strategy_meta,
            )

    row = strategy_meta["ersatzprobe"]
    assert row["label"] == "Ersatzprobe"
    assert row["attempts"] == 2
    assert row["correct"] == 1
    assert row["sources"] == {"trainer"}


def test_strategy_trends_for_profile_empty():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    trends = strategy_trends_for_profile(db, uuid.uuid4(), uuid.uuid4())
    assert trends == []
