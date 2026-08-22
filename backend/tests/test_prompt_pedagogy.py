from app.ai.generate import _build_unit_prompt
from unittest.mock import MagicMock


def test_build_unit_prompt_includes_pedagogy_digest():
    unit = MagicMock()
    unit.subject = "Mathematik"
    unit.language = "de"
    unit.target_age = "11"
    unit.difficulty = 3
    digest = "Didaktik aus den hochgeladenen Quellen:\n\nLösungswege / Strategien:\n- im Kopf"
    prompt = _build_unit_prompt(
        title="Dezimalzahlen",
        brief="Orientierung am Heft",
        unit=unit,
        task="mixed",
        hint="Allgemein",
        notes="### Foto\nAufgaben …",
        pedagogy_digest=digest,
    )
    assert "Didaktik-Regeln" in prompt
    assert "im Kopf" in prompt
    assert "Material aus den Quellen" in prompt
