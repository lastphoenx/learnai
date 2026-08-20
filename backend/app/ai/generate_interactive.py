"""Interaktiven Lerntrainer erzeugen: Plan → Karten → Quiz pro Kategorie."""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.ai.catalog import resolve_task_ai
from app.ai.errors import LlmError
from app.ai.generate import _collect_source_notes, _save_generated_modules
from app.ai.prompts.interactive import (
    CARDS_SYSTEM,
    PLAN_SYSTEM,
    QUIZ_SYSTEM,
    build_interactive_card_prompt,
    build_interactive_plan_prompt,
    build_interactive_quiz_prompt,
    truncate_context,
)
from app.ai.providers import complete, parse_json_object, resolve_provider
from app.ai.task_types import AI_TASK_FOR_UNIT
from app.ai.validators.interactive import validate_interactive_modules
from app.core.crypto import decrypt_text_master
from app.models import LearningRecord, User
from app.services.crypto_json import decrypt_json
from app.services.profile_service import resolve_prefs_for_profile
from app.services.unit_service import _dec_unit, _get_unit_or_404, get_trainer_options
from app.services.user_service import get_user_settings

_log = logging.getLogger(__name__)

_PLAN_NUM_PREDICT = 4096
_BATCH_NUM_PREDICT = 8192
_MIN_CARDS = 30
_MIN_QUESTIONS = 30


def _distribute(total: int, buckets: int) -> list[int]:
    base = total // buckets
    rest = total % buckets
    return [base + (1 if i < rest else 0) for i in range(buckets)]


def _parse_plan(text: str) -> list[dict]:
    parsed = parse_json_object(text)
    categories = parsed.get("categories")
    if not isinstance(categories, list) or len(categories) < 4:
        raise LlmError("Gliederung unvollständig", "thin_content")
    out: list[dict] = []
    for raw in categories[:6]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or raw.get("title") or "").strip()
        if not name:
            continue
        out.append(
            {
                "name": name[:120],
                "focus": str(raw.get("focus") or "")[:300],
            }
        )
    if len(out) < 4:
        raise LlmError("Zu wenige Kategorien in der Gliederung", "thin_content")
    return out


def _normalize_plan_counts(categories: list[dict], *, card_target: int, question_target: int) -> list[dict]:
    card_parts = _distribute(card_target, len(categories))
    question_parts = _distribute(question_target, len(categories))
    normalized: list[dict] = []
    for index, cat in enumerate(categories):
        normalized.append(
            {
                "name": cat["name"],
                "focus": cat.get("focus") or "",
                "cards": card_parts[index],
                "questions": question_parts[index],
            }
        )
    return normalized


def _parse_cards(text: str, expected: int) -> list[dict]:
    parsed = parse_json_object(text)
    cards = parsed.get("cards")
    if not isinstance(cards, list):
        raise LlmError("Keine Lernkarten in der Antwort", "bad_json")
    out: list[dict] = []
    for raw in cards:
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("question") or "").strip()
        a = str(raw.get("answer") or "").strip()
        if not q or not a:
            continue
        out.append(
            {
                "question": q[:240],
                "answer": a[:800],
                "tip": str(raw.get("tip") or "")[:240],
            }
        )
    min_accept = max(2, int(expected * 0.6))
    if len(out) < min_accept:
        raise LlmError(f"Lernkarten unvollständig ({len(out)}/{expected})", "thin_content")
    if len(out) < expected:
        _log.warning("generate_interactive cards_short got=%d expected=%d", len(out), expected)
    return out[:expected] if len(out) >= expected else out


def _parse_questions(text: str, expected: int) -> list[dict]:
    parsed = parse_json_object(text)
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        raise LlmError("Keine Quizfragen in der Antwort", "bad_json")
    out: list[dict] = []
    for raw in questions:
        if not isinstance(raw, dict):
            continue
        options = raw.get("options") if isinstance(raw.get("options"), list) else []
        if len(options) != 4:
            continue
        out.append(
            {
                "q": str(raw.get("q") or "")[:400],
                "options": [str(o)[:200] for o in options[:4]],
                "answer": int(raw.get("answer", 0)),
                "explanation": str(raw.get("explanation") or "")[:400],
            }
        )
    min_accept = max(2, int(expected * 0.6))
    if len(out) < min_accept:
        raise LlmError(f"Quizfragen unvollständig ({len(out)}/{expected})", "thin_content")
    if len(out) < expected:
        _log.warning("generate_interactive questions_short got=%d expected=%d", len(out), expected)
    return out[:expected] if len(out) >= expected else out


def _complete_with_retry(
    *,
    prompt: str,
    provider: str,
    system: str,
    model: str | None,
    num_predict: int,
    label: str,
) -> dict:
    last_exc: LlmError | None = None
    for attempt in (1, 2):
        try:
            return complete(
                prompt=prompt,
                provider=provider,
                system=system,
                model=model,
                num_predict=num_predict,
            )
        except LlmError as exc:
            last_exc = exc
            _log.warning(
                "generate_interactive %s_fail attempt=%d code=%s msg=%s",
                label,
                attempt,
                exc.code,
                exc.message,
            )
    assert last_exc is not None
    raise last_exc


