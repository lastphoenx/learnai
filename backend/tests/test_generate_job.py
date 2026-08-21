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
