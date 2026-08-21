"""Hintergrund-Generierung (interaktiver Trainer — kein HTTP-Timeout)."""

from __future__ import annotations

import logging
import uuid

from app.ai.errors import LlmError
from app.core.db.session import SessionLocal
from app.models import User
from app.services.generate_job import get_generate_job, make_progress_callback, set_generate_job
from app.services.unit_service import UnitError, _get_unit_or_404
from app.worker import celery_app

_log = logging.getLogger(__name__)

_GENERIC_GENERATE_ERROR = "Generierung fehlgeschlagen. Bitte erneut versuchen."


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
        job = get_generate_job(unit_id) or {}
        details: list[str] = []
        if job.get("modules"):
            details.append(f"{job['modules']} Bereiche")
        if job.get("cards"):
            details.append(f"{job['cards']} Karten")
        if job.get("questions"):
            details.append(f"{job['questions']} Quizfragen")
        done_message = "Lernblöcke wurden erstellt."
        if details:
            done_message = f"{done_message} ({', '.join(details)})"
        progress("done", message=done_message)
        _log.info("generate_unit_task done unit_id=%s", unit_id)
    except UnitError as exc:
        db.rollback()
        progress("failed", error=exc.message)
        _log.warning("generate_unit_task unit_error unit_id=%s msg=%s", unit_id, exc.message)
    except LlmError as exc:
        db.rollback()
        try:
            unit = _get_unit_or_404(db, user, uuid.UUID(unit_id))
            module_count = len(unit.modules or [])
            if module_count >= 4:
                db.commit()
                progress(
                    "partial",
                    message=(
                        f"Entwurf gespeichert ({module_count} Bereiche). "
                        f"Validierung: {exc.message}"
                    ),
                    modules=module_count,
                )
                _log.warning(
                    "generate_unit_task salvaged unit_id=%s modules=%d validation=%s",
                    unit_id,
                    module_count,
                    exc.message,
                )
            else:
                progress("failed", error=exc.message)
                _log.warning(
                    "generate_unit_task llm_error unit_id=%s code=%s msg=%s",
                    unit_id,
                    exc.code,
                    exc.message,
                )
        except Exception:
            progress("failed", error=exc.message)
            _log.warning(
                "generate_unit_task llm_error unit_id=%s code=%s msg=%s",
                unit_id,
                exc.code,
                exc.message,
            )
    except Exception as exc:
        db.rollback()
        _log.exception("generate_unit_task failed unit_id=%s", unit_id)
        progress("failed", error=_GENERIC_GENERATE_ERROR)
    finally:
        db.close()
