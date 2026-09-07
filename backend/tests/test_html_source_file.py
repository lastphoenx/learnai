def test_html_source_uses_inline_disposition():
    from starlette.responses import FileResponse

    response = FileResponse(
        "/tmp/x.html",
        media_type="text/html; charset=utf-8",
        filename="pack.html",
        content_disposition_type="inline",
    )
    assert "inline" in response.headers.get("content-disposition", "").lower()
    assert "attachment" not in response.headers.get("content-disposition", "").lower()
