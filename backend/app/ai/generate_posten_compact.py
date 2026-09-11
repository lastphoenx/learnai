"""Posten kompakt: ein LLM-Call, HTML-ähnliche Struktur, optional multimodal."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.ai.errors import LlmError
from app.ai.generate import _collect_source_notes, _save_generated_modules, load_unit_source_images
from app.ai.generate_german_compact import should_use_german_compact
from app.ai.generate_interactive import _parse_questions
from app.ai.prompts.posten_compact import (
    POSTEN_COMPACT_COUNTS,
    POSTEN_COMPACT_SYSTEM,
    build_posten_compact_prompt,
)
from app.ai.providers import complete, parse_json_object
from app.ai.validators.interactive import dedupe_interactive_modules, validate_interactive_modules
from app.core.basiswissen import empty_basiswissen
from app.core.label_diagram import build_label_diagram_from_terms
from app.core.quiz_numeric import repair_quiz_block
from app.models import User
from app.services.unit_service import _dec_unit, _get_unit_or_404

_log = logging.getLogger(__name__)

_COMPACT_NUM_PREDICT = 8192
_INSTRUCTION_TERM = re.compile(
    r"^(einleitung\s+lesen|lineal|unterstreichen|form,\s*material|form\s+und\s+material|"
    r"lösungsweg|lese\s+die|markiere|kreise\s+an|trage\s+ein)",
    re.I,
)
_DATE_RANGE_TERM = re.compile(
    r"^\d{1,4}\s*(?:bis|–|-)\s*\d{1,4}\s*(?:v\.?\s*Chr|n\.?\s*Chr)?",
    re.I,
)
_SINGLE_YEAR_TERM = re.compile(
    r"^\d{1,4}\s*(?:v\.?\s*Chr|n\.?\s*Chr)\.?$",
    re.I,
)
_CIRCULAR_QUESTION = re.compile(
    r"was\s+(?:ist\s+(?:der\s+)?fachbegriff|bedeutet)\s+[«\"]?(.+?)[»\"]?[\s?]*$",
    re.I,
)


def should_use_posten_compact(
    *,
    trainer_preset: str | None,
    focus_group: str,
    math_focus: str | None,
) -> bool:
    if str(trainer_preset or "").strip() != "posten_compact":
        return False
    if should_use_german_compact(focus_group=focus_group, math_focus=math_focus):
        return False
    return True


def _is_weak_card(question: str, answer: str) -> bool:
    q = str(question or "").strip()
    a = str(answer or "").strip()
    if not q or not a:
        return True
    if _INSTRUCTION_TERM.search(q) or _INSTRUCTION_TERM.search(a):
        return True
    match = _CIRCULAR_QUESTION.search(q)
    if match:
        term = match.group(1).strip().strip("«»\"'")
        if term and term.lower() in a.lower() and len(a) < len(term) + 24:
            return True
    quoted = re.findall(r"[«\"]([^»\"]+)[»\"]", q)
    for fragment in quoted:
        frag = fragment.strip()
        if _DATE_RANGE_TERM.match(frag) or _SINGLE_YEAR_TERM.match(frag):
            return True
        if frag.lower() in a.lower() and len(a) <= len(frag) + 8:
            return True
    return False


def _parse_facts(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        text = str(item.get("text") or "").strip()
        if title and text:
            out.append({"title": title[:120], "text": text[:1200]})
    return out[: POSTEN_COMPACT_COUNTS["facts_max"]]


def _parse_cards(raw: object, *, expected: int) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    seen_q: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question") or "").strip()
        a = str(item.get("answer") or "").strip()
        if _is_weak_card(q, a):
            continue
        key = q.lower()
        if key in seen_q:
            continue
        seen_q.add(key)
        kind = str(item.get("kind") or "mental").strip().lower()
        entry: dict[str, Any] = {
            "kind": "merk" if kind == "merk" else "mental",
            "question": q[:240],
            "answer": a[:2000],
            "tip": str(item.get("tip") or "")[:240],
        }
        out.append(entry)
    return out[:expected]


def _parse_timeline(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    slots_raw = raw.get("slots")
    if not isinstance(slots_raw, list) or len(slots_raw) < 3:
        return None
    slots: list[dict[str, str]] = []
    for item in slots_raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("term") or "").strip()
        hint = str(item.get("hint") or item.get("definition") or "").strip()
        if label:
            slots.append({"label": label[:120], "hint": hint[:160]})
    if len(slots) < 3:
        return None
    return {
        "title": str(raw.get("title") or "Epochen auf dem Zeitstrahl")[:120],
        "slots": slots[:10],
    }


def _timeline_practice_item(timeline: dict[str, Any]) -> dict[str, Any] | None:
    slots = timeline.get("slots") or []
    terms = [str(s.get("label") or "").strip() for s in slots if isinstance(s, dict)]
    terms = [t for t in terms if t]
    if len(terms) < 3:
        return None
    hints = {
        str(s.get("label") or "").strip(): str(s.get("hint") or "").strip()
        for s in slots
        if isinstance(s, dict) and str(s.get("label") or "").strip()
    }
    count = len(terms)
    placements = []
    for index, term in enumerate(terms):
        x = round(0.1 + (0.8 * index / max(1, count - 1)), 3)
        y = 0.4 if index % 2 == 0 else 0.72
        placements.append({"term": term, "x": x, "y": y})
    diagram = build_label_diagram_from_terms(
        terms,
        title=str(timeline.get("title") or "Epochen auf dem Zeitstrahl")[:120],
        instruction="Ordne die Epochen chronologisch auf dem Zeitstrahl zu.",
        placements=placements,
        term_hints=hints,
        layout="timeline",
        shuffle_terms=True,
        max_terms=10,
    )
    if not diagram:
        return None
    expected = {h["id"]: h["accept"][0] for h in diagram.get("hotspots") or [] if h.get("accept")}
    return {
        "prompt": str(diagram.get("instruction") or "Ordne die Epochen auf dem Zeitstrahl zu."),
        "hint": "Ordne von früh nach spät.",
        "answer_type": "label_diagram",
        "answer": json.dumps(expected, ensure_ascii=False),
        "diagram": diagram,
        "source": "posten_compact",
    }


def _parse_posten_compact_payload(
    text: str,
    *,
    card_target: int,
    question_target: int,
) -> dict[str, Any]:
    parsed = parse_json_object(text)
    if not isinstance(parsed, dict):
        raise LlmError("Posten kompakt: kein JSON-Objekt", "bad_json")
    goal = str(parsed.get("goal") or "").strip()
    facts = _parse_facts(parsed.get("facts"))
    cards = _parse_cards(parsed.get("cards"), expected=card_target)
    quiz_raw = parsed.get("quiz")
    quiz_list = quiz_raw if isinstance(quiz_raw, list) else []
    questions = _parse_questions(
        json.dumps({"questions": quiz_list}, ensure_ascii=False),
        question_target,
    )
    for q in questions:
        q["question_type"] = "concept"
        q["source"] = "posten_compact"
    timeline = _parse_timeline(parsed.get("timeline"))

    min_facts = POSTEN_COMPACT_COUNTS["facts_min"]
    min_cards = max(6, int(card_target * 0.6))
    min_questions = max(4, int(question_target * 0.6))
    if len(facts) < min_facts:
        raise LlmError(f"Facts unvollständig ({len(facts)}/{min_facts})", "thin_content")
    if len(cards) < min_cards:
        raise LlmError(f"Lernkarten unvollständig ({len(cards)}/{card_target})", "thin_content")
    if len(questions) < min_questions:
        raise LlmError(f"Quiz unvollständig ({len(questions)}/{question_target})", "thin_content")
    return {
        "goal": goal,
        "facts": facts,
        "cards": cards,
        "quiz_questions": questions,
        "timeline": timeline,
    }


def posten_compact_payload_to_modules(payload: dict[str, Any], *, title: str, focus_group: str) -> list[dict]:
    goal = str(payload.get("goal") or "").strip()
    facts = list(payload.get("facts") or [])
    cards = list(payload.get("cards") or [])
    quiz_questions = list(payload.get("quiz_questions") or [])
    timeline = payload.get("timeline")
    practice: list[dict] = []
    if isinstance(timeline, dict):
        item = _timeline_practice_item(timeline)
        if item:
            practice.append(item)

    modules: list[dict] = [
        {
            "title": "Einstieg",
            "content": {
                "intro": goal[:600] or title[:200],
                "knowledge": facts,
                "cards": [],
                "practice": [],
                "basiswissen": empty_basiswissen(focus_group=focus_group),
            },
            "quiz": {"questions": []},
        },
        {
            "title": "Lernkarten",
            "content": {
                "intro": "Kurz abfragen — Frage zuerst, dann die Antwort.",
                "knowledge": [],
                "cards": cards,
                "practice": [],
                "basiswissen": empty_basiswissen(focus_group=focus_group),
            },
            "quiz": {"questions": []},
        },
        {
            "title": "Quiz",
            "content": {
                "intro": "Multiple Choice — eine Antwort ist richtig.",
                "knowledge": [],
                "cards": [],
                "practice": [],
                "basiswissen": empty_basiswissen(focus_group=focus_group),
            },
            "quiz": {"questions": quiz_questions},
        },
    ]
    if practice:
        modules.append(
            {
                "title": "Aufgaben",
                "content": {
                    "intro": "Ordne Begriffe am Zeitstrahl zu.",
                    "knowledge": [],
                    "cards": [],
                    "practice": practice,
                    "basiswissen": empty_basiswissen(focus_group=focus_group),
                },
                "quiz": {"questions": []},
            }
        )
    return modules


def _complete_posten_compact(
    *,
    prompt: str,
    provider: str,
    model: str | None,
    num_predict: int,
    label: str,
    images: list[tuple[bytes, str]] | None = None,
) -> dict:
    last_exc: LlmError | None = None
    for attempt in (1, 2, 3):
        try:
            result = complete(
                prompt=prompt,
                provider=provider,
                system=POSTEN_COMPACT_SYSTEM,
                model=model,
                num_predict=num_predict,
                json_mode=True,
                images=images,
            )
            parse_json_object(result["text"])
            return result
        except LlmError as exc:
            last_exc = exc
            _log.warning(
                "generate_posten_compact %s_fail attempt=%d code=%s msg=%s",
                label,
                attempt,
                exc.code,
                exc.message,
            )
    assert last_exc is not None
    raise last_exc


def generate_posten_compact(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str,
    model: str | None,
    title: str,
    brief: str,
    options: dict,
    progress: Callable[..., None] | None = None,
    provider_override: str | None = None,
    target_prefs: dict | None = None,
    fallback_prefs: dict | None = None,
) -> dict:
    from app.ai.subject_focus import detect_focus_group
    from app.services.ai_run_snapshot import build_ai_run_snapshot, persist_last_ai_run, resolve_generation_ai_tasks
    from app.services.profile_service import resolve_unit_ai_prefs

    unit = _get_unit_or_404(db, user, unit_id)
    if target_prefs is None or fallback_prefs is None:
        target_prefs, fallback_prefs = resolve_unit_ai_prefs(db, user, unit.profile_id)
    focus_group = (
        detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or "interactive"))
        or "general"
    )
    difficulty = int(unit.difficulty or 3)
    card_target = int(options.get("cards") or POSTEN_COMPACT_COUNTS["cards"])
    question_target = int(options.get("questions") or POSTEN_COMPACT_COUNTS["quiz"])
    style = str(options.get("style") or "exam")
    answer_length = str(options.get("answer_length") or "short")

    images = load_unit_source_images(unit)
    multimodal = len(images) > 0
    notes = ""
    if not multimodal:
        if progress:
            progress("extracting_sources")
        notes = _collect_source_notes(db, unit, target_prefs, fallback_prefs)
        db.commit()
        _log.info(
            "generate_posten_compact text_path unit_id=%s notes_chars=%d",
            unit_id,
            len(notes),
        )
    else:
        _log.info(
            "generate_posten_compact multimodal unit_id=%s images=%d provider=%s",
            unit_id,
            len(images),
            provider,
        )

    prompt = build_posten_compact_prompt(
        title=title,
        brief=brief,
        subject=unit.subject,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=difficulty,
        style=style,
        answer_length=answer_length,
        notes=notes,
        multimodal=multimodal,
        card_target=card_target,
        question_target=question_target,
    )

    t0 = time.monotonic()
    retry_hint = ""
    result: dict | None = None
    modules: list[dict] = []
    last_exc: LlmError | None = None
    min_modules = 3

    for attempt in (1, 2):
        if progress:
            progress("generating_posten_compact", attempt=attempt, multimodal=multimodal)
        result = _complete_posten_compact(
            prompt=prompt + retry_hint,
            provider=provider,
            model=model,
            num_predict=_COMPACT_NUM_PREDICT,
            label=f"posten_compact_{attempt}",
            images=images if multimodal else None,
        )
        try:
            payload = _parse_posten_compact_payload(
                result["text"],
                card_target=card_target,
                question_target=question_target,
            )
            modules = posten_compact_payload_to_modules(payload, title=title, focus_group=focus_group)
            min_modules = 4 if len(modules) >= 4 else 3
            modules, dedupe_warnings = dedupe_interactive_modules(modules)
            for warning in dedupe_warnings:
                _log.warning("generate_posten_compact dedupe unit_id=%s %s", unit_id, warning)
            for module in modules:
                quiz = module.get("quiz") if isinstance(module, dict) else None
                if isinstance(module, dict) and isinstance(quiz, dict):
                    module["quiz"] = repair_quiz_block(quiz)
            validate_interactive_modules(
                modules,
                min_cards=card_target,
                min_questions=question_target,
                min_modules=min_modules,
            )
            last_exc = None
            break
        except LlmError as exc:
            last_exc = exc
            _log.warning(
                "generate_posten_compact attempt=%d unit_id=%s code=%s msg=%s",
                attempt,
                unit_id,
                exc.code,
                exc.message,
            )
            if attempt == 1 and exc.code == "thin_content":
                retry_hint = (
                    "\n\nWICHTIG — vorheriger Versuch zu dünn. "
                    f"Liefere mindestens {POSTEN_COMPACT_COUNTS['facts_min']} facts, "
                    f"{card_target} cards und {question_target} quiz — keine Auslassungen.\n"
                )
                continue
            raise

    if last_exc is not None or result is None:
        assert last_exc is not None
        raise last_exc

    total_cards = sum(len(m["content"]["cards"]) for m in modules)
    total_questions = sum(len(m["quiz"]["questions"]) for m in modules)
    meta = dict(result)
    meta["generation_mode"] = "posten_compact"
    meta["multimodal"] = multimodal
    meta["pipeline"] = "multimodal" if multimodal else "text_digest"
    if progress:
        progress("saving", cards=total_cards, questions=total_questions)
    _save_generated_modules(
        db,
        unit,
        modules,
        result_meta=meta,
        task="interactive",
        final=True,
    )
    db.commit()
    persist_last_ai_run(
        db,
        unit_id,
        build_ai_run_snapshot(
            tasks=resolve_generation_ai_tasks(
                target_prefs,
                fallback_prefs,
                "interactive",
                provider_override=provider_override or provider,
                source_count=len(unit.sources or []),
                mixed_result=meta,
            ),
            stats={"modules": len(modules), "cards": total_cards, "questions": total_questions},
            triggered_by=str(user.id),
        ),
    )
    _log.info(
        "generate_posten_compact done unit_id=%s multimodal=%s cards=%d questions=%d ms=%d",
        unit_id,
        multimodal,
        total_cards,
        total_questions,
        int((time.monotonic() - t0) * 1000),
    )
    if progress:
        progress("done", cards=total_cards, questions=total_questions, modules=len(modules))
    return _dec_unit(unit)
