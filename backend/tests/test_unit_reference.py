"""Tests für Referenz-Codes Lerneinheiten."""

from __future__ import annotations

import pytest

from app.services.unit_reference_service import UnitReferenceError, parse_reference_code


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
