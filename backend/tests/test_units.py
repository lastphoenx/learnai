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


def test_template_ids_from_recon():
    from app.services.unit_service import _attach_template_fields, _template_ids_from_recon

    tid, troot = _template_ids_from_recon(
        {"template_unit_id": "parent-id", "template_root_id": "root-id"}
    )
    assert tid == "parent-id"
    assert troot == "root-id"

    row = {"id": "unit-1"}
    _attach_template_fields(row, None)
    assert row["template_unit_id"] is None
    assert row["template_root_id"] == "unit-1"


def test_update_unit_profile_unassign(monkeypatch):
    import base64
    import os
    import uuid
    from unittest.mock import MagicMock

    from app.models import LearningProfile, LearningRecord, LearningUnit, User
    from app.services.unit_service import update_unit_profile

    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", key)
    from app.config import Settings

    monkeypatch.setattr("app.config.settings", Settings())
    monkeypatch.setattr("app.core.crypto.encryption.settings", Settings())

    tenant_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child_profile_id = uuid.uuid4()
    child_user_id = uuid.uuid4()
    unit_id = uuid.uuid4()

    parent = MagicMock(spec=User)
    parent.id = parent_id
    parent.tenant_id = tenant_id
    parent.is_child = False
    parent.is_admin = False

    unit = MagicMock(spec=LearningUnit)
    unit.id = unit_id
    unit.tenant_id = tenant_id
    unit.created_by_id = parent_id
    unit.profile_id = child_profile_id
    unit.learner_id = child_user_id
    unit.task_type = "mixed"
    unit.title_encrypted = b"x"
    unit.brief_encrypted = None
    unit.modules = []
    unit.sources = []
    unit.profile = None

    record = MagicMock(spec=LearningRecord)
    record.unit_id = unit_id
    record.reconstruction_encrypted = None
    record.exam_results = []

    db = MagicMock()

    monkeypatch.setattr("app.services.unit_service._get_unit_or_404", lambda _db, _user, _uid: unit)
    monkeypatch.setattr("app.services.unit_service.get_unit", lambda _db, _user, _uid: {"id": str(unit_id), "profile_id": None})
    monkeypatch.setattr("app.services.unit_service.log_event", lambda *a, **k: None)
    db.query.return_value.filter.return_value.first.return_value = record

    update_unit_profile(db, parent, unit_id, profile_id=None)
    assert unit.profile_id is None
    assert unit.learner_id == parent_id
    assert record.profile_id is None
    assert record.user_id == parent_id
