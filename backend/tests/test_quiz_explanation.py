import pytest

from app.core.quiz_explanation import (
    build_worked_solution,
    complete_method_explanation,
    distinct_variant_count,
    enrich_quiz_explanation,
    explanation_has_derivation,
    explanation_is_weak,
    method_explanation_incomplete,
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
    assert "Spaltenrechnung" in text
    assert "582" in text
    assert "52,38" in text
    assert "Variante 2 (Zerlegung)" in text


def test_multiply_small_decimal_has_reihe_and_notes():
    text = build_worked_solution("Berechne im Kopf: 8 · 1.5", 12.0)
    assert text is not None
    assert "Variante 1 (Kopfrechnen)" in text
    assert "8er-Reihe" in text
    assert "12" in text
    assert "Variante 2 (schriftlich)" in text
    assert "8 × 15 = 120" in text


def test_written_multiply_uses_algorithm_not_product_only():
    text = build_worked_solution("Wie löst du die Aufgabe 5 · 13.6 schriftlich?", 68.0)
    assert text is not None
    assert "Variante 1 (Spaltenrechnung)" in text
    assert "5 × 136 = 680" in text
    assert "<<spalten:" in text
    assert '"kind":"column_mul"' in text
    assert "Variante 2 (Zerlegung)" in text
    assert "5 × 13 = 65" in text
    assert "Dann 5 × 0,6 = 3" in text
    assert ", 5 ×" not in text


def test_multiply_two_digit_uses_zehner_einer_and_column():
    text = build_worked_solution("Was ergibt 24 · 9,36?", 224.64)
    assert text is not None
    assert "Variante 1 (Zerlegung Zehner/Einer)" in text
    assert "24 = 20 + 4" in text
    assert "20 × 9,36 = 187,2" in text
    assert "Dann 4 × 9,36 = 37,44" in text
    assert "187,2 + 37,44 = 224,64" in text
    assert "Variante 2 (Spaltenrechnung)" in text
    assert "24 × 936 = 22464" in text
    assert "<<spalten:" in text
    assert "3744" in text and "18720" in text
    assert "Variante 3 (Zerlegung)" in text
    assert "9,36 = 9 + 0,36" in text


def test_written_two_digit_puts_column_first():
    text = build_worked_solution("Wie löst du 24 · 9,36 schriftlich?", 224.64)
    assert text is not None
    assert text.startswith("Variante 1 (Spaltenrechnung)")
    assert "Variante 2 (Zerlegung Zehner/Einer)" in text
    assert "24 = 20 + 4" in text


def test_notes_question_puts_zerlegung_first_and_column_second():
    text = build_worked_solution("Wie löst du die Aufgabe 9 · 7.2 mit Notizen?", 64.8)
    assert text is not None
    assert text.startswith("Variante 1 (Zerlegung)")
    assert "7,2 = 7 + 0,2" in text
    assert "Variante 2 (Spaltenrechnung)" in text
    assert "<<spalten:" in text


def test_zehner_einer_skipped_when_ones_digit_zero():
    text = build_worked_solution("Was ergibt 20 · 9,36?", 187.2)
    assert text is not None
    assert "Zerlegung Zehner/Einer" not in text
    assert "schriftlich" in text or "Spaltenrechnung" in text


def test_product_only_variant_is_weak():
    expl = (
        "Variante 1 (Schriftliches Rechnen): 5 · 13.6 = 68\n"
        "Variante 2 (Notieren): 5 · 13 = 65, 5 · 0.6 = 3 → 65 + 3 = 68"
    )
    q = "Wie löst du die Aufgabe 5 · 13.6 schriftlich?"
    assert explanation_is_weak(expl, q)
    enriched = enrich_quiz_explanation(
        {
            "q": q,
            "options": ["6800", "680", "68", "6.8"],
            "answer": 2,
            "explanation": expl,
            "question_type": "calculation",
        }
    )
    assert "5 × 136 = 680" in enriched
    assert "Dann 5 × 0,6 = 3" in enriched
    assert "65, 5" not in enriched


def test_recipe_variants_are_weak():
    recipe = (
        "Variante 1 (Kopfrechnen): Du multiplizierst 8 mit 1 und dann addierst du 8 mal 0,5.\n"
        "Variante 2 (Notizen): Schreibe 1.5 als Summe von 1 und 0.5, multipliziere beide Teile mit 8 "
        "und addiere die Ergebnisse."
    )
    assert not explanation_has_derivation(recipe)
    assert explanation_is_weak(recipe, "Berechne im Kopf: 8 · 1.5")


def test_enrich_replaces_recipe_variants_for_8_times_1_5():
    recipe = (
        "Variante 1 (Kopfrechnen): Du multiplizierst 8 mit 1 und dann addierst du 8 mal 0,5.\n"
        "Variante 2 (Notizen): Schreibe 1.5 als Summe von 1 und 0.5, multipliziere beide Teile mit 8 "
        "und addiere die Ergebnisse."
    )
    q = {
        "q": "Berechne im Kopf: 8 · 1.5",
        "options": ["12", "13", "14", "15"],
        "answer": 0,
        "explanation": recipe,
        "question_type": "calculation",
    }
    enriched = enrich_quiz_explanation(q)
    assert enriched != recipe
    assert "8 × 1 = 8" in enriched or "8 × 1 = 8" in enriched.replace(",", ".")
    assert "8 × 0,5 = 4" in enriched or "8 × 0.5 = 4" in enriched.replace(",", ".")
    assert "8 + 4 = 12" in enriched or "8 + 4 = 12" in enriched.replace(",", ".")


def test_enrich_replaces_weak():
    q = {
        "q": "Was ergibt sich aus der Multiplikation von 9 · 5.82?",
        "options": ["52.38", "46.38", "50.38", "54.38"],
        "answer": 0,
        "explanation": "Das Ergebnis von 9 multipliziert mit 5.82 ist 52.38.",
    }
    enriched = enrich_quiz_explanation(q)
    assert "52,38" in enriched
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


def test_division_897_by_10_does_not_round_away_decimal():
    text = build_worked_solution("Was ist das Ergebnis von 89.7 : 10?", 8.97)
    assert text is not None
    assert "10⁻0" not in text
    assert "90 ÷ 10 = 9" not in text
    assert "8,97" in text


def test_add_has_two_variants():
    text = build_worked_solution("Wie berechnest du die Summe von 3,2 und 4,8?", 8.0)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text
    assert "Spaltenrechnung" in text
    assert "Dezimalteile" in text
    assert explanation_has_derivation(text, "Wie berechnest du die Summe von 3,2 und 4,8?")


def test_add_small_decimals_use_kopf_not_degenerate_zerlegung():
    text = build_worked_solution("Was ist 0,85 + 0,15?", 1.0)
    assert text is not None
    assert "Zerlegung" not in text
    assert "0,85" in text and "0,15" in text
    assert explanation_has_derivation(text, "Was ist 0,85 + 0,15?")


def test_parse_addition_with_plus_symbol():
    parsed = parse_arithmetic_operands("Was ist 2,5 + 1,2?")
    assert parsed is not None
    assert parsed[0] == "add"


def test_parse_difference_zwischen():
    parsed = parse_arithmetic_operands("Berechne die Differenz zwischen 600.9 und 389.7.")
    assert parsed is not None
    assert parsed[0] == "sub"
    assert abs(parsed[1] - 600.9) < 1e-6
    assert abs(parsed[2] - 389.7) < 1e-6


def test_sub_has_two_variants():
    text = build_worked_solution("Was ist das Ergebnis der Subtraktion von 5,6 und 2,9?", 2.7)
    assert text is not None
    assert "Variante 1" in text
    assert "Variante 2" in text
    assert "Spaltenrechnung" in text
    assert explanation_has_derivation(text, "Was ist das Ergebnis der Subtraktion von 5,6 und 2,9?")


def test_division_by_100_uses_two_zeros_not_one():
    text = build_worked_solution("Was ist 800 : 100?", 8.0)
    assert text is not None
    assert "2 Nullen" in text
    assert "1 Null" not in text
    assert "100er-Reihe" not in text


def test_division_960_by_40_kuerzen_not_times_table():
    text = build_worked_solution("Wie löse ich die Division 960 : 40?", 24.0)
    assert text is not None
    assert "40er-Reihe" not in text
    assert "4er-Reihe" in text
    assert "96" in text
    assert "Kürzen" in text or "Zehnerpotenz" in text


def test_division_160_by_40_cancels_to_16_over_4():
    text = build_worked_solution("Was ist das Ergebnis von 160 : 40?", 4.0)
    assert text is not None
    assert "40er-Reihe" not in text
    assert "16" in text and "4er-Reihe" in text


def test_distinct_variant_count_ignores_duplicate_bodies():
    text = (
        "Variante 1 (Schriftliche Rechnung): Zuerst die Ganzzahlen, dann die Nachkommastellen: "
        "300 - 125 = 175 und 89 - 23 = 66. Also ist das Ergebnis 175.66.\n\n"
        "Variante 2 (Kopfrechnen): Zuerst die Ganzzahlen, dann die Nachkommastellen: "
        "300 - 125 = 175 und 89 - 23 = 66. Also ist das Ergebnis 175.66."
    )
    assert distinct_variant_count(text) == 1


def test_enrich_replaces_duplicate_variant_bodies():
    q = {
        "q": "Berechne die Differenz zwischen 300.89 und 125.23.",
        "options": ["174.66", "176.66", "175.66", "177.66"],
        "answer": 2,
        "question_type": "calculation",
        "explanation": (
            "Variante 1 (Schriftliche Rechnung): Zuerst die Ganzzahlen, dann die Nachkommastellen: "
            "300 - 125 = 175 und 89 - 23 = 66. Also ist das Ergebnis 175.66.\n\n"
            "Variante 2 (Kopfrechnen): Zuerst die Ganzzahlen, dann die Nachkommastellen: "
            "300 - 125 = 175 und 89 - 23 = 66. Also ist das Ergebnis 175.66."
        ),
    }
    enriched = enrich_quiz_explanation(q)
    assert distinct_variant_count(enriched) >= 2
    assert "40er-Reihe" not in enriched


def test_enrich_method_replaces_weak_product_only():
    q = {
        "q": "Welche Methode eignet sich am besten für 2,5 · 4?",
        "options": ["Kopfrechnen", "Schriftlich", "Schätzen", "Raten"],
        "answer": 0,
        "explanation": "2,5 × 4 = 10",
        "question_type": "method",
    }
    assert explanation_is_weak(q["explanation"], q["q"])
    enriched = enrich_quiz_explanation(q)
    assert enriched != q["explanation"]
    assert "Variante 1" in enriched
    assert explanation_has_derivation(enriched, q["q"])


def test_enrich_keeps_strong_multi_variant():
    explanation = (
        "Variante 1 (Reihen): 72 ÷ 9 = 8, Komma eine Stelle → 0,8. "
        "Variante 2 (Komma verschieben): 72 ÷ 9 = 8, das sind 8 Hundertstel = 0,8."
    )
    q = {
        "q": "Wie berechnest du 7.2 : 9?",
        "options": ["0,8", "0,08", "8", "0,72"],
        "answer": 0,
        "explanation": explanation,
        "question_type": "calculation",
    }
    assert explanation_has_derivation(explanation)
    assert enrich_quiz_explanation(q) == explanation


def test_enrich_completes_method_question_with_sum():
    q = {
        "q": "Wie löst du die Aufgabe 15 · 6.28 mit der Zerlegungsmethode?",
        "options": [
            "Zerlege 15 in 10 und 5, dann berechne: 10 · 6.28 = 62.8 und 5 · 6.28 = 31.4.",
            "Zerlege 15 in 9 und 6",
        ],
        "answer": 0,
        "explanation": (
            "Die Zerlegungsmethode vereinfacht die Multiplikation, indem man eine Zahl "
            "in kleinere Teile zerlegt: Zerlege 15 in 10 und 5, dann berechne: "
            "10 · 6.28 = 62.8 und 5 · 6.28 = 31.4."
        ),
        "question_type": "method",
    }
    assert method_explanation_incomplete(q["explanation"], q["q"], q)
    enriched = enrich_quiz_explanation(q)
    assert "62,8 + 31,4 = 94,2" in enriched
    assert enriched.startswith("Die Zerlegungsmethode")


def test_enrich_completes_method_mentions_without_stated_products():
    q = {
        "q": "Welches Vorgehen passt zu 24 · 9,36?",
        "options": ["Zerlegung", "Im Kopf", "Nur schätzen", "Raten"],
        "answer": 0,
        "explanation": "Zerlegung in 20·9,36 und 4·9,36 — wie im Heft gezeigt.",
        "question_type": "method",
    }
    filled = complete_method_explanation(q["explanation"], q["q"], q)
    assert "187,2 + 37,44 = 224,64" in filled
    assert enrich_quiz_explanation(q) == filled


def test_enrich_keeps_qualitative_method_question():
    q = {
        "q": "Welches Vorgehen passt bei großen Zahlen?",
        "options": ["Schriftlich", "Raten"],
        "answer": 0,
        "explanation": "Schriftlich rechnen, weil Kopfrechnen unsicher wird.",
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


def test_card_keeps_heft_kuerzen_path():
    from app.core.solution_repair import enrich_card_answer

    original = (
        "810 : 90 = 9. Zuerst teile ich 810 durch 9, was 90 ergibt. "
        "Da der Divisor 90 ist, dividiere ich das Ergebnis noch einmal durch 10: 90 : 10 = 9."
    )
    shown = enrich_card_answer(
        {
            "kind": "merk",
            "question": "Wie löse ich die Division 810 : 90?",
            "answer": original,
        }
    )
    assert "810 durch 9" in shown
    assert "90 : 10 = 9" in shown or "90 ÷ 10" in shown
    assert "90er-Reihe" not in shown


def test_leading_result_line_is_not_weak():
    question = "Wie löse ich die Division 810 : 90?"
    with_lead = (
        "810 : 90 = 9. Variante 1 (Aus dem Heft): Zuerst teile ich 810 durch 9, was 90 ergibt. "
        "Da der Divisor 90 ist, dividiere ich das Ergebnis noch einmal durch 10: 90 : 10 = 9."
    )
    without_lead = (
        "Variante 1 (Aus dem Heft): Zuerst teile ich 810 durch 9, was 90 ergibt. "
        "Da der Divisor 90 ist, dividiere ich das Ergebnis noch einmal durch 10: 90 : 10 = 9."
    )
    assert explanation_has_derivation(without_lead, question)
    assert not explanation_is_weak(without_lead, question)
    assert explanation_has_derivation(with_lead, question)
    assert not explanation_is_weak(with_lead, question)


def test_card_keeps_heft_when_result_precedes_variante():
    from app.core.solution_repair import enrich_card_answer

    original = (
        "810 : 90 = 9. Variante 1 (Aus dem Heft): Zuerst teile ich 810 durch 9, was 90 ergibt. "
        "Da der Divisor 90 ist, dividiere ich das Ergebnis noch einmal durch 10: 90 : 10 = 9."
    )
    shown = enrich_card_answer(
        {
            "kind": "merk",
            "question": "Wie löse ich die Division 810 : 90?",
            "answer": original,
        }
    )
    assert "810 durch 9" in shown
    assert "90 : 10 = 9" in shown
    assert shown.lower().count("variante 1") == 1
    assert "Aus dem Heft" in shown


def test_merge_does_not_double_variante_1_after_result_line():
    from app.core.quiz_explanation import merge_worked_variants

    primary = (
        "810 : 90 = 9. Variante 1 (Aus dem Heft): Zuerst teile ich 810 durch 9, was 90 ergibt. "
        "Da der Divisor 90 ist, dividiere ich das Ergebnis noch einmal durch 10: 90 : 10 = 9."
    )
    question = "Wie löse ich die Division 810 : 90?"
    worked = build_worked_solution(question, 9.0)
    assert worked
    merged = merge_worked_variants(primary, worked, question=question)
    assert merged.lower().count("variante 1") == 1
    assert "Aus dem Heft" in merged
    assert "810 durch 9" in merged


def test_knowledge_scrubs_reihe_phrase_not_just_label():
    from app.core.solution_repair import enrich_knowledge_text

    shown = enrich_knowledge_text(
        "Bei solchen Aufgaben rechnet man oft aus der 90er-Reihe: 810:90=9."
    )
    assert "90er-Reihe" not in shown
    assert "aus der" not in shown.lower()


def test_card_replaces_invalid_times_table():
    from app.core.solution_repair import enrich_card_answer

    shown = enrich_card_answer(
        {
            "kind": "merk",
            "question": "Wie löse ich die Division 960 : 40?",
            "answer": "Variante 1 (Reihen): 960 ÷ 40. Aus der 40er-Reihe: 960 ÷ 40 = 24.",
        }
    )
    assert "40er-Reihe" not in shown
    assert "4er-Reihe" in shown
    assert "Kürzen" in shown or "96" in shown


def test_input_card_keeps_short_answer():
    from app.core.solution_repair import enrich_card_answer

    shown = enrich_card_answer(
        {
            "kind": "input",
            "question": "Was ist das Ergebnis von 810 : 90?",
            "answer": "9",
        }
    )
    assert shown == "9"


def test_knowledge_drops_false_equation():
    from app.core.solution_repair import enrich_knowledge_text

    shown = enrich_knowledge_text("Merke: 4 + 6 = 11. Addieren heisst zusammenzählen.")
    assert "4 + 6 = 11" not in shown
    assert "zusammenzählen" in shown


def test_knowledge_scrubs_invalid_reihe():
    from app.core.solution_repair import enrich_knowledge_text

    shown = enrich_knowledge_text("600 ÷ 100. Aus der 100er-Reihe: 600 ÷ 100 = 6.")
    assert "100er-Reihe" not in shown


def test_repair_generated_module_fixes_quiz_and_card():
    from app.core.solution_repair import repair_generated_module

    raw = {
        "title": "Division",
        "content": {
            "cards": [
                {
                    "kind": "merk",
                    "question": "Wie löse ich 160 : 40?",
                    "answer": "Aus der 40er-Reihe: 160 ÷ 40 = 4.",
                }
            ],
            "knowledge": [{"title": "Reihe", "text": "Nutze die 90er-Reihe."}],
        },
        "quiz": {
            "questions": [
                {
                    "q": "Was ist das Ergebnis der Division 960 : 40?",
                    "options": ["24", "23", "26", "25"],
                    "answer": 0,
                    "question_type": "calculation",
                    "explanation": "Variante 1 (Reihen): 960 ÷ 40. Aus der 40er-Reihe: 960 ÷ 40 = 24.",
                }
            ]
        },
    }
    out = repair_generated_module(raw)
    card_answer = out["content"]["cards"][0]["answer"]
    quiz_expl = out["quiz"]["questions"][0]["explanation"]
    knowledge = out["content"]["knowledge"][0]["text"]
    assert "40er-Reihe" not in card_answer
    assert "40er-Reihe" not in quiz_expl
    assert "90er-Reihe" not in knowledge
    assert "4er-Reihe" in quiz_expl or "Kürzen" in quiz_expl


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Wie dividiere ich die Dezimalzahl 72 durch den Divisor 80?", 0.9),
        ("Wie löse ich die Division 960 : 40?", 24.0),
        ("Was ist das Ergebnis von 810 : 90?", 9.0),
    ],
)
def test_division_question_parsing_and_worked_solution(question, expected):
    parsed = parse_arithmetic_operands(question)
    assert parsed is not None
    assert parsed[0] == "div"
    text = build_worked_solution(question, expected)
    assert text is not None
    assert "40er-Reihe" not in text
    assert "80er-Reihe" not in text
    assert "90er-Reihe" not in text
    assert "10er-Reihe" not in text


def test_division_72_by_80_has_derivation_not_recipe():
    question = "Wie dividiere ich die Dezimalzahl 72 durch den Divisor 80?"
    assert explanation_is_weak("72 : 80 = 0,9", question)
    text = build_worked_solution(question, 0.9)
    assert text is not None
    assert "Kürzen" in text or "Komma" in text
    assert explanation_has_derivation(text, question)


def test_enrich_replaces_weak_72_by_80_recipe():
    question = "Wie dividiere ich die Dezimalzahl 72 durch den Divisor 80?"
    q = {
        "q": question,
        "options": ["0,9", "0,09", "9", "0,72"],
        "answer": 0,
        "question_type": "calculation",
        "explanation": "72 : 80 = 0,9",
    }
    enriched = enrich_quiz_explanation(q)
    assert enriched != q["explanation"]
    assert explanation_has_derivation(enriched, question)
