from app.core.card_answer import grade_input_card, grade_worked_solution
from app.core.content_analysis import analyze_interactive_modules, classify_operation
from app.core.method_taxonomy import classify_method, normalize_method_id


def test_classify_addition():
    assert classify_operation("Wie berechnest du die Summe von 3,2 und 4,8?") == "add"


def test_classify_division_colon():
    assert classify_operation("Was ist das Ergebnis von 24.68 : 8?") == "div"


def test_classify_method_written():
    assert classify_method("Rechne schriftlich: 584,5 + 67,81", kind="input") == "written"


def test_normalize_method_alias():
    assert normalize_method_id("zerlegung") == "decomposition"


def test_classify_addition_symbol():
    assert classify_operation("Was ist 2,5 + 1,2?") == "add"


def test_analyze_modules_overview():
    modules = [
        {
            "title": "Dezimal Addition",
            "content": {
                "cards": [
                    {
                        "kind": "merk",
                        "question": "Wann rechnest du im Kopf?",
                        "answer": "Bei einfachen Zahlen.",
                        "method_id": "mental",
                    },
                    {
                        "kind": "input",
                        "question": "Rechne schriftlich: 1,4 + 3,8",
                        "answer": "5,2",
                        "expected_method": "written",
                    },
                ],
            },
            "quiz": {
                "questions": [
                    {"q": "Was ist 2,5 + 1,2?", "question_type": "calculation"},
                    {
                        "q": "Welches Vorgehen passt zu 24 · 9,36?",
                        "question_type": "method",
                        "method_id": "decomposition",
                    },
                ],
            },
        }
    ]
    result = analyze_interactive_modules(modules)
    assert result["quiz"]["total"] == 2
    assert result["cards"]["total"] == 2
    assert "Diese Einheit enthält" in result["overview"]
    assert any(op["key"] == "add" for op in result["quiz"]["operations"])
    assert any(op["key"] == "written" for op in result["cards"]["methods"])


def test_grade_input_card_text_variants():
    graded = grade_input_card(
        question="Welchen Fall hat «die Sonne»?",
        expected_answer="Akkusativ|Akk.",
        user_answer="akkusativ",
        answer_type="short_text",
    )
    assert graded["result_correct"] is True
    assert graded["answer_type"] == "short_text"


def test_grade_input_card_numeric():
    graded = grade_input_card(
        question="Was ist 1,4 + 3,8?",
        expected_answer="5,2",
        user_answer="5.2",
    )
    assert graded["result_correct"] is True
    assert graded["correct"] is True


def test_grade_worked_solution_accepts_decomposition_steps():
    ok, _ = grade_worked_solution(
        "Rechne: 14 × 0,85",
        "11,9",
        "Ich zerlege 14 in 10 und 4. 10 x 0.85 = 8.5 und 4 x 0.85 = 3.4",
        expected_method="decomposition",
    )
    assert ok is True


def test_grade_worked_solution_accepts_steps():
    ok, _ = grade_worked_solution(
        "Was ist 24,68 : 8?",
        "3,085",
        "Ich zerlege 24 und 0,68. 24 geteilt durch 8 ist 3. Dann 680 Tausendstel durch 8 = 85. Ergebnis 3,085.",
    )
    assert ok is True


def test_grade_worked_solution_expects_method():
    ok, feedback = grade_worked_solution(
        "Rechne schriftlich: 15,09 + 8,74",
        "23,83",
        "Ich schreibe die Zahlen untereinander mit Komma ausgerichtet und addiere Stelle für Stelle. Ergebnis 23,83.",
        expected_method="written",
    )
    assert ok is True
    assert feedback
