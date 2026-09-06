"""Tests für Kinder-Freigabe (quality-gated)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.unit_release_service import (
    attach_learner_release_fields,
    is_released_to_learners,
    sync_learner_release_from_quality,
    unit_targets_child_learner,
)


def _child_unit(*, released: bool = False, mode: str | None = None):
    unit = MagicMock()
    unit.profile_id = uuid4()
    unit.profile = MagicMock()
    unit.profile.is_child_profile = True
    unit.learner_released_at = datetime.now(timezone.utc) if released else None
    unit.learner_release_mode = mode
    return unit


def test_unit_targets_child_learner():
    unit = _child_unit()
    assert unit_targets_child_learner(unit)
    unit.profile.is_child_profile = False
    assert not unit_targets_child_learner(unit)


def test_auto_release_on_good_quality():
    unit = _child_unit()
    sync_learner_release_from_quality(MagicMock(), unit, "good")
    assert is_released_to_learners(unit)
    assert unit.learner_release_mode == "auto"


def test_partial_clears_auto_release():
    unit = _child_unit(released=True, mode="auto")
    sync_learner_release_from_quality(MagicMock(), unit, "partial")
    assert not is_released_to_learners(unit)
    assert unit.learner_release_mode is None


def test_manual_release_survives_partial_quality():
    unit = _child_unit(released=True, mode="manual")
    sync_learner_release_from_quality(MagicMock(), unit, "partial")
    assert is_released_to_learners(unit)
    assert unit.learner_release_mode == "manual"


def test_attach_learner_release_fields_pending():
    unit = _child_unit()
    row: dict = {}
    attach_learner_release_fields(row, unit, quality_level="partial")
    assert row["learner_release"]["pending"] is True
    assert row["learner_release"]["auto_release_eligible"] is False
