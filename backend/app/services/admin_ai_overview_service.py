"""Admin-Übersicht: KI-Konfiguration aller Lerneinheiten."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.core.crypto import decrypt_text_master
from app.models import LearningRecord, LearningUnit, User
from app.services.ai_run_snapshot import summarize_unit_ai_context
from app.services.unit_reference_service import ensure_unit_reference_codes
from app.services.unit_service import _accessible_units


def build_admin_ai_overview(db: Session, user: User) -> dict:
    units = (
        _accessible_units(db, user)
        .options(joinedload(LearningUnit.profile), joinedload(LearningUnit.sources))
        .order_by(LearningUnit.created_at.desc())
        .all()
    )
    unit_ids = [u.id for u in units]
    records_by_unit: dict = {}
    if unit_ids:
        for record in db.query(LearningRecord).filter(LearningRecord.unit_id.in_(unit_ids)).all():
            records_by_unit[record.unit_id] = record

    rows: list[dict] = []
    for unit in units:
        record = records_by_unit.get(unit.id)
        refs = ensure_unit_reference_codes(db, unit, record, persist=False)
        title = decrypt_text_master(unit.title_encrypted)
        learner = unit.profile.display_name if unit.profile else "—"
        ai = summarize_unit_ai_context(db, user, unit, record)
        last = ai.get("last_run") if isinstance(ai, dict) else None
        last_tasks = last.get("tasks") if isinstance(last, dict) else None
        rows.append(
            {
                "unit_id": str(unit.id),
                "reference_code": refs.get("reference_code"),
                "title": title,
                "learner": learner,
                "task_type": unit.task_type or "mixed",
                "status": unit.status,
                "source_count": len(unit.sources or []),
                "module_count": len(unit.modules or []),
                "current_ai": ai.get("current") if isinstance(ai, dict) else {},
                "last_ai_run": last,
                "last_ai_summary": _compact_tasks(last_tasks),
            }
        )
    return {"count": len(rows), "units": rows}


def _compact_tasks(tasks: dict | None) -> str | None:
    if not isinstance(tasks, dict) or not tasks:
        return None
    parts: list[str] = []
    for key in sorted(tasks.keys()):
        row = tasks.get(key)
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip()
        if not provider:
            continue
        model = str(row.get("model") or "(auto)")
        parts.append(f"{provider} {model}")
    return " · ".join(parts) if parts else None
