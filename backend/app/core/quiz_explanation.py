"""Rechenwege für Quiz-Erklärungen (Laufzeit-Anreicherung schwacher LLM-Texte)."""

from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher

from app.core.quiz_numeric import try_compute_from_question

TIMES_TABLE_MIN = 2
TIMES_TABLE_MAX = 12

_NUM = r"-?\d+(?:[.,]\d+)?"
_OP_SYMBOL = r"[·×*]"
_WEAK_EXPLANATION = re.compile(
    r"^(das\s+)?(ergebnis|die\s+summe|die\s+differenz|das\s+produkt|"
    r"die\s+multiplikation|die\s+addition|die\s+subtraktion|die\s+division).{0,80}"
    r"(ist|ergibt|beträgt|lautet|entspricht)\s+[\d,.]+",
    re.I | re.S,
)
_EQUATION = re.compile(
    rf"{_NUM}\s*(?:{_OP_SYMBOL}|[+\-−]|[:÷/])\s*{_NUM}\s*=\s*{_NUM}",
)
_MUL_MENTION = re.compile(
    rf"({_NUM})\s*(?:{_OP_SYMBOL})\s*({_NUM})(?:\s*=\s*({_NUM}))?",
)
_VARIANT_SPLIT = re.compile(r"(?=Variante\s+\d+\s*(?:\([^)]*\))?\s*:)", re.I)
_VARIANT_HEAD = re.compile(r"^Variante\s+\d+\s*(?:\([^)]*\))?\s*:?\s*", re.I)
_REIHE_CLAIM = re.compile(r"(\d+)\s*er-reihe", re.I)
_STEP_COMMA = re.compile(
    rf"(=\s*{_NUM})\s*,\s*(?={_NUM}\s*(?:{_OP_SYMBOL}|[+\-−]|[:÷/]))",
)
_WRITTEN_HINT = re.compile(r"schriftlich", re.I)
_MENTAL_HINT = re.compile(r"im kopf|kopfrechn", re.I)
_NOTES_HINT = re.compile(r"notiz", re.I)
_PARSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "mul",
        re.compile(
            rf"(?:multiplikation\s+von|multipliziere|produkt\s+von)\s+({_NUM})\s*(?:{_OP_SYMBOL}|und|mit)\s*({_NUM})",
            re.I,
        ),
    ),
    ("mul", re.compile(rf"({_NUM})\s*{_OP_SYMBOL}\s*({_NUM})")),
    ("add", re.compile(rf"({_NUM})\s*\+\s*({_NUM})")),
    (
        "add",
        re.compile(rf"(?:addition|summe)\s+von\s+({_NUM})\s+und\s+({_NUM})", re.I),
    ),
    ("sub", re.compile(rf"({_NUM})\s*-\s*({_NUM})")),
    (
        "sub",
        re.compile(
            rf"(?:subtraktion|differenz)\s+(?:von|zwischen)\s+({_NUM})\s+und\s+({_NUM})",
            re.I,
        ),
    ),
    (
        "div",
        re.compile(
            rf"(?:division|quotient|ergebnis)\s+von\s+({_NUM})\s*(?:[:÷/]|geteilt\s+durch|durch)\s*({_NUM})",
            re.I,
        ),
    ),
    ("div", re.compile(rf"({_NUM})\s*(?:[:÷/]|geteilt\s+durch)\s*({_NUM})")),
    ("div", re.compile(rf"({_NUM})\s+durch\s+({_NUM})", re.I)),
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


def _variant_chunks(text: str) -> list[str]:
    parts = _VARIANT_SPLIT.split(str(text or ""))
    return [part.strip() for part in parts if part.strip()]


def _text_has_variant_label(text: str) -> bool:
    """True wenn irgendwo ein «Variante N»-Block steht, auch nach einer Ergebniszeile."""
    return any(_VARIANT_HEAD.match(chunk) for chunk in _variant_chunks(text))


def times_table_ok(n: int) -> bool:
    return TIMES_TABLE_MIN <= int(n) <= TIMES_TABLE_MAX


def explanation_uses_invalid_times_table(text: str) -> bool:
    """True bei «40er-Reihe» u. ä. — Einmaleins gilt nur 2–12."""
    for match in _REIHE_CLAIM.finditer(str(text or "")):
        if not times_table_ok(int(match.group(1))):
            return True
    return False


def _variant_body(chunk: str) -> str:
    text = _VARIANT_HEAD.sub("", str(chunk or "").strip())
    text = text.replace(",", ".")
    return re.sub(r"\s+", " ", text).strip().lower()


