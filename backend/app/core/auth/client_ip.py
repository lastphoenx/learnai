"""Client-IP hinter nginx → Next.js → API (nur vertrauenswürdige Proxy-Kette)."""

from __future__ import annotations

import ipaddress
import logging

from fastapi import Request

from app.config import settings

_log = logging.getLogger(__name__)

_parsed_trusted: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None


def _trusted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    global _parsed_trusted
    if _parsed_trusted is not None:
        return _parsed_trusted
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in settings.trusted_proxy_cidrs.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            if "/" not in item:
                addr = ipaddress.ip_address(item)
                nets.append(ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}", strict=False))
            else:
                nets.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            _log.warning("Ungültiger TRUSTED_PROXY_CIDRS-Eintrag ignoriert: %s", item)
    _parsed_trusted = nets
    return nets


def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _is_trusted_proxy(ip: str) -> bool:
    addr = _parse_ip(ip)
    if not addr:
        return False
    return any(addr in net for net in _trusted_networks())


def is_public_client_ip(ip: str | None) -> bool:
    """Öffentliche IP — geeignet für Sperren/Rate-Limits."""
    if not ip:
        return False
    addr = _parse_ip(ip)
    if not addr:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
    )


def _pick_from_forwarded(forwarded: str, *, public_only: bool = False) -> str | None:
    # Rechts nach links: erste IP, die kein vertrauenswürdiger Proxy ist (RFC 7239 / nginx-Standard).
    parts = [part.strip() for part in forwarded.split(",") if part.strip()]
    for candidate in reversed(parts):
        if not _parse_ip(candidate):
            continue
        if _is_trusted_proxy(candidate):
            continue
        if public_only and not is_public_client_ip(candidate):
            continue
        return candidate
    return None


def get_client_ip(request: Request) -> str | None:
    """
    Ermittelt die Client-IP für Brute-Force-Schutz.

    Hinter vertrauenswürdigem Proxy (nginx): X-Real-IP / X-Forwarded-For —
    auch private LAN-IPs (z.B. 192.168.x), damit nicht alle Nutzer dieselbe
    Proxy-IP teilen. Ohne Header: None (keine IP-Sperre).
    """
    peer = request.client.host if request.client else ""

    if peer and _is_trusted_proxy(peer):
        forwarded = (request.headers.get("x-forwarded-for") or "").strip()
        if forwarded:
            picked = _pick_from_forwarded(forwarded)
            if picked:
                return picked

        real = (request.headers.get("x-real-ip") or "").strip()
        if real and _parse_ip(real):
            return real

        _log.warning(
            "Vertrauenswürdiger Proxy %s ohne Client-IP in Headers — IP-Sperre übersprungen",
            peer,
        )
        return None

    if peer and _parse_ip(peer):
        return peer

    return None


def describe_client_ip(request: Request) -> dict[str, str | bool | None]:
    """Diagnose für Login-Tests: Peer, Header, ermittelte Client-IP."""
    peer = request.client.host if request.client else ""
    real = (request.headers.get("x-real-ip") or "").strip() or None
    forwarded = (request.headers.get("x-forwarded-for") or "").strip() or None
    client_ip = get_client_ip(request)
    return {
        "peer": peer or None,
        "peer_trusted_proxy": bool(peer and _is_trusted_proxy(peer)),
        "x_real_ip": real,
        "x_forwarded_for": forwarded,
        "client_ip": client_ip,
        "client_ip_blockable": is_public_client_ip(client_ip),
    }


def log_client_ip(request: Request, *, context: str, email: str | None = None) -> None:
    info = describe_client_ip(request)
    email_part = f" email={email}" if email else ""
    _log.info(
        "login_ip_debug context=%s%s peer=%s trusted_proxy=%s x_real_ip=%s "
        "x_forwarded_for=%s client_ip=%s blockable=%s",
        context,
        email_part,
        info["peer"],
        info["peer_trusted_proxy"],
        info["x_real_ip"],
        info["x_forwarded_for"],
        info["client_ip"],
        info["client_ip_blockable"],
    )
