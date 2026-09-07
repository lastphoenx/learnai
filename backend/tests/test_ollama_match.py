from app.ai.ollama_match import first_ollama_hint, match_ollama_hints

INSTALLED = [
    "qwen2.5vl:72b",
    "qwen2.5vl:7b",
    "qwen2.5vl:32b",
    "qwen2.5vl:latest",
    "qwen2.5:32b",
]


def test_vision_hints_prefer_32b_for_accuracy():
    hints = ["qwen2.5vl:32b", "qwen2.5vl:7b", "qwen2.5vl:latest"]
    assert match_ollama_hints(hints, INSTALLED, limit=3) == [
        "qwen2.5vl:32b",
        "qwen2.5vl:7b",
        "qwen2.5vl:latest",
    ]
    assert first_ollama_hint(hints, INSTALLED) == "qwen2.5vl:32b"


def test_vision_catalog_matches_accuracy_first_policy():
    from app.ai.catalog import local_hints

    assert local_hints("vision")[:3] == ["qwen2.5vl:32b", "qwen2.5vl:7b", "qwen2.5vl:latest"]


def test_generic_hint_without_tag_not_used_for_vision():
    # Altes Verhalten: "qwen2.5vl" hätte 72b getroffen (Listenreihenfolge)
    hints = ["qwen2.5vl:7b", "qwen2.5vl:32b"]
    assert first_ollama_hint(hints, INSTALLED) == "qwen2.5vl:7b"
