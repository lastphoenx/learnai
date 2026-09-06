"""Upload Magic-Byte-Validierung."""

import pytest

from app.core.upload_validation import UploadValidationError, detect_upload, validate_upload_bytes


def test_detect_pdf():
    data = b"%PDF-1.4\n%..."
    out = detect_upload(data, "work.pdf")
    assert out is not None
    assert out.kind == "document"
    assert out.content_type == "application/pdf"


def test_detect_png():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    out = detect_upload(data, "scan.png")
    assert out is not None
    assert out.kind == "image"


def test_reject_unknown():
    with pytest.raises(UploadValidationError):
        validate_upload_bytes(b"not a real file !!!", filename="x.bin", declared_content_type="application/octet-stream")


def test_detect_html():
    data = b"<!DOCTYPE html><html><body><h1>Hallo</h1></body></html>"
    out = detect_upload(data, "trainer.html")
    assert out is not None
    assert out.kind == "html"
    assert "html" in out.content_type
    validated = validate_upload_bytes(data, filename="trainer.html", declared_content_type="text/html")
    assert validated.kind == "html"


def test_reject_html_as_pdf():
    with pytest.raises(UploadValidationError):
        validate_upload_bytes(
            b"<!DOCTYPE html><html></html>",
            filename="x.pdf",
            declared_content_type="application/pdf",
        )


def test_reject_audio_when_disallowed():
    data = b"ID3" + b"\x00" * 20
    with pytest.raises(UploadValidationError):
        validate_upload_bytes(data, filename="exam.mp3", allow_audio=False)
