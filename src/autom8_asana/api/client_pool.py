"""Token-keyed client pool for S2S resilience.

Per IMP-19 (INIT-RUNTIME-OPT-002): With >80% S2S traffic using one bot PAT,
per-request client creation discards rate limiter, circuit breaker, and AIMD
semaphore state on every request. This pool maintains long-lived clients
keyed by token hash, enabling these stateful components to accumulate
meaningful signal.

Design:
- Pool keyed by SHA-256 hash prefix of token (16 hex chars)
- LRU eviction when pool exceeds max_size (100)
- TTL-based expiry: 1 hour for S2S clients, 5 minutes for user-PAT clients
- Returned clients have aclose() as a no-op to prevent dependency teardown
  from invalidating pooled clients (per QA condition R4)
- Circuit breaker tuned: failure_threshold=10, recovery_timeout=30s (per R4)
- Pool metrics: hits, misses, evictions tracked via structlog
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig, CircuitBreakerConfig

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)

__all__ = ["ClientPool"]


class _PooledClientWrapper:
    """Wrapper that proxies all attribute access to the underlying AsanaClient.

    The only override is aclose() and close(), which are no-ops.
    This prevents FastAPI dependency teardown from closing pooled clients.
    Per QA condition R4: pooled clients MUST NOT be closed by dependency teardown.
    """

    __slots__ = ("_client",)

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    async def aclose(self) -> None:
        """No-op: pooled clients are closed only via pool.close_all()."""

    async def close(self) -> None:
        """No-op: pooled clients are closed only via pool.close_all()."""

    async def __aenter__(self) -> _PooledClientWrapper:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - no-op for pooled clients."""


class ClientPool:
    """Token-keyed pool of AsanaClient instances.

    Maintains long-lived clients so that rate limiters, circuit breakers,
    and AIMD semaphores accumulate state across requests sharing the same
    token.

    Args:
        max_size: Maximum number of pooled clients (default 100).
        s2s_ttl: TTL in seconds for S2S (bot PAT) clients (default 3600).
        pat_ttl: TTL in seconds for user-PAT clients (default 300).

    Example:
        pool = ClientPool()
        client = await pool.get_or_create(token="xoxb-...", is_s2s=True)
        # client is a wrapper with aclose() as no-op
        await client.tasks.get_async("123")
    """

    def __init__(
        self,
        *,
        max_size: int = 100,
        s2s_ttl: float = 3600.0,
        pat_ttl: float = 300.0,
        cache_provider: CacheProvider | None = None,
    ) -> None:
        # Pool: token_hash -> (client, last_access_time, created_at_time, is_s2s)
        self._pool: dict[str, tuple[AsanaClient, float, float, bool]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._s2s_ttl = s2s_ttl
        self._pat_ttl = pat_ttl
        self._cache_provider = cache_provider
        self._stats: dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token to a 16-char hex string for pool keying."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    def _is_expired(self, created_at: float, is_s2s: bool) -> bool:
        """Check if a pooled client has exceeded its TTL."""
        ttl = self._s2s_ttl if is_s2s else self._pat_ttl
        return (time.monotonic() - created_at) > ttl

    def _evict_lru(self) -> None:
        """Evict the least-recently-used entry from the pool.

        Must be called while holding self._lock.
        """
        if not self._pool:
            return

        lru_key = min(self._pool, key=lambda k: self._pool[k][1])
        del self._pool[lru_key]
        self._stats["evictions"] += 1
        logger.info(
            "pool.eviction",
            extra={
                "evicted_key": lru_key,
                "pool_size": len(self._pool),
            },
        )

    @staticmethod
    def _make_pool_config() -> AsanaConfig:
        """Create AsanaConfig with CB tuning per QA condition R4.

        Returns:
            AsanaConfig with failure_threshold=10, recovery_timeout=30s.
        """
        return AsanaConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=10,
                recovery_timeout=30.0,
            ),
        )

    async def get_or_create(
        self,
        token: str,
        *,
        is_s2s: bool = False,
    ) -> AsanaClient:
        """Get an existing pooled client or create a new one.

        Args:
            token: Asana PAT (bot or user).
            is_s2s: True for S2S (bot PAT) clients (1hr TTL),
                    False for user-PAT clients (5min TTL).

        Returns:
            AsanaClient (wrapped with no-op aclose) for the given token.
        """
        key = self._hash_token(token)
        now = time.monotonic()

        async with self._lock:
            entry = self._pool.get(key)

            if entry is not None:
                client, _last_access, created_at, entry_is_s2s = entry

                if not self._is_expired(created_at, entry_is_s2s):
                    # Cache hit: update last_access time
                    self._pool[key] = (client, now, created_at, entry_is_s2s)
                    self._stats["hits"] += 1
                    logger.debug(
                        "pool.hit",
                        extra={
                            "token_hash": key,
                            "is_s2s": is_s2s,
                            "pool_size": len(self._pool),
                        },
                    )
                    return _PooledClientWrapper(client)  # type: ignore[return-value]

                # Expired: remove stale entry, create fresh below
                del self._pool[key]

            # Cache miss: create new client
            # DEF-005: inject shared cache_provider so pooled clients share
            # the same cache backend as warm-up tasks.
            config = self._make_pool_config()
            client = AsanaClient(
                token=token,
                config=config,
                cache_provider=self._cache_provider,
            )
            self._pool[key] = (client, now, now, is_s2s)
            self._stats["misses"] += 1

            # LRU eviction if over capacity
            if len(self._pool) > self._max_size:
                self._evict_lru()

            logger.debug(
                "pool.miss",
                extra={
                    "token_hash": key,
                    "is_s2s": is_s2s,
                    "pool_size": len(self._pool),
                },
            )

        return _PooledClientWrapper(client)  # type: ignore[return-value]

    async def close_all(self) -> None:
        """Close all pooled clients and clear the pool.

        Called during application shutdown (lifespan handler).
        """
        async with self._lock:
            for key, (client, _, _, _) in self._pool.items():
                try:
                    await client.aclose()
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "pool.close_error",
                        extra={"token_hash": key},
                        exc_info=True,
                    )
            self._pool.clear()
            logger.info(
                "pool.closed",
                extra={
                    "stats": self._stats.copy(),
                },
            )

    @property
    def stats(self) -> dict[str, int]:
        """Return a copy of pool statistics."""
        return self._stats.copy()

    @property
    def size(self) -> int:
        """Current number of clients in the pool."""
        return len(self._pool)
