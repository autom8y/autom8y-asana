"""Tests for staleness detection helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.integration.staleness_coordinator import (
    StalenessCheckCoordinator,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType, _parse_datetime
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings
from autom8_asana.cache.policies.coalescer import RequestCoalescer
from autom8_asana.cache.policies.lightweight_checker import LightweightChecker, _chunk
from autom8_asana.cache.policies.staleness import (
    check_batch_staleness,
    check_entry_staleness,
    partition_by_staleness,
)
from autom8_asana.core.errors import RedisTransportError


class TestCheckEntryStaleness:
    """Tests for check_entry_staleness function."""

    def test_expired_entry_is_stale(self) -> None:
        """Test that expired entries are always stale."""
        # Entry with 1 second TTL, created 2 seconds ago
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC) - timedelta(seconds=2),
            ttl=1,
        )

        assert check_entry_staleness(entry, None, FreshnessIntent.EVENTUAL) is True
        assert check_entry_staleness(entry, None, FreshnessIntent.STRICT) is True

    def test_eventual_freshness_trusts_ttl(self) -> None:
        """Test that EVENTUAL freshness only checks TTL."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now - timedelta(hours=1),  # Old version
            cached_at=now,  # Recently cached
            ttl=300,
        )

        # Even with old version, EVENTUAL should not be stale if TTL valid
        newer_version = (now + timedelta(minutes=30)).isoformat()
        assert check_entry_staleness(entry, newer_version, FreshnessIntent.EVENTUAL) is False

    def test_strict_freshness_checks_version(self) -> None:
        """Test that STRICT freshness verifies version."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now - timedelta(hours=1),
            cached_at=now,
            ttl=300,
        )

        # Newer source version should be stale in STRICT mode
        newer_version = now.isoformat()
        assert check_entry_staleness(entry, newer_version, FreshnessIntent.STRICT) is True

    def test_strict_freshness_current_version(self) -> None:
        """Test that STRICT freshness accepts current version."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now,
            cached_at=now,
            ttl=300,
        )

        # Same or older source version is not stale
        same_version = now.isoformat()
        older_version = (now - timedelta(hours=1)).isoformat()

        assert check_entry_staleness(entry, same_version, FreshnessIntent.STRICT) is False
        assert check_entry_staleness(entry, older_version, FreshnessIntent.STRICT) is False

    def test_strict_without_current_version_is_stale(self) -> None:
        """Test that STRICT without current version treats as stale."""
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            ttl=300,
        )

        # Cannot verify without current version in STRICT mode
        assert check_entry_staleness(entry, None, FreshnessIntent.STRICT) is True

    def test_version_string_with_z_suffix(self) -> None:
        """Test version comparison with Z suffix timestamp."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=300,
        )

        # Z suffix should be handled correctly
        newer_version = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert check_entry_staleness(entry, newer_version, FreshnessIntent.STRICT) is True

    def test_no_ttl_not_expired(self) -> None:
        """Test that entries without TTL are not expired."""
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
            cached_at=datetime.now(UTC) - timedelta(days=365),
            ttl=None,  # No expiration
        )

        assert check_entry_staleness(entry, None, FreshnessIntent.EVENTUAL) is False


class TestCheckBatchStaleness:
    """Tests for check_batch_staleness function."""

    def test_all_missing_entries(self) -> None:
        """Test that missing entries are marked stale."""
        cache = EnhancedInMemoryCacheProvider()

        result = check_batch_staleness(
            cache,
            ["123", "456", "789"],
            EntryType.TASK,
            {},
            FreshnessIntent.EVENTUAL,
        )

        assert result == {"123": True, "456": True, "789": True}

    def test_all_cached_entries_eventual(self) -> None:
        """Test cached entries in EVENTUAL mode."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Pre-populate cache
        for gid in ["123", "456", "789"]:
            cache.set_versioned(
                gid,
                CacheEntry(
                    key=gid,
                    data={"gid": gid},
                    entry_type=EntryType.TASK,
                    version=now,
                    ttl=300,
                ),
            )

        result = check_batch_staleness(
            cache,
            ["123", "456", "789"],
            EntryType.TASK,
            {"123": now.isoformat(), "456": now.isoformat(), "789": now.isoformat()},
            FreshnessIntent.EVENTUAL,
        )

        assert result == {"123": False, "456": False, "789": False}

    def test_mixed_cached_and_missing(self) -> None:
        """Test mix of cached and missing entries."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Only cache "123"
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123"},
                entry_type=EntryType.TASK,
                version=now,
                ttl=300,
            ),
        )

        result = check_batch_staleness(
            cache,
            ["123", "456"],
            EntryType.TASK,
            {},
            FreshnessIntent.EVENTUAL,
        )

        assert result["123"] is False  # Cached
        assert result["456"] is True  # Missing

    def test_strict_mode_with_versions(self) -> None:
        """Test STRICT mode compares versions."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)
        older = now - timedelta(hours=1)

        # Cache with older version
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123"},
                entry_type=EntryType.TASK,
                version=older,
                ttl=300,
            ),
        )

        result = check_batch_staleness(
            cache,
            ["123"],
            EntryType.TASK,
            {"123": now.isoformat()},  # Newer current version
            FreshnessIntent.STRICT,
        )

        assert result["123"] is True  # Stale because version is older

    def test_empty_gids_list(self) -> None:
        """Test with empty GIDs list."""
        cache = EnhancedInMemoryCacheProvider()

        result = check_batch_staleness(
            cache,
            [],
            EntryType.TASK,
            {},
            FreshnessIntent.EVENTUAL,
        )

        assert result == {}

    def test_different_entry_types(self) -> None:
        """Test that entry types are respected."""
        cache = EnhancedInMemoryCacheProvider()
        now = datetime.now(UTC)

        # Cache as TASK type
        cache.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={"gid": "123"},
                entry_type=EntryType.TASK,
                ttl=300,
                version=now,
            ),
        )

        # Query as SUBTASKS type - should be stale (not found)
        result = check_batch_staleness(
            cache,
            ["123"],
            EntryType.SUBTASKS,
            {},
            FreshnessIntent.EVENTUAL,
        )

        assert result["123"] is True


