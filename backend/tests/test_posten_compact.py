"""Tests für Posten-kompakt Single-Shot-Generierung."""

import json
from pathlib import Path

from app.ai.generate_german_compact import should_use_german_compact
from app.ai.generate_posten_compact import (
    _is_weak_card,
    _parse_posten_compact_payload,
    posten_compact_payload_to_modules,
    should_use_posten_compact,
)
from app.ai.validators.interactive import dedupe_interactive_modules, validate_interactive_modules


def test_should_use_posten_compact_routing():
    assert should_use_posten_compact(
        trainer_preset="posten_compact",
        focus_group="nmg",
        math_focus=None,
    )
    assert not should_use_posten_compact(
        trainer_preset="standard",
        focus_group="nmg",
        math_focus=None,
    )
    assert not should_use_posten_compact(
        trainer_preset="posten_compact",
        focus_group="german",
        math_focus="de_grammar",
    )
    assert should_use_german_compact(focus_group="german", math_focus="de_grammar")


def test_is_weak_card_rejects_tautology_and_dates():
    assert _is_weak_card("Was ist der Fachbegriff «Fundstücke»?", "Fundstücke")
    assert _is_weak_card("Was bedeutet «9500 bis 5500 v. Chr.»?", "9500 bis 5500 v. Chr.")
    assert _is_weak_card("Einleitung lesen", "Lies die Einleitung.")
    assert not _is_weak_card(
        "Wer untersucht ausgegrabene Fundstücke?",
        "Archäologinnen und Archäologen.",
    )


def test_is_weak_card_rejects_single_year_terms():
    assert _is_weak_card("Was bedeutet «800 v. Chr.»?", "800 v. Chr.: Die Eisenzeit beginnt etwa 800 v. Chr.")


def test_parse_posten_compact_posten14_fixture():
    fixture = Path(__file__).parent / "fixtures" / "posten_compact_posten14.json"
    payload = _parse_posten_compact_payload(
        fixture.read_text(encoding="utf-8"),
        card_target=12,
        question_target=8,
    )
    assert len(payload["facts"]) >= 3
    assert len(payload["cards"]) == 12
    assert len(payload["quiz_questions"]) == 8
    assert all(q.get("source") == "posten_compact" for q in payload["quiz_questions"])
    assert payload["timeline"] is not None


def test_posten_compact_module_mapping():
    fixture = Path(__file__).parent / "fixtures" / "posten_compact_posten14.json"
    payload = _parse_posten_compact_payload(
        fixture.read_text(encoding="utf-8"),
        card_target=12,
        question_target=8,
    )
    modules = posten_compact_payload_to_modules(payload, title="Posten 14", focus_group="nmg")
    modules, _ = dedupe_interactive_modules(modules)
    assert len(modules) == 4
    total_cards = sum(len(m["content"]["cards"]) for m in modules)
    total_quiz = sum(len(m["quiz"]["questions"]) for m in modules)
    assert total_cards == 12
    assert total_quiz == 8
    practice = modules[-1]["content"].get("practice") or []
    assert any(p.get("answer_type") == "label_diagram" for p in practice)
    validate_interactive_modules(
        modules,
        min_cards=12,
        min_questions=8,
        min_modules=4,
    )


def test_posten_compact_rejects_instruction_terms_in_parse():
    raw = {
        "goal": "Lernziel.",
        "facts": [
            {"title": "A", "text": "Text eins."},
            {"title": "B", "text": "Text zwei."},
            {"title": "C", "text": "Text drei."},
        ],
        "cards": [
            {"question": "Einleitung lesen", "answer": "Lies die Einleitung."},
            {"question": "Was bedeutet «9500 bis 5500 v. Chr.»?", "answer": "9500 bis 5500 v. Chr."},
        ]
        + [
            {"question": f"Gute Frage {i}?", "answer": f"Antwort {i}."}
            for i in range(12)
        ],
        "quiz": [
            {
                "q": f"Quiz {i}?",
                "options": ["A", "B", "C", "D"],
                "answer": 0,
                "explanation": "Weil.",
            }
            for i in range(8)
        ],
    }
    payload = _parse_posten_compact_payload(
        json.dumps(raw, ensure_ascii=False),
        card_target=12,
        question_target=8,
    )
    questions = [c["question"].lower() for c in payload["cards"]]
    assert "einleitung lesen" not in questions
    assert not any("9500 bis 5500" in q for q in questions)


def test_load_unit_source_images_empty_without_sources():
    from types import SimpleNamespace

    from app.ai.generate import load_unit_source_images

    unit = SimpleNamespace(sources=[])
    assert load_unit_source_images(unit) == []


def test_complete_accepts_images_parameter(monkeypatch):
    from app.ai.providers import complete

    captured: dict = {}

    def fake_openai_multimodal(prompt, images, **kwargs):
        captured["images"] = len(images)
        captured["prompt"] = prompt
        from app.ai.providers import LlmResult

        return LlmResult(provider="openai", model="gpt-test", text='{"ok": true}')

    monkeypatch.setattr("app.ai.providers._openai_multimodal_chat", fake_openai_multimodal)
    result = complete(
        prompt="Test",
        provider="openai",
        images=[(b"\xff\xd8\xff", "image/jpeg")],
        json_mode=True,
    )
    assert captured["images"] == 1
    assert result["text"] == '{"ok": true}'
