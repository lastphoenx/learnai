from app.ai.prompts.interactive import SOURCE_RULES, TYPED_CARDS_SYSTEM


def test_typed_cards_system_is_subject_neutral():
    assert "Kopf-Rechn" not in TYPED_CARDS_SYSTEM
    assert "answer_type" in TYPED_CARDS_SYSTEM
    assert "short_text" in TYPED_CARDS_SYSTEM
    assert "cloze" in TYPED_CARDS_SYSTEM


def test_typed_cards_require_result_and_variants():
    assert "Endergebnis" in TYPED_CARDS_SYSTEM
    assert "Variante 1 (Aus dem Heft)" in TYPED_CARDS_SYSTEM
    assert "Variante 2 (Alternativer Weg)" in TYPED_CARDS_SYSTEM


def test_source_rules_use_loesungswege():
    assert "Lösungswege" in SOURCE_RULES
    assert "Rechenwege" not in SOURCE_RULES
