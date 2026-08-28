import json
from pathlib import Path

from app.core.answer_match import cloze_answers_match
from app.core.basiswissen import (
    derive_cloze_cards,
    derive_concept_quiz_questions,
    derive_mental_term_cards,
    enrich_module_with_basiswissen,
    merge_concept_questions,
    parse_basiswissen_payload,
    strip_basiswissen_derivatives,
)

SAMPLE_BASISWISSEN = {
    "basiswissen": {
        "schema_version": 1,
        "focus_group": "math",
        "concepts": [
            {
                "id": "multiplication_terms",
                "kind": "relation",
                "label": "Multiplikation",
                "parts": [
                    {"role": "factor", "term": "Faktor", "aliases": ["Faktor"]},
                    {"role": "factor", "term": "Faktor", "aliases": ["Faktor"]},
                    {"role": "product", "term": "Produkt", "aliases": ["Produkt"]},
                ],
                "pattern": "Faktor × Faktor = Produkt",
                "example": "3 × 4 = 12",
                "hint": "Beim Malnehmen heissen die beiden Zahlen Faktoren, das Ergebnis Produkt.",
            },
            {
                "id": "addition_terms",
                "kind": "relation",
                "label": "Addition",
                "parts": [
                    {"role": "summand", "term": "Summand"},
                    {"role": "summand", "term": "Summand"},
                    {"role": "sum", "term": "Summe"},
                ],
                "pattern": "Summand + Summand = Summe",
                "example": "3 + 4 = 7",
                "hint": "Beim Plus rechnen heissen die Zahlen Summanden.",
            },
        ],
        "cloze_templates": [
            {
                "id": "mul_product",
                "concept_id": "multiplication_terms",
                "sentence": "Bei der Multiplikation heisst das Ergebnis ___.",
                "answers": ["Produkt"],
                "blank_roles": ["product"],
            },
            {
                "id": "mul_factors",
                "concept_id": "multiplication_terms",
                "sentence": "___ × ___ = Produkt",
                "answers": ["Faktor", "Faktor"],
                "blank_roles": ["factor", "factor"],
            },
        ],
    }
}


def test_parse_basiswissen_payload():
    parsed = parse_basiswissen_payload(SAMPLE_BASISWISSEN, focus_group="math")
    assert parsed["focus_group"] == "math"
    assert len(parsed["concepts"]) == 2
    assert len(parsed["cloze_templates"]) == 2


def test_derive_cloze_cards_from_basiswissen():
    bw = parse_basiswissen_payload(SAMPLE_BASISWISSEN, focus_group="math")
    cards = derive_cloze_cards(bw)
    assert len(cards) == 2
    assert cards[0]["answer_type"] == "cloze"
    assert cards[0]["source"] == "basiswissen"
    assert "Produkt" in cards[0]["answer"]


def test_derive_mental_term_cards_dedupes_repeated_terms():
    bw = parse_basiswissen_payload(SAMPLE_BASISWISSEN, focus_group="math")
    cards = derive_mental_term_cards(bw)
    factor_cards = [c for c in cards if "Faktor" in c["question"]]
    assert len(factor_cards) == 1


def test_derive_concept_quiz_questions():
    bw = parse_basiswissen_payload(SAMPLE_BASISWISSEN, focus_group="math")
    questions = derive_concept_quiz_questions(bw, max_count=4)
    assert questions
    assert all(q.get("question_type") == "concept" for q in questions)
    assert all(len(q.get("options") or []) == 4 for q in questions)


def test_merge_concept_questions_replaces_calculation_slots():
    calc = [
        {"q": "Was ist 2+2?", "options": ["a", "b", "c", "d"], "answer": 0, "question_type": "calculation"},
        {"q": "Was ist 3+3?", "options": ["a", "b", "c", "d"], "answer": 0, "question_type": "calculation"},
    ]
    concept = [
        {"q": "Begriff?", "options": ["a", "b", "c", "d"], "answer": 1, "question_type": "concept"},
    ]
    merged = merge_concept_questions(calc, concept, max_ratio=0.5)
    assert merged[-1]["question_type"] == "concept"


def test_enrich_module_with_basiswissen_adds_cards_and_overview():
    bw = parse_basiswissen_payload(SAMPLE_BASISWISSEN, focus_group="math")
    content = {"knowledge": [{"title": "Regel", "text": "Text"}], "cards": []}
    quiz = {"questions": [{"q": "2+2?", "options": ["3", "4", "5", "6"], "answer": 1, "question_type": "calculation"}]}
    out_content, out_quiz = enrich_module_with_basiswissen(
        content=content,
        quiz=quiz,
        basiswissen=bw,
        question_count=3,
    )
    assert out_content.get("basiswissen")
    assert any("Fachbegriffe" in str(k.get("title")) for k in out_content["knowledge"])
    assert len(out_content["cards"]) >= 2
    assert any(q.get("question_type") == "concept" for q in out_quiz["questions"])


def test_cloze_answers_match_multiple_blanks():
    assert cloze_answers_match("Faktor|Faktor", "Faktor|Faktor")
    assert cloze_answers_match("Faktor|Faktor", "faktor|faktor")
    assert not cloze_answers_match("Faktor|Faktor", "Produkt|Faktor")


def test_strip_basiswissen_derivatives_removes_derived_content():
    content = {
        "knowledge": [
            {"title": "Fachbegriffe im Überblick", "text": "…"},
            {"title": "Regel", "text": "Text"},
        ],
        "cards": [
            {"question": "Normal", "source": "llm"},
            {"question": "Lücke", "source": "basiswissen", "card_role": "cloze"},
        ],
        "basiswissen": {"concepts": []},
    }
    quiz = {
        "questions": [
            {"q": "2+2?", "question_type": "calculation"},
            {"q": "Begriff?", "question_type": "concept"},
        ]
    }
    stripped_content, stripped_quiz = strip_basiswissen_derivatives(content, quiz)
    assert len(stripped_content["cards"]) == 1
    assert len(stripped_content["knowledge"]) == 1
    assert all(q.get("question_type") != "concept" for q in stripped_quiz["questions"])


def test_golden_fixture_math_arithmetic_terms():
    fixture_path = Path(__file__).parent / "fixtures" / "basiswissen" / "math_arithmetic_terms.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    bw = parse_basiswissen_payload(payload, focus_group="math")
    assert len(bw["concepts"]) >= 2
    assert derive_cloze_cards(bw)
    assert derive_concept_quiz_questions(bw, max_count=3)