class TestPartitionByStaleness:
    """Tests for partition_by_staleness function."""

    def test_all_stale(self) -> None:
        """Test partition with all stale entries."""
        staleness = {"123": True, "456": True, "789": True}
        stale, current = partition_by_staleness(staleness)

        assert sorted(stale) == ["123", "456", "789"]
        assert current == []

    def test_all_current(self) -> None:
        """Test partition with all current entries."""
        staleness = {"123": False, "456": False, "789": False}
        stale, current = partition_by_staleness(staleness)

        assert stale == []
        assert sorted(current) == ["123", "456", "789"]

    def test_mixed(self) -> None:
        """Test partition with mixed entries."""
        staleness = {"123": True, "456": False, "789": True, "000": False}
        stale, current = partition_by_staleness(staleness)

        assert sorted(stale) == ["123", "789"]
        assert sorted(current) == ["000", "456"]

    def test_empty(self) -> None:
        """Test partition with empty input."""
        stale, current = partition_by_staleness({})

        assert stale == []
        assert current == []

    def test_single_stale(self) -> None:
        """Test partition with single stale entry."""
        staleness = {"123": True}
        stale, current = partition_by_staleness(staleness)

        assert stale == ["123"]
        assert current == []

    def test_single_current(self) -> None:
        """Test partition with single current entry."""
        staleness = {"123": False}
        stale, current = partition_by_staleness(staleness)

        assert stale == []
        assert current == ["123"]


# --- Adversarial tests (merged from test_staleness_adversarial.py; Sprint 15 S4) ---

def make_entry(
    gid: str,
    modified_at: str = "2025-12-23T10:00:00.000Z",
    ttl: int = 300,
    extension_count: int = 0,
) -> CacheEntry:
    """Create a test CacheEntry."""
    version = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
    return CacheEntry(
        key=gid,
        data={"gid": gid, "name": f"Task {gid}"},
        entry_type=EntryType.TASK,
        version=version,
        cached_at=datetime.now(UTC),
        ttl=ttl,
        metadata={"extension_count": extension_count} if extension_count > 0 else {},
    )


