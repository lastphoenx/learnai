#!/usr/bin/env python3
"""Quiz-Antworten an Referenz-Slot reparieren (z. B. 0036.02.07).

Beispiele:
  python scripts/repair_quiz_by_reference.py 0036.02.07 --show
  python scripts/repair_quiz_by_reference.py 0036.02.07 --apply
  python scripts/repair_quiz_by_reference.py 0036 --apply-all

Container:
  docker compose exec -T api python /opt/scripts/repair_quiz_by_reference.py 0036.02.07 --apply
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
from app.models import User  # noqa: E402
from app.services.quiz_repair_service import (  # noqa: E402
    repair_all_quizzes_in_family,
    repair_quiz_slot_for_reference,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Quiz-Reparatur per Referenz-Slot")
    parser.add_argument("ref", help="0036.02.07 oder Familie 0036 mit --apply-all")
    parser.add_argument("--show", action="store_true", help="Nur anzeigen (dry-run)")
    parser.add_argument("--apply", action="store_true", help="Änderungen in DB speichern")
    parser.add_argument(
        "--apply-all",
        action="store_true",
        help="Ganze Familie: alle Quiz-Fragen reparieren (nur mit Familien-Ref 0036)",
    )
    parser.add_argument("--tenant-id", help="Tenant-UUID (sonst erster Admin)")
    args = parser.parse_args()

    if not args.show and not args.apply and not args.apply_all:
        args.show = True

    dry_run = not args.apply and not args.apply_all

    db = SessionLocal()
    try:
        q = db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True))
        if args.tenant_id:
            q = q.filter(User.tenant_id == uuid.UUID(args.tenant_id))
        admin = q.order_by(User.created_at.asc()).first()
        if not admin:
            print("Kein Admin-Benutzer gefunden.", file=sys.stderr)
            return 1

        if args.apply_all:
            n = repair_all_quizzes_in_family(db, admin, args.ref, dry_run=dry_run)
            if dry_run:
                print(f"Dry-run: {n} Modul-Quiz würden geändert.")
            else:
                db.commit()
                print(f"Gespeichert: {n} Modul-Quiz repariert.")
            return 0

        rows = repair_quiz_slot_for_reference(db, admin, args.ref, dry_run=dry_run)
        if not rows:
            print(f"Kein Treffer für {args.ref}.", file=sys.stderr)
            return 2

        for row in rows:
            print(f"=== {row.get('reference_code')} unit={row.get('unit_id')} slot={row.get('slot')} ===")
            print("Vorher:", json.dumps(row.get("before"), ensure_ascii=False, indent=2))
            print("Nachher:", json.dumps(row.get("after"), ensure_ascii=False, indent=2))
            print(f"Geändert: {row.get('changed')}")
            print()

        if args.apply:
            db.commit()
            print("Änderungen gespeichert.")
        else:
            print("Dry-run — zum Speichern: --apply")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
