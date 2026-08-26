from app.ai.extract import STT_PROVIDERS, effective_stt_provider


def test_stt_providers_set():
    assert "browser" in STT_PROVIDERS
    assert "local" in STT_PROVIDERS


def test_effective_stt_browser_falls_back_to_local_when_whisper(monkeypatch):
    monkeypatch.setattr("app.ai.extract.settings.whisper_url", "http://127.0.0.1:9000")
    assert effective_stt_provider({"stt_provider": "browser"}) == "local"


def test_effective_stt_respects_openai():
    assert effective_stt_provider({"stt_provider": "openai"}) == "openai"


def test_warmup_stt_skips_browser():
    from app.ai.extract import warmup_stt

    assert warmup_stt("browser") == {"ok": True, "provider": "browser"}


def test_silent_wav_is_valid_riff():
    from app.ai.extract import _silent_wav_bytes

    data = _silent_wav_bytes()
    assert data.startswith(b"RIFF")
    assert b"WAVE" in data[:16]
    assert len(data) > 44
