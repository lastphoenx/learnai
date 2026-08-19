"""Chat- und Vision-Aufrufe: Ollama (lokal), OpenAI, Anthropic."""

from __future__ import annotations

import base64
import json
import re

import httpx

from app.ai.catalog import catalog_public
from app.ai.errors import LlmError
from app.ai.model_registry import model_catalog
from app.config import settings

VISION_NAME_HINTS = (
    "llava",
    "vision",
    "bakllava",
    "moondream",
    "minicpm-v",
    "qwen2.5vl",
    "qwen2-vl",
    "llama3.2-vision",
)


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
    data["ollama"] = {**data["ollama"], **ollama_status()}
    data["task_catalog"] = catalog_public()
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
) -> LlmResult:
    name = resolve_provider(provider)
    text = prompt.strip()
    if not text:
        raise LlmError("Leerer Prompt", "empty")
    if name == "ollama":
        return _ollama_chat(text, system=system, model=model)
    if name == "openai":
        return _openai_chat(text, system=system, model=model)
    return _anthropic_chat(text, system=system, model=model)


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


def parse_json_object(text: str) -> dict:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(raw[start : end + 1])
        if isinstance(data, dict):
            return data
    raise LlmError("KI-Antwort war kein JSON", "bad_json")


def _ollama_chat(prompt: str, system: str | None = None, model: str | None = None) -> LlmResult:
    model = (model or settings.ollama_model).strip()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "stream": False}
    data = _ollama_post("/api/chat", payload)
    text = (data.get("message") or {}).get("content") or ""
    if not text.strip():
        raise LlmError("Ollama lieferte keinen Text", "empty_response")
    return LlmResult(provider="ollama", model=model, text=text.strip())


def _ollama_vision(b64: str, prompt: str, model: str | None = None) -> LlmResult:
    model = (model or "").strip() or _ollama_vision_model()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [b64]}],
        "stream": False,
    }
    data = _ollama_post("/api/chat", payload, timeout=180.0)
    text = (data.get("message") or {}).get("content") or ""
    if not text.strip():
        raise LlmError("Ollama-Vision lieferte keinen Text", "empty_response")
    return LlmResult(provider="ollama", model=model, text=text.strip())


def _ollama_vision_model() -> str:
    if settings.ollama_vision_model.strip():
        return settings.ollama_vision_model.strip()
    status = ollama_status()
    for name in status.get("models") or []:
        lower = name.lower()
        if any(hint in lower for hint in VISION_NAME_HINTS):
            return name
    raise LlmError(
        "Kein Ollama-Vision-Modell gefunden. OLLAMA_VISION_MODEL setzen oder ein llava/vision-Modell pullen.",
        "no_vision_model",
    )


def _ollama_post(path: str, payload: dict, timeout: float = 120.0) -> dict:
    url = settings.ollama_url.rstrip("/") + path
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        raise LlmError(f"Ollama nicht erreichbar ({settings.ollama_url})", "ollama_down") from exc
    if response.status_code >= 400:
        raise LlmError(f"Ollama Fehler ({response.status_code})", "provider")
    return response.json()


def _openai_chat(prompt: str, system: str | None = None, model: str | None = None) -> LlmResult:
    if not settings.openai_api_key:
        raise LlmError("OPENAI_API_KEY fehlt", "missing_key")
    model = (model or settings.openai_model).strip()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = _openai_post(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
        }
    )
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


def _anthropic_chat(prompt: str, system: str | None = None, model: str | None = None) -> LlmResult:
    if not settings.anthropic_api_key:
        raise LlmError("ANTHROPIC_API_KEY fehlt", "missing_key")
    model = (model or settings.anthropic_model).strip()
    body: dict = {
        "model": model,
        "max_tokens": 4096,
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
