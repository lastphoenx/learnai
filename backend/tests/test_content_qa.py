from app.core.basiswissen import derive_mental_term_cards, parse_basiswissen_payload
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


def test_content_qa_ignores_german_case_drill_shared_answers():
    content = {
        "cards": [
            {"kind": "mental", "question": f"Wer schläft? Satz {i}.", "answer": "Nominativ"}
            for i in range(5)
        ]
    }
    warnings = collect_content_warnings_for_module(content=content, quiz={"questions": []}, focus_group="german")
    assert not any(w["kind"] == "generic_mental_cards" for w in warnings)


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


def test_content_qa_flags_near_duplicate_mental_cards_from_fixture():
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parent / "fixtures" / "basiswissen" / "german_four_cases.json"
    bw = parse_basiswissen_payload(json.loads(fixture_path.read_text(encoding="utf-8")), focus_group="german")
    # Simuliert altes Verhalten: gleicher Hint-Körper für Gen/Dat/Akk
    shared = "Wer? = Nominativ; Wessen? = Genitiv; Wem? = Dativ; Wen? = Akkusativ. Fälle zeigen, welche Aufgabe ein Nomen im Satz hat."
    content = {
        "cards": [
            {
                "source": "basiswissen",
                "card_role": "term",
                "question": "Was bedeutet «Genitiv» bei Die vier Fälle?",
                "answer": f"Genitiv — {shared}",
            },
            {
                "source": "basiswissen",
                "card_role": "term",
                "question": "Was bedeutet «Dativ» bei Die vier Fälle?",
                "answer": f"Dativ — {shared}",
            },
            {
                "source": "basiswissen",
                "card_role": "term",
                "question": "Was bedeutet «Akkusativ» bei Die vier Fälle?",
                "answer": f"Akkusativ — {shared}",
            },
        ]
    }
    warnings = collect_content_warnings_for_module(content=content, quiz={"questions": []}, focus_group="german")
    assert any(w["kind"] == "generic_mental_cards" for w in warnings)

    fixed_warnings = collect_content_warnings_for_module(
        content={"cards": derive_mental_term_cards(bw)},
        quiz={"questions": []},
        focus_group="german",
    )
    assert not any(w["kind"] == "generic_mental_cards" for w in fixed_warnings)


def test_summarize_content_warnings():
    summary = summarize_content_warnings([{"level": "warn"}, {"level": "info"}])
    assert summary["total"] == 2
    assert summary["warn"] == 1
