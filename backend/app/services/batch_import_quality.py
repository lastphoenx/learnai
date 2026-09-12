"""Kompakte Qualitätsübersicht für Batch-Import-Jobs."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.crypto import decrypt_text_master
from app.models import LearningRecord, LearningUnit, User
from app.services.batch_import_service import get_batch_import_status
from app.services.crypto_json import decrypt_json
from app.services.pedagogy_service import _pedagogy_quality
from app.services.unit_quality_report_service import build_unit_quality_report_for_user
from app.services.ai_run_snapshot import format_finished_at_zurich, format_last_ai_run_compact, last_ai_run_from_recon, normalize_last_ai_run_snapshot
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
    last_ai_run = last_ai_run_from_recon(recon if isinstance(recon, dict) else None)

    payload: dict[str, Any] = {
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
    if last_ai_run:
        display_run = normalize_last_ai_run_snapshot(last_ai_run) or last_ai_run
        payload["last_ai_run"] = {
            "finished_at": display_run.get("finished_at"),
            "pipeline": display_run.get("pipeline"),
            "tasks": display_run.get("tasks"),
            "stats": display_run.get("stats"),
            "vision_used": display_run.get("vision_used"),
            "summary": format_last_ai_run_compact(display_run),
        }
    return payload


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
        if unit_id_raw and status in {"done", "failed"}:
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


def _batch_report_filename(job: dict[str, Any], batch_id: str) -> str:
    label = str(job.get("label") or job.get("description") or "batch").strip()
    slug = re.sub(r"[^\w\-]+", "_", label, flags=re.UNICODE).strip("_")[:60] or "batch"
    short_id = str(batch_id).split("-", 1)[0]
    return f"{slug}_{short_id}_quality.md"


def build_batch_import_quality_report(db: Session, user: User, batch_id: str) -> dict[str, Any]:
    """Vollständiger Markdown-Report für alle Batch-Zeilen mit Referenz."""
    job = get_batch_import_status(db, user, batch_id)
    summary = build_batch_import_quality_summary(db, user, batch_id)
    generated_at = datetime.now(timezone.utc).isoformat()
    generated_at_display = format_finished_at_zurich(generated_at) or generated_at
    label = str(job.get("label") or "").strip() or batch_id

    header = [
        "# LearnAI Batch — Qualitätsreports",
        "",
        f"**Batch:** {label}",
        f"**Batch-ID:** `{batch_id}`",
        f"**Status:** {summary.get('job_status') or job.get('status') or '—'}",
        f"**Fortschritt:** {summary.get('done', 0)}/{summary.get('total', 0)} fertig",
        f"**Erstellt:** {generated_at_display} (Europe/Zurich)",
        "",
    ]

    body: list[str] = []
    unit_count = 0
    skipped = 0

    for row in summary.get("rows") or []:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or f"Zeile {int(row.get('index', 0)) + 1}")
        status = str(row.get("generate_status") or "pending")
        quality = row.get("quality") if isinstance(row.get("quality"), dict) else None
        ref = str((quality or {}).get("reference_code") or "").strip()
        if not ref:
            skipped += 1
            continue
        try:
            unit_report = build_unit_quality_report_for_user(db, user, ref)
        except UnitError:
            skipped += 1
            continue
        unit_count += 1
        body.append("---")
        body.append("")
        body.append(f"<!-- {title} · {status} · {ref} -->")
        body.append("")
        body.append(str(unit_report.get("report") or "").rstrip())
        body.append("")

    if unit_count <= 0:
        raise UnitError("Keine Reports für diesen Batch — keine fertigen Einheiten mit Referenz", "nothing_to_do")

    if skipped:
        header.append(f"*Hinweis: {skipped} Zeile(n) ohne Report übersprungen.*")
        header.append("")

    report = "\n".join(header + body).strip() + "\n"
    return {
        "batch_id": batch_id,
        "label": label,
        "filename": _batch_report_filename(job, batch_id),
        "unit_count": unit_count,
        "skipped": skipped,
        "generated_at": generated_at,
        "report": report,
    }
