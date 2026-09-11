"""Batch-weite Wartungsaktionen (Practice, später weitere Fixes)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.ai.generate_interactive import backfill_basiswissen_for_unit
from app.models import User
from app.services.batch_import_registry import resolve_batch_job
from app.services.generate_job import _redis_client
from app.services.unit_service import UnitError

_log = logging.getLogger(__name__)

_MAINTENANCE_TTL_SEC = 86400


def _maintenance_key(batch_id: str) -> str:
    return f"batch_maintenance:{batch_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_batch_maintenance_status(batch_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    if not client:
        return None
    raw = client.get(_maintenance_key(batch_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _set_batch_maintenance(batch_id: str, payload: dict[str, Any]) -> None:
    client = _redis_client()
    if not client:
        return
    payload["updated_at"] = _now_iso()
    client.setex(_maintenance_key(batch_id), _MAINTENANCE_TTL_SEC, json.dumps(payload, ensure_ascii=False))


def unit_ids_from_batch_job(
    job: dict[str, Any],
    *,
    indices: list[int] | None = None,
    only_done: bool = True,
) -> list[tuple[int, str]]:
    units = job.get("units") if isinstance(job.get("units"), list) else []
    index_set = set(indices) if indices is not None else None
    out: list[tuple[int, str]] = []
    for index, row in enumerate(units):
        if not isinstance(row, dict):
            continue
        if index_set is not None and index not in index_set:
            continue
        if only_done and row.get("generate_status") != "done":
            continue
        uid = str(row.get("unit_id") or "").strip()
        if uid:
            out.append((index, uid))
    return out


def rederive_practice_for_batch(
    db: Session,
    user: User,
    batch_id: str,
    *,
    indices: list[int] | None = None,
    progress_cb: Any | None = None,
) -> dict[str, Any]:
    job = resolve_batch_job(batch_id)
    if not job:
        raise UnitError("Batch-Job nicht gefunden", "not_found")
    if str(job.get("user_id")) != str(user.id) and not user.is_admin:
        raise UnitError("Kein Zugriff auf diesen Batch-Job", "forbidden")

    targets = unit_ids_from_batch_job(job, indices=indices, only_done=True)
    if not targets:
        raise UnitError("Keine fertigen Einheiten mit unit_id im Batch", "nothing_to_do")

    results: list[dict[str, Any]] = []
    ok = 0
    total = len(targets)
    _log.info(
        "batch_rederive_practice batch_id=%s units=%d indices=%s",
        batch_id,
        total,
        indices,
    )
    for step, (index, raw_id) in enumerate(targets, start=1):
        row = (job.get("units") or [None])[index] if index < len(job.get("units") or []) else {}
        title = str((row or {}).get("title") or raw_id)[:120]
        ref = str((row or {}).get("reference_code") or "").strip()
        progress_msg = f"[{step}/{total}] Übungsaufgaben: {title}"
        _log.info(
            "batch_rederive_practice [%s/%s] start index=%s ref=%s unit_id=%s title=%s",
            step,
            total,
            index,
            ref or "—",
            raw_id,
            title,
        )
        if progress_cb:
            progress_cb(
                step=step,
                total=total,
                message=progress_msg,
            )
        try:
            unit_id = uuid.UUID(raw_id)
            result = backfill_basiswissen_for_unit(db, user, unit_id, force=True)
            db.commit()
            ok += 1
            _log.info(
                "batch_rederive_practice [%s/%s] done index=%s unit_id=%s "
                "updated_modules=%s skipped_modules=%s errors=%s",
                step,
                total,
                index,
                raw_id,
                result.get("updated_modules", 0),
                result.get("skipped_modules", 0),
                len(result.get("errors") or []),
            )
            results.append(
                {
                    "index": index,
                    "unit_id": raw_id,
                    "title": title,
                    "ok": True,
                    "updated_modules": result.get("updated_modules", 0),
                    "skipped_modules": result.get("skipped_modules", 0),
                    "errors": result.get("errors") or [],
                }
            )
        except Exception as exc:
            db.rollback()
            _log.exception("batch_rederive_practice failed unit_id=%s", raw_id)
            results.append(
                {
                    "index": index,
                    "unit_id": raw_id,
                    "title": title,
                    "ok": False,
                    "error": str(exc),
                }
            )

    return {
        "batch_id": batch_id,
        "action": "rederive_practice",
        "total": total,
        "ok": ok,
        "failed": total - ok,
        "results": results,
    }


def run_batch_rederive_practice(batch_id: str, user_id: str, indices: list[int] | None = None) -> None:
    from app.core.db.session import SessionLocal

    _set_batch_maintenance(
        batch_id,
        {
            "batch_id": batch_id,
            "action": "rederive_practice",
            "status": "running",
            "total": 0,
            "current": 0,
            "message": "Startet…",
            "results": [],
        },
    )
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            raise UnitError("Benutzer nicht gefunden", "not_found")

        job = resolve_batch_job(batch_id)
        if not job:
            raise UnitError("Batch-Job nicht gefunden", "not_found")
        targets = unit_ids_from_batch_job(job, indices=indices, only_done=True)

        def progress_cb(*, step: int, total: int, message: str) -> None:
            _set_batch_maintenance(
                batch_id,
                {
                    "batch_id": batch_id,
                    "action": "rederive_practice",
                    "status": "running",
                    "total": total,
                    "current": step,
                    "message": message,
                    "results": [],
                },
            )

        _set_batch_maintenance(
            batch_id,
            {
                "batch_id": batch_id,
                "action": "rederive_practice",
                "status": "running",
                "total": len(targets),
                "current": 0,
                "message": f"{len(targets)} Einheiten…",
                "results": [],
            },
        )
        summary = rederive_practice_for_batch(
            db,
            user,
            batch_id,
            indices=indices,
            progress_cb=progress_cb,
        )
        _log.info(
            "batch_rederive_practice finished batch_id=%s ok=%s/%s failed=%s",
            batch_id,
            summary["ok"],
            summary["total"],
            summary["failed"],
        )
        _set_batch_maintenance(
            batch_id,
            {
                **summary,
                "status": "done" if summary["failed"] == 0 else "partial",
                "message": f"Fertig: {summary['ok']}/{summary['total']} Einheiten",
            },
        )
    except Exception as exc:
        _log.exception("run_batch_rederive_practice batch_id=%s", batch_id)
        _set_batch_maintenance(
            batch_id,
            {
                "batch_id": batch_id,
                "action": "rederive_practice",
                "status": "failed",
                "message": str(exc),
                "error": str(exc),
            },
        )
    finally:
        db.close()
