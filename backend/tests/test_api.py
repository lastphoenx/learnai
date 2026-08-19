import base64
import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def env_keys(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-pytest-only-32chars!!")
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")
    from app.config import Settings

    settings = Settings()
    monkeypatch.setattr("app.config.settings", settings)
    monkeypatch.setattr("app.core.crypto.encryption.settings", settings)


@pytest.fixture
def client(env_keys, monkeypatch):
    mock_db = MagicMock()
    mock_db.execute.return_value = None

    def override_get_db():
        yield mock_db

    from app.core.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200


def test_register_disabled_when_flag_false(env_keys, monkeypatch):
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    from app.config import Settings

    monkeypatch.setattr("app.config.settings", Settings())

    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    from app.core.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    res = c.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "verylongpassword1", "display_name": "A"},
    )
    assert res.status_code == 403
