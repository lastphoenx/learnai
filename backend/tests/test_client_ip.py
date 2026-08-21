"""Tests für Client-IP hinter Proxy."""

from unittest.mock import MagicMock

from app.core.auth.client_ip import get_client_ip, is_public_client_ip


def _request(*, peer: str, headers: dict[str, str] | None = None):
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = peer
    req.headers = headers or {}
    return req


def test_trusted_proxy_uses_x_real_ip():
    req = _request(peer="172.18.0.6", headers={"x-real-ip": "203.0.113.50"})
    assert get_client_ip(req) == "203.0.113.50"


def test_trusted_proxy_uses_forwarded_for():
    req = _request(
        peer="10.0.0.5",
        headers={"x-forwarded-for": "203.0.113.51, 10.0.0.5"},
    )
    assert get_client_ip(req) == "203.0.113.51"


def test_trusted_proxy_ignores_spoofed_left_xff():
    req = _request(
        peer="10.0.0.5",
        headers={"x-forwarded-for": "1.2.3.4, 203.0.113.51"},
    )
    assert get_client_ip(req) == "203.0.113.51"


def test_trusted_proxy_ignores_spoofed_x_real_ip():
    req = _request(peer="10.0.0.5", headers={"x-real-ip": "10.0.0.1", "x-forwarded-for": "203.0.113.52"})
    assert get_client_ip(req) == "203.0.113.52"


def test_trusted_proxy_without_client_ip_returns_none():
    req = _request(peer="172.18.0.6", headers={})
    assert get_client_ip(req) is None


def test_untrusted_peer_ignores_spoofed_headers():
    req = _request(peer="203.0.113.99", headers={"x-forwarded-for": "1.2.3.4"})
    assert get_client_ip(req) == "203.0.113.99"


def test_trusted_proxy_uses_private_lan_ip():
    req = _request(peer="10.0.0.1", headers={"x-real-ip": "192.168.1.50"})
    assert get_client_ip(req) == "192.168.1.50"


def test_private_ip_not_blockable():
    assert not is_public_client_ip("172.18.0.6")
    assert not is_public_client_ip("192.168.1.1")
    assert is_public_client_ip("203.0.113.1")
