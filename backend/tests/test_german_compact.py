"""Tests für kompakten Deutsch-Grammatik-Generator."""

import json
from pathlib import Path

import pytest

from app.ai.generate_german_compact import (
    _collapse_duplicate_mental_answers,
    _enrich_compact_quiz,
    _parse_understand,
    compact_payload_to_modules,
    should_use_german_compact,
)
from app.ai.prompts.german_compact import COMPACT_COUNTS
from app.core.content_qa import collect_content_warnings_for_module
from app.core.german_case_analysis import spacy_available
from app.ai.validators.interactive import validate_interactive_modules


def test_should_use_german_compact_for_de_grammar():
    assert should_use_german_compact(focus_group="german", math_focus="de_grammar")
    assert not should_use_german_compact(focus_group="german", math_focus="de_spelling")
    assert not should_use_german_compact(focus_group="math", math_focus="de_grammar")


def test_parse_understand_marks_span_with_mark_tag():
    raw = [
        {
            "sentence": "Der Mars leuchtet am Himmel.",
            "span": "Der Mars",
            "answer": "Nominativ",
            "explanation": "Wer leuchtet?",
        }
    ]
    cards = _parse_understand(raw)
    assert len(cards) == 1
    assert "<mark>Der Mars</mark>" in cards[0]["question"]


def test_parse_understand_repairs_whole_sentence_span():
    if not spacy_available():
        pytest.skip("spaCy not available")
    raw = [
        {
            "sentence": "Die Ringe des Saturns glitzern.",
            "span": "Die Ringe des Saturns glitzern.",
            "answer": "Nominativ",
            "explanation": "Wer glitzert?",
        }
    ]
    cards = _parse_understand(raw)
    assert len(cards) == 1
    assert "<mark>" in cards[0]["question"]


def test_enrich_compact_quiz_adds_mark_highlight():
    raw = [
        {
            "q": "Bestimme den Fall der markierten Wortgruppe: Das Spielzeug der Katze liegt im Flur.",
            "options": ["Dativ", "Akkusativ", "Nominativ", "Genitiv"],
            "answer": 3,
            "explanation": "Wessen?",
            "sentence": "Das Spielzeug der Katze liegt im Flur.",
            "span": "der Katze",
        }
    ]
    enriched = _enrich_compact_quiz(raw, raw)
    assert "<mark>der Katze</mark>" in enriched[0]["q"]


def test_collapse_duplicate_mental_answers():
    cards = [
        {"kind": "mental", "question": "A?", "answer": "Nominativ"},
        {"kind": "mental", "question": "B?", "answer": "Nominativ"},
        {"kind": "mental", "question": "C?", "answer": "Nominativ"},
        {"kind": "merk", "question": "D?", "answer": "Nominativ"},
    ]
    kept = _collapse_duplicate_mental_answers(cards)
    assert len([c for c in kept if c.get("kind") == "mental"]) == 2
    assert len([c for c in kept if c.get("kind") == "merk"]) == 1


def test_content_qa_flags_compact_mental_duplicates():
    shared = "Wer? = Nominativ; Wessen? = Genitiv; Wem? = Dativ; Wen? = Akkusativ."
    content = {
        "cards": [
            {"kind": "mental", "question": f"Was bedeutet «Genitiv» {i}?", "answer": f"Genitiv — {shared}"}
            for i in range(3)
        ]
    }
    warnings = collect_content_warnings_for_module(content=content, quiz={"questions": []}, focus_group="german")
    assert any(w["kind"] == "generic_mental_cards" for w in warnings)


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
                "question": f"Bestimme den Fall: «Satz {i}.»",
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
            {"kind": "merk", "question": "Welche Frage gehört zum Nominativ?", "answer": "Wer oder was?"}
            for _ in range(COMPACT_COUNTS["merk_cards"])
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
    drill = modules[2]["content"]["cards"]
    assert sum(1 for c in drill if c.get("card_role") == "term") == COMPACT_COUNTS["merk_cards"]
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


def test_compact_fixture_structure_if_present():
    fixture = Path(__file__).parent / "fixtures" / "german_compact_sample.json"
    if not fixture.exists():
        return
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    modules = compact_payload_to_modules(payload, title="Die vier Fälle", difficulty=1)
    assert len(modules) == 4
