"""Tests für effective_ai_config."""

from app.ai.effective import effective_ai_config


def test_effective_uses_profile_by_task():
    prefs = {
        "llm_provider": "",
        "llm_model": "",
        "by_task": {
            "mixed": {"provider": "ollama", "model": "qwen2.5:32b"},
            "vision": {"provider": "ollama", "model": "qwen2.5vl:7b"},
        },
    }
    out = effective_ai_config(prefs)
    assert out["unit_generate"]["mixed"]["effective_model"] == "qwen2.5:32b"
    assert out["unit_generate"]["vision"]["effective_model"] == "qwen2.5vl:7b"
    assert out["env"]["ollama_vision_timeout_sec"] >= 600


def test_effective_empty_profile_has_env_fallback():
    out = effective_ai_config({})
    mixed = out["unit_generate"]["mixed"]
    assert mixed["provider"] == "ollama"
    assert mixed["effective_model"]  # from settings default qwen2.5:32b
