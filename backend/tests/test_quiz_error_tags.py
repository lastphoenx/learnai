"""Quiz-Fehler-Tags (Heuristik)."""

from app.ai.error_tags import aggregate_quiz_error_tags, infer_quiz_error_tags


def test_infer_fraction_tag_from_question():
    tags = infer_quiz_error_tags(
        question="Welcher Bruch ist größer: 1/3 oder 1/4?",
        module_title="Bruchrechnung",
    )
    assert "fractions_compare" in tags or "fractions_denominator" in tags


def test_aggregate_quiz_error_tags_counts():
    weaknesses = [
        {"error_tags": ["fractions_denominator", "calculation_error"]},
        {"error_tags": ["fractions_denominator"]},
    ]
    rows = aggregate_quiz_error_tags(weaknesses)
    by_key = {row["key"]: row["count"] for row in rows}
    assert by_key["fractions_denominator"] == 2
    assert by_key["calculation_error"] == 1


def test_infer_quiz_with_material_label():
    tags = infer_quiz_error_tags(
        question="Wann nutzt du die Ersatzprobe?",
        module_title="Deutsch",
        material_labels=["Ersatzprobe"],
    )
    assert tags and tags[0].startswith("label:")
