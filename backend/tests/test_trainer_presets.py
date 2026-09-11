"""Tests für Trainer-Umfangs-Presets."""

import pytest

from app.core.trainer_presets import (
    DEFAULT_PRESET_ID,
    apply_trainer_preset,
    detect_trainer_preset,
    preset_options,
    trainer_presets_public,
)
from app.schemas import TrainerOptionsSchema


def test_trainer_presets_public_includes_custom_limits():
    presets = trainer_presets_public()
    ids = {p["id"] for p in presets}
    assert ids == {"posten_compact", "standard", "exam_review", "custom"}
    custom = next(p for p in presets if p["id"] == "custom")
    assert custom["limits"]["cards_min"] == 5


def test_posten_compact_options():
    opts = preset_options("posten_compact")
    assert opts["cards"] == 12
    assert opts["questions"] == 8
    assert opts["style"] == "exam"


def test_apply_trainer_preset_standard():
    opts, stored = apply_trainer_preset("standard")
    assert stored == "standard"
    assert opts["cards"] == 50


def test_apply_trainer_preset_custom_with_overrides():
    opts, stored = apply_trainer_preset(
        "custom",
        overrides={"cards": 7, "questions": 6, "style": "exam"},
    )
    assert stored == "custom"
    assert opts["cards"] == 7
    assert opts["questions"] == 6


def test_detect_trainer_preset():
    assert detect_trainer_preset(preset_options("posten_compact")) == "posten_compact"
    assert detect_trainer_preset({"cards": 7, "questions": 6, "style": "exam"}) == "custom"


def test_schema_allows_five_cards():
    parsed = TrainerOptionsSchema(cards=5, questions=5)
    assert parsed.cards == 5


def test_schema_rejects_four_cards():
    with pytest.raises(Exception):
        TrainerOptionsSchema(cards=4, questions=5)


def test_unknown_preset_raises():
    with pytest.raises(ValueError):
        apply_trainer_preset("not_a_preset")


def test_default_preset_id():
    assert DEFAULT_PRESET_ID == "standard"
