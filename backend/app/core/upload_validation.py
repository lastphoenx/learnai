"""Magic-Byte-Validierung für Datei-Uploads (Quellen + Prüfungen)."""

from __future__ import annotations

from dataclasses import dataclass


class UploadValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_upload") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DetectedUpload:
    kind: str  # image | document | audio | html
    content_type: str


def _starts_with(data: bytes, prefix: bytes) -> bool:
    return len(data) >= len(prefix) and data[: len(prefix)] == prefix


def _is_html(data: bytes, filename: str = "") -> bool:
    name = (filename or "").lower()
    if name.endswith((".html", ".htm")):
        return True
    head = data[:512].lstrip().lower()
    return head.startswith((b"<!doctype", b"<html", b"<head", b"<body", b"<meta", b"<title"))


def _is_pdf(data: bytes) -> bool:
    return len(data) >= 5 and data[:5] == b"%PDF-"


def _is_jpeg(data: bytes) -> bool:
    return len(data) >= 3 and data[:3] == b"\xff\xd8\xff"


def _is_png(data: bytes) -> bool:
    return _starts_with(data, b"\x89PNG\r\n\x1a\n")


def _is_webp(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _is_heic(data: bytes) -> bool:
    if len(data) < 12 or data[4:8] != b"ftyp":
        return False
    brand = data[8:12]
    return brand in {b"heic", b"heix", b"hevc", b"mif1"}


def _is_wav(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _is_ogg(data: bytes) -> bool:
    return _starts_with(data, b"OggS")


def _is_mp3(data: bytes) -> bool:
    if _starts_with(data, b"ID3"):
        return True
    if len(data) >= 2 and data[0] == 0xFF and data[1] in {0xFB, 0xF3, 0xF2, 0xFA}:
        return True
    return False


def _is_m4a(data: bytes) -> bool:
    if len(data) < 12 or data[4:8] != b"ftyp":
        return False
    brand = data[8:12]
    return brand in {b"M4A ", b"mp42", b"isom", b"iso2", b"MSNV", b"3gp4"}


def detect_upload(data: bytes, filename: str = "") -> DetectedUpload | None:
    """Erkennt erlaubten Dateityp anhand Magic Bytes (nicht Client-Header)."""
    if not data:
        return None
    name = (filename or "").lower()

    if _is_pdf(data):
        return DetectedUpload(kind="document", content_type="application/pdf")
    if _is_jpeg(data):
        return DetectedUpload(kind="image", content_type="image/jpeg")
    if _is_png(data):
        return DetectedUpload(kind="image", content_type="image/png")
    if _is_webp(data):
        return DetectedUpload(kind="image", content_type="image/webp")
    if _is_heic(data):
        return DetectedUpload(kind="image", content_type="image/heic")
    if _is_wav(data):
        return DetectedUpload(kind="audio", content_type="audio/wav")
    if _is_ogg(data):
        return DetectedUpload(kind="audio", content_type="audio/ogg")
    if _is_mp3(data):
        return DetectedUpload(kind="audio", content_type="audio/mpeg")
    if _is_m4a(data) or name.endswith(".m4a"):
        if _is_m4a(data):
            return DetectedUpload(kind="audio", content_type="audio/mp4")
    # HTML nach Magic-Bytes der Binärformate prüfen — sonst würden PDF/Bilder falsch durchgehen
    if _is_html(data, name):
        return DetectedUpload(kind="html", content_type="text/html; charset=utf-8")
    return None


def validate_upload_bytes(
    data: bytes,
    *,
    filename: str = "",
    declared_content_type: str | None = None,
    allow_audio: bool = True,
) -> DetectedUpload:
    detected = detect_upload(data, filename)
    if not detected:
        raise UploadValidationError(
            "Dateityp nicht erkannt oder nicht erlaubt (nur PDF, Bilder, HTML"
            + (", Audio" if allow_audio else "")
            + ")",
            "invalid_file_type",
        )
    if not allow_audio and detected.kind == "audio":
        raise UploadValidationError("Audio-Dateien sind hier nicht erlaubt", "invalid_file_type")

    declared = (declared_content_type or "").split(";")[0].strip().lower()
    if declared and declared not in {"application/octet-stream", "binary/octet-stream"}:
        family_ok = (
            (detected.kind == "image" and declared.startswith("image/"))
            or (detected.kind == "document" and declared == "application/pdf")
            or (detected.kind == "audio" and declared.startswith("audio/"))
            or (detected.kind == "html" and declared in {"text/html", "application/xhtml+xml"})
        )
        if not family_ok:
            raise UploadValidationError(
                "Content-Type passt nicht zum Dateiinhalt",
                "content_type_mismatch",
            )

    return detected
