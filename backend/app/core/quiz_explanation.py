"""Rechenwege für Quiz-Erklärungen (Laufzeit-Anreicherung schwacher LLM-Texte)."""

from __future__ import annotations

import re

from app.core.quiz_numeric import try_compute_from_question

_NUM = r"-?\d+(?:[.,]\d+)?"
_OP_SYMBOL = r"[·×*]"
_WEAK_EXPLANATION = re.compile(
    r"^(das\s+)?(ergebnis|die\s+summe|die\s+differenz|das\s+produkt|"
    r"die\s+multiplikation|die\s+addition|die\s+subtraktion|die\s+division).{0,80}"
    r"(ist|ergibt|beträgt|lautet|entspricht)\s+[\d,.]+",
    re.I | re.S,
)
_PARSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "mul",
        re.compile(
            rf"(?:multiplikation\s+von|multipliziere|produkt\s+von)\s+({_NUM})\s*(?:{_OP_SYMBOL}|und|mit)\s*({_NUM})",
            re.I,
        ),
    ),
    ("mul", re.compile(rf"({_NUM})\s*{_OP_SYMBOL}\s*({_NUM})")),
    (
        "add",
        re.compile(rf"(?:addition|summe)\s+von\s+({_NUM})\s+und\s+({_NUM})", re.I),
    ),
    (
        "sub",
        re.compile(rf"(?:subtraktion|differenz)\s+von\s+({_NUM})\s+und\s+({_NUM})", re.I),
    ),
    (
        "div",
        re.compile(rf"(?:division|quotient)\s+von\s+({_NUM})\s+(?:durch|und)\s+({_NUM})", re.I),
    ),
]


def _to_float(raw: str) -> float:
    return float(str(raw).replace(",", "."))


def _fmt_num(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def parse_arithmetic_operands(question: str) -> tuple[str, float, float] | None:
    text = str(question or "").replace(",", ".")
    for op, pattern in _PARSE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        try:
            return op, _to_float(match.group(1)), _to_float(match.group(2))
        except ValueError:
            continue
    return None


def explanation_is_weak(explanation: str, question: str) -> bool:
    expl = str(explanation or "").strip()
    if not expl:
        return True
    lower = expl.lower()
    if any(token in lower for token in ("zuerst", "rechnung:", "schritt", "addiere", "subtrahiere", "multipliziere")):
        return False
    if _WEAK_EXPLANATION.search(expl):
        return True
    if try_compute_from_question(question) is not None and len(expl) < 110:
        return True
    return False


def _add_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    return (
        f"Rechnung: {a_s} + {b_s}. "
        f"Addiere die Zahlen (Dezimalstellen untereinander): {a_s} + {b_s} = {r_s}."
    )


def _sub_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    return (
        f"Rechnung: {a_s} − {b_s}. "
        f"Subtrahiere (Dezimalstellen untereinander): {a_s} − {b_s} = {r_s}."
    )


def _div_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    return f"Rechnung: {a_s} ÷ {b_s} = {r_s}."


def _mul_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    if abs(b - round(b)) < 1e-6:
        return f"Rechnung: {a_s} × {b_s} = {r_s}."
    if abs(a - round(a)) < 1e-6 and abs(b - round(b)) >= 1e-6:
        whole = int(b) if b >= 0 else -int(-b)
        frac = round(b - whole, 10)
        if abs(frac) < 1e-9:
            return f"Rechnung: {a_s} × {b_s} = {r_s}."
        part_whole = a * whole
        part_frac = a * frac
        return (
            f"Rechnung: {a_s} × {b_s}. "
            f"Zuerst {a_s} × {_fmt_num(whole)} = {_fmt_num(part_whole)}. "
            f"Dann {a_s} × {_fmt_num(frac)} = {_fmt_num(part_frac)}. "
            f"Addiere: {_fmt_num(part_whole)} + {_fmt_num(part_frac)} = {r_s}."
        )
    return f"Rechnung: {a_s} × {b_s} = {r_s}."


def build_worked_solution(question: str, expected: float | None = None) -> str | None:
    parsed = parse_arithmetic_operands(question)
    if parsed:
        op, a, b = parsed
        if expected is None:
            if op == "add":
                expected = a + b
            elif op == "sub":
                expected = a - b
            elif op == "mul":
                expected = a * b
            elif op == "div":
                if abs(b) < 1e-12:
                    return None
                expected = a / b
        if op == "add":
            return _add_steps(a, b, expected)
        if op == "sub":
            return _sub_steps(a, b, expected)
        if op == "mul":
            return _mul_steps(a, b, expected)
        if op == "div":
            return _div_steps(a, b, expected)

    if expected is None:
        expected = try_compute_from_question(question)
    if expected is None:
        return None
    return f"Rechnung: Ergebnis = {_fmt_num(expected)}."


def enrich_quiz_explanation(q: dict) -> str:
    original = str(q.get("explanation") or "").strip()
    question = str(q.get("q") or "")
    if not explanation_is_weak(original, question):
        return original
    worked = build_worked_solution(question)
    if worked:
        return worked
    return original
