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
_CASE_QUESTION = re.compile(
    r"\b(welchen|welcher|welches|welchem)\s+fall\b|\bkasus\b|\bfall\b.*[«\"']|"
    r"^fall\s+(?:von|in)\s*:",
    re.I,
)
_FALL_DRILL_PREFIX = re.compile(
    r"^(?:Bestimme\s+den\s+Fall(?:\s+der\s+markierten\s+Wortgruppe)?|Fall)"
    r"(?:\s+(?:von|in|des\s+(?:markierten\s+)?(?:Satzglieds|Wortgruppe)))?\s*:\s*(.+)$",
    re.I,
)

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


_ATTR_DEPS = frozenset({"nk", "ag", "og", "mnr", "bv", "nmod", "amod"})


def _char_span_from_text(doc: Any, span_text: str) -> Any | None:
    needle = str(span_text or "").strip()
    if not needle:
        return None
    hay = doc.text
    idx = hay.lower().find(needle.lower())
    if idx < 0:
        return None
    return doc.char_span(idx, idx + len(needle), alignment_mode="expand")


def _token_in_char_span(token: Any, char_span: Any) -> bool:
    return char_span.start <= token.i < char_span.end


def _descends_from(token: Any, ancestor: Any) -> bool:
    if token.i == ancestor.i:
        return True
    current = token
    for _ in range(24):
        head = current.head
        if head.i == current.i:
            break
        if head.i == ancestor.i:
            return True
        current = head
    return False


def _phrase_head_in_span(char_span: Any) -> Any:
    """Syntaktischer Kopf der Spanne — bevorzugt Nomen mit Head ausserhalb der Spanne."""
    external = [
        t
        for t in char_span
        if t.head.i < char_span.start or t.head.i >= char_span.end
    ]
    if not external:
        return char_span.root
    content = [t for t in external if t.pos_ in ("NOUN", "PROPN", "PRON")]
    if content:
        return max(content, key=lambda t: t.i)
    for anchor in sorted(external, key=lambda t: t.i):
        for child in anchor.children:
            if not _token_in_char_span(child, char_span):
                continue
            if child.pos_ in ("NOUN", "PROPN", "PRON"):
                return child
    return max(external, key=lambda t: t.i)


def _case_of_subtree(token: Any) -> str | None:
    case = _morph_case(token)
    if case:
        return case
    for child in token.subtree:
        if child is token:
            continue
        case = _morph_case(child)
        if case:
            return case
    return None


def _subtree_text_in_span(doc: Any, token: Any, char_span: Any) -> str:
    tokens = [t for t in token.subtree if _token_in_char_span(t, char_span)]
    if not tokens:
        return str(token.text or "").strip()
    tokens.sort(key=lambda t: t.i)
    start = tokens[0].i
    end = tokens[-1].i + 1
    return doc[start:end].text.strip()


def _nested_cases_in_span(doc: Any, char_span: Any, head: Any, outer_case: str) -> list[tuple[str, str]]:
    nested: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(token: Any) -> None:
        inner_case = _case_of_subtree(token)
        if not inner_case or inner_case == outer_case:
            return
        phrase = _subtree_text_in_span(doc, token, char_span)
        if not phrase:
            return
        key = (phrase.lower(), inner_case)
        if key in seen:
            return
        seen.add(key)
        nested.append((phrase, inner_case))

    for child in head.children:
        if _token_in_char_span(child, char_span):
            _add(child)

    for token in char_span:
        if token.i == head.i:
            continue
        if token.dep_ == "det" and token.head.i == head.i:
            continue
        inner_case = _case_of_subtree(token)
        if not inner_case or inner_case == outer_case:
            continue
        if token.dep_.lower() in _ATTR_DEPS or _descends_from(token, head):
            _add(token)

    nested.sort(key=lambda item: (-len(item[0]), item[0].lower()))
    deduped: list[tuple[str, str]] = []
    seen_cases: set[str] = set()
    for phrase, case in nested:
        if case in seen_cases:
            continue
        seen_cases.add(case)
        deduped.append((phrase, case))
    return deduped


def case_with_nested_attributes(doc: Any, span_text: str) -> dict[str, Any]:
    """Liefert äusseren Fall der Spanne plus eingebettete abweichende Fälle."""
    char_span = _char_span_from_text(doc, span_text)
    if char_span is None:
        return {"case": None, "nested": [], "detail": "char_span fehlgeschlagen"}

    head = _phrase_head_in_span(char_span)
    outer_case = _case_of_subtree(head)
    detail = f"Kopf «{head.text}»" if outer_case else "kein Case-Morph Merkmal"
    if not outer_case:
        for token in char_span:
            outer_case = _morph_case(token)
            if outer_case:
                detail = f"Token «{token.text}»"
                break

    nested = _nested_cases_in_span(doc, char_span, head, outer_case) if outer_case else []

    return {"case": outer_case, "nested": nested, "detail": detail}


