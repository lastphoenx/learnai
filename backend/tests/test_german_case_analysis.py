import pytest

from app.core.german_case_analysis import (
    analyze_span_case,
    build_case_check_spec,
    case_from_label,
    case_with_nested_attributes,
    extract_case_drill_sentence,
    format_case_card_question,
    format_case_quiz_question,
    get_case_check_spec,
    infer_case_check_from_question,
    parse_case_check,
    repair_case_check,
    spacy_available,
    verify_case_answer_with_nesting,
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


def test_extract_case_drill_sentence_fall_von():
    assert (
        extract_case_drill_sentence("Fall von: Die Ringe des Saturns glitzern.")
        == "Die Ringe des Saturns glitzern."
    )


def test_build_case_check_spec_picks_span_from_expected_case():
    if not spacy_available():
        pytest.skip("spaCy not available")
    spec = build_case_check_spec(
        sentence="Die Katze fängt die Maus.",
        expected_answer="Akkusativ",
    )
    assert spec is not None
    assert spec["span"] == "die Maus"


def test_get_case_check_spec_resolves_unmarked_fall_von():
    if not spacy_available():
        pytest.skip("spaCy not available")
    card = {
        "kind": "mental",
        "question": "Fall von: Die Katze fängt die Maus.",
        "answer": "Akkusativ",
    }
    spec = get_case_check_spec(card)
    assert spec is not None
    assert spec["span"] == "die Maus"


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


def test_whole_sentence_span_does_not_treat_sentence_start_as_full_sentence():
    from app.core.german_case_analysis import _span_covers_whole_sentence

    sentence = "Der Mars trägt den Namen des römischen Kriegsgottes."
    assert not _span_covers_whole_sentence(sentence, "Der Mars")
    assert _span_covers_whole_sentence(sentence, sentence)


def test_nominativ_phrase_span_is_not_whole_sentence():
    from app.core.german_case_analysis import _span_covers_whole_sentence

    assert not _span_covers_whole_sentence(
        "Rot ist die Farbe des Blutes.",
        "die Farbe des Blutes",
    )


def test_parse_case_check_rejects_sentence_start_as_whole_span():
    spec = parse_case_check({"sentence": "Der Mars trägt den Namen.", "span": "Der Mars"})
    assert spec is not None
    assert spec["span"] == "Der Mars"


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


def test_nested_genitive_inside_nominativ_phrase_is_detected():
    if not pytest.importorskip("spacy"):
        return
    from app.core.german_case_analysis import _load_nlp, spacy_available

    if not spacy_available():
        pytest.skip("de_core_news_sm nicht installiert")
    nlp = _load_nlp()
    result = case_with_nested_attributes(
        doc=nlp("Rot ist die Farbe des Blutes."),
        span_text="die Farbe des Blutes",
    )
    assert result["case"] == "nom"
    assert ("des Blutes", "gen") in result["nested"]


def test_answer_matching_embedded_case_is_not_flatly_wrong():
    if not pytest.importorskip("spacy"):
        return
    from app.core.german_case_analysis import spacy_available

    if not spacy_available():
        pytest.skip("de_core_news_sm nicht installiert")
    outcome = verify_case_answer_with_nesting(
        expected_answer="Nominativ",
        given_answer="Genitiv",
        sentence="Rot ist die Farbe des Blutes.",
        span="die Farbe des Blutes",
    )
    assert outcome == "teilrichtig_falsche_ebene"


def test_format_case_quiz_question_adds_bracket_mark():
    question = {
        "q": "Bestimme den Fall der markierten Wortgruppe: Das Spielzeug der Katze liegt im Flur.",
        "options": ["Dativ", "Akkusativ", "Nominativ", "Genitiv"],
        "answer": 3,
        "grammar": {
            "case_check": {
                "sentence": "Das Spielzeug der Katze liegt im Flur.",
                "span": "der Katze",
            }
        },
    }
    formatted = format_case_quiz_question(question)
    assert "<mark>der Katze</mark>" in formatted["q"]


def test_format_case_card_question_adds_mark_highlight():
    card = {
        "question": "Bestimme den Fall der markierten Wortgruppe: Der Mars leuchtet rot am Himmel.",
        "answer": "Nominativ",
        "grammar": {
            "case_check": {
                "sentence": "Der Mars leuchtet rot am Himmel.",
                "span": "Der Mars",
            }
        },
    }
    formatted = format_case_card_question(card)
    assert "<mark>Der Mars</mark>" in formatted["question"]
    assert formatted["question"].index("<mark>Der Mars</mark>") < formatted["question"].index("leuchtet")


def test_repair_case_check_fixes_whole_sentence_span():
    if not spacy_available():
        pytest.skip("spaCy not available")
    card = {
        "question": "Bestimme den Fall der markierten Wortgruppe: «Die Ringe des Saturns glitzern.»",
        "answer": "Nominativ",
        "grammar": {
            "case_check": {
                "sentence": "Die Ringe des Saturns glitzern.",
                "span": "Die Ringe des Saturns glitzern.",
            }
        },
    }
    repaired = repair_case_check(card, answer="Nominativ")
    spec = repaired.get("grammar", {}).get("case_check", {})
    assert spec.get("span") != "Die Ringe des Saturns glitzern."
    formatted = format_case_card_question(repaired)
    assert "<mark>" in formatted["question"]
