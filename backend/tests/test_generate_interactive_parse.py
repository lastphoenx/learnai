from app.ai.errors import LlmError
from app.ai.generate_interactive import _min_accept_count, _parse_cards, _parse_questions


def test_min_accept_count_scales_for_small_targets():
    assert _min_accept_count(0) == 0
    assert _min_accept_count(1) == 1
    assert _min_accept_count(2) == 2
    assert _min_accept_count(8) == 4


def test_parse_questions_accepts_single_valid_question():
    text = """{
      "questions": [{
        "q": "Wann begann die Steinzeit?",
        "options": ["5000 v.Chr.", "50000 v.Chr.", "1500", "2020"],
        "answer": 1
      }]
    }"""
    out = _parse_questions(text, 1)
    assert len(out) == 1
    assert out[0]["q"].startswith("Wann")


def test_parse_questions_returns_empty_when_expected_zero():
    assert _parse_questions('{"questions": []}', 0) == []


def test_parse_cards_accepts_single_valid_card():
    text = """{
      "cards": [{"question": "Was ist ein Zeitstrahl?", "answer": "Eine Darstellung von Ereignissen in zeitlicher Reihenfolge."}]
    }"""
    out = _parse_cards(text, 1)
    assert len(out) == 1


def test_parse_questions_still_rejects_empty_when_one_expected():
    try:
        _parse_questions('{"questions": []}', 1)
        assert False, "expected LlmError"
    except LlmError as exc:
        assert exc.code == "thin_content"
        assert "1/1" in exc.message
