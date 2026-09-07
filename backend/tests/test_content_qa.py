from app.core.content_qa import collect_content_warnings_for_module, summarize_content_warnings


def test_content_qa_flags_duplicate_explanations():
    warnings = collect_content_warnings_for_module(
        content={},
        quiz={
            "questions": [
                {"q": "Frage A?", "explanation": "Fälle zeigen, welche Aufgabe ein Nomen im Satz hat. Mit den W-Fragen findest du sie."},
                {"q": "Frage B?", "explanation": "Fälle zeigen, welche Aufgabe ein Nomen im Satz hat. Mit den W-Fragen findest du sie."},
            ]
        },
        focus_group="german",
    )
    kinds = {w["kind"] for w in warnings}
    assert "duplicate_quiz_explanation" in kinds


def test_content_qa_flags_generic_label_diagram_for_german():
    warnings = collect_content_warnings_for_module(
        content={
            "practice": [
                {
                    "answer_type": "label_diagram",
                    "source": "basiswissen",
                    "diagram": {"template": "generic", "hotspots": []},
                }
            ]
        },
        quiz={"questions": []},
        focus_group="german",
    )
    assert any(w["kind"] == "generic_label_diagram" for w in warnings)


def test_summarize_content_warnings():
    summary = summarize_content_warnings([{"level": "warn"}, {"level": "info"}])
    assert summary["total"] == 2
    assert summary["warn"] == 1
