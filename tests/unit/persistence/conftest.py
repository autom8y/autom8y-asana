"""Shared fixtures for persistence module tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import EntryType


class MockCacheProviderForInvalidation(_SDKMockCacheProvider):
    """Shared mock cache provider for persistence invalidation tests.

    Superset of both test_session_invalidation.py and
    test_session_dataframe_invalidation.py variants. Provides:
    - fail_on_invalidate flag: simulates generic invalidation failure
    - fail_on_dataframe_invalidate flag: simulates DataFrame-specific failure
    - invalidate_calls tracking: records all invalidation invocations
    - get_invalidations_for_type(): filters calls by EntryType

    get_versioned always returns None and set_versioned is a no-op,
    matching the invalidation-test semantics of both originals.
    """

    def __init__(self) -> None:
        super().__init__()
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []
        self.fail_on_invalidate: bool = False
        self.fail_on_dataframe_invalidate: bool = False

    def get_versioned(self, key: str, entry_type: EntryType, freshness: object = None) -> None:
        """Always returns None (invalidation-test semantics)."""
        return None

    def set_versioned(self, key: str, entry: Any) -> None:
        """No-op (invalidation-test semantics)."""

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache entry with fail simulation."""
        if self.fail_on_invalidate:
            raise ConnectionError("Cache invalidation failed")
        if (
            self.fail_on_dataframe_invalidate
            and entry_types is not None
        ):
            from autom8_asana.cache.models.entry import EntryType as _EntryType

            if _EntryType.DATAFRAME in entry_types:
                raise ConnectionError("DataFrame cache invalidation failed")
        self.invalidate_calls.append((key, entry_types))

    def get_invalidations_for_type(
        self, entry_type: EntryType
    ) -> list[tuple[str, list[EntryType] | None]]:
        """Return invalidation calls that include a specific entry type."""
        return [
            (key, types)
            for key, types in self.invalidate_calls
            if types and entry_type in types
        ]


@pytest.fixture
def invalidation_cache_provider() -> MockCacheProviderForInvalidation:
    """Create a shared mock cache provider for invalidation tests."""
    return MockCacheProviderForInvalidation()
