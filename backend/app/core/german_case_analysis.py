"""Fallbestimmung im deutschen Fliesstext — spaCy als Zusatzsignal (Ticket B).

Kein 100%-Gate: confidence=high + Abweichung → Warnung/Verwerfen bei Generierung.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.core.german_declension import normalize_case

_log = logging.getLogger(__name__)

_CASE_LABELS: dict[str, tuple[str, ...]] = {
    "nom": ("nominativ", "nom", "n"),
    "gen": ("genitiv", "gen", "g"),
    "dat": ("dativ", "dat", "d"),
    "acc": ("akkusativ", "akkus", "akk", "a"),
}

_QUOTED_SPAN = re.compile(r"[«\"']([^»\"']{2,120})[»\"']")
_SENTENCE_PREFIX = re.compile(
    r"(?:Im Satz|Satz|Im Text|Text)\s*[:\-]?\s*[«\"']([^»\"']+[.!?])[»\"']",
    re.I,
)
_WORD_IN_SENTENCE = re.compile(
    r"(?:Wort|Satzglied|Ausdruck)\s+[«\"']([^»\"']{1,80})[»\"'].{0,40}?"
    r"(?:im\s+Satz|Satz)\s*[:\-]?\s*[«\"']([^»\"']+)[»\"']",
    re.I,
)
_BLANK_AFTER = re.compile(r"___\s+([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß\-]*)")
_BLANK_BEFORE = re.compile(r"([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß\-]*)\s+___")
_BLANK_AT_END = re.compile(r"___\s*[.!?]?\s*$")
_CASE_QUESTION = re.compile(r"\b(welchen|welcher|welches|welchem)\s+fall\b|\bkasus\b|\bfall\b.*[«\"']", re.I)

_FUNCTION_WORDS = frozenset(
    {
        "der",
        "die",
        "das",
        "ein",
        "eine",
        "einem",
        "einen",
        "einer",
        "eines",
        "dem",
        "den",
        "des",
        "ich",
        "du",
        "er",
        "sie",
        "es",
        "wir",
        "ihr",
        "mein",
        "dein",
        "sein",
        "unser",
        "euer",
    }
)

_nlp: Any | None = None
_nlp_unavailable: bool = False


@dataclass(frozen=True)
class CaseAnalysisResult:
    case: str | None
    confidence: str  # high | low | unavailable
    span: str
    sentence: str
    detail: str = ""


def _normalize_label(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    raw = re.sub(r"[^\w\s]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def case_from_label(text: str) -> str | None:
    """Mappt «Akkusativ|Akk.» o. ä. auf nom|gen|dat|acc."""
    parts = [p.strip() for p in str(text or "").split("|") if p.strip()]
    if not parts:
        return None
    for part in parts:
        norm = _normalize_label(part)
        if not norm:
            continue
        direct = normalize_case(norm)
        if direct:
            return direct
        for case, labels in _CASE_LABELS.items():
            for label in labels:
                if norm == label or norm.startswith(label + " ") or norm.endswith(" " + label):
                    return case
    return None


def case_label_de(case: str | None) -> str:
    return {
        "nom": "Nominativ",
        "gen": "Genitiv",
        "dat": "Dativ",
        "acc": "Akkusativ",
    }.get(str(case or ""), "?")


def spacy_available() -> bool:
    _load_nlp()
    return _nlp is not None and not _nlp_unavailable


def _load_nlp() -> Any | None:
    global _nlp, _nlp_unavailable
    if _nlp_unavailable:
        return None
    if _nlp is not None:
        return _nlp
    try:
        import spacy
    except ImportError:
        _log.info("german_case_analysis: spacy nicht installiert")
        _nlp_unavailable = True
        return None
    for model in ("de_core_news_sm", "de_core_news_md"):
        try:
            _nlp = spacy.load(model)
            return _nlp
        except OSError:
            continue
    _log.warning("german_case_analysis: kein deutsches spaCy-Modell gefunden")
    _nlp_unavailable = True
    return None


def _morph_case(token: Any) -> str | None:
    cases = token.morph.get("Case") if hasattr(token, "morph") else []
    if not cases:
        return None
    mapped = normalize_case(str(cases[0]))
    return mapped


def _case_from_span(doc: Any, span_text: str) -> tuple[str | None, str]:
    needle = str(span_text or "").strip()
    if not needle:
        return None, "leerer Span"
    hay = doc.text
    idx = hay.lower().find(needle.lower())
    if idx < 0:
        return None, "Span im Satz nicht gefunden"
    char_span = doc.char_span(idx, idx + len(needle), alignment_mode="expand")
    if char_span is None:
        return None, "char_span fehlgeschlagen"
    for token in char_span:
        case = _morph_case(token)
        if case:
            return case, f"Token «{token.text}»"
    root_case = _morph_case(char_span.root)
    if root_case:
        return root_case, f"Kopf «{char_span.root.text}»"
    return None, "kein Case-Morph Merkmal"


def _span_covers_whole_sentence(sentence: str, span: str) -> bool:
    """True wenn Span praktisch der ganze Satz ist — dann ist Fallprüfung sinnlos."""
    sent_tokens = [t for t in re.findall(r"\w+", sentence, flags=re.UNICODE) if t]
    span_tokens = [t for t in re.findall(r"\w+", span, flags=re.UNICODE) if t]
    if not span_tokens:
        return True
    if len(span_tokens) >= max(3, int(len(sent_tokens) * 0.6 + 0.5)):
        return True
    sent_norm = _normalize_label(sentence)
    span_norm = _normalize_label(span)
    return bool(sent_norm and span_norm and span_norm == sent_norm)


def _span_from_blank_sentence(sentence: str) -> str | None:
    """Bei Lückensatz: angrenzendes Inhaltswort als Zielspan, sonst None."""
    if _BLANK_AT_END.search(sentence.strip()):
        return None
    after = _BLANK_AFTER.search(sentence)
    if after:
        word = after.group(1)
        if word.lower() not in _FUNCTION_WORDS:
            return word
    before = _BLANK_BEFORE.search(sentence)
    if before:
        word = before.group(1)
        if word.lower() not in _FUNCTION_WORDS:
            return word
    return None


def analyze_span_case(*, sentence: str, span: str) -> CaseAnalysisResult:
    """Erkennt den Kasus eines markierten Satzglieds via spaCy."""
    sent = str(sentence or "").strip()
    span_text = str(span or "").strip()
    if not sent or not span_text:
        return CaseAnalysisResult(
            case=None,
            confidence="unavailable",
            span=span_text,
            sentence=sent,
            detail="Satz oder Span fehlt",
        )
    if _span_covers_whole_sentence(sent, span_text):
        return CaseAnalysisResult(
            case=None,
            confidence="unavailable",
            span=span_text,
            sentence=sent,
            detail="Span entspricht dem ganzen Satz — nicht prüfbar",
        )
    nlp = _load_nlp()
    if nlp is None:
        return CaseAnalysisResult(
            case=None,
            confidence="unavailable",
            span=span_text,
            sentence=sent,
            detail="spaCy/Modell nicht verfügbar",
        )
    doc = nlp(sent)
    case, detail = _case_from_span(doc, span_text)
    if case:
        return CaseAnalysisResult(
            case=case,
            confidence="high",
            span=span_text,
            sentence=sent,
            detail=detail,
        )
    return CaseAnalysisResult(
        case=None,
        confidence="low",
        span=span_text,
        sentence=sent,
        detail=detail,
    )


def parse_case_check(raw: object) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    sentence = str(raw.get("sentence") or raw.get("context") or "").strip()
    span = str(raw.get("span") or raw.get("phrase") or "").strip()
    if sentence and span:
        if _span_covers_whole_sentence(sentence, span):
            return None
        out: dict[str, str] = {"sentence": sentence[:500], "span": span[:120]}
        expected = normalize_case(str(raw.get("expected_case") or raw.get("case") or ""))
        if expected:
            out["expected_case"] = expected
        return out
    return None


def infer_case_check_from_question(question: str) -> dict[str, str] | None:
    """Heuristik für Fall-Fragen — nur wenn ein kurzer Zielspan erkennbar ist."""
    q = str(question or "").strip()
    if not q or not _CASE_QUESTION.search(q):
        return None

    word_in_sent = _WORD_IN_SENTENCE.search(q)
    if word_in_sent:
        span = word_in_sent.group(1).strip()
        sentence = word_in_sent.group(2).strip()
        if span and sentence and not _span_covers_whole_sentence(sentence, span):
            return {"sentence": sentence[:500], "span": span[:120]}

    sentence_match = _SENTENCE_PREFIX.search(q)
    quotes = _QUOTED_SPAN.findall(q)
    if not quotes:
        return None
    if sentence_match:
        sentence = sentence_match.group(1).strip()
        span = quotes[-1].strip()
        if span and span != sentence and not _span_covers_whole_sentence(sentence, span):
            return {"sentence": sentence[:500], "span": span[:120]}
    if len(quotes) >= 2:
        first, second = quotes[0].strip(), quotes[1].strip()
        # Zielwort vor dem Satz: «Buch» … «Das ist mein Buch.»
        if (
            len(first.split()) <= 3
            and not first.endswith((".", "!", "?"))
            and (second.endswith((".", "!", "?")) or len(second.split()) >= 3)
            and not _span_covers_whole_sentence(second, first)
        ):
            return {"sentence": second[:500], "span": first[:120]}
        if first.endswith((".", "!", "?")) and second in first:
            return {"sentence": first[:500], "span": second[:120]}
        if first.endswith((".", "!", "?")) and not _span_covers_whole_sentence(first, second):
            return {"sentence": first[:500], "span": second[:120]}

    span = quotes[-1].strip()
    # Einzelnes Satz-Zitat mit Lücke → angrenzendes Wort, sonst nicht prüfbar
    if "___" in span:
        target = _span_from_blank_sentence(span)
        if target:
            return {"sentence": span[:500], "span": target[:120]}
        return None
    # Kein Fallback mehr: ganzen Satz als Span zurückgeben (führte zu False-Positives)
    if _span_covers_whole_sentence(q, span) or len(span.split()) >= 4:
        return None
    return {"sentence": q[:500], "span": span[:120]}


def get_case_check_spec(card: dict[str, Any]) -> dict[str, str] | None:
    grammar = card.get("grammar")
    if isinstance(grammar, dict):
        case_check = parse_case_check(grammar.get("case_check"))
        if case_check:
            return case_check
    inferred = infer_case_check_from_question(str(card.get("question") or ""))
    return inferred


def verify_case_label(
    *,
    expected_answer: str,
    sentence: str,
    span: str,
) -> tuple[bool | None, CaseAnalysisResult]:
    """Vergleicht gespeicherte Fall-Antwort mit spaCy.

    Returns:
        True = übereinstimmend, False = Abweichung (nur bei confidence=high),
        None = nicht beurteilbar (spaCy fehlt / kein Case).
    """
    expected_case = case_from_label(expected_answer)
    result = analyze_span_case(sentence=sentence, span=span)
    if result.confidence == "unavailable" or not result.case or not expected_case:
        return None, result
    if result.confidence != "high":
        return None, result
    return result.case == expected_case, result
