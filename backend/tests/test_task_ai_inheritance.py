"""Tests für zweistufige KI-Einstellungs-Vererbung (Kind → Erwachsener → Katalog)."""

from app.ai.catalog import (
    effective_prefs_for_task,
    has_explicit_task_setting,
    resolve_task_ai_for_unit,
)


def test_has_explicit_task_setting_requires_provider():
    assert not has_explicit_task_setting({"by_task": {"mixed": {"provider": "", "model": ""}}}, "mixed")
    assert has_explicit_task_setting({"by_task": {"mixed": {"provider": "openai", "model": "gpt-4o"}}}, "mixed")


def test_quality_task_falls_back_to_acting_adult_settings():
    child = {"llm_provider": "ollama", "llm_model": "qwen2.5:7b", "by_task": {}}
    parent = {
        "by_task": {
            "mixed": {"provider": "openai", "model": "gpt-5.6-terra"},
        },
    }
    provider, model = resolve_task_ai_for_unit(child, parent, "mixed")
    assert provider == "openai"
    assert model == "gpt-5.6-terra"


def test_quality_task_uses_child_when_explicit():
    child = {
        "by_task": {
            "mixed": {"provider": "ollama", "model": "qwen2.5:32b"},
        },
    }
    parent = {
        "by_task": {
            "mixed": {"provider": "openai", "model": "gpt-5.6-terra"},
        },
    }
    provider, model = resolve_task_ai_for_unit(child, parent, "mixed")
    assert provider == "ollama"
    assert model == "qwen2.5:32b"


def test_sensitive_task_ignores_acting_adult_settings():
    child = {"by_task": {}}
    parent = {
        "by_task": {
            "exam": {"provider": "openai", "model": "gpt-4o"},
            "exam_analysis": {"provider": "openai", "model": "gpt-4o"},
        },
    }
    exam_provider, _ = resolve_task_ai_for_unit(child, parent, "exam")
    analysis_provider, _ = resolve_task_ai_for_unit(child, parent, "exam_analysis")
    assert exam_provider == "ollama"
    assert analysis_provider == "ollama"


def test_effective_prefs_for_task_sensitive_stays_on_target():
    child = {"by_task": {}}
    parent = {"by_task": {"mixed": {"provider": "openai", "model": "gpt-4o"}}}
    assert effective_prefs_for_task(child, parent, "exam") is child
    assert effective_prefs_for_task(child, parent, "mixed") is parent
