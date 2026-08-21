from app.ai.extract import STT_PROVIDERS, effective_stt_provider


def test_stt_providers_set():
    assert "browser" in STT_PROVIDERS
    assert "local" in STT_PROVIDERS


def test_effective_stt_browser_falls_back_to_local_when_whisper(monkeypatch):
    monkeypatch.setattr("app.ai.extract.settings.whisper_url", "http://127.0.0.1:9000")
    assert effective_stt_provider({"stt_provider": "browser"}) == "local"


def test_effective_stt_respects_openai():
    assert effective_stt_provider({"stt_provider": "openai"}) == "openai"


def test_effective_stt_respects_local():
    assert effective_stt_provider({"stt_provider": "local"}) == "local"
