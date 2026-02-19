"""Unit tests for CacheEntry dataclass.

Per TDD-DATAFRAME-CACHE-001: Tests for cache entry creation, staleness
detection, and watermark-based freshness checks.
"""

from datetime import UTC, datetime, timedelta

import polars as pl

from autom8_asana.cache.integration.dataframe_cache import (
    DataFrameCacheEntry as CacheEntry,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_creation_computes_row_count(self) -> None:
        """CacheEntry computes row_count from DataFrame."""
        df = pl.DataFrame({"gid": ["1", "2", "3"], "name": ["A", "B", "C"]})

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=df,
            watermark=datetime.now(UTC),
            created_at=datetime.now(UTC),
            schema_version="1.0.0",
        )

        assert entry.row_count == 3

    def test_creation_with_empty_dataframe(self) -> None:
        """CacheEntry handles empty DataFrame."""
        df = pl.DataFrame({"gid": []})

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=df,
            watermark=datetime.now(UTC),
            created_at=datetime.now(UTC),
            schema_version="1.0.0",
        )

        assert entry.row_count == 0

    def test_is_stale_within_ttl(self) -> None:
        """Entry within TTL is not stale."""
        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1", "2"]}),
            watermark=datetime.now(UTC),
            created_at=datetime.now(UTC),
            schema_version="1.0.0",
        )

        assert not entry.is_stale(ttl_seconds=3600)

    def test_is_stale_beyond_ttl(self) -> None:
        """Entry beyond TTL is stale."""
        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1", "2"]}),
            watermark=datetime.now(UTC),
            created_at=datetime.now(UTC) - timedelta(hours=2),
            schema_version="1.0.0",
        )

        assert entry.is_stale(ttl_seconds=3600)

    def test_is_stale_at_boundary(self) -> None:
        """Entry at TTL boundary is stale."""
        created = datetime.now(UTC) - timedelta(seconds=3601)

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1"]}),
            watermark=datetime.now(UTC),
            created_at=created,
            schema_version="1.0.0",
        )

        assert entry.is_stale(ttl_seconds=3600)

    def test_is_fresh_by_watermark_newer(self) -> None:
        """Entry is fresh when watermark >= current."""
        now = datetime.now(UTC)

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1"]}),
            watermark=now,
            created_at=now,
            schema_version="1.0.0",
        )

        # Entry watermark equals current watermark - fresh
        assert entry.is_fresh_by_watermark(now)

        # Entry watermark is newer than current - fresh
        older = now - timedelta(minutes=5)
        assert entry.is_fresh_by_watermark(older)

    def test_is_not_fresh_by_watermark_older(self) -> None:
        """Entry is stale when watermark < current."""
        now = datetime.now(UTC)
        entry_watermark = now - timedelta(minutes=10)

        entry = CacheEntry(
            project_gid="proj-1",
            entity_type="unit",
            dataframe=pl.DataFrame({"gid": ["1"]}),
            watermark=entry_watermark,
            created_at=now - timedelta(minutes=10),
            schema_version="1.0.0",
        )

        # Current watermark is newer - stale
        assert not entry.is_fresh_by_watermark(now)

    def test_attributes_accessible(self) -> None:
        """All attributes are accessible after creation."""
        df = pl.DataFrame({"gid": ["1"], "name": ["Test"]})
        watermark = datetime.now(UTC)
        created = datetime.now(UTC) - timedelta(minutes=5)

        entry = CacheEntry(
            project_gid="proj-123",
            entity_type="offer",
            dataframe=df,
            watermark=watermark,
            created_at=created,
            schema_version="2.0.0",
        )

        assert entry.project_gid == "proj-123"
        assert entry.entity_type == "offer"
        assert len(entry.dataframe) == 1
        assert entry.watermark == watermark
        assert entry.created_at == created
        assert entry.schema_version == "2.0.0"
        assert entry.row_count == 1
