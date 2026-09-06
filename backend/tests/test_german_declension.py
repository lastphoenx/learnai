import pytest

from app.core.german_declension import (
    decline,
    decline_noun,
    expected_blank_answers,
    normalize_gender,
    parse_grammar_blanks,
    verify_cloze_answer,
)


@pytest.mark.parametrize(
    "case,gender,number,determiner_type,stem,expected_suffix",
    [
        ("nom", "masc", "sg", "der-word", "d", "er"),
        ("gen", "masc", "sg", "der-word", "d", "es"),
        ("dat", "masc", "sg", "der-word", "d", "em"),
        ("acc", "masc", "sg", "der-word", "d", "en"),
        ("nom", "fem", "sg", "der-word", "d", "e"),
        ("gen", "fem", "sg", "der-word", "d", "er"),
        ("nom", "neut", "sg", "der-word", "d", "es"),
        ("gen", "neut", "sg", "der-word", "d", "es"),
        ("nom", "masc", "sg", "ein-word", "ein", ""),
        ("gen", "neut", "sg", "ein-word", "ein", "es"),
        ("acc", "neut", "sg", "ein-word", "ein", ""),
    ],
)
def test_determiner_suffixes(case, gender, number, determiner_type, stem, expected_suffix):
    from app.core.german_declension import _decline_determiner

    full = _decline_determiner(
        determiner_type=determiner_type,
        determiner_stem=stem,
        case=case,
        gender=gender,
        number=number,
    )
    assert full == f"{stem}{expected_suffix}"


def test_decline_full_phrase_genitiv_neutrum():
    result = decline(
        lemma="Spiel",
        gender="neut",
        number="sg",
        case="gen",
        determiner_type="ein-word",
        determiner_stem="ein",
        adjective_stem="verloren",
    )
    assert result == {
        "determiner": "eines",
        "adjective": "verlorenen",
        "noun": "Spiels",
    }


def test_weak_masculine_accusative():
    assert decline_noun(lemma="Mensch", gender="masc", number="sg", case="acc") == "Menschen"
    assert decline_noun(lemma="Affe", gender="masc", number="sg", case="acc") == "Affen"


def test_mixed_masculine_genitive():
    assert decline_noun(lemma="Name", gender="masc", number="sg", case="gen") == "Namens"


def test_material_infolge_eines_verlorenen_spiels():
    blanks = parse_grammar_blanks(
        [
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
    )
    assert verify_cloze_answer(blanks=blanks, given_answer="es|en|s")
    assert expected_blank_answers(blanks) == ["es", "en", "s"]


def test_material_infolge_der_kleinsten_beule():
    blanks = parse_grammar_blanks(
        [
            {
                "part": "ending",
                "case": "gen",
                "gender": "fem",
                "number": "sg",
                "determiner_type": "der-word",
                "determiner_stem": "d",
            },
            {
                "part": "ending",
                "case": "gen",
                "gender": "fem",
                "number": "sg",
                "adjective_stem": "kleinst",
                "determiner_type": "der-word",
            },
        ]
    )
    assert verify_cloze_answer(blanks=blanks, given_answer="er|en")


def test_material_jeder_schlechten_zeugnisnote():
    blanks = parse_grammar_blanks(
        [
            {
                "part": "ending",
                "case": "gen",
                "gender": "fem",
                "number": "sg",
                "determiner_type": "der-word",
                "determiner_stem": "jed",
            },
            {
                "part": "ending",
                "case": "gen",
                "gender": "fem",
                "number": "sg",
                "adjective_stem": "schlecht",
                "determiner_type": "der-word",
            },
        ]
    )
    assert verify_cloze_answer(blanks=blanks, given_answer="er|en")


def test_material_waehrend_des_essens():
    blanks = parse_grammar_blanks(
        [
            {
                "part": "ending",
                "case": "gen",
                "gender": "neut",
                "number": "sg",
                "determiner_type": "der-word",
                "determiner_stem": "d",
            },
            {
                "part": "ending",
                "case": "gen",
                "gender": "neut",
                "number": "sg",
                "lemma": "Essen",
            },
        ]
    )
    assert verify_cloze_answer(blanks=blanks, given_answer="es|s")


def test_material_waehrend_der_radionachrichten():
    blanks = parse_grammar_blanks(
        [
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
    )
    assert verify_cloze_answer(blanks=blanks, given_answer="er|")


def test_material_oberhalb_des_flusses():
    blanks = parse_grammar_blanks(
        [
            {
                "part": "ending",
                "case": "gen",
                "gender": "masc",
                "number": "sg",
                "determiner_type": "der-word",
                "determiner_stem": "d",
            },
            {
                "part": "ending",
                "case": "gen",
                "gender": "masc",
                "number": "sg",
                "lemma": "Fluss",
            },
        ]
    )
    assert verify_cloze_answer(blanks=blanks, given_answer="es|es")


def test_normalize_gender_accepts_prompt_synonyms():
    assert normalize_gender("männlich") == "masc"
    assert normalize_gender("Maskulinum") == "masc"
    assert normalize_gender("weiblich") == "fem"


def test_expected_blank_answers_combined_genitiv_endings():
    blanks = parse_grammar_blanks(
        [
            {
                "part": "ending",
                "case": "gen",
                "gender": "neut",
                "number": "sg",
                "determiner_type": "ein-word",
                "determiner_stem": "ein",
                "lemma": "Spiel",
                "adjective_stem": "verloren",
            }
        ]
    )
    assert expected_blank_answers(blanks) == ["es"]


def test_decline_logs_normalization_failure(caplog):
    import logging

    caplog.set_level(logging.WARNING)
    result = decline(
        lemma="Spiel",
        gender="INVALID",
        number="sg",
        case="gen",
        determiner_type="ein-word",
    )
    assert result == {"determiner": "", "adjective": "", "noun": ""}
    assert "decline_normalization_failed" in caplog.text
    assert "gender='INVALID'" in caplog.text
