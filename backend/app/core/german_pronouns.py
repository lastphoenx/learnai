"""Personalpronomen und Fallunterscheidung — Referenzdaten (nicht KI-Text)."""

from __future__ import annotations

from typing import Any

from app.core.german_declension import normalize_case, normalize_gender

# Personalpronomen 3. Person Sg. — Formen, die in Ersatzproben den Fall zeigen sollen.
_PERSONAL_PRONOUNS: dict[str, dict[str, str]] = {
    "masc": {"nom": "er", "acc": "ihn", "dat": "ihm", "gen": "seiner"},
    "fem": {"nom": "sie", "acc": "sie", "dat": "ihr", "gen": "ihrer"},
    "neut": {"nom": "es", "acc": "es", "dat": "ihm", "gen": "seiner"},
}

_ERSATZ_PRONOUN_TOKENS = frozenset({"er", "sie", "es", "ihn", "ihm", "ihr", "seiner", "ihrer"})


def personal_pronoun(*, gender: str, case: str) -> str | None:
    g = normalize_gender(gender)
    c = normalize_case(case)
    if not g or not c:
        return None
    return _PERSONAL_PRONOUNS.get(g, {}).get(c)


def pronoun_distinguishes_case(gender: str, case_a: str, case_b: str) -> bool:
    """False, wenn das Pronomen in beiden Fällen gleich aussieht (z. B. neut nom/acc)."""
    forms = _PERSONAL_PRONOUNS.get(normalize_gender(gender) or "", {})
    a = forms.get(normalize_case(case_a) or "")
    b = forms.get(normalize_case(case_b) or "")
    if not a or not b:
        return True  # nicht prüfbar → nicht blockieren
    return a != b


def text_mentions_ersatz_pronoun(text: str) -> bool:
    tokens = {t.lower().strip(".,;:!?()„\"'«»") for t in str(text or "").split()}
    return bool(tokens & _ERSATZ_PRONOUN_TOKENS)


def structured_gender_and_case(payload: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Liest Genus/Fall nur aus strukturierten Feldern (grammar / blanks) — kein Text-Raten."""
    if not isinstance(payload, dict):
        return None, None
    grammar = payload.get("grammar")
    if not isinstance(grammar, dict):
        grammar = payload
    gender = normalize_gender(str(grammar.get("gender") or ""))
    case = normalize_case(str(grammar.get("case") or ""))
    if gender and case:
        return gender, case
    blanks = grammar.get("blanks")
    if not isinstance(blanks, list):
        return gender, case
    from app.core.german_declension import parse_grammar_blanks

    parsed = parse_grammar_blanks(blanks)
    if not parsed:
        return gender, case
    first = parsed[0]
    return first.get("gender"), first.get("case")


def ersatzprobe_example_is_useful(payload: dict[str, Any] | str, *, text: str | None = None) -> bool:
    """False nur wenn Genus+Fall bekannt sind und das Pronomen den Fall nicht unterscheidet.

    Bewusst konservativ: ohne strukturierte Metadaten → True (nicht blockieren).
    """
    if isinstance(payload, str):
        blob = payload
        gender, case = None, None
    else:
        blob = text if text is not None else " ".join(
            filter(
                None,
                [
                    str(payload.get("problem") or ""),
                    str(payload.get("example") or ""),
                    *(str(s) for s in (payload.get("steps") or []) if isinstance(payload.get("steps"), list)),
                ],
            )
        )
        gender, case = structured_gender_and_case(payload)
    if not gender or not case:
        return True
    if not text_mentions_ersatz_pronoun(blob):
        return True
    # Nom/Akk sind die kritische Verwechslung bei Ersatzproben; gegen Dativ immer prüfen.
    rivals = ("nom", "acc") if case in {"nom", "acc"} else ("nom", "acc", "dat")
    for other in rivals:
        if other == case:
            continue
        if not pronoun_distinguishes_case(gender, case, other):
            return False
    return True
