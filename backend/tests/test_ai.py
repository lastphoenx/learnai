from app.ai.errors import LlmError
from app.ai.generate import _validate_modules
from app.ai.providers import parse_json_object
from app.ai.validators.interactive import validate_interactive_modules


def test_parse_json_object_plain():
    data = parse_json_object('{"modules":[{"title":"A"}]}')
    assert data["modules"][0]["title"] == "A"


def test_parse_json_object_fenced():
    data = parse_json_object('Hier:\n```json\n{"modules":[{"title":"B"}]}\n```\n')
    assert data["modules"][0]["title"] == "B"


def test_parse_json_object_ignores_ascii_fence_inside_json():
    raw = """{
  "questions": [{
    "q": "0.45 + 0.60",
    "options": ["1.05", "1.15", "0.15", "10.5"],
    "answer": 0,
    "explanation": "Schriftlich:\\n```\\n   0.45\\n+  0.60\\n------\\n   1.05\\n```"
  }]
}"""
    data = parse_json_object(raw)
    assert data["questions"][0]["q"] == "0.45 + 0.60"
    assert "1.05" in data["questions"][0]["explanation"]


def test_parse_json_object_trailing_commas():
    data = parse_json_object('{"questions":[{"q":"1+1","options":["1","2","3","4"],}],}')
    assert data["questions"][0]["q"] == "1+1"


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


def test_validate_interactive_respects_posten_compact_targets():
    modules = []
    for i in range(4):
        modules.append(
            {
                "title": f"Bereich {i}",
                "content": {
                    "cards": [
                        {"question": f"Frage {i}-{j}?", "answer": f"Antwort {i}-{j}."}
                        for j in range(3)
                    ],
                    "knowledge": [{"title": "T", "text": "Wissen"}],
                },
                "quiz": {
                    "questions": [
                        {
                            "q": f"Quiz {i}-{j}?",
                            "options": ["A", "B", "C", "D"],
                            "answer": 0,
                        }
                        for j in range(2)
                    ]
                },
            }
        )
    validate_interactive_modules(modules, min_cards=12, min_questions=8)
    try:
        validate_interactive_modules(modules, min_cards=30, min_questions=30)
        assert False, "expected LlmError"
    except LlmError as exc:
        assert "Zu wenige Lernkarten (12, mindestens 30)" in exc.message


def test_validate_modules_rejects_thin_blocks():
    thin = [{"title": "A", "content": {"text": "Kurz."}, "quiz": {"questions": []}}]
    try:
        _validate_modules(thin, task="mixed")
        assert False, "expected LlmError"
    except LlmError as exc:
        assert exc.code == "thin_content"

