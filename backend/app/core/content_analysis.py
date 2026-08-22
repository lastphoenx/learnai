"""Inhaltsanalyse für Quiz und Lernkarten (Rechenarten, Lösungswege)."""

from __future__ import annotations

import re

from app.core.method_taxonomy import METHOD_LABELS, classify_method, normalize_method_id
from app.core.quiz_explanation import parse_arithmetic_operands

_OP_LABELS = {
    "add": "Addition",
    "sub": "Subtraktion",
    "mul": "Multiplikation",
    "div": "Division",
    "other": "Sonstiges",
}

_KEYWORD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("add", re.compile(r"addition|summe|addier", re.I)),
    ("sub", re.compile(r"subtraktion|differenz|subtrahier", re.I)),
    ("mul", re.compile(r"multiplikation|produkt|multiplizier|·|×", re.I)),
    ("div", re.compile(r"division|quotient|dividier|geteilt|[:÷/]", re.I)),
]


def classify_operation(text: str) -> str:
    parsed = parse_arithmetic_operands(str(text or ""))
    if parsed:
        return parsed[0]
    lower = str(text or "").lower()
    for op, pattern in _KEYWORD_PATTERNS:
        if pattern.search(lower):
            return op
    return "other"


def _resolve_card_method(card: dict) -> str:
    explicit = normalize_method_id(card.get("method_id") or card.get("expected_method"))
    if explicit:
        return explicit
    kind = str(card.get("kind") or "").strip().lower()
    question = str(card.get("question") or "")
    answer = str(card.get("answer") or "")
    return classify_method(f"{question} {answer}", kind=kind or None)


def _resolve_quiz_method(question: dict) -> str:
    q_type = str(question.get("question_type") or "").strip().lower()
    explicit = normalize_method_id(question.get("method_id"))
    text = str(question.get("q") or "")
    if q_type == "method":
        return explicit or "method_choice"
    if explicit:
        return explicit
    return classify_method(text)


def _count_ops(texts: list[str]) -> dict[str, int]:
    counts = {key: 0 for key in _OP_LABELS}
    for text in texts:
        counts[classify_operation(text)] += 1
    return counts


def _count_methods(items: list[dict], *, item_kind: str) -> dict[str, int]:
    counts = {key: 0 for key in METHOD_LABELS}
    for item in items:
        if not isinstance(item, dict):
            continue
        if item_kind == "card":
            method = _resolve_card_method(item)
        else:
            method = _resolve_quiz_method(item)
        counts[method] = counts.get(method, 0) + 1
    return counts


def _format_breakdown(counts: dict[str, int], *, total: int, labels: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    for key, label in labels.items():
        count = int(counts.get(key) or 0)
        if count <= 0:
            continue
        rows.append(
            {
                "key": key,
                "label": label,
                "count": count,
                "percent": round(100 * count / total) if total else 0,
            }
        )
    return rows


def _summary_sentence(kind_label: str, counts: dict[str, int], total: int, labels: dict[str, str]) -> str:
    if total <= 0:
        return f"Keine {kind_label} vorhanden."
    parts: list[str] = []
    for key, label in labels.items():
        count = int(counts.get(key) or 0)
        if count > 0:
            parts.append(f"{count}× {label}")
    breakdown = ", ".join(parts) if parts else "keine Zuordnung erkannt"
    return f"{total} {kind_label}: {breakdown}."


def analyze_interactive_modules(modules: list) -> dict:
    quiz_items: list[dict] = []
    card_items: list[dict] = []
    quiz_texts: list[str] = []
    card_texts: list[str] = []
    by_module: list[dict] = []

    for raw in modules:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "Bereich").strip()
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        module_quiz: list[dict] = []
        module_cards: list[dict] = []
        for card in content.get("cards") or []:
            if isinstance(card, dict):
                q = str(card.get("question") or "").strip()
                if q:
                    module_cards.append(card)
                    card_items.append(card)
                    card_texts.append(q)
        for q in quiz.get("questions") or []:
            if isinstance(q, dict):
                text = str(q.get("q") or "").strip()
                if text:
                    module_quiz.append(q)
                    quiz_items.append(q)
                    quiz_texts.append(text)
        quiz_counts = _count_ops([str(q.get("q") or "") for q in module_quiz])
        card_counts = _count_ops([str(c.get("question") or "") for c in module_cards])
        quiz_methods = _count_methods(module_quiz, item_kind="quiz")
        card_methods = _count_methods(module_cards, item_kind="card")
        by_module.append(
            {
                "domain": title,
                "quiz_total": len(module_quiz),
                "quiz_ops": _format_breakdown(quiz_counts, total=len(module_quiz) or 1, labels=_OP_LABELS),
                "quiz_methods": _format_breakdown(
                    quiz_methods, total=len(module_quiz) or 1, labels=METHOD_LABELS
                ),
                "card_total": len(module_cards),
                "card_ops": _format_breakdown(card_counts, total=len(module_cards) or 1, labels=_OP_LABELS),
                "card_methods": _format_breakdown(
                    card_methods, total=len(module_cards) or 1, labels=METHOD_LABELS
                ),
            }
        )

    quiz_counts = _count_ops(quiz_texts)
    card_counts = _count_ops(card_texts)
    quiz_methods = _count_methods(quiz_items, item_kind="quiz")
    card_methods = _count_methods(card_items, item_kind="card")
    quiz_total = len(quiz_texts)
    card_total = len(card_texts)
    method_summary = _summary_sentence("Lernkarten (Lösungswege)", card_methods, card_total, METHOD_LABELS)
    quiz_method_summary = _summary_sentence("Quizfragen (Lösungswege)", quiz_methods, quiz_total, METHOD_LABELS)
    return {
        "quiz": {
            "total": quiz_total,
            "operations": _format_breakdown(quiz_counts, total=quiz_total or 1, labels=_OP_LABELS),
            "methods": _format_breakdown(quiz_methods, total=quiz_total or 1, labels=METHOD_LABELS),
            "summary": _summary_sentence("Quizfragen", quiz_counts, quiz_total, _OP_LABELS),
            "methods_summary": quiz_method_summary,
        },
        "cards": {
            "total": card_total,
            "operations": _format_breakdown(card_counts, total=card_total or 1, labels=_OP_LABELS),
            "methods": _format_breakdown(card_methods, total=card_total or 1, labels=METHOD_LABELS),
            "summary": _summary_sentence("Lernkarten", card_counts, card_total, _OP_LABELS),
            "methods_summary": method_summary,
        },
        "by_module": by_module,
        "overview": (
            f"Diese Einheit enthält {quiz_total} Quizfragen und {card_total} Lernkarten. "
            f"{_summary_sentence('Quizfragen', quiz_counts, quiz_total, _OP_LABELS)} "
            f"{method_summary} {quiz_method_summary}"
        ).strip(),
    }
