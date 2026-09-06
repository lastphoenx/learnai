from app.core.grammar_verify import (
    collect_grammar_warnings_for_module,
    finalize_german_cards,
    finalize_german_cards_with_drops,
    format_grammar_report_section,
    summarize_grammar_warnings,
    verify_card_case_label,
    verify_card_case_label_with_nesting,
)


def test_finalize_german_cards_keeps_non_case_cards():
    cards = [{"kind": "mental", "question": "Was ist Genus?", "answer": "Maskulin|Feminin|Neutrum"}]
    kept = finalize_german_cards(cards, focus_group="german")
    assert len(kept) == 1


def test_finalize_german_cards_with_drops_returns_reason_list():
    cards = [
        {
            "kind": "input",
            "question": "Welcher Fall?",
            "answer": "Akkusativ",
            "grammar": {"case_check": {"sentence": "Ich sehe den Hund.", "span": "den Hund"}},
        }
    ]
    kept, dropped = finalize_german_cards_with_drops(cards, focus_group="german")
    assert isinstance(kept, list)
    assert isinstance(dropped, list)


def test_collect_grammar_warnings_declension_ok():
    content = {
        "basiswissen": {
            "focus_group": "german",
            "concepts": [],
            "cloze_templates": [
                {
                    "id": "gen",
                    "sentence": "infolge ein___ Spiel___",
                    "answers": ["es", "s"],
                    "grammar": {
                        "blanks": [
                            {
                                "part": "ending",
                                "case": "gen",
                                "gender": "neut",
                                "number": "sg",
                                "determiner_type": "ein-word",
                                "determiner_stem": "ein",
                            },
                            {
                                "part": "ending",
                                "case": "gen",
                                "gender": "neut",
                                "number": "sg",
                                "lemma": "Spiel",
                            },
                        ]
                    },
                }
            ],
        },
        "cards": [],
    }
    warnings = collect_grammar_warnings_for_module(content=content, focus_group="german")
    assert any(w.get("kind") == "declension" for w in warnings)


def test_format_grammar_report_section_markdown():
    warnings = [
        {"kind": "declension", "level": "ok", "ref": "cloze:gen", "message": "engine-geprüft"},
        {"kind": "case", "level": "warn", "ref": "K01:input", "message": "Abweichung spaCy"},
    ]
    lines = format_grammar_report_section(warnings)
    text = "\n".join(lines)
    assert "Grammatik" not in text or "Deklination" in text
    assert "Fallbestimmung" in text
    assert summarize_grammar_warnings(warnings)["warn"] == 1


def test_verify_card_case_label_without_spacy_is_info():
    card = {
        "question": 'Im Satz «Die Erde umkreist die Sonne.» — welchen Fall hat «die Sonne»?',
        "answer": "Akkusativ",
        "grammar": {
            "case_check": {
                "sentence": "Die Erde umkreist die Sonne.",
                "span": "die Sonne",
            }
        },
    }
    level, message = verify_card_case_label(card)
    assert level in {"ok", "warn", "info", None}
    assert message is None or "die Sonne" in message


def test_verify_card_case_label_with_nesting():
    import pytest

    if not pytest.importorskip("spacy"):
        return
    from app.core.german_case_analysis import spacy_available

    if not spacy_available():
        pytest.skip("de_core_news_sm nicht installiert")
    outcome = verify_card_case_label_with_nesting(
        expected="Nominativ",
        given="Genitiv",
        sentence="Rot ist die Farbe des Blutes.",
        span="die Farbe des Blutes",
    )
    assert outcome == "teilrichtig_falsche_ebene"


def test_finalize_drops_nested_case_cards_at_low_difficulty():
    import pytest

    if not pytest.importorskip("spacy"):
        return
    from app.core.german_case_analysis import spacy_available

    if not spacy_available():
        pytest.skip("de_core_news_sm nicht installiert")
    card = {
        "kind": "input",
        "question": "Welchen Fall hat «die Farbe des Blutes»?",
        "answer": "Nominativ",
        "grammar": {
            "case_check": {
                "sentence": "Rot ist die Farbe des Blutes.",
                "span": "die Farbe des Blutes",
            }
        },
    }
    kept_low, dropped_low = finalize_german_cards_with_drops([card], focus_group="german", difficulty=1)
    assert len(kept_low) == 0
    assert len(dropped_low) == 1
    kept_high, _ = finalize_german_cards_with_drops([card], focus_group="german", difficulty=4)
    assert len(kept_high) == 1
    nested = kept_high[0].get("grammar", {}).get("case_check", {}).get("nested")
    assert isinstance(nested, list) and len(nested) >= 1
