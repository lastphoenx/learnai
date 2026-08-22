#!/usr/bin/env python3
"""Aktuelle Login-Sperren und Zähler in Redis anzeigen.

E-Mails liegen in der DB nur als email_hash (SHA256) — Klartext ist nicht nötig.
Container: docker compose exec -T api python /opt/scripts/list_login_blocks.py
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.auth.bruteforce import _client  # noqa: E402
from app.core.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.services.user_service import _account_display_name  # noqa: E402


@dataclass(frozen=True)
class UserRef:
    user_id: str
    display_name: str


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


def _users_by_email_hash() -> dict[str, UserRef]:
    db = SessionLocal()
    try:
        result: dict[str, UserRef] = {}
        for user in db.query(User).all():
            name = _account_display_name(user) or "(ohne Namen)"
            result[user.email_hash] = UserRef(str(user.id), name)
        return result
    finally:
        db.close()


def _scan_auth_keys(r, pattern: str) -> list[str]:
    return sorted(r.scan_iter(pattern))


def _print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _email_label(email_hash: str, users_by_hash: dict[str, UserRef]) -> str:
    ref = users_by_hash.get(email_hash)
    if ref:
        return f"{ref.display_name} (registriert, id {ref.user_id[:8]}…)"
    return f"unbekannte E-Mail (hash {email_hash[:12]}…)"


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

    users_by_hash = _users_by_email_hash()

    block_ips: list[tuple[str, str, int]] = []
    block_emails: list[tuple[str, str, int]] = []

    for key in _scan_auth_keys(r, "auth:block:ip:*"):
        ip = key.removeprefix("auth:block:ip:")
        reason = r.get(key) or "?"
        ttl = int(r.ttl(key))
        block_ips.append((ip, reason, ttl))

    for key in _scan_auth_keys(r, "auth:block:email:*"):
        email_hash = key.removeprefix("auth:block:email:")
        reason = r.get(key) or "?"
        ttl = int(r.ttl(key))
        block_emails.append((email_hash, reason, ttl))

    _print_section("Gesperrte IPs")
    if not block_ips:
        print("(keine)")
    else:
        for ip, reason, ttl in block_ips:
            print(f"  {ip:<40} Grund: {reason:<16} TTL: {_fmt_ttl(ttl)}")

    _print_section("Gesperrte E-Mails (Hash, Klartext nicht in DB)")
    if not block_emails:
        print("(keine)")
    else:
        for email_hash, reason, ttl in block_emails:
            label = _email_label(email_hash, users_by_hash)
            print(f"  {label}")
            print(f"    hash: {email_hash}")
            print(f"    Grund: {reason:<16} TTL: {_fmt_ttl(ttl)}")

    if args.verbose:
        fail_by_target: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
        for key in _scan_auth_keys(r, "auth:fail:*"):
            ttl = int(r.ttl(key))
            value = r.get(key) or "?"
            if key.startswith("auth:fail:ip:"):
                fail_by_target[key.removeprefix("auth:fail:ip:")].append(("login", value, ttl))
            elif key.startswith("auth:fail:email:"):
                email_hash = key.removeprefix("auth:fail:email:")
                fail_by_target[_email_label(email_hash, users_by_hash)].append(("email", value, ttl))
            elif key.startswith("auth:fail:2fa:"):
                fail_by_target[key.removeprefix("auth:fail:2fa:")].append(("2fa", value, ttl))

        _print_section("Aktive Fehlversuchs-Zähler (noch nicht gesperrt)")
        if not fail_by_target:
            print("(keine)")
        else:
            for target, entries in sorted(fail_by_target.items()):
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

    if block_ips or block_emails:
        _print_section("Entsperren (Beispiele)")
        for ip, _, _ in block_ips:
            print(f"  docker compose exec -T api python /opt/scripts/unlock_login.py --ip {ip}")
        for email_hash, _, _ in block_emails:
            print(
                f"  docker compose exec -T api python /opt/scripts/unlock_login.py "
                f"--email-hash {email_hash}"
            )
        print(
            "  Alternativ mit Login-E-Mail (Klartext eingeben, wird wie beim Login gehasht): "
            "--email user@example.com"
        )

    unknown_blocks = sum(1 for h, _, _ in block_emails if h not in users_by_hash)
    if unknown_blocks:
        print(
            f"\nHinweis: {unknown_blocks} E-Mail-Sperre(n) passen zu keinem registrierten Benutzer "
            "(Tippfehler beim Login oder nicht erlaubte Adresse)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
