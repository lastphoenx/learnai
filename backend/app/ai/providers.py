"""Chat- und Vision-Aufrufe: Ollama (lokal), OpenAI, Anthropic."""

from __future__ import annotations

import base64
import json
import logging
import re

import httpx

from app.ai.catalog import local_hints
from app.ai.errors import LlmError
from app.ai.model_registry import model_catalog
from app.ai.ollama_match import first_ollama_hint
from app.config import settings

_log = logging.getLogger(__name__)

_VALID_JSON_ESCAPES = frozenset('"\\/bfnrtu')


class LlmResult(dict):
    """provider, model, text"""


def configured_providers() -> dict:
    return {
        "llm_provider": settings.llm_provider,
        "openai": {"configured": bool(settings.openai_api_key)},
        "anthropic": {"configured": bool(settings.anthropic_api_key)},
        "ollama": {"url": settings.ollama_url, "configured": bool(settings.ollama_url)},
        "tts": {
            "provider": settings.tts_provider,
            "configured": settings.tts_provider == "openai" and bool(settings.openai_api_key),
        },
        "stt": {
            "browser": {"configured": True},
            "local": {"configured": bool((settings.whisper_url or "").strip())},
            "openai": {"configured": bool(settings.openai_api_key)},
            "anthropic": {"configured": False},
        },
    }


def ollama_status() -> dict:
    url = settings.ollama_url.rstrip("/")
    try:
        response = httpx.get(f"{url}/api/tags", timeout=8.0)
        response.raise_for_status()
        models = [m.get("name", "") for m in response.json().get("models", []) if m.get("name")]
        return {"ok": True, "url": url, "models": models}
    except Exception as exc:
        return {"ok": False, "url": url, "models": [], "error": str(exc)[:200]}


def provider_status() -> dict:
    data = configured_providers()
    ollama = ollama_status()
    data["ollama"] = {**data["ollama"], **ollama}
    from app.ai.catalog import catalog_with_resolved

    data["task_catalog"] = catalog_with_resolved(ollama.get("models") or [])
    data["models"] = model_catalog()
    return data


def resolve_provider(override: str | None = None) -> str:
    name = (override or settings.llm_provider or "ollama").strip().lower()
    if name not in {"ollama", "openai", "anthropic"}:
        raise LlmError(f"Unbekannter Provider: {name}", "bad_provider")
    return name


def complete(
    *,
    prompt: str,
    provider: str | None = None,
    system: str | None = None,
    model: str | None = None,
    num_predict: int | None = None,
    json_mode: bool = False,
) -> LlmResult:
    name = resolve_provider(provider)
    text = prompt.strip()
    if not text:
        raise LlmError("Leerer Prompt", "empty")
    if name == "ollama":
        return _ollama_chat(
            text, system=system, model=model, num_predict=num_predict, json_mode=json_mode
        )
    if name == "openai":
        return _openai_chat(text, system=system, model=model, max_tokens=num_predict)
    return _anthropic_chat(text, system=system, model=model, max_tokens=num_predict)


def describe_image(
    *,
    image_bytes: bytes,
    mime: str,
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
) -> LlmResult:
    name = resolve_provider(provider)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    media = mime if mime.startswith("image/") else "image/jpeg"
    if name == "ollama":
        return _ollama_vision(b64, prompt, model=model)
    if name == "openai":
        return _openai_vision(b64, media, prompt, model=model)
    return _anthropic_vision(b64, media, prompt, model=model)


def _repair_invalid_json_escapes(raw: str) -> str:
    """LLMs often emit LaTeX like \\( … \\) — invalid in strict JSON."""
    return re.sub(
        r"\\(.)",
        lambda m: m.group(0) if m.group(1) in _VALID_JSON_ESCAPES else m.group(1),
        raw,
    )