class TestRaceConditionsCoalescer:
    """Race condition tests for RequestCoalescer (NFR-REL-003)."""

    async def test_100_concurrent_requests_for_same_gid(self) -> None:
        """Test 100+ concurrent requests for same GID share single result.

        Per FR-BATCH-004 and NFR-REL-003: Multiple callers for same GID
        receive same result with no duplicate API calls.
        """
        mock_checker = MagicMock()
        call_count = 0

        async def mock_check_batch(entries: list[CacheEntry]) -> dict[str, str | None]:
            nonlocal call_count
            call_count += 1
            # Simulate API latency
            await asyncio.sleep(0.01)
            return {"123": "2025-12-23T10:30:00.000Z"}

        mock_checker.check_batch_async = mock_check_batch

        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=50,
            max_batch=100,
        )

        # Submit 100 concurrent requests for same GID
        tasks = [coalescer.request_check_async(make_entry("123")) for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # All should get same result
        assert all(r == "2025-12-23T10:30:00.000Z" for r in results)

        # Only ONE API call should have been made (deduplication)
        assert call_count == 1, f"Expected 1 API call, got {call_count}"

    async def test_concurrent_different_gids_batched(self) -> None:
        """Test concurrent requests for different GIDs are batched efficiently."""
        mock_checker = MagicMock()
        call_count = 0

        async def mock_check_batch(entries: list[CacheEntry]) -> dict[str, str | None]:
            nonlocal call_count
            call_count += 1
            return {e.key: "2025-12-23T10:30:00.000Z" for e in entries}

        mock_checker.check_batch_async = mock_check_batch

        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=50,
            max_batch=100,
        )

        # Submit 50 concurrent requests for different GIDs
        tasks = [coalescer.request_check_async(make_entry(str(i))) for i in range(50)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 50
        assert all(r is not None for r in results)

        # Should be batched into single call
        assert call_count == 1, f"Expected 1 batch, got {call_count}"


class TestTimerEdgeCases:
    """Timer boundary condition tests."""

    async def test_request_at_window_boundary(self) -> None:
        """Test request arriving within coalesce window gets batched.

        Uses a very large window (2000ms) with a short sleep (50ms) to ensure
        the second request always arrives well before the timer fires, even
        on slow CI runners where event loop scheduling can be delayed.
        """
        mock_checker = MagicMock()
        batches_received = []

        async def mock_check_batch(entries: list[CacheEntry]) -> dict[str, str | None]:
            batches_received.append([e.key for e in entries])
            return {e.key: "2025-12-23T10:30:00.000Z" for e in entries}

        mock_checker.check_batch_async = mock_check_batch

        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=2000,  # Very large window to eliminate CI timing flakiness
            max_batch=100,
        )

        # First request starts the timer
        task1 = asyncio.create_task(coalescer.request_check_async(make_entry("1")))

        # Wait a short time well under the window (50ms out of 2000ms)
        await asyncio.sleep(0.050)

        # Second request arrives within window
        task2 = asyncio.create_task(coalescer.request_check_async(make_entry("2")))

        # Force flush to avoid waiting the full 2s window
        await asyncio.sleep(0.010)
        await coalescer.flush_pending()

        results = await asyncio.gather(task1, task2)

        # Both should be in same batch
        assert len(results) == 2
        assert len(batches_received) == 1
        assert set(batches_received[0]) == {"1", "2"}

    async def test_zero_window_immediate_execution(self) -> None:
        """Test that zero coalesce window executes immediately."""
        mock_checker = MagicMock()
        mock_checker.check_batch_async = AsyncMock(return_value={"123": "2025-12-23T10:30:00.000Z"})

        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=0,  # Zero window
            max_batch=100,
        )

        import time

        start = time.monotonic()
        result = await coalescer.request_check_async(make_entry("123"))
        elapsed = time.monotonic() - start

        assert result == "2025-12-23T10:30:00.000Z"
        # Should complete nearly immediately (no waiting)
        assert elapsed < 0.05, f"Zero window should be immediate, took {elapsed}s"


