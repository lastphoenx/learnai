"""Fachneutrale Antwortabgleich-Logik für Eingabekarten."""

from __future__ import annotations

import re
import unicodedata

from app.core.quiz_numeric import parse_quiz_numeric

_ANSWER_TYPES = frozenset({"numeric", "short_text", "cloze", "text"})
_CLOZE_MARKERS = ("___", "…", "...")


def normalize_text_answer(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    raw = re.sub(r"[^\w\s|]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def answer_variants(expected: str) -> list[str]:
    parts = [p.strip() for p in str(expected or "").split("|") if p.strip()]
    if not parts:
        return []
    variants: list[str] = []
    for part in parts:
        normalized = normalize_text_answer(part)
        if normalized and normalized not in variants:
            variants.append(normalized)
    return variants


def infer_answer_type(*, question: str, answer: str, raw_type: str | None = None) -> str:
    explicit = str(raw_type or "").strip().lower()
    if explicit in _ANSWER_TYPES:
        return "numeric" if explicit in {"numeric", "number"} else ("short_text" if explicit == "text" else explicit)
    if any(marker in str(question or "") for marker in _CLOZE_MARKERS):
        return "cloze"
    if parse_quiz_numeric(answer) is not None and re.fullmatch(
        r"[\d\s.,+\-/%]+",
        str(answer or "").strip(),
    ):
        return "numeric"
    return "short_text"


def text_answers_match(expected: str, user_answer: str) -> bool:
    user_norm = normalize_text_answer(user_answer)
    if not user_norm:
        return False
    variants = answer_variants(expected)
    if not variants:
        return user_norm == normalize_text_answer(expected)
    for variant in variants:
        if variant == user_norm:
            return True
        if len(variant) >= 3 and len(user_norm) >= 3:
            if variant.startswith(user_norm) or user_norm.startswith(variant):
                return True
    return False


def cloze_answers_match(expected: str, user_answer: str) -> bool:
    """Mehrere Lücken: erwartete Antworten mit | getrennt, gleiche Reihenfolge."""
    expected_parts = [p.strip() for p in str(expected or "").split("|") if p.strip()]
    user_parts = [p.strip() for p in str(user_answer or "").split("|") if p.strip()]
    if not expected_parts:
        return text_answers_match(expected, user_answer)
    if len(user_parts) != len(expected_parts):
        if len(expected_parts) == 1:
            return text_answers_match(expected_parts[0], user_answer)
        return False
    return all(text_answers_match(exp, usr) for exp, usr in zip(expected_parts, user_parts))


def answers_match(expected: str, user_answer: str, *, answer_type: str | None = None) -> bool:
    kind = str(answer_type or "").strip().lower() or infer_answer_type(question="", answer=expected)
    if kind == "numeric":
        exp_num = parse_quiz_numeric(expected)
        usr_num = parse_quiz_numeric(user_answer)
        if exp_num is not None and usr_num is not None:
            return abs(exp_num - usr_num) < 1e-6
    if kind == "cloze" and "|" in str(expected or ""):
        return cloze_answers_match(expected, user_answer)
    return text_answers_match(expected, user_answer)
