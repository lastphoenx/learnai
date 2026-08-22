#!/usr/bin/env python3
"""Login-E-Mail in Account-Settings nachtragen (bestehende Benutzer).

Container:
  docker compose exec -T api python /opt/scripts/backfill_login_email.py --email user@example.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.auth.passwords import hash_email  # noqa: E402
from app.core.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.user_service import assign_login_email  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Login-E-Mail einem Benutzer zuordnen (Hash-Check)")
    parser.add_argument("--email", required=True, help="Login-E-Mail des Benutzers")
    parser.add_argument("--user-id", help="Optional: nur diesen Benutzer (UUID)")
    args = parser.parse_args()

    email = args.email.strip()
    email_hash = hash_email(email)
    db = SessionLocal()
    try:
        q = db.query(User).filter(User.email_hash == email_hash)
        if args.user_id:
            q = q.filter(User.id == args.user_id)
        users = q.all()
        if not users:
            print("Kein Benutzer mit passendem E-Mail-Hash gefunden.", file=sys.stderr)
            return 1
        for user in users:
            assign_login_email(user, email)
            name = user.id
            print(f"OK: {name} ← {email}")
        db.commit()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
