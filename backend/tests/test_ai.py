from app.ai.providers import parse_json_object


def test_parse_json_object_plain():
    data = parse_json_object('{"modules":[{"title":"A"}]}')
    assert data["modules"][0]["title"] == "A"


def test_parse_json_object_fenced():
    data = parse_json_object('Hier:\n```json\n{"modules":[{"title":"B"}]}\n```\n')
    assert data["modules"][0]["title"] == "B"
