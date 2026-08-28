"""Strukturiertes Basiswissen: Parser, Validierung, Ableitung von Karten und Quiz."""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.core.answer_match import infer_answer_type
from app.core.basiswissen_profiles import FOCUS_GROUP_PROMPTS, ROLE_LABELS_DE

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


def _parse_cloze(raw: object, *, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    sentence = str(raw.get("sentence") or "").strip()
    if not sentence or not any(m in sentence for m in _CLOZE_MARKERS):
        return None
    answers_raw = raw.get("answers")
    answers: list[str] = []
    if isinstance(answers_raw, list):
        answers = [str(a).strip() for a in answers_raw if str(a).strip()]
    elif isinstance(answers_raw, str) and answers_raw.strip():
        answers = [a.strip() for a in answers_raw.split("|") if a.strip()]
    if not answers:
        return None
    blank_roles_raw = raw.get("blank_roles")
    blank_roles: list[str] = []
    if isinstance(blank_roles_raw, list):
        blank_roles = [str(r).strip().lower()[:40] for r in blank_roles_raw if str(r).strip()]
    template_id = str(raw.get("id") or "").strip() or _slug(f"cloze_{index}")
    concept_id = str(raw.get("concept_id") or "").strip()[:64]
    return {
        "id": template_id[:64],
        "concept_id": concept_id,
        "sentence": sentence[:400],
        "answers": answers[:8],
        "blank_roles": blank_roles[:8],
    }


def parse_basiswissen_payload(parsed: dict[str, Any], *, focus_group: str) -> dict[str, Any]:
    raw = parsed.get("basiswissen")
    if not isinstance(raw, dict):
        raw = parsed
    group = str(raw.get("focus_group") or focus_group or "general").strip().lower()[:24]
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
        blank_count = sum(template.get("sentence", "").count(m) for m in _CLOZE_MARKERS)
        answer_count = len(template.get("answers") or [])
        if blank_count > 0 and answer_count != blank_count and answer_count != 1:
            warnings.append(f"Cloze {template.get('id')}: Anzahl Lücken und Antworten weicht ab")
    return warnings


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
        answer_str = "|".join(str(a).strip() for a in answers if str(a).strip())
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


def derive_mental_term_cards(basiswissen: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for concept in basiswissen.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        label = str(concept.get("label") or "").strip()
        hint = str(concept.get("hint") or "").strip()
        example = str(concept.get("example") or "").strip()
        pattern = str(concept.get("pattern") or "").strip()
        answer_body = hint or pattern or example
        if not label or not answer_body:
            continue
        seen_terms: set[str] = set()
        for part in concept.get("parts") or []:
            if not isinstance(part, dict):
                continue
            term = str(part.get("term") or "").strip()
            role = str(part.get("role") or "").strip()
            if not term:
                continue
            term_key = term.lower()
            if term_key in seen_terms:
                continue
            seen_terms.add(term_key)
            role_label = ROLE_LABELS_DE.get(role, role)
            question = f"Was bedeutet «{term}» bei {label}?"
            if role_label and role_label.lower() != term.lower():
                answer = f"{role_label}: {answer_body}"
            else:
                answer = answer_body
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
    return cards[:24]


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
        target = parts[-1]
        correct = str(target.get("term") or "").strip()
        if not correct:
            continue
        distractors = _distractor_terms(concepts, exclude={correct}, count=3)
        while len(distractors) < 3:
            distractors.append(f"Antwort {len(distractors) + 1}")
        options = [correct] + distractors[:3]
        # shuffle deterministically by concept id hash
        order = sorted(range(4), key=lambda i: (options[i], concept.get("id"), i))
        shuffled = [options[i] for i in order]
        answer_idx = shuffled.index(correct)
        pattern = str(concept.get("pattern") or "").strip()
        q_text = (
            f"Welcher Begriff passt bei {label}? "
            f"(Muster: {pattern})" if pattern else f"Welcher Begriff gehört zu {label}?"
        )
        explanation = str(concept.get("hint") or concept.get("example") or pattern or correct)
        questions.append(
            {
                "q": q_text[:400],
                "options": [f"{chr(65 + i)}) {opt}" for i, opt in enumerate(shuffled)],
                "answer": answer_idx,
                "explanation": explanation[:1200],
                "question_type": "concept",
                "concept_id": str(concept.get("id") or "")[:64],
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
                "options": [f"{chr(65 + i)}) {opt}" for i, opt in enumerate(shuffled)],
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
    content["cards"] = cards
    content["knowledge"] = knowledge
    quiz["questions"] = questions
    return content, quiz


def enrich_module_with_basiswissen(
    *,
    content: dict[str, Any],
    quiz: dict[str, Any],
    basiswissen: dict[str, Any],
    question_count: int,
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
    derived = derive_mental_term_cards(bw) + derive_cloze_cards(bw)
    content["cards"] = prepend_unique_cards(cards, derived)
    questions = list(quiz.get("questions") or [])
    concept_max = max(2, question_count // 3)
    concept_qs = derive_concept_quiz_questions(bw, max_count=concept_max)
    quiz["questions"] = merge_concept_questions(questions, concept_qs)
    return content, quiz


def focus_group_prompt_hint(focus_group: str | None) -> str:
    if not focus_group:
        return FOCUS_GROUP_PROMPTS.get("math", "")
    return FOCUS_GROUP_PROMPTS.get(focus_group, FOCUS_GROUP_PROMPTS.get("math", ""))
