"""Unit tests for DataFrameCache orchestrator.

Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
Tests for tiered caching, cache validation, build lock management,
statistics, and entity-level TTL with SWR.
"""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.factory import (
    get_dataframe_cache,
    reset_dataframe_cache,
    set_dataframe_cache,
)
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCache,
    FreshnessStatus,
    _get_schema_version_for_entity,
)
from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCacheEntry as CacheEntry,
)


def make_entry(
    project_gid: str = "proj-1",
    entity_type: str = "unit",
    schema_version: str | None = None,
    created_hours_ago: int = 0,
    created_seconds_ago: int | None = None,
) -> CacheEntry:
    """Create a test CacheEntry.

    If schema_version is not provided, looks up the correct version from
    SchemaRegistry to ensure test entries are valid by default.

    Args:
        created_seconds_ago: Fine-grained age control (takes precedence
            over created_hours_ago when provided).
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

    if created_seconds_ago is not None:
        age = timedelta(seconds=created_seconds_ago)
    else:
        age = timedelta(hours=created_hours_ago)

    return CacheEntry(
        project_gid=project_gid,
        entity_type=entity_type,
        dataframe=df,
        watermark=datetime.now(UTC),
        created_at=datetime.now(UTC) - age,
        schema_version=schema_version,
    )


def make_cache(
    memory_tier: MemoryTier | None = None,
    progressive_tier: MagicMock | None = None,
    coalescer: DataFrameCacheCoalescer | None = None,
    circuit_breaker: CircuitBreaker | None = None,
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
        else AsyncMock(),
        coalescer=coalescer if coalescer is not None else DataFrameCacheCoalescer(),
        circuit_breaker=circuit_breaker
        if circuit_breaker is not None
        else CircuitBreaker(),
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
        """Get returns None when circuit is open and no cached data exists."""
        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(circuit_breaker=circuit, progressive_tier=progressive_tier)

        result = await cache.get_async("proj-1", "unit")

        assert result is None

        stats = cache.get_stats()
        assert stats["unit"]["circuit_breaks"] == 1

    @pytest.mark.asyncio
    async def test_get_expired_entry_served_as_lkg(self) -> None:
        """Get serves entries beyond SWR grace window as LKG."""
        memory = MemoryTier(max_entries=100)
        # unit TTL=900s, grace=2700s. 24 hours old = far beyond grace, but LKG.
        old_entry = make_entry(created_hours_ago=24)
        memory.put("unit:proj-1", old_entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "unit")

        # Should be served as LKG
        assert result is old_entry
        # Should still be in memory
        assert memory.get("unit:proj-1") is old_entry
        # Should increment LKG stats
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 1

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
        current_watermark = datetime.now(UTC) + timedelta(minutes=5)
        result = await cache.get_async("proj-1", "unit", current_watermark)

        assert result is None

    @pytest.mark.asyncio
    async def test_put_writes_to_both_tiers(self) -> None:
        """Put writes to progressive tier first, then memory."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        df = pl.DataFrame({"gid": ["1"], "name": ["A"]})
        watermark = datetime.now(UTC)

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
        circuit._circuits["proj-1"].last_failure = time.monotonic() - 120
        circuit.is_open("proj-1")  # Triggers half-open

        progressive_tier = AsyncMock()
        cache = make_cache(progressive_tier=progressive_tier, circuit_breaker=circuit)

        df = pl.DataFrame({"gid": ["1"]})
        await cache.put_async("proj-1", "unit", df, datetime.now(UTC))

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


