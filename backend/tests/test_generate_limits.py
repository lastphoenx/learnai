from unittest.mock import MagicMock, patch

import pytest

from app.services.generate_limits import acquire_generate_slot, release_generate_slot
from app.services.unit_service import UnitError


@patch("app.services.generate_limits._redis_client")
def test_acquire_respects_user_parallel_limit(mock_redis_fn):
    client = MagicMock()
    mock_redis_fn.return_value = client
    client.sismember.return_value = False
    client.incr.return_value = 1
    client.scard.side_effect = [2, 0]

    with pytest.raises(UnitError, match="parallele Generierungen"):
        acquire_generate_slot(user_id="u1", tenant_id="t1", unit_id="unit-a")

    client.decr.assert_called_once()


@patch("app.services.generate_limits._redis_client")
def test_release_clears_slot(mock_redis_fn):
    client = MagicMock()
    mock_redis_fn.return_value = client
    release_generate_slot(user_id="u1", tenant_id="t1", unit_id="unit-a")
    assert client.srem.call_count == 2