def _repair_trailing_commas(raw: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", raw)


def _loads_json_object(raw: str) -> dict | None:
    variants = [
        raw,
        _repair_invalid_json_escapes(raw),
        _repair_trailing_commas(raw),
        _repair_trailing_commas(_repair_invalid_json_escapes(raw)),
    ]
    seen: set[str] = set()
    for candidate in variants:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def parse_json_object(text: str) -> dict:
    raw = text.strip()
    data = _loads_json_object(raw)
    if data is not None:
        return data
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        data = _loads_json_object(raw[start : end + 1])
        if data is not None:
            return data
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        inner = fence.group(1).strip()
        if inner.startswith("{") or inner.startswith("["):
            data = _loads_json_object(inner)
            if data is not None:
                return data
            start = inner.find("{")
            end = inner.rfind("}")
            if start >= 0 and end > start:
                data = _loads_json_object(inner[start : end + 1])
                if data is not None:
                    return data
    compact = raw.replace("\n", " ")
    _log.warning(
        "parse_json_object fail chars=%d head=%s tail=%s",
        len(raw),
        compact[:160],
        compact[-120:] if len(compact) > 120 else compact,
    )
    raise LlmError("KI-Antwort war kein JSON", "bad_json")


def _ollama_chat_model(explicit: str | None = None) -> str:
    name = (explicit or settings.ollama_model or "").strip()
    if name:
        return name
    installed = ollama_status().get("models") or []
    return first_ollama_hint(local_hints("mixed"), installed)


def _ollama_chat(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    *,
    num_predict: int | None = None,
    json_mode: bool = False,
) -> LlmResult:
    model = _ollama_chat_model(model)
    if not model:
        raise LlmError(
            "Kein Ollama-Chat-Modell. OLLAMA_MODEL setzen oder qwen2.5:32b ollama pull.",
            "no_chat_model",
        )
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload: dict = {"model": model, "messages": messages, "stream": False}
    if json_mode:
        payload["format"] = "json"
    if num_predict:
        payload["options"] = {"num_predict": num_predict, "temperature": 0.35}
    _log.info(
        "ollama_chat start model=%s timeout_s=%d num_predict=%s json_mode=%s",
        model,
        settings.ollama_chat_timeout_sec,
        num_predict or "default",
        json_mode,
    )
    data = _ollama_post("/api/chat", payload, timeout=float(settings.ollama_chat_timeout_sec))
    text = (data.get("message") or {}).get("content") or ""
    _log.info(
        "ollama_chat done model=%s done_reason=%s eval_count=%s prompt_eval_count=%s chars=%d",
        model,
        data.get("done_reason") or "?",
        data.get("eval_count"),
        data.get("prompt_eval_count"),
        len(text),
    )
    if not text.strip():
        raise LlmError("Ollama lieferte keinen Text", "empty_response")
    return LlmResult(provider="ollama", model=model, text=text.strip())


def _ollama_vision_model(explicit: str | None = None) -> str:
    name = (explicit or settings.ollama_vision_model or "").strip()
    if name:
        return name
    installed = ollama_status().get("models") or []
    return first_ollama_hint(local_hints("vision"), installed)


def _ollama_vision(b64: str, prompt: str, model: str | None = None) -> LlmResult:
    model = _ollama_vision_model(model)
    if not model:
        raise LlmError(
            "Kein Ollama-Vision-Modell. OLLAMA_VISION_MODEL setzen oder qwen2.5vl:7b pullen.",
            "no_vision_model",
        )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [b64]}],
        "stream": False,
    }
    _log.info("ollama_vision start model=%s timeout_s=%d", model, settings.ollama_vision_timeout_sec)
    data = _ollama_post("/api/chat", payload, timeout=float(settings.ollama_vision_timeout_sec))
    text = (data.get("message") or {}).get("content") or ""
    _log.info(
        "ollama_vision done model=%s done_reason=%s eval_count=%s chars=%d",
        model,
        data.get("done_reason") or "?",
        data.get("eval_count"),
        len(text),
    )
    if not text.strip():
        raise LlmError("Ollama-Vision lieferte keinen Text", "empty_response")
    return LlmResult(provider="ollama", model=model, text=text.strip())


