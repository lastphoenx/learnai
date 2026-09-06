"""Verfügbare Modelle live von OpenAI/Anthropic laden — keine erfundenen IDs."""

from __future__ import annotations

import re
import time

import httpx

from app.config import settings

_CACHE_TTL_SEC = 300
_cache: dict = {"ts": 0.0, "data": {}}

OPENAI_TTS_IDS = frozenset({"tts-1", "tts-1-hd", "gpt-4o-mini-tts"})
OPENAI_CHAT_RE = re.compile(r"^(gpt-|o[134]-|chatgpt-)", re.I)
OPENAI_VISION_RE = re.compile(r"^(gpt-4|gpt-5|o\d-)", re.I)
OPENAI_NON_CHAT_HINTS = ("-tts", "whisper", "embedding", "dall-e", "moderation", "realtime", "transcribe", "audio")
ANTHROPIC_CHAT_RE = re.compile(r"^claude-", re.I)


def _is_openai_chat(model_id: str) -> bool:
    if model_id in OPENAI_TTS_IDS:
        return False
    if not OPENAI_CHAT_RE.match(model_id):
        return False
    lower = model_id.lower()
    return not any(part in lower for part in OPENAI_NON_CHAT_HINTS)


def _is_openai_vision(model_id: str) -> bool:
    return _is_openai_chat(model_id) and bool(OPENAI_VISION_RE.match(model_id))


def _fetch_openai() -> dict:
    if not settings.openai_api_key:
        return {
            "ok": False,
            "configured": False,
            "chat": [],
            "vision": [],
            "tts": list(OPENAI_TTS_IDS),
            "error": "OPENAI_API_KEY fehlt",
        }
    try:
        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=15.0,
        )
        response.raise_for_status()
        ids = sorted({row.get("id", "") for row in response.json().get("data", []) if row.get("id")})
        chat = sorted(m for m in ids if _is_openai_chat(m))
        vision = sorted(m for m in ids if _is_openai_vision(m))
        tts = sorted(m for m in ids if m in OPENAI_TTS_IDS)
        if not tts:
            tts = sorted(OPENAI_TTS_IDS)
        return {
            "ok": True,
            "configured": True,
            "chat": chat,
            "vision": vision or chat,
            "tts": tts,
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "chat": [],
            "vision": [],
            "tts": list(OPENAI_TTS_IDS),
            "error": str(exc)[:200],
        }


def _fetch_anthropic() -> dict:
    if not settings.anthropic_api_key:
        return {"ok": False, "configured": False, "chat": [], "vision": [], "error": "ANTHROPIC_API_KEY fehlt"}
    try:
        response = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        rows = response.json().get("data") or response.json().get("models") or []
        ids = sorted(
            {
                (row.get("id") or row.get("name") or "")
                for row in rows
                if (row.get("id") or row.get("name"))
            }
        )
        chat = sorted(m for m in ids if ANTHROPIC_CHAT_RE.match(m))
        return {
            "ok": True,
            "configured": True,
            "chat": chat,
            "vision": chat,
            "error": None,
        }
    except Exception as exc:
        return {"ok": False, "configured": True, "chat": [], "vision": [], "error": str(exc)[:200]}


def model_catalog(force: bool = False) -> dict:
    now = time.time()
    if not force and _cache["data"] and now - _cache["ts"] < _CACHE_TTL_SEC:
        return _cache["data"]
    openai = _fetch_openai()
    anthropic = _fetch_anthropic()
    data = {"openai": openai, "anthropic": anthropic}
    _cache["ts"] = now
    _cache["data"] = data
    return data


def allowed_models(provider: str, *, task_key: str = "mixed") -> list[str]:
    cat = model_catalog()
    name = provider.strip().lower()
    if name == "openai":
        o = cat["openai"]
        if task_key == "tts":
            return list(o.get("tts") or [])
        if task_key == "vision":
            return list(o.get("vision") or o.get("chat") or [])
        return list(o.get("chat") or [])
    if name == "anthropic":
        a = cat["anthropic"]
        return list(a.get("chat") or a.get("vision") or [])
    return []


def validate_model(provider: str, model: str, *, task_key: str = "mixed") -> str:
    """Leer = Server-Default. Sonst muss Modell in der Live-Liste stehen."""
    cleaned = (model or "").strip()
    if not cleaned:
        return ""
    name = (provider or "").strip().lower()
    if name not in {"openai", "anthropic", "ollama"}:
        raise ValueError(f"Unbekannter Provider: {provider}")
    if name == "ollama":
        return cleaned[:80]
    allowed = allowed_models(name, task_key=task_key)
    if not allowed:
        cat = model_catalog()
        block = cat.get(name) or {}
        err = block.get("error") or "Provider nicht erreichbar"
        raise ValueError(f"Keine Modell-Liste für {name}: {err}")
    if cleaned not in allowed:
        raise ValueError(f"Modell «{cleaned}» ist bei {name} nicht verfügbar")
    return cleaned


def pick_external_model(provider: str, hints: list[str], *, task_key: str = "mixed") -> str:
    models = pick_external_models(provider, hints, task_key=task_key, limit=1)
    return models[0] if models else ""


def pick_external_models(
    provider: str,
    hints: list[str],
    *,
    task_key: str = "mixed",
    limit: int = 3,
) -> list[str]:
    available = allowed_models(provider, task_key=task_key)
    if not available:
        return []
    lower = [m.lower() for m in available]
    picked: list[str] = []
    used: set[str] = set()
    for hint in hints:
        if len(picked) >= limit:
            break
        token = hint.split(":")[0].lower() if ":" not in hint else hint.lower()
        for idx, mid in enumerate(lower):
            name = available[idx]
            if name in used:
                continue
            if mid == hint.lower() or (":" in hint and mid == hint.lower()) or mid.startswith(token):
                picked.append(name)
                used.add(name)
                break
    for name in available:
        if len(picked) >= limit:
            break
        if name not in used:
            picked.append(name)
            used.add(name)
    return picked[:limit]
