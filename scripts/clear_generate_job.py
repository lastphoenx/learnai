#!/usr/bin/env python3
"""Hängende oder laufende «Mit KI aufbereiten»-Jobs in Redis auflisten/abbrechen.

Container:
  docker compose exec -T api python /opt/scripts/clear_generate_job.py --list
  docker compose exec -T api python /opt/scripts/clear_generate_job.py --stale
  docker compose exec -T api python /opt/scripts/clear_generate_job.py --unit-id <UUID>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.db.session import SessionLocal  # noqa: E402
from app.services.generate_control import (  # noqa: E402
    STALE_MESSAGE,
    USER_CANCEL_MESSAGE,
    abort_generate_job,
    fail_all_stale_generate_jobs,
)
from app.services.generate_job import iter_generate_jobs, job_is_active, job_is_stale  # noqa: E402


def _print_job(unit_id: str, job: dict) -> None:
    status = job.get("status")
    stale = " stale" if job_is_stale(job) else ""
    print(
        f"{unit_id}  {status}{stale}  stage={job.get('stage') or '-'}  "
        f"updated={job.get('updated_at') or '-'}  {job.get('message') or ''}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LearnAI KI-Aufbereiten: Jobs listen oder abbrechen (Redis)",
    )
    parser.add_argument("--list", action="store_true", help="Alle Generate-Jobs anzeigen")
    parser.add_argument(
        "--stale",
        action="store_true",
        help="Nur hängende Jobs zurücksetzen (kein Fortschritt)",
    )
    parser.add_argument("--unit-id", help="Einen Job per Einheiten-UUID abbrechen")
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="Alle queued/running Jobs abbrechen (Notfall)",
    )
    args = parser.parse_args()

    if not args.list and not args.stale and not args.unit_id and not args.all_active:
        parser.error("Mindestens eine Option: --list, --stale, --unit-id oder --all-active")

    jobs = iter_generate_jobs()
    if args.list:
        if not jobs:
            print("Keine Generate-Jobs in Redis.")
        for unit_id, job in jobs:
            _print_job(unit_id, job)
        if not args.stale and not args.unit_id and not args.all_active:
            return 0

    db = SessionLocal()
    try:
        if args.stale:
            cleared = fail_all_stale_generate_jobs(db)
            db.commit()
            print(f"stale: {len(cleared)} Job(s) zurückgesetzt")
            for uid in cleared:
                print(f"  {uid}")
        if args.unit_id:
            payload = abort_generate_job(args.unit_id.strip(), reason=USER_CANCEL_MESSAGE, db=db)
            db.commit()
            if payload:
                print(f"abgebrochen: {args.unit_id.strip()} → {payload.get('status')}")
            else:
                print(f"kein aktiver Job: {args.unit_id.strip()}")
        if args.all_active:
            n = 0
            for unit_id, job in iter_generate_jobs():
                if not job_is_active(job):
                    continue
                abort_generate_job(unit_id, reason=USER_CANCEL_MESSAGE, db=db)
                n += 1
                print(f"  {unit_id}")
            db.commit()
            print(f"all-active: {n} Job(s) abgebrochen")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
