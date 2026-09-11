"""Strukturiertes Basiswissen: Parser, Validierung, Ableitung von Karten und Quiz."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from app.core.answer_match import infer_answer_type
from app.core.focus_groups import normalize_focus_group
from app.core.basiswissen_profiles import CASE_ROLE_MENTAL_HINTS, FOCUS_GROUP_PROMPTS, ROLE_LABELS_DE
from app.core.german_pedagogy_verify import repair_german_concept_genitive_preposition
from app.core.grammar_verify import repair_basiswissen_grammar, verify_basiswissen_grammar
from app.core.practice_derive import derive_practice_items

_log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_CLOZE_MARKERS = ("___", "…", "...")
_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    text = _SLUG.sub("_", str(value or "").strip().lower()).strip("_")
    return text[:48] or f"id_{uuid.uuid4().hex[:8]}"


def empty_basiswissen(*, focus_group: str = "general") -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "focus_group": focus_group,
        "concepts": [],
        "cloze_templates": [],
    }


def _parse_part(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    term = str(raw.get("term") or "").strip()
    if not term:
        return None
    role = str(raw.get("role") or "term").strip().lower()[:40]
    aliases_raw = raw.get("aliases")
    aliases: list[str] = []
    if isinstance(aliases_raw, list):
        aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]
    if term not in aliases:
        aliases.insert(0, term)
    return {"role": role, "term": term[:80], "aliases": aliases[:6]}


def _parse_concept(raw: object, *, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    label = str(raw.get("label") or "").strip()
    if not label:
        return None
    parts_raw = raw.get("parts")
    parts: list[dict[str, Any]] = []
    if isinstance(parts_raw, list):
        for item in parts_raw:
            parsed = _parse_part(item)
            if parsed:
                parts.append(parsed)
    concept_id = str(raw.get("id") or "").strip() or _slug(f"{label}_{index}")
    kind = str(raw.get("kind") or "relation").strip().lower()[:24]
    if kind not in {"relation", "definition", "rule", "vocabulary"}:
        kind = "relation"
    return {
        "id": concept_id[:64],
        "kind": kind,
        "label": label[:120],
        "parts": parts[:12],
        "pattern": str(raw.get("pattern") or "")[:240],
        "example": str(raw.get("example") or "")[:300],
        "hint": str(raw.get("hint") or "")[:400],
    }


def cloze_blank_count(template: dict[str, Any]) -> int:
    """Anzahl Lücken — grammar.blanks hat Vorrang vor ___-Zählung im Satz."""
    from app.core.german_declension import parse_grammar_blanks

    grammar = template.get("grammar")
    if isinstance(grammar, dict):
        blanks = parse_grammar_blanks(grammar.get("blanks"))
        if blanks:
            return len(blanks)
    sentence = str(template.get("sentence") or "")
    return sum(sentence.count(marker) for marker in _CLOZE_MARKERS)


def repair_cloze_answer_count(template: dict[str, Any]) -> dict[str, Any]:
    """Gleicht answers-Länge an Lücken an (eine Antwort für alle gleichen Lücken)."""
    fixed = dict(template)
    blank_count = cloze_blank_count(fixed)
    if blank_count <= 0:
        return fixed
    answers = list(fixed.get("answers") or [])
    if len(answers) == blank_count:
        return fixed
    if len(answers) == 1 and blank_count > 1:
        fixed["answers"] = answers * blank_count
    return fixed


def sanitize_basiswissen_cloze_templates(basiswissen: dict[str, Any]) -> dict[str, Any]:
    """Verwirft Cloze-Templates mit nicht reparierbarem Lücken/Antworten-Mismatch."""
    repaired = dict(basiswissen)
    kept: list[dict[str, Any]] = []
    for raw in basiswissen.get("cloze_templates") or []:
        if not isinstance(raw, dict):
            continue
        template = repair_cloze_answer_count(raw)
        blank_count = cloze_blank_count(template)
        answer_count = len(template.get("answers") or [])
        if blank_count <= 0:
            _log.warning(
                "sanitize_basiswissen drop cloze id=%s reason=no_blanks",
                template.get("id") or "?",
            )
            continue
        if answer_count != blank_count:
            _log.warning(
                "sanitize_basiswissen drop cloze id=%s reason=count_mismatch blanks=%d answers=%d",
                template.get("id") or "?",
                blank_count,
                answer_count,
            )
            continue
        kept.append(template)
    repaired["cloze_templates"] = kept
    return repaired


def _parse_cloze(raw: object, *, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    sentence = str(raw.get("sentence") or "").strip()
    if not sentence or not any(m in sentence for m in _CLOZE_MARKERS):
        return None
    answers_raw = raw.get("answers")
    answers: list[str] = []
    if isinstance(answers_raw, list):
        answers = [str(a).strip() for a in answers_raw]
    elif isinstance(answers_raw, str):
        answers = [part.strip() for part in answers_raw.split("|")]
    grammar_raw = raw.get("grammar")
    grammar = grammar_raw if isinstance(grammar_raw, dict) else None
    from app.core.german_declension import parse_grammar_blanks

    has_grammar_blanks = bool(
        isinstance(grammar, dict) and parse_grammar_blanks(grammar.get("blanks"))
    )
    if not answers and not has_grammar_blanks:
        return None
    blank_roles_raw = raw.get("blank_roles")
    blank_roles: list[str] = []
    if isinstance(blank_roles_raw, list):
        blank_roles = [str(r).strip().lower()[:40] for r in blank_roles_raw if str(r).strip()]
    template_id = str(raw.get("id") or "").strip() or _slug(f"cloze_{index}")
    concept_id = str(raw.get("concept_id") or "").strip()[:64]
    out: dict[str, Any] = {
        "id": template_id[:64],
        "concept_id": concept_id,
        "sentence": sentence[:400],
        "answers": answers[:8],
        "blank_roles": blank_roles[:8],
    }
    if grammar:
        out["grammar"] = grammar
    return out


def parse_basiswissen_payload(parsed: dict[str, Any], *, focus_group: str) -> dict[str, Any]:
    raw = parsed.get("basiswissen")
    if not isinstance(raw, dict):
        raw = parsed
    group = str(raw.get("focus_group") or focus_group or "general").strip().lower()[:24]
    group = normalize_focus_group(group)
    concepts: list[dict[str, Any]] = []
    for index, item in enumerate(raw.get("concepts") or []):
        concept = _parse_concept(item, index=index)
        if concept and (concept.get("parts") or concept.get("hint")):
            concepts.append(concept)
    cloze_templates: list[dict[str, Any]] = []
    for index, item in enumerate(raw.get("cloze_templates") or []):
        template = _parse_cloze(item, index=index)
        if template:
            cloze_templates.append(template)
    return {
        "schema_version": SCHEMA_VERSION,
        "focus_group": group,
        "concepts": concepts[:12],
        "cloze_templates": cloze_templates[:16],
    }


def validate_basiswissen(basiswissen: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    concepts = basiswissen.get("concepts") or []
    templates = basiswissen.get("cloze_templates") or []
    concept_ids = {str(c.get("id")) for c in concepts if isinstance(c, dict)}
    if not concepts:
        warnings.append("Keine concepts im Basiswissen")
    for template in templates:
        if not isinstance(template, dict):
            continue
        cid = str(template.get("concept_id") or "")
        if cid and cid not in concept_ids:
            warnings.append(f"Cloze {template.get('id')} verweist auf unbekanntes concept {cid}")
        blank_count = cloze_blank_count(template)
        answer_count = len(template.get("answers") or [])
        if blank_count > 0 and answer_count != blank_count and answer_count != 1:
            warnings.append(f"Cloze {template.get('id')}: Anzahl Lücken und Antworten weicht ab")
    warnings.extend(verify_basiswissen_grammar(basiswissen))
    return warnings


def repair_basiswissen_concepts(basiswissen: dict[str, Any]) -> dict[str, Any]:
    """Deutsch: Genitiv-Präpositions-Fehler in Concepts wie im Pedagogy-Digest korrigieren."""
    group = normalize_focus_group(str(basiswissen.get("focus_group") or ""))
    if group != "german":
        return basiswissen
    repaired = dict(basiswissen)
    concepts: list[dict[str, Any]] = []
    for raw in basiswissen.get("concepts") or []:
        if not isinstance(raw, dict):
            continue
        concepts.append(repair_german_concept_genitive_preposition(raw))
    repaired["concepts"] = concepts
    return repaired


def finalize_basiswissen(basiswissen: dict[str, Any]) -> dict[str, Any]:
    """Fachspezifische Reparatur vor dem Speichern (Deutsch: Deklination + Concept-QA)."""
    return sanitize_basiswissen_cloze_templates(
        repair_basiswissen_concepts(repair_basiswissen_grammar(basiswissen))
    )


def knowledge_overview_from_basiswissen(basiswissen: dict[str, Any]) -> dict[str, str] | None:
    concepts = basiswissen.get("concepts") or []
    if not concepts:
        return None
    lines: list[str] = []
    for concept in concepts[:8]:
        if not isinstance(concept, dict):
            continue
        label = str(concept.get("label") or "").strip()
        pattern = str(concept.get("pattern") or "").strip()
        example = str(concept.get("example") or "").strip()
        hint = str(concept.get("hint") or "").strip()
        chunk = label
        if pattern:
            chunk += f": {pattern}"
        if example:
            chunk += f" (z. B. {example})"
        elif hint:
            chunk += f" — {hint}"
        lines.append(chunk)
    if not lines:
        return None
    return {
        "title": "Fachbegriffe im Überblick",
        "text": " ".join(lines)[:900],
    }


def _concept_terms(concept: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for part in concept.get("parts") or []:
        if not isinstance(part, dict):
            continue
        term = str(part.get("term") or "").strip()
        if term and term not in terms:
            terms.append(term)
    return terms


def _distractor_terms(concepts: list[dict[str, Any]], *, exclude: set[str], count: int = 3) -> list[str]:
    pool: list[str] = []
    for concept in concepts:
        for term in _concept_terms(concept):
            if term in exclude or term in pool:
                continue
            pool.append(term)
    return pool[:count]


def derive_cloze_cards(basiswissen: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    concepts_by_id = {
        str(c.get("id")): c for c in (basiswissen.get("concepts") or []) if isinstance(c, dict)
    }
    for template in basiswissen.get("cloze_templates") or []:
        if not isinstance(template, dict):
            continue
        sentence = str(template.get("sentence") or "").strip()
        answers = template.get("answers") or []
        if not sentence or not answers:
            continue
        answer_str = "|".join(str(a).strip() for a in answers)
        concept = concepts_by_id.get(str(template.get("concept_id") or ""), {})
        label = str(concept.get("label") or "Fachbegriffe")
        cards.append(
            {
                "kind": "input",
                "question": sentence[:240],
                "answer": answer_str[:200],
                "tip": str(concept.get("hint") or "")[:240],
                "answer_type": "cloze",
                "card_role": "cloze",
                "source": "basiswissen",
                "basiswissen_id": str(template.get("id") or "")[:64],
                "concept_id": str(template.get("concept_id") or "")[:64],
                "method_label": label[:120],
            }
        )
    return cards


def _pattern_lists_multiple_parts(pattern: str, parts: list[dict[str, Any]]) -> bool:
    if not pattern:
        return False
    terms = [str(p.get("term") or "").strip() for p in parts if str(p.get("term") or "").strip()]
    if len(terms) < 2:
        return False
    pl = pattern.lower()
    hits = sum(1 for term in terms if term.lower() in pl)
    return hits >= 2


_PATTERN_CHUNK_SPLIT = re.compile(
    r"[;\n|]"
    r"|(?:\s*[–—→>]\s*)"
    r"|(?:,\s+(?=[A-ZÄÖÜ\"«(]|der |die |das |des |dem |den ))"
)
_TERM_STOPWORDS = frozenset(
    {
        "der",
        "die",
        "das",
        "des",
        "dem",
        "den",
        "ein",
        "eine",
        "eines",
        "einem",
        "einen",
        "und",
        "oder",
        "bei",
        "mit",
        "zum",
        "zur",
        "vom",
        "aus",
        "als",
        "nach",
        "the",
    }
)
_ARTICLE_CASE_HINTS: tuple[tuple[str, str], ...] = (
    ("des ", "Genitiv — Wessen?"),
    ("dem ", "Dativ — Wem?"),
    ("den ", "Akkusativ — Wen oder was?"),
)
_CASE_ROLE_FORM_HINTS: dict[str, str] = {
    "nominativ": "Nominativ — Wer oder was?",
    "genitiv": "Genitiv — Wessen?",
    "dativ": "Dativ — Wem?",
    "akkusativ": "Akkusativ — Wen oder was?",
}
_PROCEDURE_MATCH_STOPWORDS = frozenset(
    {"markieren", "stellen", "bestimmen", "bilden", "fragen", "erkennen", "passende", "passenden"}
)
_PROCEDURE_ORDINALS = ("Zuerst", "Dann", "Danach", "Zum Schluss")


def _is_procedural_role(role: str) -> bool:
    if not role:
        return False
    if role in {"step", "result", "method", "strategy", "procedure", "question", "function", "ending"}:
        return True
    return role.startswith("step_")


def _term_content_tokens(term: str, *, for_pattern: bool = False) -> set[str]:
    stop = _TERM_STOPWORDS if not for_pattern else (_TERM_STOPWORDS | _PROCEDURE_MATCH_STOPWORDS)
    return {
        token
        for token in re.findall(r"[a-zäöüß]{3,}", term.lower())
        if token not in stop
    }


def _split_pattern_chunks(pattern: str) -> list[str]:
    if not pattern:
        return []
    chunks: list[str] = []
    for chunk in re.split(_PATTERN_CHUNK_SPLIT, pattern):
        piece = chunk.strip().strip(".")
        if not piece:
            continue
        for step in re.split(
            r"\s+(?=(?:zuerst|dann|danach|als nächstes|zuletzt)\b)|(?:\s+und\s+zuletzt\s+)",
            piece,
            flags=re.I,
        ):
            step_piece = step.strip().strip(",")
            if step_piece:
                chunks.append(step_piece)
    return chunks


def _segment_lists_multiple_forms(segment: str) -> bool:
    return len(_split_pattern_chunks(segment)) >= 2


def _declension_form_hint(
    term: str,
    *,
    concept: dict[str, Any] | None = None,
    part: dict[str, Any] | None = None,
) -> str:
    role = str((part or {}).get("role") or "").strip().lower()
    if role in _CASE_ROLE_FORM_HINTS:
        return _CASE_ROLE_FORM_HINTS[role]
    lower = term.lower().lstrip()
    label = str((concept or {}).get("label") or "").lower()
    for prefix, hint in _ARTICLE_CASE_HINTS:
        if lower.startswith(prefix):
            return hint
    if lower.startswith("der "):
        if any(token in label for token in ("genitiv", "wessen", "besitz", "plural")):
            return "Genitiv — Wessen?"
        if any(token in label for token in ("dativ", "wem")):
            return "Dativ — Wem?"
        if any(token in label for token in ("nominativ", "wer-fall", "subjekt")):
            return "Nominativ — Wer oder was?"
    return ""


def _best_pattern_segment(pattern: str, term: str) -> str | None:
    """Extrahiert den passenden Muster-Abschnitt (Fallzeile, Verfahrensschritt, Tabellenform)."""
    needle = term.strip().lower()
    if not needle or not pattern:
        return None
    chunks = _split_pattern_chunks(pattern)
    if not chunks:
        return None
    exact = [chunk for chunk in chunks if chunk.lower() == needle]
    if exact:
        return exact[0]
    substring = [chunk for chunk in chunks if needle in chunk.lower()]
    if len(substring) == 1:
        return substring[0]
    if len(substring) > 1:
        return min(substring, key=len)
    tokens = _term_content_tokens(term, for_pattern=True)
    if tokens:
        best: str | None = None
        best_score = 0
        for chunk in chunks:
            score = len(tokens & _term_content_tokens(chunk, for_pattern=True))
            if score > best_score:
                best_score = score
                best = chunk
        if best_score >= 1 and best:
            return best
    for chunk in chunks:
        if needle in chunk.lower():
            return chunk
    return None


def _pattern_segment_for_term(pattern: str, term: str) -> str | None:
    return _best_pattern_segment(pattern, term)


def _mental_term_answer(
    part: dict[str, Any],
    concept: dict[str, Any],
    *,
    step_index: int | None = None,
) -> str:
    term = str(part.get("term") or "").strip()
    role = str(part.get("role") or "").strip().lower()
    label = str(concept.get("label") or "").strip()
    role_label = ROLE_LABELS_DE.get(role, role)
    example = str(concept.get("example") or "").strip()
    pattern = str(concept.get("pattern") or "").strip()
    hint = str(concept.get("hint") or "").strip()
    role_hint = CASE_ROLE_MENTAL_HINTS.get(role, "")
    multi_part = _pattern_lists_multiple_parts(pattern, concept.get("parts") or [])
    shared_hint = multi_part and hint
    form_hint = _declension_form_hint(term, concept=concept, part=part)
    is_table_form = bool(form_hint and re.match(r"^(der|die|das|des|dem|den)\s+", term, re.I))

    if example and term.lower() in example.lower() and not is_table_form:
        return f"{term}: {example}"[:2000]

    segment = _best_pattern_segment(pattern, term)
    if segment and _segment_lists_multiple_forms(segment) and segment.lower() != term.lower():
        narrowed = _best_pattern_segment(segment, term)
        if narrowed and not _segment_lists_multiple_forms(narrowed):
            segment = narrowed
    if segment and segment.strip().lower() == pattern.strip().lower() and term.lower() not in segment.lower():
        segment = None
    if segment and not _is_degenerate_segment_answer(term, segment):
        if segment.lower() == term.lower() and form_hint:
            return f"{term}: {form_hint}"[:2000]
        bits = [f"{term}: {segment}"]
        if role_hint and role_hint.lower() not in segment.lower():
            bits.append(role_hint)
        answer_text = ". ".join(bits)[:2000]
        if not _is_degenerate_mental_answer(term, answer_text):
            return answer_text

    if is_table_form:
        return f"{term}: {form_hint}"[:2000]

    if _is_procedural_role(role):
        if step_index:
            ordinal = (
                _PROCEDURE_ORDINALS[step_index - 1]
                if 1 <= step_index <= len(_PROCEDURE_ORDINALS)
                else f"Schritt {step_index}"
            )
            return f"{term}: {ordinal} bei «{label}» — {term}."[:2000]
        return f"{term}: Schritt bei «{label}» — {term}."[:2000]

    if role_label and role_label.lower() not in {term.lower(), ""}:
        line = f"{term} ({role_label})"
        if role_hint:
            line = f"{line}: {role_hint}"
        elif hint and not shared_hint:
            line = f"{line}: {hint}"
        return line[:2000]
    if role_hint:
        return f"{term}: {role_hint}"[:2000]
    if hint and not shared_hint:
        return f"{term}: {hint}"[:2000]
    return pattern or example or term


def _concept_quiz_explanation(concept: dict[str, Any], part: dict[str, Any], correct: str) -> str:
    example = str(concept.get("example") or "").strip()
    pattern = str(concept.get("pattern") or "").strip()
    role = str(part.get("role") or "").strip()
    role_label = ROLE_LABELS_DE.get(role, role)
    bits = [f"Richtig: {correct}."]
    if role_label and role_label.lower() not in {correct.lower(), ""}:
        bits.append(f"Rolle: {role_label}.")
    if example and correct.lower() in example.lower():
        bits.append(example)
    elif pattern and correct.lower() in pattern.lower():
        bits.append(f"Muster: {pattern}")
    return " ".join(bits)[:1200]


def _scrub_term_clue(text: str, term: str) -> str | None:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if len(raw) < 12:
        return None
    if term.lower() not in raw.lower():
        return raw[:220]
    if re.match(rf"^{re.escape(term)}\b", raw, flags=re.I):
        return None
    clue = re.sub(re.escape(term), "…", raw, count=1, flags=re.I)
    clue = re.sub(r"\s+", " ", clue).strip(" .—–-")
    if len(clue) < 14 or clue in {"…", "….", "… …"}:
        return None
    if re.match(r"^…(\s|$)", clue):
        return None
    return clue[:220]


def _mental_term_question(term: str, part: dict[str, Any], concept: dict[str, Any]) -> str:
    label = str(concept.get("label") or "").strip()
    role = str(part.get("role") or "").strip().lower()
    role_label = ROLE_LABELS_DE.get(role, "")
    for raw in (str(part.get("hint") or "").strip(), str(concept.get("hint") or "").strip()):
        clue = _scrub_term_clue(raw, term)
        if clue:
            topic = (
                label[:48]
                if label and label.lower() not in {term.lower(), "thema", "topic", "begriff"}
                else "diesem Abschnitt"
            )
            return f"Was ist «{term}»? (Hinweis: {clue}; Thema: {topic})"
    if role_label and role_label.lower() not in {term.lower(), "", "begriff", "term", "part", "whole"}:
        return f"Welche Rolle hat «{term}» — {role_label}?"
    if label and term.lower() != label.lower() and len(label.split()) <= 6:
        return f"Was bezeichnet «{term}» im Zusammenhang «{label}»?"
    return f"Was ist der Fachbegriff «{term}»?"


def mental_term_from_question(question: str) -> str:
    match = re.search(r"«([^»]+)»", str(question or ""))
    return match.group(1).strip() if match else ""


def _answer_body_after_term_prefix(term: str, answer: str) -> str:
    text = str(answer or "").strip()
    prefix = str(term or "").strip()
    if not prefix:
        return text.lower()
    if text.lower().startswith(prefix.lower()):
        rest = text[len(prefix) :].lstrip()
        if rest[:1] in {":", "—", "-"}:
            rest = rest[1:].lstrip()
        return rest.lower()
    return text.lower()


def _is_degenerate_segment_answer(term: str, segment: str) -> bool:
    t = term.strip().lower()
    s = segment.strip().lower()
    if not s or s == t:
        return True
    words = t.split()
    if len(words) > 1 and s == words[0]:
        return True
    if s in t and len(s) < max(8, len(t) * 0.45):
        return True
    return False


def _is_degenerate_mental_answer(term: str, answer: str) -> bool:
    t = term.strip().lower()
    body = _answer_body_after_term_prefix(term, answer)
    if not body or body == t:
        return True
    if len(body.split()) <= 1 and body in t:
        return True
    if t in body and len(body) < len(t) + 12:
        return True
    return False


def is_weak_mental_card_entry(*, question: str, answer: str, term: str | None = None) -> bool:
    """Schwache/tautologische Mental-Karte (LLM oder abgeleitet)."""
    resolved = (term or mental_term_from_question(question)).strip()
    if not resolved:
        return False
    return _is_weak_mental_card(question, resolved, answer)


def _is_weak_mental_card(question: str, term: str, answer: str) -> bool:
    q = question.strip().lower()
    t = term.strip().lower()
    a = answer.strip().lower()
    if not t or not a:
        return True
    if "was bedeutet" in q and f"«{term}»".lower() in q and " bei " in q:
        tail = q.split(" bei ", 1)[-1].strip(" ?.")
        if t in tail or tail == t:
            return True
    if _is_degenerate_mental_answer(term, answer):
        return True
    if a.startswith(f"{t}:") and t in a and len(a.split()) <= 8:
        return True
    if a == t or a.startswith(f"{t} ") and len(a) < len(t) + 16:
        return True
    return False


def _mental_question_key(question: str) -> str:
    return re.sub(r"\s+", " ", str(question or "").strip().lower())[:240]


def _mental_term_key(term: str) -> str:
    return str(term or "").strip().lower()


def derive_mental_term_cards(
    basiswissen: dict[str, Any],
    *,
    card_state: dict[str, Any] | None = None,
    max_count: int = 16,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen_answers: set[str] = set()
    global_terms: set[str] | None = None
    global_questions: set[str] | None = None
    if card_state is not None:
        global_terms = card_state.setdefault("mental_terms", set())
        global_questions = card_state.setdefault("mental_questions", set())
    for concept in basiswissen.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        if len(cards) >= max_count:
            break
        label = str(concept.get("label") or "").strip()
        example = str(concept.get("example") or "").strip()
        pattern = str(concept.get("pattern") or "").strip()
        hint = str(concept.get("hint") or "").strip()
        if not label or not (hint or pattern or example):
            continue
        seen_terms: set[str] = set()
        procedural_parts = [
            p
            for p in (concept.get("parts") or [])
            if isinstance(p, dict) and _is_procedural_role(str(p.get("role") or "").strip().lower())
        ]
        step_index_by_term = {
            str(p.get("term") or "").strip(): idx + 1 for idx, p in enumerate(procedural_parts)
        }
        for part in concept.get("parts") or []:
            if len(cards) >= max_count:
                break
            if not isinstance(part, dict):
                continue
            term = str(part.get("term") or "").strip()
            if not term:
                continue
            term_key = _mental_term_key(term)
            if term_key in seen_terms:
                continue
            if global_terms is not None and term_key in global_terms:
                continue
            seen_terms.add(term_key)
            question = _mental_term_question(term, part, concept)
            answer = _mental_term_answer(
                part,
                concept,
                step_index=step_index_by_term.get(term),
            )
            if _is_weak_mental_card(question, term, answer):
                continue
            q_key = _mental_question_key(question)
            if global_questions is not None and q_key in global_questions:
                continue
            answer_key = answer[:80].strip().lower()
            if answer_key in seen_answers:
                continue
            seen_answers.add(answer_key)
            if global_terms is not None:
                global_terms.add(term_key)
            if global_questions is not None:
                global_questions.add(q_key)
            cards.append(
                {
                    "kind": "mental",
                    "question": question[:240],
                    "answer": answer[:2000],
                    "tip": example[:240] if example else pattern[:240],
                    "card_role": "term",
                    "source": "basiswissen",
                    "concept_id": str(concept.get("id") or "")[:64],
                    "method_label": label[:120],
                }
            )
    return cards[:max_count]


def _concept_quiz_question_text(
    *,
    correct: str,
    label: str,
    multi_part: bool,
    role_label: str,
    has_pattern: bool,
) -> str:
    correct_l = correct.lower()
    label_l = label.lower()
    label_is_sentence = len(label) > 64 or label.count(" ") >= 7
    if correct_l == label_l:
        return f"Was bedeutet der Fachbegriff «{correct}»?"
    if not multi_part and label_l.startswith(correct_l) and len(label) <= len(correct) + 4:
        return f"Was bedeutet der Fachbegriff «{correct}»?"
    if label_is_sentence:
        if multi_part and role_label and role_label.lower() not in {correct_l, ""}:
            return f"Welche Rolle hat «{correct}» in diesem Abschnitt?"
        return f"Was bedeutet «{correct}» in diesem Zusammenhang?"
    if multi_part:
        if role_label and role_label.lower() not in {correct_l, ""}:
            return f"Welche Rolle hat «{correct}» bei {label}?"
        return f"Was bezeichnet «{correct}» bei {label}?"
    if has_pattern:
        return f"Was bezeichnet «{correct}» bei {label}?"
    return f"Welcher Begriff gehört zu {label}?"


def derive_concept_quiz_questions(
    basiswissen: dict[str, Any],
    *,
    max_count: int = 4,
) -> list[dict[str, Any]]:
    concepts = [c for c in (basiswissen.get("concepts") or []) if isinstance(c, dict)]
    if not concepts:
        return []
    questions: list[dict[str, Any]] = []
    for concept in concepts:
        if len(questions) >= max_count:
            break
        label = str(concept.get("label") or "").strip()
        parts = [p for p in (concept.get("parts") or []) if isinstance(p, dict)]
        if not parts:
            continue
        pattern = str(concept.get("pattern") or "").strip()
        multi_part = len(parts) > 1 or _pattern_lists_multiple_parts(pattern, parts)
        targets = parts if multi_part else [parts[-1]]
        for part in targets:
            if len(questions) >= max_count:
                break
            correct = str(part.get("term") or "").strip()
            if not correct:
                continue
            distractors = _distractor_terms(concepts, exclude={correct}, count=3)
            while len(distractors) < 3:
                distractors.append(f"Antwort {len(distractors) + 1}")
            options = [correct] + distractors[:3]
            order = sorted(range(4), key=lambda i: (options[i], concept.get("id"), part.get("role"), i))
            shuffled = [options[i] for i in order]
            answer_idx = shuffled.index(correct)
            role_label = ROLE_LABELS_DE.get(str(part.get("role") or "").strip(), "")
            q_text = _concept_quiz_question_text(
                correct=correct,
                label=label,
                multi_part=multi_part,
                role_label=role_label,
                has_pattern=bool(pattern),
            )
            explanation = _concept_quiz_explanation(concept, part, correct)
            questions.append(
                {
                    "q": q_text[:400],
                    "options": [str(opt).strip() for opt in shuffled],
                    "answer": answer_idx,
                    "explanation": explanation[:1200],
                    "question_type": "concept",
                    "concept_id": str(concept.get("id") or "")[:64],
                    "target_term": correct[:80],
                }
            )
    for template in basiswissen.get("cloze_templates") or []:
        if len(questions) >= max_count:
            break
        if not isinstance(template, dict):
            continue
        answers = template.get("answers") or []
        if not answers:
            continue
        correct = str(answers[0]).strip()
        sentence = str(template.get("sentence") or "").replace("___", "___").strip()
        distractors = _distractor_terms(concepts, exclude={correct}, count=3)
        while len(distractors) < 3:
            distractors.append("—")
        options = [correct] + distractors[:3]
        order = sorted(range(4), key=lambda i: (options[i], template.get("id"), i))
        shuffled = [options[i] for i in order]
        answer_idx = shuffled.index(correct)
        questions.append(
            {
                "q": f"Welcher Begriff fehlt? {sentence}"[:400],
                "options": [str(opt).strip() for opt in shuffled],
                "answer": answer_idx,
                "explanation": f"Richtig: {correct}."[:1200],
                "question_type": "concept",
                "concept_id": str(template.get("concept_id") or "")[:64],
            }
        )
    return questions[:max_count]


def merge_concept_questions(
    questions: list[dict[str, Any]],
    concept_questions: list[dict[str, Any]],
    *,
    max_ratio: float = 0.4,
) -> list[dict[str, Any]]:
    if not concept_questions or not questions:
        return questions
    max_concept = max(1, min(len(concept_questions), int(len(questions) * max_ratio)))
    selected = concept_questions[:max_concept]
    out = list(questions)
    replaceable = [
        i
        for i, q in enumerate(out)
        if str(q.get("question_type") or "calculation") not in {"method", "concept"}
    ]
    for idx, concept_q in zip(replaceable[-len(selected) :], selected):
        out[idx] = concept_q
    return out


def prepend_unique_cards(existing: list[dict], derived: list[dict]) -> list[dict]:
    seen = {str(c.get("question") or "").strip().lower() for c in existing}
    out = []
    for card in derived:
        key = str(card.get("question") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(card)
    return out + existing


_OVERVIEW_TITLE = "fachbegriffe im überblick"


def strip_basiswissen_derivatives(
    content: dict[str, Any],
    quiz: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Entfernt abgeleitete Karten/Quiz-Einträge vor einer erneuten Anreicherung."""
    content = dict(content)
    quiz = dict(quiz) if isinstance(quiz, dict) else {"questions": []}
    cards = [
        card
        for card in (content.get("cards") or [])
        if isinstance(card, dict) and str(card.get("source") or "").strip().lower() != "basiswissen"
    ]
    knowledge = [
        item
        for item in (content.get("knowledge") or [])
        if isinstance(item, dict)
        and str(item.get("title") or "").strip().lower() != _OVERVIEW_TITLE
    ]
    questions = [
        question
        for question in (quiz.get("questions") or [])
        if isinstance(question, dict) and str(question.get("question_type") or "") != "concept"
    ]
    practice = [
        item
        for item in (content.get("practice") or [])
        if isinstance(item, dict)
        and str(item.get("source") or "").strip().lower() not in {"basiswissen", "pedagogy"}
    ]
    content["cards"] = cards
    content["knowledge"] = knowledge
    content["practice"] = practice
    quiz["questions"] = questions
    return content, quiz


