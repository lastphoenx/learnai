from app.services.unit_service import reconstruction_payload


def test_reconstruction_payload_shape():
    payload = reconstruction_payload(
        title="Bruchrechnen",
        brief="Einstieg mit Fotos aus dem Lernmittel",
        subject="math",
        language="de",
        target_age="6-12",
        difficulty=2,
    )
    assert payload["title"] == "Bruchrechnen"
    assert payload["language"] == "de"
    assert payload["difficulty"] == 2
    assert "brief" in payload