class TestEntityTTLAndSWR:
    """Tests for entity-level TTL enforcement and stale-while-revalidate."""

    @pytest.mark.asyncio
    async def test_fresh_entry_served_immediately(self) -> None:
        """Entry within entity TTL is served as fresh (no SWR triggered)."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s. Entry is 60s old → fresh.
        entry = make_entry(entity_type="unit", created_seconds_ago=60)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)
        result = await cache.get_async("proj-1", "unit")

        assert result is entry
        stats = cache.get_stats()
        assert stats["unit"]["memory_hits"] == 1
        assert stats["unit"]["swr_serves"] == 0

    @pytest.mark.asyncio
    async def test_stale_entry_within_grace_triggers_swr(self) -> None:
        """Entry past TTL but within grace window is served + SWR fires."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, grace = 2700s. Entry 1200s old → stale but servable.
        entry = make_entry(entity_type="unit", created_seconds_ago=1200)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch(
            "autom8_asana.cache.dataframe_cache.asyncio.create_task"
        ) as mock_task:
            result = await cache.get_async("proj-1", "unit")

        assert result is entry
        stats = cache.get_stats()
        assert stats["unit"]["swr_serves"] == 1
        assert stats["unit"]["swr_refreshes_triggered"] == 1
        mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_expired_entry_beyond_grace_served_as_lkg(self) -> None:
        """Entry beyond SWR grace window is served as LKG."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, grace = 2700s. Entry 3600s old → expired but LKG.
        entry = make_entry(entity_type="unit", created_seconds_ago=3600)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "unit")

        # Should be served as LKG
        assert result is entry
        # Should still be in memory
        assert memory.get("unit:proj-1") is entry
        # Should increment LKG stats
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 1

    @pytest.mark.asyncio
    async def test_offer_entity_ttl_respected(self) -> None:
        """Offer entity (TTL=180s) goes stale faster than unit (TTL=900s)."""
        memory = MemoryTier(max_entries=100)
        # offer TTL = 180s. Entry 200s old → stale (within grace 540s).
        entry = make_entry(entity_type="offer", created_seconds_ago=200)
        memory.put("offer:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "offer")

        assert result is entry
        stats = cache.get_stats()
        assert stats["offer"]["swr_serves"] == 1

    @pytest.mark.asyncio
    async def test_offer_expired_beyond_grace_served_as_lkg(self) -> None:
        """Offer entity beyond 3x TTL (540s) served as LKG."""
        memory = MemoryTier(max_entries=100)
        # offer TTL = 180s, grace = 540s. Entry 600s old → expired but LKG.
        entry = make_entry(entity_type="offer", created_seconds_ago=600)
        memory.put("offer:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "offer")

        # Should be served as LKG
        assert result is entry
        stats = cache.get_stats()
        assert stats["offer"]["lkg_serves"] == 1

    @pytest.mark.asyncio
    async def test_business_entity_ttl_respected(self) -> None:
        """Business entity (TTL=3600s) stays fresh for longer."""
        memory = MemoryTier(max_entries=100)
        # business TTL = 3600s. Entry 1800s old → still fresh.
        entry = make_entry(entity_type="business", created_seconds_ago=1800)
        memory.put("business:proj-1", entry)

        cache = make_cache(memory_tier=memory)
        result = await cache.get_async("proj-1", "business")

        assert result is entry
        stats = cache.get_stats()
        assert stats["business"]["swr_serves"] == 0

    @pytest.mark.asyncio
    async def test_swr_deduplicates_concurrent_refreshes(self) -> None:
        """Coalescer prevents duplicate SWR refreshes for same key."""
        memory = MemoryTier(max_entries=100)
        coalescer = DataFrameCacheCoalescer()
        # Simulate an in-progress build
        await coalescer.try_acquire_async("unit:proj-1")

        entry = make_entry(entity_type="unit", created_seconds_ago=1200)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory, coalescer=coalescer)

        with patch(
            "autom8_asana.cache.dataframe_cache.asyncio.create_task"
        ) as mock_task:
            result = await cache.get_async("proj-1", "unit")

        # Entry is still served (SWR)
        assert result is entry
        # But no new task is created (build already in progress)
        mock_task.assert_not_called()
        stats = cache.get_stats()
        assert stats["unit"]["swr_serves"] == 1
        assert stats["unit"]["swr_refreshes_triggered"] == 0

    @pytest.mark.asyncio
    async def test_swr_on_s3_tier_hydrates_memory(self) -> None:
        """SWR entry from S3 tier is served and hydrated to memory."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        # unit TTL = 900s, entry 1200s old → stale but servable from S3
        entry = make_entry(entity_type="unit", created_seconds_ago=1200)
        progressive_tier.get_async.return_value = entry

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "unit")

        assert result is entry
        # Should hydrate memory tier even for SWR entries
        assert memory.get("unit:proj-1") is entry

    def test_check_freshness_returns_correct_states(self) -> None:
        """_check_freshness returns correct FreshnessStatus for each age band."""
        cache = make_cache()

        # Fresh: 60s old, unit TTL = 900s
        fresh_entry = make_entry(entity_type="unit", created_seconds_ago=60)
        assert cache._check_freshness(fresh_entry, None) == FreshnessStatus.FRESH

        # Stale servable: 1200s old, unit TTL = 900s, grace = 2700s
        stale_entry = make_entry(entity_type="unit", created_seconds_ago=1200)
        assert (
            cache._check_freshness(stale_entry, None) == FreshnessStatus.STALE_SERVABLE
        )

        # Expired servable (LKG): 3600s old, unit TTL = 900s, grace = 2700s
        expired_entry = make_entry(entity_type="unit", created_seconds_ago=3600)
        assert (
            cache._check_freshness(expired_entry, None)
            == FreshnessStatus.EXPIRED_SERVABLE
        )

    def test_check_freshness_schema_mismatch_is_rejected(self) -> None:
        """Schema mismatch always returns SCHEMA_MISMATCH regardless of age."""
        cache = make_cache()
        entry = make_entry(entity_type="unit", schema_version="0.0.1")
        assert cache._check_freshness(entry, None) == FreshnessStatus.SCHEMA_MISMATCH

    def test_check_freshness_stale_watermark_is_rejected(self) -> None:
        """Stale watermark always returns WATERMARK_STALE regardless of age."""
        cache = make_cache()
        entry = make_entry(entity_type="unit", created_seconds_ago=0)
        future_watermark = datetime.now(UTC) + timedelta(minutes=5)
        assert (
            cache._check_freshness(entry, future_watermark)
            == FreshnessStatus.WATERMARK_STALE
        )


