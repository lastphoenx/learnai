from datetime import datetime, timedelta, timezone

from app.services.learn_service import (
    QUIZ_RETRY_COOLDOWN,
    _parse_retry_at,
    _retry_available_at_iso,
)


def test_retry_available_at_is_ten_minutes_ahead():
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    iso = _retry_available_at_iso(base)
    parsed = _parse_retry_at(iso)
    assert parsed is not None
    assert parsed - base == QUIZ_RETRY_COOLDOWN


def test_parse_retry_at_accepts_iso():
    value = "2026-01-01T12:10:00+00:00"
    parsed = _parse_retry_at(value)
    assert parsed is not None
    assert parsed.year == 2026
