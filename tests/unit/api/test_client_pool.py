"""Unit tests for ClientPool (IMP-19).

Tests token-keyed client pooling for S2S resilience:
- Pool hit (same token returns same underlying client)
- Pool miss (new token creates new client)
- TTL eviction (expired client gets replaced)
- LRU eviction (over max_size evicts oldest-accessed)
- close_all() closes all clients
- aclose() safety (pooled client aclose is no-op)
- Stats tracking (hits/misses/evictions counted correctly)
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.api.client_pool import ClientPool, _PooledClientWrapper


@pytest.fixture
def pool() -> ClientPool:
    """Create a pool with small size for testing."""
    return ClientPool(max_size=3, s2s_ttl=3600.0, pat_ttl=300.0)


@pytest.fixture
def mock_asana_client():
    """Create a mock AsanaClient constructor."""
    with patch("autom8_asana.api.client_pool.AsanaClient") as mock_cls:
        # Each call returns a new mock instance
        mock_cls.side_effect = lambda **kwargs: MagicMock(
            aclose=AsyncMock(),
            close=AsyncMock(),
            _token=kwargs.get("token", "unknown"),
        )
        yield mock_cls


class TestPoolHit:
    """Same token returns same underlying client."""

    async def test_same_token_returns_same_client(self, pool, mock_asana_client):
        """Second call with same token returns the same pooled client."""
        client1 = await pool.get_or_create("token-abc", is_s2s=True)
        client2 = await pool.get_or_create("token-abc", is_s2s=True)

        # Both wrappers should proxy the same underlying client
        assert client1._client is client2._client
        # Only one AsanaClient was constructed
        assert mock_asana_client.call_count == 1

    async def test_hit_increments_stats(self, pool, mock_asana_client):
        """Pool hit increments the hits counter."""
        await pool.get_or_create("token-abc")
        await pool.get_or_create("token-abc")

        assert pool.stats["hits"] == 1
        assert pool.stats["misses"] == 1  # First call is always a miss


class TestPoolMiss:
    """New token creates new client."""

    async def test_different_tokens_create_different_clients(self, pool, mock_asana_client):
        """Different tokens create separate clients."""
        client1 = await pool.get_or_create("token-abc")
        client2 = await pool.get_or_create("token-xyz")

        assert client1._client is not client2._client
        assert mock_asana_client.call_count == 2

    async def test_miss_increments_stats(self, pool, mock_asana_client):
        """Pool miss increments the misses counter."""
        await pool.get_or_create("token-abc")
        await pool.get_or_create("token-xyz")

        assert pool.stats["misses"] == 2
        assert pool.stats["hits"] == 0


class TestTTLEviction:
    """Expired client gets replaced with a fresh one."""

    async def test_expired_s2s_client_is_replaced(self, mock_asana_client):
        """S2S client past its TTL is replaced on next access."""
        pool = ClientPool(max_size=10, s2s_ttl=0.01, pat_ttl=300.0)

        client1 = await pool.get_or_create("token-abc", is_s2s=True)

        # Wait for TTL to expire
        await asyncio.sleep(0.02)

        client2 = await pool.get_or_create("token-abc", is_s2s=True)

        # Should be a different underlying client
        assert client1._client is not client2._client
        assert mock_asana_client.call_count == 2
        # Both calls are misses (first is fresh, second replaces expired)
        assert pool.stats["misses"] == 2

    async def test_expired_pat_client_is_replaced(self, mock_asana_client):
        """PAT client past its TTL is replaced on next access."""
        pool = ClientPool(max_size=10, s2s_ttl=3600.0, pat_ttl=0.01)

        client1 = await pool.get_or_create("token-abc", is_s2s=False)

        await asyncio.sleep(0.02)

        client2 = await pool.get_or_create("token-abc", is_s2s=False)

        assert client1._client is not client2._client
        assert mock_asana_client.call_count == 2

    async def test_non_expired_client_is_reused(self, mock_asana_client):
        """Client within TTL is reused."""
        pool = ClientPool(max_size=10, s2s_ttl=3600.0, pat_ttl=300.0)

        client1 = await pool.get_or_create("token-abc", is_s2s=True)
        client2 = await pool.get_or_create("token-abc", is_s2s=True)

        assert client1._client is client2._client
        assert mock_asana_client.call_count == 1


class TestLRUEviction:
    """Over max_size evicts least-recently-used entry."""

    async def test_lru_eviction_when_over_capacity(self, mock_asana_client):
        """Adding a 4th client to a max_size=3 pool evicts the LRU entry."""
        pool = ClientPool(max_size=3, s2s_ttl=3600.0, pat_ttl=300.0)

        # Add 3 clients
        await pool.get_or_create("token-a")
        await pool.get_or_create("token-b")
        await pool.get_or_create("token-c")

        assert pool.size == 3

        # Access token-a to make it recently used (token-b becomes LRU)
        await pool.get_or_create("token-a")

        # Add 4th -- should evict token-b (least recently used)
        await pool.get_or_create("token-d")

        assert pool.size == 3
        assert pool.stats["evictions"] == 1

        # token-a should still be in pool (was accessed recently)
        client_a = await pool.get_or_create("token-a")
        assert pool.stats["hits"] == 2  # Two hits for token-a

        # token-b was evicted, so accessing it creates a new client
        old_misses = pool.stats["misses"]
        await pool.get_or_create("token-b")
        assert pool.stats["misses"] == old_misses + 1

    async def test_eviction_increments_stats(self, mock_asana_client):
        """Eviction counter increments on each eviction."""
        pool = ClientPool(max_size=2, s2s_ttl=3600.0, pat_ttl=300.0)

        await pool.get_or_create("token-a")
        await pool.get_or_create("token-b")
        await pool.get_or_create("token-c")  # Evicts LRU

        assert pool.stats["evictions"] == 1

        await pool.get_or_create("token-d")  # Evicts LRU again

        assert pool.stats["evictions"] == 2


class TestCloseAll:
    """close_all() closes all clients and clears pool."""

    async def test_close_all_closes_all_clients(self, pool, mock_asana_client):
        """close_all() calls aclose() on each underlying client."""
        client_a = await pool.get_or_create("token-a")
        client_b = await pool.get_or_create("token-b")

        assert pool.size == 2

        await pool.close_all()

        assert pool.size == 0
        # Each underlying client's aclose() was called
        client_a._client.aclose.assert_called_once()
        client_b._client.aclose.assert_called_once()

    async def test_close_all_tolerates_close_errors(self, mock_asana_client):
        """close_all() continues even if individual client.aclose() fails."""
        pool = ClientPool(max_size=10)

        # Create a client that raises on close
        error_client = MagicMock()
        error_client.aclose = AsyncMock(side_effect=RuntimeError("close failed"))

        await pool.get_or_create("token-a")

        # Inject the error client directly
        key = pool._hash_token("token-a")
        pool._pool[key] = (error_client, time.monotonic(), time.monotonic(), False)

        # Should not raise
        await pool.close_all()
        assert pool.size == 0


class TestAcloseSafety:
    """Pooled client aclose is no-op (per QA condition R4)."""

    async def test_wrapper_aclose_is_noop(self, pool, mock_asana_client):
        """aclose() on returned client does NOT close the underlying client."""
        client = await pool.get_or_create("token-abc")

        # Call aclose -- should be a no-op
        await client.aclose()

        # The underlying client's aclose should NOT have been called
        assert not client._client.aclose.called

    async def test_wrapper_close_is_noop(self, pool, mock_asana_client):
        """close() on returned client does NOT close the underlying client."""
        client = await pool.get_or_create("token-abc")

        await client.close()

        assert not client._client.close.called

    async def test_wrapper_proxies_attributes(self, pool, mock_asana_client):
        """Wrapper proxies attribute access to underlying client."""
        client = await pool.get_or_create("token-abc")

        # Access an attribute that exists on the mock
        _ = client._token
        assert client._token == client._client._token

    async def test_wrapper_context_manager_is_noop(self, pool, mock_asana_client):
        """Using wrapper as async context manager does not close client."""
        client = await pool.get_or_create("token-abc")

        async with client as c:
            assert c is client

        # aclose should NOT have been called on the real client
        assert not client._client.aclose.called


class TestPooledClientWrapper:
    """Direct tests for _PooledClientWrapper."""

    def test_wrapper_getattr_delegates(self):
        """Attribute access delegates to inner client."""
        inner = MagicMock()
        inner.tasks = "tasks_client"
        wrapper = _PooledClientWrapper(inner)

        assert wrapper.tasks == "tasks_client"

    async def test_wrapper_aclose_does_nothing(self):
        """aclose is a no-op."""
        inner = MagicMock()
        inner.aclose = AsyncMock()
        wrapper = _PooledClientWrapper(inner)

        await wrapper.aclose()
        inner.aclose.assert_not_called()

    async def test_wrapper_close_does_nothing(self):
        """close is a no-op."""
        inner = MagicMock()
        inner.close = AsyncMock()
        wrapper = _PooledClientWrapper(inner)

        await wrapper.close()
        inner.close.assert_not_called()


class TestStatsTracking:
    """Stats are tracked correctly across operations."""

    async def test_initial_stats_are_zero(self, pool):
        """Fresh pool has zero stats."""
        assert pool.stats == {"hits": 0, "misses": 0, "evictions": 0}

    async def test_stats_reflect_operations(self, mock_asana_client):
        """Stats accurately reflect pool operations."""
        pool = ClientPool(max_size=2)

        # 2 misses
        await pool.get_or_create("token-a")
        await pool.get_or_create("token-b")

        # 1 hit
        await pool.get_or_create("token-a")

        # 1 miss + 1 eviction (over capacity)
        await pool.get_or_create("token-c")

        assert pool.stats == {"hits": 1, "misses": 3, "evictions": 1}

    async def test_stats_returns_copy(self, pool):
        """stats property returns a copy, not the internal dict."""
        stats = pool.stats
        stats["hits"] = 999

        assert pool.stats["hits"] == 0


class TestCBTuning:
    """Circuit breaker is configured per QA condition R4."""

    async def test_pool_config_has_cb_tuning(self):
        """Pool config uses failure_threshold=10, recovery_timeout=30."""
        config = ClientPool._make_pool_config()

        assert config.circuit_breaker.enabled is True
        assert config.circuit_breaker.failure_threshold == 10
        assert config.circuit_breaker.recovery_timeout == 30.0

    async def test_client_created_with_pool_config(self, mock_asana_client):
        """New clients are created with the pool's tuned config."""
        pool = ClientPool()
        await pool.get_or_create("token-abc")

        # Verify AsanaClient was called with token and config
        call_kwargs = mock_asana_client.call_args[1]
        assert call_kwargs["token"] == "token-abc"
        config = call_kwargs["config"]
        assert config.circuit_breaker.failure_threshold == 10
        assert config.circuit_breaker.recovery_timeout == 30.0


