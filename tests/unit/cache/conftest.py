"""Shared fixtures for cache module tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import CacheEntry, EntryType


class CacheDomainMockProvider(_SDKMockCacheProvider):
    """Shared mock cache provider for cache/ subtree tests.

    Extends SDK MockCacheProvider using type:key composite key ordering,
    matching the convention used throughout tests/unit/cache/. Provides
    get_versioned, set_versioned, invalidate, and get_batch for full
    coverage of cache domain test needs.
    """

    @property
    def _cache(self) -> dict[str, CacheEntry]:
        """Alias for SDK _versioned_store (backward compat for direct access)."""
        return self._versioned_store  # type: ignore[return-value]

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: object = None,
    ) -> CacheEntry | None:
        """Get entry using type:key composite key (cache/ subtree convention)."""
        self.calls.append(
            (
                "get_versioned",
                {"key": key, "entry_type": entry_type, "freshness": freshness},
            )
        )
        cache_key = f"{entry_type.value}:{key}"
        return self._versioned_store.get(cache_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store entry using type:key composite key (cache/ subtree convention)."""
        self.calls.append(("set_versioned", {"key": key, "entry": entry}))
        cache_key = f"{entry.entry_type.value}:{key}"
        self._versioned_store[cache_key] = entry

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries using type:key composite key."""
        self.calls.append(("invalidate", {"key": key, "entry_types": entry_types}))
        if entry_types is None:
            from autom8_asana.cache.models.entry import EntryType as _EntryType

            entry_types = list(_EntryType)
        for et in entry_types:
            cache_key = f"{et.value}:{key}"
            self._versioned_store.pop(cache_key, None)

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Batch get using individual lookups with type:key composite key."""
        self.calls.append(("get_batch", {"keys": keys, "entry_type": entry_type}))
        result: dict[str, CacheEntry | None] = {}
        for key in keys:
            cache_key = f"{entry_type.value}:{key}"
            result[key] = self._versioned_store.get(cache_key)
        return result


@pytest.fixture
def cache_domain_provider() -> CacheDomainMockProvider:
    """Create a mock cache provider for cache/ subtree tests (type:key ordering)."""
    return CacheDomainMockProvider()


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client
