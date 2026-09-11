#!/usr/bin/env python3
"""Übungsaufgaben (force-Basiswissen-Backfill) für eine oder mehrere Einheiten — ohne UI-Klickerei.

Beispiele:
  docker compose exec -T api python /opt/scripts/rederive_practice_units.py UNIT-UUID
  docker compose exec -T api python /opt/scripts/rederive_practice_units.py --batch BATCH-UUID
  docker compose exec -T api python /opt/scripts/rederive_practice_units.py u1 u2 u3
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.ai.generate_interactive import backfill_basiswissen_for_unit  # noqa: E402
from app.core.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.batch_import_job import get_batch_import_job  # noqa: E402


def _unit_ids_from_batch(batch_id: str) -> list[str]:
    job = get_batch_import_job(batch_id)
    if not job:
        raise SystemExit(f"Batch nicht gefunden: {batch_id}")
    ids: list[str] = []
    for row in job.get("units") or []:
        if not isinstance(row, dict):
            continue
        uid = str(row.get("unit_id") or "").strip()
        if uid and uid not in ids:
            ids.append(uid)
    if not ids:
        raise SystemExit(f"Batch {batch_id}: keine unit_id in den Zeilen")
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Practice-Aufgaben neu ableiten (force backfill)")
    parser.add_argument("unit_ids", nargs="*", help="Einheits-UUID(s)")
    parser.add_argument("--batch", help="Alle unit_id aus Batch-Job")
    parser.add_argument("--user-id", help="Owner-UUID (Default: Batch-user oder erster Admin)")
    args = parser.parse_args()

    unit_ids = list(args.unit_ids or [])
    if args.batch:
        unit_ids.extend(_unit_ids_from_batch(args.batch))
    unit_ids = [u for u in dict.fromkeys(unit_ids) if u]

    if not unit_ids:
        parser.error("Mindestens eine unit_id oder --batch angeben")

    db = SessionLocal()
    try:
        user: User | None = None
        if args.user_id:
            user = db.query(User).filter(User.id == uuid.UUID(args.user_id)).first()
        if not user and args.batch:
            job = get_batch_import_job(args.batch)
            if job and job.get("user_id"):
                user = db.query(User).filter(User.id == job["user_id"]).first()
        if not user:
            user = db.query(User).filter(User.is_admin.is_(True)).order_by(User.created_at).first()
        if not user:
            print("Kein Benutzer gefunden", file=sys.stderr)
            return 1

        ok = 0
        for raw_id in unit_ids:
            try:
                unit_id = uuid.UUID(raw_id)
            except ValueError:
                print(f"Ungültige UUID: {raw_id}", file=sys.stderr)
                continue
            print(f"=== {unit_id} ===")
            try:
                result = backfill_basiswissen_for_unit(db, user, unit_id, force=True)
                db.commit()
                print(
                    f"OK: {result.get('updated_modules', 0)} Module, "
                    f"{result.get('skipped_modules', 0)} übersprungen"
                )
                for err in result.get("errors") or []:
                    print(f"  WARN: {err}")
                ok += 1
            except Exception as exc:
                db.rollback()
                print(f"FEHLER: {exc}", file=sys.stderr)
        print(f"fertig: {ok}/{len(unit_ids)} Einheiten")
        return 0 if ok == len(unit_ids) else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
