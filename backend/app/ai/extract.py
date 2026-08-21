"""Text aus PDF, Audio und Webseiten extrahieren."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import httpx

from app.ai.errors import LlmError
from app.config import settings


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text + " ")

    def text(self) -> str:
        raw = "".join(self._chunks)
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", raw)).strip()


def extract_pdf_text(path: Path, *, max_pages: int = 20) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise LlmError("pypdf nicht installiert", "pdf_missing") from exc

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages[:max_pages]):
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(f"--- Seite {i + 1} ---\n{text}")
    combined = "\n\n".join(parts).strip()
    if len(combined) >= 40:
        return combined
    return _pdf_vision_fallback(path, max_pages=min(5, max_pages))


def _pdf_vision_fallback(path: Path, *, max_pages: int = 5) -> str:
    """Gescannte PDFs: erste Seiten als Bild an Vision-Modell."""
    try:
        import fitz  # pymupdf
    except ImportError:
        return "(PDF ohne Textschicht — für gescannte PDFs «pymupdf» installieren)"

    from app.ai.providers import describe_image

    doc = fitz.open(str(path))
    parts: list[str] = []
    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        data = pix.tobytes("png")
        described = describe_image(
            image_bytes=data,
            mime="image/png",
            prompt="Extrahiere allen sichtbaren Text und beschreibe Aufgaben aus dieser PDF-Seite.",
            provider="ollama",
            model=None,
        )
        parts.append(f"--- Seite {i + 1} ---\n{described['text']}")
    doc.close()
    return "\n\n".join(parts).strip() or "(PDF konnte nicht gelesen werden)"


STT_PROVIDERS = frozenset({"browser", "local", "openai", "anthropic"})


def _whisper_transcription_url() -> str | None:
    base = (settings.whisper_url or "").strip().rstrip("/")
    if not base:
        return None
    if base.endswith("/audio/transcriptions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/audio/transcriptions"
    return f"{base}/v1/audio/transcriptions"


def _default_server_stt_provider() -> str:
    if (settings.whisper_url or "").strip():
        return "local"
    return "openai"


def effective_stt_provider(prefs: dict | None) -> str:
    """Server-seitige Transkription (Audio-Uploads, API). Browser-STT fällt auf lokal/OpenAI zurück."""
    raw = str((prefs or {}).get("stt_provider") or "").strip().lower()
    if raw == "local":
        return "local"
    if raw == "openai":
        return "openai"
    if raw == "anthropic":
        raise LlmError(
            "Anthropic bietet keine Spracherkennung. Bitte Lokal, OpenAI oder Browser wählen.",
            "stt_unsupported",
        )
    return _default_server_stt_provider()


def _transcribe_whisper_local(path: Path, *, language: str) -> str:
    whisper_url = _whisper_transcription_url()
    if not whisper_url:
        raise LlmError(
            "Lokales Whisper nicht konfiguriert (WHISPER_URL fehlt)",
            "no_transcription",
        )
    headers: dict[str, str] = {}
    if settings.whisper_api_key:
        headers["Authorization"] = f"Bearer {settings.whisper_api_key}"
    with path.open("rb") as handle:
        response = httpx.post(
            whisper_url,
            headers=headers,
            files={"file": (path.name, handle, "application/octet-stream")},
            data={"model": "whisper-1", "language": language[:2]},
            timeout=300.0,
        )
    if response.status_code >= 400:
        raise LlmError(f"Whisper-Fehler: {response.text[:200]}", "whisper_error")
    payload = response.json()
    return str(payload.get("text") or "").strip()


def _transcribe_whisper_openai(path: Path, *, language: str) -> str:
    if not settings.openai_api_key:
        raise LlmError(
            "OpenAI API-Key fehlt für Spracherkennung",
            "no_transcription",
        )
    with path.open("rb") as handle:
        response = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            files={"file": (path.name, handle, "application/octet-stream")},
            data={"model": "whisper-1", "language": language[:2]},
            timeout=120.0,
        )
    if response.status_code >= 400:
        raise LlmError(f"Whisper-Fehler: {response.text[:200]}", "whisper_error")
    payload = response.json()
    return str(payload.get("text") or "").strip()


def transcribe_audio(path: Path, *, language: str = "de", provider: str | None = None) -> str:
    name = (provider or "").strip().lower() or _default_server_stt_provider()
    if name == "browser":
        raise LlmError("Browser-STT läuft nur im Frontend.", "stt_browser_only")
    if name == "anthropic":
        raise LlmError(
            "Anthropic bietet keine Spracherkennung. Bitte Lokal, OpenAI oder Browser wählen.",
            "stt_unsupported",
        )
    if name == "local":
        return _transcribe_whisper_local(path, language=language)
    if name == "openai":
        return _transcribe_whisper_openai(path, language=language)
    raise LlmError(f"Unbekannter STT-Provider: {name}", "bad_stt_provider")


def fetch_url_text(url: str, *, max_bytes: int = 2_000_000) -> str:
    from app.core.url_safety import validate_public_http_url

    safe_url = validate_public_http_url(url)
    max_redirects = 5
    current = safe_url

    with httpx.Client(follow_redirects=False, timeout=20.0) as client:
        for _ in range(max_redirects + 1):
            validate_public_http_url(current)
            response = client.get(
                current,
                headers={"User-Agent": "LearnAI/1.0 (educational fetch)"},
            )
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise LlmError("Ungültige Weiterleitung", "fetch_failed")
                current = httpx.URL(current).join(location).human_repr()
                continue
            break
        else:
            raise LlmError("Zu viele Weiterleitungen", "fetch_failed")

    if response.status_code >= 400:
        raise LlmError(f"URL nicht erreichbar ({response.status_code})", "fetch_failed")

    content_type = (response.headers.get("content-type") or "").lower()
    data = response.content[:max_bytes]
    final_url = str(response.url)

    if "pdf" in content_type or final_url.lower().endswith(".pdf"):
        tmp = Path(settings.upload_dir) / "_tmp" / f"url-{abs(hash(final_url))}.pdf"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            return extract_pdf_text(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    if "html" in content_type or "<html" in data[:500].lower():
        parser = _HTMLTextExtractor()
        parser.feed(response.text[:500_000])
        text = parser.text()
        if len(text) >= 40:
            return text
        raise LlmError("Webseite enthält zu wenig lesbaren Text", "empty_page")

    if content_type.startswith("text/"):
        return response.text[:100_000].strip()

    raise LlmError("URL-Inhaltstyp nicht unterstützt", "unsupported_type")
