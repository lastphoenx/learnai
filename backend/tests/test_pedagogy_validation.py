from app.ai.providers import LlmError
import pytest

from app.core.pedagogy_validation import assess_pedagogy_coverage, enforce_label_coverage


def test_assess_pedagogy_coverage_warns_on_missing_patterns():
    profile = {
        "methods": [{"label": "Ersatzprobe"}, {"label": "Fragenmethode"}],
        "exercise_patterns": ["Fälle bestimmen"],
        "worked_examples": [{"problem": "Der Merkur", "steps": ["Nominativ"]}],
    }
    modules = [
        {
            "content": {"cards": [{"question": "Ersatzprobe?", "answer": "mit männlichem Nomen"}]},
            "quiz": {"questions": []},
        }
    ]
    result = assess_pedagogy_coverage(modules, profile)
    assert result["labels_matched"] >= 1
    assert any("exercise_pattern_missing" in w for w in result["warnings"])


def test_enforce_label_coverage_requires_two_labels():
    profile = {"methods": [{"label": "Ersatzprobe"}, {"label": "Fragenmethode"}]}
    bad = [{"content": {"cards": [{"question": "x", "answer": "y"}]}, "quiz": {"questions": []}}]
    with pytest.raises(LlmError):
        enforce_label_coverage(bad, profile)