def _bodies_near_duplicate(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= 0.92


def distinct_variant_count(text: str) -> int:
    """Zählt inhaltlich verschiedene Varianten, nicht nur «Variante N»-Labels."""
    chunks = _variant_chunks(text)
    labeled = [chunk for chunk in chunks if _VARIANT_HEAD.match(chunk)]
    if not labeled:
        return 1 if str(text or "").strip() else 0
    unique: list[str] = []
    for chunk in labeled:
        body = _variant_body(chunk)
        if not body:
            continue
        if any(_bodies_near_duplicate(body, seen) for seen in unique):
            continue
        unique.append(body)
    return len(unique)


def collapse_duplicate_variants(text: str) -> str:
    """Entfernt wortgleiche / fast gleiche Varianten-Blöcke, Labels neu nummerieren."""
    original = str(text or "").strip()
    chunks = _variant_chunks(original)
    labeled = [chunk for chunk in chunks if _VARIANT_HEAD.match(chunk)]
    if len(labeled) < 2:
        return original
    unique: list[str] = []
    seen: list[str] = []
    for chunk in labeled:
        body = _variant_body(chunk)
        if not body or any(_bodies_near_duplicate(body, prev) for prev in seen):
            continue
        seen.append(body)
        unique.append(chunk)
    if len(unique) == len(labeled):
        return original
    return _number_mul_variants(unique) or unique[0]


def _clarify_step_separators(text: str) -> str:
    """Verhindert '65, 5 ·' → gelesen als 65,5."""
    return _STEP_COMMA.sub(r"\1. Dann ", str(text or ""))


def _equation_restates_problem(equation: str, question: str) -> bool:
    parsed = parse_arithmetic_operands(question)
    if not parsed:
        return False
    op, a, b = parsed
    if op == "add":
        expected = a + b
    elif op == "sub":
        expected = a - b
    elif op == "mul":
        expected = a * b
    elif op == "div":
        if abs(b) < 1e-12:
            return False
        expected = a / b
    else:
        return False
    nums = [_to_float(raw) for raw in re.findall(_NUM, equation)]
    if len(nums) < 3:
        return False
    left = {round(nums[0], 6), round(nums[1], 6)}
    operands = {round(a, 6), round(b, 6)}
    return left == operands and abs(nums[2] - expected) < 1e-4


def _chunk_has_intermediate(chunk: str, question: str) -> bool:
    matches = list(_EQUATION.finditer(chunk))
    if not matches:
        return False
    return any(not _equation_restates_problem(match.group(0), question) for match in matches)


def _chunks_for_derivation(text: str, question: str = "") -> list[str]:
    """Führende «Ergebnis zuerst»-Zeile vor Variante 1 zählt nicht als eigener Weg."""
    chunks = _variant_chunks(text)
    if len(chunks) < 2:
        return chunks
    first, *rest = chunks
    if _VARIANT_HEAD.match(first):
        return chunks
    if not any(_VARIANT_HEAD.match(chunk) for chunk in rest):
        return chunks
    if question:
        if _chunk_has_intermediate(first, question):
            return chunks
        return rest
    if _EQUATION.search(first) and len(first) > 80:
        return chunks
    return rest


def explanation_has_derivation(explanation: str, question: str = "") -> bool:
    """True nur wenn jede Variante eine Zwischenrechnung hat, nicht nur a · b = Ergebnis."""
    expl = str(explanation or "").strip()
    if not expl:
        return False
    chunks = _chunks_for_derivation(expl, question)
    if question:
        if len(chunks) >= 2:
            return all(_chunk_has_intermediate(chunk, question) for chunk in chunks)
        if chunks:
            return _chunk_has_intermediate(chunks[0], question)
        return False
    if len(chunks) >= 2:
        return all(_EQUATION.search(chunk) for chunk in chunks)
    return bool(_EQUATION.search(expl))


def explanation_is_weak(explanation: str, question: str) -> bool:
    expl = str(explanation or "").strip()
    if not expl:
        return True
    if explanation_uses_invalid_times_table(expl):
        return True
    if explanation_has_derivation(expl, question):
        return False
    if _WEAK_EXPLANATION.search(expl):
        return True
    computable = (
        parse_arithmetic_operands(question) is not None or try_compute_from_question(question) is not None
    )
    if computable:
        return True
    return len(expl) < 40


def _join_variants(primary: str, alt: str | None) -> str:
    if alt:
        return f"{primary}\n\n{alt}"
    return primary


def _decimal_places(value: float) -> int:
    text = f"{value:.10f}".rstrip("0")
    if "." not in text:
        return 0
    return len(text.split(".")[1])


def _add_alternative_steps(a: float, b: float, result: float) -> str | None:
    """Zerlegung in Ganze + Dezimalteile."""
    if abs(a - round(a)) >= 1e-6 or abs(b - round(b)) >= 1e-6:
        a_whole = int(a) if a >= 0 else -int(-a)
        a_frac = round(a - a_whole, 10)
        b_whole = int(b) if b >= 0 else -int(-b)
        b_frac = round(b - b_whole, 10)
        if a_whole == 0 and b_whole == 0:
            return None
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
        if a_whole == 0 and b_whole == 0:
            return None
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


def _scale_to_int_pair(a: float, b: float) -> tuple[int, int, int]:
    scale = max(_decimal_places(a), _decimal_places(b))
    factor = 10**scale
    return int(round(a * factor)), int(round(b * factor)), scale


def _add_column_carry_notes(scaled_a: int, scaled_b: int) -> str | None:
    width = max(len(str(scaled_a)), len(str(scaled_b)))
    a_digits = [int(ch) for ch in str(scaled_a).zfill(width)]
    b_digits = [int(ch) for ch in str(scaled_b).zfill(width)]
    carry = 0
    notes: list[str] = []
    for index, (da, db) in enumerate(zip(a_digits, b_digits, strict=True)):
        place = width - index
        total = da + db + carry
        next_carry = total // 10
        if next_carry and index < width - 1:
            notes.append(
                f"Stelle {place}: {da} + {db} = {total}, schreibe {total % 10}, Merke {next_carry}."
            )
        elif total >= 10:
            notes.append(f"Stelle {place}: {da} + {db} = {total}, schreibe {total % 10}.")
        carry = next_carry
    return " ".join(notes) if notes else None


def _sub_column_borrow_notes(scaled_a: int, scaled_b: int) -> str | None:
    width = max(len(str(scaled_a)), len(str(scaled_b)))
    a_digits = [int(ch) for ch in str(scaled_a).zfill(width)]
    b_digits = [int(ch) for ch in str(scaled_b).zfill(width)]
    notes: list[str] = []
    for index in range(width):
        da = a_digits[index]
        db = b_digits[index]
        if da >= db:
            continue
        place = width - index
        notes.append(
            f"Stelle {place}: {da} < {db}, entlehne 1 → {da + 10} − {db} = {da + 10 - db}."
        )
        borrow_from = index - 1
        while borrow_from >= 0 and a_digits[borrow_from] == 0:
            borrow_from -= 1
        if borrow_from >= 0:
            a_digits[borrow_from] -= 1
        a_digits[index] = da + 10
    return " ".join(notes) if notes else None


def _add_column_steps(a: float, b: float, result: float) -> str:
    scaled_a, scaled_b, scale = _scale_to_int_pair(a, b)
    total = scaled_a + scaled_b
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    bits = [f"Variante 1 (Spaltenrechnung): {a_s} + {b_s}."]
    carry = _add_column_carry_notes(scaled_a, scaled_b)
    if carry:
        bits.append(carry)
    if scale:
        bits.append(
            f"Ohne Komma: {_fmt_num(float(scaled_a))} + {_fmt_num(float(scaled_b))} = "
            f"{_fmt_num(float(total))}."
        )
        stelle = "Stelle" if scale == 1 else "Stellen"
        bits.append(f"Komma {scale} {stelle} nach links: {r_s}.")
    else:
        bits.append(
            f"Rechne: {_fmt_num(float(scaled_a))} + {_fmt_num(float(scaled_b))} = {r_s}."
        )
    return " ".join(bits)


def _sub_column_steps(a: float, b: float, result: float) -> str:
    scaled_a, scaled_b, scale = _scale_to_int_pair(a, b)
    diff = scaled_a - scaled_b
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    bits = [f"Variante 1 (Spaltenrechnung): {a_s} − {b_s}."]
    borrow = _sub_column_borrow_notes(scaled_a, scaled_b)
    if borrow:
        bits.append(borrow)
    if scale:
        bits.append(
            f"Ohne Komma: {_fmt_num(float(scaled_a))} − {_fmt_num(float(scaled_b))} = "
            f"{_fmt_num(float(diff))}."
        )
        stelle = "Stelle" if scale == 1 else "Stellen"
        bits.append(f"Komma {scale} {stelle} nach links: {r_s}.")
    else:
        bits.append(
            f"Rechne: {_fmt_num(float(scaled_a))} − {_fmt_num(float(scaled_b))} = {r_s}."
        )
    return " ".join(bits)


def _add_kopf_steps(a: float, b: float, result: float) -> str | None:
    a_whole = int(a) if a >= 0 else -int(-a)
    a_frac = round(a - a_whole, 10)
    b_whole = int(b) if b >= 0 else -int(-b)
    b_frac = round(b - b_whole, 10)
    if a_whole == 0 and b_whole == 0:
        scaled_a, scaled_b, scale = _scale_to_int_pair(a, b)
        total = scaled_a + scaled_b
        stelle = "Stelle" if scale == 1 else "Stellen"
        return (
            f"Variante 2 (Kopfrechnen): {_fmt_num(a)} + {_fmt_num(b)} — "
            f"ohne Komma: {_fmt_num(float(scaled_a))} + {_fmt_num(float(scaled_b))} = "
            f"{_fmt_num(float(total))}. Komma {scale} {stelle} nach links: {_fmt_num(result)}."
        )
    parts = [f"Variante 2 (Kopfrechnen): {_fmt_num(a)} + {_fmt_num(b)}."]
    carry_whole = 0
    if abs(a_frac) >= 1e-9 or abs(b_frac) >= 1e-9:
        frac_sum = round(a_frac + b_frac, 10)
        parts.append(
            f"Zuerst Dezimalteile: {_fmt_num(a_frac)} + {_fmt_num(b_frac)} = {_fmt_num(frac_sum)}."
        )
        if frac_sum >= 1 - 1e-9:
            carry_whole = 1
            parts.append("1 zum Ganzen übertragen.")
    whole_sum = a_whole + b_whole + carry_whole
    if a_whole or b_whole or carry_whole:
        bits = [f"{_fmt_num(float(a_whole))}", f"{_fmt_num(float(b_whole))}"]
        if carry_whole:
            bits.append("1")
        parts.append(f"Ganze: {' + '.join(bits)} = {_fmt_num(float(whole_sum))}.")
    parts.append(f"Ergebnis: {_fmt_num(result)}.")
    return " ".join(parts)


def _sub_kopf_steps(a: float, b: float, result: float) -> str | None:
    a_whole = int(a) if a >= 0 else -int(-a)
    a_frac = round(a - a_whole, 10)
    b_whole = int(b) if b >= 0 else -int(-b)
    b_frac = round(b - b_whole, 10)
    if a_whole == 0 and b_whole == 0:
        scaled_a, scaled_b, scale = _scale_to_int_pair(a, b)
        diff = scaled_a - scaled_b
        stelle = "Stelle" if scale == 1 else "Stellen"
        return (
            f"Variante 2 (Kopfrechnen): {_fmt_num(a)} − {_fmt_num(b)} — "
            f"ohne Komma: {_fmt_num(float(scaled_a))} − {_fmt_num(float(scaled_b))} = "
            f"{_fmt_num(float(diff))}. Komma {scale} {stelle} nach links: {_fmt_num(result)}."
        )
    parts = [f"Variante 2 (Kopfrechnen): {_fmt_num(a)} − {_fmt_num(b)}."]
    borrow_whole = 0
    if abs(a_frac) >= 1e-9 or abs(b_frac) >= 1e-9:
        if a_frac < b_frac - 1e-9:
            borrow_whole = 1
            a_frac = round(a_frac + 1, 10)
            parts.append("Vom Ganzen 1 entlehnen für die Dezimalteile.")
        frac_diff = round(a_frac - b_frac, 10)
        parts.append(
            f"Dezimalteile: {_fmt_num(a_frac)} − {_fmt_num(b_frac)} = {_fmt_num(frac_diff)}."
        )
    whole_diff = a_whole - b_whole - borrow_whole
    if a_whole or b_whole or borrow_whole:
        parts.append(
            f"Ganze: {_fmt_num(float(a_whole))} − {_fmt_num(float(b_whole))}"
            f"{f' − 1' if borrow_whole else ''} = {_fmt_num(float(whole_diff))}."
        )
    parts.append(f"Ergebnis: {_fmt_num(result)}.")
    return " ".join(parts)


def _add_steps(a: float, b: float, result: float) -> str:
    column = _add_column_steps(a, b, result)
    kopf = _add_kopf_steps(a, b, result)
    zerlegung = _add_alternative_steps(a, b, result)
    variants = [column, kopf]
    if zerlegung:
        variants.append(zerlegung.replace("Variante 2", "Variante 3", 1))
    return _number_mul_variants(variants) or column


def _sub_steps(a: float, b: float, result: float) -> str:
    column = _sub_column_steps(a, b, result)
    kopf = _sub_kopf_steps(a, b, result)
    zerlegung = _sub_alternative_steps(a, b, result)
    variants = [column, kopf]
    if zerlegung:
        variants.append(zerlegung.replace("Variante 2", "Variante 3", 1))
    return _number_mul_variants(variants) or column


def _divisor_trailing_zero_count(divisor: int) -> int | None:
    if divisor <= 0:
        return None
    count = 0
    value = divisor
    while value % 10 == 0:
        count += 1
        value //= 10
    if value != 1:
        return None
    return count


def _div_kopf_nullen_steps(a: float, b: float, result: float) -> str | None:
    """Kopfrechnen durch 10/100/…: korrekte Anzahl Nullen am Dividenden streichen."""
    if abs(a - round(a)) >= 1e-6 or abs(b - round(b)) >= 1e-6:
        return None
    b_int = int(round(b))
    zeros = _divisor_trailing_zero_count(b_int)
    if zeros is None:
        return None
    a_int = int(round(a))
    stripped = a_int
    for _ in range(zeros):
        if stripped % 10 != 0:
            return None
        stripped //= 10
    if not _near(float(stripped), result):
        return None
    label = "Nullen" if zeros > 1 else "Null"
    return (
        f"Variante 3 (Kopfrechnen): {_fmt_num(float(a_int))} ÷ {b_int} — "
        f"durch {b_int} teilen heißt {zeros} {label} am Ende weglassen: "
        f"{_fmt_num(float(a_int))} → {_fmt_num(float(stripped))}."
    )


def _reihe_label(divisor: int) -> str | None:
    if not times_table_ok(divisor):
        return None
    return f"{divisor}er-Reihe"


def _split_trailing_tens(n: int) -> tuple[int, int]:
    if n <= 0:
        return n, 0
    zeros = 0
    value = abs(int(n))
    while value % 10 == 0:
        value //= 10
        zeros += 1
    return value, zeros


def _div_kuerzen_cancel_zeros(a: float, b: float, result: float) -> str | None:
    """960 : 40 → Nullen streichen → 96 : 4 (4er-Reihe)."""
    if abs(a - round(a)) >= 1e-6 or abs(b - round(b)) >= 1e-6:
        return None
    a_int, b_int = int(round(a)), int(round(b))
    if a_int <= 0 or b_int <= 0:
        return None
    _core_b, zeros_b = _split_trailing_tens(b_int)
    _core_a, zeros_a = _split_trailing_tens(a_int)
    cancel = min(zeros_a, zeros_b)
    if cancel < 1:
        return None
    a_reduced = a_int // (10 ** cancel)
    b_reduced = b_int // (10 ** cancel)
    if b_reduced <= 0 or a_reduced % b_reduced != 0:
        return None
    if not times_table_ok(b_reduced):
        return None
    quotient = a_reduced // b_reduced
    if not _near(float(quotient), result):
        return None
    reihe = _reihe_label(b_reduced)
    zeros_word = "Null" if cancel == 1 else "Nullen"
    return (
        f"Variante 1 (Kürzen): {_fmt_num(float(a_int))} ÷ {b_int} — "
        f"{cancel} {zeros_word} streichen: {_fmt_num(float(a_reduced))} ÷ {b_reduced}. "
        f"Aus der {reihe}: {_fmt_num(float(a_reduced))} ÷ {b_reduced} = {_fmt_num(float(quotient))}."
    )


def _div_kuerzen_factor_power10(a: float, b: float, result: float) -> str | None:
    """40 = 4 × 10: zuerst ÷10, dann 4er-Reihe."""
    if abs(b - round(b)) >= 1e-6:
        return None
    b_int = int(round(b))
    if b_int <= 0:
        return None
    core_b, zeros_b = _split_trailing_tens(b_int)
    if zeros_b < 1 or not times_table_ok(core_b):
        return None
    power = 10 ** zeros_b
    mid = a / power
    final = mid / core_b
    if not _near(final, result):
        return None
    reihe = _reihe_label(core_b)
    if zeros_b == 1:
        shift = "durch 10 teilen (Komma eine Stelle / eine Null)"
    else:
        shift = (
            f"durch {power} teilen (Komma {zeros_b} Stellen / {zeros_b} Nullen)"
        )
    return (
        f"Variante 2 (Zehnerpotenz): {b_int} = {core_b} × {power}. "
        f"Zuerst {shift}: {_fmt_num(a)} → {_fmt_num(mid)}. "
        f"Dann aus der {reihe}: {_fmt_num(mid)} ÷ {core_b} = {_fmt_num(result)}."
    )


def _div_kuerzen_gcd(a: float, b: float, result: float) -> str | None:
    """90 : 150 — durch gcd kürzen, Rest mit Einmaleins wenn möglich."""
    if abs(a - round(a)) >= 1e-6 or abs(b - round(b)) >= 1e-6:
        return None
    a_int, b_int = int(round(a)), int(round(b))
    if a_int <= 0 or b_int <= 0:
        return None
    g = math.gcd(a_int, b_int)
    if g <= 1:
        return None
    a2, b2 = a_int // g, b_int // g
    if b2 <= 1:
        return None
    if not _near(a2 / b2, result):
        return None
    extra = f"{_fmt_num(float(a2))} ÷ {b2} = {_fmt_num(result)}"
    reihe = _reihe_label(b2)
    if reihe:
        extra = f"Aus der {reihe}: {extra}"
    return (
        f"Variante 1 (Kürzen): {_fmt_num(float(a_int))} ÷ {b_int} — "
        f"durch {g} kürzen: {_fmt_num(float(a2))} ÷ {b2}. {extra}."
    )


def _place_unit(decimals: int) -> str:
    return {1: "Zehntel", 2: "Hundertstel", 3: "Tausendstel"}.get(decimals, f"10⁻{decimals}-tel")


def _integer_place_parts(n: int) -> list[int]:
    """24 → [20, 4], 135 → [100, 30, 5]. Nullstellen entfallen."""
    n = abs(n)
    parts: list[int] = []
    place = 1
    while n:
        digit = n % 10
        if digit:
            parts.append(digit * place)
        n //= 10
        place *= 10
    parts.reverse()
    return parts


def _number_mul_variants(parts: list[str | None]) -> str:
    numbered: list[str] = []
    index = 1
    for part in parts:
        if not part:
            continue
        numbered.append(re.sub(r"^Variante \d+", f"Variante {index}", part.strip(), count=1))
        index += 1
    if not numbered:
        return ""
    text = numbered[0]
    for extra in numbered[1:]:
        text = _join_variants(text, extra)
    return text


def _find_scale_for_division(value: float, divisor: int, *, max_decimals: int = 4) -> tuple[int, int] | None:
    # decimals=0 nur bei echten Ganzzahlen — sonst rundet round(89.7) zu 90 und
    # _place_unit(0) wird zu «10⁻0-tel».
    start = 0 if abs(value - round(value)) < 1e-6 else 1
    for decimals in range(start, max_decimals + 1):
        scaled = int(round(value * (10**decimals)))
        if scaled > 0 and scaled % divisor == 0:
            return scaled, decimals
    return None


def _find_scale_for_fraction(frac: float, divisor: int, *, max_decimals: int = 4) -> tuple[int, int] | None:
    if frac <= 0:
        return None
    for decimals in range(1, max_decimals + 1):
        scaled = int(round(frac * (10**decimals)))
        if scaled > 0 and scaled % divisor == 0:
            return scaled, decimals
    return None


def _div_reihen_scaled(a: float, b_int: int, result: float) -> str | None:
    """Reihen-Weg über skalierte Ganzzahl, wenn Zerlegung am Komma nicht passt."""
    full_scale = _find_scale_for_division(a, b_int)
    if full_scale is None:
        return None
    scaled, decimals = full_scale
    quotient = scaled // b_int
    unit = _place_unit(decimals)
    reihe = _reihe_label(b_int)
    if not reihe:
        return None
    v_result = quotient / (10**decimals)
    return (
        f"Variante 1 (Reihen): {_fmt_num(a)} = {scaled} {unit}. "
        f"Aus der {reihe}: {scaled} ÷ {b_int} = {quotient}. "
        f"Komma {decimals} Stelle{'n' if decimals > 1 else ''} nach links: {_fmt_num(v_result)}."
    )


def _div_steps_reihen(a: float, b: float, result: float) -> str | None:
    """Zerlegung am Komma + Einmaleins-Reihe des Divisors."""
    if abs(b - round(b)) >= 1e-6:
        return None
    b_int = int(round(b))
    if b_int <= 0:
        return None

    whole = int(a) if a >= 0 else -int(-a)
    frac = round(a - whole, 10)
    reihe = _reihe_label(b_int)
    if not reihe:
        return None
    a_s, r_s = _fmt_num(a), _fmt_num(result)

    if frac <= 0:
        if whole % b_int == 0:
            q = whole // b_int
            return (
                f"Variante 1 (Reihen): {a_s} ÷ {b_int}. "
                f"Aus der {reihe}: {_fmt_num(float(whole))} ÷ {b_int} = {_fmt_num(float(q))}."
            )
        return _div_reihen_scaled(a, b_int, result)

    frac_scale = _find_scale_for_fraction(frac, b_int)
    if frac_scale is None:
        return _div_reihen_scaled(a, b_int, result)
    scaled_frac, frac_decimals = frac_scale
    q_frac_part = scaled_frac // b_int
    v_frac = q_frac_part / (10**frac_decimals)
    unit = _place_unit(frac_decimals)

    if whole > 0 and whole % b_int == 0:
        q_whole = whole // b_int
        return (
            f"Variante 1 (Reihen & Zerlegung): {a_s} = {_fmt_num(float(whole))} + {_fmt_num(frac)}. "
            f"Aus der {reihe}: {_fmt_num(float(whole))} ÷ {b_int} = {_fmt_num(float(q_whole))}. "
            f"Den Rest als {scaled_frac} {unit}: {scaled_frac} ÷ {b_int} = {q_frac_part} (wieder {reihe}). "
            f"{q_frac_part} {unit} = {_fmt_num(v_frac)}. "
            f"Addiere: {_fmt_num(float(q_whole))} + {_fmt_num(v_frac)} = {r_s}."
        )

    if whole == 0:
        return (
            f"Variante 1 (Reihen): {a_s} = {scaled_frac} {unit}. "
            f"Aus der {reihe}: {scaled_frac} ÷ {b_int} = {q_frac_part}. "
            f"Komma {frac_decimals} Stelle{'n' if frac_decimals > 1 else ''} nach links: {_fmt_num(v_frac)}."
        )
    return _div_reihen_scaled(a, b_int, result)


def _div_steps_stellenwert(a: float, b: float, result: float) -> str | None:
    if abs(b - round(b)) >= 1e-6:
        return None
    b_int = int(round(b))
    if b_int == 0:
        return None
    if abs(a - round(a)) < 1e-6:
        return None
    full_scale = _find_scale_for_division(a, b_int)
    if full_scale is None:
        return None
    scaled, decimals = full_scale
    unit = _place_unit(decimals)
    quotient = scaled // b_int
    return (
        f"Variante 2 (Komma verschieben): {_fmt_num(a)} = {scaled} {unit}. "
        f"Teile: {scaled} ÷ {b_int} = {quotient}. "
        f"Komma {decimals} Stelle{'n' if decimals > 1 else ''} zurück: {_fmt_num(result)}."
    )


def _div_steps(a: float, b: float, result: float) -> str:
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    if abs(b - round(b)) >= 1e-6:
        return f"Variante 1: {a_s} ÷ {b_s} = {r_s}."
    b_int = int(round(b))
    if b_int == 0:
        return f"Variante 1: {a_s} ÷ {b_s} = {r_s}."

    reihen = _div_steps_reihen(a, b, result)
    cancel = _div_kuerzen_cancel_zeros(a, b, result)
    factor = _div_kuerzen_factor_power10(a, b, result)
    gcd_v = _div_kuerzen_gcd(a, b, result)
    alt = _div_steps_stellenwert(a, b, result)
    kopf = _div_kopf_nullen_steps(a, b, result)
    if times_table_ok(b_int):
        parts = [reihen, alt, kopf, cancel]
    elif _divisor_trailing_zero_count(b_int) is not None:
        parts = [kopf, alt, cancel, factor]
    else:
        parts = [cancel, factor, gcd_v, alt, kopf]
    merged = _number_mul_variants([variant for variant in parts if variant])
    if merged:
        return merged
    computed = a / b_int
    return (
        f"Variante 1: {_fmt_num(a)} ÷ {b_int} = {_fmt_num(computed)}.\n\n"
        f"Variante 2: Rechnung nachprüfen — welche Antwort passt am besten zu {_fmt_num(computed)}?"
    )


def _question_mul_style(question: str) -> str:
    text = str(question or "")
    if _WRITTEN_HINT.search(text):
        return "written"
    if _MENTAL_HINT.search(text):
        return "mental"
    if _NOTES_HINT.search(text):
        return "notes"
    return "default"


def _mul_by_digit_with_carry(top: int, digit: int) -> tuple[int, list[str]]:
    """Ziffer × mehrstellige Zahl. Gibt (Teilprodukt, Überträge LTR über den Top-Ziffern) zurück."""
    n = len(str(top))
    if digit == 0:
        return 0, [""] * n
    top_digits = [int(ch) for ch in reversed(str(top))]
    written: list[str] = []
    carries_from_right: list[str] = [""] * n
    carry = 0
    last = n - 1
    for i, td in enumerate(top_digits):
        total = td * digit + carry
        if i == last:
            written.extend(reversed(str(total)))
            carry = 0
        else:
            write = total % 10
            carry = total // 10
            written.append(str(write))
            if carry:
                carries_from_right[i + 1] = str(carry)
    product = int("".join(reversed(written)))
    carries_ltr = list(reversed(carries_from_right))
    return product, carries_ltr


def _mul_column_steps(a_int: int, b: float, result: float) -> str | None:
    """Spaltenmultiplikation: Kurztext plus strukturierte Darstellung für das Frontend."""
    if a_int <= 0 or b <= 0:
        return None
    decimals = _decimal_places(b)
    if decimals < 1:
        return None
    top = int(round(b * (10**decimals)))
    if top <= 0:
        return None
    raw = a_int * top
    stelle = "Stelle" if decimals == 1 else "Stellen"
    dez = "Dezimalstelle" if decimals == 1 else "Dezimalstellen"
    bottom_digits = [int(ch) for ch in reversed(str(a_int))]
    partials: list[int] = []
    carries: list[str] = [""] * len(str(top))
    for shift, digit in enumerate(bottom_digits):
        if digit == 0:
            continue
        product, row_carries = _mul_by_digit_with_carry(top, digit)
        shifted = product * (10**shift)
        partials.append(shifted)
        if shift == 0:
            carries = row_carries
    payload = {
        "kind": "column_mul",
        "top": str(top),
        "bottom": str(a_int),
        "carries": carries,
        "partials": [str(p) for p in partials],
        "total": str(raw),
        "decimals": decimals,
        "result": _fmt_num(result),
    }
    marker = f"<<spalten:{json.dumps(payload, separators=(',', ':'))}>>"
    bits = [
        f"Variante 1 (Spaltenrechnung): {marker}",
        f"Rechne ohne Komma: {_fmt_num(float(a_int))} × {top} = {_fmt_num(float(raw))}.",
    ]
    if len(partials) > 1:
        bits.append(f"Teilprodukte: {' + '.join(str(p) for p in partials)} = {raw}.")
    bits.append(
        f"{_fmt_num(b)} hat {decimals} {dez} — Komma im Ergebnis "
        f"{decimals} {stelle} nach links: {_fmt_num(result)}."
    )
    return " ".join(bits)


def _mul_written_steps(a_int: int, b: float, result: float) -> str | None:
    decimals = _decimal_places(b)
    if decimals < 1:
        return None
    scaled = int(round(b * (10**decimals)))
    raw = a_int * scaled
    stelle = "Stelle" if decimals == 1 else "Stellen"
    dez = "Dezimalstelle" if decimals == 1 else "Dezimalstellen"
    return (
        f"Variante 1 (schriftlich): Rechne ohne Komma: "
        f"{_fmt_num(float(a_int))} × {scaled} = {_fmt_num(float(raw))}. "
        f"{_fmt_num(b)} hat {decimals} {dez} — Komma im Ergebnis "
        f"{decimals} {stelle} nach links: {_fmt_num(result)}."
    )


def _mul_reihe_for_frac(a_int: int, frac: float) -> str | None:
    """8 × 0,5 über 8 × 5 = 40, Komma eine Stelle → 4."""
    decimals = _decimal_places(frac)
    if decimals < 1:
        return None
    scaled = int(round(frac * (10**decimals)))
    if scaled <= 0:
        return None
    product = a_int * scaled
    shifted = product / (10**decimals)
    unit = _place_unit(decimals)
    stelle = "Stelle" if decimals == 1 else "Stellen"
    reihe = _reihe_label(a_int)
    series = f" (aus der {reihe})" if reihe else ""
    return (
        f"{_fmt_num(float(a_int))} × {scaled} = {_fmt_num(float(product))}"
        f"{series}. "
        f"Komma {decimals} {stelle} nach links ({unit}): {_fmt_num(shifted)}"
    )


def _mul_kopf_steps(a_int: int, b: float, result: float) -> str:
    whole = int(b) if b >= 0 else -int(-b)
    frac = round(b - whole, 10)
    a_s = _fmt_num(float(a_int))
    parts = [f"Variante 1 (Kopfrechnen): {a_s} × {_fmt_num(b)}."]
    if whole:
        parts.append(f"Zuerst {a_s} × {_fmt_num(float(whole))} = {_fmt_num(float(a_int * whole))}.")
    if abs(frac) >= 1e-9:
        reihe = _mul_reihe_for_frac(a_int, frac)
        if reihe:
            parts.append(
                f"Dann {a_s} × {_fmt_num(frac)}: {reihe} — also {a_s} × {_fmt_num(frac)} = {_fmt_num(a_int * frac)}."
            )
        else:
            parts.append(f"Dann {a_s} × {_fmt_num(frac)} = {_fmt_num(a_int * frac)}.")
    if whole and abs(frac) >= 1e-9:
        parts.append(
            f"Addiere: {_fmt_num(float(a_int * whole))} + {_fmt_num(a_int * frac)} = {_fmt_num(result)}."
        )
    else:
        parts.append(f"Ergebnis: {_fmt_num(result)}.")
    return " ".join(parts)


def _mul_zerlegung_steps(a_int: int, b: float, result: float) -> str | None:
    whole = int(b) if b >= 0 else -int(-b)
    frac = round(b - whole, 10)
    if abs(frac) < 1e-9:
        return None
    a_s = _fmt_num(float(a_int))
    part_whole = a_int * whole
    part_frac = a_int * frac
    return (
        f"Variante 2 (Zerlegung): {_fmt_num(b)} = {_fmt_num(float(whole))} + {_fmt_num(frac)}. "
        f"{a_s} × {_fmt_num(float(whole))} = {_fmt_num(part_whole)}. "
        f"Dann {a_s} × {_fmt_num(frac)} = {_fmt_num(part_frac)}. "
        f"Zusammen: {_fmt_num(part_whole)} + {_fmt_num(part_frac)} = {_fmt_num(result)}."
    )


def _mul_zehner_einer_steps(a_int: int, b: float, result: float) -> str | None:
    """Zerlegung des mehrstelligen Faktors, z. B. 24 = 20 + 4, beide × Dezimalzahl."""
    if a_int <= 0 or b <= 0 or a_int % 10 == 0:
        return None
    parts = _integer_place_parts(a_int)
    if len(parts) < 2:
        return None
    decimals = _decimal_places(b)
    scaled_b = int(round(b * (10**decimals)))
    label = "Zerlegung Zehner/Einer" if a_int < 100 else "Zerlegung Stellenwerte"
    split = " + ".join(_fmt_num(float(p)) for p in parts)
    bits = [f"Variante 1 ({label}): {_fmt_num(float(a_int))} = {split}."]
    shown_parts: list[str] = []
    for i, part in enumerate(parts):
        shown = (part * scaled_b) / (10**decimals)
        shown_s = _fmt_num(shown)
        shown_parts.append(shown_s)
        eq = f"{_fmt_num(float(part))} × {_fmt_num(b)} = {shown_s}."
        bits.append(eq if i == 0 else f"Dann {eq}")
    bits.append(f"Zusammen: {' + '.join(shown_parts)} = {_fmt_num(result)}.")
    return " ".join(bits)


def _mul_alternative_steps(a: float, b: float, result: float) -> str | None:
    """Dritter Weg über Stellenwert-Zerlegung, z. B. 250,1 → (20+5)×10 + 0,1."""
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
        f"Variante 3 (Stellenwert): {_fmt_num(b)} = {_fmt_num(t_high)}×10 + {_fmt_num(t_low)}×10 + {_fmt_num(frac)}. "
        f"{a_s} × {_fmt_num(t_high)} = {_fmt_num(p_high)}. "
        f"Dann {a_s} × {_fmt_num(t_low)} = {_fmt_num(p_low)}. "
        f"{_fmt_num(p_high)} + {_fmt_num(p_low)} = {_fmt_num(sub_sum)}. "
        f"{_fmt_num(sub_sum)} × 10 = {_fmt_num(prod_whole)}. "
        f"Dann {a_s} × {_fmt_num(frac)} = {_fmt_num(p_frac)}. "
        f"Zusammen: {_fmt_num(prod_whole)} + {_fmt_num(p_frac)} = {_fmt_num(result)}."
    )


