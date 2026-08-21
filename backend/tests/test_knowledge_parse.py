from app.ai.generate_interactive import _parse_knowledge


def test_parse_knowledge_accepts_multiple_items():
    text = """{
        "knowledge": [
            {"title": "Regel", "text": "Komma unter Komma schreiben."},
            {"title": "Beispiel", "text": "3,2 + 4,8 = 8,0."},
            {"title": "Fehler", "text": "Dezimalstellen nicht vergessen."}
        ]
    }"""
    items = _parse_knowledge(text, fallback_focus="Fokus", category_name="Dezimalzahlen")
    assert len(items) == 3
    assert items[0]["title"] == "Regel"


def test_parse_knowledge_falls_back_to_focus():
    items = _parse_knowledge('{"knowledge": []}', fallback_focus="Dezimal verstehen.", category_name="Test")
    assert len(items) == 1
    assert items[0]["title"] == "Überblick"
    assert "Dezimal" in items[0]["text"]
