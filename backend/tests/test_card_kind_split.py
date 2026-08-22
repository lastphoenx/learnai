from app.ai.generate_interactive import _split_card_kinds


def test_split_card_kinds_math_focus_keeps_mental_share():
    merk, mental, input_cards = _split_card_kinds(30, math_focus="decimals")
    assert mental >= 8
    assert merk + mental + input_cards == 30


def test_split_card_kinds_without_math_focus_reduces_mental():
    merk, mental, input_cards = _split_card_kinds(30, math_focus=None)
    assert mental <= 5
    assert input_cards > mental
    assert merk + mental + input_cards == 30
