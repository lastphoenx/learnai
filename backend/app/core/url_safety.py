"""SSRF-Schutz für HTTP(S)-Quellen."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.ai.errors import LlmError

_BLOCKED = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _ip_blocked(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        return True
    if addr.is_multicast:
        return True
    return any(addr in net for net in _BLOCKED)


def _hostname_blocked(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return True
    if host in {"localhost", "localhost.localdomain"}:
        return True
    if host.endswith(".local") or host.endswith(".internal"):
        return True
    try:
        if _ip_blocked(host):
            return True
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise LlmError(f"URL-Host nicht auflösbar: {host}", "bad_url") from exc
    if not infos:
        raise LlmError(f"URL-Host nicht auflösbar: {host}", "bad_url")
    for info in infos:
        ip = info[4][0]
        if _ip_blocked(ip):
            return True
    return False


def validate_public_http_url(url: str) -> str:
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LlmError("Ungültige URL (nur http/https)", "bad_url")
    if parsed.username or parsed.password:
        raise LlmError("URLs mit Anmeldedaten sind nicht erlaubt", "bad_url")
    if _hostname_blocked(parsed.hostname):
        raise LlmError("URL-Ziel im internen Netz ist nicht erlaubt", "bad_url")
    return cleaned
