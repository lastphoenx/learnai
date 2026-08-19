import pytest

from app.core.auth.rbac import ProjectRole
from app.core.locking import LockError, acquire_lock, lock_is_active, release_lock, require_lock
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class FakeLockable:
    def __init__(self):
        self.locked_by_id = None
        self.locked_until = None


def test_acquire_and_release():
    entity = FakeLockable()
    uid = uuid4()
    acquire_lock(entity, uid)
    assert lock_is_active(entity)
    release_lock(entity, uid)
    assert not lock_is_active(entity)


def test_require_lock_fails_without_lock():
    entity = FakeLockable()
    with pytest.raises(LockError):
        require_lock(entity, uuid4())


def test_role_ordering():
    assert ProjectRole.MEMBER > ProjectRole.VIEWER
    assert ProjectRole.OWNER > ProjectRole.MANAGER
