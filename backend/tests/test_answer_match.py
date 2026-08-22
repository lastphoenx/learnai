from app.core.answer_match import answers_match, infer_answer_type, text_answers_match


def test_text_answers_match_variants():
    assert text_answers_match("Akkusativ|Akk.", "akkusativ")
    assert text_answers_match("Akkusativ|Akk.", "Akk.")
    assert not text_answers_match("Genitiv", "Akkusativ")


def test_infer_answer_type_numeric():
    assert infer_answer_type(question="Was ist 2+2?", answer="4") == "numeric"


def test_infer_answer_type_short_text():
    assert infer_answer_type(question="Welcher Fall?", answer="Akkusativ") == "short_text"


def test_infer_answer_type_cloze():
    assert infer_answer_type(question="Die Erde umkreist die ___", answer="Sonne") == "cloze"


def test_answers_match_numeric_tolerance():
    assert answers_match("5,2", "5.2", answer_type="numeric")
