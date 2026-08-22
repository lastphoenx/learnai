from app.core.method_taxonomy import classify_method, method_label, normalize_method_id


def test_method_label():
    assert method_label("written") == "Schriftlich"


def test_classify_method_choice_question():
    assert classify_method("Welches Vorgehen passt zu dieser Aufgabe?") == "method_choice"
