from app.core.quiz_content_patches import parse_quiz_slot_ref


def test_parse_quiz_slot_ref():
    family, mod, q = parse_quiz_slot_ref("0036.02.07")
    assert family == "0036"
    assert mod == 2
    assert q == 7
