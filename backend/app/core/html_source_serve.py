"""Serving self-contained HTML exercise packs in a sandboxed iframe."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from starlette.responses import FileResponse

from app.models import UnitSource

_HTML_PREFIXES = (b"<!doctype", b"<html", b"<head", b"<body", b"<meta", b"<title")
# Explizite Nicht-HTML-Quellen: kein Content-Sniffing (sonst würde kind=document ignoriert).
_EXPLICIT_NON_HTML_KINDS = frozenset({"document", "image", "audio", "pdf"})


def is_html_pack_source(
    source: UnitSource,
    name: str,
    path: Path,
    *,
    pack_mode: bool = False,
) -> bool:
    """True when the file should render inline in HtmlPackFrame (not as download)."""
    if pack_mode:
        return True
    if source.kind == "html":
        return True
    if "html" in (source.content_type or "").lower():
        return True
    if name.lower().endswith((".html", ".htm")):
        return True
    if source.kind in _EXPLICIT_NON_HTML_KINDS:
        return False
    try:
        head = path.read_bytes()[:512].lstrip().lower()
    except OSError:
        return False
    return head.startswith(_HTML_PREFIXES)


def html_pack_filename(name: str) -> str:
    if name.lower().endswith((".html", ".htm")):
        return name
    return f"{name}.html"


def inline_content_disposition(filename: str) -> str:
    quoted = quote(filename)
    if quoted != filename:
        return f"inline; filename*=utf-8''{quoted}"
    return f'inline; filename="{filename}"'


def build_html_pack_file_response(path: Path, name: str) -> FileResponse:
    response = FileResponse(
        path,
        media_type="text/html; charset=utf-8",
        content_disposition_type="inline",
    )
    # Ohne filename: manche Browser/iframes behandeln inline+filename sonst als Download.
    response.headers["Content-Disposition"] = "inline"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = (
        "frame-ancestors 'self'; default-src 'none'; "
        "script-src 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'unsafe-inline'; img-src data: blob: 'self'; "
        "font-src data: 'self'; connect-src 'none'; base-uri 'none'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "private, no-cache"
    return response
