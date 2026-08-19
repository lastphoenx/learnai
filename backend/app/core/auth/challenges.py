"""Kurzlebige Login-Challenges für den 2FA-Zwischenschritt."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import LoginChallenge


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_challenge_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_login_challenge(db: Session, user_id) -> str:
    token = generate_challenge_token()
    challenge = LoginChallenge(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=_utcnow() + timedelta(seconds=settings.login_challenge_ttl_sec),
    )
    db.add(challenge)
    db.flush()
    return token


def consume_login_challenge(db: Session, token: str) -> LoginChallenge | None:
    if not token:
        return None
    challenge = (
        db.query(LoginChallenge)
        .filter(
            LoginChallenge.token_hash == hash_token(token),
            LoginChallenge.used_at.is_(None),
            LoginChallenge.expires_at > _utcnow(),
        )
        .first()
    )
    if challenge:
        challenge.used_at = _utcnow()
    return challenge
