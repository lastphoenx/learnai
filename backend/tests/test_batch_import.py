"""Tests für PDF-Batch-Import (API + Rate-Limit)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.batch_import_service import (
    _parse_payload,
    _unit_specs,
    _validate_intro_pages,
    run_batch_import,
    start_batch_import,
)
from app.services.generate_limits import acquire_batch_generate_rate_slot
from app.services.unit_service import UnitError


def _sample_pdf(tmp_path: Path) -> bytes:
    import pymupdf

    path = tmp_path / "heft.pdf"
    doc = pymupdf.open()
    try:
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"Seite {i + 1}")
        doc.save(str(path))
    finally:
        doc.close()
    return path.read_bytes()


def test_parse_payload_and_unit_specs():
    payload = _parse_payload(
        {
            "units": [
                {
                    "title": "Posten 14",
                    "page_from": 2,
                    "page_to": 3,
                    "posten": 14,
                    "brief_suffix": "Nur Posten 14",
                },
            ]
        }
    )
    specs = _unit_specs(payload)
    assert specs[0]["title"] == "Posten 14"
    assert specs[0]["page_from"] == 2
    assert specs[0]["brief_suffix"] == "Nur Posten 14"


@patch("app.tasks.batch_import.batch_import_task")
@patch("app.services.batch_import_service.acquire_batch_generate_rate_slot")
def test_start_batch_import_queues_job(mock_rate, mock_task, tmp_path):
    mock_task.delay.return_value = MagicMock(id="celery-1")
    pdf = _sample_pdf(tmp_path)
    payload = json.dumps(
        {
            "units": [{"title": "A", "page_from": 1, "page_to": 2}],
            "default_preset": "posten_compact",
        }
    )
    db = MagicMock()
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    user.tenant_id = "22222222-2222-2222-2222-222222222222"

    result = start_batch_import(db, user, pdf_bytes=pdf, filename="heft.pdf", payload_raw=payload)
    assert result["unit_count"] == 1
    assert result["batch_job_id"]
    mock_rate.assert_called_once_with(user_id=str(user.id))
    mock_task.delay.assert_called_once()


@patch("app.services.generate_limits._redis_client")
def test_batch_rate_counts_once_for_whole_import(mock_redis_fn):
    client = MagicMock()
    mock_redis_fn.return_value = client
    client.incr.return_value = 1

    acquire_batch_generate_rate_slot(user_id="u1")
    assert client.incr.call_count == 1


@patch("app.services.generate_limits._redis_client")
def test_batch_rate_rejects_when_hourly_limit_exceeded(mock_redis_fn):
    client = MagicMock()
    mock_redis_fn.return_value = client
    client.incr.return_value = 11

    with pytest.raises(UnitError, match="Stündliches Generierungs-Limit"):
        acquire_batch_generate_rate_slot(user_id="u1")
    client.decr.assert_called_once()


def test_validate_intro_pages_outside_pdf(tmp_path):
    pdf = _sample_pdf(tmp_path)
    path = tmp_path / "intro.pdf"
    path.write_bytes(pdf)
    with pytest.raises(UnitError, match="Intro-Seiten"):
        _validate_intro_pages(path, {"shared_brief_pages": [1, 2, 3, 4, 5, 6]})


@patch("app.services.batch_import_runner.process_batch_import_unit")
@patch("app.services.batch_import_service._build_shared_brief")
@patch("app.core.db.session.SessionLocal")
@patch("app.services.batch_import_job._redis_client")
def test_run_batch_import_setup_failure_marks_failed(
    mock_redis_fn,
    mock_session_local,
    mock_brief,
    mock_process,
    tmp_path,
):
    store: dict[str, str] = {}
    client = MagicMock()
    client.setex = lambda key, _ttl, value: store.update({key: value})
    client.get = lambda key: store.get(key)
    mock_redis_fn.return_value = client

    mock_brief.side_effect = UnitError("Intro fehlt", "invalid_page_range")
    batch_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(_sample_pdf(tmp_path))
    from app.services.batch_import_job import create_batch_import_job

    create_batch_import_job(
        batch_id=batch_id,
        user_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        total=1,
        pdf_path=str(pdf_path),
        units=[{"title": "A", "page_from": 1, "page_to": 2, "generate_status": "pending"}],
    )
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    mock_session_local.return_value = db

    run_batch_import(batch_id, str(user.id))

    mock_process.assert_not_called()
    from app.services.batch_import_job import get_batch_import_job

    job = get_batch_import_job(batch_id)
    assert job is not None
    assert job["status"] == "failed"
