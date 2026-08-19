"""Lerneinheiten: lebendes Gefäss + Verlauf, der das Löschen überlebt."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.core.crypto.classification import DataClassification
from app.models import LearningEvent, LearningRecord, LearningUnit, UnitModule, UnitSource, User
from app.services.audit import log_event
from app.services.crypto_json import decrypt_json, encrypt_json


class UnitError(Exception):
    def __init__(self, message: str, code: str = "unit_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def reconstruction_payload(
    *,
    title: str,
    brief: str | None,
    subject: str | None,
    language: str,
    target_age: str | None,
    difficulty: int,
) -> dict:
    return {
        "title": title,
        "brief": brief or "",
        "subject": subject,
        "language": language,
        "target_age": target_age,
        "difficulty": difficulty,
    }


def _dec_unit(unit: LearningUnit, *, sources: bool = True, modules: bool = True) -> dict:
    data = {
        "id": str(unit.id),
        "title": decrypt_text_master(unit.title_encrypted),
        "brief": decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None,
        "subject": unit.subject,
        "language": unit.language,
        "target_age": unit.target_age,
        "difficulty": unit.difficulty,
        "status": unit.status,
        "auto_purge_sources": unit.auto_purge_sources,
        "created_at": unit.created_at.isoformat(),
        "updated_at": unit.updated_at.isoformat(),
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


def _dec_record(record: LearningRecord) -> dict:
    return {
        "id": str(record.id),
        "unit_id": str(record.unit_id) if record.unit_id else None,
        "unit_alive": record.unit_id is not None,
        "title": decrypt_text_master(record.title_encrypted),
        "summary": decrypt_text_master(record.summary_encrypted) if record.summary_encrypted else None,
        "subject": record.subject,
        "language": record.language,
        "difficulty": record.difficulty,
        "reconstruction": decrypt_json(record.reconstruction_encrypted),
        "stats": decrypt_json(record.stats_encrypted) or {},
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
    q = db.query(LearningUnit).filter(LearningUnit.tenant_id == user.tenant_id)
    if user.is_admin:
        return q
    return q.filter(
        (LearningUnit.created_by_id == user.id) | (LearningUnit.learner_id == user.id)
    )


def list_units(db: Session, user: User) -> list[dict]:
    units = _accessible_units(db, user).order_by(LearningUnit.created_at.desc()).all()
    return [_dec_unit(u, sources=False, modules=False) for u in units]


def get_unit(db: Session, user: User, unit_id: uuid.UUID) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    return _dec_unit(unit)


def _get_unit_or_404(db: Session, user: User, unit_id: uuid.UUID) -> LearningUnit:
    unit = db.get(LearningUnit, unit_id)
    if not unit or unit.tenant_id != user.tenant_id:
        raise UnitError("Lerneinheit nicht gefunden", "not_found")
    if not user.is_admin and unit.created_by_id != user.id and unit.learner_id != user.id:
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
    auto_purge_sources: bool = False,
) -> dict:
    if difficulty < 1 or difficulty > 5:
        raise UnitError("Schwierigkeit muss 1–5 sein", "invalid_difficulty")

    recon = reconstruction_payload(
        title=title,
        brief=brief,
        subject=subject,
        language=language,
        target_age=target_age,
        difficulty=difficulty,
    )
    unit = LearningUnit(
        tenant_id=user.tenant_id,
        created_by_id=user.id,
        learner_id=user.id,
        title_encrypted=encrypt_text_master(title),
        brief_encrypted=encrypt_text_master(brief) if brief else None,
        subject=subject,
        language=language,
        target_age=target_age,
        difficulty=difficulty,
        status="draft",
        auto_purge_sources=auto_purge_sources,
        classification=DataClassification.INTERNAL,
    )
    db.add(unit)
    db.flush()

    record = LearningRecord(
        tenant_id=user.tenant_id,
        user_id=user.id,
        unit_id=unit.id,
        title_encrypted=encrypt_text_master(title),
        summary_encrypted=encrypt_text_master(brief) if brief else encrypt_text_master(title),
        subject=subject,
        language=language,
        difficulty=difficulty,
        reconstruction_encrypted=encrypt_json(recon),
        stats_encrypted=encrypt_json({"modules_done": 0, "quizzes": 0, "exams": 0}),
    )
    db.add(record)
    db.flush()
    _add_event(db, record, "unit_created", {"title": title})
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="unit.create",
        resource_type="learning_unit",
        resource_id=unit.id,
    )
    return _dec_unit(unit)


def create_unit_from_record(
    db: Session,
    user: User,
    record_id: uuid.UUID,
    *,
    difficulty: int | None = None,
) -> dict:
    record = db.get(LearningRecord, record_id)
    if not record or record.tenant_id != user.tenant_id:
        raise UnitError("Verlaufseintrag nicht gefunden", "not_found")
    if not user.is_admin and record.user_id != user.id:
        raise UnitError("Kein Zugriff", "forbidden")
    recon = decrypt_json(record.reconstruction_encrypted) or {}
    new_difficulty = difficulty if difficulty is not None else int(recon.get("difficulty") or record.difficulty)
    return create_unit(
        db,
        user,
        title=str(recon.get("title") or decrypt_text_master(record.title_encrypted)),
        brief=recon.get("brief") or (decrypt_text_master(record.summary_encrypted) if record.summary_encrypted else None),
        subject=recon.get("subject") or record.subject,
        language=str(recon.get("language") or record.language),
        target_age=recon.get("target_age"),
        difficulty=new_difficulty,
    )


def update_unit_flags(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    auto_purge_sources: bool | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    if auto_purge_sources is not None:
        unit.auto_purge_sources = auto_purge_sources
    db.flush()
    return _dec_unit(unit)


def delete_unit(db: Session, user: User, unit_id: uuid.UUID) -> None:
    """Löscht Inhalt + Dateien. Verlauf und Ergebnisse bleiben."""
    unit = _get_unit_or_404(db, user, unit_id)
    records = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).all()
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
        detail="content_purged_history_kept",
    )
    db.delete(unit)


def list_records(db: Session, user: User) -> list[dict]:
    q = db.query(LearningRecord).filter(LearningRecord.tenant_id == user.tenant_id)
    if not user.is_admin:
        q = q.filter(LearningRecord.user_id == user.id)
    rows = q.order_by(LearningRecord.last_activity_at.desc()).all()
    return [_dec_record(r) for r in rows]


def get_record(db: Session, user: User, record_id: uuid.UUID) -> dict:
    record = db.get(LearningRecord, record_id)
    if not record or record.tenant_id != user.tenant_id:
        raise UnitError("Verlaufseintrag nicht gefunden", "not_found")
    if not user.is_admin and record.user_id != user.id:
        raise UnitError("Kein Zugriff", "forbidden")
    data = _dec_record(record)
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
    unit = _get_unit_or_404(db, user, unit_id)
    kind = _kind_from_content(filename, content_type)
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
