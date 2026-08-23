"""Numeric equivalence and answer resolution for multiple-choice quizzes."""

from __future__ import annotations

import re

_NUMERIC_OPTION = re.compile(r"-?\d+(?:[.,]\d+)?")
_PURE_NUMERIC_OPTION = re.compile(r"^-?\d+(?:[.,]\d+)?(?:\s*/\s*-?\d+(?:[.,]\d+)?)?$")
_OPTION_LABEL = re.compile(r"^[a-d]\)\s*", re.I)
_METHOD_QUESTION = re.compile(
    r"zerlegungsmethode|schriftliche\s+methode|wie löst du|welche methode|"
    r"mit der (?:zerlegungs|reihen|komma|stellenwert).{0,12}methode",
    re.I,
)
_ERGIBT = re.compile(r"ergibt\s+(-?\d+(?:[.,]\d+)?)", re.I)
_ADDITION = re.compile(
    r"addition\s+von\s+(-?\d+(?:[.,]\d+)?)\s+und\s+(-?\d+(?:[.,]\d+)?)",
    re.I,
)
_SUBTRACTION = re.compile(
    r"subtraktion\s+von\s+(-?\d+(?:[.,]\d+)?)\s+und\s+(-?\d+(?:[.,]\d+)?)",
    re.I,
)
_MULTIPLICATION = re.compile(
    r"(?:multiplikation\s+von|multipliziere)\s+(-?\d+(?:[.,]\d+)?)\s+(?:und|mit)\s+(-?\d+(?:[.,]\d+)?)",
    re.I,
)
_DIVISION = re.compile(
    r"(?:division\s+von|quotient\s+von|ergebnis\s+von|dividiere)\s+(-?\d+(?:[.,]\d+)?)\s*"
    r"(?:[:÷/]|geteilt\s+durch|durch)\s*(-?\d+(?:[.,]\d+)?)",
    re.I,
)
_DIV_COLON = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*(?:[:÷/]|geteilt\s+durch)\s*(-?\d+(?:[.,]\d+)?)",
    re.I,
)
_MULT_DOT = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*[·×*]\s*(-?\d+(?:[.,]\d+)?)",
    re.I,
)
_ADD_SYMBOL = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*\+\s*(-?\d+(?:[.,]\d+)?)")
_SUB_SYMBOL = re.compile(r"(-?\d+(?:[.,]\d+)?)\s+-\s+(-?\d+(?:[.,]\d+)?)")


def strip_option_label(text: str) -> str:
    return _OPTION_LABEL.sub("", str(text or "").strip()).strip()


def is_numeric_choice_option(text: str) -> bool:
    """True nur bei Optionen, die im Wesentlichen eine Zahl sind — nicht bei Fliesstext."""
    stripped = strip_option_label(text)
    compact = re.sub(r"\s+", "", stripped)
    return bool(compact) and bool(_PURE_NUMERIC_OPTION.match(compact))


def _normalize_choice_text(text: str) -> str:
    return re.sub(r"\s+", " ", strip_option_label(text).lower().replace(",", ".")).strip()


def parse_quiz_numeric(text: str) -> float | None:
    raw = strip_option_label(text).lower().replace(",", ".")
    compact = re.sub(r"\s+", "", raw)
    if "/" in compact:
        parts = compact.split("/", 1)
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return None
    match = _NUMERIC_OPTION.search(compact)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_expected_from_explanation(explanation: str) -> float | None:
    text = str(explanation or "").replace(",", ".")
    match = _ERGIBT.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def try_compute_from_question(question: str) -> float | None:
    raw = str(question or "")
    if _METHOD_QUESTION.search(raw):
        return None
    text = raw.replace(",", ".")
    match = _ADD_SYMBOL.search(text)
    if match:
        return float(match.group(1)) + float(match.group(2))
    match = _SUB_SYMBOL.search(text)
    if match:
        return float(match.group(1)) - float(match.group(2))
    match = _ADDITION.search(text)
    if match:
        return float(match.group(1)) + float(match.group(2))
    match = _SUBTRACTION.search(text)
    if match:
        return float(match.group(1)) - float(match.group(2))
    match = _MULT_DOT.search(text)
    if match:
        return float(match.group(1).replace(",", ".")) * float(match.group(2).replace(",", "."))
    match = _MULTIPLICATION.search(text)
    if match:
        return float(match.group(1)) * float(match.group(2))
    match = _DIVISION.search(text)
    if match:
        divisor = float(match.group(2).replace(",", "."))
        if abs(divisor) < 1e-12:
            return None
        return float(match.group(1).replace(",", ".")) / divisor
    match = _DIV_COLON.search(text)
    if match:
        divisor = float(match.group(2).replace(",", "."))
        if abs(divisor) < 1e-12:
            return None
        return float(match.group(1).replace(",", ".")) / divisor
    return None


