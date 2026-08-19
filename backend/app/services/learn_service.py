"""Lernmodus: Fortschritt, Quiz-Antworten, Pause/Resume."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import LearningRecord, LearningUnit, UnitModule, User
from app.services.crypto_json import decrypt_json, encrypt_json
from app.services.unit_service import UnitError, _add_event, _dec_module, _dec_unit, _get_unit_or_404


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
    return {
        "unit": unit_data,
        "record_id": str(record.id),
        "modules": module_payload,
        "progress": learn,
        "summary": _progress_summary(stats, len(modules)),
    }


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


def _find_module(unit: LearningUnit, module_id: uuid.UUID) -> UnitModule:
    for m in unit.modules:
        if m.id == module_id:
            return m
    raise UnitError("Lernblock nicht gefunden", "not_found")
