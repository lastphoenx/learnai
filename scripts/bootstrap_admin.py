#!/usr/bin/env python3
"""Ersten Admin-Benutzer anlegen (Self-Host Bootstrap)."""

import argparse
import getpass
import sys
from pathlib import Path

# backend/ als Python-Pfad
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.db.session import SessionLocal
from app.services.user_service import AuthError, register_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Admin-Benutzer für LearnAI anlegen")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", default="")
    args = parser.parse_args()
    password = getpass.getpass("Passwort: ")
    password2 = getpass.getpass("Passwort wiederholen: ")
    if password != password2:
        print("Passwörter stimmen nicht überein.", file=sys.stderr)
        return 1
    if len(password) < 12:
        print("Passwort muss mindestens 12 Zeichen haben.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = register_user(
            db,
            email=args.email,
            password=password,
            display_name=args.display_name or args.email.split("@")[0],
            is_admin=True,
        )
        db.commit()
        print(f"Admin angelegt: {user.id}")
        return 0
    except AuthError as exc:
        db.rollback()
        print(f"Fehler: {exc.message}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
