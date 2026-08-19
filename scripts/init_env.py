#!/usr/bin/env python3
"""Interaktiv: .env anlegen, DB-Passwort per Prompt, Keys falls leer."""

from __future__ import annotations

import base64
import getpass
import re
import secrets
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"

_FORBIDDEN = set(" \t\n\r#'\"$\\")
_DEFAULT_PW = "change-me-strong-password"


def _set_key(text: str, key: str, value: str) -> str:
    line = f"{key}={value}"
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pat.search(text):
        return pat.sub(lambda _: line, text, count=1)
    return text.rstrip() + "\n" + line + "\n"


def _get(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}=(.*)$", text, re.M)
    return (m.group(1).strip() if m else "").strip("'\"")


def _prompt_db_password(current: str) -> str:
    if current and current != _DEFAULT_PW:
        reuse = input("POSTGRES_PASSWORD ist schon gesetzt. Behalten? [Y/n] ").strip().lower()
        if reuse in ("", "y", "yes", "j", "ja"):
            return current

    print("PostgreSQL-Passwort (min. 16 Zeichen). Leer + Enter = generieren.")
    pw = getpass.getpass("DB-Passwort: ")
    pw2 = getpass.getpass("DB-Passwort wiederholen: ")
    if pw != pw2:
        print("Passwörter stimmen nicht überein.", file=sys.stderr)
        sys.exit(1)
    if pw == "":
        pw = secrets.token_urlsafe(32)
        print("Passwort generiert. Einmalig anzeigen? Nur wenn du es woanders brauchst.")
        show = input("Passwort jetzt einmal ausgeben? [y/N] ").strip().lower()
        if show in ("y", "yes", "j", "ja"):
            print(pw)
        return pw
    if len(pw) < 16:
        print("Passwort muss mindestens 16 Zeichen haben.", file=sys.stderr)
        sys.exit(1)
    bad = _FORBIDDEN.intersection(pw)
    if bad:
        print(f"Ungeeignete Zeichen im Passwort: {''.join(sorted(bad))}", file=sys.stderr)
        print("Keine Leerzeichen, Quotes, #, $, Backslash.", file=sys.stderr)
        sys.exit(1)
    return pw


def main() -> int:
    if not EXAMPLE.is_file():
        print(f"Fehlt: {EXAMPLE}", file=sys.stderr)
        return 1
    if not ENV_PATH.is_file():
        ENV_PATH.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Angelegt: {ENV_PATH}")

    text = ENV_PATH.read_text(encoding="utf-8")
    pw = _prompt_db_password(_get(text, "POSTGRES_PASSWORD"))
    enc = urllib.parse.quote(pw, safe="")

    text = _set_key(text, "POSTGRES_DB", "learnai")
    text = _set_key(text, "POSTGRES_USER", "learnai")
    text = _set_key(text, "POSTGRES_PASSWORD", pw)
    text = _set_key(
        text,
        "DATABASE_URL",
        f"postgresql+psycopg://learnai:{enc}@db:5432/learnai",
    )

    if not _get(text, "ENCRYPTION_MASTER_KEY"):
        master = base64.b64encode(secrets.token_bytes(32)).decode()
        text = _set_key(text, "ENCRYPTION_MASTER_KEY", master)
        print("ENCRYPTION_MASTER_KEY erzeugt.")
    else:
        print("ENCRYPTION_MASTER_KEY unverändert.")

    if not _get(text, "SESSION_SECRET"):
        text = _set_key(text, "SESSION_SECRET", secrets.token_urlsafe(64))
        print("SESSION_SECRET erzeugt.")
    else:
        print("SESSION_SECRET unverändert.")

    prod = input("Produktions-Domain (z.B. app.example.com, leer = localhost)? ").strip()
    if prod:
        origin = prod if prod.startswith("http") else f"https://{prod}"
        text = _set_key(text, "CORS_ORIGINS", origin)
        text = _set_key(text, "COOKIE_SECURE", "true")
    else:
        text = _set_key(text, "CORS_ORIGINS", "http://localhost:3000")
        text = _set_key(text, "COOKIE_SECURE", "false")

    ENV_PATH.write_text(text, encoding="utf-8")
    ENV_PATH.chmod(0o600)
    print(f"Geschrieben: {ENV_PATH} (chmod 600)")
    print("DATABASE_URL: postgresql+psycopg://learnai:***@db:5432/learnai")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
