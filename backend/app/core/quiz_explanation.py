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


def _join_variants(primary: str, alt: str | None) -> str:
    if alt:
        return f"{primary}\n\n{alt}"
    return primary
    """Zerlegung in Ganze + Dezimalteile."""
    if abs(a - round(a)) >= 1e-6 or abs(b - round(b)) >= 1e-6:
        a_whole = int(a) if a >= 0 else -int(-a)
        a_frac = round(a - a_whole, 10)
        b_whole = int(b) if b >= 0 else -int(-b)
        b_frac = round(b - b_whole, 10)
        if abs(a_frac) < 1e-9 and abs(b_frac) < 1e-9:
            return None
        sum_whole = a_whole + b_whole
        sum_frac = round(a_frac + b_frac, 10)
        total = round(sum_whole + sum_frac, 10)
        return (
            f"Variante 2 (Zerlegung): {_fmt_num(a)} = {_fmt_num(a_whole)} + {_fmt_num(a_frac)}, "
            f"{_fmt_num(b)} = {_fmt_num(b_whole)} + {_fmt_num(b_frac)}. "
            f"Ganze: {_fmt_num(a_whole)} + {_fmt_num(b_whole)} = {_fmt_num(sum_whole)}. "
            f"Dezimal: {_fmt_num(a_frac)} + {_fmt_num(b_frac)} = {_fmt_num(sum_frac)}. "
            f"Zusammen: {_fmt_num(sum_whole)} + {_fmt_num(sum_frac)} = {_fmt_num(total)}."
        )
    return None


def _sub_alternative_steps(a: float, b: float, result: float) -> str | None:
    if abs(a - round(a)) >= 1e-6 or abs(b - round(b)) >= 1e-6:
        a_whole = int(a) if a >= 0 else -int(-a)
        a_frac = round(a - a_whole, 10)
        b_whole = int(b) if b >= 0 else -int(-b)
        b_frac = round(b - b_whole, 10)
        if abs(a_frac) < 1e-9 and abs(b_frac) < 1e-9:
            return None
        diff_whole = a_whole - b_whole
        diff_frac = round(a_frac - b_frac, 10)
        if diff_frac < -1e-9:
            diff_whole -= 1
            diff_frac = round(diff_frac + 1, 10)
        total = round(diff_whole + diff_frac, 10)
        return (
            f"Variante 2 (Zerlegung): Ganze {_fmt_num(a_whole)} − {_fmt_num(b_whole)} = {_fmt_num(diff_whole)}. "
            f"Dezimal {_fmt_num(a_frac)} − {_fmt_num(b_frac)} = {_fmt_num(diff_frac)}. "
            f"Zusammen: {_fmt_num(diff_whole)} + {_fmt_num(diff_frac)} = {_fmt_num(total)}."
        )
    return None


def _add_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    primary = (
        f"Variante 1 (untereinander): {a_s} + {b_s}. "
        f"Addiere die Zahlen (Dezimalstellen untereinander): {a_s} + {b_s} = {r_s}."
    )
    alt = _add_alternative_steps(a, b, result)
    return _join_variants(primary, alt)


def _sub_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    primary = (
        f"Variante 1 (untereinander): {a_s} − {b_s}. "
        f"Subtrahiere (Dezimalstellen untereinander): {a_s} − {b_s} = {r_s}."
    )
    alt = _sub_alternative_steps(a, b, result)
    return _join_variants(primary, alt)


def _div_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    return f"Rechnung: {a_s} ÷ {b_s} = {r_s}."


def _mul_alternative_steps(a: float, b: float, result: float) -> str | None:
    """Zweiter Weg über Stellenwert-Zerlegung, z. B. 250,1 → (20+5)×10 + 0,1."""
    if abs(a - round(a)) >= 1e-6:
        return None
    a_int = int(round(a))
    if abs(b - round(b)) < 1e-6:
        return None
    whole = int(b) if b >= 0 else -int(-b)
    frac = round(b - whole, 10)
    if frac <= 0 or whole < 100 or whole % 10 != 0:
        return None
    tens_group = whole // 10
    t_high = (tens_group // 10) * 10
    t_low = tens_group - t_high
    if t_low <= 0 or t_high <= 0:
        return None

    p_high = a_int * t_high
    p_low = a_int * t_low
    sub_sum = p_high + p_low
    prod_whole = sub_sum * 10
    p_frac = a_int * frac
    a_s = _fmt_num(float(a_int))
    return (
        f"Variante 2 (Stellenwert): {_fmt_num(b)} = {_fmt_num(t_high)}×10 + {_fmt_num(t_low)}×10 + {_fmt_num(frac)}. "
        f"{a_s}×{_fmt_num(t_high)}={_fmt_num(p_high)}, {a_s}×{_fmt_num(t_low)}={_fmt_num(p_low)}, "
        f"{_fmt_num(p_high)}+{_fmt_num(p_low)}={_fmt_num(sub_sum)}, {_fmt_num(sub_sum)}×10={_fmt_num(prod_whole)}. "
        f"Dann {a_s}×{_fmt_num(frac)}={_fmt_num(p_frac)}, "
        f"{_fmt_num(prod_whole)}+{_fmt_num(p_frac)}={_fmt_num(result)}."
    )


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
        primary = (
            f"Variante 1 (Ganzes + Dezimal): {a_s} × {b_s}. "
            f"Zuerst {a_s} × {_fmt_num(whole)} = {_fmt_num(part_whole)}. "
            f"Dann {a_s} × {_fmt_num(frac)} = {_fmt_num(part_frac)}. "
            f"Addiere: {_fmt_num(part_whole)} + {_fmt_num(part_frac)} = {r_s}."
        )
        alt = _mul_alternative_steps(a, b, result)
        if alt:
            return _join_variants(primary, alt)
        return primary
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
    question = str(q.get("q") or "")
    worked = build_worked_solution(question)
    if worked:
        return worked
    original = str(q.get("explanation") or "").strip()
    return original
