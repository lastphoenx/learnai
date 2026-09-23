"""Tests für Posten-kompakt Single-Shot-Generierung."""

import json
from pathlib import Path

from app.ai.generate_german_compact import should_use_german_compact
from app.ai.generate_posten_compact import (
    _is_weak_card,
    _parse_posten_compact_payload,
    build_thin_retry_hint,
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
    assert should_use_posten_compact(
        trainer_preset="exam_review",
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
    assert not should_use_posten_compact(
        trainer_preset="exam_review",
        focus_group="german",
        math_focus="de_grammar",
    )
    assert should_use_german_compact(focus_group="german", math_focus="de_grammar")


def test_exam_review_system_prompt_and_counts():
    from app.ai.prompts.posten_compact import EXAM_REVIEW_COUNTS, build_compact_system_prompt

    system = build_compact_system_prompt("exam_review")
    assert "Lernzielkontrolle" in system
    assert str(EXAM_REVIEW_COUNTS["quiz"]) in system
    assert str(EXAM_REVIEW_COUNTS["cards"]) in system


def test_spatial_system_prompt_extension():
    from app.ai.prompts.posten_compact import build_compact_system_prompt

    base = build_compact_system_prompt("posten_compact", spatial_geometry=False)
    spatial = build_compact_system_prompt("posten_compact", spatial_geometry=True)
    assert "image_choice_items" not in base
    assert "image_choice_items" in spatial


def test_posten_compact_spatial_payload_to_practice():
    raw = {
        "goal": "Du kennst Ansichten.",
        "facts": [
            {"title": "Aufsicht", "text": "Von oben."},
            {"title": "Vorderansicht", "text": "Von vorne."},
            {"title": "Bauplan", "text": "Zahlen im Raster."},
        ],
        "cards": [{"question": f"Frage {i}?", "answer": f"A{i}."} for i in range(12)],
        "quiz": [
            {"q": f"Q{i}?", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "x"}
            for i in range(8)
        ],
        "grid_fill_items": [
            {
                "prompt": "Trage Höhen ein.",
                "rows": 2,
                "cols": 2,
                "cell_type": "number",
                "reference_height_matrix": [[1, 2], [3, 1]],
                "answer": [[1, 2], [3, None]],
            }
        ],
    }
    payload = _parse_posten_compact_payload(
        json.dumps(raw, ensure_ascii=False),
        card_target=12,
        question_target=8,
    )
    assert len(payload["grid_fill_items"]) == 1
    modules = posten_compact_payload_to_modules(
        payload,
        title="Geo",
        focus_group="math",
        source_ids=["00000000-0000-0000-0000-000000000001"],
    )
    aufgaben = next(m for m in modules if m["title"] == "Aufgaben")
    practice = aufgaben["content"].get("practice") or []
    assert any(p.get("answer_type") == "grid_fill" for p in practice)


def test_posten_compact_region_paint_payload_to_practice():
    raw = {
        "goal": "Du kennst Würfel.",
        "facts": [
            {"title": "A", "text": "1."},
            {"title": "B", "text": "2."},
            {"title": "C", "text": "3."},
        ],
        "cards": [{"question": f"Frage {i}?", "answer": f"A{i}."} for i in range(12)],
        "quiz": [
            {"q": f"Q{i}?", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "x"}
            for i in range(8)
        ],
        "region_paint_items": [
            {
                "prompt": "Färbe gemäss Ansicht.",
                "template": "iso_tower_2",
                "answer": {"lower_top": "yellow", "upper_right": "green"},
            }
        ],
    }
    payload = _parse_posten_compact_payload(
        json.dumps(raw, ensure_ascii=False),
        card_target=12,
        question_target=8,
    )
    assert len(payload["region_paint_items"]) == 1
    modules = posten_compact_payload_to_modules(
        payload,
        title="Geo",
        focus_group="math",
        source_ids=[],
    )
    practice = next(m for m in modules if m["title"] == "Aufgaben")["content"].get("practice") or []
    assert any(p.get("answer_type") == "region_paint" for p in practice)


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


def test_parse_timeline_rejects_geometry_vocab_slots():
    from app.ai.generate_posten_compact import _parse_timeline

    bogus = {
        "title": "Ansichten und Pläne",
        "slots": [
            {"label": "Netz", "hint": "Würfelnetz"},
            {"label": "Bauplan", "hint": "Grundriss"},
            {"label": "Ansicht", "hint": "Vorderansicht"},
            {"label": "Körper", "hint": "Raumkörper"},
        ],
    }
    assert _parse_timeline(bogus) is None


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
    aufgaben = next(m for m in modules if m["title"] == "Aufgaben")
    practice = aufgaben["content"].get("practice") or []
    assert any(p.get("answer_type") == "label_diagram" for p in practice)
    validate_interactive_modules(
        modules,
        min_cards=12,
        min_questions=8,
        min_modules=4,
    )


def test_posten_compact_without_timeline_builds_aufgaben_from_quiz():
    raw = {
        "goal": "Du kennst den Faustkeil.",
        "facts": [
            {"title": "Faustkeil", "text": "Werkzeug aus Feuerstein."},
            {"title": "Feuer", "text": "Wärme und Licht."},
            {"title": "Leben", "text": "Jäger und Sammler."},
        ],
        "cards": [
            {"question": f"Frage {i}?", "answer": f"Antwort {i}."} for i in range(12)
        ],
        "quiz": [
            {
                "q": f"Quiz {i}?",
                "options": ["A", "B", "C", "D"],
                "answer": i % 4,
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
    assert payload["timeline"] is None
    modules = posten_compact_payload_to_modules(payload, title="Posten 15", focus_group="nmg")
    assert len(modules) == 4
    aufgaben = next(m for m in modules if m["title"] == "Aufgaben")
    practice = aufgaben["content"].get("practice") or []
    assert len(practice) == 4
    assert all(p.get("answer_type") == "choice" for p in practice)
    assert all(m["content"].get("practice") == [] for m in modules if m["title"] != "Aufgaben")


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


def test_thin_retry_hint_combines_content_and_spatial():
    # Regression: unit_id d3881fee... — Versuch 1 scheiterte an thin_content
    # (zu wenige Quizfragen), der Retry-Hinweis erwähnte damals nur
    # Fakten/Karten/Quiz. Die KI bekam nie den Raumaufgaben-Hinweis und
    # speicherte Versuch 2 komplett ohne Raumaufgaben (thin_spatial_soft,
    # practice=0, raw=0). Bei aktivierter Raumgeometrie muss der Hinweis
    # IMMER beide Themen abdecken, unabhängig davon, welcher Fehler zuerst kam.
    hint = build_thin_retry_hint(
        "thin_content",
        spatial_geometry=True,
        facts_min=6,
        card_target=12,
        question_target=8,
    )
    assert "vorheriger Versuch zu dünn" in hint
    assert "Raumaufgaben fehlten im JSON" in hint


def test_thin_retry_hint_content_only_without_spatial():
    hint = build_thin_retry_hint(
        "thin_content",
        spatial_geometry=False,
        facts_min=6,
        card_target=12,
        question_target=8,
    )
    assert "vorheriger Versuch zu dünn" in hint
    assert "Raumaufgaben" not in hint


def test_thin_retry_hint_spatial_only_for_thin_spatial():
    hint = build_thin_retry_hint(
        "thin_spatial",
        spatial_geometry=True,
        facts_min=6,
        card_target=12,
        question_target=8,
    )
    assert "vorheriger Versuch zu dünn" not in hint
    assert "Raumaufgaben fehlten im JSON" in hint


def test_thin_retry_hint_mentions_all_spatial_types():
    # net_build/synthetic_viewpoint (Phase 3/4) fehlten im Hinweistext.
    hint = build_thin_retry_hint(
        "thin_spatial",
        spatial_geometry=True,
        facts_min=6,
        card_target=12,
        question_target=8,
    )
    assert "net_build_items" in hint
    assert "synthetic_viewpoint_items" in hint