def _mul_steps(a: float, b: float, result: float, *, question: str = "") -> str:
    if abs(a - round(a)) >= 1e-6 and abs(b - round(b)) < 1e-6:
        a, b = b, a
    a_s, b_s, r_s = _fmt_num(a), _fmt_num(b), _fmt_num(result)
    if abs(b - round(b)) < 1e-6:
        return f"Rechnung: {a_s} × {b_s} = {r_s}."
    if abs(a - round(a)) < 1e-6 and abs(b - round(b)) >= 1e-6:
        a_int = int(round(a))
        frac = round(b - (int(b) if b >= 0 else -int(-b)), 10)
        if abs(frac) < 1e-9:
            return f"Rechnung: {a_s} × {b_s} = {r_s}."
        written = _mul_written_steps(a_int, b, result)
        column = _mul_column_steps(a_int, b, result)
        kopf = _mul_kopf_steps(a_int, b, result)
        zerlegung = _mul_zerlegung_steps(a_int, b, result)
        zehner = _mul_zehner_einer_steps(a_int, b, result)
        place = _mul_alternative_steps(float(a_int), b, result)
        style = _question_mul_style(question)
        if style == "written":
            variants = [column or written, zehner or zerlegung]
        elif style == "mental":
            variants = [kopf, zehner or written or zerlegung]
        elif style == "notes":
            variants = [zehner or zerlegung, column or written]
        elif zehner:
            variants = [zehner, column or written, zerlegung]
        else:
            variants = [column or written or kopf, zerlegung]
        if place:
            variants.append(place)
        return _number_mul_variants(variants) or f"Rechnung: {a_s} × {b_s} = {r_s}."
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
            return _mul_steps(a, b, expected, question=question)
        if op == "div":
            return _div_steps(a, b, expected)

    if expected is None:
        expected = try_compute_from_question(question)
    if expected is None:
        return None
    return f"Rechnung: Ergebnis = {_fmt_num(expected)}."


