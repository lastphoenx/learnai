"""Redis-Status für PDF-Batch-Import (Mehrere Lerneinheiten)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.generate_job import _redis_client

_JOB_TTL_SEC = 86400 * 2


def _persist(job: dict[str, Any]) -> None:
    if not job:
        return
    try:
        from app.services.batch_import_registry import persist_batch_manifest

        persist_batch_manifest(job)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("batch manifest persist failed batch_id=%s", job.get("batch_id"))


def _key(batch_id: str) -> str:
    return f"batch_import:{batch_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_batch_import_job(
    *,
    batch_id: str,
    user_id: str,
    tenant_id: str,
    total: int,
    pdf_path: str,
    units: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "batch_id": batch_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "status": "queued",
        "cancel_requested": False,
        "total": total,
        "current_index": 0,
        "progress_pct": 0,
        "pdf_path": pdf_path,
        "units": units,
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
        "error": None,
        "message": "In Warteschlange…",
    }
    client = _redis_client()
    if client:
        client.setex(_key(batch_id), _JOB_TTL_SEC, json.dumps(payload, ensure_ascii=False))
    _persist(payload)
    return payload


def get_batch_import_job(batch_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    if not client:
        return None
    raw = client.get(_key(batch_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def update_batch_import_job(batch_id: str, **fields: Any) -> dict[str, Any] | None:
    existing = get_batch_import_job(batch_id)
    if not existing:
        from app.services.batch_import_registry import load_batch_manifest

        existing = load_batch_manifest(batch_id) or {}
    if not existing:
        return None
    existing.update(fields)
    existing["updated_at"] = _now_iso()
    total = int(existing.get("total") or 1)
    done = sum(
        1
        for row in existing.get("units") or []
        if isinstance(row, dict) and row.get("generate_status") in {"done", "partial", "failed"}
    )
    if fields.get("progress_pct") is None and total > 0:
        existing["progress_pct"] = min(100, int(100 * done / total))
    client = _redis_client()
    if client:
        client.setex(_key(batch_id), _JOB_TTL_SEC, json.dumps(existing, ensure_ascii=False))
    _persist(existing)
    return existing


def set_batch_unit_row(batch_id: str, index: int, **fields: Any) -> dict[str, Any] | None:
    job = get_batch_import_job(batch_id)
    if not job:
        return None
    units = job.get("units")
    if not isinstance(units, list) or index < 0 or index >= len(units):
        return None
    row = dict(units[index]) if isinstance(units[index], dict) else {}
    row.update(fields)
    units[index] = row
    return update_batch_import_job(batch_id, units=units, current_index=index)


def request_batch_cancel(batch_id: str) -> dict[str, Any] | None:
    return update_batch_import_job(
        batch_id,
        cancel_requested=True,
        status="cancelling",
        message="Abbruch angefordert…",
    )


def batch_cancel_requested(batch_id: str) -> bool:
    job = get_batch_import_job(batch_id)
    return bool(job and job.get("cancel_requested"))


def batch_is_active(job: dict[str, Any] | None) -> bool:
    return bool(job and job.get("status") in {"queued", "running", "cancelling"})


_RESUMABLE_STATUSES = frozenset({"cancelled", "partial", "failed"})


def batch_has_pending_units(job: dict[str, Any] | None) -> bool:
    if not job:
        return False
    units = job.get("units") or []
    return any(
        isinstance(row, dict) and row.get("generate_status") != "done"
        for row in units
    )


def batch_can_resume(job: dict[str, Any] | None) -> bool:
    if not job or batch_is_active(job):
        return False
    if job.get("status") not in _RESUMABLE_STATUSES:
        return False
    return batch_has_pending_units(job)


def new_batch_id() -> str:
    return str(uuid.uuid4())
