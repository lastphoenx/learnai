"""Fortschritts-Callback für KI-Generierung."""

from unittest.mock import patch

from app.services.generate_job import make_progress_callback


@patch("app.services.generate_job.set_generate_job")
def test_progress_done_custom_message_not_duplicated(mock_set):
    progress = make_progress_callback("unit-1", "user-1")
    progress("done", message="Lernblöcke wurden erstellt.", cards=50, questions=45)

    mock_set.assert_called_once()
    _, kwargs = mock_set.call_args
    assert kwargs["message"] == "Lernblöcke wurden erstellt."
    assert kwargs["cards"] == 50
    assert kwargs["questions"] == 45


@patch("app.services.generate_job.set_generate_job")
def test_progress_failed_uses_error_message(mock_set):
    progress = make_progress_callback("unit-1", "user-1")
    progress("failed", error="Ollama timeout")

    mock_set.assert_called_once()
    _, kwargs = mock_set.call_args
    assert kwargs["status"] == "failed"
    assert kwargs["message"] == "Ollama timeout"
    assert kwargs["error"] == "Ollama timeout"


@patch("app.services.generate_job.set_generate_job")
def test_progress_partial_status(mock_set):
    progress = make_progress_callback("unit-1", "user-1")
    progress("partial", message="Entwurf gespeichert (5 Bereiche).", modules=5)

    mock_set.assert_called_once()
    _, kwargs = mock_set.call_args
    assert kwargs["status"] == "partial"
    assert kwargs["modules"] == 5


def test_snapshot_last_generate_terminal_only():
    from app.services.generate_job import snapshot_last_generate

    assert snapshot_last_generate({"status": "running"}) is None
    snap = snapshot_last_generate(
        {
            "status": "partial",
            "message": "Entwurf gespeichert",
            "updated_at": "2026-08-27T11:59:52+00:00",
            "modules": 6,
        }
    )
    assert snap is not None
    assert snap["status"] == "partial"
    assert snap["modules"] == 6
    assert snap["updated_at"] == "2026-08-27T11:59:52+00:00"


def test_queued_job_resets_started_at(monkeypatch):
    from app.services import generate_job as gj

    stored = {
        "status": "partial",
        "started_at": "2026-08-26T19:40:45+00:00",
        "modules": 6,
        "cards": 49,
        "index": 1,
    }
    monkeypatch.setattr(gj, "get_generate_job", lambda _uid: stored)
    written = {}

    class _FakeRedis:
        def setex(self, key, ttl, value):
            written["payload"] = value

    monkeypatch.setattr(gj, "_redis_client", lambda: _FakeRedis())
    payload = gj.set_generate_job("unit-1", user_id="user-1", status="queued", stage="queued")
    assert payload["status"] == "queued"
    assert payload["started_at"] != "2026-08-26T19:40:45+00:00"
    assert "modules" not in payload
    assert "index" not in payload


def test_should_salvage_only_after_this_run_saved():
    from app.tasks.generate import should_salvage_partial

    assert should_salvage_partial(6, "saving") is True
    assert should_salvage_partial(6, "category") is False
    assert should_salvage_partial(6, "planning") is False
    assert should_salvage_partial(3, "saving") is False