def _count_variants(text: str) -> int:
    lower = str(text or "").lower()
    return sum(1 for index in range(1, 10) if f"variante {index}" in lower)


def _extract_from_variant(text: str, start: int = 2) -> str | None:
    lower = text.lower()
    marker = f"variante {start}"
    idx = lower.find(marker)
    if idx < 0:
        return None
    return text[idx:].strip()


def _merge_explanations(primary: str, secondary: str, *, question: str) -> str:
    """Starke Heft-/KI-Erklärung mit unseren Rechenweg-Varianten kombinieren."""
    primary = str(primary or "").strip()
    secondary = str(secondary or "").strip()
    if not primary:
        return secondary
    if not secondary:
        return primary
    if primary == secondary:
        return primary
    if explanation_is_weak(primary, question):
        return secondary

    p_variants = distinct_variant_count(primary)
    s_variants = distinct_variant_count(secondary)

    if p_variants >= 2 and explanation_has_derivation(primary, question):
        return primary

    if p_variants == 0 and not explanation_is_weak(primary, question):
        if s_variants >= 2:
            alt = _extract_from_variant(secondary, 2)
            if alt:
                return f"Variante 1 (Heft): {primary}\n\n{alt}"
        alt_only = _extract_from_variant(secondary, 2) or secondary
        return f"Variante 1 (Heft): {primary}\n\n{alt_only}"

    if p_variants == 1 and s_variants >= 2:
        alt = _extract_from_variant(secondary, 2)
        if alt:
            if not _text_has_variant_label(primary):
                return f"Variante 1 (Heft): {primary}\n\n{alt}"
            return f"{primary}\n\n{alt}"

    return _join_variants(primary, secondary)