class TestLKGCacheFallback:
    """Tests for Last-Known-Good (LKG) cache fallback behavior."""

    @pytest.mark.asyncio
    async def test_lkg_serves_expired_entry(self) -> None:
        """Expired entry beyond grace window is served as LKG."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, grace = 2700s. Entry 4000s old → LKG.
        entry = make_entry(entity_type="unit", created_seconds_ago=4000)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "unit")

        # Should serve the entry
        assert result is entry
        # Should increment LKG stats
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 1
        assert stats["unit"]["memory_hits"] == 1

    @pytest.mark.asyncio
    async def test_schema_mismatch_never_served_lkg(self) -> None:
        """Schema mismatch entries are never served as LKG."""
        memory = MemoryTier(max_entries=100)
        # Wrong schema version, even if fresh
        entry = make_entry(entity_type="unit", schema_version="0.0.1")
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        result = await cache.get_async("proj-1", "unit")

        # Should NOT be served
        assert result is None
        # Should be removed from memory
        assert memory.get("unit:proj-1") is None
        # Should NOT increment LKG stats
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 0

    @pytest.mark.asyncio
    async def test_watermark_stale_never_served_lkg(self) -> None:
        """Watermark stale entries are never served as LKG."""
        memory = MemoryTier(max_entries=100)
        # Entry with old watermark
        entry = make_entry(entity_type="unit", created_seconds_ago=100)
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        # Pass a newer watermark to simulate source having newer data
        current_watermark = datetime.now(UTC) + timedelta(minutes=5)
        result = await cache.get_async("proj-1", "unit", current_watermark)

        # Should NOT be served
        assert result is None
        # Should be removed from memory
        assert memory.get("unit:proj-1") is None
        # Should NOT increment LKG stats
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 0

    @pytest.mark.asyncio
    async def test_lkg_triggers_swr_refresh(self) -> None:
        """LKG serve triggers SWR refresh in background."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(entity_type="unit", created_seconds_ago=4000)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch(
            "autom8_asana.cache.dataframe_cache.asyncio.create_task"
        ) as mock_task:
            result = await cache.get_async("proj-1", "unit")

        # Should serve entry
        assert result is entry
        # Should trigger background refresh
        mock_task.assert_called_once()
        # Should increment refresh triggered stat
        stats = cache.get_stats()
        assert stats["unit"]["swr_refreshes_triggered"] == 1

    @pytest.mark.asyncio
    async def test_lkg_stats_tracked(self) -> None:
        """LKG serves are tracked in statistics."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(entity_type="unit", created_seconds_ago=4000)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            # Serve LKG twice
            await cache.get_async("proj-1", "unit")
            await cache.get_async("proj-1", "unit")

        stats = cache.get_stats()
        # Should have 2 LKG serves
        assert stats["unit"]["lkg_serves"] == 2
        # Should have 2 memory hits
        assert stats["unit"]["memory_hits"] == 2
        # SWR refresh triggered twice (no build in progress to coalese with mock)
        assert stats["unit"]["swr_refreshes_triggered"] == 2

    @pytest.mark.asyncio
    async def test_lkg_from_s3_tier(self) -> None:
        """LKG entry from S3 tier is served and hydrated to memory."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        # Expired entry from S3
        entry = make_entry(entity_type="unit", created_seconds_ago=4000)
        progressive_tier.get_async.return_value = entry

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "unit")

        # Should serve entry
        assert result is entry
        # Should hydrate memory
        assert memory.get("unit:proj-1") is entry
        # Should track LKG serve
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 1
        assert stats["unit"]["s3_hits"] == 1


