"""Bewertung von Eingabe-Lernkarten (Ergebnis + optionaler Lösungsweg)."""

from __future__ import annotations

import re

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


def _normalize_free_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower().replace(",", "."))


def _result_matches(expected: str, user_answer: str) -> bool:
    exp_num = parse_quiz_numeric(expected)
    usr_num = parse_quiz_numeric(user_answer)
    if exp_num is not None and usr_num is not None:
        return abs(exp_num - usr_num) < 1e-6
    return _normalize_free_text(expected) == _normalize_free_text(user_answer)


def _method_hint_hits(method_id: str | None, text: str) -> int:
    key = normalize_method_id(method_id)
    if not key:
        return 0
    hints = METHOD_HINTS.get(key, ())
    return sum(1 for hint in hints if hint in text)


def grade_worked_solution(
    question: str,
    expected_answer: str,
    user_text: str,
    *,
    expected_method: str | None = None,
) -> tuple[bool, str]:
    text = _normalize_free_text(user_text)
    if len(text) < 12:
        return False, "Beschreibe den Lösungsweg etwas ausführlicher (mindestens ein paar Wörter)."

    exp_num = parse_quiz_numeric(expected_answer)
    has_result = False
    if exp_num is not None:
        result_str = f"{exp_num:.6f}".rstrip("0").rstrip(".")
        has_result = result_str in text or f"{exp_num}".replace(".", ",") in user_text.lower()

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

    method_hits = _method_hint_hits(expected_method, text)
    method_id = normalize_method_id(expected_method)

    ok = has_result and (step_hits >= 2 or variant_hits >= 1 or len(text) >= 45)
    if mentions_task:
        ok = ok or (step_hits >= 1 and len(text) >= 30)
    if method_id and has_result:
        if method_hits >= 1 and (step_hits >= 1 or len(text) >= 25):
            ok = True
        elif method_hits == 0 and step_hits >= 2:
            ok = ok or len(text) >= 40

    if ok:
        if method_id and method_hits == 0:
            return True, (
                f"Ergebnis stimmt. Für «{method_label(method_id)}» könntest du die Methode noch klarer benennen."
            )
        return True, "Guter Lösungsweg — du hast Rechenschritte erklärt."
    if not has_result:
        return False, "Nenne im Lösungsweg auch das Ergebnis."
    if method_id and method_hits == 0:
        return (
            False,
            f"Beschreibe den Weg für «{method_label(method_id)}» "
            f"(z. B. {', '.join(METHOD_HINTS.get(method_id, ())[:2])}).",
        )
    return False, "Ergänze noch einen Rechenschritt (z. B. Zerlegung, Reihe oder Komma verschieben)."


def grade_input_card(
    *,
    question: str,
    expected_answer: str,
    user_answer: str,
    worked_solution: str | None = None,
    expected_method: str | None = None,
) -> dict:
    result_correct = _result_matches(expected_answer, user_answer)
    worked_correct: bool | None = None
    worked_feedback: str | None = None

    if worked_solution and worked_solution.strip():
        worked_correct, worked_feedback = grade_worked_solution(
            question,
            expected_answer,
            worked_solution,
            expected_method=expected_method,
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
    }
