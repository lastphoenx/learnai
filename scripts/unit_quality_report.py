#!/usr/bin/env python3
"""Qualitätsreport für eine Lerneinheit per Referenz-Code (Admin).

Beispiele:
  python scripts/unit_quality_report.py 0001
  python scripts/unit_quality_report.py 0001.0001
  python scripts/unit_quality_report.py 0001.0001 --out report.md

Container:
  docker compose exec -T api python /opt/scripts/unit_quality_report.py 0001.0001
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.unit_quality_report_service import build_unit_quality_report_for_user  # noqa: E402
from app.services.unit_service import UnitError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="LearnAI Qualitätsreport per Referenz")
    parser.add_argument("ref", help="Familie 0001 oder Instanz 0001.0001")
    parser.add_argument("--tenant-id", help="Tenant-UUID (sonst erster Admin)")
    parser.add_argument("--out", "-o", help="Markdown-Datei (sonst stdout)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True))
        if args.tenant_id:
            import uuid

            q = q.filter(User.tenant_id == uuid.UUID(args.tenant_id))
        admin = q.order_by(User.created_at.asc()).first()
        if not admin:
            print("Kein Admin-Benutzer gefunden.", file=sys.stderr)
            return 1
        result = build_unit_quality_report_for_user(db, admin, args.ref)
        db.commit()
        report = result["report"]
        if args.out:
            Path(args.out).write_text(report, encoding="utf-8")
            print(f"Report geschrieben: {args.out}")
        else:
            print(report)
        return 0
    except UnitError as exc:
        db.rollback()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
