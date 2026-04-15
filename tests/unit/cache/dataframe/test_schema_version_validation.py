"""Unit tests for DataFrameCache schema version validation using SchemaRegistry.

Per TDD-unit-cascade-resolution-fix: Tests that schema version validation
uses SchemaRegistry lookup per entity type, not a hardcoded cache-level version.

This prevents stale cache hits when entity schemas are bumped independently
(e.g., UNIT_SCHEMA bumped while cache was initialized with an older version).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCache,
    _get_schema_version_for_entity,
)
from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCacheEntry as CacheEntry,
)
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA


def make_entry(
    project_gid: str = "proj-1",
    entity_type: str = "unit",
    schema_version: str = "1.0.0",
    created_hours_ago: int = 0,
) -> CacheEntry:
    """Create a test CacheEntry."""
    df = pl.DataFrame(
        {
            "gid": ["gid-1", "gid-2"],
            "name": ["A", "B"],
        }
    )

    return CacheEntry(
        project_gid=project_gid,
        entity_type=entity_type,
        dataframe=df,
        watermark=datetime.now(UTC),
        created_at=datetime.now(UTC) - timedelta(hours=created_hours_ago),
        schema_version=schema_version,
    )


def make_cache(
    memory_tier: MemoryTier | None = None,
    progressive_tier: MagicMock | None = None,
    coalescer: DataFrameCacheCoalescer | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    schema_version: str = "1.0.0",
) -> DataFrameCache:
    """Create a DataFrameCache with mocked dependencies."""
    return DataFrameCache(
        memory_tier=memory_tier if memory_tier is not None else MemoryTier(max_entries=100),
        progressive_tier=progressive_tier if progressive_tier is not None else MagicMock(),
        coalescer=coalescer if coalescer is not None else DataFrameCacheCoalescer(),
        circuit_breaker=circuit_breaker if circuit_breaker is not None else CircuitBreaker(),
        schema_version=schema_version,
    )


class TestSchemaVersionLookup:
    """Tests for _get_schema_version_for_entity helper."""

    def test_lookup_unit_schema_version(self) -> None:
        """Lookup returns UNIT_SCHEMA version dynamically."""
        version = _get_schema_version_for_entity("unit")

        assert version == UNIT_SCHEMA.version

    def test_lookup_contact_schema_version(self) -> None:
        """Lookup returns CONTACT_SCHEMA version."""
        version = _get_schema_version_for_entity("contact")

        assert version is not None
        # Contact schema should be at 1.0.0 or its current version
        assert isinstance(version, str)

    def test_lookup_offer_schema_version(self) -> None:
        """Lookup returns OFFER_SCHEMA version."""
        version = _get_schema_version_for_entity("offer")

        assert version is not None
        assert isinstance(version, str)

    def test_lookup_unknown_entity_type_returns_base(self) -> None:
        """Unknown entity type falls back to base schema version."""
        # "Unknown" will title() to "Unknown", which falls back to "*" (base)
        version = _get_schema_version_for_entity("unknown")

        # Base schema is at 1.1.0 (parent_gid column added for hierarchy reconstruction)
        assert version == "1.1.0"

    def test_lookup_handles_registry_failure_gracefully(self) -> None:
        """Registry failure returns None instead of raising."""
        with patch(
            "autom8_asana.dataframes.models.registry.SchemaRegistry.get_instance"
        ) as mock_registry:
            mock_registry.side_effect = RuntimeError("Registry unavailable")

            version = _get_schema_version_for_entity("unit")

            assert version is None


class TestSchemaVersionValidation:
    """Tests for _check_freshness() using SchemaRegistry lookup."""

    async def test_entry_valid_when_version_matches_registry(self) -> None:
        """Entry is valid when its version matches registry version."""
        memory = MemoryTier(max_entries=100)
        # Create entry with version matching current UNIT_SCHEMA
        entry = make_entry(entity_type="unit", schema_version=UNIT_SCHEMA.version)
        memory.put("unit:proj-1", entry)

        cache = make_cache(memory_tier=memory)

        result = await cache.get_async("proj-1", "unit")

        assert result is not None
        assert result.schema_version == UNIT_SCHEMA.version

    async def test_entry_invalid_when_version_older_than_registry(self) -> None:
        """Entry is invalid when its version is older than registry version.

        This is the root cause bug fix: cache entries stamped with 1.0.0
        should be rejected when UNIT_SCHEMA is at 1.1.0.
        """
        memory = MemoryTier(max_entries=100)
        # Create entry with old version (1.0.0) but UNIT_SCHEMA is at 1.1.0
        entry = make_entry(entity_type="unit", schema_version="1.0.0")
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        result = await cache.get_async("proj-1", "unit")

        # Should reject the stale entry
        assert result is None

    async def test_entry_invalid_when_registry_lookup_fails(self) -> None:
        """Entry is invalid when registry lookup fails (defensive)."""
        memory = MemoryTier(max_entries=100)
        entry = make_entry(entity_type="unit", schema_version=UNIT_SCHEMA.version)
        memory.put("unit:proj-1", entry)

        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        with patch(
            "autom8_asana.cache.integration.dataframe_cache._get_schema_version_for_entity"
        ) as mock_lookup:
            mock_lookup.return_value = None  # Simulate registry failure

            result = await cache.get_async("proj-1", "unit")

            # Should reject entry when we can't verify version
            assert result is None


class TestPutAsyncSchemaVersion:
    """Tests for put_async() stamping entries with registry version."""

    async def test_put_stamps_entry_with_registry_version(self) -> None:
        """put_async stamps entry with version from SchemaRegistry."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        df = pl.DataFrame({"gid": ["1"], "name": ["A"]})
        watermark = datetime.now(UTC)

        await cache.put_async("proj-1", "unit", df, watermark)

        # Verify entry was stamped with current UNIT_SCHEMA version
        entry = memory.get("unit:proj-1")
        assert entry is not None
        assert entry.schema_version == UNIT_SCHEMA.version

    async def test_put_uses_fallback_on_registry_failure(self) -> None:
        """put_async uses cache default when registry lookup fails."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()

        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            schema_version="1.0.0",  # Fallback version
        )

        df = pl.DataFrame({"gid": ["1"], "name": ["A"]})
        watermark = datetime.now(UTC)

        with patch(
            "autom8_asana.cache.integration.dataframe_cache._get_schema_version_for_entity"
        ) as mock_lookup:
            mock_lookup.return_value = None  # Simulate registry failure

            await cache.put_async("proj-1", "unit", df, watermark)

            # Should use fallback version
            entry = memory.get("unit:proj-1")
            assert entry is not None
            assert entry.schema_version == "1.0.0"

    async def test_put_contact_uses_contact_schema_version(self) -> None:
        """put_async for contact entity uses CONTACT_SCHEMA version."""
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()

        cache = make_cache(memory_tier=memory, progressive_tier=progressive_tier)

        df = pl.DataFrame({"gid": ["1"], "name": ["A"]})
        watermark = datetime.now(UTC)

        await cache.put_async("proj-1", "contact", df, watermark)

        entry = memory.get("contact:proj-1")
        assert entry is not None
        # Contact schema version from registry
        expected_version = _get_schema_version_for_entity("contact")
        assert entry.schema_version == expected_version


class TestRegressionPrevention:
    """Regression tests for the root cause bug."""

    async def test_old_version_not_matched_by_current_schema(self) -> None:
        """Regression: Cache entries with old version are rejected for current UNIT_SCHEMA.

        Root cause: factory.py hardcoded schema_version="1.0.0" but UNIT_SCHEMA
        was bumped, causing stale cache hits.

        Fix: _check_freshness() now looks up expected version from SchemaRegistry
        instead of comparing against self.schema_version.
        """
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()
        progressive_tier.get_async.return_value = None

        # This simulates the old bug: cache initialized with 1.0.0
        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            schema_version="1.0.0",
        )

        # Entry stamped with old version
        old_entry = make_entry(entity_type="unit", schema_version="1.0.0")
        memory.put("unit:proj-1", old_entry)

        # Get should reject because UNIT_SCHEMA is at a newer version
        result = await cache.get_async("proj-1", "unit")
        assert result is None

    async def test_new_entries_stamped_with_correct_version(self) -> None:
        """Regression: New entries are stamped with registry version, not hardcoded.

        Fix: put_async() looks up version from SchemaRegistry instead of
        using self.schema_version.
        """
        memory = MemoryTier(max_entries=100)
        progressive_tier = AsyncMock()

        # Even with hardcoded 1.0.0, entries should get current version from registry
        cache = make_cache(
            memory_tier=memory,
            progressive_tier=progressive_tier,
            schema_version="1.0.0",  # Old hardcoded value
        )

        df = pl.DataFrame({"gid": ["1"], "name": ["A"]})
        await cache.put_async("proj-1", "unit", df, datetime.now(UTC))

        entry = memory.get("unit:proj-1")
        assert entry is not None
        # Entry should have UNIT_SCHEMA version, not cache default
        assert entry.schema_version == UNIT_SCHEMA.version
