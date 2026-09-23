from app.ai.catalog import resolve_reasoning_effort


def test_resolve_reasoning_effort_by_task():
    prefs = {
        "by_task": {"mixed": {"provider": "openai", "model": "gpt-5.6-luna", "reasoning_effort": "high"}},
    }
    assert resolve_reasoning_effort(prefs, "mixed", "gpt-5.6-luna") == "high"
    assert resolve_reasoning_effort(prefs, "quiz", "gpt-5.6-luna") is None


def test_resolve_reasoning_effort_fallback():
    prefs = {"llm_reasoning_effort": "medium", "by_task": {}}
    assert resolve_reasoning_effort(prefs, "mixed", "gpt-5.6-luna") == "medium"
    assert resolve_reasoning_effort(prefs, "mixed", "gpt-4o") is None
