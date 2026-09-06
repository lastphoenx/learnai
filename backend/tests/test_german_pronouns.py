from app.core.german_pronouns import (
    ersatzprobe_example_is_useful,
    pronoun_distinguishes_case,
    structured_gender_and_case,
)
from app.core.german_pedagogy_verify import (
    finalize_german_pedagogy_digest,
    worked_example_is_coherent,
)


def test_neuter_pronoun_does_not_distinguish_nom_acc():
    assert not pronoun_distinguishes_case("neut", "nom", "acc")
    assert not pronoun_distinguishes_case("fem", "nom", "acc")
    assert pronoun_distinguishes_case("masc", "nom", "acc")
    assert pronoun_distinguishes_case("neut", "nom", "dat")


def test_ersatzprobe_neuter_es_with_grammar_is_not_useful():
    example = {
        "problem": "Der Hund jagt das Kaninchen.",
        "method_label": "Ersatzprobe",
        "steps": ["Der Hund jagt das Kaninchen. → Der Hund jagt es."],
        "grammar": {"gender": "neut", "case": "acc"},
    }
    assert not ersatzprobe_example_is_useful(example)
    assert not worked_example_is_coherent(example)


def test_ersatzprobe_masculine_ihn_is_useful():
    example = {
        "problem": "Der Hund jagt den Hasen.",
        "method_label": "Ersatzprobe",
        "steps": ["Der Hund jagt den Hasen. → Der Hund jagt ihn."],
        "grammar": {"gender": "masc", "case": "acc"},
    }
    assert ersatzprobe_example_is_useful(example)
    assert worked_example_is_coherent(example)


def test_ersatzprobe_without_grammar_is_not_blocked():
    """Konservativ: ohne strukturiertes Genus nicht raten."""
    example = {
        "problem": "Der Hund jagt das Kaninchen.",
        "method_label": "Ersatzprobe",
        "steps": ["Der Hund jagt das Kaninchen. → Der Hund jagt es."],
    }
    assert ersatzprobe_example_is_useful(example)
    assert worked_example_is_coherent(example)


def test_finalize_drops_ersatzprobe_worked_example_with_neuter_grammar():
    pedagogy = {
        "key_terms": [],
        "methods": [],
        "worked_examples": [
            {
                "problem": "Der Hund jagt das Kaninchen.",
                "method_label": "Ersatzprobe",
                "steps": ["Der Hund jagt das Kaninchen. → Der Hund jagt es."],
                "grammar": {"gender": "neut", "case": "acc"},
            },
            {
                "problem": "Der Hund jagt den Hasen.",
                "method_label": "Ersatzprobe",
                "steps": ["Der Hund jagt den Hasen. → Der Hund jagt ihn."],
                "grammar": {"gender": "masc", "case": "acc"},
            },
        ],
        "exercise_formats": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    repaired = finalize_german_pedagogy_digest(pedagogy, focus_group="german")
    assert len(repaired["worked_examples"]) == 1
    assert "Hasen" in repaired["worked_examples"][0]["problem"]


def test_finalize_clears_method_example_when_neuter_ersatzprobe():
    pedagogy = {
        "key_terms": [],
        "methods": [
            {
                "label": "Ersatzprobe",
                "when": "Fall bestimmen",
                "example": "Der Hund jagt das Kaninchen. (Ersatzprobe: Der Hund jagt es.)",
                "grammar": {"gender": "neut", "case": "acc"},
            }
        ],
        "worked_examples": [],
        "exercise_formats": [],
        "exercise_patterns": [],
        "teaching_notes": [],
    }
    repaired = finalize_german_pedagogy_digest(pedagogy, focus_group="german")
    assert repaired["methods"][0]["label"] == "Ersatzprobe"
    assert repaired["methods"][0]["example"] == ""


def test_structured_gender_from_blanks():
    gender, case = structured_gender_and_case(
        {
            "grammar": {
                "blanks": [
                    {
                        "part": "word",
                        "case": "acc",
                        "gender": "neut",
                        "number": "sg",
                        "lemma": "Kaninchen",
                    }
                ]
            }
        }
    )
    assert gender == "neut"
    assert case == "acc"
