from app.ai.generate_interactive import _validate_pedagogy_method_coverage
from app.core.pedagogy_labels import (
    collect_content_blob,
    count_label_coverage,
    label_in_text,
    material_labels_from_methods,
    resolve_method_entry,
)
from app.ai.providers import LlmError
import pytest


def test_resolve_method_entry_label_primary():
    entry = resolve_method_entry({"label": "Algebraische Umformung", "when": "bei Gleichungen"})
    assert entry["label"] == "Algebraische Umformung"
    assert "id" not in entry or entry.get("id") != "other"


def test_resolve_method_entry_guesses_known_id():
    entry = resolve_method_entry({"label": "im Kopf", "when": "einfache Zahlen"})
    assert entry["label"] == "im Kopf"
    assert entry.get("id") == "mental"


def test_label_in_text_substring_and_tokens():
    assert label_in_text("im Kopf", "Julian rechnet im Kopf: 3,7 + 20,1")
    assert label_in_text("Zerlegung in Teile", "Mit Zerlegung in Teile: 15+8=23")
    assert not label_in_text("schriftlich mit Übertrag", "nur Kopfrechnen")


def test_material_labels_from_methods_dedupes():
    methods = [
        {"label": "im Kopf"},
        {"label": "Im Kopf"},
        {"id": "written", "label": "schriftlich"},
    ]
    labels = material_labels_from_methods(methods)
    assert labels == ["im Kopf", "schriftlich"]


def test_count_label_coverage_in_modules():
    labels = ["im Kopf", "schriftlich", "Rechenstrich"]
    modules = [
        {
            "content": {
                "cards": [
                    {"question": "Wann rechnest du im Kopf?", "answer": "Bei einfachen Zahlen."},
                    {"question": "Schriftlich rechnen", "answer": "Zahlen untereinander."},
                ]
            },
            "quiz": {"questions": [{"q": "Welches Vorgehen?", "options": ["im Kopf", "schriftlich", "a", "b"]}]},
        }
    ]
    blob = collect_content_blob(modules)
    assert count_label_coverage(labels, blob) >= 2


def test_validate_pedagogy_method_coverage_passes_with_labels():
    profile = {
        "methods": [
            {"label": "im Kopf"},
            {"label": "schriftlich"},
        ]
    }
    modules = [
        {
            "content": {
                "cards": [{"question": "Kopfrechnen", "answer": "im Kopf bei einfachen Aufgaben"}],
            },
            "quiz": {
                "questions": [
                    {"q": "Wann schriftlich?", "options": ["schriftlich", "a", "b", "c"], "explanation": "schriftlich"}
                ]
            },
        }
    ]
    _validate_pedagogy_method_coverage(modules, profile)


def test_validate_pedagogy_method_coverage_fails_without_labels():
    profile = {
        "methods": [
            {"label": "im Kopf"},
            {"label": "schriftlich"},
        ]
    }
    modules = [
        {
            "content": {"cards": [{"question": "Was ist 2+2?", "answer": "4"}]},
            "quiz": {"questions": [{"q": "2+2?", "options": ["4", "3", "5", "6"]}]},
        }
    ]
    with pytest.raises(LlmError):
        _validate_pedagogy_method_coverage(modules, profile)
