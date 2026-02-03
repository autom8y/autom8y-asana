"""Unit tests for DataFrameCache orchestrator.

Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
Tests for tiered caching, cache validation, build lock management,
statistics, and entity-level TTL with SWR.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.dataframe_cache import (
    CacheEntry,
    DataFrameCache,
    FreshnessStatus,
    _get_schema_version_for_entity,
    get_dataframe_cache,
    reset_dataframe_cache,
    set_dataframe_cache,
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
        else MagicMock(),
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
        """Get returns None when circuit is open."""
        circuit = CircuitBreaker(failure_threshold=1)
        circuit.record_failure("proj-1")

        cache = make_cache(circuit_breaker=circuit)

        result = await cache.get_async("proj-1", "unit")

        assert result is None

        stats = cache.get_stats()
        assert stats["unit"]["circuit_breaks"] == 1

    @pytest.mark.asyncio
    async def test_get_expired_entry_rejected(self) -> None:
        """Get rejects entries beyond SWR grace window."""
        memory = MemoryTier(max_entries=100)
        # unit TTL=900s, grace=2700s. 24 hours old = far beyond grace.
        old_entry = make_entry(created_hours_ago=24)
        memory.put("unit:proj-1", old_entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        result = await cache.get_async("proj-1", "unit")

        assert result is None
        # Expired entry should be removed from memory
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
        circuit._circuits["proj-1"].last_failure = datetime.now(UTC) - timedelta(
            seconds=120
        )
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
    async def test_expired_entry_beyond_grace_returns_none(self) -> None:
        """Entry beyond SWR grace window is treated as cache miss."""
        memory = MemoryTier(max_entries=100)
        # unit TTL = 900s, grace = 2700s. Entry 3600s old → expired.
        entry = make_entry(entity_type="unit", created_seconds_ago=3600)
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)
        result = await cache.get_async("proj-1", "unit")

        assert result is None
        assert memory.get("unit:proj-1") is None

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
    async def test_offer_expired_beyond_grace(self) -> None:
        """Offer entity beyond 3x TTL (540s) returns None."""
        memory = MemoryTier(max_entries=100)
        # offer TTL = 180s, grace = 540s. Entry 600s old → expired.
        entry = make_entry(entity_type="offer", created_seconds_ago=600)
        memory.put("offer:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)
        result = await cache.get_async("proj-1", "offer")

        assert result is None

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

        # Expired: 3600s old, unit TTL = 900s, grace = 2700s
        expired_entry = make_entry(entity_type="unit", created_seconds_ago=3600)
        assert cache._check_freshness(expired_entry, None) == FreshnessStatus.EXPIRED

    def test_check_freshness_schema_mismatch_is_expired(self) -> None:
        """Schema mismatch always returns EXPIRED regardless of age."""
        cache = make_cache()
        entry = make_entry(entity_type="unit", schema_version="0.0.1")
        assert cache._check_freshness(entry, None) == FreshnessStatus.EXPIRED

    def test_check_freshness_stale_watermark_is_expired(self) -> None:
        """Stale watermark always returns EXPIRED regardless of age."""
        cache = make_cache()
        entry = make_entry(entity_type="unit", created_seconds_ago=0)
        future_watermark = datetime.now(UTC) + timedelta(minutes=5)
        assert (
            cache._check_freshness(entry, future_watermark) == FreshnessStatus.EXPIRED
        )


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
