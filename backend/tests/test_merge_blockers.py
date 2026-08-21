import pytest

from app.ai.errors import LlmError
from app.ai.generate import _validate_modules, _validate_single_module
from app.ai.validators.interactive import (
    parse_quiz_answer,
    validate_interactive_import,
    validate_interactive_structure,
)
from app.schemas import TrainerOptionsSchema


def _long_text(words: int = 140) -> str:
    return " ".join(f"wort{i}" for i in range(words))


def _valid_module() -> dict:
    return {
        "title": "Block",
        "content": {"text": _long_text()},
        "quiz": {
            "questions": [
                {
                    "q": f"Frage {i}?",
                    "options": ["A", "B", "C", "D"],
                    "answer": 0,
                }
                for i in range(4)
            ]
        },
    }


def test_validate_single_module_accepts_valid_module():
    _validate_single_module(_valid_module(), task="mixed", index=0)


def test_validate_single_module_rejects_too_few_questions():
    mod = _valid_module()
    mod["quiz"]["questions"] = mod["quiz"]["questions"][:2]
    with pytest.raises(LlmError, match="zu wenige Quizfragen"):
        _validate_single_module(mod, task="mixed", index=0)


def test_validate_modules_still_requires_minimum_count():
    with pytest.raises(LlmError, match="Zu wenige Module"):
        _validate_modules([_valid_module()], task="mixed")


@pytest.mark.parametrize(
    "answer",
    [-1, 4, "B", True],
)
def test_parse_quiz_answer_rejects_invalid(answer):
    with pytest.raises(LlmError):
        parse_quiz_answer({"answer": answer}, label="Test")


def test_validate_interactive_structure_rejects_empty_question():
    modules = [
        {
            "title": "Bereich",
            "content": {"cards": [{"question": "Q?", "answer": "A."}], "knowledge": []},
            "quiz": {"questions": [{"q": "", "options": ["A", "B", "C", "D"], "answer": 0}]},
        }
    ]
    with pytest.raises(LlmError, match="Frage fehlt"):
        validate_interactive_structure(modules)


def test_validate_interactive_structure_rejects_duplicate_options():
    modules = [
        {
            "title": "Bereich",
            "content": {"cards": [], "knowledge": []},
            "quiz": {
                "questions": [
                    {"q": "Frage?", "options": ["A", "A", "A", "A"], "answer": 0},
                ]
            },
        }
    ]
    with pytest.raises(LlmError, match="verschieden"):
        validate_interactive_structure(modules)


def test_trainer_options_caps_cards():
    with pytest.raises(Exception):
        TrainerOptionsSchema.normalize_raw({"cards": 999999})


def test_trainer_options_maps_legacy_answer_length():
    opts = TrainerOptionsSchema.normalize_raw({"answer_length": "medium"})
    assert opts.answer_length == "normal"


def test_import_rejects_invalid_answer():
    modules = [
        {
            "title": "Import",
            "content": {"cards": [], "knowledge": []},
            "quiz": {
                "questions": [
                    {"q": "Frage?", "options": ["A", "B", "C", "D"], "answer": 9},
                ]
            },
        }
    ]
    with pytest.raises(LlmError):
        validate_interactive_import(modules)
