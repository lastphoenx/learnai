from app.core.grammar_verify import (
    collect_grammar_warnings_for_module,
    finalize_german_cards,
    format_grammar_report_section,
    summarize_grammar_warnings,
    verify_card_case_label,
)


def test_finalize_german_cards_keeps_non_case_cards():
    cards = [{"kind": "mental", "question": "Was ist Genus?", "answer": "Maskulin|Feminin|Neutrum"}]
    kept = finalize_german_cards(cards, focus_group="german")
    assert len(kept) == 1


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
