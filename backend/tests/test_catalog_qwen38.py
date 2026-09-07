from app.ai.catalog import TASK_CATALOG, local_hints


def test_catalog_lists_qwen38_27b_for_generation_tasks():
    mixed = next(item for item in TASK_CATALOG if item["key"] == "mixed")
    assert mixed["local"][0] == "qwen3.8:27b"
    hints = local_hints("mixed")
    assert hints[0] == "qwen3.8:27b"
