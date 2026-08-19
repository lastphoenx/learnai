"""Text aus PDF, Audio und Webseiten extrahieren."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

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


def transcribe_audio(path: Path, *, language: str = "de") -> str:
    if not settings.openai_api_key:
        raise LlmError("OpenAI API-Key fehlt für Audio-Transkription", "no_openai")
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


def fetch_url_text(url: str, *, max_bytes: int = 2_000_000) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LlmError("Ungültige URL (nur http/https)", "bad_url")

    response = httpx.get(
        url.strip(),
        follow_redirects=True,
        timeout=20.0,
        headers={"User-Agent": "LearnAI/1.0 (educational fetch)"},
    )
    if response.status_code >= 400:
        raise LlmError(f"URL nicht erreichbar ({response.status_code})", "fetch_failed")

    content_type = (response.headers.get("content-type") or "").lower()
    data = response.content[:max_bytes]

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        tmp = Path(settings.upload_dir) / "_tmp" / f"url-{abs(hash(url))}.pdf"
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
