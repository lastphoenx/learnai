"""Einzelne Lerneinheit innerhalb eines Batch-Imports."""

from __future__ import annotations

import uuid

from pathlib import Path
from sqlalchemy.orm import Session

from app.ai.errors import LlmError
from app.core.trainer_presets import DEFAULT_PRESET_ID
from app.models import LearningUnit, User
from app.services.batch_import_service import _attach_pdf_pages, _compose_brief
from app.services.generate_job import make_progress_callback, persist_last_generate, set_generate_job
from app.services.generate_limits import acquire_generate_slot, release_generate_slot
from app.services.unit_service import UnitError, create_unit


class BatchImportUnitFailed(Exception):
    """Generierung fehlgeschlagen — unit_id für Entwurf/Retry bekannt."""

    def __init__(self, unit_id: uuid.UUID, exc: Exception):
        self.unit_id = unit_id
        self.exc = exc
        super().__init__(getattr(exc, "message", str(exc)))


def unit_exists_after_failure(db: Session, unit_id: uuid.UUID) -> bool:
    return (
        db.query(LearningUnit.id).filter(LearningUnit.id == unit_id).first() is not None
    )


def process_batch_import_unit(
    db: Session,
    user: User,
    *,
    pdf_path: Path,
    shared_brief: str,
    spec: dict,
    profile_id: uuid.UUID | None,
    payload: dict,
) -> uuid.UUID:
    task_type = str(payload.get("task_type") or "interactive").strip().lower()
    preset = str(spec.get("preset") or payload.get("default_preset") or DEFAULT_PRESET_ID).strip()
    brief = _compose_brief(
        shared=shared_brief,
        suffix=spec.get("brief_suffix"),
        title=str(spec["title"]),
    )
    created = create_unit(
        db,
        user,
        title=str(spec["title"]),
        brief=brief,
        subject=(str(payload.get("subject") or "").strip() or None),
        language=str(payload.get("language") or "de"),
        target_age=(str(payload.get("target_age") or "").strip() or None),
        difficulty=int(payload.get("difficulty") or 1),
        task_type=task_type,
        math_focus=(str(payload.get("math_focus") or "").strip() or None),
        profile_id=profile_id,
        trainer_preset=preset,
        posten=spec.get("posten"),
    )
    unit_id = uuid.UUID(str(created["id"]))
    _attach_pdf_pages(
        db,
        user,
        unit_id,
        pdf_path,
        page_from=int(spec["page_from"]),
        page_to=int(spec["page_to"]),
    )

    if task_type != "interactive":
        return unit_id

    acquire_generate_slot(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        unit_id=str(unit_id),
        skip_rate_limit=True,
    )
    job_id = str(uuid.uuid4())
    progress = make_progress_callback(str(unit_id), str(user.id), job_id=job_id)
    set_generate_job(str(unit_id), user_id=str(user.id), status="running", stage="extracting_sources", job_id=job_id)
    try:
        from app.ai.generate import generate_modules
        from app.core.ollama_coordination import ollama_lock_holder, ollama_wait_callback

        def _ollama_wait_message(message: str) -> None:
            progress("running", message=message)

        with ollama_wait_callback(_ollama_wait_message):
            with ollama_lock_holder(f"learnai:batch:{unit_id}"):
                generate_modules(db, user, unit_id, progress=progress)
        progress("done", message="Lernblöcke wurden erstellt.")
    except (UnitError, LlmError) as exc:
        progress("failed", error="Generierung fehlgeschlagen")
        raise BatchImportUnitFailed(unit_id, exc) from exc
    finally:
        persist_last_generate(db, str(unit_id))
        release_generate_slot(user_id=str(user.id), tenant_id=str(user.tenant_id), unit_id=str(unit_id))

    return unit_id


def process_batch_regen_unit(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
) -> None:
    """Bestehende Batch-Einheit neu generieren (Quellen bleiben, Module neu)."""
    acquire_generate_slot(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        unit_id=str(unit_id),
        skip_rate_limit=True,
    )
    job_id = str(uuid.uuid4())
    progress = make_progress_callback(str(unit_id), str(user.id), job_id=job_id)
    set_generate_job(str(unit_id), user_id=str(user.id), status="running", stage="extracting_sources", job_id=job_id)
    try:
        from app.ai.generate import generate_modules
        from app.core.ollama_coordination import ollama_lock_holder, ollama_wait_callback

        def _ollama_wait_message(message: str) -> None:
            progress("running", message=message)

        with ollama_wait_callback(_ollama_wait_message):
            with ollama_lock_holder(f"learnai:batch-regen:{unit_id}"):
                generate_modules(db, user, unit_id, progress=progress)
        progress("done", message="Lernblöcke wurden erstellt.")
    except (UnitError, LlmError) as exc:
        progress("failed", error="Generierung fehlgeschlagen")
        raise BatchImportUnitFailed(unit_id, exc) from exc
    finally:
        persist_last_generate(db, str(unit_id))
        release_generate_slot(user_id=str(user.id), tenant_id=str(user.tenant_id), unit_id=str(unit_id))


def process_batch_repair_unit(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    error_hint: str | None,
) -> None:
    acquire_generate_slot(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        unit_id=str(unit_id),
        skip_rate_limit=True,
    )
    job_id = str(uuid.uuid4())
    progress = make_progress_callback(str(unit_id), str(user.id), job_id=job_id)
    set_generate_job(str(unit_id), user_id=str(user.id), status="running", stage="repairing", job_id=job_id)
    try:
        from app.core.ollama_coordination import ollama_lock_holder, ollama_wait_callback
        from app.services.batch_import_repair import repair_interactive_unit

        def _ollama_wait_message(message: str) -> None:
            progress("running", message=message)

        with ollama_wait_callback(_ollama_wait_message):
            with ollama_lock_holder(f"learnai:batch-repair:{unit_id}"):
                progress("running", message="Reparatur läuft…")
                repair_interactive_unit(db, user, unit_id, error_hint=error_hint)
        progress("done", message="Reparatur abgeschlossen.")
    except (UnitError, LlmError) as exc:
        progress("failed", error=getattr(exc, "message", str(exc)))
        raise
    finally:
        persist_last_generate(db, str(unit_id))
        release_generate_slot(user_id=str(user.id), tenant_id=str(user.tenant_id), unit_id=str(unit_id))
