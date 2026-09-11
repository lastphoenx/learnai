"""Gezielte Reparatur fehlgeschlagener Batch-Einheiten (ohne Vision/Plan neu)."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.ai.catalog import resolve_task_ai_for_unit
from app.ai.errors import LlmError
from app.ai.generate import _collect_source_notes, _save_generated_modules
from app.ai.generate_interactive import _complete_with_retry, _parse_questions
from app.ai.prompts.interactive import QUIZ_SYSTEM, build_interactive_quiz_prompt, truncate_context
from app.ai.providers import parse_json_object, resolve_provider
from app.ai.source_pedagogy import build_pedagogy_digest, collect_pedagogy_from_unit_sources
from app.ai.task_types import AI_TASK_FOR_UNIT
from app.ai.validators.interactive import dedupe_interactive_modules, validate_interactive_modules
from app.core.crypto import decrypt_text_master
from app.core.quiz_numeric import repair_quiz_block
from app.core.solution_repair import enrich_card, repair_generated_module
from app.models import LearningRecord, User
from app.services.crypto_json import decrypt_json
from app.services.profile_service import resolve_unit_ai_prefs
from app.services.unit_service import _get_unit_or_404, get_trainer_options

_log = logging.getLogger(__name__)

_RE_EMPTY_ANSWER = re.compile(r"Lernkarte ohne Antwort \(Bereich (\d+)\)")
_RE_FEW_QUESTIONS = re.compile(r"Zu wenige Quizfragen \((\d+), mindestens (\d+)\)")

CARD_ANSWER_REPAIR_SYSTEM = (
    "Du ergänzt fehlende Antworten auf Lernkarten. Antworte NUR mit JSON.\n"
    'Schema: {"answer":"..."}\n'
    "Regeln:\n"
    "- Kurze, fachlich korrekte Antwort passend zur Frage und zum Material.\n"
    "- Keine ISBN/Buchcover-Meta.\n"
)


def parse_repair_hint(error: str | None) -> dict[str, Any] | None:
    if not error:
        return None
    match = _RE_EMPTY_ANSWER.search(error)
    if match:
        return {"kind": "card_answer", "area_index": int(match.group(1)) - 1}
    match = _RE_FEW_QUESTIONS.search(error)
    if match:
        return {
            "kind": "quiz_count",
            "have": int(match.group(1)),
            "need": int(match.group(2)),
        }
    return None


def is_repairable_error(error: str | None) -> bool:
    return parse_repair_hint(error) is not None


def _modules_from_unit(unit) -> list[dict]:
    modules: list[dict] = []
    for mod in sorted(unit.modules or [], key=lambda item: item.order_index):
        content = decrypt_json(mod.content_encrypted) if mod.content_encrypted else {}
        quiz = decrypt_json(mod.quiz_encrypted) if mod.quiz_encrypted else {}
        if not isinstance(content, dict):
            content = {}
        if not isinstance(quiz, dict):
            quiz = {"questions": []}
        modules.append(
            {
                "title": decrypt_text_master(mod.title_encrypted),
                "content": content,
                "quiz": quiz,
            }
        )
    return modules


def _build_repair_context(db: Session, unit, user: User, target_prefs, fallback_prefs) -> tuple[str, str, str]:
    from app.ai.subject_focus import detect_focus_group

    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""
    notes = _collect_source_notes(db, unit, target_prefs, fallback_prefs)
    focus_group = (
        detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or "interactive"))
        or "general"
    )
    pedagogy_profile = collect_pedagogy_from_unit_sources(unit.sources, focus_group=focus_group)
    pedagogy_digest = build_pedagogy_digest(pedagogy_profile)
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    options = get_trainer_options(recon if isinstance(recon, dict) else {})
    style = str(options.get("style") or "mixed")
    answer_length = str(options.get("answer_length") or "short")
    from app.ai.prompts.interactive import build_interactive_plan_prompt

    context_prompt = build_interactive_plan_prompt(
        title=title,
        brief=brief,
        subject=unit.subject,
        math_focus=None,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=unit.difficulty,
        style=style,
        answer_length=answer_length,
        notes=notes,
        card_target=int(options.get("cards") or 12),
        question_target=int(options.get("questions") or 8),
        pedagogy_digest=pedagogy_digest,
    )
    batch_context = truncate_context(context_prompt, pedagogy_digest=pedagogy_digest)
    return batch_context, title, focus_group


def _existing_question_texts(modules: list[dict]) -> list[str]:
    seen: list[str] = []
    for raw in modules:
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        for card in content.get("cards") or []:
            if isinstance(card, dict) and str(card.get("question") or "").strip():
                seen.append(str(card["question"]))
        for q in quiz.get("questions") or []:
            if isinstance(q, dict) and str(q.get("q") or "").strip():
                seen.append(str(q["q"]))
    return seen


def _repair_card_answers(
    modules: list[dict],
    *,
    area_index: int | None,
    batch_context: str,
    provider: str,
    model: str | None,
    unit_id: uuid.UUID,
) -> int:
    fixed = 0
    for index, raw in enumerate(modules):
        if area_index is not None and index != area_index:
            continue
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        cards = content.get("cards") if isinstance(content.get("cards"), list) else []
        category_name = str(raw.get("title") or f"Bereich {index + 1}")
        intro = str(content.get("intro") or "")
        for card in cards:
            if not isinstance(card, dict):
                continue
            question = str(card.get("question") or "").strip()
            answer = str(card.get("answer") or "").strip()
            if not question or answer:
                continue
            prompt = (
                f"{batch_context}\n\n"
                f"Kategorie: {category_name}\n"
                f"Lernziel: {intro or category_name}\n"
                f"Lernkarten-Frage: {question}\n"
                "Ergänze nur die fehlende Antwort als JSON."
            )
            result = _complete_with_retry(
                prompt=prompt,
                provider=provider,
                system=CARD_ANSWER_REPAIR_SYSTEM,
                model=model,
                num_predict=1024,
                label=f"repair_card_{index + 1}",
            )
            parsed = parse_json_object(result["text"])
            new_answer = str(parsed.get("answer") or "").strip()
            if not new_answer:
                raise LlmError(f"Lernkarte ohne Antwort (Bereich {index + 1})", "thin_content")
            card["answer"] = new_answer[:800]
            fixed += 1
            _log.info(
                "batch_repair card_answer unit_id=%s area=%d question=%r",
                unit_id,
                index + 1,
                question[:60],
            )
    return fixed


def _add_quiz_questions(
    modules: list[dict],
    *,
    count: int,
    batch_context: str,
    provider: str,
    model: str | None,
    unit_id: uuid.UUID,
) -> int:
    if count <= 0:
        return 0
    added = 0
    existing = _existing_question_texts(modules)
    ranked = sorted(
        range(len(modules)),
        key=lambda idx: len(
            (
                (modules[idx].get("quiz") or {}).get("questions")
                if isinstance(modules[idx].get("quiz"), dict)
                else []
            )
            or []
        ),
    )
    for module_index in ranked:
        if added >= count:
            break
        raw = modules[module_index]
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {"questions": []}
        questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []
        category_name = str(raw.get("title") or f"Bereich {module_index + 1}")
        intro = str(content.get("intro") or "")
        cards = [c for c in (content.get("cards") or []) if isinstance(c, dict)]
        need_here = min(count - added, max(1, count // max(1, len(modules) - module_index)))
        quiz_prompt = build_interactive_quiz_prompt(
            context=batch_context,
            category_name=category_name,
            category_focus=intro or category_name,
            count=need_here,
            card_summaries=[f"{c.get('question')} → {str(c.get('answer') or '')[:80]}" for c in cards[:6]],
            existing_questions=existing,
        )
        quiz_result = _complete_with_retry(
            prompt=quiz_prompt,
            provider=provider,
            system=QUIZ_SYSTEM,
            model=model,
            num_predict=4096,
            label=f"repair_quiz_{module_index + 1}",
        )
        new_questions = _parse_questions(quiz_result["text"], need_here)
        questions.extend(new_questions)
        quiz["questions"] = questions
        raw["quiz"] = quiz
        for item in new_questions:
            existing.append(str(item.get("q") or ""))
        added += len(new_questions)
        _log.info(
            "batch_repair quiz_added unit_id=%s area=%d count=%d",
            unit_id,
            module_index + 1,
            len(new_questions),
        )
    if added < count:
        total_q = sum(
            len((m.get("quiz") or {}).get("questions") or [])
            for m in modules
            if isinstance(m.get("quiz"), dict)
        )
        raise LlmError(f"Zu wenige Quizfragen ({total_q}, Ziel +{count})", "thin_content")
    return added


def repair_interactive_unit(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    error_hint: str | None = None,
) -> dict[str, Any]:
    """Ergänzt fehlende Karten-Antworten oder Quizfragen in einer Entwurfs-Einheit."""
    unit = _get_unit_or_404(db, user, unit_id)
    if str(unit.task_type or "") != "interactive":
        raise LlmError("Reparatur nur für interaktive Einheiten", "invalid_task")
    if not unit.modules:
        raise LlmError("Keine Module zum Reparieren", "no_modules")

    target_prefs, fallback_prefs = resolve_unit_ai_prefs(db, user, unit.profile_id)
    ai_task = AI_TASK_FOR_UNIT.get("interactive", "mixed")
    name, model = resolve_task_ai_for_unit(target_prefs, fallback_prefs, ai_task)
    name = resolve_provider(name)

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    options = get_trainer_options(recon if isinstance(recon, dict) else {})
    card_target = int(options.get("cards") or 12)
    question_target = int(options.get("questions") or 8)

    modules = _modules_from_unit(unit)
    batch_context, _title, _focus = _build_repair_context(db, unit, user, target_prefs, fallback_prefs)
    hint = parse_repair_hint(error_hint)

    cards_fixed = 0
    questions_added = 0

    if hint and hint["kind"] == "card_answer":
        cards_fixed = _repair_card_answers(
            modules,
            area_index=int(hint["area_index"]),
            batch_context=batch_context,
            provider=name,
            model=model,
            unit_id=unit_id,
        )
    elif hint and hint["kind"] == "quiz_count":
        deficit = int(hint["need"]) - int(hint["have"])
        questions_added = _add_quiz_questions(
            modules,
            count=deficit,
            batch_context=batch_context,
            provider=name,
            model=model,
            unit_id=unit_id,
        )
    else:
        for index, raw in enumerate(modules):
            content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
            for card in content.get("cards") or []:
                if isinstance(card, dict) and str(card.get("question") or "").strip() and not str(
                    card.get("answer") or ""
                ).strip():
                    cards_fixed += _repair_card_answers(
                        modules,
                        area_index=index,
                        batch_context=batch_context,
                        provider=name,
                        model=model,
                        unit_id=unit_id,
                    )
        total_q = sum(
            len((m.get("quiz") or {}).get("questions") or [])
            for m in modules
            if isinstance(m.get("quiz"), dict)
        )
        if total_q < question_target:
            questions_added = _add_quiz_questions(
                modules,
                count=question_target - total_q,
                batch_context=batch_context,
                provider=name,
                model=model,
                unit_id=unit_id,
            )

    if cards_fixed == 0 and questions_added == 0:
        raise LlmError("Keine reparierbaren Lücken gefunden", "nothing_to_do")

    for raw in modules:
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        cards = content.get("cards") if isinstance(content.get("cards"), list) else []
        content["cards"] = [enrich_card(c) if isinstance(c, dict) else c for c in cards]
        raw["content"] = content
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {"questions": []}
        raw["quiz"] = repair_quiz_block(quiz)
        repaired = repair_generated_module({"content": content, "quiz": raw["quiz"]})
        raw["content"] = repaired.get("content") if isinstance(repaired.get("content"), dict) else content
        raw["quiz"] = repair_quiz_block(
            repaired.get("quiz") if isinstance(repaired.get("quiz"), dict) else raw["quiz"]
        )

    modules, _dedupe = dedupe_interactive_modules(modules)
    validate_interactive_modules(
        modules,
        min_cards=max(5, card_target),
        min_questions=max(5, question_target),
    )

    result_meta = {"provider": name, "model": model, "repair": True}
    _save_generated_modules(
        db,
        unit,
        modules,
        result_meta=result_meta,
        task="interactive",
        final=True,
    )
    _log.info(
        "batch_repair done unit_id=%s cards_fixed=%d questions_added=%d",
        unit_id,
        cards_fixed,
        questions_added,
    )
    return {"unit_id": str(unit_id), "cards_fixed": cards_fixed, "questions_added": questions_added}