class TestSWRCallbackWiring:
    """Tests that factory wires the SWR build callback onto the cache."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_dataframe_cache()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_dataframe_cache()

    @patch("autom8_asana.settings.get_settings")
    def test_initialize_registers_build_callback(
        self, mock_settings: MagicMock
    ) -> None:
        """After initialize_dataframe_cache(), _build_callback is not None."""
        from autom8_asana.cache.dataframe.factory import initialize_dataframe_cache

        # Configure mock settings with S3 bucket so factory doesn't return None
        mock_s3 = MagicMock()
        mock_s3.bucket = "test-bucket"
        mock_s3.region = "us-east-1"
        mock_s3.endpoint_url = None
        mock_settings.return_value.s3 = mock_s3

        mock_cache_settings = MagicMock()
        mock_cache_settings.dataframe_heap_percent = 0.3
        mock_cache_settings.dataframe_max_entries = 100
        mock_settings.return_value.cache = mock_cache_settings

        cache = initialize_dataframe_cache()

        assert cache is not None
        assert cache._build_callback is not None


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


class TestCircuitBreakerLKG:
    """Tests for circuit breaker LKG serving behavior."""

    @pytest.mark.asyncio
    async def test_circuit_open_serves_valid_memory_entry(self) -> None:
        """Circuit open with valid cached entry in memory serves it."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry()
        memory.put("unit:proj-1", entry)

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(memory_tier=memory, circuit_breaker=circuit)

        result = await cache.get_async("proj-1", "unit")

        assert result is entry
        stats = cache.get_stats()
        assert stats["unit"]["lkg_circuit_serves"] == 1
        assert stats["unit"]["memory_hits"] == 1

    @pytest.mark.asyncio
    async def test_circuit_open_serves_valid_s3_entry(self) -> None:
        """Circuit open, memory miss, S3 hit with valid schema serves and hydrates."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        entry = make_entry()
        progressive_tier.get_async.return_value = entry

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            circuit_breaker=circuit,
        )

        result = await cache.get_async("proj-1", "unit")

        assert result is entry
        # Should hydrate memory tier
        assert memory.get("unit:proj-1") is entry
        stats = cache.get_stats()
        assert stats["unit"]["lkg_circuit_serves"] == 1
        assert stats["unit"]["s3_hits"] == 1

    @pytest.mark.asyncio
    async def test_circuit_open_rejects_schema_mismatch(self) -> None:
        """Circuit open with schema-mismatched entry returns None."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(schema_version="0.0.1")
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            circuit_breaker=circuit,
        )

        result = await cache.get_async("proj-1", "unit")

        assert result is None

    @pytest.mark.asyncio
    async def test_circuit_open_no_data_returns_none(self) -> None:
        """Circuit open with no data in any tier returns None."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            circuit_breaker=circuit,
        )

        result = await cache.get_async("proj-1", "unit")

        assert result is None
        stats = cache.get_stats()
        assert stats["unit"]["circuit_breaks"] == 1

    @pytest.mark.asyncio
    async def test_circuit_open_no_refresh_triggered(self) -> None:
        """Circuit open serve does NOT trigger SWR refresh."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry()
        memory.put("unit:proj-1", entry)

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(memory_tier=memory, circuit_breaker=circuit)

        with patch(
            "autom8_asana.cache.dataframe_cache.asyncio.create_task"
        ) as mock_task:
            result = await cache.get_async("proj-1", "unit")

        assert result is entry
        mock_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_open_tracks_lkg_circuit_serves_stat(self) -> None:
        """Circuit open with valid entry increments lkg_circuit_serves stat."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry()
        memory.put("unit:proj-1", entry)

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(memory_tier=memory, circuit_breaker=circuit)

        await cache.get_async("proj-1", "unit")

        stats = cache.get_stats()
        assert stats["unit"]["lkg_circuit_serves"] == 1


class TestMaxStalenessEnforcement:
    """Tests for LKG_MAX_STALENESS_MULTIPLIER enforcement."""

    @pytest.mark.asyncio
    async def test_max_staleness_zero_serves_unlimited(self) -> None:
        """With LKG_MAX_STALENESS_MULTIPLIER=0.0 (default), very old entry is served."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s. Entry is 24 hours old (86400s) = 96x TTL
        entry = make_entry(entity_type="unit", created_hours_ago=24)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            result = await cache.get_async("proj-1", "unit")

        assert result is entry

    @pytest.mark.asyncio
    async def test_max_staleness_within_limit_served(self) -> None:
        """With multiplier=10.0, entry aged at 8x TTL is served."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s. Entry 7200s old = 8x TTL. Multiplier=10 -> max=9000s.
        entry = make_entry(entity_type="unit", created_seconds_ago=7200)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        with patch("autom8_asana.config.LKG_MAX_STALENESS_MULTIPLIER", 10.0):
            with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
                result = await cache.get_async("proj-1", "unit")

        assert result is entry
        stats = cache.get_stats()
        assert stats["unit"]["lkg_serves"] == 1

    @pytest.mark.asyncio
    async def test_max_staleness_exceeded_rejected(self) -> None:
        """With multiplier=5.0, entry aged at 6x TTL is rejected."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None
        # unit TTL = 900s. Entry 5400s old = 6x TTL. Multiplier=5 -> max=4500s.
        entry = make_entry(entity_type="unit", created_seconds_ago=5400)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        with patch("autom8_asana.config.LKG_MAX_STALENESS_MULTIPLIER", 5.0):
            result = await cache.get_async("proj-1", "unit")

        assert result is None

    @pytest.mark.asyncio
    async def test_max_staleness_evicts_from_memory(self) -> None:
        """Rejected entry is removed from memory tier."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None
        # unit TTL = 900s. Entry 5400s old = 6x TTL. Multiplier=5 -> max=4500s.
        entry = make_entry(entity_type="unit", created_seconds_ago=5400)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        with patch("autom8_asana.config.LKG_MAX_STALENESS_MULTIPLIER", 5.0):
            await cache.get_async("proj-1", "unit")

        # Should be evicted from memory
        assert memory.get("unit:proj-1") is None

    @pytest.mark.asyncio
    async def test_max_staleness_not_applied_to_fresh_or_swr(self) -> None:
        """Fresh and SWR entries not affected by staleness cap."""
        memory = MemoryTier(max_entries=100)

        # Fresh entry: 60s old, unit TTL = 900s
        fresh_entry = make_entry(entity_type="unit", created_seconds_ago=60)
        memory.put("unit:proj-fresh", fresh_entry)

        # SWR entry: 1200s old, unit TTL = 900s, grace = 2700s
        swr_entry = make_entry(
            entity_type="unit",
            project_gid="proj-swr",
            created_seconds_ago=1200,
        )
        memory.put("unit:proj-swr", swr_entry)

        cache = make_cache(memory_tier=memory)

        # With a very restrictive multiplier (1.0 = only serve up to 1x TTL)
        with patch("autom8_asana.config.LKG_MAX_STALENESS_MULTIPLIER", 1.0):
            fresh_result = await cache.get_async("proj-fresh", "unit")
            with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
                swr_result = await cache.get_async("proj-swr", "unit")

        # Both should still be served (staleness cap only applies to EXPIRED_SERVABLE)
        assert fresh_result is fresh_entry
        assert swr_result is swr_entry


class TestSchemaIsValid:
    """Tests for the _schema_is_valid() helper method."""

    def test_schema_is_valid_matching_version(self) -> None:
        """Entry with matching schema returns True."""
        cache = make_cache()
        entry = make_entry(entity_type="unit")  # Uses registry version by default
        assert cache._schema_is_valid(entry) is True

    def test_schema_is_valid_mismatched_version(self) -> None:
        """Entry with wrong schema returns False."""
        cache = make_cache()
        entry = make_entry(entity_type="unit", schema_version="0.0.1")
        assert cache._schema_is_valid(entry) is False

    def test_schema_is_valid_registry_lookup_fails(self) -> None:
        """_schema_is_valid returns False when registry lookup fails."""
        cache = make_cache()
        entry = make_entry(entity_type="unit")

        with patch(
            "autom8_asana.cache.dataframe_cache._get_schema_version_for_entity",
            return_value=None,
        ):
            assert cache._schema_is_valid(entry) is False


class TestFreshnessInfoSideChannel:
    """Tests for FreshnessInfo side-channel storage."""

    @pytest.mark.asyncio
    async def test_freshness_info_stored_on_fresh_hit(self) -> None:
        """Fresh entry produces FreshnessInfo with freshness='fresh'."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, entry 60s old -> fresh
        entry = make_entry(entity_type="unit", created_seconds_ago=60)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)
        await cache.get_async("proj-1", "unit")

        info = cache.get_freshness_info("proj-1", "unit")
        assert info is not None
        assert info.freshness == "fresh"
        assert info.staleness_ratio < 1.0
        assert info.data_age_seconds >= 59.0  # Allow for small timing variance

    @pytest.mark.asyncio
    async def test_freshness_info_stored_on_stale_serve(self) -> None:
        """Stale entry produces FreshnessInfo with freshness='stale_servable'."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, entry 1200s old -> stale servable
        entry = make_entry(entity_type="unit", created_seconds_ago=1200)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)
        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            await cache.get_async("proj-1", "unit")

        info = cache.get_freshness_info("proj-1", "unit")
        assert info is not None
        assert info.freshness == "stale_servable"
        assert info.staleness_ratio > 1.0

    @pytest.mark.asyncio
    async def test_freshness_info_stored_on_lkg_serve(self) -> None:
        """LKG entry produces FreshnessInfo with freshness='expired_servable'."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, grace = 2700s, entry 3600s old -> expired servable
        entry = make_entry(entity_type="unit", created_seconds_ago=3600)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)
        with patch("autom8_asana.cache.dataframe_cache.asyncio.create_task"):
            await cache.get_async("proj-1", "unit")

        info = cache.get_freshness_info("proj-1", "unit")
        assert info is not None
        assert info.freshness == "expired_servable"
        assert info.staleness_ratio > 1.0

    @pytest.mark.asyncio
    async def test_freshness_info_not_stored_on_schema_reject(self) -> None:
        """Schema mismatch does NOT populate FreshnessInfo."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(entity_type="unit", schema_version="0.0.1")
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)
        await cache.get_async("proj-1", "unit")

        info = cache.get_freshness_info("proj-1", "unit")
        assert info is None

    def test_get_freshness_info_returns_none_on_miss(self) -> None:
        """get_freshness_info returns None for a key never accessed."""
        cache = make_cache()
        info = cache.get_freshness_info("nonexistent", "unit")
        assert info is None

    @pytest.mark.asyncio
    async def test_freshness_info_stored_on_circuit_lkg(self) -> None:
        """Circuit breaker LKG serve stores FreshnessInfo with freshness='circuit_lkg'."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(entity_type="unit", created_seconds_ago=60)
        memory.put("unit:proj-1", entry)

        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(memory_tier=memory, circuit_breaker=circuit)
        await cache.get_async("proj-1", "unit")

        info = cache.get_freshness_info("proj-1", "unit")
        assert info is not None
        assert info.freshness == "circuit_lkg"
        assert info.data_age_seconds >= 59.0


