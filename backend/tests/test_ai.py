from app.ai.errors import LlmError
from app.ai.generate import _validate_modules
from app.ai.providers import parse_json_object


def test_parse_json_object_plain():
    data = parse_json_object('{"modules":[{"title":"A"}]}')
    assert data["modules"][0]["title"] == "A"


def test_parse_json_object_fenced():
    data = parse_json_object('Hier:\n```json\n{"modules":[{"title":"B"}]}\n```\n')
    assert data["modules"][0]["title"] == "B"


def test_parse_json_object_latex_escapes():
    raw = """{
  "modules": [
    {
      "title": "Rechnen im Kopf",
      "content": {"text": "Zum Beispiel: \\(0.5 + 0.25 = 0.75\\)."},
      "quiz": {"questions": []}
    }
  ]
}"""
    data = parse_json_object(raw)
    assert len(data["modules"]) == 1
    assert "(0.5" in data["modules"][0]["content"]["text"]


def test_validate_modules_rejects_thin_blocks():
    thin = [{"title": "A", "content": {"text": "Kurz."}, "quiz": {"questions": []}}]
    try:
        _validate_modules(thin, task="mixed")
        assert False, "expected LlmError"
    except LlmError as exc:
        assert exc.code == "thin_content"

