from app.ai.prompts.interactive import SOURCE_RULES, TYPED_CARDS_SYSTEM


def test_typed_cards_system_is_subject_neutral():
    assert "Kopf-Rechn" not in TYPED_CARDS_SYSTEM
    assert "answer_type" in TYPED_CARDS_SYSTEM
    assert "short_text" in TYPED_CARDS_SYSTEM
    assert "cloze" in TYPED_CARDS_SYSTEM


def test_source_rules_use_loesungswege():
    assert "Lösungswege" in SOURCE_RULES
    assert "Rechenwege" not in SOURCE_RULES
