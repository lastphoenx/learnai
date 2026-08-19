"""Text-to-Speech – Standard: OpenAI (lokal optional später)."""

import httpx

from app.config import settings

LANG_VOICE = {
    "de": "nova",
    "en": "nova",
    "it": "nova",
    "fr": "nova",
}


class TtsError(Exception):
    def __init__(self, message: str, code: str = "tts_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def synthesize_openai(text: str, lang: str = "de") -> bytes:
    if settings.tts_provider != "openai":
        raise TtsError("TTS-Provider nicht konfiguriert", "disabled")
    if not settings.openai_api_key:
        raise TtsError("OPENAI_API_KEY fehlt", "missing_key")
    if not text.strip():
        raise TtsError("Kein Text", "empty")
    voice = LANG_VOICE.get(lang, "nova")
    response = httpx.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": "tts-1", "voice": voice, "input": text.strip()[:4096]},
        timeout=60.0,
    )
    if response.status_code >= 400:
        raise TtsError(f"OpenAI TTS Fehler ({response.status_code})", "provider")
    return response.content
