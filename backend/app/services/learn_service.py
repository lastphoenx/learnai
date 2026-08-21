"""Lernmodus: Fortschritt, Quiz-Antworten, Pause/Resume."""

from __future__ import annotations

import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text_master
from app.core.quiz_numeric import is_quiz_selection_correct, resolve_quiz_correct_index
from app.models import FlashcardProgress, LearningRecord, LearningUnit, UnitModule, User
from app.services.crypto_json import decrypt_json, encrypt_json
from app.services.unit_service import (
    UnitError,
    _add_event,
    _copy_sources,
    _dec_module,
    _dec_unit,
    _get_unit_or_404,
    create_unit,
    get_trainer_options,
)
from app.ai.error_tags import aggregate_quiz_error_tags, infer_quiz_error_tags, label_for_tag
from app.services.audit import log_event
from app.services.exam_insights_service import exam_learning_entry_for_unit


def _default_learn() -> dict:
    return {
        "status": "not_started",
        "module_index": 0,
        "phase": "intro",
        "question_index": 0,
        "modules": {},
        "quiz_correct": 0,
        "quiz_total": 0,
        "started_at": None,
        "completed_at": None,
    }


def _get_stats(record: LearningRecord) -> dict:
    raw = decrypt_json(record.stats_encrypted) or {}
    if not isinstance(raw, dict):
        raw = {}
    learn = raw.get("learn")
    if not isinstance(learn, dict):
        learn = _default_learn()
    else:
        merged = _default_learn()
        merged.update(learn)
        if not isinstance(merged.get("modules"), dict):
            merged["modules"] = {}
        learn = merged
    raw["learn"] = learn
    return raw


def _save_stats(db: Session, record: LearningRecord, stats: dict) -> None:
    record.stats_encrypted = encrypt_json(stats)
    db.flush()


def _get_record_for_unit(db: Session, unit_id: uuid.UUID) -> LearningRecord:
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit_id).first()
    if not record:
        raise UnitError("Verlaufseintrag nicht gefunden", "not_found")
    return record


def _strip_quiz_answers(quiz: dict | None) -> dict | None:
    if not quiz or not isinstance(quiz, dict):
        return quiz
    questions = []
    for q in quiz.get("questions") or []:
        if not isinstance(q, dict):
            continue
        questions.append({"q": q.get("q", ""), "options": q.get("options") or []})
    return {"questions": questions}


def _strip_practice_answers(content: dict | None) -> dict | None:
    if not content or not isinstance(content, dict):
        return content
    out = {k: v for k, v in content.items() if k != "practice"}
    practice = []
    for item in content.get("practice") or []:
        if not isinstance(item, dict):
            continue
        practice.append(
            {
                "prompt": item.get("prompt", ""),
                "hint": item.get("hint"),
                "answer_type": item.get("answer_type") or "text",
            }
        )
    if practice:
        out["practice"] = practice
    return out


def _module_for_learn(module: UnitModule) -> dict:
    data = _dec_module(module)
    content = data.get("content")
    if isinstance(content, dict):
        data["content"] = _strip_practice_answers(content)
    data["quiz"] = _strip_quiz_answers(data.get("quiz"))
    return data


def _progress_summary(stats: dict, module_count: int) -> dict:
    learn = stats.get("learn") or {}
    modules_done = sum(1 for m in (learn.get("modules") or {}).values() if m.get("done"))
    status = learn.get("status") or "not_started"
    pct = round(100 * modules_done / module_count) if module_count else 0
    return {
        "status": status,
        "modules_done": modules_done,
        "module_count": module_count,
        "percent": pct,
        "quiz_correct": learn.get("quiz_correct", 0),
        "quiz_total": learn.get("quiz_total", 0),
    }


def learn_progress_for_unit(db: Session, unit_id: uuid.UUID) -> dict | None:
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit_id).first()
    if not record:
        return None
    unit = db.get(LearningUnit, unit_id)
    count = len(unit.modules) if unit else 0
    return _progress_summary(_get_stats(record), count)


