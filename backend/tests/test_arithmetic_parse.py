from app.core.arithmetic_parse import parse_arithmetic_operands, try_compute_from_question


def test_parse_division_with_divisor_keyword():
    q = "Wie dividiere ich die Dezimalzahl 72 durch den Divisor 80?"
    parsed = parse_arithmetic_operands(q)
    assert parsed is not None
    op, a, b = parsed
    assert op == "div"
    assert abs(a - 72) < 1e-6
    assert abs(b - 80) < 1e-6
    assert abs(try_compute_from_question(q) - 0.9) < 1e-6


def test_method_question_not_graded_as_product():
    q = "Wie löst du die Aufgabe 14 · 0.85 mit der Zerlegungsmethode?"
    assert try_compute_from_question(q) is None
    assert parse_arithmetic_operands(q) is not None


def test_placeholder_question_with_dash_not_subtraction():
    assert parse_arithmetic_operands("Quiz 0-0?") is None
    assert try_compute_from_question("Quiz 0-0?") is None


def test_subtraction_still_requires_spaces_around_minus():
    assert parse_arithmetic_operands("Was ist 8 - 3?") is not None
    parsed = parse_arithmetic_operands("Was ist 8 - 3?")
    assert parsed is not None
    assert parsed[0] == "sub"
    assert parsed[1] == 8
    assert parsed[2] == 3
