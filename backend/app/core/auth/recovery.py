"""Recovery-Codes für 2FA-Notfall."""

from sqlalchemy.orm import Session

from app.core.auth.passwords import generate_recovery_code, hash_password, verify_password
from app.models import RecoveryCode


def normalize_code(code: str) -> str:
    return code.replace("-", "").replace(" ", "").upper()


def generate_recovery_codes(db: Session, user_id, count: int = 10) -> list[str]:
    """Erzeugt Codes, speichert Hashes, gibt Klartext-Codes einmalig zurück."""
    plaintext_codes: list[str] = []
    for _ in range(count):
        raw = generate_recovery_code()
        plaintext_codes.append(raw)
        db.add(
            RecoveryCode(
                user_id=user_id,
                code_hash=hash_password(normalize_code(raw)),
            )
        )
    db.flush()
    return plaintext_codes


def verify_and_consume_recovery_code(db: Session, user_id, code: str) -> bool:
    normalized = normalize_code(code)
    for entry in (
        db.query(RecoveryCode)
        .filter(RecoveryCode.user_id == user_id, RecoveryCode.used_at.is_(None))
        .all()
    ):
        if verify_password(entry.code_hash, normalized):
            from datetime import datetime, timezone

            entry.used_at = datetime.now(timezone.utc)
            return True
    return False