def get_learn_state(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    if not unit.modules:
        raise UnitError("Noch keine Lernblöcke — zuerst mit KI aufbereiten.", "no_modules")
    record = _get_record_for_unit(db, unit.id)
    stats = _get_stats(record)
    learn = stats["learn"]
    modules = sorted(unit.modules, key=lambda m: m.order_index)
    module_payload = [_module_for_learn(m) for m in modules]

    if learn["status"] == "not_started":
        learn["status"] = "in_progress"
        learn["started_at"] = datetime.now(timezone.utc).isoformat()
        learn["phase"] = "intro"
        stats["learn"] = learn
        _save_stats(db, record, stats)
        _add_event(db, record, "learn_started", {"unit_id": str(unit.id)})

    unit_data = _dec_unit(unit, sources=False, modules=False)
    payload: dict = {
        "unit": unit_data,
        "record_id": str(record.id),
        "modules": module_payload,
        "progress": learn,
        "summary": _progress_summary(stats, len(modules)),
    }
    if unit.task_type == "interactive":
        profile_id = _profile_id_for_learn(unit, record)
        payload["trainer"] = _interactive_trainer_payload(
            db, unit, modules, record, profile_id=profile_id
        )
    payload["quiz_weaknesses"] = collect_quiz_weaknesses(db, user, unit_id, stats=stats, unit=unit, record=record)
    payload["exam_entry"] = exam_learning_entry_for_unit(db, user.tenant_id, unit)
    return payload


def save_learn_position(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    module_index: int,
    phase: str,
    question_index: int = 0,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    stats = _get_stats(record)
    learn = stats["learn"]
    module_count = len(unit.modules)
    if module_index < 0 or module_index >= module_count:
        raise UnitError("Ungültiger Modul-Index", "invalid_index")
    if phase not in {"intro", "read", "practice", "quiz", "module_done", "complete"}:
        raise UnitError("Ungültige Phase", "invalid_phase")
    learn["module_index"] = module_index
    learn["phase"] = phase
    learn["question_index"] = max(0, question_index)
    if learn["status"] == "not_started":
        learn["status"] = "in_progress"
        learn["started_at"] = datetime.now(timezone.utc).isoformat()
    stats["learn"] = learn
    _save_stats(db, record, stats)
    _add_event(
        db,
        record,
        "learn_position",
        {"module_index": module_index, "phase": phase, "question_index": question_index},
    )
    return {"progress": learn, "summary": _progress_summary(stats, module_count)}


def mark_text_read(db: Session, user: User, unit_id: uuid.UUID, module_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    module = _find_module(unit, module_id)
    stats = _get_stats(record)
    learn = stats["learn"]
    mod_key = str(module.id)
    mod_prog = learn["modules"].setdefault(mod_key, {})
    mod_prog["text_read"] = True
    stats["learn"] = learn
    _save_stats(db, record, stats)
    _add_event(db, record, "module_text_read", {"module_id": mod_key})
    return {"progress": learn, "summary": _progress_summary(stats, len(unit.modules))}


def submit_quiz_answer(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    module_id: uuid.UUID,
    question_index: int,
    selected: int,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    module = _find_module(unit, module_id)
    quiz = decrypt_json(module.quiz_encrypted) or {}
    questions = quiz.get("questions") or []
    if question_index < 0 or question_index >= len(questions):
        raise UnitError("Ungültige Frage", "invalid_question")
    q = questions[question_index]
    correct_index = resolve_quiz_correct_index(q)
    is_correct = is_quiz_selection_correct(q, selected)

    stats = _get_stats(record)
    learn = stats["learn"]
    mod_key = str(module.id)
    mod_prog = learn["modules"].setdefault(
        mod_key,
        {"text_read": True, "answers": [], "correct": 0, "total": 0, "done": False},
    )
    answers: list[int | None] = mod_prog.setdefault("answers", [])
    while len(answers) <= question_index:
        answers.append(None)
    if answers[question_index] is None:
        learn["quiz_total"] = int(learn.get("quiz_total", 0)) + 1
        if is_correct:
            learn["quiz_correct"] = int(learn.get("quiz_correct", 0)) + 1
            mod_prog["correct"] = int(mod_prog.get("correct", 0)) + 1
        mod_prog["total"] = int(mod_prog.get("total", 0)) + 1
    answers[question_index] = selected
    mod_prog["answers"] = answers

    all_answered = len(answers) >= len(questions) and all(a is not None for a in answers[: len(questions)])
    if all_answered:
        mod_prog["done"] = True
        stats["modules_done"] = sum(
            1 for m in learn["modules"].values() if m.get("done")
        )
        stats["quizzes"] = int(stats.get("quizzes", 0)) + 1

    stats["learn"] = learn
    _save_stats(db, record, stats)
    _add_event(
        db,
        record,
        "quiz_answer",
        {
            "module_id": mod_key,
            "question_index": question_index,
            "selected": selected,
            "correct": is_correct,
        },
    )
    return {
        "correct": is_correct,
        "correct_index": correct_index,
        "explanation": q.get("explanation"),
        "progress": learn,
        "summary": _progress_summary(stats, len(unit.modules)),
        "module_quiz_done": all_answered,
        "quiz_weaknesses": collect_quiz_weaknesses(db, user, unit_id, stats=stats, unit=unit, record=record),
        **maybe_auto_quiz_trainer(db, user, unit, record),
    }


def _practice_items(module: UnitModule) -> list[dict]:
    content = decrypt_json(module.content_encrypted) or {}
    if not isinstance(content, dict):
        return []
    items = content.get("practice") or []
    return [item for item in items if isinstance(item, dict) and str(item.get("prompt", "")).strip()]


def _normalize_practice_answer(text: str, answer_type: str) -> str:
    raw = str(text or "").strip().lower()
    raw = raw.replace(",", ".")
    if answer_type == "number":
        compact = re.sub(r"\s+", "", raw)
        if "/" in compact:
            parts = compact.split("/", 1)
            try:
                return str(float(parts[0]) / float(parts[1]))
            except (ValueError, ZeroDivisionError):
                pass
        match = re.search(r"-?\d+(?:\.\d+)?", compact)
        if match:
            return match.group(0)
    return " ".join(raw.split())


def _practice_answers_match(user_text: str, expected: str, answer_type: str) -> bool:
    user_norm = _normalize_practice_answer(user_text, answer_type)
    expected_norm = _normalize_practice_answer(expected, answer_type)
    if answer_type == "number":
        try:
            return abs(float(user_norm) - float(expected_norm)) < 1e-6
        except ValueError:
            return user_norm == expected_norm
    return user_norm == expected_norm


def submit_practice_answer(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    module_id: uuid.UUID,
    exercise_index: int,
    answer_text: str,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    module = _find_module(unit, module_id)
    items = _practice_items(module)
    if exercise_index < 0 or exercise_index >= len(items):
        raise UnitError("Ungültige Übung", "invalid_index")
    item = items[exercise_index]
    answer_type = str(item.get("answer_type") or "text").strip().lower() or "text"
    expected = str(item.get("answer") or "").strip()
    if not expected:
        raise UnitError("Übung ohne Lösung", "invalid_question")
    is_correct = _practice_answers_match(answer_text, expected, answer_type)

    stats = _get_stats(record)
    learn = stats["learn"]
    mod_key = str(module.id)
    mod_prog = learn["modules"].setdefault(
        mod_key,
        {"text_read": True, "answers": [], "practice_answers": [], "correct": 0, "total": 0, "done": False},
    )
    practice_answers: list[dict | None] = mod_prog.setdefault("practice_answers", [])
    while len(practice_answers) <= exercise_index:
        practice_answers.append(None)
    if practice_answers[exercise_index] is None:
        practice_answers[exercise_index] = {
            "answer": answer_text.strip(),
            "correct": is_correct,
        }
    mod_prog["practice_answers"] = practice_answers
    stats["learn"] = learn
    _save_stats(db, record, stats)
    _add_event(
        db,
        record,
        "practice_answer",
        {
            "module_id": mod_key,
            "exercise_index": exercise_index,
            "correct": is_correct,
        },
    )
    return {
        "correct": is_correct,
        "hint": item.get("hint"),
        "expected": expected if not is_correct else None,
        "progress": learn,
        "summary": _progress_summary(stats, len(unit.modules)),
        "practice_done": len(practice_answers) >= len(items)
        and all(a is not None for a in practice_answers[: len(items)]),
    }


def complete_learn(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    stats = _get_stats(record)
    learn = stats["learn"]
    learn["status"] = "completed"
    learn["phase"] = "complete"
    learn["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["learn"] = learn
    _save_stats(db, record, stats)
    _add_event(db, record, "learn_completed", {"unit_id": str(unit.id)})
    auto = maybe_auto_quiz_trainer(db, user, unit, record)
    return {
        "progress": learn,
        "summary": _progress_summary(stats, len(unit.modules)),
        "quiz_weaknesses": collect_quiz_weaknesses(db, user, unit_id, stats=stats, unit=unit, record=record),
        **auto,
    }


def reset_learn_progress(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    stats = _get_stats(record)
    learn = stats.get("learn") or {}
    attempts = stats.get("learn_attempts") if isinstance(stats.get("learn_attempts"), list) else []
    if learn.get("status") in {"in_progress", "completed"}:
        attempts.append(
            {
                "completed_at": learn.get("completed_at"),
                "quiz_correct": learn.get("quiz_correct", 0),
                "quiz_total": learn.get("quiz_total", 0),
                "modules_done": sum(
                    1 for m in (learn.get("modules") or {}).values() if m.get("done")
                ),
            }
        )
    fresh = _default_learn()
    fresh["status"] = "in_progress"
    fresh["phase"] = "intro"
    stats["learn"] = fresh
    stats["modules_done"] = 0
    stats["learn_attempts"] = attempts[-10:]
    _clear_flashcard_progress(db, record)
    _save_stats(db, record, stats)
    _add_event(db, record, "learn_reset", {"unit_id": str(unit.id)})
    module_count = len(unit.modules)
    return {"progress": fresh, "summary": _progress_summary(stats, module_count)}


def _find_module(unit: LearningUnit, module_id: uuid.UUID) -> UnitModule:
    for m in unit.modules:
        if m.id == module_id:
            return m
    raise UnitError("Lernblock nicht gefunden", "not_found")


def _profile_id_for_learn(unit: LearningUnit, record: LearningRecord) -> uuid.UUID:
    profile_id = record.profile_id or unit.profile_id
    if not profile_id:
        raise UnitError("Kein Lernprofil zugeordnet", "forbidden")
    return profile_id


def _flashcard_key(module_id: uuid.UUID, card_index: int) -> str:
    return f"{module_id}:{card_index}"


def _apply_spaced_schedule(row: FlashcardProgress, status: str, now: datetime) -> None:
    if status == "review":
        row.interval_days = 1
        row.next_review_at = now + timedelta(days=1)
    elif status == "known":
        prev = int(row.interval_days or 0)
        row.interval_days = 3 if prev < 3 else min(prev * 2, 30)
        row.next_review_at = now + timedelta(days=row.interval_days)
    else:
        row.interval_days = 0
        row.next_review_at = None


def _flashcard_is_due(row: FlashcardProgress | None, *, now: datetime) -> bool:
    if row is None:
        return True
    if row.status == "review":
        return True
    if row.status != "known":
        return True
    if row.next_review_at is None:
        return True
    return row.next_review_at <= now


def _progress_entry(row: FlashcardProgress, *, now: datetime) -> dict[str, Any]:
    return {
        "status": row.status,
        "attempts": row.attempts,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "next_review_at": row.next_review_at.isoformat() if row.next_review_at else None,
        "interval_days": int(row.interval_days or 0),
        "due": _flashcard_is_due(row, now=now),
    }


def flashcard_progress_map(
    db: Session,
    *,
    profile_id: uuid.UUID,
    module_ids: list[uuid.UUID],
) -> dict[str, dict]:
    if not module_ids:
        return {}
    rows = (
        db.query(FlashcardProgress)
        .filter(
            FlashcardProgress.profile_id == profile_id,
            FlashcardProgress.unit_module_id.in_(module_ids),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    return {
        _flashcard_key(row.unit_module_id, row.card_index): _progress_entry(row, now=now)
        for row in rows
    }


def flashcard_stats_for_unit(
    db: Session,
    *,
    profile_id: uuid.UUID,
    unit: LearningUnit,
) -> dict[str, int]:
    modules = list(unit.modules or [])
    module_ids = [m.id for m in modules]
    progress = flashcard_progress_map(db, profile_id=profile_id, module_ids=module_ids)
    card_count = 0
    for module in modules:
        content = decrypt_json(module.content_encrypted) or {}
        if isinstance(content, dict):
            card_count += len(content.get("cards") or [])
    known_cards = sum(1 for p in progress.values() if p.get("status") == "known")
    review_cards = sum(1 for p in progress.values() if p.get("status") == "review")
    due_cards = 0
    for module in modules:
        content = decrypt_json(module.content_encrypted) or {}
        if not isinstance(content, dict):
            continue
        for index in range(len(content.get("cards") or [])):
            key = _flashcard_key(module.id, index)
            if progress.get(key, {}).get("due", True):
                due_cards += 1
    return {
        "card_count": card_count,
        "known_cards": known_cards,
        "review_cards": review_cards,
        "due_cards": due_cards,
    }


def _clear_flashcard_progress(db: Session, record: LearningRecord) -> None:
    db.query(FlashcardProgress).filter(FlashcardProgress.learning_record_id == record.id).delete()
    db.flush()


def mark_flashcard_status(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    module_id: uuid.UUID,
    card_index: int,
    status: str,
) -> dict:
    if status not in {"known", "review", "unseen"}:
        raise UnitError("Ungültiger Kartenstatus", "invalid_phase")
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    module = _find_module(unit, module_id)
    profile_id = _profile_id_for_learn(unit, record)
    content = decrypt_json(module.content_encrypted) or {}
    cards = content.get("cards") if isinstance(content, dict) else []
    if card_index < 0 or card_index >= len(cards):
        raise UnitError("Ungültige Lernkarte", "invalid_index")

    row = (
        db.query(FlashcardProgress)
        .filter(
            FlashcardProgress.profile_id == profile_id,
            FlashcardProgress.unit_module_id == module.id,
            FlashcardProgress.card_index == card_index,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if not row:
        row = FlashcardProgress(
            profile_id=profile_id,
            learning_record_id=record.id,
            unit_module_id=module.id,
            card_index=card_index,
            status=status,
            attempts=1,
            last_seen_at=now,
        )
        db.add(row)
    else:
        row.status = status
        row.attempts = int(row.attempts or 0) + 1
        row.last_seen_at = now

    _apply_spaced_schedule(row, status, now)

    db.flush()
    module_ids = [m.id for m in unit.modules]
    progress = flashcard_progress_map(db, profile_id=profile_id, module_ids=module_ids)
    return {"flashcard_progress": progress, "card_key": _flashcard_key(module.id, card_index), "status": status}


def _interactive_trainer_payload(
    db: Session,
    unit: LearningUnit,
    modules: list[UnitModule],
    record: LearningRecord,
    *,
    profile_id: uuid.UUID,
) -> dict:
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    knowledge: list[dict] = []
    cards: list[dict] = []
    total_questions = 0
    for module in modules:
        content = decrypt_json(module.content_encrypted) or {}
        if not isinstance(content, dict):
            continue
        domain = decrypt_text_master(module.title_encrypted)
        for item in content.get("knowledge") or []:
            if isinstance(item, dict):
                knowledge.append({**item, "domain": domain, "module_id": str(module.id)})
        for index, card in enumerate(content.get("cards") or []):
            if isinstance(card, dict):
                cards.append(
                    {
                        **card,
                        "domain": domain,
                        "module_id": str(module.id),
                        "card_index": index,
                        "card_key": _flashcard_key(module.id, index),
                    }
                )
        quiz = decrypt_json(module.quiz_encrypted) or {}
        total_questions += len((quiz.get("questions") if isinstance(quiz, dict) else []) or [])

    module_ids = [m.id for m in modules]
    progress = flashcard_progress_map(db, profile_id=profile_id, module_ids=module_ids)
    known = sum(1 for p in progress.values() if p.get("status") == "known")
    due_cards = sum(1 for card in cards if progress.get(card["card_key"], {}).get("due", True))
    return {
        "options": get_trainer_options(recon if isinstance(recon, dict) else {}),
        "knowledge": knowledge,
        "cards": cards,
        "flashcard_progress": progress,
        "stats": {
            "card_count": len(cards),
            "question_count": total_questions,
            "known_cards": known,
            "review_cards": sum(1 for p in progress.values() if p.get("status") == "review"),
            "due_cards": due_cards,
        },
    }


QUIZ_TRAINER_OPTIONS: dict[str, int | str] = {
    "cards": 20,
    "questions": 15,
    "style": "playful",
    "answer_length": "short",
}

AUTO_REMEDIATION_MIN_WRONG = 3
AUTO_REMEDIATION_MIN_TOTAL = 3
AUTO_REMEDIATION_MIN_RATIO = 0.25


def maybe_auto_quiz_trainer(
    db: Session,
    user: User,
    unit: LearningUnit,
    record: LearningRecord,
) -> dict[str, Any]:
    weakness_data = collect_quiz_weaknesses(db, user, unit.id, unit=unit, record=record)
    if weakness_data.get("trainer_unit_id"):
        return {}
    wrong = int(weakness_data.get("wrong_count") or 0)
    total = int(weakness_data.get("quiz_total") or 0)
    if wrong < AUTO_REMEDIATION_MIN_WRONG or total < AUTO_REMEDIATION_MIN_TOTAL:
        return {}
    if wrong / total < AUTO_REMEDIATION_MIN_RATIO:
        return {}
    try:
        result = create_interactive_trainer_from_quiz(db, user, unit.id)
        trainer_id = str(result["unit"]["id"])
        enqueue_trainer_generate(trainer_id, user)
        return {
            "auto_trainer_unit_id": trainer_id,
            "auto_trainer_started": True,
        }
    except UnitError:
        return {}


def enqueue_trainer_generate(unit_id: str, user: User) -> None:
    from app.services.generate_job import get_generate_job, job_is_active, set_generate_job
    from app.services.generate_limits import acquire_generate_slot
    from app.tasks.generate import generate_unit_task

    if job_is_active(get_generate_job(unit_id)):
        return
    try:
        acquire_generate_slot(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            unit_id=unit_id,
        )
    except Exception:
        return
    set_generate_job(unit_id, user_id=str(user.id), status="queued", stage="queued")
    generate_unit_task.delay(unit_id, str(user.id), None)


def _parent_recon(record: LearningRecord) -> dict:
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    return recon if isinstance(recon, dict) else {}


def _save_parent_recon(db: Session, record: LearningRecord, recon: dict) -> None:
    record.reconstruction_encrypted = encrypt_json(recon)
    db.flush()


def collect_quiz_weaknesses(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    stats: dict | None = None,
    unit: LearningUnit | None = None,
    record: LearningRecord | None = None,
) -> dict:
    unit = unit or _get_unit_or_404(db, user, unit_id)
    record = record or _get_record_for_unit(db, unit.id)
    stats = stats or _get_stats(record)
    learn = stats.get("learn") or {}
    modules = sorted(unit.modules or [], key=lambda m: m.order_index)
    weaknesses: list[dict[str, Any]] = []
    recon = _parent_recon(record)
    math_focus = (recon.get("math_focus") or "").strip() if isinstance(recon.get("math_focus"), str) else ""

    for module in modules:
        mod_key = str(module.id)
        mod_prog = (learn.get("modules") or {}).get(mod_key) or {}
        answers = mod_prog.get("answers") or []
        quiz = decrypt_json(module.quiz_encrypted) or {}
        questions = quiz.get("questions") if isinstance(quiz, dict) else []
        if not isinstance(questions, list):
            questions = []
        module_title = decrypt_text_master(module.title_encrypted)

        for i, selected in enumerate(answers):
            if i >= len(questions) or selected is None:
                continue
            q = questions[i]
            if not isinstance(q, dict):
                continue
            correct_index = resolve_quiz_correct_index(q)
            if is_quiz_selection_correct(q, selected):
                continue
            options = q.get("options") or []
            question_text = str(q.get("q", ""))
            explanation = str(q.get("explanation") or "")
            error_tags = infer_quiz_error_tags(
                question=question_text,
                module_title=module_title,
                explanation=explanation,
                math_focus=math_focus,
            )
            weaknesses.append(
                {
                    "module_id": mod_key,
                    "module_title": module_title,
                    "question_index": i,
                    "question": question_text,
                    "selected": selected,
                    "selected_label": options[selected] if 0 <= selected < len(options) else None,
                    "correct_index": correct_index,
                    "correct_label": options[correct_index] if 0 <= correct_index < len(options) else None,
                    "explanation": q.get("explanation"),
                    "error_tags": error_tags,
                }
            )

    quiz_correct = int(learn.get("quiz_correct", 0))
    quiz_total = int(learn.get("quiz_total", 0))
    error_tags = aggregate_quiz_error_tags(weaknesses)
    return {
        "quiz_correct": quiz_correct,
        "quiz_total": quiz_total,
        "wrong_count": len(weaknesses),
        "weaknesses": weaknesses,
        "error_tags": error_tags,
        "remediation_unit_id": recon.get("quiz_remediation_unit_id"),
        "trainer_unit_id": recon.get("quiz_trainer_unit_id"),
        "can_remediate": len(weaknesses) > 0 and quiz_total > 0,
    }


def _append_weakness_details(lines: list[str], weakness_data: dict, *, max_per_module: int) -> None:
    tag_rows = weakness_data.get("error_tags") or []
    if tag_rows:
        lines.append("\nFehlermuster (Tags):")
        for row in tag_rows[:12]:
            label = row.get("label") or label_for_tag(str(row.get("tag") or ""))
            count = row.get("count", 1)
            lines.append(f"- {label} ({row.get('tag')}): {count}×")
    by_module: dict[str, list[dict]] = {}
    for item in weakness_data.get("weaknesses") or []:
        title = (item.get("module_title") or "Thema").strip()
        by_module.setdefault(title, []).append(item)
    for mod_title, items in by_module.items():
        lines.append(f"\nThema «{mod_title}» ({len(items)} Fehler):")
        for w in items[:max_per_module]:
            tag_hint = ", ".join(w.get("error_tags") or []) or "—"
            lines.append(f"- Frage: {w.get('question', '').strip()} [{tag_hint}]")
            if w.get("selected_label"):
                lines.append(f"  Gewählt: {w['selected_label']}")
            if w.get("correct_label"):
                lines.append(f"  Richtig: {w['correct_label']}")
            if w.get("explanation"):
                lines.append(f"  Erklärung: {w['explanation']}")


def build_review_brief_from_quiz_weaknesses(
    weakness_data: dict,
    *,
    unit_title: str,
    unit_brief: str | None,
) -> str:
    lines = [
        "Wiederholung/Festigung mit Fokus auf Quiz-Schwächen aus der App.",
        f"Ursprungseinheit: {unit_title}.",
        f"Quiz-Ergebnis: {weakness_data['quiz_correct']}/{weakness_data['quiz_total']} richtig.",
        "Erstelle 2–3 kurze Module nur zu den unten genannten Fehlern — keine 1:1-Neugenerierung des ganzen Stoffs.",
    ]
    _append_weakness_details(lines, weakness_data, max_per_module=8)
    if unit_brief and unit_brief.strip():
        lines.append(f"\nHintergrund: {unit_brief.strip()[:600]}")
    return "\n".join(lines)


def _build_quiz_remediation_brief(
    weakness_data: dict,
    *,
    unit_title: str,
    unit_brief: str | None,
) -> str:
    lines = [
        "Nacharbeit basierend auf falschen Quiz-Antworten in der App.",
        f"Ursprungseinheit: {unit_title}.",
        f"Quiz-Ergebnis: {weakness_data['quiz_correct']}/{weakness_data['quiz_total']} richtig.",
        "Erstelle 1–2 kurze Lernmodule (Tutorial-Stil): Einstieg erklären, dann Verständnisfragen.",
        "Fokus nur auf die unten genannten Fehler — keine Wiederholung des ganzen Stoffs.",
    ]
    _append_weakness_details(lines, weakness_data, max_per_module=8)
    if unit_brief and unit_brief.strip():
        lines.append(f"\nHintergrund: {unit_brief.strip()[:600]}")
    return "\n".join(lines)


def _build_quiz_trainer_brief(
    weakness_data: dict,
    *,
    unit_title: str,
    unit_brief: str | None,
) -> str:
    lines = [
        "Interaktiver Lerntrainer — gezielt zu Quiz-Schwächen aus der App.",
        "Erstelle Lernkarten und Quiz NUR zu den unten genannten Fehlern.",
        "Didaktik: kurzes Kernwissen (Tutorial), dann Karten zum Üben, dann Check-Fragen.",
        f"Ursprungseinheit: {unit_title}.",
        f"Quiz-Ergebnis: {weakness_data['quiz_correct']}/{weakness_data['quiz_total']} richtig.",
    ]
    _append_weakness_details(lines, weakness_data, max_per_module=10)
    if unit_brief and unit_brief.strip():
        lines.append(f"\nKontext: {unit_brief.strip()[:400]}")
    return "\n".join(lines)


def create_remediation_from_quiz(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    weakness_data = collect_quiz_weaknesses(db, user, unit_id, unit=unit, record=record)
    if not weakness_data["can_remediate"]:
        raise UnitError("Keine Quiz-Schwächen — zuerst lernen und Fragen beantworten.", "no_weaknesses")

    recon = _parent_recon(record)
    existing_id = recon.get("quiz_remediation_unit_id")
    if existing_id:
        existing = db.get(LearningUnit, uuid.UUID(str(existing_id)))
        if existing and existing.tenant_id == user.tenant_id:
            return {"weaknesses": weakness_data, "unit": _dec_unit(existing)}

    title = decrypt_text_master(unit.title_encrypted)
    if not title.lower().startswith("nacharbeit"):
        title = f"Nacharbeit (Quiz): {title}"
    unit_brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None
    brief = _build_quiz_remediation_brief(
        weakness_data,
        unit_title=decrypt_text_master(unit.title_encrypted),
        unit_brief=unit_brief,
    )

    parent_focus = None
    if recon.get("math_focus"):
        parent_focus = str(recon.get("math_focus")).strip() or None
    new_difficulty = min(unit.difficulty + 1, 5)

    result = create_unit(
        db,
        user,
        title=title,
        brief=brief,
        subject=unit.subject,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=new_difficulty,
        task_type="review",
        math_focus=parent_focus,
        profile_id=unit.profile_id,
    )
    new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
    if not new_unit:
        raise UnitError("Nacharbeit konnte nicht erstellt werden", "create_failed")
    _copy_sources(db, unit, new_unit)

    recon["quiz_remediation_unit_id"] = str(new_unit.id)
    _save_parent_recon(db, record, recon)
    _add_event(
        db,
        record,
        "quiz_remediation_created",
        {
            "remediation_unit_id": str(new_unit.id),
            "source_unit_id": str(unit.id),
            "wrong_count": weakness_data["wrong_count"],
        },
    )
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="learn.quiz_remediation_create",
        resource_type="learning_unit",
        resource_id=unit.id,
        detail=f"remediation={new_unit.id}",
    )
    return {"weaknesses": weakness_data, "unit": _dec_unit(new_unit)}


def create_interactive_trainer_from_quiz(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    weakness_data = collect_quiz_weaknesses(db, user, unit_id, unit=unit, record=record)
    if not weakness_data["can_remediate"]:
        raise UnitError("Keine Quiz-Schwächen — zuerst lernen und Fragen beantworten.", "no_weaknesses")

    recon = _parent_recon(record)
    existing_id = recon.get("quiz_trainer_unit_id")
    if existing_id:
        existing = db.get(LearningUnit, uuid.UUID(str(existing_id)))
        if existing and existing.tenant_id == user.tenant_id:
            return {"weaknesses": weakness_data, "unit": _dec_unit(existing)}

    title = decrypt_text_master(unit.title_encrypted)
    if not title.lower().startswith("trainer:"):
        title = f"Trainer (Quiz): {title}"
    unit_brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None
    brief = _build_quiz_trainer_brief(
        weakness_data,
        unit_title=decrypt_text_master(unit.title_encrypted),
        unit_brief=unit_brief,
    )

    parent_focus = None
    if recon.get("math_focus"):
        parent_focus = str(recon.get("math_focus")).strip() or None

    result = create_unit(
        db,
        user,
        title=title,
        brief=brief,
        subject=unit.subject,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=unit.difficulty,
        task_type="interactive",
        math_focus=parent_focus,
        profile_id=unit.profile_id,
    )
    new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
    if not new_unit:
        raise UnitError("Trainer-Einheit konnte nicht erstellt werden", "create_failed")
    _copy_sources(db, unit, new_unit)

    new_record = db.query(LearningRecord).filter(LearningRecord.unit_id == new_unit.id).first()
    if new_record:
        child_recon = _parent_recon(new_record)
        child_recon["source_unit_id"] = str(unit.id)
        child_recon["trainer_options"] = dict(QUIZ_TRAINER_OPTIONS)
        new_record.reconstruction_encrypted = encrypt_json(child_recon)

    recon["quiz_trainer_unit_id"] = str(new_unit.id)
    _save_parent_recon(db, record, recon)
    _add_event(
        db,
        record,
        "quiz_trainer_created",
        {
            "trainer_unit_id": str(new_unit.id),
            "source_unit_id": str(unit.id),
            "wrong_count": weakness_data["wrong_count"],
        },
    )
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="learn.quiz_trainer_create",
        resource_type="learning_unit",
        resource_id=unit.id,
        detail=f"trainer={new_unit.id}",
    )
    return {"weaknesses": weakness_data, "unit": _dec_unit(new_unit)}
