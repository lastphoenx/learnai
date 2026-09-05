from app.core.grammar_verify import repair_basiswissen_grammar, verify_basiswissen_grammar


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
