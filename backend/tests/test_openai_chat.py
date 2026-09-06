"""OpenAI Chat-Parameter für GPT-5/o-Serie und Fehlerdetails."""

from app.ai.model_registry import _is_openai_vision
from app.ai.providers import _is_reasoning_family, _openai_chat, _openai_post
from app.ai.errors import LlmError


def test_openai_vision_list_includes_gpt5():
    assert _is_openai_vision("gpt-5.6-terra")
    assert _is_openai_vision("gpt-4o")
    assert not _is_openai_vision("tts-1")


def test_is_reasoning_family():
    assert _is_reasoning_family("gpt-5.6-terra")
    assert _is_reasoning_family("o3-mini")
    assert not _is_reasoning_family("gpt-4o")
    assert not _is_reasoning_family("gpt-4.1-mini")


def test_openai_chat_omits_temperature_for_gpt5_family(monkeypatch):
    monkeypatch.setattr("app.ai.providers.settings.openai_api_key", "sk-test")
    captured: dict = {}

    def fake_post(body, timeout=90.0):
        captured.update(body)
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("app.ai.providers._openai_post", fake_post)
    _openai_chat("Test", model="gpt-5.6-terra", max_tokens=100)
    assert "temperature" not in captured
    assert captured.get("max_completion_tokens") == 100
    assert "max_tokens" not in captured


def test_openai_chat_keeps_legacy_params_for_gpt4(monkeypatch):
    monkeypatch.setattr("app.ai.providers.settings.openai_api_key", "sk-test")
    captured: dict = {}

    def fake_post(body, timeout=90.0):
        captured.update(body)
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("app.ai.providers._openai_post", fake_post)
    _openai_chat("Test", model="gpt-4o", max_tokens=512)
    assert captured.get("temperature") == 0.3
    assert captured.get("max_tokens") == 512
    assert "max_completion_tokens" not in captured


def test_openai_post_includes_error_detail(monkeypatch):
    class FakeResponse:
        status_code = 400

        @staticmethod
        def json():
            return {"error": {"message": "Unsupported parameter: max_tokens"}}

        text = ""

    monkeypatch.setattr("app.ai.providers.settings.openai_api_key", "sk-test")
    monkeypatch.setattr(
        "app.ai.providers.httpx.post",
        lambda *args, **kwargs: FakeResponse(),
    )
    try:
        _openai_post({"model": "gpt-5.6-terra", "messages": []})
        assert False, "expected LlmError"
    except LlmError as exc:
        assert "max_tokens" in exc.message
        assert "400" in exc.message
