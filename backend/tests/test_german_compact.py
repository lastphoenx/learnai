"""Tests für kompakten Deutsch-Grammatik-Generator."""

from app.ai.generate_german_compact import compact_payload_to_modules, should_use_german_compact
from app.ai.prompts.german_compact import COMPACT_COUNTS
from app.ai.validators.interactive import validate_interactive_modules


def test_should_use_german_compact_for_de_grammar():
    assert should_use_german_compact(focus_group="german", math_focus="de_grammar")
    assert not should_use_german_compact(focus_group="german", math_focus="de_spelling")
    assert not should_use_german_compact(focus_group="math", math_focus="de_grammar")


def test_compact_payload_to_modules_counts():
    payload = {
        "theory": {
            "intro": "Mission Fall-Detektiv",
            "knowledge": [{"title": "Frageprobe", "text": "Wer? Wessen? Wem? Wen?"}],
            "cases": [{"name": "Nominativ", "question": "Wer?", "example": "Der Löwe schläft."}],
        },
        "understand_cards": [
            {
                "kind": "input",
                "question": f"Bestimme den Fall: «Satz {i}.» — markiert: [Wort {i}]",
                "answer": "Nominativ",
                "answer_type": "short_text",
                "grammar": {
                    "case_check": {
                        "sentence": f"Satz {i}.",
                        "span": f"Wort {i}",
                    }
                },
            }
            for i in range(COMPACT_COUNTS["understand"])
        ],
        "merk_cards": [
            {"kind": "merk", "question": f"Merk {i}?", "answer": f"A{i}"}
            for i in range(COMPACT_COUNTS["merk_cards"])
        ],
        "mental_cards": [
            {"kind": "mental", "question": f"Kopf {i}?", "answer": f"B{i}"}
            for i in range(COMPACT_COUNTS["mental_cards"])
        ],
        "quiz_questions": [
            {
                "q": f"Quiz {i}?",
                "options": ["Nominativ", "Genitiv", "Dativ", "Akkusativ"],
                "answer": 0,
                "explanation": "Weil Wer?",
                "question_type": "concept",
            }
            for i in range(COMPACT_COUNTS["quiz"])
        ],
    }
    modules = compact_payload_to_modules(payload, title="Die vier Fälle", difficulty=1)
    assert len(modules) == 4
    total_cards = sum(len(m["content"]["cards"]) for m in modules)
    total_quiz = sum(len(m["quiz"]["questions"]) for m in modules)
    assert total_cards == COMPACT_COUNTS["understand"] + COMPACT_COUNTS["merk_cards"] + COMPACT_COUNTS["mental_cards"]
    assert total_quiz == COMPACT_COUNTS["quiz"]
    validate_interactive_modules(
        modules,
        min_cards=25,
        min_questions=20,
        min_modules=4,
    )