_MAX_DERIVED_MENTAL_CARDS = 8
_MAX_DERIVED_CLOZE_CARDS = 3
_MAX_DERIVED_MENTAL_PER_MODULE_COMPACT = 2


def enrich_module_with_basiswissen(
    *,
    content: dict[str, Any],
    quiz: dict[str, Any],
    basiswissen: dict[str, Any],
    question_count: int,
    category_label: str = "",
    pedagogy: dict[str, Any] | None = None,
    practice_state: dict[str, Any] | None = None,
    card_state: dict[str, Any] | None = None,
    compact: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bw = basiswissen if isinstance(basiswissen, dict) else empty_basiswissen()
    content = dict(content)
    quiz = dict(quiz) if isinstance(quiz, dict) else {"questions": []}
    content["basiswissen"] = bw
    knowledge = list(content.get("knowledge") or [])
    overview = knowledge_overview_from_basiswissen(bw)
    if overview and not any(
        str(k.get("title") or "").strip().lower() == overview["title"].lower()
        for k in knowledge
        if isinstance(k, dict)
    ):
        knowledge.insert(0, overview)
    content["knowledge"] = knowledge
    cards = list(content.get("cards") or [])
    mental_cap = _MAX_DERIVED_MENTAL_PER_MODULE_COMPACT if compact else _MAX_DERIVED_MENTAL_CARDS
    derived = derive_mental_term_cards(bw, card_state=card_state, max_count=mental_cap)
    derived += derive_cloze_cards(bw)[: (_MAX_DERIVED_CLOZE_CARDS if not compact else 1)]
    content["cards"] = prepend_unique_cards(cards, derived)
    questions = list(quiz.get("questions") or [])
    concept_max = max(2, question_count // 4)
    concept_qs = derive_concept_quiz_questions(bw, max_count=concept_max)
    quiz["questions"] = merge_concept_questions(questions, concept_qs)
    practice = list(content.get("practice") or [])
    derived_practice: list[dict[str, Any]] = []
    if not (compact and practice_state is not None and practice_state.get("unit_practice_done")):
        derived_practice = derive_practice_items(
            pedagogy=pedagogy if isinstance(pedagogy, dict) else {},
            basiswissen=bw,
            category_label=category_label,
            focus_group=bw.get("focus_group"),
            practice_state=practice_state,
        )
        if derived_practice and compact and practice_state is not None:
            practice_state["unit_practice_done"] = True
    if derived_practice:
        seen_prompts = {str(p.get("prompt") or "").strip().lower() for p in practice if isinstance(p, dict)}
        for item in derived_practice:
            key = str(item.get("prompt") or "").strip().lower()
            if key and key not in seen_prompts:
                seen_prompts.add(key)
                practice.append(item)
        content["practice"] = practice
    return content, quiz


def focus_group_prompt_hint(focus_group: str | None) -> str:
    if not focus_group:
        return FOCUS_GROUP_PROMPTS.get("math", "")
    return FOCUS_GROUP_PROMPTS.get(focus_group, FOCUS_GROUP_PROMPTS.get("math", ""))
