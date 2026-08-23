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
_EQUATION = re.compile(
    rf"{_NUM}\s*(?:{_OP_SYMBOL}|[+\-−]|[:÷/])\s*{_NUM}\s*=\s*{_NUM}",
)
_VARIANT_SPLIT = re.compile(r"(?=Variante\s+\d+\s*(?:\([^)]*\))?\s*:)", re.I)
_STEP_COMMA = re.compile(
    rf"(=\s*{_NUM})\s*,\s*(?={_NUM}\s*(?:{_OP_SYMBOL}|[+\-−]|[:÷/]))",
)
_WRITTEN_HINT = re.compile(r"schriftlich", re.I)
_MENTAL_HINT = re.compile(r"im kopf|kopfrechn", re.I)
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
        re.compile(rf"(?:subtraktion|differenz)\s+von\s+({_NUM})\s+und\s+({_NUM})", re.I),
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


def explanation_has_derivation(explanation: str, question: str = "") -> bool:
    """True nur wenn jede Variante eine Zwischenrechnung hat, nicht nur a · b = Ergebnis."""
    expl = str(explanation or "").strip()
    if not expl:
        return False
    chunks = _variant_chunks(expl)
    if question:
        if len(chunks) >= 2:
            return all(_chunk_has_intermediate(chunk, question) for chunk in chunks)
        return _chunk_has_intermediate(expl, question)
    if len(chunks) >= 2:
        return all(_EQUATION.search(chunk) for chunk in chunks)
    return bool(_EQUATION.search(expl))


def explanation_is_weak(explanation: str, question: str) -> bool:
    expl = str(explanation or "").strip()
    if not expl:
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


def _reihe_label(divisor: int) -> str:
    return f"{divisor}er-Reihe"


def _place_unit(decimals: int) -> str:
    return {1: "Zehntel", 2: "Hundertstel", 3: "Tausendstel"}.get(decimals, f"10⁻{decimals}-tel")


def _find_scale_for_division(value: float, divisor: int, *, max_decimals: int = 4) -> tuple[int, int] | None:
    for decimals in range(0, max_decimals + 1):
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

    primary = _div_steps_reihen(a, b, result)
    alt = _div_steps_stellenwert(a, b, result)
    if primary and alt:
        return _join_variants(primary, alt)
    if primary:
        return primary
    if alt:
        return alt
    if abs(a - round(a)) < 1e-6 and int(round(a)) % b_int == 0:
        q = int(round(a)) // b_int
        return (
            f"Variante 1 (Reihen): {_fmt_num(a)} ÷ {b_int}. "
            f"Aus der {_reihe_label(b_int)}: {_fmt_num(float(int(round(a))))} ÷ {b_int} = {_fmt_num(float(q))}."
        )
    # Letzter Ausweg: trotzdem Schritte aus der Berechnung
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
    return "default"


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
    return (
        f"{_fmt_num(float(a_int))} × {scaled} = {_fmt_num(float(product))} "
        f"(aus der {_reihe_label(a_int)}). "
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
        kopf = _mul_kopf_steps(a_int, b, result)
        zerlegung = _mul_zerlegung_steps(a_int, b, result)
        place = _mul_alternative_steps(float(a_int), b, result)
        style = _question_mul_style(question)
        if style == "written" and written:
            primary, alt = written, zerlegung
        elif style == "mental":
            primary, alt = kopf, written or zerlegung
        else:
            primary, alt = written or kopf, zerlegung
        if alt and alt.startswith("Variante 1"):
            alt = re.sub(r"^Variante 1", "Variante 2", alt, count=1)
        text = primary
        if alt:
            text = _join_variants(text, alt)
        if place:
            text = _join_variants(text, place)
        return text
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

    p_variants = _count_variants(primary)
    s_variants = _count_variants(secondary)

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
            return f"{primary}\n\n{alt}"

    return _join_variants(primary, secondary)


def enrich_quiz_explanation(q: dict) -> str:
    question = str(q.get("q") or "")
    original = str(q.get("explanation") or "").strip()
    q_type = str(q.get("question_type") or "").strip().lower()

    if q_type == "method":
        return original or "Wähle den Lösungsweg, der zur Aufgabe am besten passt."

    worked = build_worked_solution(question)

    if original and not explanation_is_weak(original, question):
        if worked and _count_variants(original) < 2 and _count_variants(worked) >= 1:
            return _clarify_step_separators(_merge_explanations(original, worked, question=question))
        return _clarify_step_separators(original)

    if worked:
        return _clarify_step_separators(worked)

    return _clarify_step_separators(original)
