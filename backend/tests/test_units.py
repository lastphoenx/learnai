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
    assert payload["task_type"] == "mixed"
    assert "brief" in payload


def test_merge_template_recon_keeps_trainer_options(monkeypatch):
    import base64
    import os

    from app.services.unit_service import reconstruction_payload
    from app.services.crypto_json import encrypt_json, decrypt_json

    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", key)
    from app.config import Settings

    monkeypatch.setattr("app.config.settings", Settings())
    monkeypatch.setattr("app.core.crypto.encryption.settings", Settings())

    src = reconstruction_payload(
        title="Bruchrechnen",
        brief="Test",
        subject="math",
        language="de",
        target_age="12",
        difficulty=2,
        task_type="interactive",
        trainer_options={"cards": 40, "questions": 35, "style": "playful", "answer_length": "short"},
    )
    src["template_unit_id"] = "source-id"
    dst = reconstruction_payload(
        title="Bruchrechnen",
        brief="Test",
        subject="math",
        language="de",
        target_age="12",
        difficulty=2,
        task_type="interactive",
        trainer_options={"cards": 50, "questions": 50, "style": "playful", "answer_length": "short"},
    )
    merged = dict(dst)
    merged["trainer_options"] = dict(src["trainer_options"])
    merged["template_unit_id"] = src["template_unit_id"]
    roundtrip = decrypt_json(encrypt_json(merged))
    assert roundtrip["trainer_options"]["cards"] == 40
    assert roundtrip["template_unit_id"] == "source-id"
