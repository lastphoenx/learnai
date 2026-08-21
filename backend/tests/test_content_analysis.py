from app.core.card_answer import grade_input_card, grade_worked_solution
from app.core.content_analysis import analyze_interactive_modules, classify_operation


def test_classify_addition():
    assert classify_operation("Wie berechnest du die Summe von 3,2 und 4,8?") == "add"


def test_classify_division_colon():
    assert classify_operation("Was ist das Ergebnis von 24.68 : 8?") == "div"


def test_analyze_modules_overview():
    modules = [
        {
            "title": "Dezimal Addition",
            "content": {
                "cards": [{"question": "Wie addierst du 1,4 + 3,8?", "answer": "5,2"}],
            },
            "quiz": {
                "questions": [
                    {"q": "Was ist 2,5 + 1,2?"},
                    {"q": "Was ergibt 8.32 : 4?"},
                ],
            },
        }
    ]
    result = analyze_interactive_modules(modules)
    assert result["quiz"]["total"] == 2
    assert result["cards"]["total"] == 1
    assert "Diese Einheit enthält" in result["overview"]
    assert any(op["key"] == "add" for op in result["quiz"]["operations"])


def test_grade_input_card_numeric():
    graded = grade_input_card(
        question="Was ist 1,4 + 3,8?",
        expected_answer="5,2",
        user_answer="5.2",
    )
    assert graded["result_correct"] is True
    assert graded["correct"] is True


def test_grade_worked_solution_accepts_steps():
    ok, _ = grade_worked_solution(
        "Was ist 24,68 : 8?",
        "3,085",
        "Ich zerlege 24 und 0,68. 24 geteilt durch 8 ist 3. Dann 680 Tausendstel durch 8 = 85. Ergebnis 3,085.",
    )
    assert ok is True