def merge_worked_variants(primary: str, secondary: str, *, question: str) -> str:
    """Öffentlicher Einstieg: Heft-/KI-Text mit Template-Varianten kombinieren."""
    return _merge_explanations(primary, secondary, question=question)


def _near(a: float, b: float) -> bool:
    return abs(a - b) < 1e-3


def _closes_with_expected(text: str, expected: float) -> bool:
    stripped = str(text or "").rstrip()
    if not stripped:
        return False
    closing = re.search(
        rf"(?:zusammen|ergebnis|gesamt)\s*:?\s*.*?=\s*({_NUM})\s*\.?\s*$",
        stripped,
        re.I | re.S,
    )
    if closing and _near(_to_float(closing.group(1)), expected):
        return True
    tail_eq = re.search(rf"=\s*({_NUM})\s*\.?\s*$", stripped)
    if tail_eq and _near(_to_float(tail_eq.group(1)), expected):
        eqs = list(_EQUATION.finditer(stripped))
        if eqs:
            last_nums = re.findall(_NUM, eqs[-1].group(0))
            if last_nums and _near(_to_float(last_nums[-1]), expected):
                return True
        elif _near(_to_float(tail_eq.group(1)), expected):
            return True
    return False


def _decomp_partial_products(text: str, a: float, b: float) -> list[float]:
    """Teilprodukte einer Zehner/Einer-Zerlegung, z. B. 10·6,28 und 5·6,28."""
    seen: set[tuple[float, float]] = set()
    pieces_a: list[float] = []
    prods_a: list[float] = []
    pieces_b: list[float] = []
    prods_b: list[float] = []
    for match in _MUL_MENTION.finditer(text or ""):
        x, y = _to_float(match.group(1)), _to_float(match.group(2))
        key = (round(x, 6), round(y, 6))
        swapped = (key[1], key[0])
        if key in seen or swapped in seen:
            continue
        seen.add(key)
        if (_near(x, a) and _near(y, b)) or (_near(x, b) and _near(y, a)):
            continue
        stated = _to_float(match.group(3)) if match.group(3) else None
        prod = stated if stated is not None else x * y
        if _near(y, b):
            pieces_a.append(x)
            prods_a.append(prod)
        elif _near(x, b):
            pieces_a.append(y)
            prods_a.append(prod)
        elif _near(y, a):
            pieces_b.append(x)
            prods_b.append(prod)
        elif _near(x, a):
            pieces_b.append(y)
            prods_b.append(prod)
    if len(pieces_a) >= 2 and _near(sum(pieces_a), a):
        return prods_a
    if len(pieces_b) >= 2 and _near(sum(pieces_b), b):
        return prods_b
    return []


