"""Zentralisiertes Record-Locking (Soft Lock mit Lease)."""

from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

LOCK_MINUTES = 15


class Lockable(Protocol):
    locked_by_id: UUID | None
    locked_until: datetime | None


class LockError(Exception):
    def __init__(self, message: str, code: str = "locked"):
        self.message = message
        self.code = code
        super().__init__(message)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lock_is_active(entity: Lockable) -> bool:
    if not entity.locked_by_id or not entity.locked_until:
        return False
    return entity.locked_until > _utcnow()


def acquire_lock(entity: Lockable, user_id: UUID) -> None:
    if lock_is_active(entity) and entity.locked_by_id != user_id:
        raise LockError("Datensatz wird bereits bearbeitet")
    entity.locked_by_id = user_id
    entity.locked_until = _utcnow() + timedelta(minutes=LOCK_MINUTES)


def release_lock(entity: Lockable, user_id: UUID) -> None:
    if entity.locked_by_id == user_id:
        entity.locked_by_id = None
        entity.locked_until = None


def require_lock(entity: Lockable, user_id: UUID) -> None:
    if not lock_is_active(entity) or entity.locked_by_id != user_id:
        raise LockError("Bearbeitungssperre erforderlich – zuerst lock setzen")


def refresh_lock(entity: Lockable, user_id: UUID) -> None:
    if entity.locked_by_id == user_id:
        entity.locked_until = _utcnow() + timedelta(minutes=LOCK_MINUTES)
