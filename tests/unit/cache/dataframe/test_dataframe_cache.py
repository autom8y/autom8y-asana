"""Unit tests for DataFrameCache orchestrator.

Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
Tests for tiered caching, cache validation, build lock management,
and statistics.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.cache.dataframe_cache import (
    CacheEntry,
    DataFrameCache,
    _get_schema_version_for_entity,
    get_dataframe_cache,
    reset_dataframe_cache,
    set_dataframe_cache,
)
from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier


def make_entry(
    project_gid: str = "proj-1",
    entity_type: str = "unit",
    schema_version: str | None = None,
    created_hours_ago: int = 0,
) -> CacheEntry:
    """Create a test CacheEntry.

    If schema_version is not provided, looks up the correct version from
    SchemaRegistry to ensure test entries are valid by default.
    """
    df = pl.DataFrame(
        {
            "gid": ["gid-1", "gid-2"],
            "name": ["A", "B"],
        }
    )

    # Default to registry version if not explicitly provided
    if schema_version is None:
        schema_version = _get_schema_version_for_entity(entity_type) or "1.0.0"

    return CacheEntry(
        project_gid=project_gid,
        entity_type=entity_type,
        dataframe=df,
        watermark=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc) - timedelta(hours=created_hours_ago),
        schema_version=schema_version,
    )


def make_cache(
    memory_tier: MemoryTier | None = None,
    progressive_tier: MagicMock | None = None,
    coalescer: DataFrameCacheCoalescer | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    ttl_hours: int = 12,
    schema_version: str = "1.0.0",
) -> DataFrameCache:
    """Create a DataFrameCache with mocked dependencies.

    Note: Uses explicit None checks because MemoryTier.__len__ returns 0
    for empty cache, making it falsy in boolean context.
    """
    return DataFrameCache(
        memory_tier=memory_tier
        if memory_tier is not None
        else MemoryTier(max_entries=100),
        progressive_tier=progressive_tier
        if progressive_tier is not None
        else MagicMock(),
        coalescer=coalescer if coalescer is not None else DataFrameCacheCoalescer(),
        circuit_breaker=circuit_breaker
        if circuit_breaker is not None
        else CircuitBreaker(),
        ttl_hours=ttl_hours,
        schema_version=schema_version,
    )


class TestDataFrameCache:
    """Tests for DataFrameCache orchestrator."""

    @pytest.mark.asyncio
    async def test_get_memory_hit(self) -> None:
        """Get returns entry from memory tier."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry()
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        result = await cache.get_async("proj-1", "unit")

        assert result is not None
        assert result.project_gid == "proj-1"

        stats = cache.get_stats()
        assert stats["unit"]["memory_hits"] == 1

    @pytest.mark.asyncio
    async def test_get_memory_miss_progressive_hit(self) -> None:
        """Get falls back to progressive tier on memory miss."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        entry = make_entry()
        progressive_tier.get_async.return_value = entry

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        result = await cache.get_async("proj-1", "unit")

        assert result is not None
        assert result.project_gid == "proj-1"

        # Should hydrate memory tier
        assert memory.get("unit:proj-1") is not None

        stats = cache.get_stats()
        assert stats["unit"]["memory_misses"] == 1
        assert stats["unit"]["s3_hits"] == 1

    @pytest.mark.asyncio
    async def test_get_both_miss(self) -> None:
        """Get returns None when both tiers miss."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        result = await cache.get_async("proj-1", "unit")

        assert result is None

        stats = cache.get_stats()
        assert stats["unit"]["memory_misses"] == 1
        assert stats["unit"]["s3_misses"] == 1

    @pytest.mark.asyncio
    async def test_get_circuit_open(self) -> None:
        """Get returns None when circuit is open."""
        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(circuit_breaker=circuit)

        result = await cache.get_async("proj-1", "unit")

        assert result is None

        stats = cache.get_stats()
        assert stats["unit"]["circuit_breaks"] == 1

    @pytest.mark.asyncio
    async def test_get_stale_entry_rejected(self) -> None:
        """Get rejects stale entries from memory."""
        memory = MemoryTier(max_entries=100)
        old_entry = make_entry(created_hours_ago=24)
        memory.put("unit:proj-1", old_entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(
            memory_tier=memory, progressive_tier=progressive_tier, ttl_hours=12
        )

        result = await cache.get_async("proj-1", "unit")

        assert result is None
        # Stale entry should be removed from memory
        assert memory.get("unit:proj-1") is None

    @pytest.mark.asyncio
    async def test_get_wrong_schema_version_rejected(self) -> None:
        """Get rejects entries with wrong schema version."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(schema_version="0.9.0")
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            schema_version="1.0.0",
        )

        result = await cache.get_async("proj-1", "unit")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stale_watermark_rejected(self) -> None:
        """Get rejects entries with stale watermark."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry()
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        # Pass a newer watermark
        current_watermark = datetime.now(timezone.utc) + timedelta(minutes=5)
        result = await cache.get_async("proj-1", "unit", current_watermark)

        assert result is None

    @pytest.mark.asyncio
    async def test_put_writes_to_both_tiers(self) -> None:
        """Put writes to progressive tier first, then memory."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        df = pl.DataFrame({"gid": ["1"], "name": ["A"]})
        watermark = datetime.now(timezone.utc)

        await cache.put_async("proj-1", "unit", df, watermark)

        # Progressive tier should be called first
        progressive_tier.put_async.assert_called_once()

        # Memory should also have entry
        assert memory.get("unit:proj-1") is not None

    @pytest.mark.asyncio
    async def test_put_clears_circuit_breaker(self) -> None:
        """Put clears circuit breaker on success."""
        circuit = CircuitBreaker(failure_threshold=2)
        circuit.record_failure("proj-1")
        circuit.record_failure("proj-1")

        # Simulate timeout so circuit is half-open
        circuit._circuits["proj-1"].last_failure = datetime.now(
            timezone.utc
        ) - timedelta(seconds=120)
        circuit.is_open("proj-1")  # Triggers half-open

        progressive_tier = AsyncMock()
        cache = make_cache(progressive_tier=progressive_tier, circuit_breaker=circuit)

        df = pl.DataFrame({"gid": ["1"]})
        await cache.put_async("proj-1", "unit", df, datetime.now(timezone.utc))

        # Circuit should be closed
        from autom8_asana.cache.dataframe.circuit_breaker import CircuitState

        assert circuit.get_state("proj-1") == CircuitState.CLOSED

    def test_invalidate_removes_from_memory(self) -> None:
        """Invalidate removes entry from memory tier."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry()
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        cache.invalidate("proj-1", "unit")

        assert memory.get("unit:proj-1") is None

        stats = cache.get_stats()
        assert stats["unit"]["invalidations"] == 1

    def test_invalidate_all_entity_types(self) -> None:
        """Invalidate without entity_type removes all types."""
        memory = MemoryTier(max_entries=100)
        memory.put("unit:proj-1", make_entry(entity_type="unit"))
        memory.put("offer:proj-1", make_entry(entity_type="offer"))
        memory.put("contact:proj-1", make_entry(entity_type="contact"))

        cache = make_cache(memory_tier=memory)

        cache.invalidate("proj-1")

        assert memory.get("unit:proj-1") is None
        assert memory.get("offer:proj-1") is None
        assert memory.get("contact:proj-1") is None

    def test_invalidate_on_schema_change(self) -> None:
        """Schema change clears all memory entries."""
        memory = MemoryTier(max_entries=100)
        memory.put("unit:proj-1", make_entry())
        memory.put("unit:proj-2", make_entry(project_gid="proj-2"))

        cache = make_cache(memory_tier=memory, schema_version="1.0.0")

        cache.invalidate_on_schema_change("2.0.0")

        assert len(memory) == 0
        assert cache.schema_version == "2.0.0"

    def test_invalidate_on_same_schema_no_op(self) -> None:
        """Same schema version does not clear entries."""
        memory = MemoryTier(max_entries=100)
        memory.put("unit:proj-1", make_entry())

        cache = make_cache(memory_tier=memory, schema_version="1.0.0")

        cache.invalidate_on_schema_change("1.0.0")

        assert len(memory) == 1

    @pytest.mark.asyncio
    async def test_acquire_build_lock(self) -> None:
        """Acquire build lock delegates to coalescer."""
        coalescer = DataFrameCacheCoalescer()
        cache = make_cache(coalescer=coalescer)

        acquired = await cache.acquire_build_lock_async("proj-1", "unit")

        assert acquired is True

        stats = cache.get_stats()
        assert stats["unit"]["builds_triggered"] == 1

    @pytest.mark.asyncio
    async def test_release_build_lock_failure_records_circuit(self) -> None:
        """Release with failure records circuit breaker failure."""
        circuit = CircuitBreaker(failure_threshold=1)
        coalescer = DataFrameCacheCoalescer()

        cache = make_cache(coalescer=coalescer, circuit_breaker=circuit)

        await cache.acquire_build_lock_async("proj-1", "unit")
        await cache.release_build_lock_async("proj-1", "unit", success=False)

        assert circuit.is_open("proj-1")

    def test_reset_stats(self) -> None:
        """Reset stats clears all statistics."""
        cache = make_cache()
        cache._stats["unit"]["memory_hits"] = 10

        cache.reset_stats()

        assert cache._stats["unit"]["memory_hits"] == 0


class TestDataFrameCacheSingleton:
    """Tests for singleton access functions."""

    def test_initial_state_is_none(self) -> None:
        """Initial singleton state is None."""
        reset_dataframe_cache()

        assert get_dataframe_cache() is None

    def test_set_and_get(self) -> None:
        """Set and get singleton."""
        reset_dataframe_cache()

        cache = make_cache()
        set_dataframe_cache(cache)

        assert get_dataframe_cache() is cache

        reset_dataframe_cache()

    def test_reset_clears_singleton(self) -> None:
        """Reset clears singleton."""
        cache = make_cache()
        set_dataframe_cache(cache)

        reset_dataframe_cache()

        assert get_dataframe_cache() is None
