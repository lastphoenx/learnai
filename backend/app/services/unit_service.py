"""Lerneinheiten: lebendes Gefäss + Verlauf, der das Löschen überlebt."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.core.crypto.classification import DataClassification
from app.models import LearningEvent, LearningRecord, LearningUnit, UnitModule, UnitSource, User
from app.services.audit import log_event
from app.services.crypto_json import decrypt_json, encrypt_json
from app.ai.task_types import UNIT_TASK_KEYS, augment_brief
from app.schemas import LearnGoalsSchema, TrainerOptionsSchema
from app.services.profile_service import ProfileError, child_user_ids, get_profile_for_actor
from app.services.unit_reference_service import attach_reference_fields, ensure_unit_reference_codes

_log = logging.getLogger(__name__)


class UnitError(Exception):
    def __init__(self, message: str, code: str = "unit_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _managed_profile(db: Session, user: User, profile_id: uuid.UUID):
    """Profil laden; ProfileError als UnitError, damit die API keinen 500 liefert."""
    try:
        return get_profile_for_actor(db, user, profile_id)
    except ProfileError as exc:
        raise UnitError(exc.message, exc.code) from exc


def reconstruction_payload(
    *,
    title: str,
    brief: str | None,
    subject: str | None,
    language: str,
    target_age: str | None,
    difficulty: int,
    task_type: str = "mixed",
    math_focus: str | None = None,
    trainer_options: dict | None = None,
    learn_goals: dict | None = None,
) -> dict:
    payload = {
        "title": title,
        "brief": brief or "",
        "subject": subject,
        "language": language,
        "target_age": target_age,
        "difficulty": difficulty,
        "task_type": task_type,
        "math_focus": math_focus or "",
    }
    if trainer_options:
        payload["trainer_options"] = trainer_options
    if learn_goals:
        payload["learn_goals"] = learn_goals
    return payload


DEFAULT_TRAINER_OPTIONS: dict = {
    "cards": 50,
    "questions": 50,
    "style": "playful",
    "answer_length": "short",
    "llm_provider": None,
}


def get_trainer_options(recon: dict | None) -> dict:
    if not isinstance(recon, dict):
        return TrainerOptionsSchema().model_dump()
    raw = recon.get("trainer_options")
    if not isinstance(raw, dict):
        return TrainerOptionsSchema().model_dump()
    merged = dict(DEFAULT_TRAINER_OPTIONS)
    for key in DEFAULT_TRAINER_OPTIONS:
        if key in raw and raw[key] is not None:
            merged[key] = raw[key]
    return TrainerOptionsSchema.normalize_raw(merged).model_dump()


def get_learn_goals(recon: dict | None) -> dict:
    if not isinstance(recon, dict):
        return LearnGoalsSchema.normalize_raw({}).model_dump()
    raw = recon.get("learn_goals")
    if not isinstance(raw, dict):
        return LearnGoalsSchema.normalize_raw({}).model_dump()
    return LearnGoalsSchema.normalize_raw(raw).model_dump()


def _template_ids_from_recon(recon: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(recon, dict):
        return None, None
    template_unit_id = str(recon.get("template_unit_id") or "").strip() or None
    template_root_id = str(recon.get("template_root_id") or "").strip() or None
    return template_unit_id, template_root_id


def _sandbox_fields_from_recon(recon: dict | None) -> tuple[str | None, bool]:
    if not isinstance(recon, dict):
        return None, False
    sandbox_copy_of = str(recon.get("sandbox_copy_of") or "").strip() or None
    return sandbox_copy_of, bool(sandbox_copy_of)


def unit_is_sandbox_copy(unit: LearningUnit, record: LearningRecord | None) -> bool:
    """Test-/Sandbox-Kopie ohne Kind-Zuordnung (oder mit Erwachsenen-Profil zum Testen)."""
    if record and record.reconstruction_encrypted:
        recon = decrypt_json(record.reconstruction_encrypted)
        if isinstance(recon, dict) and recon.get("sandbox_copy_of"):
            return True
    try:
        title = decrypt_text_master(unit.title_encrypted) if unit.title_encrypted else ""
    except Exception:
        title = ""
    return str(title).strip().lower().startswith("test:")


def _attach_template_fields(row: dict, record: LearningRecord | None) -> None:
    template_unit_id, template_root_id = None, None
    sandbox_copy_of, is_sandbox_copy = None, False
    if record and record.reconstruction_encrypted:
        recon = decrypt_json(record.reconstruction_encrypted)
        template_unit_id, template_root_id = _template_ids_from_recon(recon)
        sandbox_copy_of, is_sandbox_copy = _sandbox_fields_from_recon(recon)
    if not is_sandbox_copy:
        title = str(row.get("title") or "").strip()
        if title.lower().startswith("test:"):
            is_sandbox_copy = True
    row["template_unit_id"] = template_unit_id
    row["template_root_id"] = template_root_id or row["id"]
    row["sandbox_copy_of"] = sandbox_copy_of
    row["is_sandbox_copy"] = is_sandbox_copy


def _dec_unit(unit: LearningUnit, *, sources: bool = True, modules: bool = True) -> dict:
    learner_name = None
    if unit.profile_id and unit.profile:
        learner_name = unit.profile.display_name
    data = {
        "id": str(unit.id),
        "title": decrypt_text_master(unit.title_encrypted),
        "brief": decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None,
        "subject": unit.subject,
        "language": unit.language,
        "target_age": unit.target_age,
        "difficulty": unit.difficulty,
        "task_type": unit.task_type,
        "status": unit.status,
        "auto_purge_sources": unit.auto_purge_sources,
        "profile_id": str(unit.profile_id) if unit.profile_id else None,
        "learner_name": learner_name,
        "created_at": (unit.created_at or datetime.now(timezone.utc)).isoformat(),
        "updated_at": (unit.updated_at or datetime.now(timezone.utc)).isoformat(),
        "source_count": len(unit.sources),
        "module_count": len(unit.modules),
    }
    if sources:
        data["sources"] = [_dec_source(s) for s in unit.sources]
    if modules:
        data["modules"] = [_dec_module(m) for m in sorted(unit.modules, key=lambda x: x.order_index)]
    return data


def _dec_source(source: UnitSource) -> dict:
    return {
        "id": str(source.id),
        "kind": source.kind,
        "original_name": (
            decrypt_text_master(source.original_name_encrypted) if source.original_name_encrypted else None
        ),
        "content_type": source.content_type,
        "byte_size": source.byte_size,
        "has_file": bool(source.storage_path) and source.purged_at is None,
        "has_extracted_text": source.extracted_text_encrypted is not None,
        "purged_at": source.purged_at.isoformat() if source.purged_at else None,
        "created_at": source.created_at.isoformat(),
    }


def _dec_module(module: UnitModule) -> dict:
    return {
        "id": str(module.id),
        "order_index": module.order_index,
        "title": decrypt_text_master(module.title_encrypted),
        "content": decrypt_json(module.content_encrypted),
        "quiz": decrypt_json(module.quiz_encrypted),
    }


def _dec_record(record: LearningRecord, *, exam_count: int | None = None) -> dict:
    learner_name = None
    if record.profile_id and record.profile:
        learner_name = record.profile.display_name
    return {
        "id": str(record.id),
        "unit_id": str(record.unit_id) if record.unit_id else None,
        "unit_alive": record.unit_id is not None,
        "profile_id": str(record.profile_id) if record.profile_id else None,
        "learner_name": learner_name,
        "title": decrypt_text_master(record.title_encrypted),
        "summary": decrypt_text_master(record.summary_encrypted) if record.summary_encrypted else None,
        "subject": record.subject,
        "language": record.language,
        "difficulty": record.difficulty,
        "reconstruction": decrypt_json(record.reconstruction_encrypted),
        "stats": decrypt_json(record.stats_encrypted) or {},
        "exam_count": exam_count if exam_count is not None else len(record.exam_results),
        "last_activity_at": record.last_activity_at.isoformat(),
        "created_at": record.created_at.isoformat(),
    }


def _add_event(db: Session, record: LearningRecord, event_type: str, payload: dict | None = None) -> None:
    db.add(
        LearningEvent(
            record_id=record.id,
            event_type=event_type,
            payload_encrypted=encrypt_json(payload) if payload else None,
        )
    )
    record.last_activity_at = datetime.now(timezone.utc)


def _accessible_units(db: Session, user: User):
    from sqlalchemy import or_

    q = db.query(LearningUnit).filter(LearningUnit.tenant_id == user.tenant_id)
    if user.is_admin:
        return q
    child_ids = child_user_ids(db, user)
    clauses = [LearningUnit.created_by_id == user.id, LearningUnit.learner_id == user.id]
    if child_ids:
        clauses.append(LearningUnit.learner_id.in_(child_ids))
    from app.services.profile_service import accessible_profile_ids

    profile_ids = accessible_profile_ids(db, user)
    if profile_ids:
        clauses.append(LearningUnit.profile_id.in_(profile_ids))
    return q.filter(or_(*clauses))


def list_units(db: Session, user: User) -> list[dict]:
    from app.services.learn_service import learn_progress_for_unit

    units = _accessible_units(db, user).order_by(LearningUnit.created_at.desc()).all()
    unit_ids = [u.id for u in units]
    records_by_unit: dict[uuid.UUID, LearningRecord] = {}
    if unit_ids:
        for record in db.query(LearningRecord).filter(LearningRecord.unit_id.in_(unit_ids)).all():
            records_by_unit[record.unit_id] = record
    out = []
    for u in units:
        row = _dec_unit(u, sources=False, modules=False)
        record = records_by_unit.get(u.id)
        _attach_template_fields(row, record)
        try:
            refs = ensure_unit_reference_codes(db, u, record)
            attach_reference_fields(row, refs)
        except Exception:
            _log.exception("reference codes failed unit_id=%s", u.id)
            attach_reference_fields(
                row,
                {"reference_family": None, "reference_instance": None, "reference_code": None},
            )
        prog = learn_progress_for_unit(db, u.id)
        if prog:
            row["learn_progress"] = prog
        out.append(row)
    return out


def get_unit(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    from app.services.learn_service import learn_progress_for_unit

    unit = _get_unit_or_404(db, user, unit_id)
    data = _dec_unit(unit)
    from app.models import ExamResult
    from app.services.exam_service import _dec_exam

    exam_rows = (
        db.query(ExamResult)
        .filter(ExamResult.unit_id == unit.id)
        .order_by(ExamResult.taken_at.desc().nullslast(), ExamResult.created_at.desc())
        .all()
    )
    data["exams"] = [_dec_exam(e, db) for e in exam_rows]
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    _attach_template_fields(data, record)
    refs = ensure_unit_reference_codes(db, unit, record)
    attach_reference_fields(data, refs)
    recon: dict | None = None
    if record and record.reconstruction_encrypted:
        raw_recon = decrypt_json(record.reconstruction_encrypted)
        recon = raw_recon if isinstance(raw_recon, dict) else None
    if recon:
        focus = (recon.get("math_focus") or "").strip()
        if focus:
            data["math_focus"] = focus
    prog = learn_progress_for_unit(db, unit.id)
    if prog:
        data["learn_progress"] = prog
    if recon and unit.task_type == "interactive":
        data["trainer_options"] = get_trainer_options(recon)
        data["learn_goals"] = get_learn_goals(recon)
    return data


def _get_unit_or_404(db: Session, user: User, unit_id: uuid.UUID) -> LearningUnit:
    unit = (
        db.query(LearningUnit)
        .options(joinedload(LearningUnit.modules), joinedload(LearningUnit.sources), joinedload(LearningUnit.profile))
        .filter(LearningUnit.id == unit_id)
        .first()
    )
    if not unit or unit.tenant_id != user.tenant_id:
        raise UnitError("Lerneinheit nicht gefunden", "not_found")
    if user.is_admin:
        return unit
    accessible = _accessible_units(db, user).filter(LearningUnit.id == unit_id).first()
    if not accessible:
        raise UnitError("Kein Zugriff auf diese Lerneinheit", "forbidden")
    return unit


def create_unit(
    db: Session,
    user: User,
    *,
    title: str,
    brief: str | None = None,
    subject: str | None = None,
    language: str = "de",
    target_age: str | None = None,
    difficulty: int = 1,
    task_type: str = "mixed",
    auto_purge_sources: bool = False,
    profile_id: uuid.UUID | None = None,
    math_focus: str | None = None,
    unassigned: bool = False,
) -> dict:
    if difficulty < 1 or difficulty > 5:
        raise UnitError("Schwierigkeit muss 1–5 sein", "invalid_difficulty")
    kind = (task_type or "mixed").strip().lower()
    if kind not in UNIT_TASK_KEYS:
        raise UnitError("Unbekannter Aufgabentyp", "invalid_task_type")

    focus = (math_focus or "").strip() or None
    effective_brief = augment_brief(brief, task_key=kind, math_focus=focus)

    learner_id = user.id
    chosen_profile_id: uuid.UUID | None = None
    if unassigned:
        chosen_profile_id = None
        learner_id = user.id
    elif profile_id:
        profile = _managed_profile(db, user, profile_id)
        chosen_profile_id = profile.id
        if profile.user_id:
            learner_id = profile.user_id
    elif user.profile_id:
        profile = _managed_profile(db, user, user.profile_id)
        chosen_profile_id = profile.id
        if profile.user_id:
            learner_id = profile.user_id

    recon = reconstruction_payload(
        title=title,
        brief=effective_brief,
        subject=subject,
        language=language,
        target_age=target_age,
        difficulty=difficulty,
        task_type=kind,
        math_focus=focus,
        trainer_options=dict(DEFAULT_TRAINER_OPTIONS) if kind == "interactive" else None,
    )
    unit = LearningUnit(
        tenant_id=user.tenant_id,
        created_by_id=user.id,
        learner_id=learner_id,
        profile_id=chosen_profile_id,
        title_encrypted=encrypt_text_master(title),
        brief_encrypted=encrypt_text_master(effective_brief) if effective_brief else None,
        subject=subject,
        language=language,
        target_age=target_age,
        difficulty=difficulty,
        task_type=kind,
        status="draft",
        auto_purge_sources=auto_purge_sources,
        classification=DataClassification.INTERNAL,
    )
    db.add(unit)
    db.flush()

    record = LearningRecord(
        tenant_id=user.tenant_id,
        user_id=learner_id,
        profile_id=chosen_profile_id,
        unit_id=unit.id,
        title_encrypted=encrypt_text_master(title),
        summary_encrypted=encrypt_text_master(effective_brief) if effective_brief else encrypt_text_master(title),
        subject=subject,
        language=language,
        difficulty=difficulty,
        reconstruction_encrypted=encrypt_json(recon),
        stats_encrypted=encrypt_json({"modules_done": 0, "quizzes": 0, "exams": 0, "learn": {
            "status": "not_started",
            "module_index": 0,
            "phase": "intro",
            "question_index": 0,
            "modules": {},
            "quiz_correct": 0,
            "quiz_total": 0,
            "started_at": None,
            "completed_at": None,
        }}),
    )
    db.add(record)
    db.flush()
    _add_event(db, record, "unit_created", {"title": title})
    ensure_unit_reference_codes(db, unit, record)
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.create",
        resource_type="learning_unit",
        resource_id=unit.id,
    )
    return _dec_unit(unit)


def _resolve_profile_targets(
    db: Session,
    user: User,
    *,
    profile_id: uuid.UUID | None,
    profile_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID | None]:
    if profile_ids:
        seen: set[uuid.UUID] = set()
        ordered: list[uuid.UUID] = []
        for pid in profile_ids:
            if pid in seen:
                continue
            profile = _managed_profile(db, user, pid)
            seen.add(profile.id)
            ordered.append(profile.id)
        if not ordered:
            raise UnitError("Kein Profil gewählt", "invalid_profile")
        return ordered
    if profile_id:
        profile = _managed_profile(db, user, profile_id)
        return [profile.id]
    return [None]


def create_units(
    db: Session,
    user: User,
    *,
    title: str,
    brief: str | None = None,
    subject: str | None = None,
    language: str = "de",
    target_age: str | None = None,
    difficulty: int = 1,
    task_type: str = "mixed",
    auto_purge_sources: bool = False,
    profile_id: uuid.UUID | None = None,
    profile_ids: list[uuid.UUID] | None = None,
    math_focus: str | None = None,
) -> list[dict]:
    targets = _resolve_profile_targets(db, user, profile_id=profile_id, profile_ids=profile_ids)
    return [
        create_unit(
            db,
            user,
            title=title,
            brief=brief,
            subject=subject,
            language=language,
            target_age=target_age,
            difficulty=difficulty,
            task_type=task_type,
            auto_purge_sources=auto_purge_sources,
            profile_id=pid,
            math_focus=math_focus,
        )
        for pid in targets
    ]


def assign_unit_to_profiles(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    profile_ids: list[uuid.UUID],
) -> list[dict]:
    """Vollständige Vorlage-Kopie für weitere Kinder: Quellen + Lernblöcke + Trainer-Metadaten."""
    unit = _get_unit_or_404(db, user, unit_id)
    if not profile_ids:
        raise UnitError("Keine Profile gewählt", "invalid_profile")

    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None
    math_focus = None
    src_record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if src_record and src_record.reconstruction_encrypted:
        src_recon = decrypt_json(src_record.reconstruction_encrypted)
        if isinstance(src_recon, dict):
            focus = (src_recon.get("math_focus") or "").strip()
            math_focus = focus or None

    template_modules = len(unit.modules or [])
    created: list[dict] = []
    seen: set[uuid.UUID | None] = {unit.profile_id}
    for pid in profile_ids:
        if pid in seen:
            continue
        _managed_profile(db, user, pid)
        seen.add(pid)
        result = create_unit(
            db,
            user,
            title=title,
            brief=brief,
            subject=unit.subject,
            language=unit.language,
            target_age=unit.target_age,
            difficulty=unit.difficulty,
            task_type=unit.task_type or "mixed",
            math_focus=math_focus,
            auto_purge_sources=unit.auto_purge_sources,
            profile_id=pid,
        )
        new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
        if new_unit:
            _copy_sources(db, unit, new_unit)
            new_record = db.query(LearningRecord).filter(LearningRecord.unit_id == new_unit.id).first()
            if new_record:
                _copy_template_metadata(
                    db,
                    from_unit=unit,
                    from_record=src_record,
                    to_unit=new_unit,
                    to_record=new_record,
                )
            db.refresh(new_unit, attribute_names=["modules", "sources", "status"])
            row = _dec_unit(new_unit)
            _attach_template_fields(row, new_record)
            created.append(row)
        else:
            created.append(result)
    if not created:
        raise UnitError("Einheit ist bereits allen gewählten Kindern zugewiesen", "already_assigned")
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.assign",
        resource_type="learning_unit",
        resource_id=unit.id,
        detail=f"copies={len(created)} modules_template={template_modules}",
    )
    return created


def create_test_copy_from_unit(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    """Sandbox-Kopie ohne Kind-Zuordnung — gleiche Quellen/Blöcke, eigener (leerer) Fortschritt."""
    if user.is_child:
        raise UnitError("Nur für Eltern-Accounts", "forbidden")
    unit = _get_unit_or_404(db, user, unit_id)
    src_record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()

    title = decrypt_text_master(unit.title_encrypted)
    if not title.lower().startswith("test:"):
        title = f"Test: {title}"
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None
    math_focus = None
    if src_record and src_record.reconstruction_encrypted:
        src_recon = decrypt_json(src_record.reconstruction_encrypted)
        if isinstance(src_recon, dict):
            focus = (src_recon.get("math_focus") or "").strip()
            math_focus = focus or None

    result = create_unit(
        db,
        user,
        title=title,
        brief=brief,
        subject=unit.subject,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=unit.difficulty,
        task_type=unit.task_type or "mixed",
        math_focus=math_focus,
        auto_purge_sources=unit.auto_purge_sources,
        unassigned=True,
    )
    new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
    if not new_unit:
        return result

    _copy_sources(db, unit, new_unit)
    new_record = db.query(LearningRecord).filter(LearningRecord.unit_id == new_unit.id).first()
    if new_record:
        _copy_template_metadata(
            db,
            from_unit=unit,
            from_record=src_record,
            to_unit=new_unit,
            to_record=new_record,
        )
        dst_recon = decrypt_json(new_record.reconstruction_encrypted) or {}
        if isinstance(dst_recon, dict):
            dst_recon["sandbox_copy_of"] = str(unit.id)
            new_record.reconstruction_encrypted = encrypt_json(dst_recon)

    db.refresh(new_unit, attribute_names=["modules", "sources", "status"])
    row = _dec_unit(new_unit)
    _attach_template_fields(row, new_record)
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.test_copy",
        resource_type="learning_unit",
        resource_id=new_unit.id,
        detail=f"from={unit.id}",
    )
    return row


def get_source_file(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    source_id: uuid.UUID,
) -> tuple[UnitSource, Path]:
    unit = _get_unit_or_404(db, user, unit_id)
    source = db.get(UnitSource, source_id)
    if not source or source.unit_id != unit.id:
        raise UnitError("Quelle nicht gefunden", "not_found")
    if not source.storage_path or source.purged_at is not None:
        raise UnitError("Datei nicht vorhanden", "not_found")
    path = upload_dir() / source.storage_path
    if not path.is_file():
        raise UnitError("Datei nicht vorhanden", "not_found")
    return source, path


def create_unit_from_record(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    *,
    difficulty: int | None = None,
    task_type: str | None = None,
) -> dict:
    record = db.get(LearningRecord, record_id)
    if not record or record.tenant_id != user.tenant_id:
        raise UnitError("Verlaufseintrag nicht gefunden", "not_found")
    if not user.is_admin and record.user_id != user.id:
        child_ids = child_user_ids(db, user)
        if record.user_id not in child_ids:
            from app.services.profile_service import can_view_profile_data

            if not record.profile_id or not can_view_profile_data(db, user, record.profile_id):
                raise UnitError("Kein Zugriff", "forbidden")
    recon = decrypt_json(record.reconstruction_encrypted) or {}
    new_difficulty = difficulty if difficulty is not None else int(recon.get("difficulty") or record.difficulty)
    kind = (task_type or recon.get("task_type") or "mixed").strip().lower()
    title = str(recon.get("title") or decrypt_text_master(record.title_encrypted))
    if kind == "review" and not title.lower().startswith("wiederholung"):
        title = f"Wiederholung: {title}"
    return create_unit(
        db,
        user,
        title=title,
        brief=recon.get("brief") or (decrypt_text_master(record.summary_encrypted) if record.summary_encrypted else None),
        subject=recon.get("subject") or record.subject,
        language=str(recon.get("language") or record.language),
        target_age=recon.get("target_age"),
        difficulty=new_difficulty,
        task_type=kind,
        math_focus=recon.get("math_focus") or None,
        profile_id=record.profile_id,
    )


def _copy_sources(db: Session, from_unit: LearningUnit, to_unit: LearningUnit) -> None:
    import shutil

    for src in from_unit.sources:
        new_src = UnitSource(
            unit_id=to_unit.id,
            kind=src.kind,
            original_name_encrypted=src.original_name_encrypted,
            content_type=src.content_type,
            byte_size=src.byte_size,
            extracted_text_encrypted=src.extracted_text_encrypted,
            analysis_encrypted=src.analysis_encrypted,
        )
        db.add(new_src)
        db.flush()
        if src.storage_path and src.purged_at is None:
            old_path = upload_dir() / src.storage_path
            if old_path.is_file():
                rel = f"{to_unit.id}/{new_src.id}"
                dest = upload_dir() / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old_path, dest)
                new_src.storage_path = rel
        db.flush()


def _copy_modules(db: Session, from_unit: LearningUnit, to_unit: LearningUnit) -> int:
    """Kopiert Lernblöcke 1:1 (verschlüsselte Inhalte) — Vorlage für weiteres Kind."""
    modules = sorted(from_unit.modules or [], key=lambda m: m.order_index)
    for mod in modules:
        db.add(
            UnitModule(
                unit_id=to_unit.id,
                order_index=mod.order_index,
                title_encrypted=mod.title_encrypted,
                content_encrypted=mod.content_encrypted,
                quiz_encrypted=mod.quiz_encrypted,
            )
        )
    if modules:
        to_unit.status = from_unit.status if from_unit.status in {"ready", "draft"} else "ready"
    db.flush()
    return len(modules)


def _copy_template_metadata(
    db: Session,
    *,
    from_unit: LearningUnit,
    from_record: LearningRecord | None,
    to_unit: LearningUnit,
    to_record: LearningRecord,
) -> int:
    """Quellen-Inhalt ist separat; hier Module + Trainer-Metadaten aus der Vorlage."""
    module_count = _copy_modules(db, from_unit, to_unit)
    if from_record and from_record.reconstruction_encrypted:
        src_recon = decrypt_json(from_record.reconstruction_encrypted)
        if isinstance(src_recon, dict):
            dst_recon = decrypt_json(to_record.reconstruction_encrypted) or {}
            if not isinstance(dst_recon, dict):
                dst_recon = {}
            trainer_options = src_recon.get("trainer_options")
            if isinstance(trainer_options, dict) and trainer_options:
                dst_recon["trainer_options"] = dict(trainer_options)
            learn_goals = src_recon.get("learn_goals")
            if isinstance(learn_goals, dict) and learn_goals:
                dst_recon["learn_goals"] = dict(learn_goals)
            math_focus = (src_recon.get("math_focus") or "").strip()
            if math_focus:
                dst_recon["math_focus"] = math_focus
            dst_recon["template_unit_id"] = str(from_unit.id)
            dst_recon["template_root_id"] = (
                str(src_recon.get("template_root_id") or "").strip() or str(from_unit.id)
            )
            to_record.reconstruction_encrypted = encrypt_json(dst_recon)
    ensure_unit_reference_codes(db, to_unit, to_record)
    if module_count:
        _add_event(
            db,
            to_record,
            "unit_template_copied",
            {"source_unit_id": str(from_unit.id), "module_count": module_count},
        )
    db.flush()
    return module_count


def create_review_from_unit(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    """Wiederholung — bei Quiz-Schwächen Trainer-Pfad, sonst fehlerbasierte Review oder Quellen-Kopie."""
    from app.services.learn_service import (
        build_review_brief_from_quiz_weaknesses,
        collect_quiz_weaknesses,
        create_interactive_trainer_from_quiz,
        enqueue_trainer_generate,
    )

    unit = _get_unit_or_404(db, user, unit_id)
    src_record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    weakness_data = collect_quiz_weaknesses(
        db, user, unit_id, unit=unit, record=src_record
    )

    if weakness_data.get("can_remediate"):
        trainer_result = create_interactive_trainer_from_quiz(db, user, unit_id)
        trainer_unit = trainer_result["unit"]
        enqueue_trainer_generate(str(trainer_unit["id"]), user)
        log_event(
            db,
            tenant_id=user.tenant_id,
            actor_id=user.id,
            action="unit.review_create",
            resource_type="learning_unit",
            resource_id=uuid.UUID(trainer_unit["id"]),
            detail=f"from={unit.id} mode=quiz_trainer wrong={weakness_data['wrong_count']}",
        )
        return {**trainer_unit, "review_mode": "quiz_trainer"}

    title = decrypt_text_master(unit.title_encrypted)
    if not title.lower().startswith("wiederholung"):
        title = f"Wiederholung: {title}"
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""
    math_focus = None
    difficulty = unit.difficulty
    quiz_error_tags: list[dict] = []
    if src_record and src_record.reconstruction_encrypted:
        src_recon = decrypt_json(src_record.reconstruction_encrypted)
        if isinstance(src_recon, dict):
            focus = (src_recon.get("math_focus") or "").strip()
            math_focus = focus or None

    if weakness_data.get("wrong_count", 0) > 0 and weakness_data.get("quiz_total", 0) > 0:
        brief = build_review_brief_from_quiz_weaknesses(
            weakness_data,
            unit_title=decrypt_text_master(unit.title_encrypted),
            unit_brief=brief or None,
        )
        quiz_error_tags = weakness_data.get("error_tags") or []
        difficulty = min(unit.difficulty + 1, 5)

    result = create_unit(
        db,
        user,
        title=title,
        brief=brief,
        subject=unit.subject,
        language=unit.language,
        target_age=unit.target_age,
        difficulty=difficulty,
        task_type="review",
        math_focus=math_focus,
        profile_id=unit.profile_id,
    )
    new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
    if new_unit:
        _copy_sources(db, unit, new_unit)
        if quiz_error_tags and src_record:
            new_record = db.query(LearningRecord).filter(LearningRecord.unit_id == new_unit.id).first()
            if new_record:
                recon = decrypt_json(new_record.reconstruction_encrypted) or {}
                if not isinstance(recon, dict):
                    recon = {}
                recon["quiz_error_tags"] = quiz_error_tags
                recon["review_source_unit_id"] = str(unit.id)
                recon["review_from_quiz_weaknesses"] = True
                new_record.reconstruction_encrypted = encrypt_json(recon)
                db.flush()
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.review_create",
        resource_type="learning_unit",
        resource_id=uuid.UUID(result["id"]),
        detail=f"from={unit.id}",
    )
    return _dec_unit(new_unit) if new_unit else result


def _template_root_for_unit(unit: LearningUnit, record: LearningRecord | None) -> str:
    if record and record.reconstruction_encrypted:
        recon = decrypt_json(record.reconstruction_encrypted)
        if isinstance(recon, dict):
            root = str(recon.get("template_root_id") or "").strip()
            if root:
                return root
    return str(unit.id)


def _conflicting_template_sibling(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    template_root: str,
    profile_id: uuid.UUID,
    exclude_unit_id: uuid.UUID,
) -> LearningUnit | None:
    candidates = (
        db.query(LearningUnit)
        .filter(
            LearningUnit.tenant_id == tenant_id,
            LearningUnit.profile_id == profile_id,
            LearningUnit.id != exclude_unit_id,
        )
        .all()
    )
    for candidate in candidates:
        record = db.query(LearningRecord).filter(LearningRecord.unit_id == candidate.id).first()
        if _template_root_for_unit(candidate, record) == template_root:
            return candidate
    return None


def update_unit_profile(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    profile_id: uuid.UUID | None,
) -> dict:
    """Kind-Zuordnung setzen oder aufheben — Einheit bleibt erhalten."""
    if user.is_child:
        raise UnitError("Nur für Eltern-Accounts", "forbidden")
    unit = _get_unit_or_404(db, user, unit_id)
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    template_root = _template_root_for_unit(unit, record)

    new_profile_id: uuid.UUID | None = None
    new_learner_id = unit.created_by_id

    is_sandbox = unit_is_sandbox_copy(unit, record)

    if profile_id is not None:
        profile = _managed_profile(db, user, profile_id)
        if not profile.is_child_profile and not is_sandbox:
            raise UnitError("Nur Kinder-Profile können zugewiesen werden", "invalid_profile")
        if profile.is_child_profile:
            conflict = _conflicting_template_sibling(
                db,
                tenant_id=user.tenant_id,
                template_root=template_root,
                profile_id=profile.id,
                exclude_unit_id=unit.id,
            )
            if conflict:
                raise UnitError(
                    "Dieses Kind hat bereits eine Kopie dieser Einheit",
                    "already_assigned",
                )
        new_profile_id = profile.id
        if profile.user_id:
            new_learner_id = profile.user_id

    unit.profile_id = new_profile_id
    unit.learner_id = new_learner_id
    if record:
        record.profile_id = new_profile_id
        record.user_id = new_learner_id
        _add_event(
            db,
            record,
            "unit_profile_changed",
            {
                "profile_id": str(new_profile_id) if new_profile_id else None,
                "learner_id": str(new_learner_id),
            },
        )
    db.flush()
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.profile",
        resource_type="learning_unit",
        resource_id=unit.id,
        detail=f"profile_id={new_profile_id or 'none'}",
    )
    return get_unit(db, user, unit.id)


def update_unit_flags(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    auto_purge_sources: bool | None = None,
) -> dict:
    return update_unit(db, user, unit_id, auto_purge_sources=auto_purge_sources)


def update_unit(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    title: str | None = None,
    brief: str | None = None,
    subject: str | None = None,
    language: str | None = None,
    target_age: str | None = None,
    difficulty: int | None = None,
    task_type: str | None = None,
    math_focus: str | None = None,
    auto_purge_sources: bool | None = None,
    trainer_options: dict | None = None,
    learn_goals: dict | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}

    if title is not None:
        cleaned = title.strip()
        if not cleaned:
            raise UnitError("Titel darf nicht leer sein", "invalid_title")
        unit.title_encrypted = encrypt_text_master(cleaned)

    if subject is not None:
        unit.subject = subject.strip() or None
    if language is not None:
        unit.language = language.strip() or "de"
    if target_age is not None:
        unit.target_age = target_age.strip() or None
    if difficulty is not None:
        if difficulty < 1 or difficulty > 5:
            raise UnitError("Schwierigkeit muss 1–5 sein", "invalid_difficulty")
        unit.difficulty = difficulty

    kind = unit.task_type
    if task_type is not None:
        kind = (task_type or "mixed").strip().lower()
        if kind not in UNIT_TASK_KEYS:
            raise UnitError("Unbekannter Aufgabentyp", "invalid_task_type")
        unit.task_type = kind

    focus = (recon.get("math_focus") or "").strip() or None
    if math_focus is not None:
        focus = (math_focus or "").strip() or None

    brief_changed = brief is not None or task_type is not None or math_focus is not None
    if brief_changed:
        current_brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""
        new_brief = brief.strip() if brief is not None else current_brief
        effective_brief = augment_brief(new_brief or None, task_key=kind, math_focus=focus)
        unit.brief_encrypted = encrypt_text_master(effective_brief) if effective_brief else None

    if auto_purge_sources is not None:
        unit.auto_purge_sources = auto_purge_sources

    if trainer_options is not None:
        merged = get_trainer_options(recon)
        if isinstance(trainer_options, dict):
            for key, value in trainer_options.items():
                if key in DEFAULT_TRAINER_OPTIONS:
                    merged[key] = value
        else:
            merged.update(trainer_options.model_dump(exclude_unset=True))
        recon["trainer_options"] = TrainerOptionsSchema.normalize_raw(merged).model_dump()

    if learn_goals is not None:
        raw = learn_goals if isinstance(learn_goals, dict) else learn_goals.model_dump(exclude_unset=True)
        normalized = LearnGoalsSchema.normalize_raw(raw).model_dump()
        cards = normalized.get("cards") or {}
        has_cards = any(cards.get(k) for k in ("merk", "mental", "input"))
        if not normalized.get("quiz") and not has_cards and not normalized.get("deadline"):
            recon.pop("learn_goals", None)
        else:
            recon["learn_goals"] = normalized

    if record:
        dec_title = decrypt_text_master(unit.title_encrypted)
        dec_brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""
        record.title_encrypted = encrypt_text_master(dec_title)
        record.summary_encrypted = encrypt_text_master(dec_brief or dec_title)
        record.subject = unit.subject
        record.language = unit.language
        record.difficulty = unit.difficulty
        recon = reconstruction_payload(
            title=dec_title,
            brief=dec_brief,
            subject=unit.subject,
            language=unit.language,
            target_age=unit.target_age,
            difficulty=unit.difficulty,
            task_type=unit.task_type,
            math_focus=focus,
            trainer_options=recon.get("trainer_options") if unit.task_type == "interactive" else None,
            learn_goals=recon.get("learn_goals") if unit.task_type == "interactive" else None,
        )
        record.reconstruction_encrypted = encrypt_json(recon)

    db.flush()
    return _dec_unit(unit)


def delete_unit(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    purge_history: bool = False,
) -> None:
    """Löscht Inhalt + Dateien. Standard: Verlauf bleibt; optional komplett mit Prüfungen."""
    from sqlalchemy.orm import joinedload

    from app.services.exam_service import _purge_exam_file

    unit = _get_unit_or_404(db, user, unit_id)
    records = (
        db.query(LearningRecord)
        .options(joinedload(LearningRecord.exam_results))
        .filter(LearningRecord.unit_id == unit.id)
        .all()
    )
    if purge_history:
        for record in records:
            for exam in list(record.exam_results or []):
                _purge_exam_file(exam)
            db.delete(record)
    else:
        for record in records:
            _add_event(
                db,
                record,
                "unit_deleted",
                {"title": decrypt_text_master(unit.title_encrypted), "kept": "history"},
            )
            record.unit_id = None
    db.flush()

    for source in list(unit.sources):
        _purge_source_file(source)

    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.delete",
        resource_type="learning_unit",
        resource_id=unit.id,
        detail="content_and_history_purged" if purge_history else "content_purged_history_kept",
    )
    db.delete(unit)


def list_records(db: Session, user: User) -> list[dict]:
    from sqlalchemy import or_

    q = db.query(LearningRecord).filter(LearningRecord.tenant_id == user.tenant_id)
    if not user.is_admin:
        child_ids = child_user_ids(db, user)
        ids = {user.id, *child_ids}
        from app.services.profile_service import accessible_profile_ids

        profile_ids = accessible_profile_ids(db, user)
        clauses = [LearningRecord.user_id.in_(ids)]
        if profile_ids:
            clauses.append(LearningRecord.profile_id.in_(profile_ids))
        q = q.filter(or_(*clauses))
    from sqlalchemy.orm import joinedload

    rows = (
        q.options(joinedload(LearningRecord.exam_results), joinedload(LearningRecord.profile))
        .order_by(LearningRecord.last_activity_at.desc())
        .all()
    )
    return [_dec_record(r) for r in rows]


def get_record(db: Session, user: User, record_id: uuid.UUID) -> dict:
    from sqlalchemy.orm import joinedload

    record = (
        db.query(LearningRecord)
        .options(joinedload(LearningRecord.exam_results), joinedload(LearningRecord.profile))
        .filter(LearningRecord.id == record_id)
        .first()
    )
    if not record or record.tenant_id != user.tenant_id:
        raise UnitError("Verlaufseintrag nicht gefunden", "not_found")
    if not user.is_admin and record.user_id != user.id:
        child_ids = child_user_ids(db, user)
        if record.user_id not in child_ids:
            from app.services.profile_service import can_view_profile_data

            if not record.profile_id or not can_view_profile_data(db, user, record.profile_id):
                raise UnitError("Kein Zugriff", "forbidden")
    data = _dec_record(record)
    from app.services.exam_service import _dec_exam

    data["exams"] = [_dec_exam(e) for e in record.exam_results]
    data["events"] = [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "payload": decrypt_json(e.payload_encrypted),
            "created_at": e.created_at.isoformat(),
        }
        for e in sorted(record.events, key=lambda x: x.created_at)
    ]
    return data


def upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def add_source(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> dict:
    from app.core.upload_validation import UploadValidationError, validate_upload_bytes

    unit = _get_unit_or_404(db, user, unit_id)
    try:
        detected = validate_upload_bytes(
            data,
            filename=filename,
            declared_content_type=content_type,
            allow_audio=True,
        )
    except UploadValidationError as exc:
        raise UnitError(str(exc), exc.code) from exc
    kind = detected.kind
    content_type = detected.content_type
    source = UnitSource(
        unit_id=unit.id,
        kind=kind,
        original_name_encrypted=encrypt_text_master(filename),
        content_type=content_type,
        byte_size=len(data),
    )
    db.add(source)
    db.flush()

    rel = f"{unit.id}/{source.id}"
    dest = upload_dir() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    source.storage_path = rel
    db.flush()

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if record:
        _add_event(db, record, "source_uploaded", {"kind": kind, "filename": filename})
    return _dec_source(source)


def add_source_url(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    url: str,
) -> dict:
    from urllib.parse import urlparse

    unit = _get_unit_or_404(db, user, unit_id)
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UnitError("Ungültige URL (nur http/https)", "bad_url")
    if len(cleaned) > 2048:
        raise UnitError("URL zu lang", "bad_url")

    source = UnitSource(
        unit_id=unit.id,
        kind="url",
        original_name_encrypted=encrypt_text_master(cleaned),
        content_type="text/html",
        byte_size=0,
    )
    db.add(source)
    db.flush()

    try:
        from app.ai.extract import fetch_url_text

        text = fetch_url_text(cleaned)
        source.extracted_text_encrypted = encrypt_text_master(text)
        db.flush()
    except Exception:
        pass

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if record:
        _add_event(db, record, "source_url_added", {"url": cleaned[:200]})
    return _dec_source(source)


def delete_source(db: Session, user: User, unit_id: uuid.UUID, source_id: uuid.UUID) -> None:
    unit = _get_unit_or_404(db, user, unit_id)
    source = db.get(UnitSource, source_id)
    if not source or source.unit_id != unit.id:
        raise UnitError("Quelle nicht gefunden", "not_found")
    _purge_source_file(source)
    db.delete(source)


def purge_source_file_keep_meta(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    source_id: uuid.UUID,
) -> dict:
    """Datei weg, OCR/Metadaten bleiben."""
    unit = _get_unit_or_404(db, user, unit_id)
    source = db.get(UnitSource, source_id)
    if not source or source.unit_id != unit.id:
        raise UnitError("Quelle nicht gefunden", "not_found")
    _purge_source_file(source)
    db.flush()
    return _dec_source(source)


def maybe_auto_purge_after_extract(db: Session, unit: LearningUnit, source: UnitSource) -> None:
    if unit.auto_purge_sources and source.extracted_text_encrypted and source.storage_path:
        _purge_source_file(source)


def _purge_source_file(source: UnitSource) -> None:
    if source.storage_path:
        path = upload_dir() / source.storage_path
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
        source.storage_path = None
    if source.purged_at is None:
        source.purged_at = datetime.now(timezone.utc)


def _kind_from_content(filename: str, content_type: str | None) -> str:
    name = filename.lower()
    ctype = (content_type or "").lower()
    if ctype.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic")):
        return "image"
    if ctype == "application/pdf" or name.endswith(".pdf"):
        return "document"
    if ctype.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".ogg", ".webm")):
        return "audio"
    return "document"
