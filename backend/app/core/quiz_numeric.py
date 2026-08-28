"""Numeric equivalence and answer resolution for multiple-choice quizzes."""

from __future__ import annotations

import re

from app.core.arithmetic_parse import try_compute_from_question as _try_compute_from_question

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
    return _try_compute_from_question(question)


def resolve_quiz_expected_value(q: dict) -> float | None:
    computed = try_compute_from_question(str(q.get("q") or ""))
    from_expl = parse_expected_from_explanation(str(q.get("explanation") or ""))
    if computed is not None:
        return computed
    return from_expl


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
    options = out.get("options")
    if isinstance(options, list) and len(options) == 4:
        out["options"] = _dedupe_numeric_options(options, int(out.get("answer", -1)))
    return out


def _format_numeric_like(value: float, like: str) -> str:
    stripped = strip_option_label(like)
    use_comma = "," in stripped
    if abs(value - round(value)) < 1e-9 and abs(value) < 1e12:
        body = str(int(round(value)))
    else:
        body = f"{value:.6g}"
    if use_comma:
        body = body.replace(".", ",")
    prefix = _OPTION_LABEL.match(str(like) or "")
    if prefix:
        return f"{prefix.group(0)}{body}"
    return body


def _distractor_candidates(value: float) -> list[float]:
    out: list[float] = []
    for factor in (10.0, 0.1, 100.0, 0.01):
        out.append(value * factor)
    for delta in (1.0, -1.0, 0.1, -0.1, 2.0, -2.0, 0.5, -0.5):
        out.append(value + delta)
    if abs(value) > 1e-12:
        out.append(-value)
    else:
        out.extend([1.0, 2.0, 10.0])
    return out


def _value_taken(used: list[float | None], candidate: float) -> bool:
    return any(v is not None and abs(v - candidate) < 1e-6 for v in used)


def _dedupe_numeric_options(options: list, answer_idx: int) -> list[str]:
    out = [str(o) for o in options]
    for i, text in enumerate(out):
        if i == answer_idx:
            continue
        current = parse_quiz_numeric(text)
        if current is None:
            continue
        others = [parse_quiz_numeric(out[j]) for j in range(len(out)) if j != i]
        if not _value_taken(others, current):
            continue
        base = parse_quiz_numeric(out[answer_idx]) if 0 <= answer_idx < len(out) else current
        if base is None:
            base = current
        used = [parse_quiz_numeric(t) for t in out]
        replacement: float | None = None
        for cand in _distractor_candidates(base):
            if not _value_taken(used, cand):
                replacement = cand
                break
        if replacement is None:
            bump = base + 1.0
            for _ in range(50):
                if not _value_taken(used, bump):
                    replacement = bump
                    break
                bump += 1.0
        if replacement is None:
            continue
        out[i] = _format_numeric_like(replacement, text)
    return out


def repair_quiz_block(quiz: dict | None) -> dict:
    if not isinstance(quiz, dict):
        return {"questions": []}
    out = dict(quiz)
    questions = quiz.get("questions")
    if isinstance(questions, list):
        out["questions"] = [repair_quiz_question(q) for q in questions]
    return out
