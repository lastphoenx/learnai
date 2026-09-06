"""Deutsche Präpositionen und Fallzuordnung — Referenzdaten (nicht KI-Text)."""

from __future__ import annotations

from app.core.pedagogy_labels import normalize_label

GENITIVE_PREPOSITIONS: frozenset[str] = frozenset(
    {
        "infolge",
        "waehrend",
        "wahrend",
        "wegen",
        "trotz",
        "aufgrund",
        "anlaesslich",
        "anlasslich",
        "angesichts",
        "innerhalb",
        "ausserhalb",
        "aussserhalb",
        "oberhalb",
        "unterhalb",
        "beiderseits",
        "diesseits",
        "jenseits",
        "mittels",
        "zwecks",
        "seitlich",
        "abseits",
        "oestlich",
        "ostlich",
        "westlich",
        "noerdlich",
        "nordlich",
    }
)

DATIVE_PREPOSITIONS: frozenset[str] = frozenset(
    {
        "aus",
        "bei",
        "mit",
        "nach",
        "seit",
        "von",
        "vom",
        "zu",
        "zum",
        "zur",
        "gegenueber",
        "gegenüber",
        "ausser",
        "außer",
        "entgegen",
    }
)

ACCUSATIVE_PREPOSITIONS: frozenset[str] = frozenset(
    {
        "durch",
        "fuer",
        "fur",
        "für",
        "gegen",
        "ohne",
        "um",
        "bis",
        "entlang",
    }
)

TWO_WAY_PREPOSITIONS: frozenset[str] = frozenset(
    {
        "an",
        "auf",
        "hinter",
        "in",
        "neben",
        "ueber",
        "uber",
        "über",
        "unter",
        "vor",
        "zwischen",
    }
)

_GENITIVE_PREPOSITION_HINT = (
    "Genitiv nach Präpositionen wie infolge, während, wegen, oberhalb, unterhalb, …"
)


def normalize_preposition(word: str | None) -> str:
    key = normalize_label(word or "")
    if key.startswith("zum "):
        return "zu"
    if key.startswith("zur "):
        return "zu"
    if key in {"vom", "von dem"}:
        return "von"
    return key.split()[0] if key else ""


def preposition_case_is_plausible(preposition: str, claimed_case: str) -> bool:
    """False, wenn die KI eine Präposition dem falschen Fall zuordnet."""
    prep = normalize_preposition(preposition)
    case = str(claimed_case or "").strip().lower()
    if not prep or not case:
        return True
    if case == "gen":
        return prep in GENITIVE_PREPOSITIONS
    if case == "dat":
        return prep in DATIVE_PREPOSITIONS or prep in TWO_WAY_PREPOSITIONS
    if case in {"acc", "akk"}:
        return prep in ACCUSATIVE_PREPOSITIONS or prep in TWO_WAY_PREPOSITIONS
    return True


def sentence_has_genitive_preposition(text: str) -> bool:
    """True, wenn im Satz eine bekannte Genitiv-Präposition vorkommt."""
    norm = normalize_label(text)
    if not norm:
        return False
    tokens = set(norm.split())
    return any(prep in tokens for prep in GENITIVE_PREPOSITIONS)


def text_lists_wrong_genitive_prepositions(text: str) -> list[str]:
    """Präpositionen, die im Text als Genitiv-Kontext genannt werden, aber keinen Genitiv verlangen."""
    norm = normalize_label(text)
    if not norm:
        return []
    if "genitiv" not in norm and "praeposition" not in norm:
        return []
    wrong: list[str] = []
    for token in norm.replace(",", " ").split():
        prep = normalize_preposition(token)
        if not prep:
            continue
        if prep in DATIVE_PREPOSITIONS | ACCUSATIVE_PREPOSITIONS:
            wrong.append(prep)
    return wrong


def genitive_preposition_reference_text() -> str:
    return _GENITIVE_PREPOSITION_HINT