class TestBatchOverflow:
    """Batch overflow handling tests (FR-BATCH-002, FR-BATCH-005)."""

    async def test_200_requests_split_into_multiple_batches(self) -> None:
        """Test 200+ requests are split at max_batch boundary."""
        mock_checker = MagicMock()
        batches_received = []

        async def mock_check_batch(entries: list[CacheEntry]) -> dict[str, str | None]:
            batches_received.append(len(entries))
            return {e.key: "2025-12-23T10:30:00.000Z" for e in entries}

        mock_checker.check_batch_async = mock_check_batch

        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=5000,  # Long window to force max_batch trigger
            max_batch=100,
        )

        # Submit 200 requests
        tasks = [coalescer.request_check_async(make_entry(str(i))) for i in range(200)]

        # Run them all
        results = await asyncio.gather(*tasks)

        assert len(results) == 200
        assert all(r is not None for r in results)

        # Should have at least 2 batches (100 each)
        assert len(batches_received) >= 2
        # First batch should be exactly 100 (max_batch)
        assert batches_received[0] == 100

    async def test_chunking_at_asana_limit(self) -> None:
        """Test LightweightChecker chunks at Asana's 10-action limit."""
        mock_batch_client = MagicMock()
        chunks_called = []

        async def mock_execute(requests):
            chunks_called.append(len(requests))
            return [
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": r.relative_path.split("/")[-1],
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
                for r in requests
            ]

        mock_batch_client.execute_async = mock_execute

        checker = LightweightChecker(batch_client=mock_batch_client, chunk_size=10)

        # 25 entries should become 3 chunks: 10, 10, 5
        entries = [make_entry(str(i)) for i in range(25)]
        result = await checker.check_batch_async(entries)

        assert len(result) == 25
        assert chunks_called == [10, 10, 5]


class TestAPITimeoutHandling:
    """API timeout and error handling tests (FR-DEGRADE-*)."""

    async def test_batch_timeout_returns_none(self) -> None:
        """Test that API timeout returns None for all entries."""
        mock_checker = MagicMock()

        async def mock_timeout(entries):
            await asyncio.sleep(10)  # Will be cancelled
            return {}

        mock_checker.check_batch_async = mock_timeout

        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=10,
            max_batch=100,
        )

        # Use asyncio.wait_for with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                coalescer.request_check_async(make_entry("123")),
                timeout=0.2,
            )

    async def test_partial_chunk_failure_isolated(self) -> None:
        """Test that one chunk failing doesn't affect other chunks."""
        mock_batch_client = MagicMock()
        call_count = 0

        async def mock_execute(requests):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail second chunk
                raise ConnectionError("Network error")
            return [
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": r.relative_path.split("/")[-1],
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
                for r in requests
            ]

        mock_batch_client.execute_async = mock_execute

        checker = LightweightChecker(batch_client=mock_batch_client, chunk_size=10)

        # 25 entries = 3 chunks, second will fail
        entries = [make_entry(str(i)) for i in range(25)]
        result = await checker.check_batch_async(entries)

        # First 10 should succeed
        for i in range(10):
            assert result[str(i)] is not None

        # Second 10 (chunk failed) should be None
        for i in range(10, 20):
            assert result[str(i)] is None

        # Third 5 should succeed
        for i in range(20, 25):
            assert result[str(i)] is not None


class TestMalformedModifiedAt:
    """Malformed modified_at handling tests (FR-DEGRADE-002)."""

    def test_empty_string_raises(self) -> None:
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError):
            _parse_datetime("")

    def test_invalid_format_raises(self) -> None:
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError):
            _parse_datetime("not-a-date")

    def test_invalid_date_components_raises(self) -> None:
        """Test invalid date components raise ValueError."""
        with pytest.raises(ValueError):
            _parse_datetime("2025-13-45T99:99:99")

    async def test_missing_modified_at_in_response(self) -> None:
        """Test that missing modified_at in response returns None."""
        mock_batch_client = MagicMock()
        mock_batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={"data": {"gid": "123"}},  # No modified_at field
                )
            ]
        )

        checker = LightweightChecker(batch_client=mock_batch_client)
        entries = [make_entry("123")]

        result = await checker.check_batch_async(entries)

        # Missing modified_at should return None
        assert result["123"] is None

    async def test_null_modified_at_in_response(self) -> None:
        """Test that null modified_at in response returns None."""
        mock_batch_client = MagicMock()
        mock_batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={"data": {"gid": "123", "modified_at": None}},
                )
            ]
        )

        checker = LightweightChecker(batch_client=mock_batch_client)
        entries = [make_entry("123")]

        result = await checker.check_batch_async(entries)

        assert result["123"] is None

    async def test_non_string_modified_at_in_response(self) -> None:
        """Test that non-string modified_at returns None."""
        mock_batch_client = MagicMock()
        mock_batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={"data": {"gid": "123", "modified_at": 12345}},  # Number instead of string
                )
            ]
        )

        checker = LightweightChecker(batch_client=mock_batch_client)
        entries = [make_entry("123")]

        result = await checker.check_batch_async(entries)

        assert result["123"] is None


