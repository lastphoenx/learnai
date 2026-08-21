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
        validate_upload_bytes(b"<html>evil</html>", filename="x.pdf", declared_content_type="application/pdf")


def test_reject_audio_when_disallowed():
    data = b"ID3" + b"\x00" * 20
    with pytest.raises(UploadValidationError):
        validate_upload_bytes(data, filename="exam.mp3", allow_audio=False)
