#!/usr/bin/env python3
"""Login-Sperren in Redis aufheben (Brute-Force-Schutz)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.auth.bruteforce import (  # noqa: E402
    _client,
    _key_email_block,
    _key_email_fail,
    _key_ip_block,
    _key_ip_fail,
    _key_ip_rate,
)
from app.core.auth.passwords import hash_email  # noqa: E402


def _delete_keys(r, keys: list[str]) -> int:
    existing = [k for k in keys if r.exists(k)]
    if not existing:
        return 0
    return int(r.delete(*existing))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LearnAI Login-Sperren aufheben (Redis auth:* Keys)",
    )
    parser.add_argument(
        "--email",
        help="E-Mail-Adresse entsperren (Fehlversuche oder unbekannte E-Mail)",
    )
    parser.add_argument("--ip", help="Client-IP entsperren (Rate-Limit / Fehlversuche)")
    parser.add_argument(
        "--flush-auth",
        action="store_true",
        help="Alle auth:* Keys löschen (nur Notfall, betrifft alle Nutzer kurzzeitig)",
    )
    args = parser.parse_args()

    if not args.email and not args.ip and not args.flush_auth:
        parser.error("Mindestens eine Option angeben: --email, --ip oder --flush-auth")

    r = _client()
    if not r:
        print("Redis nicht erreichbar.", file=sys.stderr)
        return 1

    total = 0
    if args.flush_auth:
        keys = list(r.scan_iter("auth:*"))
        if keys:
            total += int(r.delete(*keys))
        print(f"flush-auth: {total} Key(s) gelöscht")
        return 0

    if args.email:
        email = args.email.strip()
        email_hash = hash_email(email)
        removed = _delete_keys(
            r,
            [
                _key_email_block(email_hash),
                _key_email_fail(email_hash),
            ],
        )
        total += removed
        print(f"E-Mail «{email}»: {removed} Key(s) gelöscht")

    if args.ip:
        ip = args.ip.strip()
        removed = _delete_keys(
            r,
            [
                _key_ip_block(ip),
                _key_ip_fail(ip),
                _key_ip_rate(ip),
                f"auth:fail:2fa:{ip}",
                f"auth:rate:2fa:{ip}",
            ],
        )
        total += removed
        print(f"IP «{ip}»: {removed} Key(s) gelöscht")

    if total == 0:
        print("Keine passenden Sperr-Keys gefunden (evtl. schon abgelaufen).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
