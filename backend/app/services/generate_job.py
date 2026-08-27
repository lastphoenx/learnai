"""Fortschritt langer KI-Generierungen (Redis, gerätübergreifend pollbar)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.ai.errors import LlmError
from app.config import settings

_log = logging.getLogger(__name__)

_JOB_TTL_SEC = 86400
_QUEUED_STALE_SEC = 180
_JOB_META_KEYS = ("job_id", "celery_task_id", "tenant_id")
_redis = None
_redis_unavailable = False

STAGE_MESSAGES: dict[str, str] = {
    "queued": "In Warteschlange…",
    "extracting_sources": "Quellen werden gelesen (OCR/Vision)…",
    "planning": "Gliederung wird erstellt…",
    "category": "Lernkarten und Quiz werden erzeugt…",
    "saving": "Lernblöcke werden gespeichert…",
    "done": "Fertig",
    "partial": "Entwurf gespeichert",
    "failed": "Fehlgeschlagen",
}


def _redis_client():
    global _redis, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis is None:
        try:
            import redis

            _redis = redis.from_url(settings.redis_url, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            _log.warning("generate_job redis unavailable: %s", exc)
            _redis_unavailable = True
            return None
    return _redis


def _key(unit_id: str) -> str:
    return f"unit_generate:{unit_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _estimate_progress(stage: str, extra: dict[str, Any]) -> int:
    if stage == "queued":
        return 1
    if stage == "extracting_sources":
        return 10
    if stage == "planning":
        return 20
    if stage == "category":
        index = int(extra.get("index") or 0)
        total = max(1, int(extra.get("total") or 6))
        return 20 + int(70 * index / total)
    if stage == "saving":
        return 95
    if stage == "done":
        return 100
    if stage == "partial":
        return 100
    return 0


def _parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_generate_job(unit_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    if not client:
        return None
    raw = client.get(_key(unit_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


_TERMINAL_STATUSES = frozenset({"done", "partial", "failed"})


def snapshot_last_generate(job: dict[str, Any] | None) -> dict[str, Any] | None:
    if not job or job.get("status") not in _TERMINAL_STATUSES:
        return None
    snapshot: dict[str, Any] = {
        "status": job["status"],
        "message": job.get("message"),
        "error": job.get("error"),
        "started_at": job.get("started_at"),
        "updated_at": job.get("updated_at"),
    }
    for key in ("modules", "cards", "questions"):
        if key in job:
            snapshot[key] = job[key]
    return snapshot


def persist_last_generate(db, unit_id: str) -> None:
    """Letzten Endstand in reconstruction speichern (überlebt Redis-TTL)."""
    snapshot = snapshot_last_generate(get_generate_job(unit_id))
    if not snapshot:
        return
    import uuid as _uuid

    from app.models import LearningRecord
    from app.services.crypto_json import decrypt_json, encrypt_json

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == _uuid.UUID(unit_id)).first()
    if not record:
        return
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}
    recon["last_generate"] = snapshot
    record.reconstruction_encrypted = encrypt_json(recon)


def last_generate_from_recon(recon: dict | None) -> dict[str, Any] | None:
    if not isinstance(recon, dict):
        return None
    return snapshot_last_generate(recon.get("last_generate") if isinstance(recon.get("last_generate"), dict) else None)


def set_generate_job(unit_id: str, *, user_id: str, **fields: Any) -> dict[str, Any]:
    existing = get_generate_job(unit_id) or {}
    stage = str(fields.get("stage") or existing.get("stage") or "queued")
    extra = {k: v for k, v in fields.items() if k not in {"status", "stage", "error", "user_id"}}
    message = str(fields.get("message") or STAGE_MESSAGES.get(stage, stage))
    progress_pct = fields.get("progress_pct")
    if progress_pct is None:
        progress_pct = _estimate_progress(stage, extra)

    if fields.get("status") == "queued":
        existing = {}
        started_at = _now_iso()
        job_id = str(fields.get("job_id") or uuid.uuid4())
    else:
        started_at = existing.get("started_at") or _now_iso()
        job_id = str(fields.get("job_id") or existing.get("job_id") or uuid.uuid4())

    payload: dict[str, Any] = {
        "unit_id": unit_id,
        "user_id": user_id,
        "status": fields.get("status") or existing.get("status") or "queued",
        "stage": stage,
        "message": message,
        "progress_pct": progress_pct,
        "error": fields.get("error"),
        "started_at": started_at,
        "updated_at": _now_iso(),
        "job_id": job_id,
    }
    for key in ("index", "total", "category", "modules", "cards", "questions", *_JOB_META_KEYS):
        if key == "job_id":
            continue
        if key in fields:
            payload[key] = fields[key]
        elif key in existing:
            payload[key] = existing[key]

    client = _redis_client()
    if client:
        client.setex(_key(unit_id), _JOB_TTL_SEC, json.dumps(payload, ensure_ascii=False))
    return payload


def clear_generate_job(unit_id: str) -> None:
    client = _redis_client()
    if client:
        client.delete(_key(unit_id))


def job_is_active(job: dict[str, Any] | None) -> bool:
    return bool(job and job.get("status") in {"queued", "running"})


def job_is_stale(job: dict[str, Any] | None, *, now: datetime | None = None) -> bool:
    if not job_is_active(job) or job is None:
        return False
    stamp = _parse_iso(str(job.get("updated_at") or "") or None) or _parse_iso(
        str(job.get("started_at") or "") or None
    )
    if stamp is None:
        return True
    age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
    if job.get("status") == "queued":
        return age > _QUEUED_STALE_SEC
    return age > settings.generate_stale_after_sec


def job_was_stopped(unit_id: str, job_id: str | None) -> bool:
    current = get_generate_job(unit_id) or {}
    current_id = current.get("job_id")
    if job_id and current_id and current_id != job_id:
        return True
    return current.get("status") == "failed"


def iter_generate_jobs() -> list[tuple[str, dict[str, Any]]]:
    client = _redis_client()
    if not client:
        return []
    found: list[tuple[str, dict[str, Any]]] = []
    for key in client.scan_iter("unit_generate:*"):
        unit_id = str(key).split(":", 1)[-1]
        job = get_generate_job(unit_id)
        if job:
            found.append((unit_id, job))
    return found


def make_progress_callback(unit_id: str, user_id: str, job_id: str | None = None):
    def report(stage: str, **extra: Any) -> None:
        current = get_generate_job(unit_id) or {}
        current_id = current.get("job_id")
        if job_id and current_id and current_id != job_id:
            raise LlmError("Generierung abgebrochen", "cancelled")
        terminal = stage in {"done", "partial", "failed"}
        if not terminal and current.get("status") == "failed":
            raise LlmError(str(current.get("error") or "Generierung abgebrochen"), "cancelled")

        status = "running"
        if stage == "done":
            status = "done"
        elif stage == "partial":
            status = "partial"
        elif stage == "failed":
            status = "failed"

        custom_message = extra.pop("message", None)
        if custom_message:
            message = str(custom_message)
        elif stage == "failed" and extra.get("error"):
            message = str(extra["error"])
        elif stage == "category":
            name = str(extra.get("category") or extra.get("name") or "").strip()
            index = extra.get("index")
            total = extra.get("total")
            if index and total:
                message = f"Kategorie {index}/{total}" + (f": {name}" if name else "…")
            else:
                message = STAGE_MESSAGES.get(stage, stage)
        else:
            message = STAGE_MESSAGES.get(stage, stage)

        set_generate_job(
            unit_id,
            user_id=user_id,
            status=status,
            stage=stage,
            message=message,
            job_id=job_id or current_id,
            **extra,
        )

    return report
