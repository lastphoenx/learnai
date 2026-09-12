"""Celery-Worker für später KI-Jobs (Kursgenerierung, OCR, TTS)."""

import os

from celery import Celery
from celery.signals import worker_ready

celery_app = Celery(
    "learnai",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    include=["app.tasks.generate", "app.tasks.batch_import", "app.tasks.batch_maintenance"],
)


@worker_ready.connect
def _reconcile_redis_batch_state_on_worker_start(**_kwargs) -> None:
    """Nach Worker-Neustart: hängende Redis-Status bereinigen."""
    import logging

    log = logging.getLogger(__name__)
    try:
        from app.services.batch_import_job import reconcile_all_active_batch_import_jobs
        from app.services.batch_import_maintenance import fail_running_batch_maintenance

        batches = reconcile_all_active_batch_import_jobs()
        maint = fail_running_batch_maintenance(
            reason="Wartung unterbrochen (Worker-Neustart) — bitte erneut starten",
        )
        if batches or maint:
            log.info("worker_ready reconciled batch_import=%s batch_maintenance=%s", batches, maint)
    except Exception:
        log.exception("worker_ready batch redis reconcile failed")


@celery_app.task(name="learnai.ping")
def ping() -> str:
    return "ok"
