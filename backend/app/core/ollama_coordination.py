"""Ollama-Laufzeitstatus und clusterweiter Inference-Lock (Redis, CT 135 + CT 136)."""

from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable

import httpx

from app.ai.errors import LlmError
from app.config import settings

_log = logging.getLogger(__name__)

_LOCK_KEY = "ollama:inference:lock"
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
end
return 0
"""

_ollama_wait_callback: contextvars.ContextVar[Callable[[str], None] | None] = contextvars.ContextVar(
    "ollama_wait_callback",
    default=None,
)
_ollama_lock_holder: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ollama_lock_holder",
    default=None,
)

_redis_client = None
_redis_unavailable = False


def _lock_redis_url() -> str:
    explicit = (settings.ollama_lock_redis_url or "").strip()
    if explicit:
        return explicit
    return settings.redis_url


def _redis_client_for_lock():
    global _redis_client, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.from_url(_lock_redis_url(), decode_responses=True)
            _redis_client.ping()
        except Exception as exc:
            _log.warning("ollama_lock redis unavailable: %s", exc)
            _redis_unavailable = True
            return None
    return _redis_client


def _ollama_root_url() -> str:
    return settings.ollama_url.rstrip("/")


def _ollama_model_key(name: str) -> str:
    raw = str(name or "").strip().lower()
    if ":" in raw:
        return raw.split(":", 1)[0]
    return raw


def _ollama_same_model(a: str, b: str) -> bool:
    ka, kb = _ollama_model_key(a), _ollama_model_key(b)
    return bool(ka and kb and (ka == kb or ka.startswith(kb) or kb.startswith(ka)))


def _fetch_ollama_ps(timeout: float = 3.0) -> list[dict[str, Any]]:
    root = _ollama_root_url()
    if not root:
        return []
    try:
        response = httpx.get(f"{root}/api/ps", timeout=timeout)
        response.raise_for_status()
        data = response.json()
        models = data.get("models") or []
        return [m for m in models if isinstance(m, dict)]
    except (httpx.HTTPError, ValueError, TypeError):
        return []


def ollama_runtime_status(wanted_model: str | None = None) -> dict[str, Any]:
    """Belegt Ollama ein anderes Modell? Für Job-UI und Wartemeldungen."""
    root = _ollama_root_url()
    if not root:
        return {
            "ok": False,
            "loaded": [],
            "other_loaded": [],
            "switching": False,
            "message": "Ollama ist nicht konfiguriert.",
        }
    loaded: list[str] = []
    for row in _fetch_ollama_ps():
        name = str(row.get("name") or row.get("model") or "").strip()
        if name:
            loaded.append(name)
    want = str(wanted_model or "").strip()
    others = [name for name in loaded if want and not _ollama_same_model(name, want)]
    switching = bool(others)
    lock_holder = current_lock_holder()
    if lock_holder and not holder_is_self(lock_holder):
        holder_label = _holder_label(lock_holder)
        msg = f"Ollama wird von {holder_label} genutzt — Ihre Anfrage wartet."
    elif not loaded:
        msg = f"Ollama ist frei — lädt bei Bedarf «{want}»." if want else "Ollama ist frei."
    elif switching:
        shown = ", ".join(f"«{name}»" for name in others[:3])
        msg = (
            f"Ollama hat derzeit {shown} geladen"
            + (f" — wechselt auf «{want}»" if want else "")
            + ". Modellwechsel kann 1–3 Minuten dauern."
        )
    else:
        msg = f"Ollama hat «{want}» bereits geladen." if want else f"Ollama hat «{loaded[0]}» im Speicher."
    return {
        "ok": True,
        "loaded": loaded,
        "other_loaded": others,
        "switching": switching,
        "lock_holder": lock_holder,
        "message": msg,
    }


def current_lock_holder() -> str | None:
    client = _redis_client_for_lock()
    if not client:
        return None
    try:
        value = client.get(_LOCK_KEY)
        return str(value).strip() if value else None
    except Exception:
        return None


def _holder_label(holder: str) -> str:
    raw = str(holder or "").strip()
    if raw.startswith("learnai:"):
        return "LearnAI"
    if raw.startswith("slitprojekthub:"):
        return "SlitProjektHub"
    return raw.split(":", 1)[0] if ":" in raw else raw or "einem anderen Dienst"


def holder_is_self(holder: str | None) -> bool:
    if not holder:
        return False
    prefix = f"{settings.ollama_lock_app_name}:"
    return str(holder).startswith(prefix)


def wait_message_for_model(model: str | None, *, lock_holder: str | None = None) -> str:
    holder = lock_holder if lock_holder is not None else current_lock_holder()
    runtime = ollama_runtime_status(model)
    if holder and not holder_is_self(holder):
        return f"Wartet auf Ollama ({_holder_label(holder)})… {runtime.get('message') or ''}".strip()
    if runtime.get("switching"):
        return str(runtime.get("message") or "Ollama wechselt das Modell — bitte warten…")
    return str(runtime.get("message") or "Wartet auf Ollama…")


@contextmanager
def ollama_lock_holder(holder: str):
    token = _ollama_lock_holder.set(holder)
    try:
        yield
    finally:
        _ollama_lock_holder.reset(token)


def resolve_lock_holder() -> str:
    explicit = _ollama_lock_holder.get()
    if explicit:
        return explicit
    return f"{settings.ollama_lock_app_name}:inference"


@contextmanager
def ollama_wait_callback(callback: Callable[[str], None] | None):
    token = _ollama_wait_callback.set(callback)
    try:
        yield
    finally:
        _ollama_wait_callback.reset(token)


@contextmanager
def ollama_inference_lock(holder: str, *, model: str | None = None):
    """Clusterweiter Mutex vor Ollama-HTTP-Calls. Heartbeat via Callback während Wartezeit."""
    if not settings.ollama_lock_enabled:
        yield
        return

    client = _redis_client_for_lock()
    if not client:
        yield
        return

    acquired = False
    deadline = time.monotonic() + max(30, int(settings.ollama_lock_wait_sec))
    wait_cb = _ollama_wait_callback.get()

    try:
        while time.monotonic() < deadline:
            try:
                if client.set(_LOCK_KEY, holder, nx=True, ex=int(settings.ollama_lock_ttl_sec)):
                    acquired = True
                    break
            except Exception as exc:
                _log.warning("ollama_lock acquire failed holder=%s err=%s", holder, exc)
                break
            current = client.get(_LOCK_KEY)
            msg = wait_message_for_model(model, lock_holder=current)
            if wait_cb:
                wait_cb(msg)
            time.sleep(float(settings.ollama_lock_poll_sec))

        if not acquired and settings.ollama_lock_required:
            raise LlmError(
                "Ollama ist durch einen anderen Dienst belegt — bitte in ein paar Minuten erneut versuchen.",
                "ollama_busy",
            )
        if acquired:
            _log.info("ollama_lock acquired holder=%s model=%s", holder, model or "-")
        yield
    finally:
        if acquired:
            try:
                client.eval(_RELEASE_SCRIPT, 1, _LOCK_KEY, holder)
                _log.info("ollama_lock released holder=%s", holder)
            except Exception:
                _log.warning("ollama_lock release failed holder=%s", holder, exc_info=True)


def enrich_active_job_with_ollama(job: dict[str, Any] | None, *, model: str | None = None) -> dict[str, Any] | None:
    """Hängt Ollama-Status an laufende Generate-Jobs (API-Poll)."""
    if not job or job.get("status") not in {"queued", "running"}:
        return job
    runtime = ollama_runtime_status(model)
    holder = runtime.get("lock_holder")
    out = dict(job)
    out["ollama"] = {
        "ok": runtime.get("ok"),
        "loaded": runtime.get("loaded") or [],
        "other_loaded": runtime.get("other_loaded") or [],
        "switching": bool(runtime.get("switching")),
        "lock_holder": holder,
        "message": runtime.get("message"),
    }
    if holder and not holder_is_self(str(holder)):
        out["message"] = wait_message_for_model(model, lock_holder=str(holder))
    elif runtime.get("switching") and not str(out.get("message") or "").strip():
        out["message"] = str(runtime.get("message") or "")
    return out
