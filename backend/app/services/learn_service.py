"""Lernmodus: Fortschritt, Quiz-Antworten, Pause/Resume."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text_master
from app.models import FlashcardProgress, LearningRecord, LearningUnit, UnitModule, User
from app.services.crypto_json import decrypt_json, encrypt_json
from app.services.unit_service import (
    UnitError,
    _add_event,
    _dec_module,
    _dec_unit,
    _get_unit_or_404,
    get_trainer_options,
)


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


def _module_for_learn(module: UnitModule) -> dict:
    data = _dec_module(module)
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
    if phase not in {"intro", "read", "quiz", "module_done", "complete"}:
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
    correct_index = int(q.get("answer", -1))
    is_correct = selected == correct_index

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
    return {"progress": learn, "summary": _progress_summary(stats, len(unit.modules))}


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
    return {
        _flashcard_key(row.unit_module_id, row.card_index): {
            "status": row.status,
            "attempts": row.attempts,
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        }
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
    return {
        "card_count": card_count,
        "known_cards": known_cards,
        "review_cards": review_cards,
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
        },
    }
