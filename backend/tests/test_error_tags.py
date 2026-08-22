"""Material-first Fehler-Tags für Prüfung und Quiz."""

from app.ai.error_tags import (
    collect_error_items_from_analysis,
    infer_quiz_error_tags,
    resolve_error_pattern,
)


def test_resolve_error_pattern_label_primary():
    resolved = resolve_error_pattern(
        {"label": "Genus beim Nomen verwechselt", "tag": "", "count": 2}
    )
    assert resolved["label"] == "Genus beim Nomen verwechselt"
    assert resolved["key"].startswith("label:")
    assert resolved.get("tag") == "grammar"


def test_resolve_error_pattern_known_tag_optional():
    resolved = resolve_error_pattern(
        {"label": "Nenner bei Brüchen verwechselt", "tag": "fractions_denominator", "count": 1}
    )
    assert resolved["tag"] == "fractions_denominator"
    assert resolved["key"] == "fractions_denominator"


def test_collect_error_items_prefers_labels():
    analysis = {
        "error_patterns": [
            {"label": "Artikel falsch gewählt", "count": 2},
            {"label": "Brüche: Nenner verwechselt", "tag": "fractions_denominator", "count": 1},
        ],
        "tasks": [
            {"error_labels": ["Kommasetzung fehlt"], "error_tags": []},
        ],
    }
    items = collect_error_items_from_analysis(analysis)
    labels = [item["label"] for item in items]
    assert "Artikel falsch gewählt" in labels
    assert "Kommasetzung fehlt" in labels
    assert any(item.get("tag") == "fractions_denominator" for item in items)


def test_infer_quiz_error_tags_uses_material_labels_first():
    tags = infer_quiz_error_tags(
        question="Wann nutzt du die Ersatzprobe?",
        module_title="Nomen Genus",
        explanation="Plural hilft beim Genus",
        material_labels=["Ersatzprobe", "Wörterbuch-Strategie"],
    )
    assert tags[0].startswith("label:")
    assert "ersatzprobe" in tags[0]


def test_infer_quiz_error_tags_math_fallback():
    tags = infer_quiz_error_tags(
        question="Welcher Bruch ist größer: 1/3 oder 1/4?",
        module_title="Bruchrechnung",
    )
    assert "fractions_compare" in tags or "fractions_denominator" in tags
