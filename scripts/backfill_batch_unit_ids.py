#!/usr/bin/env python3
"""Fehlende unit_id in Batch-Redis aus draft-Einheiten in PostgreSQL nachziehen.

Pilot / alte Fehler vor Sprint 7a:
  docker compose exec -T api python /opt/scripts/backfill_batch_unit_ids.py BATCH-UUID
  docker compose exec -T api python /opt/scripts/backfill_batch_unit_ids.py BATCH-UUID --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.batch_import_draft_link import link_batch_import_drafts  # noqa: E402
from app.services.batch_import_job import get_batch_import_job  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-Fehlerzeilen mit DB-Entwürfen verknüpfen")
    parser.add_argument("batch_id", help="batch_job_id (UUID)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, Redis nicht schreiben")
    args = parser.parse_args()

    job = get_batch_import_job(args.batch_id)
    if not job:
        print(f"Batch nicht gefunden: {args.batch_id}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == job.get("user_id")).first()
        if not user:
            print("Batch-Benutzer nicht gefunden", file=sys.stderr)
            return 1

        if args.dry_run:
            from app.services.batch_import_draft_link import _find_draft_unit, _linked_unit_ids, _parse_iso
            from datetime import timedelta

            units = job.get("units") or []
            started = _parse_iso(str(job.get("started_at") or ""))
            since = started - timedelta(hours=2) if started else None
            linked = _linked_unit_ids(units)
            found = 0
            for index, row in enumerate(units):
                if not isinstance(row, dict):
                    continue
                if row.get("generate_status") != "failed" or row.get("unit_id"):
                    continue
                match = _find_draft_unit(db, user, row=row, exclude=linked, since=since)
                if match:
                    found += 1
                    print(f"Zeile {index + 1}: {row.get('title')} -> {match.id}")
                    linked.add(match.id)
                else:
                    print(f"Zeile {index + 1}: {row.get('title')} -> kein Entwurf")
            print(f"dry-run: {found} Verknüpfung(en) möglich")
            return 0

        result = link_batch_import_drafts(db, user, args.batch_id)
        for row in result["rows"]:
            print(f"Zeile {row['index'] + 1}: {row.get('title')} -> {row['unit_id']}")
        print(f"verknüpft: {result['linked']}")
        return 0 if result["linked"] >= 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