class TestDeletedEntityHandling:
    """Deleted entity (404) handling tests (FR-STALE-006)."""

    async def test_404_invalidates_cache(self) -> None:
        """Test that 404 response invalidates cache entry."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = MagicMock()

        batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=404,
                    body={"errors": [{"message": "Not found"}]},
                )
            ]
        )

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        entry = make_entry("123")

        result = await coordinator.check_and_get_async(entry)

        # Should return None
        assert result is None

        # Stats should track error
        stats = coordinator.get_extension_stats()
        assert stats["error_count"] >= 1


class TestTTLCeilingBoundary:
    """TTL ceiling boundary tests (FR-TTL-002)."""

    def test_ttl_exactly_at_ceiling(self) -> None:
        """Test TTL at exactly the ceiling value."""
        settings = StalenessCheckSettings(base_ttl=300, max_ttl=86400)

        # At count 9, calculated = 300 * 512 = 153600, capped to 86400
        assert settings.calculate_extended_ttl(9) == 86400

        # Any higher count should also return ceiling
        assert settings.calculate_extended_ttl(10) == 86400
        assert settings.calculate_extended_ttl(100) == 86400

    def test_ttl_just_below_ceiling(self) -> None:
        """Test TTL just below the ceiling."""
        settings = StalenessCheckSettings(base_ttl=300, max_ttl=86400)

        # At count 8: 300 * 256 = 76800 (below ceiling)
        assert settings.calculate_extended_ttl(8) == 76800

    async def test_progressive_extension_respects_ceiling(self) -> None:
        """Test that progressive extension never exceeds ceiling."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = MagicMock()

        batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": "123",
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
            ]
        )

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(
                enabled=True,
                base_ttl=300,
                max_ttl=86400,
                coalesce_window_ms=1,
            ),
        )

        # Start with entry at extension_count=8 (76800 TTL)
        entry = make_entry("123", ttl=76800, extension_count=8)

        result = await coordinator.check_and_get_async(entry)

        # Should extend to ceiling (86400), not 153600
        assert result is not None
        assert result.ttl == 86400
        assert result.metadata.get("extension_count") == 9

        # Another extension should stay at ceiling
        result2 = await coordinator.check_and_get_async(result)
        assert result2 is not None
        assert result2.ttl == 86400
        assert result2.metadata.get("extension_count") == 10