class TestSWRBuildLockRelease:
    """Tests for SWR refresh build lock release guarantees.

    Per TDD-WS2 Section 4.2/4.4: The build lock must be released
    even when the build callback raises an unexpected error.
    """

    @pytest.mark.asyncio
    async def test_swr_build_lock_released_on_callback_error(self) -> None:
        """Build lock is released when build callback raises an error.

        Per TDD-WS2 Section 4.4 Hardening Item 1: Uses try/finally
        to guarantee release_build_lock_async is always called.
        """
        coalescer = DataFrameCacheCoalescer()
        cache = make_cache(coalescer=coalescer)

        # Register a callback that raises
        async def failing_callback(project_gid: str, entity_type: str) -> None:
            raise ConnectionError("build failed unexpectedly")

        cache.set_build_callback(failing_callback)

        # Run the SWR refresh directly
        await cache._swr_refresh_async("proj-1", "unit")

        # The build lock should be released (not leaked).
        # Verify by acquiring it again -- if leaked, this would return False.
        acquired = await coalescer.try_acquire_async("unit:proj-1")
        assert acquired is True, "Build lock was not released after callback error"

    @pytest.mark.asyncio
    async def test_swr_build_lock_released_on_success(self) -> None:
        """Build lock is released on successful callback execution."""
        coalescer = DataFrameCacheCoalescer()
        cache = make_cache(coalescer=coalescer)

        # Register a callback that succeeds
        callback_called = False

        async def success_callback(project_gid: str, entity_type: str) -> None:
            nonlocal callback_called
            callback_called = True

        cache.set_build_callback(success_callback)

        await cache._swr_refresh_async("proj-1", "unit")

        assert callback_called
        # The build lock should be released
        acquired = await coalescer.try_acquire_async("unit:proj-1")
        assert acquired is True, "Build lock was not released after success"

    @pytest.mark.asyncio
    async def test_swr_build_lock_released_on_no_callback(self) -> None:
        """Build lock is released when no callback is registered."""
        coalescer = DataFrameCacheCoalescer()
        cache = make_cache(coalescer=coalescer)

        # No callback registered (default)
        await cache._swr_refresh_async("proj-1", "unit")

        # The build lock should be released
        acquired = await coalescer.try_acquire_async("unit:proj-1")
        assert acquired is True, "Build lock was not released when no callback set"

    @pytest.mark.asyncio
    async def test_swr_circuit_breaker_records_failure_on_error(self) -> None:
        """Circuit breaker records failure when build callback raises."""
        circuit = CircuitBreaker(failure_threshold=1)
        coalescer = DataFrameCacheCoalescer()
        cache = make_cache(coalescer=coalescer, circuit_breaker=circuit)

        async def failing_callback(project_gid: str, entity_type: str) -> None:
            raise ConnectionError("build failed")

        cache.set_build_callback(failing_callback)

        await cache._swr_refresh_async("proj-1", "unit")

        # Circuit breaker should have recorded the failure
        assert circuit.is_open("proj-1")
