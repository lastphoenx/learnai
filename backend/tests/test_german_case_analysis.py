import pytest

from app.core.german_case_analysis import (
    analyze_span_case,
    case_from_label,
    infer_case_check_from_question,
    parse_case_check,
    verify_case_label,
)


def test_case_from_label_variants():
    assert case_from_label("Akkusativ") == "acc"
    assert case_from_label("Akk.|Akkusativ") == "acc"
    assert case_from_label("Nom.") == "nom"
    assert case_from_label("Genitiv") == "gen"
    assert case_from_label("Dativ") == "dat"


def test_parse_case_check():
    spec = parse_case_check({"sentence": "Die Erde umkreist die Sonne.", "span": "die Sonne"})
    assert spec is not None
    assert spec["span"] == "die Sonne"


def test_infer_case_check_from_question_two_quotes():
    q = 'Im Satz «Die Erde umkreist die Sonne.» — welchen Fall hat «die Sonne»?'
    spec = infer_case_check_from_question(q)
    assert spec is not None
    assert "Sonne" in spec["span"]


def test_infer_case_check_finds_word_quoted_before_sentence():
    spec = infer_case_check_from_question(
        "Welchen Kasus hat das Wort 'Buch' im Satz: 'Das ist mein Buch.'?"
    )
    assert spec is not None
    assert spec["span"] == "Buch"
    assert "Buch" in spec["sentence"]


def test_infer_case_check_blank_sentence_uses_adjacent_word():
    spec = infer_case_check_from_question(
        "Bestimme den Fall des markierten Satzglieds in dem folgenden "
        "Satz: 'Ich sehe ___ Löwen im Zoo.'"
    )
    assert spec is not None
    assert spec["span"] == "Löwen"
    assert "___" in spec["sentence"]


def test_infer_case_check_blank_at_end_is_not_whole_sentence_span():
    spec = infer_case_check_from_question(
        "Bestimme den Fall des markierten Satzglieds in dem folgenden Satz: 'Das Buch gehört ___.'"
    )
    assert spec is None


def test_whole_sentence_span_is_unavailable_not_high_confidence():
    result = analyze_span_case(
        sentence="Ich sehe ___ Löwen im Zoo.",
        span="Ich sehe ___ Löwen im Zoo.",
    )
    assert result.confidence != "high"
    assert result.confidence == "unavailable"


@pytest.mark.parametrize(
    "sentence,span,expected",
    [
        ("Der Mars trägt den Namen des römischen Kriegsgottes.", "Der Mars", "nom"),
        ("Der Mars trägt den Namen des römischen Kriegsgottes.", "den Namen", "acc"),
        ("Die Oberfläche der Sonne ist hell.", "der Sonne", "gen"),
        ("Unser Sonnensystem hat neun Planeten.", "neun Planeten", "acc"),
    ],
)
def test_analyze_span_case_with_spacy(sentence, span, expected):
    if not pytest.importorskip("spacy"):
        return
    from app.core.german_case_analysis import spacy_available

    if not spacy_available():
        pytest.skip("de_core_news_sm nicht installiert")
    result = analyze_span_case(sentence=sentence, span=span)
    assert result.confidence in {"high", "low"}
    if result.confidence == "high":
        assert result.case == expected


def test_verify_case_label_match():
    if not pytest.importorskip("spacy"):
        return
    from app.core.german_case_analysis import spacy_available

    if not spacy_available():
        pytest.skip("de_core_news_sm nicht installiert")
    match, result = verify_case_label(
        expected_answer="Nominativ",
        sentence="Der Mars trägt den Namen des Gottes.",
        span="Der Mars",
    )
    assert match is True
    assert result.case == "nom"
