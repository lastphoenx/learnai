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
    assert "task_catalog" in out


def test_effective_empty_profile_uses_catalog_fallback():
    out = effective_ai_config({})
    mixed = out["unit_generate"]["mixed"]
    assert mixed["provider"] == "ollama"
    assert "recommended" in mixed


def test_effective_uses_inheritance_when_fallback_prefs_given():
    child = {"by_task": {}}
    parent = {"by_task": {"mixed": {"provider": "openai", "model": "gpt-4o"}}}
    out = effective_ai_config(child, fallback_prefs=parent)
    assert out["tasks"]["mixed"]["provider"] == "openai"
    assert out["tasks"]["exam"]["provider"] == "ollama"
    assert out["tasks"]["mixed"]["source"] == "adult"


def test_effective_config_applies_unit_provider_override():
    """Ticket-Repro: leeres by_task, Override openai — Label und Provider müssen übereinstimmen."""
    from app.ai.effective import EffectiveAiContext

    ctx = EffectiveAiContext(has_unit_profile=True, unit_provider_override="openai")
    out = effective_ai_config({"by_task": {}}, fallback_prefs={"by_task": {}}, context=ctx)
    assert out["tasks"]["mixed"]["provider"] == "openai"
    assert out["tasks"]["mixed"]["source"] == "unit"


def test_effective_applies_unit_provider_override_to_mixed_only():
    from app.ai.effective import EffectiveAiContext

    child = {"by_task": {"mixed": {"provider": "ollama", "model": "qwen2.5:32b"}}}
    parent = {"by_task": {}}
    out = effective_ai_config(
        child,
        fallback_prefs=parent,
        context=EffectiveAiContext(
            has_unit_profile=True,
            child_label="Lena",
            unit_provider_override="openai",
        ),
    )
    mixed = out["tasks"]["mixed"]
    assert mixed["provider"] == "openai"
    assert mixed["source"] == "unit"
    assert "openai" in mixed["source_label"].lower()
    assert out["tasks"]["vision"]["source"] != "unit"
