import pytest

from app.ai.errors import LlmError
from app.core.url_safety import validate_public_http_url


def test_rejects_localhost():
    with pytest.raises(LlmError, match="internen Netz"):
        validate_public_http_url("http://localhost/test")


def test_rejects_private_ip_literal():
    with pytest.raises(LlmError, match="internen Netz"):
        validate_public_http_url("http://192.168.1.1/doc")


def test_rejects_metadata_ip():
    with pytest.raises(LlmError, match="internen Netz"):
        validate_public_http_url("http://169.254.169.254/latest/meta-data/")


def test_rejects_credentials_in_url():
    with pytest.raises(LlmError, match="Anmeldedaten"):
        validate_public_http_url("http://user:pass@example.com/")
