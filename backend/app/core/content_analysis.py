"""Inhaltsanalyse für Quiz und Lernkarten (Rechenarten, Themen)."""

from __future__ import annotations

import re

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


def _count_ops(texts: list[str]) -> dict[str, int]:
    counts = {key: 0 for key in _OP_LABELS}
    for text in texts:
        counts[classify_operation(text)] += 1
    return counts


def _format_breakdown(counts: dict[str, int], *, total: int) -> list[dict]:
    rows: list[dict] = []
    for key, label in _OP_LABELS.items():
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


def _summary_sentence(kind_label: str, counts: dict[str, int], total: int) -> str:
    if total <= 0:
        return f"Keine {kind_label} vorhanden."
    parts: list[str] = []
    for key, label in _OP_LABELS.items():
        count = int(counts.get(key) or 0)
        if count > 0:
            parts.append(f"{count}× {label}")
    breakdown = ", ".join(parts) if parts else "keine Rechenart erkannt"
    return f"{total} {kind_label}: {breakdown}."


def analyze_interactive_modules(modules: list) -> dict:
    quiz_texts: list[str] = []
    card_texts: list[str] = []
    by_module: list[dict] = []

    for raw in modules:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "Bereich").strip()
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        module_quiz: list[str] = []
        module_cards: list[str] = []
        for card in content.get("cards") or []:
            if isinstance(card, dict):
                q = str(card.get("question") or "").strip()
                if q:
                    module_cards.append(q)
                    card_texts.append(q)
        for q in quiz.get("questions") or []:
            if isinstance(q, dict):
                text = str(q.get("q") or "").strip()
                if text:
                    module_quiz.append(text)
                    quiz_texts.append(text)
        quiz_counts = _count_ops(module_quiz)
        card_counts = _count_ops(module_cards)
        by_module.append(
            {
                "domain": title,
                "quiz_total": len(module_quiz),
                "quiz_ops": _format_breakdown(quiz_counts, total=len(module_quiz) or 1),
                "card_total": len(module_cards),
                "card_ops": _format_breakdown(card_counts, total=len(module_cards) or 1),
            }
        )

    quiz_counts = _count_ops(quiz_texts)
    card_counts = _count_ops(card_texts)
    quiz_total = len(quiz_texts)
    card_total = len(card_texts)
    return {
        "quiz": {
            "total": quiz_total,
            "operations": _format_breakdown(quiz_counts, total=quiz_total or 1),
            "summary": _summary_sentence("Quizfragen", quiz_counts, quiz_total),
        },
        "cards": {
            "total": card_total,
            "operations": _format_breakdown(card_counts, total=card_total or 1),
            "summary": _summary_sentence("Lernkarten", card_counts, card_total),
        },
        "by_module": by_module,
        "overview": (
            f"Diese Einheit enthält {quiz_total} Quizfragen und {card_total} Lernkarten. "
            f"{_summary_sentence('Quizfragen', quiz_counts, quiz_total)} "
            f"{_summary_sentence('Lernkarten', card_counts, card_total)}"
        ).strip(),
    }
