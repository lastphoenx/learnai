"""Qualitätsreport — Practice-Items und Zeitstempel Europe/Zurich."""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock

import pytest

from app.core.crypto import encrypt_text_master
from app.services.ai_run_snapshot import format_finished_at_zurich
from app.services.crypto_json import encrypt_json
from app.services.unit_quality_report_service import _module_section, _practice_lines


def test_format_finished_at_zurich_converts_utc_to_local():
    # 02:45 UTC = 04:45 CEST (September)
    assert format_finished_at_zurich("2026-09-12T02:45:00+00:00") == "2026-09-12 04:45"


@pytest.fixture
def master_key_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", key)
    from app.config import Settings

    monkeypatch.setattr("app.config.settings", Settings())
    monkeypatch.setattr("app.core.crypto.encryption.settings", Settings())


def test_practice_lines_renders_label_diagram():
    content = {
        "intro": "Ordne Begriffe am Zeitstrahl zu.",
        "knowledge": [],
        "cards": [],
        "practice": [
            {
                "prompt": "Ordne die Epochen chronologisch auf dem Zeitstrahl zu.",
                "hint": "Ordne von früh nach spät.",
                "answer_type": "label_diagram",
                "answer": "{}",
                "diagram": {
                    "layout": "timeline",
                    "title": "Epochen auf dem Zeitstrahl",
                    "hotspots": [{"id": f"h{i}", "accept": [f"Term {i}"]} for i in range(10)],
                },
            }
        ],
    }
    lines = _practice_lines(content, module_ref="0010.04")
    report = "\n".join(lines)
    assert "#### Übung 0010.04.P01" in report
    assert "label_diagram" in report
    assert "10 Begriffe" in report
    assert "Layout: timeline" in report
    assert "Ordne die Epochen" in report


def test_practice_lines_renders_choice_fallback():
    content = {
        "practice": [
            {
                "prompt": "Wann fand der Rütlischwur statt?",
                "answer_type": "choice",
                "options": ["1291", "1386", "1515", "1848"],
                "answer": "0",
                "hint": "Beginn der Eidgenossenschaft.",
            }
        ],
    }
    report = "\n".join(_practice_lines(content, module_ref="0011.04"))
    assert "choice" in report
    assert "[A] ✓ 1291" in report
    assert "Rütlischwur" in report


def test_module_section_includes_practice_beyond_intro(master_key_env):
    mod = MagicMock()
    mod.order_index = 3
    mod.title_encrypted = encrypt_text_master("Aufgaben")
    mod.content_encrypted = encrypt_json(
        {
            "intro": "Ordne Begriffe am Zeitstrahl zu.",
            "knowledge": [],
            "cards": [],
            "practice": [
                {
                    "prompt": "Ordne die Epochen auf dem Zeitstrahl zu.",
                    "answer_type": "label_diagram",
                    "diagram": {
                        "layout": "timeline",
                        "hotspots": [{"id": "a", "accept": ["Steinzeit"]}],
                    },
                }
            ],
        }
    )
    mod.quiz_encrypted = encrypt_json({})

    unit = MagicMock()
    unit.modules = [mod]
    unit.status = "ready"

    report = "\n".join(_module_section(unit, family="0010", instance="0001"))
    assert "### Modul 0010.04: Aufgaben" in report
    assert "Intro: Ordne Begriffe am Zeitstrahl zu." in report
    assert "#### Übung 0010.04.P01" in report
    assert "label_diagram" in report
