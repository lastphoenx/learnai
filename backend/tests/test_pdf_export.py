"""Tests für PDF-Export."""

from __future__ import annotations

import pytest

from app.services.pdf_export_service import build_unit_worksheet_html, html_to_pdf
from app.services.unit_service import UnitError


def test_html_to_pdf_returns_pdf_bytes():
    pdf = html_to_pdf("<h1>Test</h1><p>Hallo Welt</p>")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def test_worksheet_requires_modules():
    with pytest.raises(UnitError) as exc:
        build_unit_worksheet_html({"title": "Test", "modules": []})
    assert exc.value.code == "no_modules"


def test_worksheet_html_contains_questions():
    html_body = build_unit_worksheet_html(
        {
            "title": "Brüche",
            "subject": "Mathematik",
            "difficulty": 2,
            "modules": [
                {
                    "title": "Einführung",
                    "content": {"text": "Kurzer Lerntext."},
                    "quiz": {
                        "questions": [
                            {"q": "Was ist 1/2 + 1/4?", "options": ["1/4", "3/4", "1"], "answer": 1}
                        ]
                    },
                }
            ],
        }
    )
    assert "Brüche" in html_body
    assert "1/2 + 1/4" in html_body
    assert "a)" in html_body


def test_interactive_trainer_worksheet_html():
    from app.services.pdf_export_service import build_interactive_trainer_worksheet_html

    html_body = build_interactive_trainer_worksheet_html(
        {
            "title": "Bruchrechnen",
            "task_type": "interactive",
            "subject": "Mathematik",
            "difficulty": 2,
            "modules": [
                {
                    "title": "Grundlagen",
                    "content": {
                        "intro": "Kurzer Überblick.",
                        "knowledge": [{"title": "Nenner", "text": "Unten steht der Nenner."}],
                        "cards": [
                            {
                                "question": "Was ist 1/2 + 1/4?",
                                "answer": "3/4",
                                "tip": "Gleichnamig machen",
                            }
                        ],
                    },
                    "quiz": {
                        "questions": [
                            {
                                "q": "Was ist 0.5 als Bruch?",
                                "options": ["1/4", "1/2", "3/4", "1"],
                                "answer": 1,
                            }
                        ]
                    },
                }
            ],
        }
    )
    assert "Lerntrainer" in html_body
    assert "Kernwissen" in html_body
    assert "Lernkarten" in html_body
    assert "flashcard-table" in html_body
    assert "3/4" in html_body
    assert "Quiz-Lösungen" in html_body
    assert "1. b)" in html_body


def test_build_unit_worksheet_routes_interactive():
    html_body = build_unit_worksheet_html(
        {
            "title": "Test",
            "task_type": "interactive",
            "modules": [
                {
                    "title": "A",
                    "content": {"cards": [{"question": "Q?", "answer": "A."}]},
                    "quiz": {"questions": []},
                }
            ],
        }
    )
    assert "Lernkarten" in html_body
