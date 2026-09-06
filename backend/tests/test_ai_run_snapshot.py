"""Tests für KI-Herkunft und Generierungs-Snapshot."""

from app.ai.effective import EffectiveAiContext, effective_ai_config, task_setting_source
from app.services.ai_run_snapshot import build_ai_run_snapshot, last_ai_run_from_recon, resolve_generation_ai_tasks


def test_task_setting_source_child_explicit():
    source, label = task_setting_source(
        target_prefs={"by_task": {"mixed": {"provider": "openai", "model": "gpt-4o"}}},
        fallback_prefs={"by_task": {"mixed": {"provider": "ollama", "model": "qwen"}}},
        task_key="mixed",
        ctx=EffectiveAiContext(has_unit_profile=True, child_label="Lena", adult_label="Eltern"),
    )
    assert source == "child"
    assert "Lena" in label


def test_task_setting_source_adult_inherited():
    source, label = task_setting_source(
        target_prefs={"by_task": {}},
        fallback_prefs={"by_task": {"mixed": {"provider": "openai", "model": "gpt-5.6-terra"}}},
        task_key="mixed",
        ctx=EffectiveAiContext(has_unit_profile=True, child_label="Lena", adult_label="Eltern"),
    )
    assert source == "adult"
    assert "Eltern" in label


def test_effective_ai_config_includes_source():
    child = {"by_task": {}}
    parent = {"by_task": {"mixed": {"provider": "openai", "model": "gpt-4o"}}}
    out = effective_ai_config(
        child,
        fallback_prefs=parent,
        context=EffectiveAiContext(has_unit_profile=True, child_label="Lena", adult_label="Eltern"),
    )
    mixed = out["tasks"]["mixed"]
    assert mixed["source"] == "adult"
    assert mixed["source_label"]
    assert out["inheritance"]["child_label"] == "Lena"


def test_build_ai_run_snapshot():
    snap = build_ai_run_snapshot(
        tasks={"mixed": {"provider": "openai", "model": "gpt-4o"}, "vision": {"provider": "openai", "model": "gpt-4o"}},
        stats={"modules": 6, "cards": 50},
        triggered_by="user-1",
    )
    assert snap["tasks"]["mixed"]["model"] == "gpt-4o"
    assert snap["stats"]["cards"] == 50
    assert snap["finished_at"]


def test_last_ai_run_from_recon():
    recon = {"last_ai_run": {"tasks": {"mixed": {"provider": "openai", "model": "gpt-4o"}}}}
    assert last_ai_run_from_recon(recon) is not None
    assert last_ai_run_from_recon({}) is None


def test_resolve_generation_ai_tasks_includes_vision_with_sources():
    tasks = resolve_generation_ai_tasks({}, None, "interactive", source_count=3)
    assert "mixed" in tasks
    assert "vision" in tasks
