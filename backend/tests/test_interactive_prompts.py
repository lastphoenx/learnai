from app.ai.prompts.interactive import build_topic_content_constraints


def test_decimal_constraints_from_title():
    rules = build_topic_content_constraints(
        title="Bruchrechnen mit Dezimalstellen",
        brief="",
        math_focus=None,
    )
    assert "Dezimalzahlen" in rules
    assert "Brüche" in rules
    assert "80%" in rules


def test_decimal_constraints_from_math_focus_label():
    rules = build_topic_content_constraints(
        title="Mathe Übung",
        brief="",
        math_focus="Dezimalzahlen & Komma",
    )
    assert "Dezimalzahlen" in rules
    assert "Brüche" not in rules


def test_no_constraints_for_generic_title():
    rules = build_topic_content_constraints(
        title="Leseverständnis",
        brief="Kurze Texte",
        math_focus=None,
    )
    assert rules == ""
