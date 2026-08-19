"""Tests für Brute-Force-Hilfen."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth.bruteforce import assert_login_allowed, record_unknown_email


@pytest.fixture
def mock_redis():
    store: dict[str, int | str] = {}
    ttl: dict[str, int] = {}

    r = MagicMock()

    def exists(key):
        return key in store

    def incr(key):
        store[key] = int(store.get(key, 0)) + 1
        return store[key]

    def expire(key, seconds):
        ttl[key] = seconds

    def set_(key, value, ex=None):
        store[key] = value
        if ex:
            ttl[key] = ex

    r.exists.side_effect = exists
    r.incr.side_effect = incr
    r.expire.side_effect = expire
    r.set.side_effect = set_
    return r, store


def test_unknown_email_blocks(mock_redis):
    r, store = mock_redis
    with patch("app.core.auth.bruteforce._client", return_value=r):
        record_unknown_email(ip="1.2.3.4", email="nobody@example.com")
        assert any(k.startswith("auth:block:ip:") for k in store)
        assert any(k.startswith("auth:block:email:") for k in store)


def test_rate_limit(mock_redis):
    r, store = mock_redis
    with patch("app.core.auth.bruteforce._client", return_value=r):
        with patch("app.core.auth.bruteforce.settings") as s:
            s.login_rate_limit_per_ip = 2
            s.login_rate_limit_window_sec = 60
            assert_login_allowed(ip="203.0.113.10", email="a@b.c")
            assert_login_allowed(ip="203.0.113.10", email="a@b.c")
            with pytest.raises(HTTPException) as exc:
                assert_login_allowed(ip="203.0.113.10", email="a@b.c")
            assert exc.value.status_code == 429


def test_no_ip_skips_rate_limit(mock_redis):
    r, store = mock_redis
    with patch("app.core.auth.bruteforce._client", return_value=r):
        with patch("app.core.auth.bruteforce.settings") as s:
            s.login_rate_limit_per_ip = 1
            s.login_rate_limit_window_sec = 60
            for _ in range(5):
                assert_login_allowed(ip=None, email="unique@example.com")
