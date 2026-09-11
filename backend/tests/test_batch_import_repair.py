"""Tests für gezielte Batch-Reparatur."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.batch_import_repair import is_repairable_error, parse_repair_hint
from app.services.batch_import_service import repair_batch_import_units
from app.services.unit_service import UnitError


def _sample_pdf(tmp_path: Path) -> bytes:
    import pymupdf

    path = tmp_path / "heft.pdf"
    doc = pymupdf.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), "Seite 1")
        doc.save(str(path))
    finally:
        doc.close()
    return path.read_bytes()


def test_parse_repair_hint_card_answer():
    hint = parse_repair_hint("Lernkarte ohne Antwort (Bereich 4)")
    assert hint == {"kind": "card_answer", "area_index": 3}


def test_parse_repair_hint_quiz_count():
    hint = parse_repair_hint("Zu wenige Quizfragen (7, mindestens 8)")
    assert hint == {"kind": "quiz_count", "have": 7, "need": 8}


def test_is_repairable_error():
    assert is_repairable_error("Lernkarte ohne Antwort (Bereich 1)")
    assert is_repairable_error("Zu wenige Quizfragen (7, mindestens 8)")
    assert not is_repairable_error("Vision fehlgeschlagen")


@patch("app.tasks.batch_import.batch_import_task")
@patch("app.services.batch_import_job._redis_client")
def test_repair_batch_import_units_queues_repair_pending(mock_redis_fn, mock_task, tmp_path):
    store: dict[str, str] = {}
    client = MagicMock()
    client.setex = lambda key, _ttl, value: store.update({key: value})
    client.get = lambda key: store.get(key)
    mock_redis_fn.return_value = client
    mock_task.delay.return_value = MagicMock(id="celery-repair-1")

    batch_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(_sample_pdf(tmp_path))

    from app.services.batch_import_job import create_batch_import_job, update_batch_import_job

    create_batch_import_job(
        batch_id=batch_id,
        user_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        total=1,
        pdf_path=str(pdf_path),
        units=[
            {
                "title": "B",
                "page_from": 1,
                "page_to": 1,
                "generate_status": "failed",
                "unit_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "error": "Zu wenige Quizfragen (7, mindestens 8)",
            },
        ],
    )
    update_batch_import_job(batch_id, status="partial", payload={"default_preset": "posten_compact"})

    db = MagicMock()
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    user.is_admin = False

    job = repair_batch_import_units(db, user, batch_id, [0])
    assert job["status"] == "queued"
    assert job["units"][0]["generate_status"] == "repair_pending"
    assert job["units"][0]["unit_id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert job["units"][0]["error"] == "Zu wenige Quizfragen (7, mindestens 8)"
    mock_task.delay.assert_called_once_with(batch_id, str(user.id))


@patch("app.services.batch_import_job._redis_client")
def test_repair_batch_import_units_rejects_without_draft(mock_redis_fn):
    store: dict[str, str] = {}
    client = MagicMock()
    client.setex = lambda key, _ttl, value: store.update({key: value})
    client.get = lambda key: store.get(key)
    mock_redis_fn.return_value = client

    from app.services.batch_import_job import create_batch_import_job, update_batch_import_job

    batch_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    create_batch_import_job(
        batch_id=batch_id,
        user_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        total=1,
        pdf_path="/tmp/x.pdf",
        units=[
            {
                "title": "B",
                "page_from": 1,
                "page_to": 1,
                "generate_status": "failed",
                "error": "Zu wenige Quizfragen (7, mindestens 8)",
            },
        ],
    )
    update_batch_import_job(batch_id, status="partial")

    db = MagicMock()
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    user.is_admin = False

    with pytest.raises(UnitError, match="Entwurf"):
        repair_batch_import_units(db, user, batch_id, [0])
