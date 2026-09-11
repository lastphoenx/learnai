"""Tests für PDF-Seitenbereich (Batch-Import Grundlage)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ai.errors import LlmError
from app.ai.extract import (
    extract_pdf_pages_text,
    pdf_page_count,
    render_pdf_pages,
)


def _write_sample_pdf(path: Path, *, pages: int = 3) -> None:
    import pymupdf

    doc = pymupdf.open()
    try:
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"Lernheft Seite {i + 1} — Posten {14 + i}")
        doc.save(str(path))
    finally:
        doc.close()


def test_pdf_page_count_and_render_range(tmp_path: Path):
    pdf = tmp_path / "heft.pdf"
    _write_sample_pdf(pdf, pages=4)

    assert pdf_page_count(pdf) == 4

    rendered = render_pdf_pages(pdf, page_from=2, page_to=3)
    assert [num for num, _ in rendered] == [2, 3]
    for _, png in rendered:
        assert png.startswith(b"\x89PNG")


def test_extract_pdf_pages_text_reads_text_layer(tmp_path: Path):
    pdf = tmp_path / "text.pdf"
    _write_sample_pdf(pdf, pages=2)

    text = extract_pdf_pages_text(pdf, page_from=1, page_to=2, vision_fallback=False)
    assert "Seite 1" in text
    assert "Seite 2" in text
    assert "--- Seite 1 ---" in text


def test_invalid_page_range_raises(tmp_path: Path):
    pdf = tmp_path / "small.pdf"
    _write_sample_pdf(pdf, pages=2)

    with pytest.raises(LlmError) as exc:
        render_pdf_pages(pdf, page_from=3, page_to=4)
    assert exc.value.code == "invalid_page_range"

    with pytest.raises(LlmError) as exc:
        render_pdf_pages(pdf, page_from=2, page_to=1)
    assert exc.value.code == "invalid_page_range"
