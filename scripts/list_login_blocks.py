#!/usr/bin/env python3
"""Aktuelle Login-Sperren und Zähler in Redis anzeigen.

Container: docker compose exec -T api python /opt/scripts/list_login_blocks.py
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.auth.bruteforce import _client  # noqa: E402
from app.core.auth.passwords import hash_email  # noqa: E402
from app.core.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def _fmt_ttl(ttl: int) -> str:
    if ttl < 0:
        return "kein Ablauf"
    if ttl == 0:
        return "läuft ab"
    if ttl >= 86400:
        days = ttl // 86400
        hours = (ttl % 86400) // 3600
        return f"{days}d {hours}h"
    if ttl >= 3600:
        return f"{ttl // 3600}h {(ttl % 3600) // 60}m"
    if ttl >= 60:
        return f"{ttl // 60}m {ttl % 60}s"
    return f"{ttl}s"


def _email_lookup() -> dict[str, str]:
    db = SessionLocal()
    try:
        users = db.query(User.email).all()
        return {hash_email(email): email for (email,) in users}
    finally:
        db.close()


def _scan_auth_keys(r, pattern: str) -> list[str]:
    return sorted(r.scan_iter(pattern))


def _print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    parser = argparse.ArgumentParser(description="LearnAI Login-Sperren in Redis auflisten")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Auch Fehlversuchs-Zähler und Rate-Limits anzeigen",
    )
    args = parser.parse_args()

    r = _client()
    if not r:
        print("Redis nicht erreichbar.", file=sys.stderr)
        return 1

    email_by_hash = _email_lookup()

    block_ips: list[tuple[str, str, int]] = []
    block_emails: list[tuple[str, str, str, int]] = []

    for key in _scan_auth_keys(r, "auth:block:ip:*"):
        ip = key.removeprefix("auth:block:ip:")
        reason = r.get(key) or "?"
        ttl = int(r.ttl(key))
        block_ips.append((ip, reason, ttl))

    for key in _scan_auth_keys(r, "auth:block:email:*"):
        email_hash = key.removeprefix("auth:block:email:")
        reason = r.get(key) or "?"
        ttl = int(r.ttl(key))
        email = email_by_hash.get(email_hash, "")
        block_emails.append((email_hash, email, reason, ttl))

    _print_section("Gesperrte IPs")
    if not block_ips:
        print("(keine)")
    else:
        for ip, reason, ttl in block_ips:
            print(f"  {ip:<40} Grund: {reason:<16} TTL: {_fmt_ttl(ttl)}")

    _print_section("Gesperrte E-Mails")
    if not block_emails:
        print("(keine)")
    else:
        for email_hash, email, reason, ttl in block_emails:
            label = email if email else f"(unbekannt, hash {email_hash[:12]}…)"
            print(f"  {label:<40} Grund: {reason:<16} TTL: {_fmt_ttl(ttl)}")

    if args.verbose:
        fail_by_ip: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for key in _scan_auth_keys(r, "auth:fail:*"):
            ttl = int(r.ttl(key))
            value = r.get(key) or "?"
            if key.startswith("auth:fail:ip:"):
                fail_by_ip[key.removeprefix("auth:fail:ip:")].append(("login", value, ttl))
            elif key.startswith("auth:fail:email:"):
                email_hash = key.removeprefix("auth:fail:email:")
                email = email_by_hash.get(email_hash, email_hash[:12] + "…")
                fail_by_ip[email].append(("email", value, ttl))
            elif key.startswith("auth:fail:2fa:"):
                fail_by_ip[key.removeprefix("auth:fail:2fa:")].append(("2fa", value, ttl))

        _print_section("Aktive Fehlversuchs-Zähler (noch nicht gesperrt)")
        if not fail_by_ip:
            print("(keine)")
        else:
            for target, entries in sorted(fail_by_ip.items()):
                for kind, value, ttl in entries:
                    print(f"  {target:<40} {kind}: {value}  TTL: {_fmt_ttl(ttl)}")

        rate_keys = _scan_auth_keys(r, "auth:rate:*")
        _print_section("Aktive Rate-Limits")
        if not rate_keys:
            print("(keine)")
        else:
            for key in rate_keys:
                target = key.removeprefix("auth:rate:")
                value = r.get(key) or "?"
                ttl = int(r.ttl(key))
                print(f"  {target:<40} Zähler: {value:<4} TTL: {_fmt_ttl(ttl)}")

    print()
    print(f"Zusammenfassung: {len(block_ips)} IP-Sperre(n), {len(block_emails)} E-Mail-Sperre(n)")
    unknown_blocks = sum(1 for _, email, _, _ in block_emails if not email)
    if unknown_blocks:
        print(
            f"Hinweis: {unknown_blocks} E-Mail-Sperre(n) passen zu keinem registrierten Benutzer "
            "(Tippfehler oder nicht erlaubte Adresse)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
