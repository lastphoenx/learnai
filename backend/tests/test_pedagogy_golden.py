"""Golden-Set-Regression für die Pedagogy-Pipeline (ohne Live-Vision)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai.source_pedagogy import build_pedagogy_digest, parse_pedagogy_extraction
from app.core.pedagogy_labels import is_schema_placeholder, material_labels_from_methods

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pedagogy_golden"
_GOLDEN_FILES = sorted(_FIXTURE_DIR.glob("*.json"))


@pytest.mark.parametrize("fixture_path", _GOLDEN_FILES, ids=lambda p: p.stem)
def test_pedagogy_golden_fixture(fixture_path: Path):
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    summary, pedagogy = parse_pedagogy_extraction(json.dumps(payload))

    methods = pedagogy.get("methods") or []
    labels = material_labels_from_methods(methods)
    assert len(labels) >= 2, f"{fixture_path.name}: mindestens 2 Methoden-Labels erwartet"

    for method in methods:
        for field in ("when", "example", "label"):
            value = method.get(field) or ""
            assert not is_schema_placeholder(value), f"Schema-Platzhalter in methods.{field}: {value!r}"

    patterns = pedagogy.get("exercise_patterns") or []
    assert patterns, f"{fixture_path.name}: mindestens ein exercise_pattern erwartet"
    for pattern in patterns:
        assert not is_schema_placeholder(pattern)

    digest = build_pedagogy_digest(pedagogy)
    assert "kurzer Satz" not in digest
    assert "kurzes Beispiel mit Zahlen" not in digest
    assert labels[0] in digest or labels[0][:20] in digest

    if summary:
        assert not is_schema_placeholder(summary)