def complete_method_explanation(text: str, question: str, q: dict | None = None) -> str:
    """Hängt die fehlende Summe an eine Strategiewahl-Herleitung, wenn berechenbar."""
    original = str(text or "").strip()
    parsed = parse_arithmetic_operands(question)
    if not parsed or parsed[0] != "mul":
        return original
    _, a, b = parsed
    expected = a * b
    corpus = original
    if q:
        options = q.get("options") or []
        answer = q.get("answer")
        if isinstance(options, list) and isinstance(answer, int) and 0 <= answer < len(options):
            opt = str(options[answer] or "").strip()
            if opt and opt not in original:
                corpus = f"{original}\n{opt}"
    if _closes_with_expected(original, expected) or _closes_with_expected(corpus, expected):
        return original
    products = _decomp_partial_products(corpus, a, b) or _decomp_partial_products(original, a, b)
    if len(products) < 2 or not _near(sum(products), expected):
        return original
    line = f"Zusammen: {' + '.join(_fmt_num(p) for p in products)} = {_fmt_num(expected)}."
    if _fmt_num(expected) in original.replace(".", ",") and "zusammen" in original.lower():
        return original
    return f"{original.rstrip('. ')}. {line}"


def method_explanation_incomplete(text: str, question: str, q: dict | None = None) -> bool:
    original = str(text or "").strip()
    return complete_method_explanation(original, question, q) != original


def enrich_quiz_explanation(q: dict) -> str:
    question = str(q.get("q") or "")
    original = collapse_duplicate_variants(str(q.get("explanation") or "").strip())
    q_type = str(q.get("question_type") or "").strip().lower()

    if q_type == "method":
        filled = complete_method_explanation(original, question, q)
        if explanation_is_weak(filled, question):
            worked = build_worked_solution(question)
            if worked:
                filled = (
                    _merge_explanations(filled, worked, question=question)
                    if filled.strip()
                    else worked
                )
        return _clarify_step_separators(
            filled or "Wähle den Lösungsweg, der zur Aufgabe am besten passt."
        )

    worked = build_worked_solution(question)

    if original and not explanation_is_weak(original, question):
        if worked and distinct_variant_count(original) < 2 and distinct_variant_count(worked) >= 1:
            return _clarify_step_separators(_merge_explanations(original, worked, question=question))
        return _clarify_step_separators(original)

    if worked:
        return _clarify_step_separators(worked)

    return _clarify_step_separators(original)
