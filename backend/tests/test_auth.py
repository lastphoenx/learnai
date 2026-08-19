import pytest

from app.core.auth.passwords import hash_password, verify_password
from app.core.auth.recovery import normalize_code
from app.core.auth.recovery import normalize_code
from app.core.auth.totp import generate_totp_secret, verify_totp


def test_recovery_code_normalize():
    assert normalize_code("abcd-ef12") == "ABCDEF12"


def test_totp_roundtrip():
    secret = generate_totp_secret()
    import pyotp

    code = pyotp.TOTP(secret).now()
    assert verify_totp(secret, code)


def test_recovery_code_hash():
    code = normalize_code("abcd-ef12")
    hashed = hash_password(code)
    assert verify_password(hashed, code)
