"""Celery-Task für PDF-Batch-Import."""

from __future__ import annotations

import logging

from app.services.batch_import_service import run_batch_import
from app.worker import celery_app

_log = logging.getLogger(__name__)


@celery_app.task(name="learnai.batch_import", bind=True, max_retries=0)
def batch_import_task(self, batch_id: str, user_id: str) -> None:
    _log.info("batch_import_task start batch_id=%s", batch_id)
    run_batch_import(batch_id, user_id)
    _log.info("batch_import_task done batch_id=%s", batch_id)
