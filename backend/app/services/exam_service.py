"""Schulprüfungen hochladen und benoten (Phase A)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.core.crypto.classification import DataClassification
from app.models import ExamResult, LearningRecord, LearningUnit, User
from app.services.audit import log_event
from app.services.crypto_json import decrypt_json, encrypt_json
from app.services.unit_service import (
    UnitError,
    _add_event,
    _copy_sources,
    _dec_unit,
    _get_unit_or_404,
    create_unit,
    upload_dir,
)

EXAM_TYPES = frozenset({"klassenarbeit", "test", "muendlich", "sonstiges"})


def _dec_exam(exam: ExamResult) -> dict:
    analysis = None
    if exam.analysis_encrypted:
        raw = decrypt_json(exam.analysis_encrypted)
        if isinstance(raw, dict):
            analysis = raw
    return {
        "id": str(exam.id),
        "unit_id": str(exam.unit_id) if exam.unit_id else None,
        "record_id": str(exam.record_id),
        "taken_at": exam.taken_at.isoformat() if exam.taken_at else None,
        "exam_type": exam.exam_type,
        "grade_label": decrypt_text_master(exam.grade_label_encrypted)
        if exam.grade_label_encrypted
        else None,
        "score": exam.score,
        "max_score": exam.max_score,
        "notes": decrypt_text_master(exam.notes_encrypted) if exam.notes_encrypted else None,
        "original_name": decrypt_text_master(exam.original_name_encrypted)
        if exam.original_name_encrypted
        else None,
        "content_type": exam.content_type,
        "byte_size": exam.byte_size,
        "has_file": bool(exam.storage_path),
        "status": exam.status,
        "analysis": analysis,
        "remediation_unit_id": str(exam.remediation_unit_id) if exam.remediation_unit_id else None,
        "created_at": exam.created_at.isoformat(),
        "updated_at": exam.updated_at.isoformat(),
    }


def _get_record_for_unit(db: Session, unit_id: uuid.UUID) -> LearningRecord:
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit_id).first()
    if not record:
        raise UnitError("Kein Lernverlauf für diese Einheit", "not_found")
    return record


def _get_exam_or_404(db: Session, user: User, unit_id: uuid.UUID, exam_id: uuid.UUID) -> ExamResult:
    _get_unit_or_404(db, user, unit_id)
    exam = db.get(ExamResult, exam_id)
    if not exam or exam.tenant_id != user.tenant_id or exam.unit_id != unit_id:
        raise UnitError("Prüfung nicht gefunden", "not_found")
    return exam


def list_exams_for_unit(db: Session, user: User, unit_id: uuid.UUID) -> list[dict]:
    _get_unit_or_404(db, user, unit_id)
    rows = (
        db.query(ExamResult)
        .filter(ExamResult.unit_id == unit_id)
        .order_by(ExamResult.taken_at.desc().nullslast(), ExamResult.created_at.desc())
        .all()
    )
    return [_dec_exam(e) for e in rows]


def list_exams_for_record(db: Session, user: User, record_id: uuid.UUID) -> list[dict]:
    from app.services.unit_service import get_record

    get_record(db, user, record_id)
    rows = (
        db.query(ExamResult)
        .filter(ExamResult.record_id == record_id)
        .order_by(ExamResult.taken_at.desc().nullslast(), ExamResult.created_at.desc())
        .all()
    )
    return [_dec_exam(e) for e in rows]


def create_exam(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
    taken_at: date | None = None,
    exam_type: str = "klassenarbeit",
    grade_label: str | None = None,
    score: int | None = None,
    max_score: int | None = None,
    notes: str | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = _get_record_for_unit(db, unit.id)
    kind = (exam_type or "klassenarbeit").strip().lower()
    if kind not in EXAM_TYPES:
        raise UnitError("Unbekannter Prüfungstyp", "invalid_exam_type")
    if score is not None and score < 0:
        raise UnitError("Punkte dürfen nicht negativ sein", "invalid_score")
    if max_score is not None and max_score < 1:
        raise UnitError("Maximalpunkte müssen mindestens 1 sein", "invalid_score")
    if score is not None and max_score is not None and score > max_score:
        raise UnitError("Erreichte Punkte dürfen Maximalpunkte nicht überschreiten", "invalid_score")

    taken_dt = None
    if taken_at:
        taken_dt = datetime.combine(taken_at, datetime.min.time(), tzinfo=timezone.utc)

    exam = ExamResult(
        tenant_id=user.tenant_id,
        record_id=record.id,
        unit_id=unit.id,
        profile_id=unit.profile_id,
        uploaded_by_id=user.id,
        taken_at=taken_dt,
        exam_type=kind,
        grade_label_encrypted=encrypt_text_master(grade_label.strip())
        if grade_label and grade_label.strip()
        else None,
        score=score,
        max_score=max_score,
        notes_encrypted=encrypt_text_master(notes.strip()) if notes and notes.strip() else None,
        original_name_encrypted=encrypt_text_master(filename),
        content_type=content_type,
        byte_size=len(data),
        status="uploaded",
        classification=DataClassification.CONFIDENTIAL,
    )
    db.add(exam)
    db.flush()

    rel = f"exams/{exam.id}"
    dest = upload_dir() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    exam.storage_path = rel
    db.flush()

    _add_event(
        db,
        record,
        "exam_uploaded",
        {
            "exam_id": str(exam.id),
            "exam_type": kind,
            "grade_label": grade_label,
            "score": score,
            "max_score": max_score,
        },
    )
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="exam.create",
        resource_type="exam_result",
        resource_id=exam.id,
        detail=f"unit={unit.id}",
    )
    return _dec_exam(exam)


def update_exam(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    exam_id: uuid.UUID,
    *,
    taken_at: date | None = None,
    exam_type: str | None = None,
    grade_label: str | None = None,
    score: int | None = None,
    max_score: int | None = None,
    notes: str | None = None,
    clear_grade: bool = False,
    clear_notes: bool = False,
) -> dict:
    exam = _get_exam_or_404(db, user, unit_id, exam_id)

    if exam_type is not None:
        kind = exam_type.strip().lower()
        if kind not in EXAM_TYPES:
            raise UnitError("Unbekannter Prüfungstyp", "invalid_exam_type")
        exam.exam_type = kind

    if taken_at is not None:
        exam.taken_at = (
            datetime.combine(taken_at, datetime.min.time(), tzinfo=timezone.utc) if taken_at else None
        )

    if clear_grade:
        exam.grade_label_encrypted = None
    elif grade_label is not None:
        exam.grade_label_encrypted = (
            encrypt_text_master(grade_label.strip()) if grade_label.strip() else None
        )

    if score is not None:
        exam.score = score
    if max_score is not None:
        exam.max_score = max_score

    new_score = exam.score
    new_max = exam.max_score
    if new_score is not None and new_score < 0:
        raise UnitError("Punkte dürfen nicht negativ sein", "invalid_score")
    if new_max is not None and new_max < 1:
        raise UnitError("Maximalpunkte müssen mindestens 1 sein", "invalid_score")
    if new_score is not None and new_max is not None and new_score > new_max:
        raise UnitError("Erreichte Punkte dürfen Maximalpunkte nicht überschreiten", "invalid_score")

    if clear_notes:
        exam.notes_encrypted = None
    elif notes is not None:
        exam.notes_encrypted = encrypt_text_master(notes.strip()) if notes.strip() else None

    db.flush()
    return _dec_exam(exam)


def delete_exam(db: Session, user: User, unit_id: uuid.UUID, exam_id: uuid.UUID) -> None:
    exam = _get_exam_or_404(db, user, unit_id, exam_id)
    _purge_exam_file(exam)
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="exam.delete",
        resource_type="exam_result",
        resource_id=exam.id,
    )
    db.delete(exam)


def exam_file_path(exam: ExamResult) -> Path | None:
    if not exam.storage_path:
        return None
    path = upload_dir() / exam.storage_path
    return path if path.is_file() else None


def get_exam_file(db: Session, user: User, unit_id: uuid.UUID, exam_id: uuid.UUID) -> tuple[ExamResult, Path]:
    exam = _get_exam_or_404(db, user, unit_id, exam_id)
    path = exam_file_path(exam)
    if not path:
        raise UnitError("Datei nicht vorhanden", "not_found")
    return exam, path


def analyze_exam(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    exam_id: uuid.UUID,
    *,
    provider: str | None = None,
) -> dict:
    from app.ai.errors import LlmError
    from app.ai.exam_analyze import analyze_exam_content
    from app.core.crypto import decrypt_text_master

    unit = _get_unit_or_404(db, user, unit_id)
    exam = _get_exam_or_404(db, user, unit_id, exam_id)
    path = exam_file_path(exam)
    if not path:
        raise UnitError("Keine Datei für die Analyse vorhanden", "no_file")

    title = decrypt_text_master(unit.title_encrypted)
    grade = decrypt_text_master(exam.grade_label_encrypted) if exam.grade_label_encrypted else None
    notes = decrypt_text_master(exam.notes_encrypted) if exam.notes_encrypted else None

    from app.services.profile_service import resolve_prefs_for_profile
    from app.services.user_service import get_user_settings

    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)

    try:
        analysis = analyze_exam_content(
            path,
            content_type=exam.content_type,
            subject=unit.subject,
            unit_title=title,
            grade_label=grade,
            score=exam.score,
            max_score=exam.max_score,
            teacher_notes=notes,
            prefs=prefs,
            provider=provider,
        )
    except LlmError as exc:
        raise UnitError(exc.message, "analysis_failed") from exc

    exam.analysis_encrypted = encrypt_json(analysis)
    exam.status = "analyzed"
    db.flush()

    record = db.get(LearningRecord, exam.record_id)
    if record:
        _add_event(
            db,
            record,
            "exam_analyzed",
            {
                "exam_id": str(exam.id),
                "gap_count": len(analysis.get("gaps") or []),
                "pattern_count": len(analysis.get("error_patterns") or []),
            },
        )
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="exam.analyze",
        resource_type="exam_result",
        resource_id=exam.id,
    )
    return _dec_exam(exam)


def _infer_math_focus(analysis: dict, parent_focus: str | None) -> str | None:
    if parent_focus:
        return parent_focus
    from app.ai.task_types import MATH_FOCUS_OPTIONS

    keys = [o["key"] for o in MATH_FOCUS_OPTIONS if o.get("key")]
    for pattern in analysis.get("error_patterns") or []:
        tag = str(pattern.get("tag") or "").lower()
        label = str(pattern.get("label") or "").lower()
        haystack = f"{tag} {label}"
        for key in keys:
            if key and key in haystack:
                return key
    return None


def _build_remediation_brief(
    analysis: dict,
    *,
    unit_brief: str | None,
    grade_label: str | None,
    score: int | None,
    max_score: int | None,
) -> str:
    lines = ["Nacharbeit basierend auf der Schulprüfungs-Analyse."]
    if grade_label:
        lines.append(f"Schulnote: {grade_label}.")
    elif score is not None and max_score is not None:
        lines.append(f"Ergebnis: {score}/{max_score} Punkte.")
    summary = (analysis.get("summary") or "").strip()
    if summary:
        lines.append(f"Zusammenfassung: {summary}")
    gaps = [str(g).strip() for g in (analysis.get("gaps") or []) if str(g).strip()]
    if gaps:
        lines.append("Verständnislücken gezielt üben:")
        lines.extend(f"- {g}" for g in gaps[:8])
    patterns = analysis.get("error_patterns") or []
    if patterns:
        lines.append("Fehlermuster aus der Prüfung:")
        for p in patterns[:8]:
            label = (p.get("label") or p.get("tag") or "").strip()
            if label:
                lines.append(f"- {label}")
    recs = [str(r).strip() for r in (analysis.get("recommendations") or []) if str(r).strip()]
    if recs:
        lines.append("Konkrete Lernschritte:")
        lines.extend(f"- {r}" for r in recs[:6])
    wrong_tasks = [t for t in (analysis.get("tasks") or []) if isinstance(t, dict) and t.get("correct") is False]
    if wrong_tasks:
        lines.append("Fehlerhafte Aufgaben (mit Tags):")
        for t in wrong_tasks[:8]:
            desc = (t.get("description") or "").strip() or f"Aufgabe {t.get('index', '?')}"
            tags = [str(x).strip() for x in (t.get("error_tags") or []) if str(x).strip()]
            tag_part = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"- {desc}{tag_part}")
    if unit_brief and unit_brief.strip():
        lines.append(f"Hintergrund zur Ursprungseinheit: {unit_brief.strip()[:600]}")
    return "\n".join(lines)


def create_remediation_from_exam(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    exam_id: uuid.UUID,
) -> dict:
    """Neue Wiederholungs-Einheit aus Prüfungsanalyse (Phase C)."""
    unit = _get_unit_or_404(db, user, unit_id)
    exam = _get_exam_or_404(db, user, unit_id, exam_id)

    if exam.remediation_unit_id:
        existing = db.get(LearningUnit, exam.remediation_unit_id)
        if existing and existing.tenant_id == user.tenant_id:
            return {"exam": _dec_exam(exam), "unit": _dec_unit(existing)}
        exam.remediation_unit_id = None

    if not exam.analysis_encrypted:
        raise UnitError("Zuerst eine KI-Analyse der Prüfung durchführen", "not_analyzed")
    analysis = decrypt_json(exam.analysis_encrypted)
    if not isinstance(analysis, dict):
        raise UnitError("Analyse-Daten ungültig", "not_analyzed")

    title = decrypt_text_master(unit.title_encrypted)
    if not title.lower().startswith("nacharbeit"):
        title = f"Nacharbeit: {title}"
    unit_brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None
    grade = decrypt_text_master(exam.grade_label_encrypted) if exam.grade_label_encrypted else None
    brief = _build_remediation_brief(
        analysis,
        unit_brief=unit_brief,
        grade_label=grade,
        score=exam.score,
        max_score=exam.max_score,
    )

    parent_focus = None
    src_record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if src_record and src_record.reconstruction_encrypted:
        src_recon = decrypt_json(src_record.reconstruction_encrypted)
        if isinstance(src_recon, dict):
            focus = (src_recon.get("math_focus") or "").strip()
            parent_focus = focus or None
    math_focus = _infer_math_focus(analysis, parent_focus)
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
        math_focus=math_focus,
        profile_id=unit.profile_id,
    )
    new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
    if not new_unit:
        raise UnitError("Nacharbeit konnte nicht erstellt werden", "create_failed")
    _copy_sources(db, unit, new_unit)

    exam.remediation_unit_id = new_unit.id
    exam.status = "action_created"
    db.flush()

    record = db.get(LearningRecord, exam.record_id)
    if record:
        _add_event(
            db,
            record,
            "exam_remediation_created",
            {
                "exam_id": str(exam.id),
                "remediation_unit_id": str(new_unit.id),
                "source_unit_id": str(unit.id),
            },
        )
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="exam.remediation_create",
        resource_type="exam_result",
        resource_id=exam.id,
        detail=f"unit={new_unit.id}",
    )
    return {"exam": _dec_exam(exam), "unit": _dec_unit(new_unit)}


def _purge_exam_file(exam: ExamResult) -> None:
    if exam.storage_path:
        path = upload_dir() / exam.storage_path
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
        exam.storage_path = None
