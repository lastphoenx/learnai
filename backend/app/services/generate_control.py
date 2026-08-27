"""Start, Abbruch und Stale-Reset für KI-Generierung."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.models import User
from app.services.generate_job import (
    get_generate_job,
    iter_generate_jobs,
    job_is_active,
    job_is_stale,
    persist_last_generate,
    set_generate_job,
)
from app.services.generate_limits import acquire_generate_slot, release_generate_slot_for_unit

_log = logging.getLogger(__name__)

USER_CANCEL_MESSAGE = "Abgebrochen"
STALE_MESSAGE = "Kein Fortschritt — Job wurde zurückgesetzt. Du kannst erneut aufbereiten."


def _revoke_celery(task_id: str | None) -> None:
    if not task_id:
        return
    try:
        from app.worker import celery_app

        celery_app.control.revoke(str(task_id), terminate=True, signal="SIGTERM")
    except Exception:
        _log.warning("generate_revoke_failed task_id=%s", task_id, exc_info=True)


def abort_generate_job(
    unit_id: str,
    *,
    reason: str,
    db: Session | None = None,
    revoke: bool = True,
) -> dict | None:
    job = get_generate_job(unit_id)
    if not job_is_active(job) or job is None:
        return job
    user_id = str(job.get("user_id") or "")
    tenant_id = str(job.get("tenant_id") or "") or None
    task_id = job.get("celery_task_id")
    payload = set_generate_job(
        unit_id,
        user_id=user_id or "unknown",
        status="failed",
        stage="failed",
        error=reason,
        message=reason,
        job_id=job.get("job_id"),
    )
    if db is not None:
        persist_last_generate(db, unit_id)
    release_generate_slot_for_unit(
        unit_id=unit_id,
        user_id=user_id or None,
        tenant_id=tenant_id,
    )
    if revoke:
        _revoke_celery(str(task_id) if task_id else None)
    _log.warning("generate_aborted unit_id=%s reason=%s", unit_id, reason)
    return payload


def fail_stale_generate_job(db: Session, unit_id: str) -> dict | None:
    job = get_generate_job(unit_id)
    if not job_is_stale(job):
        return None
    return abort_generate_job(unit_id, reason=STALE_MESSAGE, db=db)


def fail_all_stale_generate_jobs(db: Session | None = None) -> list[str]:
    cleared: list[str] = []
    for unit_id, job in iter_generate_jobs():
        if not job_is_stale(job):
            continue
        abort_generate_job(unit_id, reason=STALE_MESSAGE, db=db)
        cleared.append(unit_id)
    return cleared


def start_generate_job(user: User, unit_id: str, provider: str | None = None) -> dict:
    fail_stale_generate_job(None, unit_id)
    existing = get_generate_job(unit_id)
    if job_is_active(existing) and existing is not None:
        return existing

    from app.tasks.generate import generate_unit_task

    acquire_generate_slot(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        unit_id=unit_id,
    )
    job_id = str(uuid.uuid4())
    set_generate_job(
        unit_id,
        user_id=str(user.id),
        status="queued",
        stage="queued",
        job_id=job_id,
        tenant_id=str(user.tenant_id),
    )
    result = generate_unit_task.delay(unit_id, str(user.id), provider)
    return set_generate_job(
        unit_id,
        user_id=str(user.id),
        celery_task_id=result.id,
        job_id=job_id,
        tenant_id=str(user.tenant_id),
    )