def _case_from_span(doc: Any, span_text: str) -> tuple[str | None, str]:
    needle = str(span_text or "").strip()
    if not needle:
        return None, "leerer Span"
    char_span = _char_span_from_text(doc, span_text)
    if char_span is None:
        idx = doc.text.lower().find(needle.lower())
        if idx < 0:
            return None, "Span im Satz nicht gefunden"
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
    sent_norm = _normalize_label(sentence)
    span_norm = _normalize_label(span)
    if sent_norm and span_norm and span_norm == sent_norm:
        return True
    # Lange Spans (>85 % der Satz-Tokens) nur blockieren, wenn kein klares Teilsatzglied bleibt
    if len(span_tokens) >= max(4, int(len(sent_tokens) * 0.85 + 0.5)):
        return True
    return False


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


def extract_case_drill_sentence(question: str) -> str | None:
    """Satz aus «Fall von: …» / Doppelpunkt-Fragen — ohne markiertes Satzglied."""
    q = str(question or "").strip()
    if not q:
        return None
    match = _FALL_DRILL_PREFIX.match(q)
    if match:
        return match.group(1).strip().strip("«»\"'")[:500]
    for marker in (
        "markierten Wortgruppe:",
        "markierten Wortgruppe",
        "markierten Satzglieds:",
        "markierten Satzglieds",
    ):
        if marker in q:
            tail = q.split(marker, 1)[1].strip().strip("«»\"'")
            if len(tail) > 8:
                return tail[:500]
    if ":" in q:
        tail = q.rsplit(":", 1)[1].strip().strip("«»\"'")
        if len(tail) > 8 and (tail.endswith((".", "!", "?")) or len(tail.split()) >= 4):
            return tail[:500]
    return None


def build_case_check_spec(
    *,
    sentence: str,
    span: str = "",
    expected_answer: str = "",
) -> dict[str, str] | None:
    """Baut case_check aus Satz + optional Span oder erwartetem Fall-Label."""
    sent = str(sentence or "").strip()
    if not sent:
        return None
    sp = str(span or "").strip()
    if not sp and expected_answer:
        sp = find_span_for_expected_case(sentence=sent, expected_answer=expected_answer) or ""
    if not sp or sp not in sent or _span_covers_whole_sentence(sent, sp):
        return None
    return {"sentence": sent[:500], "span": sp[:120]}


def expected_case_answer_from_item(item: dict[str, Any]) -> str:
    """Fall-Label aus Karte oder Quiz (options[answer])."""
    raw = item.get("answer")
    if isinstance(raw, bool):
        return ""
    if isinstance(raw, int) or (isinstance(raw, str) and str(raw).strip().isdigit()):
        options = item.get("options") if isinstance(item.get("options"), list) else []
        idx = int(raw)
        if 0 <= idx < len(options):
            return str(options[idx]).strip()
    return str(raw or "").strip()


def sentence_has_finite_verb(sentence: str) -> bool | None:
    """None wenn spaCy fehlt. de_core_news_sm liefert oft kein VerbForm — POS reicht."""
    nlp = _load_nlp()
    sent = str(sentence or "").strip()
    if nlp is None or not sent:
        return None
    doc = nlp(sent)
    for token in doc:
        if token.pos_ == "VERB":
            return True
        if token.pos_ == "AUX" and token.dep_ in ("ROOT", "cop", "aux", "oc"):
            return True
    return False


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
    for key in ("question", "q"):
        inferred = infer_case_check_from_question(str(card.get(key) or ""))
        if inferred:
            return inferred
    answer = expected_case_answer_from_item(card)
    primary = answer.split("|")[0].strip()
    if case_from_label(primary):
        for key in ("question", "q"):
            sentence = extract_case_drill_sentence(str(card.get(key) or ""))
            if sentence:
                built = build_case_check_spec(sentence=sentence, expected_answer=primary)
                if built:
                    return built
    return None


def find_span_for_expected_case(*, sentence: str, expected_answer: str) -> str | None:
    """Findet ein Satzglied mit dem erwarteten Fall (spaCy, confidence=high)."""
    expected_case = case_from_label(expected_answer)
    sent = str(sentence or "").strip()
    if not expected_case or not sent:
        return None
    nlp = _load_nlp()
    if nlp is None:
        return None
    doc = nlp(sent)
    best: tuple[int, str] | None = None
    for chunk in doc.noun_chunks:
        span = chunk.text.strip()
        if len(span) < 2:
            continue
        result = analyze_span_case(sentence=sent, span=span)
        if result.case != expected_case or result.confidence != "high":
            continue
        score = len(span)
        if best is None or score > best[0]:
            best = (score, span)
    return best[1] if best else None


