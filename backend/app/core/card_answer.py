"""Bewertung von Eingabe-Lernkarten (Ergebnis + optionaler Lösungsweg)."""

from __future__ import annotations

import re

from app.core.answer_match import answers_match, infer_answer_type
from app.core.method_taxonomy import METHOD_HINTS, method_label, normalize_method_id
from app.core.quiz_explanation import build_worked_solution, parse_arithmetic_operands
from app.core.quiz_numeric import parse_quiz_numeric

_STEP_HINTS = (
    "zerleg",
    "addier",
    "subtrahier",
    "multipliz",
    "teile",
    "divid",
    "reihe",
    "komma",
    "hundertstel",
    "zehntel",
    "tausendstel",
    "stellenwert",
    "schritt",
    "zuerst",
    "dann",
)

_MULT_STEP = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[x×*·]\s*(\d+(?:[.,]\d+)?)\s*=\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)


def _decomposition_steps_ok(question: str, user_text: str, expected_answer: str) -> bool:
    """Erkennt Zerlegungsschritte wie 10×0,85=8,5 und 4×0,85=3,4."""
    parsed = parse_arithmetic_operands(question)
    if not parsed:
        return False
    op, _a, _b = parsed
    if op != "mul":
        return False
    exp_num = parse_quiz_numeric(expected_answer)
    if exp_num is None:
        return False
    steps = _MULT_STEP.findall(str(user_text or "").lower().replace(",", "."))
    if len(steps) < 2:
        return False
    partials: list[float] = []
    for _left, _right, result in steps:
        try:
            partials.append(float(result.replace(",", ".")))
        except ValueError:
            continue
    if len(partials) < 2:
        return False
    return abs(sum(partials) - exp_num) < 0.02


def _normalize_free_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower().replace(",", "."))


def _method_display_name(
    expected_method: str | None,
    *,
    expected_method_label: str | None = None,
) -> str | None:
    label = str(expected_method_label or "").strip()
    if label:
        return label
    method_id = normalize_method_id(expected_method)
    if method_id:
        return method_label(method_id)
    return None


def _method_hint_hits(
    expected_method: str | None,
    text: str,
    *,
    expected_method_label: str | None = None,
) -> int:
    label = str(expected_method_label or "").strip().lower()
    hits = 0
    if label and label in text:
        hits += 2
    key = normalize_method_id(expected_method)
    if key:
        hints = METHOD_HINTS.get(key, ())
        hits += sum(1 for hint in hints if hint in text)
    return hits


def grade_worked_solution(
    question: str,
    expected_answer: str,
    user_text: str,
    *,
    expected_method: str | None = None,
    expected_method_label: str | None = None,
    answer_type: str | None = None,
) -> tuple[bool, str]:
    text = _normalize_free_text(user_text)
    if len(text) < 12:
        return False, "Beschreibe den Lösungsweg etwas ausführlicher (mindestens ein paar Wörter)."

    kind = infer_answer_type(question=question, answer=expected_answer, raw_type=answer_type)
    method_name = _method_display_name(expected_method, expected_method_label=expected_method_label)

    exp_num = parse_quiz_numeric(expected_answer)
    has_result = answers_match(expected_answer, user_text, answer_type=kind)
    decomp_ok = _decomposition_steps_ok(question, user_text, expected_answer)
    if exp_num is not None and kind == "numeric":
        result_str = f"{exp_num:.6f}".rstrip("0").rstrip(".")
        has_result = has_result or result_str in text or f"{exp_num}".replace(".", ",") in user_text.lower()
    if decomp_ok:
        has_result = True

    parsed = parse_arithmetic_operands(question)
    mentions_task = False
    if parsed:
        _, a, b = parsed
        for value in (a, b):
            for variant in (f"{value}", f"{value:.2f}".rstrip("0").rstrip(".")):
                if variant.replace(".", ",") in user_text.lower() or variant in text:
                    mentions_task = True
                    break

    step_hits = sum(1 for hint in _STEP_HINTS if hint in text)
    worked = build_worked_solution(question, exp_num)
    variant_hits = 0
    if worked:
        for token in ("variante", "reihe", "zerlegung", "komma", "addier", "teile"):
            if token in worked.lower() and token in text:
                variant_hits += 1

    method_hits = _method_hint_hits(
        expected_method,
        text,
        expected_method_label=expected_method_label,
    )
    method_id = normalize_method_id(expected_method)

    ok = has_result and (step_hits >= 2 or variant_hits >= 1 or len(text) >= 45)
    if decomp_ok:
        ok = True
    if mentions_task:
        ok = ok or (step_hits >= 1 and len(text) >= 30)
    if method_name and has_result:
        if method_hits >= 1 and (step_hits >= 1 or len(text) >= 25):
            ok = True
        elif method_hits == 0 and step_hits >= 2:
            ok = ok or len(text) >= 40
    if kind != "numeric" and has_result and len(text) >= 20:
        ok = True

    if ok:
        if method_name and method_hits == 0:
            return True, (
                f"Ergebnis stimmt. Für «{method_name}» könntest du die Methode noch klarer benennen."
            )
        return True, "Guter Lösungsweg — du hast die Schritte nachvollziehbar erklärt."
    if not has_result:
        return False, "Nenne im Lösungsweg auch das Ergebnis."
    if method_name and method_hits == 0:
        return (
            False,
            f"Beschreibe den Weg für «{method_name}» — benenne die Strategie und die wichtigsten Schritte.",
        )
    return False, "Ergänze noch einen nachvollziehbaren Zwischenschritt."


def grade_input_card(
    *,
    question: str,
    expected_answer: str,
    user_answer: str,
    worked_solution: str | None = None,
    expected_method: str | None = None,
    expected_method_label: str | None = None,
    answer_type: str | None = None,
) -> dict:
    kind = infer_answer_type(question=question, answer=expected_answer, raw_type=answer_type)
    result_correct = answers_match(expected_answer, user_answer, answer_type=kind)
    worked_correct: bool | None = None
    worked_feedback: str | None = None

    if worked_solution and worked_solution.strip():
        worked_correct, worked_feedback = grade_worked_solution(
            question,
            expected_answer,
            worked_solution,
            expected_method=expected_method,
            expected_method_label=expected_method_label,
            answer_type=kind,
        )

    correct = result_correct and (worked_correct is not False)
    explanation = None
    if not result_correct:
        explanation = build_worked_solution(question) or f"Lösung: {expected_answer}"

    return {
        "correct": correct,
        "result_correct": result_correct,
        "worked_correct": worked_correct,
        "worked_feedback": worked_feedback,
        "explanation": explanation,
        "expected": expected_answer if not result_correct else None,
        "expected_method": normalize_method_id(expected_method),
        "expected_method_label": str(expected_method_label or "").strip() or None,
        "answer_type": kind,
    }
