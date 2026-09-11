from app.core.trainer_cards import count_trainer_card_kinds, is_term_trainer_card


def test_is_term_trainer_card_excludes_input_cloze():
    assert not is_term_trainer_card(
        {"kind": "input", "card_role": "cloze", "answer_type": "cloze"},
    )
    assert is_term_trainer_card({"kind": "mental", "card_role": "term"})


def test_count_trainer_card_kinds_partitions_all():
    cards = [
        {"kind": "merk"},
        {"kind": "mental"},
        {"kind": "mental", "card_role": "term"},
        {"kind": "input"},
        {"kind": "input", "card_role": "cloze"},
    ]
    counts = count_trainer_card_kinds(cards)
    assert counts["merk"] == 1
    assert counts["mental"] == 2
    assert counts["input"] == 2
    assert counts["term"] == 1
    assert counts["all"] == 5
    assert counts["merk"] + counts["mental"] + counts["input"] == counts["all"]