def _ollama_post(path: str, payload: dict, timeout: float | None = None) -> dict:
    if timeout is None:
        timeout = float(settings.ollama_chat_timeout_sec)
    model = str(payload.get("model") or "").strip() or None
    from app.core.ollama_coordination import ollama_inference_lock, resolve_lock_holder

    with ollama_inference_lock(resolve_lock_holder(), model=model):
        return _ollama_post_unlocked(path, payload, timeout=timeout)


def _ollama_post_unlocked(path: str, payload: dict, timeout: float | None = None) -> dict:
    if timeout is None:
        timeout = float(settings.ollama_chat_timeout_sec)
    url = settings.ollama_url.rstrip("/") + path
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.TimeoutException as exc:
        model = payload.get("model", "?")
        _log.warning("ollama_timeout path=%s model=%s timeout_s=%d", path, model, int(timeout))
        raise LlmError(
            f"Ollama Zeitüberschreitung nach {int(timeout)}s "
            f"(Modell {model}) — kleineres Vision-Modell oder OLLAMA_VISION_TIMEOUT_SEC erhöhen",
            "ollama_timeout",
        ) from exc
    except httpx.HTTPError as exc:
        raise LlmError(f"Ollama nicht erreichbar ({settings.ollama_url})", "ollama_down") from exc
    if response.status_code >= 400:
        body = (response.text or "")[:200]
        raise LlmError(f"Ollama Fehler ({response.status_code}): {body}", "provider")
    return response.json()


def _openai_chat(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    *,
    max_tokens: int | None = None,
) -> LlmResult:
    if not settings.openai_api_key:
        raise LlmError("OPENAI_API_KEY fehlt", "missing_key")
    model = (model or settings.openai_model).strip()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
    }
    if max_tokens:
        body["max_tokens"] = max_tokens
    data = _openai_post(body)
    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    if not text.strip():
        raise LlmError("OpenAI lieferte keinen Text", "empty_response")
    return LlmResult(provider="openai", model=model, text=text.strip())


def _openai_vision(b64: str, mime: str, prompt: str, model: str | None = None) -> LlmResult:
    if not settings.openai_api_key:
        raise LlmError("OPENAI_API_KEY fehlt", "missing_key")
    model = (model or settings.openai_model).strip()
    data = _openai_post(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            ],
            "temperature": 0.2,
        },
        timeout=180.0,
    )
    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    if not text.strip():
        raise LlmError("OpenAI-Vision lieferte keinen Text", "empty_response")
    return LlmResult(provider="openai", model=model, text=text.strip())


def _openai_post(payload: dict, timeout: float = 90.0) -> dict:
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise LlmError("OpenAI nicht erreichbar", "openai_down") from exc
    if response.status_code >= 400:
        raise LlmError(f"OpenAI Fehler ({response.status_code})", "provider")
    return response.json()


def _anthropic_chat(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    *,
    max_tokens: int | None = None,
) -> LlmResult:
    if not settings.anthropic_api_key:
        raise LlmError("ANTHROPIC_API_KEY fehlt", "missing_key")
    model = (model or settings.anthropic_model).strip()
    body: dict = {
        "model": model,
        "max_tokens": max_tokens or 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system
    data = _anthropic_post(body)
    text = _anthropic_text(data)
    return LlmResult(provider="anthropic", model=model, text=text)


def _anthropic_vision(b64: str, mime: str, prompt: str, model: str | None = None) -> LlmResult:
    if not settings.anthropic_api_key:
        raise LlmError("ANTHROPIC_API_KEY fehlt", "missing_key")
    model = (model or settings.anthropic_model).strip()
    data = _anthropic_post(
        {
            "model": model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        },
        timeout=180.0,
    )
    text = _anthropic_text(data)
    return LlmResult(provider="anthropic", model=model, text=text)


def _anthropic_text(data: dict) -> str:
    parts = data.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not text.strip():
        raise LlmError("Anthropic lieferte keinen Text", "empty_response")
    return text.strip()


def _anthropic_post(payload: dict, timeout: float = 90.0) -> dict:
    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise LlmError("Anthropic nicht erreichbar", "anthropic_down") from exc
    if response.status_code >= 400:
        raise LlmError(f"Anthropic Fehler ({response.status_code})", "provider")
    return response.json()
