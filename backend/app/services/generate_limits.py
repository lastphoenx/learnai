"""Concurrency- und Rate-Limits für KI-Generierung."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings
from app.services.generate_job import _redis_client
from app.services.unit_service import UnitError

_log = logging.getLogger(__name__)

_SLOT_TTL_SEC = 86400


def _user_active_key(user_id: str) -> str:
    return f"generate:active:user:{user_id}"


def _tenant_active_key(tenant_id: str) -> str:
    return f"generate:active:tenant:{tenant_id}"


def _rate_key(user_id: str) -> str:
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    return f"generate:rate:user:{user_id}:{hour}"


def acquire_generate_slot(*, user_id: str, tenant_id: str, unit_id: str) -> None:
    client = _redis_client()
    if not client:
        _log.warning("generate_limits redis unavailable — limits skipped")
        return

    user_key = _user_active_key(user_id)
    tenant_key = _tenant_active_key(tenant_id)
    if client.sismember(user_key, unit_id):
        return

    rate_key = _rate_key(user_id)
    started = client.incr(rate_key)
    if started == 1:
        client.expire(rate_key, 3600)
    if started > settings.generate_rate_limit_per_user_hour:
        client.decr(rate_key)
        raise UnitError(
            f"Stündliches Generierungs-Limit erreicht ({settings.generate_rate_limit_per_user_hour}/h)",
            "rate_limited",
        )

    if client.scard(user_key) >= settings.generate_max_active_per_user:
        client.decr(rate_key)
        raise UnitError(
            f"Maximal {settings.generate_max_active_per_user} parallele Generierungen pro Benutzer",
            "rate_limited",
        )
    if client.scard(tenant_key) >= settings.generate_max_active_per_tenant:
        client.decr(rate_key)
        raise UnitError(
            f"Maximal {settings.generate_max_active_per_tenant} parallele Generierungen im Mandanten",
            "rate_limited",
        )

    client.sadd(user_key, unit_id)
    client.expire(user_key, _SLOT_TTL_SEC)
    client.sadd(tenant_key, unit_id)
    client.expire(tenant_key, _SLOT_TTL_SEC)


def release_generate_slot(*, user_id: str, tenant_id: str, unit_id: str) -> None:
    client = _redis_client()
    if not client:
        return
    client.srem(_user_active_key(user_id), unit_id)
    client.srem(_tenant_active_key(tenant_id), unit_id)
