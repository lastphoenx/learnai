"""Golden-Set-Regression für die Pedagogy-Pipeline (ohne Live-Vision)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.pedagogy_golden_service import validate_pedagogy_fixture

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "pedagogy_golden"
_GOLDEN_FILES = sorted(_FIXTURE_DIR.glob("*.json"))


@pytest.mark.parametrize("fixture_path", _GOLDEN_FILES, ids=lambda p: p.stem)
def test_pedagogy_golden_fixture(fixture_path: Path):
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    min_labels = int(meta.get("min_method_labels") or 2)
    body = {k: v for k, v in payload.items() if k != "_meta"}
    validate_pedagogy_fixture(body, min_method_labels=min_labels, fixture_name=fixture_path.name)
