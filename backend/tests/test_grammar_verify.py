from app.core.grammar_verify import repair_basiswissen_grammar, verify_basiswissen_grammar
from app.core.german_declension import cloze_answers_repairable, expected_blank_answers, parse_grammar_blanks


def test_repair_basiswissen_sets_answers_from_engine():
    basiswissen = {
        "focus_group": "german",
        "concepts": [{"id": "genitiv", "label": "Genitiv", "parts": [{"role": "case", "term": "Genitiv"}]}],
        "cloze_templates": [
            {
                "id": "spiel_gen",
                "concept_id": "genitiv",
                "sentence": "infolge ein___ verloren___ Spiel___",
                "answers": ["falsch", "falsch", "falsch"],
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
                            "adjective_stem": "verloren",
                            "determiner_type": "ein-word",
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
    }
    repaired = repair_basiswissen_grammar(basiswissen)
    assert repaired["cloze_templates"][0]["answers"] == ["es", "en", "s"]
    assert not verify_basiswissen_grammar(repaired)


def test_template_without_grammar_left_unchanged():
    basiswissen = {
        "focus_group": "german",
        "concepts": [],
        "cloze_templates": [
            {
                "id": "term",
                "sentence": "Der Nominativ ist der ___ Fall.",
                "answers": ["erste"],
            }
        ],
    }
    repaired = repair_basiswissen_grammar(basiswissen)
    assert repaired["cloze_templates"][0]["answers"] == ["erste"]


def test_repair_basiswissen_genitiv_plural_empty_ending_passes():
    basiswissen = {
        "focus_group": "german",
        "concepts": [],
        "cloze_templates": [
            {
                "id": "genitiv_plural",
                "concept_id": "genitiv",
                "sentence": "während der Radionachricht___",
                "answers": ["falsch"],
                "grammar": {
                    "blanks": [
                        {
                            "part": "ending",
                            "case": "gen",
                            "gender": "fem",
                            "number": "pl",
                            "determiner_type": "der-word",
                            "determiner_stem": "d",
                        },
                        {
                            "part": "ending",
                            "case": "gen",
                            "gender": "fem",
                            "number": "pl",
                            "lemma": "Radionachricht",
                        },
                    ]
                },
            }
        ],
    }
    repaired = repair_basiswissen_grammar(basiswissen)
    assert len(repaired["cloze_templates"]) == 1
    assert repaired["cloze_templates"][0]["answers"] == ["er", ""]
    assert not verify_basiswissen_grammar(repaired)


def test_cloze_answers_repairable_rejects_empty_when_expected_not():
    blanks = parse_grammar_blanks(
        [
            {
                "part": "word",
                "case": "gen",
                "gender": "neut",
                "number": "sg",
                "lemma": "Spiel",
            }
        ]
    )
    ok, reason = cloze_answers_repairable(blanks, [""])
    assert ok is False
    assert reason is not None
    assert "Spiels" in reason or "alle Antworten leer" in reason
