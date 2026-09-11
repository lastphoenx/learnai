"""Kompakte Qualitätsübersicht für Batch-Import-Jobs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.crypto import decrypt_text_master
from app.models import LearningRecord, LearningUnit, User
from app.services.batch_import_service import get_batch_import_status
from app.services.crypto_json import decrypt_json
from app.services.pedagogy_service import _pedagogy_quality
from app.services.unit_reference_service import ensure_unit_reference_codes
from app.services.unit_service import UnitError, get_trainer_options


def _count_trainer_content(unit: LearningUnit) -> tuple[int, int, int]:
    modules = len(unit.modules or [])
    cards = 0
    questions = 0
    for module in unit.modules or []:
        content = decrypt_json(module.content_encrypted) if module.content_encrypted else {}
        quiz = decrypt_json(module.quiz_encrypted) if module.quiz_encrypted else {}
        if isinstance(content, dict):
            raw_cards = content.get("cards")
            if isinstance(raw_cards, list):
                cards += len(raw_cards)
        if isinstance(quiz, dict):
            raw_questions = quiz.get("questions")
            if isinstance(raw_questions, list):
                questions += len(raw_questions)
    return modules, cards, questions


def summarize_batch_unit_quality(db: Session, user: User, unit_id: uuid.UUID) -> dict[str, Any]:
    unit = (
        db.query(LearningUnit)
        .options(joinedload(LearningUnit.modules), joinedload(LearningUnit.sources), joinedload(LearningUnit.profile))
        .filter(LearningUnit.id == unit_id, LearningUnit.tenant_id == user.tenant_id)
        .first()
    )
    if not unit:
        raise UnitError("Einheit nicht gefunden", "not_found")

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    refs = ensure_unit_reference_codes(db, unit, record, persist=True) if record else {}
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    trainer = get_trainer_options(recon if isinstance(recon, dict) else {})
    modules, cards, questions = _count_trainer_content(unit)

    from app.ai.source_pedagogy import collect_pedagogy_from_unit_sources
    from app.ai.subject_focus import detect_focus_group

    focus_group = detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or "interactive"))
    pedagogy_profile = collect_pedagogy_from_unit_sources(unit.sources, focus_group=focus_group)
    quality = _pedagogy_quality(pedagogy_profile, focus_group=focus_group)

    return {
        "unit_id": str(unit.id),
        "reference_code": refs.get("reference_code"),
        "title": decrypt_text_master(unit.title_encrypted),
        "status": unit.status,
        "module_count": modules,
        "card_count": cards,
        "question_count": questions,
        "trainer_target_cards": trainer.get("cards"),
        "trainer_target_questions": trainer.get("questions"),
        "pedagogy_level": quality.get("level"),
        "pedagogy_methods": quality.get("method_count"),
        "pedagogy_key_terms": quality.get("key_term_count"),
        "unit_url": f"/units/{unit.id}",
        "report_ref": refs.get("reference_code"),
    }


def build_batch_import_quality_summary(db: Session, user: User, batch_id: str) -> dict[str, Any]:
    job = get_batch_import_status(db, user, batch_id)
    rows: list[dict[str, Any]] = []
    done = failed = pending = 0

    for index, row in enumerate(job.get("units") or []):
        if not isinstance(row, dict):
            continue
        status = str(row.get("generate_status") or "pending")
        if status == "done":
            done += 1
        elif status == "failed":
            failed += 1
        elif status == "pending":
            pending += 1

        entry: dict[str, Any] = {
            "index": index,
            "title": row.get("title"),
            "posten": row.get("posten"),
            "is_review": bool(row.get("is_review")),
            "generate_status": status,
            "error": row.get("error"),
            "page_from": row.get("page_from"),
            "page_to": row.get("page_to"),
            "quality": None,
        }
        unit_id_raw = row.get("unit_id")
        if unit_id_raw and status == "done":
            try:
                entry["quality"] = summarize_batch_unit_quality(db, user, uuid.UUID(str(unit_id_raw)))
            except UnitError:
                entry["quality"] = None
        rows.append(entry)

    return {
        "batch_id": batch_id,
        "job_status": job.get("status"),
        "total": job.get("total") or len(rows),
        "done": done,
        "failed": failed,
        "pending": pending,
        "rows": rows,
    }
