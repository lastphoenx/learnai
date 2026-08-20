"""Hintergrund-Generierung (interaktiver Trainer — kein HTTP-Timeout)."""

from __future__ import annotations

import logging
import uuid

from app.ai.errors import LlmError
from app.core.db.session import SessionLocal
from app.models import User
from app.services.generate_job import make_progress_callback, set_generate_job
from app.services.unit_service import UnitError, _get_unit_or_404
from app.worker import celery_app

_log = logging.getLogger(__name__)


@celery_app.task(name="learnai.generate_unit", bind=True, max_retries=0)
def generate_unit_task(self, unit_id: str, user_id: str, provider: str | None = None) -> None:
    db = SessionLocal()
    progress = make_progress_callback(unit_id, user_id)
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            set_generate_job(
                unit_id,
                user_id=user_id,
                status="failed",
                stage="failed",
                error="Benutzer nicht gefunden",
            )
            return

        unit = _get_unit_or_404(db, user, uuid.UUID(unit_id))
        set_generate_job(unit_id, user_id=user_id, status="running", stage="extracting_sources")

        from app.ai.generate import generate_modules

        generate_modules(
            db,
            user,
            uuid.UUID(unit_id),
            provider=provider,
            progress=progress,
        )
        db.commit()
        progress("done", message="Lernblöcke wurden erstellt.")
        _log.info("generate_unit_task done unit_id=%s", unit_id)
    except UnitError as exc:
        db.rollback()
        progress("failed", error=exc.message)
        _log.warning("generate_unit_task unit_error unit_id=%s msg=%s", unit_id, exc.message)
    except LlmError as exc:
        db.rollback()
        progress("failed", error=exc.message)
        _log.warning("generate_unit_task llm_error unit_id=%s code=%s msg=%s", unit_id, exc.code, exc.message)
    except Exception as exc:
        db.rollback()
        progress("failed", error=str(exc) or "Unbekannter Fehler")
        _log.exception("generate_unit_task failed unit_id=%s", unit_id)
    finally:
        db.close()
