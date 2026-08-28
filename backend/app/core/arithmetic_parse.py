"""Erkennung von Rechenaufgaben in Freitext-Fragen (Quiz, Karten, Erklärungen)."""

from __future__ import annotations

import re

_NUM = r"-?\d+(?:[.,]\d+)?"
_QNUM = re.compile(_NUM)
_OP_SYMBOL = r"[·×*]"

_METHOD_QUESTION = re.compile(
    r"zerlegungsmethode|schriftliche\s+methode|wie löst du|welche methode|"
    r"mit der (?:zerlegungs|reihen|komma|stellenwert).{0,12}methode",
    re.I,
)

_DIV_KEYWORD = re.compile(r"dividier|divisor|geteilt|quotient|[:÷/]", re.I)
_MUL_KEYWORD = re.compile(rf"multipliz|produkt|{_OP_SYMBOL}", re.I)
_ADD_KEYWORD = re.compile(r"addier|summe|\+", re.I)
_SUB_KEYWORD = re.compile(r"subtrahier|differenz", re.I)

_PARSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "mul",
        re.compile(
            rf"(?:multiplikation\s+von|multipliziere\w*|produkt\s+von)\s+(?:\w+\s+)*({_NUM})\s*"
            rf"(?:{_OP_SYMBOL}|und|mit)\s*(?:\w+\s+)*({_NUM})",
            re.I,
        ),
    ),
    ("mul", re.compile(rf"({_NUM})\s*{_OP_SYMBOL}\s*({_NUM})")),
    ("add", re.compile(rf"({_NUM})\s*\+\s*({_NUM})")),
    (
        "add",
        re.compile(
            rf"(?:addition|summe)\s+(?:von\s+)?(?:\w+\s+)*({_NUM})\s+und\s+(?:\w+\s+)*({_NUM})",
            re.I,
        ),
    ),
    ("sub", re.compile(rf"({_NUM})\s+-\s+({_NUM})")),
    (
        "sub",
        re.compile(
            rf"(?:subtraktion|differenz)\s+(?:von|zwischen)\s+(?:\w+\s+)*({_NUM})\s+und\s+(?:\w+\s+)*({_NUM})",
            re.I,
        ),
    ),
    (
        "div",
        re.compile(
            rf"(?:division|quotient|ergebnis)\s+von\s+(?:\w+\s+)*({_NUM})\s*"
            rf"(?:[:÷/]|geteilt\s+durch|durch(?:\s+(?:den\s+)?(?:divisor|teiler))?)\s*(?:\w+\s+)*({_NUM})",
            re.I,
        ),
    ),
    (
        "div",
        re.compile(
            rf"(?:dividiere\w*)\s+(?:\w+\s+)*({_NUM})\s*"
            rf"(?:[:÷/]|geteilt\s+durch|durch(?:\s+(?:den\s+)?(?:divisor|teiler))?)\s*(?:\w+\s+)*({_NUM})",
            re.I,
        ),
    ),
    ("div", re.compile(rf"({_NUM})\s*(?:[:÷/]|geteilt\s+durch)\s*({_NUM})")),
    (
        "div",
        re.compile(
            rf"({_NUM})\s+durch(?:\s+(?:den\s+)?(?:divisor|teiler))?\s*({_NUM})",
            re.I,
        ),
    ),
]


def _to_float(raw: str) -> float:
    return float(str(raw).replace(",", "."))


def numbers_in_text(text: str) -> list[float]:
    out: list[float] = []
    for match in _QNUM.findall(str(text or "").replace(",", ".")):
        try:
            out.append(_to_float(match))
        except ValueError:
            continue
    return out


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

    nums = numbers_in_text(text)
    if len(nums) < 2:
        return None
    a, b = nums[0], nums[1]
    if _DIV_KEYWORD.search(text) and abs(b) > 1e-12:
        return "div", a, b
    if _MUL_KEYWORD.search(text):
        return "mul", a, b
    if _SUB_KEYWORD.search(text):
        return "sub", a, b
    if _ADD_KEYWORD.search(text):
        return "add", a, b
    return None


def try_compute_from_question(question: str) -> float | None:
    if _METHOD_QUESTION.search(str(question or "")):
        return None
    parsed = parse_arithmetic_operands(question)
    if not parsed:
        return None
    op, a, b = parsed
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    if op == "div":
        if abs(b) < 1e-12:
            return None
        return a / b
    return None


def question_is_computable(question: str) -> bool:
    return parse_arithmetic_operands(question) is not None
