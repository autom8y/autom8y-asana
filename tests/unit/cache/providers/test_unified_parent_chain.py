"""Tests for gap-tolerant parent chain in UnifiedTaskStore.

Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: Validates that get_parent_chain_async
skips missing ancestors instead of breaking at the first gap.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.providers.unified import UnifiedTaskStore


@pytest.fixture
def mock_cache_provider() -> MagicMock:
    """Create a mock CacheProvider."""
    provider = MagicMock()
    provider.get_versioned = MagicMock(return_value=None)
    provider.set_versioned = MagicMock()
    provider.get_batch = MagicMock(return_value={})
    provider.set_batch = MagicMock()
    provider.invalidate = MagicMock()
    return provider


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client


@pytest.fixture
def store(mock_cache_provider: MagicMock, mock_batch_client: MagicMock) -> UnifiedTaskStore:
    """Create a UnifiedTaskStore with mocks."""
    return UnifiedTaskStore(
        cache=mock_cache_provider,
        batch_client=mock_batch_client,
        freshness_mode=FreshnessIntent.EVENTUAL,
    )


def _make_entry(gid: str, name: str | None = None) -> CacheEntry:
    """Create a CacheEntry for testing."""
    version = datetime(2025, 12, 23, 10, 0, 0, tzinfo=UTC)
    cached_at = datetime.now(UTC)
    return CacheEntry(
        key=gid,
        data={
            "gid": gid,
            "name": name or f"Task {gid}",
            "modified_at": "2025-12-23T10:00:00.000Z",
        },
        entry_type=EntryType.TASK,
        version=version,
        cached_at=cached_at,
        ttl=300,
        metadata={"completeness_level": 20},
    )


def _register_chain(store: UnifiedTaskStore, chain: list[tuple[str, str]]) -> None:
    """Register parent-child relationships in the hierarchy index.

    Args:
        store: UnifiedTaskStore whose hierarchy index to populate.
        chain: List of (child_gid, parent_gid) tuples.
    """
    for child_gid, parent_gid in chain:
        store._hierarchy.register({"gid": child_gid, "parent": {"gid": parent_gid}})


class TestParentChainGapTolerance:
    """Tests for gap-tolerant parent chain traversal.

    Per TDD-CASCADE-FAILURE-FIXES-001 Fix 2: When get_parent_chain_async
    encounters a missing ancestor, it should skip the gap and continue
    collecting remaining ancestors.
    """

    @pytest.mark.asyncio
    async def test_parent_chain_skips_gap_returns_remaining(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Chain A->B->C with B missing returns [A, C]."""
        # Set up hierarchy: task-1 -> A -> B -> C
        _register_chain(
            store,
            [
                ("task-1", "A"),
                ("A", "B"),
                ("B", "C"),
            ],
        )

        entry_a = _make_entry("A", "Holder A")
        entry_c = _make_entry("C", "Business C")

        # B is missing from cache; A and C are present
        mock_cache_provider.get_batch.return_value = {
            "A": entry_a,
            "C": entry_c,
        }

        chain = await store.get_parent_chain_async("task-1")

        assert len(chain) == 2
        assert chain[0]["gid"] == "A"
        assert chain[1]["gid"] == "C"

    @pytest.mark.asyncio
    async def test_parent_chain_no_gaps_unchanged_behavior(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """All ancestors cached returns full chain [A, B, C]."""
        _register_chain(
            store,
            [
                ("task-1", "A"),
                ("A", "B"),
                ("B", "C"),
            ],
        )

        entry_a = _make_entry("A")
        entry_b = _make_entry("B")
        entry_c = _make_entry("C")

        mock_cache_provider.get_batch.return_value = {
            "A": entry_a,
            "B": entry_b,
            "C": entry_c,
        }

        chain = await store.get_parent_chain_async("task-1")

        assert len(chain) == 3
        assert chain[0]["gid"] == "A"
        assert chain[1]["gid"] == "B"
        assert chain[2]["gid"] == "C"

    @pytest.mark.asyncio
    async def test_parent_chain_all_missing_returns_empty(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """No ancestors cached returns empty chain."""
        _register_chain(
            store,
            [
                ("task-1", "A"),
                ("A", "B"),
                ("B", "C"),
            ],
        )

        # All missing from cache
        mock_cache_provider.get_batch.return_value = {}

        chain = await store.get_parent_chain_async("task-1")

        assert chain == []

    @pytest.mark.asyncio
    async def test_parent_chain_gap_logged_at_info(
        self,
        store: UnifiedTaskStore,
        mock_cache_provider: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Gaps produce an INFO-level log with gap GIDs.

        autom8y_log writes structured JSON to stdout, so we capture stdout
        and verify the log event content.
        """
        _register_chain(
            store,
            [
                ("task-1", "A"),
                ("A", "B"),
                ("B", "C"),
            ],
        )

        entry_a = _make_entry("A")
        # B and C missing
        mock_cache_provider.get_batch.return_value = {"A": entry_a}

        await store.get_parent_chain_async("task-1")

        captured = capsys.readouterr()
        # Verify log output contains the event at info level
        assert "parent_chain_gaps_skipped" in captured.out
        assert "info" in captured.out
        assert "task-1" in captured.out
        assert "found_count" in captured.out

    @pytest.mark.asyncio
    async def test_parent_chain_gap_stat_counter_incremented(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Gap count is tracked in stats."""
        _register_chain(
            store,
            [
                ("task-1", "A"),
                ("A", "B"),
                ("B", "C"),
            ],
        )

        entry_c = _make_entry("C")
        # A and B missing
        mock_cache_provider.get_batch.return_value = {"C": entry_c}

        await store.get_parent_chain_async("task-1")

        stats = store.get_stats()
        assert stats["parent_chain_gaps"] == 2

    @pytest.mark.asyncio
    async def test_parent_chain_gap_stat_accumulates_across_calls(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Gap stat counter accumulates across multiple calls."""
        _register_chain(
            store,
            [
                ("task-1", "A"),
                ("A", "B"),
            ],
        )

        # First call: A missing (1 gap)
        mock_cache_provider.get_batch.return_value = {"B": _make_entry("B")}
        await store.get_parent_chain_async("task-1")

        # Second call: same setup (1 more gap)
        await store.get_parent_chain_async("task-1")

        stats = store.get_stats()
        assert stats["parent_chain_gaps"] == 2
