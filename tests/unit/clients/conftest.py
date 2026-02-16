"""Shared fixtures for client cache tests."""

from __future__ import annotations

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

from autom8_asana.cache.models.entry import CacheEntry, EntryType


class MockCacheProvider(_SDKMockCacheProvider):
    """Mock cache provider for client tests (extends SDK MockCacheProvider).

    Adds satellite-specific typed tracking lists (get_versioned_calls,
    set_versioned_calls, etc.) on top of the SDK's unified .calls list
    and assertion helpers. Handles EntryType enum values for composite
    key construction.
    """

    def __init__(self) -> None:
        super().__init__()
        self.get_versioned_calls: list[tuple[str, EntryType]] = []
        self.set_versioned_calls: list[tuple[str, CacheEntry]] = []
        self.set_batch_calls: list[dict[str, CacheEntry]] = []
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []

    @property
    def _cache(self) -> dict[str, CacheEntry]:
        """Alias for SDK _versioned_store (backward compat for tests that pre-populate)."""
        return self._versioned_store  # type: ignore[return-value]

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: object = None,
    ) -> CacheEntry | None:
        """Get entry from cache with satellite tracking."""
        self.get_versioned_calls.append((key, entry_type))
        self.calls.append(
            (
                "get_versioned",
                {"key": key, "entry_type": entry_type, "freshness": freshness},
            )
        )
        composite_key = f"{key}:{entry_type.value}"
        return self._versioned_store.get(composite_key)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store entry in cache with satellite tracking."""
        self.set_versioned_calls.append((key, entry))
        self.calls.append(("set_versioned", {"key": key, "entry": entry}))
        composite_key = f"{key}:{entry.entry_type.value}"
        self._versioned_store[composite_key] = entry

    def set_batch(self, entries: dict[str, CacheEntry]) -> None:
        """Store multiple entries with satellite tracking."""
        self.set_batch_calls.append(entries)
        self.calls.append(("set_batch", {"entries": entries}))
        for key, entry in entries.items():
            composite_key = f"{key}:{entry.entry_type.value}"
            self._versioned_store[composite_key] = entry

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache entry with satellite tracking."""
        self.invalidate_calls.append((key, entry_types))
        self.calls.append(("invalidate", {"key": key, "entry_types": entry_types}))
        if entry_types:
            for entry_type in entry_types:
                self._versioned_store.pop(f"{key}:{entry_type.value}", None)
        else:
            keys_to_remove = [
                k for k in self._versioned_store if k.startswith(f"{key}:")
            ]
            for k in keys_to_remove:
                del self._versioned_store[k]
            self._store.pop(key, None)


@pytest.fixture
def cache_provider() -> MockCacheProvider:
    """Create a mock cache provider (SDK-backed with satellite tracking)."""
    return MockCacheProvider()
