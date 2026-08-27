"""Gemeinsame Prüfung und Reparatur von Lösungswegen (Quiz, Karten, Wissen)."""

from __future__ import annotations

import re

from app.ai.source_pedagogy import equation_is_arithmetically_ok
from app.core.quiz_explanation import (
    build_worked_solution,
    collapse_duplicate_variants,
    distinct_variant_count,
    enrich_quiz_explanation,
    explanation_is_weak,
    explanation_uses_invalid_times_table,
    merge_worked_variants,
    parse_arithmetic_operands,
    times_table_ok,
)
from app.core.quiz_numeric import parse_quiz_numeric

_EQ = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*([+\-·×*:÷/x])\s*(-?\d+(?:[.,]\d+)?)\s*=\s*(-?\d+(?:[.,]\d+)?)"
)
_REIHE_CLAIM = re.compile(r"(\d+)\s*er-reihe", re.I)
_AUS_DER_EMPTY = re.compile(r"aus der\s*:?\s*", re.I)


def _drop_false_equations(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        if equation_is_arithmetically_ok(match.group(0)) is False:
            return ""
        return match.group(0)

    cleaned = _EQ.sub(repl, str(text or ""))
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned.strip()


def _scrub_invalid_reihe(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        if times_table_ok(int(match.group(1))):
            return match.group(0)
        return ""

    cleaned = _REIHE_CLAIM.sub(repl, str(text or ""))
    cleaned = _AUS_DER_EMPTY.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned.strip()


def enrich_knowledge_text(text: str) -> str:
    """Wissens-Hub: falsche Gleichungen und N-er-Reihe für N>12 entfernen."""
    original = str(text or "").strip()
    if not original:
        return original
    cleaned = _drop_false_equations(original)
    if explanation_uses_invalid_times_table(cleaned):
        cleaned = _scrub_invalid_reihe(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or original


def enrich_knowledge_item(item: dict) -> dict:
    if not isinstance(item, dict):
        return item
    out = dict(item)
    out["text"] = enrich_knowledge_text(str(item.get("text") or ""))
    return out


def enrich_card_answer(card: dict) -> str:
    """Merk/Mental: schwachen oder duplizierten Weg flicken. Input und Kurzresultat unverändert."""
    if not isinstance(card, dict):
        return ""
    question = str(card.get("question") or "")
    original = collapse_duplicate_variants(str(card.get("answer") or "").strip())
    kind = str(card.get("kind") or "").strip().lower()
    if kind == "input":
        return original
    if parse_quiz_numeric(original) is not None and len(original) < 24:
        return original
    if not original:
        return original

    computable = parse_arithmetic_operands(question) is not None
    if not computable:
        return enrich_knowledge_text(original)

    worked = build_worked_solution(question)
    if explanation_is_weak(original, question):
        return worked or original
    if worked and distinct_variant_count(original) < 2:
        return merge_worked_variants(original, worked, question=question)
    return original


def enrich_card(card: dict) -> dict:
    if not isinstance(card, dict):
        return card
    out = dict(card)
    out["answer"] = enrich_card_answer(card)
    return out


def repair_generated_module(raw: dict) -> dict:
    """Persistenz: Quiz-, Karten- und Wissenstexte vor dem Speichern flicken."""
    if not isinstance(raw, dict):
        return raw
    out = dict(raw)
    content = dict(out.get("content") or {}) if isinstance(out.get("content"), dict) else {}
    quiz = dict(out.get("quiz") or {}) if isinstance(out.get("quiz"), dict) else {}

    cards = content.get("cards")
    if isinstance(cards, list):
        content["cards"] = [enrich_card(card) if isinstance(card, dict) else card for card in cards]

    knowledge = content.get("knowledge")
    if isinstance(knowledge, list):
        content["knowledge"] = [
            enrich_knowledge_item(item) if isinstance(item, dict) else item for item in knowledge
        ]

    questions = quiz.get("questions")
    if isinstance(questions, list):
        repaired_q = []
        for question in questions:
            if not isinstance(question, dict):
                repaired_q.append(question)
                continue
            item = dict(question)
            item["explanation"] = enrich_quiz_explanation(item)
            repaired_q.append(item)
        quiz["questions"] = repaired_q

    out["content"] = content
    out["quiz"] = quiz
    return out
