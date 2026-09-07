from pathlib import Path

from app.core.html_source_serve import (
    build_html_pack_file_response,
    inline_content_disposition,
    is_html_pack_source,
)
from app.models import UnitSource


def test_html_source_uses_inline_disposition():
    response = build_html_pack_file_response(Path("/tmp/x.html"), "pack.html")
    disp = response.headers.get("content-disposition", "").lower()
    assert disp == "inline"
    assert "attachment" not in disp


def test_pack_query_forces_html_mode(tmp_path: Path):
    html = tmp_path / "note.txt"
    html.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    source = UnitSource(kind="document", content_type="application/octet-stream")
    assert not is_html_pack_source(source, "note.txt", html, pack_mode=False)
    assert is_html_pack_source(source, "note.txt", html, pack_mode=True)


def test_html_extension_overrides_non_html_kind(tmp_path: Path):
    path = tmp_path / "pack.htm"
    path.write_text("<html><body>Hi</body></html>", encoding="utf-8")
    source = UnitSource(kind="document", content_type="application/octet-stream")
    assert is_html_pack_source(source, "pack.htm", path)


def test_document_kind_blocks_html_sniffing(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    source = UnitSource(kind="document", content_type="application/octet-stream")
    assert not is_html_pack_source(source, "notes.txt", path, pack_mode=False)


def test_inline_content_disposition_ascii():
    assert inline_content_disposition("pack.html") == 'inline; filename="pack.html"'


def test_inline_content_disposition_unicode():
    disp = inline_content_disposition("übung.html")
    assert disp.startswith("inline; filename*=utf-8''")
