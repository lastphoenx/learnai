"""Text aus PDF, Audio und Webseiten extrahieren."""

from __future__ import annotations

import os
import re
import struct
import tempfile
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


def _require_pymupdf():
    try:
        import pymupdf
    except ImportError as exc:
        raise LlmError("pymupdf nicht installiert", "pdf_missing") from exc
    return pymupdf


def pdf_page_count(path: Path) -> int:
    pymupdf = _require_pymupdf()
    doc = pymupdf.open(str(path))
    try:
        return len(doc)
    finally:
        doc.close()


def _normalize_page_range(
    *,
    page_from: int,
    page_to: int,
    page_count: int,
) -> tuple[int, int]:
    if page_count <= 0:
        raise LlmError("PDF enthält keine Seiten", "empty_pdf")
    start = int(page_from)
    end = int(page_to)
    if start < 1 or end < 1:
        raise LlmError("Seitenbereich muss ≥ 1 sein", "invalid_page_range")
    if start > end:
        raise LlmError("Seiten von darf nicht grösser sein als Seiten bis", "invalid_page_range")
    if start > page_count or end > page_count:
        raise LlmError(
            f"Seitenbereich {start}–{end} ausserhalb des PDF (1–{page_count})",
            "invalid_page_range",
        )
    return start, end


def render_pdf_pages(
    path: Path,
    *,
    page_from: int,
    page_to: int,
    dpi_scale: float = 1.5,
) -> list[tuple[int, bytes]]:
    """Rendert PDF-Seiten (1-basiert, inklusive) als PNG-Bytes."""
    pymupdf = _require_pymupdf()
    if dpi_scale <= 0:
        raise LlmError("dpi_scale muss > 0 sein", "invalid_page_range")

    doc = pymupdf.open(str(path))
    try:
        start, end = _normalize_page_range(
            page_from=page_from,
            page_to=page_to,
            page_count=len(doc),
        )
        matrix = pymupdf.Matrix(dpi_scale, dpi_scale)
        out: list[tuple[int, bytes]] = []
        for page_num in range(start, end + 1):
            page = doc[page_num - 1]
            pix = page.get_pixmap(matrix=matrix)
            out.append((page_num, pix.tobytes("png")))
        return out
    finally:
        doc.close()


def extract_pdf_pages_text(
    path: Path,
    *,
    page_from: int,
    page_to: int,
    vision_fallback: bool = True,
) -> str:
    """Text aus einem Seitenbereich — pypdf zuerst, optional Vision pro Seite."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise LlmError("pypdf nicht installiert", "pdf_missing") from exc

    pymupdf = _require_pymupdf()
    doc = pymupdf.open(str(path))
    try:
        start, end = _normalize_page_range(
            page_from=page_from,
            page_to=page_to,
            page_count=len(doc),
        )
    finally:
        doc.close()

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page_num in range(start, end + 1):
        text = (reader.pages[page_num - 1].extract_text() or "").strip()
        if text:
            parts.append(f"--- Seite {page_num} ---\n{text}")

    combined = "\n\n".join(parts).strip()
    if len(combined) >= 40:
        return combined

    if not vision_fallback:
        return combined

    from app.ai.providers import describe_image

    rendered = render_pdf_pages(path, page_from=start, page_to=end)
    vision_parts: list[str] = []
    for page_num, png_bytes in rendered:
        described = describe_image(
            image_bytes=png_bytes,
            mime="image/png",
            prompt="Extrahiere allen sichtbaren Text und beschreibe Aufgaben aus dieser PDF-Seite.",
            provider="ollama",
            model=None,
        )
        vision_parts.append(f"--- Seite {page_num} ---\n{described['text']}")
    return "\n\n".join(vision_parts).strip() or combined or "(PDF konnte nicht gelesen werden)"


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
        page_count = pdf_page_count(path)
    except LlmError:
        return "(PDF ohne Textschicht — für gescannte PDFs «pymupdf» installieren)"

    end = min(page_count, max(1, max_pages))
    return extract_pdf_pages_text(path, page_from=1, page_to=end, vision_fallback=True)


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


def _silent_wav_bytes(*, duration_ms: int = 80, rate: int = 16000) -> bytes:
    frames = max(1, rate * duration_ms // 1000)
    data = b"\x00\x00" * frames
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return header + b"data" + struct.pack("<I", len(data)) + data


def warmup_stt(provider: str | None = None) -> dict:
    """Lädt lokales Whisper vor. Browser/OpenAI brauchen keinen Server-Modellload."""
    name = (provider or "").strip().lower() or _default_server_stt_provider()
    if name in {"browser", "anthropic", "openai"}:
        return {"ok": True, "provider": name}
    if name == "local" and not _whisper_transcription_url():
        return {"ok": False, "provider": name, "error": "WHISPER_URL fehlt"}
    handle, tmp_name = tempfile.mkstemp(suffix=".wav")
    tmp_path = Path(tmp_name)
    try:
        os.close(handle)
        tmp_path.write_bytes(_silent_wav_bytes())
        transcribe_audio(tmp_path, language="de", provider=name)
        return {"ok": True, "provider": name}
    except LlmError as exc:
        return {"ok": False, "provider": name, "error": exc.message}
    except Exception as exc:
        return {"ok": False, "provider": name, "error": str(exc)[:200]}
    finally:
        tmp_path.unlink(missing_ok=True)


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
