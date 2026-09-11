"""Entwurfs-Einheiten aus der DB mit fehlenden Batch-Zeilen verknüpfen."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.crypto import decrypt_text_master
from app.models import LearningRecord, LearningUnit, User
from app.services.batch_import_job import get_batch_import_job, update_batch_import_job
from app.services.batch_import_service import get_batch_import_status
from app.services.crypto_json import decrypt_json
from app.services.unit_service import UnitError


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _linked_unit_ids(units: list[Any]) -> set[uuid.UUID]:
    linked: set[uuid.UUID] = set()
    for row in units:
        if not isinstance(row, dict):
            continue
        raw = row.get("unit_id")
        if not raw:
            continue
        try:
            linked.add(uuid.UUID(str(raw)))
        except ValueError:
            continue
    return linked


def _find_draft_unit(
    db: Session,
    user: User,
    *,
    row: dict[str, Any],
    exclude: set[uuid.UUID],
    since: datetime | None,
) -> LearningUnit | None:
    title = str(row.get("title") or "").strip()
    posten = row.get("posten")
    posten_int = int(posten) if posten not in (None, "") else None

    query = (
        db.query(LearningUnit)
        .options(joinedload(LearningUnit.modules))
        .filter(
            LearningUnit.tenant_id == user.tenant_id,
            LearningUnit.created_by_id == user.id,
            LearningUnit.status == "draft",
            LearningUnit.task_type == "interactive",
        )
    )
    if since:
        query = query.filter(LearningUnit.created_at >= since)

    candidates: list[LearningUnit] = []
    for unit in query.all():
        if unit.id in exclude:
            continue
        if not unit.modules:
            continue
        unit_title = decrypt_text_master(unit.title_encrypted).strip()
        if title and unit_title != title:
            continue
        if posten_int is not None:
            record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
            recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}
            if not isinstance(recon, dict) or recon.get("posten") != posten_int:
                continue
        candidates.append(unit)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return max(candidates, key=lambda unit: (len(unit.modules or []), unit.created_at or datetime.min.replace(tzinfo=timezone.utc)))


def link_batch_import_drafts(db: Session, user: User, batch_id: str) -> dict[str, Any]:
    """Setzt unit_id auf fehlgeschlagenen Batch-Zeilen, wenn passende draft-Einheit existiert."""
    job = get_batch_import_status(db, user, batch_id)
    units = job.get("units") or []
    if not isinstance(units, list):
        raise UnitError("Batch ohne Einheiten", "invalid_state")

    started = _parse_iso(str(job.get("started_at") or ""))
    since = started - timedelta(hours=2) if started else None
    linked_ids = _linked_unit_ids(units)
    updated_units: list[dict[str, Any]] = []
    linked_rows: list[dict[str, Any]] = []

    for index, row in enumerate(units):
        if not isinstance(row, dict):
            updated_units.append(row)
            continue
        next_row = dict(row)
        if next_row.get("generate_status") != "failed" or next_row.get("unit_id"):
            updated_units.append(next_row)
            continue
        match = _find_draft_unit(db, user, row=next_row, exclude=linked_ids, since=since)
        if match:
            next_row["unit_id"] = str(match.id)
            linked_ids.add(match.id)
            linked_rows.append(
                {
                    "index": index,
                    "title": next_row.get("title"),
                    "posten": next_row.get("posten"),
                    "unit_id": str(match.id),
                }
            )
        updated_units.append(next_row)

    if not linked_rows:
        return {
            "batch_id": batch_id,
            "linked": 0,
            "rows": [],
            "job": job,
        }

    refreshed = update_batch_import_job(batch_id, units=updated_units)
    if not refreshed:
        raise UnitError("Batch-Job nicht gefunden", "not_found")
    return {
        "batch_id": batch_id,
        "linked": len(linked_rows),
        "rows": linked_rows,
        "job": refreshed,
    }
