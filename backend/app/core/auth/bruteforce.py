"""Brute-Force-Schutz für Login/2FA (Redis)."""

from __future__ import annotations

import ipaddress
import logging

from fastapi import HTTPException, status

from app.config import settings
from app.core.auth.passwords import hash_email

_log = logging.getLogger(__name__)

# 10 Jahre — praktisch «für immer» für unbekannte E-Mails
_FOREVER_TTL = 10 * 365 * 24 * 3600

_redis = None
_redis_unavailable = False


def _client():
    global _redis, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis is None:
        try:
            import redis

            _redis = redis.from_url(settings.redis_url, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            _log.warning("Redis für Brute-Force-Schutz nicht erreichbar: %s", exc)
            _redis_unavailable = True
            return None
    return _redis


def _key_ip_block(ip: str) -> str:
    return f"auth:block:ip:{ip}"


def _key_email_block(email_hash: str) -> str:
    return f"auth:block:email:{email_hash}"


def _key_ip_fail(ip: str) -> str:
    return f"auth:fail:ip:{ip}"


def _key_email_fail(email_hash: str) -> str:
    return f"auth:fail:email:{email_hash}"


def _key_ip_rate(ip: str) -> str:
    return f"auth:rate:ip:{ip}"


def _generic_denied() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültige Anmeldedaten")


def _too_many() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Zu viele Anmeldeversuche. Bitte später erneut versuchen.",
    )


def _ip_ok(ip: str | None) -> bool:
    """Rate-Limits/Sperren pro Client-IP — nicht für reine Proxy-/Docker-Peers."""
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_loopback:
        return False
    return True


def assert_login_allowed(*, ip: str | None, email: str) -> None:
    """Vor dem Passwort-Check: Rate-Limit, IP-/E-Mail-Sperren."""
    r = _client()
    if not r:
        return

    email_hash = hash_email(email)
    if r.exists(_key_email_block(email_hash)):
        raise _generic_denied()

    if not _ip_ok(ip):
        return

    if r.exists(_key_ip_block(ip)):
        raise _too_many()

    window = max(settings.login_rate_limit_window_sec, 1)
    limit = max(settings.login_rate_limit_per_ip, 1)
    rate_key = _key_ip_rate(ip)
    count = r.incr(rate_key)
    if count == 1:
        r.expire(rate_key, window)
    if count > limit:
        raise _too_many()


def assert_2fa_allowed(*, ip: str | None) -> None:
    r = _client()
    if not r or not _ip_ok(ip):
        return
    if r.exists(_key_ip_block(ip)):
        raise _too_many()
    window = max(settings.login_rate_limit_window_sec, 1)
    limit = max(settings.login_2fa_rate_limit_per_ip, 1)
    rate_key = f"auth:rate:2fa:{ip}"
    count = r.incr(rate_key)
    if count == 1:
        r.expire(rate_key, window)
    if count > limit:
        raise _too_many()


def record_unknown_email(*, ip: str | None, email: str) -> None:
    """Unbekannte E-Mail (nicht vorerfasst): E-Mail dauerhaft; IP wenn Client-IP ermittelt."""
    r = _client()
    if not r:
        return
    email_hash = hash_email(email)
    ttl = settings.login_unknown_block_ttl_sec or _FOREVER_TTL
    r.set(_key_email_block(email_hash), "unknown", ex=ttl)
    if _ip_ok(ip):
        ip_ttl = settings.login_unknown_ip_block_ttl_sec or ttl
        r.set(_key_ip_block(ip), "unknown_email", ex=ip_ttl)
        _log.warning("Login blockiert: unbekannte E-Mail (ip=%s)", ip)
    else:
        _log.warning("Login blockiert: unbekannte E-Mail (ohne verlässliche Client-IP)")


def record_failed_login(*, ip: str | None, email: str) -> None:
    """Falsches Passwort für bekannten Benutzer."""
    r = _client()
    if not r:
        return
    email_hash = hash_email(email)
    window = max(settings.login_fail_window_sec, 60)
    email_max = max(settings.login_max_failures_per_email, 1)
    email_ttl = max(settings.login_email_block_ttl_sec, 60)

    email_count = r.incr(_key_email_fail(email_hash))
    if email_count == 1:
        r.expire(_key_email_fail(email_hash), window)
    if email_count >= email_max:
        r.set(_key_email_block(email_hash), "failures", ex=email_ttl)
        _log.warning("E-Mail nach Login-Fehlversuchen gesperrt (count=%s)", email_count)

    if not _ip_ok(ip):
        return

    ip_max = max(settings.login_max_failures_per_ip, 1)
    ip_ttl = max(settings.login_ip_block_ttl_sec, 60)
    ip_count = r.incr(_key_ip_fail(ip))
    if ip_count == 1:
        r.expire(_key_ip_fail(ip), window)
    if ip_count >= ip_max:
        r.set(_key_ip_block(ip), "failures", ex=ip_ttl)
        _log.warning("IP nach Login-Fehlversuchen gesperrt (ip=%s, count=%s)", ip, ip_count)


def record_failed_2fa(*, ip: str | None) -> None:
    r = _client()
    if not r or not _ip_ok(ip):
        return
    window = max(settings.login_fail_window_sec, 60)
    ip_max = max(settings.login_2fa_max_failures_per_ip, 1)
    ip_ttl = max(settings.login_ip_block_ttl_sec, 60)
    ip_count = r.incr(f"auth:fail:2fa:{ip}")
    if ip_count == 1:
        r.expire(f"auth:fail:2fa:{ip}", window)
    if ip_count >= ip_max:
        r.set(_key_ip_block(ip), "2fa_failures", ex=ip_ttl)
        _log.warning("IP nach 2FA-Fehlversuchen gesperrt (ip=%s)", ip)


def record_success(*, ip: str | None, email: str | None = None) -> None:
    r = _client()
    if not r:
        return
    keys: list[str] = []
    if _ip_ok(ip):
        keys.extend([_key_ip_fail(ip), f"auth:fail:2fa:{ip}", _key_ip_rate(ip), f"auth:rate:2fa:{ip}"])
    if email:
        keys.append(_key_email_fail(hash_email(email)))
    for key in keys:
        r.delete(key)