def repair_case_check(item: dict[str, Any], *, answer: str | None = None) -> dict[str, Any]:
    """Span reparieren wenn LLM ganzen Satz oder ungültiges Satzglied liefert (K05-Fall)."""
    grammar = item.get("grammar")
    if not isinstance(grammar, dict):
        return item
    raw = grammar.get("case_check")
    if not isinstance(raw, dict):
        return item
    sentence = str(raw.get("sentence") or "").strip()
    span = str(raw.get("span") or "").strip()
    expected = str(answer or item.get("answer") or "").strip()
    if not sentence:
        return item
    invalid = not span or span not in sentence or _span_covers_whole_sentence(sentence, span)
    if invalid and expected:
        fixed = find_span_for_expected_case(sentence=sentence, expected_answer=expected)
        if fixed:
            span = fixed
    if not span or span not in sentence or _span_covers_whole_sentence(sentence, span):
        return item
    out = dict(item)
    g = dict(grammar)
    cc: dict[str, Any] = {"sentence": sentence[:500], "span": span[:120]}
    nested = raw.get("nested")
    if isinstance(nested, (dict, list)):
        cc["nested"] = nested
    g["case_check"] = cc
    out["grammar"] = g
    return out


def _replace_sentence_variant(question: str, sentence: str, marked_sentence: str) -> str | None:
    if sentence in question:
        return question.replace(sentence, marked_sentence, 1)
    stripped = sentence.strip().strip("«»\"'")
    for variant in (sentence, stripped, f"«{stripped}»", f"«{stripped.rstrip('.')}»"):
        if variant and variant in question:
            return question.replace(variant, marked_sentence, 1)
    return None


def _format_case_highlight_text(
    item: dict[str, Any],
    *,
    text_key: str,
    max_len: int,
) -> dict[str, Any]:
    item = repair_case_check(item, answer=str(item.get("answer") or ""))
    spec = get_case_check_spec(item)
    if not spec:
        return item
    question = str(item.get(text_key) or "")
    if re.search(r"<mark>|\[[^\]]+\]", question, re.I):
        return item
    sentence = spec["sentence"].strip()
    span = spec["span"].strip()
    if not sentence or not span or span not in sentence:
        return item
    marked_sentence = sentence.replace(span, f"<mark>{span}</mark>", 1)
    new_question = _replace_sentence_variant(question, sentence, marked_sentence)
    if not new_question:
        colon_idx = question.rfind(":")
        if colon_idx < 0:
            return item
        tail = question[colon_idx + 1 :].strip().strip("«»\"'")
        if tail not in {sentence, sentence.rstrip("."), sentence.strip("«»\"'")}:
            return item
        new_question = f"{question[: colon_idx + 1]} {marked_sentence}"
    out = dict(item)
    out[text_key] = new_question.strip()[:max_len]
    return out


def format_case_card_question(card: dict[str, Any]) -> dict[str, Any]:
    """Markiert span in Fall-Fragen mit <mark>, wenn noch keine Hervorhebung vorhanden ist."""
    return _format_case_highlight_text(card, text_key="question", max_len=500)


def format_case_quiz_question(question: dict[str, Any]) -> dict[str, Any]:
    """Wie format_case_card_question, für Quiz-Einträge mit Feld «q»."""
    return _format_case_highlight_text(question, text_key="q", max_len=400)


def analyze_span_case_nested(*, sentence: str, span: str) -> dict[str, Any]:
    """Wie analyze_span_case, inkl. eingebetteter abweichender Fälle in der Spanne."""
    sent = str(sentence or "").strip()
    span_text = str(span or "").strip()
    if not sent or not span_text:
        return {"case": None, "nested": [], "detail": "Satz oder Span fehlt", "confidence": "unavailable"}
    if _span_covers_whole_sentence(sent, span_text):
        return {
            "case": None,
            "nested": [],
            "detail": "Span entspricht dem ganzen Satz — nicht prüfbar",
            "confidence": "unavailable",
        }
    nlp = _load_nlp()
    if nlp is None:
        return {"case": None, "nested": [], "detail": "spaCy/Modell nicht verfügbar", "confidence": "unavailable"}
    doc = nlp(sent)
    result = case_with_nested_attributes(doc, span_text)
    confidence = "high" if result.get("case") else "low"
    result["confidence"] = confidence
    return result


def verify_case_answer_with_nesting(
    *,
    expected_answer: str,
    given_answer: str,
    sentence: str,
    span: str,
) -> str:
    """Ergebnis: correct | wrong | teilrichtig_falsche_ebene | unavailable."""
    expected_case = case_from_label(expected_answer)
    given_case = case_from_label(given_answer)
    if not expected_case or not given_case:
        return "unavailable"
    if expected_case == given_case:
        return "correct"
    analysis = analyze_span_case_nested(sentence=sentence, span=span)
    if analysis.get("confidence") != "high":
        return "wrong"
    nested = analysis.get("nested") or []
    for _text, nested_case in nested:
        if nested_case == given_case:
            return "teilrichtig_falsche_ebene"
    return "wrong"


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
