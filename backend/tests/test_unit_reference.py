"""Tests für Referenz-Codes Lerneinheiten."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.unit_reference_service import (
    UnitReferenceError,
    _compute_codes_for_unit,
    _family_order,
    _family_order_from_groups,
    parse_reference_code,
)


def test_parse_reference_family_only():
    family, instance = parse_reference_code("0001")
    assert family == "0001"
    assert instance is None


def test_parse_reference_instance():
    family, instance = parse_reference_code("0001.0002")
    assert family == "0001"
    assert instance == "0002"


def test_parse_reference_invalid():
    with pytest.raises(UnitReferenceError):
        parse_reference_code("abc")


def _unit(created: datetime):
    unit = MagicMock()
    unit.id = uuid4()
    unit.created_at = created
    unit.tenant_id = uuid4()
    return unit


def test_family_order_accepts_two_tuples():
    older = _unit(datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = _unit(datetime(2026, 2, 1, tzinfo=timezone.utc))
    groups = {
        newer.id: [(newer, MagicMock())],
        older.id: [(older, MagicMock())],
    }
    order = _family_order_from_groups(groups)
    assert order[older.id] == "0001"
    assert order[newer.id] == "0002"


def test_family_order_does_not_index_missing_created_at_slot(monkeypatch):
    older = _unit(datetime(2026, 1, 1, tzinfo=timezone.utc))
    groups = {older.id: [(older, MagicMock())]}
    monkeypatch.setattr(
        "app.services.unit_reference_service._family_groups",
        lambda db, tenant_id: groups,
    )
    order = _family_order(MagicMock(), uuid4())
    assert order[older.id] == "0001"


def test_compute_codes_for_siblings_without_created_at_tuple(monkeypatch):
    root = _unit(datetime(2026, 1, 1, tzinfo=timezone.utc))
    copy = _unit(datetime(2026, 1, 2, tzinfo=timezone.utc))
    copy_record = MagicMock()
    copy_record.reconstruction_encrypted = None
    groups = {root.id: [(root, MagicMock()), (copy, copy_record)]}
    monkeypatch.setattr(
        "app.services.unit_reference_service._family_groups",
        lambda db, tenant_id: groups,
    )
    monkeypatch.setattr(
        "app.services.unit_reference_service._template_root_for_unit",
        lambda unit, recon: root.id,
    )
    family, instance, code = _compute_codes_for_unit(MagicMock(), root.tenant_id, copy, copy_record)
    assert family == "0001"
    assert instance == "0002"
    assert code == "0001.0002"