def resolve_quiz_expected_value(q: dict) -> float | None:
    expected = parse_expected_from_explanation(str(q.get("explanation") or ""))
    if expected is not None:
        return expected
    return try_compute_from_question(str(q.get("q") or ""))


def option_indices_matching_value(options: list, value: float) -> list[int]:
    matches: list[int] = []
    for i, opt in enumerate(options):
        if not is_numeric_choice_option(str(opt)):
            continue
        parsed = parse_quiz_numeric(str(opt))
        if parsed is not None and abs(parsed - value) < 1e-6:
            matches.append(i)
    return matches


def _prefer_matching_option_index(options: list, indices: list[int], explanation: str) -> int:
    expl = str(explanation or "").replace(",", ".")
    ranked = sorted(
        indices,
        key=lambda i: len(strip_option_label(str(options[i]))),
        reverse=True,
    )
    for i in ranked:
        label = strip_option_label(str(options[i]))
        if label and label in expl:
            return i
    for i in ranked:
        label = strip_option_label(str(options[i]))
        if "." in label and label in expl:
            return i
    return indices[0]


def resolve_quiz_correct_index(q: dict) -> int:
    options = q.get("options")
    if not isinstance(options, list) or len(options) != 4:
        try:
            return int(q.get("answer", -1))
        except (TypeError, ValueError):
            return -1

    try:
        stored = int(q.get("answer", -1))
    except (TypeError, ValueError):
        stored = -1
    expected = resolve_quiz_expected_value(q)
    if expected is not None:
        matches = option_indices_matching_value(options, expected)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return _prefer_matching_option_index(
                options,
                matches,
                str(q.get("explanation") or ""),
            )

    if 0 <= stored < len(options):
        return stored
    return -1


def quiz_options_numeric_equivalent(options: list, idx_a: int, idx_b: int) -> bool:
    if idx_a == idx_b:
        return True
    if not (0 <= idx_a < len(options) and 0 <= idx_b < len(options)):
        return False
    if not is_numeric_choice_option(str(options[idx_a])) or not is_numeric_choice_option(
        str(options[idx_b])
    ):
        return False
    a = parse_quiz_numeric(str(options[idx_a]))
    b = parse_quiz_numeric(str(options[idx_b]))
    if a is None or b is None:
        return False
    return abs(a - b) < 1e-6


def is_quiz_selection_correct(q: dict, selected: int) -> bool:
    options = q.get("options")
    if not isinstance(options, list) or not (0 <= selected < len(options)):
        return False

    selected_text = _normalize_choice_text(str(options[selected]))
    explanation = _normalize_choice_text(str(q.get("explanation") or ""))
    if selected_text and explanation and selected_text == explanation:
        return True

    expected = resolve_quiz_expected_value(q)
    if expected is not None and is_numeric_choice_option(str(options[selected])):
        selected_value = parse_quiz_numeric(str(options[selected]))
        if selected_value is not None:
            return abs(selected_value - expected) < 1e-6

    correct_index = resolve_quiz_correct_index(q)
    if selected == correct_index:
        return True
    return quiz_options_numeric_equivalent(options, selected, correct_index)


def repair_quiz_question(q: dict) -> dict:
    if not isinstance(q, dict):
        return q
    out = dict(q)
    resolved = resolve_quiz_correct_index(q)
    if 0 <= resolved <= 3:
        out["answer"] = resolved
    return out


def repair_quiz_block(quiz: dict | None) -> dict:
    if not isinstance(quiz, dict):
        return {"questions": []}
    out = dict(quiz)
    questions = quiz.get("questions")
    if isinstance(questions, list):
        out["questions"] = [repair_quiz_question(q) for q in questions]
    return out
