from app.core.quiz_explanation import (
    build_worked_solution,
    enrich_quiz_explanation,
    explanation_is_weak,
)


def test_weak_explanation_detected():
    assert explanation_is_weak(
        "Das Ergebnis von 9 multipliziert mit 5.82 ist 52.38.",
        "Was ergibt sich aus der Multiplikation von 9 · 5.82?",
    )


def test_multiply_worked_solution():
    text = build_worked_solution("Was ist das Produkt von 8 · 250.1?", 2000.8)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text
    assert "2000,8" in text


def test_multiply_simple():
    text = build_worked_solution("Was ergibt sich aus der Multiplikation von 9 · 5.82?", 52.38)
    assert text is not None
    assert "Zuerst" in text
    assert "52,38" in text


def test_enrich_replaces_weak():
    q = {
        "q": "Was ergibt sich aus der Multiplikation von 9 · 5.82?",
        "options": ["52.38", "46.38", "50.38", "54.38"],
        "answer": 0,
        "explanation": "Das Ergebnis von 9 multipliziert mit 5.82 ist 52.38.",
    }
    enriched = enrich_quiz_explanation(q)
    assert "Zuerst" in enriched
    assert enriched != q["explanation"]


def test_division_colon_worked_solution():
    text = build_worked_solution("Was ist das Ergebnis von 2.76 : 3?", 0.92)
    assert text is not None
    assert "Variante 1" in text
    assert "276" in text
    assert "0,92" in text
    assert "Variante 2" in text


def test_add_has_two_variants():
    text = build_worked_solution("Wie berechnest du die Summe von 3,2 und 4,8?", 8.0)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text


def test_sub_has_two_variants():
    text = build_worked_solution("Was ist das Ergebnis der Subtraktion von 5,6 und 2,9?", 2.7)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text
