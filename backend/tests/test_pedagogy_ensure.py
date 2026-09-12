"""Automatisches Didaktik-Nachziehen nach Multimodal-Compact."""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock, patch

import pytest

from app.ai.source_pedagogy import encode_source_analysis


@pytest.fixture
def master_key_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", key)
    from app.config import Settings

    monkeypatch.setattr("app.config.settings", Settings())
    monkeypatch.setattr("app.core.crypto.encryption.settings", Settings())


def test_unit_sources_need_pedagogy_extract_empty_blob():
    from app.services.pedagogy_service import unit_sources_need_pedagogy_extract

    unit = MagicMock()
    source = MagicMock()
    source.kind = "image"
    source.storage_path = "/uploads/x.png"
    source.purged_at = None
    source.analysis_encrypted = None
    unit.sources = [source]
    assert unit_sources_need_pedagogy_extract(unit) is True


def test_unit_sources_need_pedagogy_extract_skips_structured(master_key_env):
    from app.services.pedagogy_service import unit_sources_need_pedagogy_extract

    blob = encode_source_analysis(
        provider="ollama",
        model="qwen2.5vl:32b",
        pedagogy={
            "key_terms": [
                {"term": "Archäologie", "definition": "…"},
                {"term": "Steinzeit", "definition": "…"},
                {"term": "Mittelalter", "definition": "…"},
                {"term": "Rütlischwur", "definition": "…"},
            ],
            "assignments": [{"instruction": "Ordne die Epochen", "format": "Zeitstrahl"}],
        },
        structured=True,
    )
    unit = MagicMock()
    source = MagicMock()
    source.kind = "image"
    source.storage_path = "/uploads/x.png"
    source.purged_at = None
    from app.core.crypto import encrypt_text_master

    source.analysis_encrypted = encrypt_text_master(blob)
    unit.sources = [source]
    assert unit_sources_need_pedagogy_extract(unit) is False


@patch("app.services.pedagogy_service._vision_extract_image_source")
@patch("app.services.pedagogy_service._get_unit_or_404")
@patch("app.services.pedagogy_service.resolve_unit_ai_prefs")
def test_ensure_unit_source_pedagogy_runs_vision_when_missing(
    mock_prefs,
    mock_get_unit,
    mock_vision,
):
    from app.ai.generate import VisionExtractResult
    from app.services.pedagogy_service import ensure_unit_source_pedagogy

    mock_prefs.return_value = ({}, {})
    unit = MagicMock()
    source = MagicMock()
    source.kind = "image"
    source.storage_path = "/uploads/x.png"
    source.purged_at = None
    source.analysis_encrypted = None
    source.original_name_encrypted = None
    unit.sources = [source]
    unit.id = "11111111-1111-1111-1111-111111111111"
    unit.subject = "NMG"
    unit.task_type = "interactive"
    unit.profile_id = None
    mock_get_unit.return_value = unit
    mock_vision.return_value = VisionExtractResult(summary="Seite ok", structured=True, ok=True)

    db = MagicMock()
    user = MagicMock()

    with patch("app.services.pedagogy_service._finalize_pedagogy_extract") as mock_finalize:
        mock_finalize.return_value = {"quality": {"level": "good"}}
        result = ensure_unit_source_pedagogy(db, user, unit.id)

    assert result is not None
    assert mock_vision.call_count == 1
    mock_finalize.assert_called_once()
