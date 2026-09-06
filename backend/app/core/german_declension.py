"""Deterministische deutsche Deklination (Artikel, Adjektiv, Nomen).

Geschlossenes Regelsystem — analog zu arithmetic_parse für Mathe.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

Case = str  # nom | gen | dat | acc
Gender = str  # masc | fem | neut
Number = str  # sg | pl
DeterminerType = str  # der-word | ein-word | none

_CASE_ALIASES: dict[str, Case] = {
    "nom": "nom",
    "nominativ": "nom",
    "n": "nom",
    "gen": "gen",
    "genitiv": "gen",
    "g": "gen",
    "dat": "dat",
    "dativ": "dat",
    "d": "dat",
    "acc": "acc",
    "akkusativ": "acc",
    "akk": "acc",
    "a": "acc",
}

_GENDER_ALIASES: dict[str, Gender] = {
    "masc": "masc",
    "mask": "masc",
    "maskulin": "masc",
    "m": "masc",
    "fem": "fem",
    "feminin": "fem",
    "f": "fem",
    "neut": "neut",
    "neutrum": "neut",
    "n": "neut",
}

_NUMBER_ALIASES: dict[str, Number] = {
    "sg": "sg",
    "sing": "sg",
    "singular": "sg",
    "s": "sg",
    "pl": "pl",
    "plur": "pl",
    "plural": "pl",
    "p": "pl",
}

# Suffixe für der-Wörter (demonstrativ: d + Suffix → der, des, …)
_DER_WORD_SUFFIXES: dict[tuple[Case, Gender, Number], str] = {
    ("nom", "masc", "sg"): "er",
    ("gen", "masc", "sg"): "es",
    ("dat", "masc", "sg"): "em",
    ("acc", "masc", "sg"): "en",
    ("nom", "fem", "sg"): "e",
    ("gen", "fem", "sg"): "er",
    ("dat", "fem", "sg"): "er",
    ("acc", "fem", "sg"): "e",
    ("nom", "neut", "sg"): "es",
    ("gen", "neut", "sg"): "es",
    ("dat", "neut", "sg"): "em",
    ("acc", "neut", "sg"): "es",
    ("nom", "masc", "pl"): "e",
    ("gen", "masc", "pl"): "er",
    ("dat", "masc", "pl"): "en",
    ("acc", "masc", "pl"): "e",
    ("nom", "fem", "pl"): "e",
    ("gen", "fem", "pl"): "er",
    ("dat", "fem", "pl"): "en",
    ("acc", "fem", "pl"): "e",
    ("nom", "neut", "pl"): "e",
    ("gen", "neut", "pl"): "er",
    ("dat", "neut", "pl"): "en",
    ("acc", "neut", "pl"): "e",
}

# ein-Wörter: gleiche Endungen, aber leer bei Nom/Akk Sg mask./neutr.
_EIN_WORD_EMPTY: frozenset[tuple[Case, Gender, Number]] = frozenset(
    {
        ("nom", "masc", "sg"),
        ("nom", "neut", "sg"),
        ("acc", "neut", "sg"),
    }
)

# Schwache Maskulina (n-Deklination): ausser Nom. Sg. +(e)n
WEAK_MASCULINES: frozenset[str] = frozenset(
    {
        "mensch",
        "junge",
        "herr",
        "bauer",
        "kunde",
        "kollege",
        "experte",
        "präsident",
        "prasident",
        "polizist",
        "elefant",
        "löwe",
        "loewe",
        "hase",
        "affe",
        "bote",
        "gott",
        "kriegsgott",
        "prinz",
        "student",
        "neffe",
        "planet",
        "satellit",
    }
)

# Gemischte Deklination: Gen. Sg. +ns, sonst wie schwach
MIXED_MASCULINES: frozenset[str] = frozenset(
    {
        "name",
        "buchstabe",
        "gedanke",
        "friede",
        "glaube",
        "herz",
        "schnürsenkel",
        "schnursenkel",
    }
)

from app.core.german_prepositions import GENITIVE_PREPOSITIONS

_DER_WORD_BASES: frozenset[str] = frozenset(
    {"d", "der", "die", "das", "dies", "jen", "jeder", "jed", "welch", "manch", "solch", "all"}
)
_EIN_WORD_BASES: frozenset[str] = frozenset(
    {"ein", "kein", "mein", "dein", "sein", "ihr", "unser", "euer", "eig", "einig", "wenig", "viel"}
)

_GENITIVE_ES_ENDINGS = re.compile(r"(s|ß|ss|z|x|sch)$", re.I)


def normalize_case(value: str | None) -> Case | None:
    key = str(value or "").strip().lower()
    return _CASE_ALIASES.get(key)


def normalize_gender(value: str | None) -> Gender | None:
    key = str(value or "").strip().lower()
    return _GENDER_ALIASES.get(key)


def normalize_number(value: str | None) -> Number | None:
    key = str(value or "").strip().lower()
    return _NUMBER_ALIASES.get(key)


def normalize_determiner_type(value: str | None) -> DeterminerType | None:
    key = str(value or "").strip().lower().replace("_", "-")
    if key in {"der-word", "derword", "definite", "bestimmt"}:
        return "der-word"
    if key in {"ein-word", "einword", "indefinite", "unbestimmt", "possessive"}:
        return "ein-word"
    if key in {"none", "strong", "stark", "ohne-artikel"}:
        return "none"
    return None


def _lemma_key(lemma: str) -> str:
    text = unicodedata.normalize("NFKC", str(lemma or "")).strip().lower()
    return text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def noun_declension_class(*, lemma: str, gender: Gender) -> str:
    if gender != "masc":
        return "strong"
    key = _lemma_key(lemma)
    if key in MIXED_MASCULINES:
        return "mixed"
    if key in WEAK_MASCULINES:
        return "weak"
    return "strong"


def _needs_genitive_es(lemma: str) -> bool:
    """+es nur nach s, ß, z, x, sch — sonst +s (Spiel → Spiels, nicht Spieles)."""
    return bool(_GENITIVE_ES_ENDINGS.search(_lemma_key(lemma)))


def _append_n_if_needed(stem: str) -> str:
    lower = stem.lower()
    if lower.endswith(("n", "s")):
        return stem
    return stem + "n"


def _weak_masc_sg_form(lemma: str, *, case: Case) -> str:
    """n-Deklination: Nom. unverändert, sonst -(e)n (Mensch → Menschen, Affe → Affen)."""
    if case == "nom":
        return lemma
    if _lemma_key(lemma).endswith("e"):
        return lemma + "n"
    return lemma + "en"


def _genitive_noun_suffix(*, lemma: str, gender: Gender, declension_class: str) -> str:
    if gender == "fem":
        return ""
    if declension_class == "weak":
        return "en" if _lemma_key(lemma).endswith("e") else "n"
    if declension_class == "mixed":
        if lemma.endswith("e"):
            return "ns"
        if lemma.endswith("z"):
            return "ens"
        return "ns"
    if _needs_genitive_es(lemma):
        return "es"
    return "s"


def decline_noun(*, lemma: str, gender: Gender, number: Number, case: Case) -> str:
    lemma = str(lemma or "").strip()
    if not lemma:
        return ""
    declension_class = noun_declension_class(lemma=lemma, gender=gender)

    if number == "pl" and case == "dat":
        return _append_n_if_needed(lemma)

    if declension_class in {"weak", "mixed"} and gender == "masc" and number == "sg":
        if declension_class == "mixed" and case == "gen":
            return lemma + _genitive_noun_suffix(
                lemma=lemma, gender=gender, declension_class=declension_class
            )
        if declension_class == "weak":
            return _weak_masc_sg_form(lemma, case=case)
        if case == "nom":
            return lemma
        return _weak_masc_sg_form(lemma, case=case)

    if case == "nom":
        return lemma

    if case == "gen":
        if number == "pl":
            return lemma
        suffix = _genitive_noun_suffix(lemma=lemma, gender=gender, declension_class=declension_class)
        return lemma + suffix

    if case == "dat":
        return lemma

    if case == "acc":
        return lemma

    return lemma


def _determiner_suffix(
    *,
    determiner_type: DeterminerType,
    case: Case,
    gender: Gender,
    number: Number,
) -> str:
    if determiner_type == "none":
        return ""
    suffix = _DER_WORD_SUFFIXES.get((case, gender, number), "")
    if determiner_type == "ein-word" and (case, gender, number) in _EIN_WORD_EMPTY:
        return ""
    return suffix


def _decline_determiner(
    *,
    determiner_type: DeterminerType,
    determiner_stem: str,
    case: Case,
    gender: Gender,
    number: Number,
) -> str:
    if determiner_type == "none":
        return ""
    stem = str(determiner_stem or "").strip()
    if not stem and determiner_type == "der-word":
        stem = "d"
    suffix = _determiner_suffix(
        determiner_type=determiner_type,
        case=case,
        gender=gender,
        number=number,
    )
    return f"{stem}{suffix}"


def _adjective_declension_type(determiner_type: DeterminerType) -> str:
    if determiner_type == "none":
        return "strong"
    if determiner_type == "ein-word":
        return "mixed"
    return "weak"


def _adjective_suffix(
    *,
    declension_type: str,
    case: Case,
    gender: Gender,
    number: Number,
) -> str:
    if declension_type == "strong":
        if case == "gen" and gender in {"masc", "neut"} and number == "sg":
            return "en"
        return _DER_WORD_SUFFIXES.get((case, gender, number), "en")

    if declension_type == "mixed":
        if (case, gender, number) in _EIN_WORD_EMPTY:
            return _DER_WORD_SUFFIXES.get((case, gender, number), "en")
        if case == "nom" and number == "sg":
            return "e"
        if case == "acc" and number == "sg" and gender in {"fem", "neut"}:
            return "e"
        return "en"

    # weak
    if case == "nom" and number == "sg":
        return "e"
    if case == "acc" and number == "sg" and gender in {"fem", "neut"}:
        return "e"
    return "en"


def decline_adjective(
    *,
    stem: str,
    determiner_type: DeterminerType,
    case: Case,
    gender: Gender,
    number: Number,
) -> str:
    adj_stem = str(stem or "").strip()
    if not adj_stem:
        return ""
    declension_type = _adjective_declension_type(determiner_type)
    suffix = _adjective_suffix(
        declension_type=declension_type,
        case=case,
        gender=gender,
        number=number,
    )
    return f"{adj_stem}{suffix}"


def decline(
    *,
    lemma: str,
    gender: str,
    number: str,
    case: str,
    determiner_type: str,
    determiner_stem: str = "",
    adjective_stem: str | None = None,
) -> dict[str, str]:
    """Berechnet korrekte Wortformen für eine Nominalphrase."""
    norm_case = normalize_case(case)
    norm_gender = normalize_gender(gender)
    norm_number = normalize_number(number)
    norm_det = normalize_determiner_type(determiner_type)
    if not norm_case or not norm_gender or not norm_number or not norm_det:
        return {"determiner": "", "adjective": "", "noun": ""}

    noun = decline_noun(lemma=lemma, gender=norm_gender, number=norm_number, case=norm_case)
    determiner = _decline_determiner(
        determiner_type=norm_det,
        determiner_stem=determiner_stem,
        case=norm_case,
        gender=norm_gender,
        number=norm_number,
    )
    adjective = ""
    if adjective_stem:
        adjective = decline_adjective(
            stem=adjective_stem,
            determiner_type=norm_det,
            case=norm_case,
            gender=norm_gender,
            number=norm_number,
        )
    return {"determiner": determiner, "adjective": adjective, "noun": noun}


def _normalize_blank_answer(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    return raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def _parse_blank_spec(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    case = normalize_case(str(raw.get("case") or ""))
    gender = normalize_gender(str(raw.get("gender") or ""))
    number = normalize_number(str(raw.get("number") or ""))
    if not case or not gender or not number:
        return None
    determiner_type = normalize_determiner_type(str(raw.get("determiner_type") or raw.get("determiner") or ""))
    part = str(raw.get("part") or raw.get("blank_type") or "word").strip().lower()
    if part not in {"ending", "word", "phrase"}:
        part = "word"
    spec: dict[str, Any] = {
        "case": case,
        "gender": gender,
        "number": number,
        "part": part,
    }
    if determiner_type:
        spec["determiner_type"] = determiner_type
    lemma = str(raw.get("lemma") or raw.get("noun") or "").strip()
    if lemma:
        spec["lemma"] = lemma
    adj = str(raw.get("adjective") or raw.get("adjective_stem") or "").strip()
    if adj:
        spec["adjective_stem"] = adj
    stem = str(raw.get("determiner_stem") or raw.get("determiner_base") or "").strip()
    if stem:
        spec["determiner_stem"] = stem
    return spec


def expected_blank_answers(blanks: list[dict[str, Any]]) -> list[str]:
    """Erwartete Antworten pro Lücke (Wort, Endung oder Phrase)."""
    answers: list[str] = []
    for blank in blanks:
        case = blank["case"]
        gender = blank["gender"]
        number = blank["number"]
        part = blank.get("part") or "word"
        determiner_type = blank.get("determiner_type") or "none"
        lemma = str(blank.get("lemma") or "")
        adj_stem = blank.get("adjective_stem")
        det_stem = str(blank.get("determiner_stem") or "")

        if adj_stem and not lemma:
            adj = decline_adjective(
                stem=str(adj_stem),
                determiner_type=determiner_type if determiner_type != "none" else "mixed",
                case=case,
                gender=gender,
                number=number,
            )
            if part == "ending":
                answers.append(adj[len(str(adj_stem)) :])
            else:
                answers.append(adj)
            continue

        if blank.get("determiner_type") and not lemma and not adj_stem:
            det = _decline_determiner(
                determiner_type=determiner_type,
                determiner_stem=det_stem,
                case=case,
                gender=gender,
                number=number,
            )
            if part == "ending" and det_stem:
                answers.append(det[len(det_stem) :])
            elif part == "ending" and determiner_type == "der-word" and not det_stem:
                answers.append(det[1:] if det.startswith("d") else det)
            else:
                answers.append(det)
            continue

        if lemma and not adj_stem and not blank.get("determiner_type"):
            noun = decline_noun(lemma=lemma, gender=gender, number=number, case=case)
            if part == "ending":
                if case == "gen" and number == "pl":
                    answers.append("")
                elif case == "gen" and number == "sg" and gender != "fem":
                    suffix = noun[len(lemma) :]
                    answers.append(suffix)
                elif case == "dat" and number == "pl":
                    suffix = noun[len(lemma) :] if noun.startswith(lemma) else noun
                    answers.append(suffix or "n")
                else:
                    answers.append(noun)
            else:
                answers.append(noun)
            continue

        phrase = decline(
            lemma=lemma or "",
            gender=gender,
            number=number,
            case=case,
            determiner_type=determiner_type if blank.get("determiner_type") else "none",
            determiner_stem=det_stem,
            adjective_stem=str(adj_stem) if adj_stem else None,
        )
        if part == "phrase":
            chunk = " ".join(p for p in (phrase["determiner"], phrase["adjective"], phrase["noun"]) if p)
            answers.append(chunk.strip())
        elif part == "word":
            if blank.get("determiner_type"):
                answers.append(phrase["determiner"])
            elif adj_stem:
                answers.append(phrase["adjective"])
            else:
                answers.append(phrase["noun"])
        else:
            answers.append("")
    return answers


def _split_given_answers(given_answer: str | list[str]) -> list[str]:
    if isinstance(given_answer, list):
        return [str(p).strip() for p in given_answer]
    return [p.strip() for p in str(given_answer).split("|")]


def verify_cloze_answer(*, blanks: list[dict[str, Any]], given_answer: str | list[str]) -> bool:
    """Vergleicht Lückentext-Antworten gegen die Deklinations-Engine."""
    if not blanks:
        return False
    given_parts = _split_given_answers(given_answer)
    expected_parts = expected_blank_answers(blanks)
    if len(given_parts) != len(expected_parts):
        return False
    for expected, given in zip(expected_parts, given_parts):
        if _normalize_blank_answer(expected) != _normalize_blank_answer(given):
            return False
    return True


def parse_grammar_blanks(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    blanks: list[dict[str, Any]] = []
    for item in raw:
        spec = _parse_blank_spec(item)
        if spec:
            blanks.append(spec)
    return blanks


def infer_determiner_type_from_stem(stem: str) -> DeterminerType | None:
    key = str(stem or "").strip().lower()
    if key in _DER_WORD_BASES or key.startswith(("dies", "jen", "jed", "welch", "manch", "solch")):
        return "der-word"
    if key in _EIN_WORD_BASES or key.startswith(("mein", "dein", "sein", "unser", "euer", "kein", "ein")):
        return "ein-word"
    return None
