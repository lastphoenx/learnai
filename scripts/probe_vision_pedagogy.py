#!/usr/bin/env python3
"""Vision-Didaktik für eine Lerneinheit prüfen (Posten-Prototyp, z. B. Zeitstrahl).

Beispiele:
  docker compose exec -T api python /opt/scripts/probe_vision_pedagogy.py --ref 0010.0001
  docker compose exec -T api python /opt/scripts/probe_vision_pedagogy.py --unit-id UUID
  docker compose exec -T api python /opt/scripts/probe_vision_pedagogy.py --batch 3b6c2e13-... --posten 14
  docker compose exec -T api python /opt/scripts/probe_vision_pedagogy.py --ref 0010.0001 --refresh
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.db.session import SessionLocal  # noqa: E402
from app.core.crypto import decrypt_text_master  # noqa: E402
from app.models import User  # noqa: E402
from app.services.batch_import_registry import resolve_batch_job  # noqa: E402
from app.services.pedagogy_service import extract_unit_pedagogy, get_unit_pedagogy  # noqa: E402
from app.services.unit_reference_service import find_units_by_reference, UnitReferenceError  # noqa: E402
from app.services.unit_service import _get_unit_or_404  # noqa: E402
from app.core.timeline_diagram import summarize_timeline  # noqa: E402


def _resolve_unit_id(*, db, admin, ref: str | None, unit_id: str | None, batch_id: str | None, posten: int | None) -> uuid.UUID:
    if unit_id:
        return uuid.UUID(unit_id.strip())
    if batch_id and posten is not None:
        job = resolve_batch_job(batch_id.strip())
        if not job:
            raise SystemExit(f"Batch nicht gefunden: {batch_id}")
        for row in job.get("units") or []:
            if not isinstance(row, dict):
                continue
            if row.get("posten") == posten and row.get("unit_id"):
                return uuid.UUID(str(row["unit_id"]))
        raise SystemExit(f"Batch {batch_id}: kein unit_id für Posten {posten}")
    if ref:
        try:
            _family, _instance, matches = find_units_by_reference(db, admin.tenant_id, ref.strip())
        except UnitReferenceError as exc:
            raise SystemExit(str(exc)) from exc
        if not matches:
            raise SystemExit(f"Keine Einheit für Referenz {ref}")
        return matches[0][0].id
    raise SystemExit("Mindestens --ref, --unit-id oder --batch + --posten angeben")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vision-Didaktik-JSON für eine Einheit ausgeben")
    parser.add_argument("--ref", help="Referenz 0001.0001")
    parser.add_argument("--unit-id", help="Lerneinheits-UUID")
    parser.add_argument("--batch", help="Batch-UUID")
    parser.add_argument("--posten", type=int, help="Posten-Nummer im Batch")
    parser.add_argument("--refresh", action="store_true", help="Vision neu ausführen (Cache ignorieren)")
    parser.add_argument("--out", "-o", help="JSON in Datei schreiben")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).first()
        if not admin:
            print("Kein Admin-Benutzer.", file=sys.stderr)
            return 1
        unit_uuid = _resolve_unit_id(
            db=db,
            admin=admin,
            ref=args.ref,
            unit_id=args.unit_id,
            batch_id=args.batch,
            posten=args.posten,
        )
        if args.refresh:
            extract_unit_pedagogy(db, admin, unit_uuid)
            db.commit()
        payload = get_unit_pedagogy(db, admin, unit_uuid)
        unit_row = _get_unit_or_404(db, admin, unit_uuid)
        from app.services.unit_reference_service import ensure_unit_reference_codes
        from app.models import LearningRecord

        record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit_row.id).first()
        refs = ensure_unit_reference_codes(db, unit_row, record, persist=False) if record else {}
        profile = payload.get("profile") or {}
        summary = {
            "unit_id": str(unit_uuid),
            "title": decrypt_text_master(unit_row.title_encrypted),
            "reference_code": refs.get("reference_code"),
            "pedagogy_level": (payload.get("quality") or {}).get("level"),
            "key_terms": len(profile.get("key_terms") or []),
            "assignments": len(profile.get("assignments") or []),
            "visual_tasks": len(profile.get("visual_tasks") or []),
            "visual_tasks_with_placements": sum(
                1
                for task in profile.get("visual_tasks") or []
                if isinstance(task, dict) and task.get("placements")
            ),
        }
        timeline = summarize_timeline(profile)
        if timeline:
            summary["timeline"] = timeline
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("\n--- profile ---\n")
        body = json.dumps(profile, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).write_text(body, encoding="utf-8")
            print(f"Profil geschrieben: {args.out}")
        else:
            print(body)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
