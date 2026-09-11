"""Celery-Tasks für Batch-Wartung."""

from __future__ import annotations

import logging

from app.services.batch_import_maintenance import run_batch_rederive_practice
from app.worker import celery_app

_log = logging.getLogger(__name__)


@celery_app.task(name="learnai.batch_maintenance.rederive_practice", bind=True, max_retries=0)
def batch_rederive_practice_task(
    self,
    batch_id: str,
    user_id: str,
    indices: list[int] | None = None,
) -> None:
    _log.info("batch_rederive_practice start batch_id=%s", batch_id)
    run_batch_rederive_practice(batch_id, user_id, indices=indices)
    _log.info("batch_rederive_practice done batch_id=%s", batch_id)