def generate_interactive_modules(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)
    ai_task = AI_TASK_FOR_UNIT.get("interactive", "mixed")
    name, model = resolve_task_ai(prefs, ai_task, override=provider)
    name = resolve_provider(name)

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}
    options = get_trainer_options(recon)

    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""

    card_target = max(_MIN_CARDS, int(options.get("cards") or 50))
    question_target = max(_MIN_QUESTIONS, int(options.get("questions") or 50))
    style = str(options.get("style") or "playful")
    answer_length = str(options.get("answer_length") or "short")

    _log.info(
        "generate_interactive start unit_id=%s cards=%d questions=%d style=%s sources=%d",
        unit_id,
        card_target,
        question_target,
        style,
        len(unit.sources or []),
    )
    t0 = time.monotonic()
    notes = _collect_source_notes(db, unit, prefs)
    db.commit()
    _log.info(
        "generate_interactive sources_persisted unit_id=%s notes_chars=%d duration_ms=%d",
        unit_id,
        len(notes),
        int((time.monotonic() - t0) * 1000),
    )

    math_focus = (recon or {}).get("math_focus") if isinstance(recon, dict) else None
    math_focus_label: str | None = None
    if math_focus:
        from app.ai.task_types import MATH_FOCUS_OPTIONS

        math_focus_label = next(
            (o["label"] for o in MATH_FOCUS_OPTIONS if o["key"] == math_focus),
            str(math_focus),
        )

    context_prompt = build_interactive_plan_prompt(
        title=title,
        brief=brief,
        subject=unit.subject,
        math_focus=math_focus_label,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=unit.difficulty,
        style=style,
        answer_length=answer_length,
        notes=notes,
        card_target=card_target,
        question_target=question_target,
    )
    batch_context = truncate_context(context_prompt)

    plan_result = _complete_with_retry(
        prompt=context_prompt,
        provider=name,
        system=PLAN_SYSTEM,
        model=model,
        num_predict=_PLAN_NUM_PREDICT,
        label="plan",
    )
    categories = _normalize_plan_counts(
        _parse_plan(plan_result["text"]),
        card_target=card_target,
        question_target=question_target,
    )
    _log.info(
        "generate_interactive plan_done unit_id=%s categories=%d duration_ms=%d",
        unit_id,
        len(categories),
        int((time.monotonic() - t0) * 1000),
    )

    modules: list[dict] = []
    all_card_questions: list[str] = []

    for index, cat in enumerate(categories):
        _log.info(
            "generate_interactive category_start unit_id=%s index=%d name=%s cards=%d questions=%d",
            unit_id,
            index + 1,
            cat["name"],
            cat["cards"],
            cat["questions"],
        )
        cards_prompt = build_interactive_card_prompt(
            context=batch_context,
            category_name=cat["name"],
            category_focus=cat["focus"],
            count=cat["cards"],
            existing_questions=all_card_questions,
        )
        cards_result = _complete_with_retry(
            prompt=cards_prompt,
            provider=name,
            system=CARDS_SYSTEM,
            model=model,
            num_predict=_BATCH_NUM_PREDICT,
            label=f"cards_{index + 1}",
        )
        cards = _parse_cards(cards_result["text"], cat["cards"])
        all_card_questions.extend(c["question"] for c in cards)

        quiz_prompt = build_interactive_quiz_prompt(
            context=batch_context,
            category_name=cat["name"],
            category_focus=cat["focus"],
            count=cat["questions"],
            card_summaries=[f"{c['question']} → {c['answer'][:80]}" for c in cards[:6]],
        )
        quiz_result = _complete_with_retry(
            prompt=quiz_prompt,
            provider=name,
            system=QUIZ_SYSTEM,
            model=model,
            num_predict=_BATCH_NUM_PREDICT,
            label=f"quiz_{index + 1}",
        )
        questions = _parse_questions(quiz_result["text"], cat["questions"])

        modules.append(
            {
                "title": cat["name"],
                "content": {
                    "intro": cat["focus"] or "",
                    "knowledge": [
                        {
                            "title": cat["name"],
                            "text": cat["focus"] or f"Kernwissen zu {cat['name']}.",
                        }
                    ],
                    "cards": cards,
                },
                "quiz": {"questions": questions},
            }
        )
        _log.info(
            "generate_interactive category_done unit_id=%s index=%d cards=%d questions=%d",
            unit_id,
            index + 1,
            len(cards),
            len(questions),
        )

    validate_interactive_modules(
        modules,
        min_cards=_MIN_CARDS,
        min_questions=_MIN_QUESTIONS,
    )

    total_cards = sum(len(m["content"]["cards"]) for m in modules)
    total_questions = sum(len(m["quiz"]["questions"]) for m in modules)

    _save_generated_modules(
        db,
        unit,
        modules,
        result_meta=plan_result,
        task="interactive",
    )
    _log.info(
        "generate_interactive done unit_id=%s modules=%d cards=%d questions=%d total_ms=%d",
        unit_id,
        len(modules),
        total_cards,
        total_questions,
        int((time.monotonic() - t0) * 1000),
    )
    return _dec_unit(unit)
