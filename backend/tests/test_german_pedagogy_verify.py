import pytest

from app.core.german_pedagogy_verify import (
    finalize_german_pedagogy_digest,
    is_circular_case_definition,
    repair_key_terms,
    verify_german_pedagogy_digest,
    worked_example_is_coherent,
)
from app.core.german_prepositions import preposition_case_is_plausible
from app.core.pedagogy_labels import is_schema_placeholder


def test_zu_fuer_ohne_are_not_genitive():
    assert not preposition_case_is_plausible("zu", "gen")
    assert not preposition_case_is_plausible("fuer", "gen")
    assert not preposition_case_is_plausible("ohne", "gen")
    assert preposition_case_is_plausible("infolge", "gen")


def test_legacy_feld_placeholder_is_filtered():
    assert is_schema_placeholder("Legacy-Feld")


def test_circular_case_definition_detected():
    assert is_circular_case_definition(
        "Nominativ",
        "Der Kasus, bei dem das Substantiv den Nominativfall bezeichnet.",
    )


def test_repair_key_terms_uses_w_questions():
    repaired = repair_key_terms(
        [
            {
                "term": "Genitiv",
                "definition": "Der Kasus, bei dem das Substantiv den Genitivfall bezeichnet.",
            }
        ]
    )
    assert "Wessen" in repaired[0]["definition"]


def test_finalize_drops_wrong_genitive_preposition_claim():
    pedagogy = {
        "key_terms": [{"term": "Kasus", "definition": "Die Kasusformen in der deutschen Sprache."}],
        "methods": [
            {
                "label": "Genitiv nach Präposition",
                "when": "Überprüfe Kasusformen nach Präpositionen wie 'zu', 'für', 'ohne'.",
                "example": "",
            }
        ],
        "exercise_formats": ["Beschriften", "Genitiv", "Legacy-Feld"],
        "exercise_patterns": ["Nominativ", "Lesen"],
        "worked_examples": [],
        "teaching_notes": [],
    }
    repaired = finalize_german_pedagogy_digest(pedagogy, focus_group="german")
    when = repaired["methods"][0]["when"]
    assert "zu" not in when.lower()
    assert "infolge" in when.lower() or "während" in when.lower() or "Genitiv nach" in when
    assert "Genitiv" not in repaired["exercise_formats"]
    assert "Nominativ" not in repaired["exercise_patterns"]
    assert "Legacy-Feld" not in repaired["exercise_formats"]


def test_genitivattribut_relabel_without_genitive_preposition():
    pedagogy = {
        "key_terms": [],
        "methods": [
            {
                "label": "Genitiv nach Präposition",
                "when": "Beispiel aus dem Text",
                "example": "In der Trockenheit der Wüste gedeihen nur wenige Pflanzen.",
            }
        ],
        "worked_examples": [
            {
                "problem": "In der Trockenheit der Wüste gedeihen nur wenige Pflanzen.",
                "method_label": "Genitiv nach Präposition",
                "steps": [
                    "In der Trockenheit gedeihen nur wenige Pflanzen.",
                    "→ In der Trockenheit der Wüste gedeihen nur wenige Pflanzen.",
                ],
            }
        ],
        "exercise_formats": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    repaired = finalize_german_pedagogy_digest(pedagogy, focus_group="german")
    assert repaired["methods"][0]["label"] == "Genitivattribut"


def test_broken_zoo_example_is_dropped():
    assert not worked_example_is_coherent(
        {
            "problem": "Ich sehe im Zoo (Ersatzprobe)",
            "steps": ["Ich sehe im Zoo Affen. → Das Fell Affen ist braun."],
        }
    )
    pedagogy = {
        "key_terms": [],
        "methods": [],
        "worked_examples": [
            {
                "problem": "Ich sehe im Zoo (Ersatzprobe)",
                "method_label": "Ersatzprobe",
                "steps": ["Ich sehe im Zoo Affen. → Das Fell Affen ist braun."],
            },
            {
                "problem": "Das Fell des Tigers gefällt mir.",
                "method_label": "Ersatzprobe",
                "steps": ["Das Fell gefällt mir. → Das Fell des Tigers gefällt mir."],
            },
        ],
        "exercise_formats": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    repaired = finalize_german_pedagogy_digest(pedagogy, focus_group="german")
    assert len(repaired["worked_examples"]) == 1


def test_verify_reports_remaining_issues_before_repair():
    pedagogy = {
        "key_terms": [
            {
                "term": "Dativ",
                "definition": "Der Kasus, bei dem das Substantiv den Dativfall bezeichnet.",
            }
        ],
        "methods": [],
        "exercise_formats": ["Akkusativ"],
        "worked_examples": [],
    }
    warnings = verify_german_pedagogy_digest(pedagogy, focus_group="german")
    kinds = {w["kind"] for w in warnings}
    assert "case_definition" in kinds
    assert "exercise_format" in kinds
