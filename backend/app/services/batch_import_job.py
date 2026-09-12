"""Redis-Status für PDF-Batch-Import (Mehrere Lerneinheiten)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.services.generate_job import _parse_iso, _redis_client

_JOB_TTL_SEC = 86400 * 2
_ACTIVE_STATUSES = frozenset({"queued", "running", "cancelling"})


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
    return bool(job and job.get("status") in _ACTIVE_STATUSES)


def _unit_generate_statuses(job: dict[str, Any]) -> list[str]:
    units = job.get("units") if isinstance(job.get("units"), list) else []
    return [
        str(row.get("generate_status") or "pending")
        for row in units
        if isinstance(row, dict)
    ]


def infer_batch_terminal_status(job: dict[str, Any]) -> str | None:
    """Leitet einen End-Status aus den Zeilen ab — wenn nichts mehr läuft/wartet."""
    statuses = _unit_generate_statuses(job)
    if not statuses:
        return None
    if any(status in {"running", "pending", "repair_pending", "regen_pending"} for status in statuses):
        return None
    if all(status == "done" for status in statuses):
        return "done"
    failed = sum(1 for status in statuses if status == "failed")
    done = sum(1 for status in statuses if status == "done")
    if failed and done:
        return "partial"
    if failed:
        return "failed"
    return "done"


def batch_job_is_stale(job: dict[str, Any] | None, *, now: datetime | None = None) -> bool:
    if not batch_is_active(job) or job is None:
        return False
    stamp = _parse_iso(str(job.get("updated_at") or "") or None) or _parse_iso(
        str(job.get("started_at") or "") or None
    )
    if stamp is None:
        return True
    age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
    if job.get("status") == "queued":
        return age > 180
    return age > settings.generate_stale_after_sec


def _batch_terminal_message(status: str, job: dict[str, Any]) -> str:
    if status == "done":
        return "Batch-Import abgeschlossen"
    if status == "partial":
        failures = sum(1 for s in _unit_generate_statuses(job) if s == "failed")
        return f"Teilweise fertig ({failures} Fehler)"
    if status == "failed":
        return "Batch fehlgeschlagen"
    if status == "cancelled":
        return "Batch abgebrochen"
    return str(job.get("message") or status)


def reconcile_batch_import_job(batch_id: str) -> dict[str, Any] | None:
    """Redis/Manifest: aktiven Batch-Job bereinigen wenn alle Zeilen fertig oder hängen geblieben."""
    from app.services.batch_import_registry import load_batch_manifest

    job = get_batch_import_job(batch_id) or load_batch_manifest(batch_id)
    if not job:
        return None

    if batch_is_active(job):
        terminal = infer_batch_terminal_status(job)
        if terminal:
            return update_batch_import_job(
                batch_id,
                status=terminal,
                message=_batch_terminal_message(terminal, job),
                progress_pct=100 if terminal == "done" else job.get("progress_pct"),
                cancel_requested=False if terminal == "done" else job.get("cancel_requested"),
            )

        if batch_job_is_stale(job):
            units = job.get("units") if isinstance(job.get("units"), list) else []
            patched_units: list[Any] = []
            changed = False
            for row in units:
                if isinstance(row, dict) and row.get("generate_status") == "running":
                    patched_units.append(
                        {
                            **row,
                            "generate_status": "failed",
                            "error": "Generierung unterbrochen (Timeout oder Worker-Neustart)",
                        }
                    )
                    changed = True
                else:
                    patched_units.append(row)
            if changed:
                update_batch_import_job(batch_id, units=patched_units)
                job = get_batch_import_job(batch_id) or load_batch_manifest(batch_id) or job
            terminal = infer_batch_terminal_status(job) if isinstance(job, dict) else None
            if terminal:
                return update_batch_import_job(
                    batch_id,
                    status=terminal,
                    message=_batch_terminal_message(terminal, job),
                    progress_pct=100 if terminal == "done" else job.get("progress_pct"),
                )

    return get_batch_import_job(batch_id) or load_batch_manifest(batch_id)


def reconcile_all_active_batch_import_jobs() -> int:
    """Alle aktiven Batch-Jobs prüfen (Worker-Neustart / Recovery)."""
    client = _redis_client()
    if not client:
        return 0
    count = 0
    for key in client.scan_iter("batch_import:*"):
        batch_id = str(key).split(":", 1)[-1]
        before = get_batch_import_job(batch_id) or {}
        after = reconcile_batch_import_job(batch_id) or {}
        if before.get("status") != after.get("status"):
            count += 1
    return count


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
