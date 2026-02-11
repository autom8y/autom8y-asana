"""Shared fixtures for client cache tests."""

from __future__ import annotations

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType


class MockCacheProvider:
    """Mock cache provider for testing (superset with set_batch)."""

    def __init__(self) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self.get_versioned_calls: list[tuple[str, EntryType]] = []
        self.set_versioned_calls: list[tuple[str, CacheEntry]] = []
        self.set_batch_calls: list[dict[str, CacheEntry]] = []
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []

    def get_versioned(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        """Get entry from cache."""
        self.get_versioned_calls.append((key, entry_type))
        return self._cache.get(f"{key}:{entry_type.value}")

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store entry in cache."""
        self.set_versioned_calls.append((key, entry))
        self._cache[f"{key}:{entry.entry_type.value}"] = entry

    def set_batch(self, entries: dict[str, CacheEntry]) -> None:
        """Store multiple entries in cache."""
        self.set_batch_calls.append(entries)
        for key, entry in entries.items():
            self._cache[f"{key}:{entry.entry_type.value}"] = entry

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache entry."""
        self.invalidate_calls.append((key, entry_types))
        if entry_types:
            for entry_type in entry_types:
                self._cache.pop(f"{key}:{entry_type.value}", None)
        else:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{key}:")]
            for k in keys_to_remove:
                del self._cache[k]


@pytest.fixture
def cache_provider() -> MockCacheProvider:
    """Create a mock cache provider."""
    return MockCacheProvider()