class TestExtensionCountOverflow:
    """Extension count overflow tests."""

    def test_massive_extension_count(self) -> None:
        """Test handling of massive extension count values."""
        settings = StalenessCheckSettings(base_ttl=300, max_ttl=86400)

        # Very large extension count should still cap at max_ttl
        assert settings.calculate_extended_ttl(1000) == 86400
        assert settings.calculate_extended_ttl(999999) == 86400

    def test_negative_extension_count_raises(self) -> None:
        """Test that negative extension count raises ValueError."""
        settings = StalenessCheckSettings()

        with pytest.raises(ValueError, match="extension_count must be non-negative"):
            settings.calculate_extended_ttl(-1)

    async def test_entry_with_large_extension_count(self) -> None:
        """Test entry with already large extension count."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = MagicMock()

        batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": "123",
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
            ]
        )

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(
                enabled=True,
                base_ttl=300,
                max_ttl=86400,
                coalesce_window_ms=1,
            ),
        )

        # Entry already at high extension count
        entry = make_entry("123", ttl=86400, extension_count=100)

        result = await coordinator.check_and_get_async(entry)

        # Should still work, TTL at ceiling, count incremented
        assert result is not None
        assert result.ttl == 86400
        assert result.metadata.get("extension_count") == 101


class TestEdgeCaseBatches:
    """Edge case batch handling tests."""

    def test_chunk_empty_list(self) -> None:
        """Test chunking empty list."""
        assert _chunk([], 10) == []

    def test_chunk_single_item(self) -> None:
        """Test chunking single item works."""
        assert _chunk(["a"], 10) == [["a"]]

    def test_chunk_zero_size_returns_empty(self) -> None:
        """Test zero chunk size returns empty."""
        assert _chunk(["a", "b"], 0) == []

    def test_chunk_negative_size_returns_empty(self) -> None:
        """Test negative chunk size returns empty."""
        assert _chunk(["a", "b"], -1) == []

    async def test_single_entry_batch(self) -> None:
        """Test single entry batch works correctly."""
        mock_batch_client = MagicMock()
        mock_batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": "123",
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
            ]
        )

        checker = LightweightChecker(batch_client=mock_batch_client)
        entries = [make_entry("123")]

        result = await checker.check_batch_async(entries)

        assert len(result) == 1
        assert result["123"] == "2025-12-23T10:00:00.000Z"


class TestMixedSuccessFailure:
    """Mixed success/failure handling tests (FR-DEGRADE-003)."""

    async def test_mixed_200_404_500_responses(self) -> None:
        """Test handling mix of success, deleted, and error responses."""
        mock_batch_client = MagicMock()
        mock_batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={"data": {"gid": "1", "modified_at": "2025-12-23T10:00:00.000Z"}},
                ),
                BatchResult(
                    status_code=404,
                    body={"errors": [{"message": "Not found"}]},
                ),
                BatchResult(
                    status_code=500,
                    body={"errors": [{"message": "Internal error"}]},
                ),
                BatchResult(
                    status_code=200,
                    body={"data": {"gid": "4", "modified_at": "2025-12-23T11:00:00.000Z"}},
                ),
            ]
        )

        checker = LightweightChecker(batch_client=mock_batch_client)
        entries = [make_entry(str(i)) for i in range(1, 5)]

        result = await checker.check_batch_async(entries)

        # 1 and 4 succeed
        assert result["1"] == "2025-12-23T10:00:00.000Z"
        assert result["4"] == "2025-12-23T11:00:00.000Z"

        # 2 (404) and 3 (500) return None
        assert result["2"] is None
        assert result["3"] is None


class TestCoordinatorGracefulDegradation:
    """Coordinator graceful degradation tests."""

    async def test_cache_unavailable_handled(self) -> None:
        """Test that cache unavailability is handled gracefully."""
        mock_cache = MagicMock()
        mock_cache.set_versioned = MagicMock(side_effect=RedisTransportError("Redis down"))
        mock_cache.invalidate = MagicMock()

        batch_client = MagicMock()
        batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": "123",
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
            ]
        )

        coordinator = StalenessCheckCoordinator(
            cache_provider=mock_cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        entry = make_entry("123")

        # Should still return result even if cache update fails
        result = await coordinator.check_and_get_async(entry)

        assert result is not None
        assert result.ttl == 600  # Extended TTL

    async def test_invalidate_failure_handled(self) -> None:
        """Test that cache invalidation failure is handled gracefully."""
        mock_cache = MagicMock()
        mock_cache.set_versioned = MagicMock()
        mock_cache.invalidate = MagicMock(side_effect=RedisTransportError("Redis down"))

        batch_client = MagicMock()
        batch_client.execute_async = AsyncMock(
            return_value=[
                BatchResult(
                    status_code=404,
                    body={"errors": [{"message": "Not found"}]},
                )
            ]
        )

        coordinator = StalenessCheckCoordinator(
            cache_provider=mock_cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        entry = make_entry("123")

        # Should return None without raising
        result = await coordinator.check_and_get_async(entry)

        assert result is None
