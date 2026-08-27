from app.core.quiz_numeric import (
    is_quiz_selection_correct,
    parse_expected_from_explanation,
    parse_quiz_numeric,
    repair_quiz_question,
    resolve_quiz_correct_index,
    resolve_quiz_expected_value,
    strip_option_label,
    try_compute_from_question,
)


def test_parse_quiz_numeric():
    assert parse_quiz_numeric("10") == 10.0
    assert parse_quiz_numeric("A) 10.0") == 10.0
    assert parse_quiz_numeric("3,8") == 3.8
    assert parse_quiz_numeric("Paris") is None


def test_strip_option_label():
    assert strip_option_label("A) 10.0") == "10.0"


def test_expected_from_explanation_and_question():
    assert parse_expected_from_explanation("Die Addition von 1.6 und 8.4 ergibt 10.0.") == 10.0
    assert try_compute_from_question("Wie lautet das Ergebnis der Addition von 1.6 und 8.4?") == 10.0


def test_resolve_wrong_stored_answer():
    q = {
        "q": "Wie lautet das Ergebnis der Addition von 1.6 und 8.4?",
        "options": ["A) 9", "A) 9.0", "A) 10", "A) 10.0"],
        "answer": 1,
        "explanation": "Die Addition von 1.6 und 8.4 ergibt 10.0.",
    }
    assert resolve_quiz_correct_index(q) == 3
    assert is_quiz_selection_correct(q, 2)
    assert is_quiz_selection_correct(q, 3)
    assert not is_quiz_selection_correct(q, 1)


def test_repair_quiz_question():
    q = {
        "q": "Addition von 1.6 und 8.4?",
        "options": ["9", "9.0", "10", "10.0"],
        "answer": 1,
        "explanation": "ergibt 10.0",
    }
    repaired = repair_quiz_question(q)
    assert repaired["answer"] == 3


def test_is_quiz_selection_correct_accepts_numeric_equivalent():
    q = {
        "q": "Was ist 3.8 + 6.2?",
        "options": ["10", "10.0", "10.1", "9.9"],
        "answer": 1,
        "explanation": "Die Addition ergibt 10.0.",
    }
    assert is_quiz_selection_correct(q, 0)
    assert is_quiz_selection_correct(q, 1)


def test_resolve_quiz_non_numeric_answer_string():
    q = {
        "q": "Welche Farbe?",
        "options": ["rot", "blau", "grün", "gelb"],
        "answer": "b",
    }
    assert resolve_quiz_correct_index(q) == -1


def test_method_question_is_not_graded_by_embedded_product():
    correct = (
        "Man zerlegt 14 in 10 und 4, dann rechnet man 10 · 0.85 = 8.5 und 4 · 0.85 = 3.4"
    )
    q = {
        "q": "Wie löst du die Aufgabe 14 · 0.85 mit der Zerlegungsmethode?",
        "options": [
            "Man zerlegt 14 in 13 und 1, dann rechnet man 13 · 0.85 und 1 · 0.85",
            correct,
            "Man zerlegt 14 in 20 und -6, dann rechnet man 20 · 0.85 und -6 · 0.85",
            "Man zerlegt 14 in 7 und 7, dann rechnet man 7 · 0.85 zweimal",
        ],
        "answer": 1,
        "explanation": correct,
    }
    assert try_compute_from_question(q["q"]) is None
    assert resolve_quiz_correct_index(q) == 1
    assert is_quiz_selection_correct(q, 1)
    assert not is_quiz_selection_correct(q, 0)
    assert not is_quiz_selection_correct(q, 2)


def test_resolve_computed_question_wins_over_wrong_ergibt():
    q = {
        "q": "Was ist 4,602 × 5?",
        "options": ["23,01", "23010", "4,602", "9,204"],
        "answer": 1,
        "explanation": "4,602 × 5 ergibt 23010.",
    }
    assert try_compute_from_question(q["q"]) is not None
    assert abs(try_compute_from_question(q["q"]) - 23.01) < 1e-6
    assert parse_expected_from_explanation(q["explanation"]) == 23010.0
    assert abs(resolve_quiz_expected_value(q) - 23.01) < 1e-6
    assert resolve_quiz_correct_index(q) == 0
    repaired = repair_quiz_question(q)
    assert repaired["answer"] == 0