class TestTokenHashing:
    """Token hashing produces deterministic, fixed-length keys."""

    def test_hash_is_deterministic(self):
        """Same token always produces same hash."""
        h1 = ClientPool._hash_token("my-token")
        h2 = ClientPool._hash_token("my-token")
        assert h1 == h2

    def test_hash_is_16_chars(self):
        """Hash is truncated to 16 hex characters."""
        h = ClientPool._hash_token("my-token")
        assert len(h) == 16
        # Verify it's valid hex
        int(h, 16)

    def test_different_tokens_produce_different_hashes(self):
        """Different tokens produce different hashes."""
        h1 = ClientPool._hash_token("token-a")
        h2 = ClientPool._hash_token("token-b")
        assert h1 != h2


class TestConcurrency:
    """Pool is safe under concurrent access."""

    async def test_concurrent_gets_for_same_token(self, mock_asana_client):
        """Multiple concurrent get_or_create for the same token creates only one client."""
        pool = ClientPool()

        # Launch 10 concurrent requests for the same token
        results = await asyncio.gather(*[pool.get_or_create("token-shared") for _ in range(10)])

        # All should reference the same underlying client
        underlying_clients = {r._client for r in results}
        assert len(underlying_clients) == 1

        # Only 1 client was created
        assert mock_asana_client.call_count == 1
        assert pool.stats["misses"] == 1
        assert pool.stats["hits"] == 9

    async def test_concurrent_gets_for_different_tokens(self, mock_asana_client):
        """Concurrent get_or_create for different tokens creates separate clients."""
        pool = ClientPool(max_size=100)

        tokens = [f"token-{i}" for i in range(20)]
        results = await asyncio.gather(*[pool.get_or_create(t) for t in tokens])

        # Each token should have its own client
        assert pool.size == 20
        assert pool.stats["misses"] == 20
