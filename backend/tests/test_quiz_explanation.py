from app.core.quiz_explanation import (
    build_worked_solution,
    enrich_quiz_explanation,
    explanation_is_weak,
    parse_arithmetic_operands,
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
    assert "3er-Reihe" in text
    assert "0,92" in text


def test_division_reihen_2468():
    text = build_worked_solution("Was ist das Ergebnis von 24.68 : 8?", 3.085)
    assert text is not None
    assert "8er-Reihe" in text
    assert "Variante 2" in text
    assert "24 ÷ 8 = 3" in text.replace(",", ".") or "24 ÷ 8 = 3" in text
    assert "680" in text or "24680" in text


def test_division_reihen_832():
    text = build_worked_solution("Was ergibt 8.32 : 4?", 2.08)
    assert text is not None
    assert "4er-Reihe" in text
    assert "8 ÷ 4 = 2" in text.replace(",", ".") or "8 ÷ 4 = 2" in text
    assert "32 ÷ 4 = 8" in text.replace(",", ".") or "32 ÷ 4 = 8" in text
    assert "2,08" in text
    assert "Variante 2" in text


def test_division_72_by_9_has_both_variants():
    text = build_worked_solution("Wie berechnest du 7.2 : 9?", 0.8)
    assert text is not None
    assert "Variante 1 (Reihen)" in text
    assert "Variante 2 (Komma verschieben)" in text
    assert "9er-Reihe" in text
    assert "72" in text
    assert "0,8" in text


def test_add_has_two_variants():
    text = build_worked_solution("Wie berechnest du die Summe von 3,2 und 4,8?", 8.0)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text


def test_parse_addition_with_plus_symbol():
    parsed = parse_arithmetic_operands("Was ist 2,5 + 1,2?")
    assert parsed is not None
    assert parsed[0] == "add"


def test_sub_has_two_variants():
    text = build_worked_solution("Was ist das Ergebnis der Subtraktion von 5,6 und 2,9?", 2.7)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text


def test_enrich_keeps_strong_multi_variant():
    explanation = (
        "Variante 1 (Reihen): 7,2 ÷ 9 aus der 9er-Reihe. "
        "Variante 2 (Komma verschieben): 72 Hundertstel ÷ 9 = 8 Hundertstel."
    )
    q = {
        "q": "Wie berechnest du 7.2 : 9?",
        "options": ["0,8", "0,08", "8", "0,72"],
        "answer": 0,
        "explanation": explanation,
        "question_type": "calculation",
    }
    assert enrich_quiz_explanation(q) == explanation


def test_enrich_keeps_method_question():
    q = {
        "q": "Welches Vorgehen passt zu 24 · 9,36?",
        "options": ["Zerlegung", "Im Kopf", "Nur schätzen", "Raten"],
        "answer": 0,
        "explanation": "Zerlegung in 20·9,36 und 4·9,36 — wie im Heft gezeigt.",
        "question_type": "method",
    }
    assert enrich_quiz_explanation(q) == q["explanation"]


def test_enrich_merges_heft_with_runtime_variant():
    q = {
        "q": "Wie berechnest du die Summe von 3,2 und 4,8?",
        "options": ["8", "7,2", "8,2", "9"],
        "answer": 0,
        "explanation": (
            "Addiere Stelle für Stelle: 3 + 4 = 7 und 0,2 + 0,8 = 1,0. Zusammen 8,0."
        ),
        "question_type": "calculation",
    }
    enriched = enrich_quiz_explanation(q)
    assert "Variante 1" in enriched
    assert "Variante 2" in enriched
