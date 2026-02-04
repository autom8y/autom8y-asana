"""Integration tests for staleness check flow.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Validates E2E unchanged path,
changed path, batch coalescing, and graceful degradation.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.integration.staleness_coordinator import StalenessCheckCoordinator
from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings


def make_mock_batch_client() -> MagicMock:
    """Create a mock batch client for testing."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client


def make_entry(
    gid: str,
    modified_at: str = "2025-12-23T10:00:00.000Z",
    ttl: int = 300,
    extension_count: int = 0,
    expired: bool = True,
) -> CacheEntry:
    """Create a test CacheEntry.

    Args:
        gid: Task GID.
        modified_at: Modified timestamp.
        ttl: TTL in seconds.
        extension_count: Number of previous extensions.
        expired: If True, set cached_at to make entry expired.
    """
    version = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))

    if expired:
        # Set cached_at to past so entry is expired
        cached_at = datetime.now(UTC) - timedelta(seconds=ttl + 60)
    else:
        cached_at = datetime.now(UTC)

    return CacheEntry(
        key=gid,
        data={"gid": gid, "name": f"Task {gid}", "modified_at": modified_at},
        entry_type=EntryType.TASK,
        version=version,
        cached_at=cached_at,
        ttl=ttl,
        metadata={"extension_count": extension_count} if extension_count > 0 else {},
    )


class TestStalenessFlowUnchanged:
    """Test E2E flow for unchanged entities."""

    @pytest.mark.asyncio
    async def test_unchanged_entity_gets_extended_ttl(self) -> None:
        """Test that unchanged entity gets TTL extended."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(
                enabled=True,
                base_ttl=300,
                max_ttl=86400,
                coalesce_window_ms=1,  # Fast for testing
            ),
        )

        # Create expired entry
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z", expired=True)

        # Mock batch response: same modified_at (unchanged)
        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:00:00.000Z"}
                },
            )
        ]

        # Check staleness
        result = await coordinator.check_and_get_async(entry)

        # Should get extended entry
        assert result is not None
        assert result.key == "123"
        assert result.ttl == 600  # Extended from 300
        assert result.metadata.get("extension_count") == 1
        assert result.data["name"] == "Task 123"  # Data preserved

    @pytest.mark.asyncio
    async def test_progressive_ttl_extension_over_multiple_checks(self) -> None:
        """Test that TTL progressively extends with each check."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

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

        modified_at = "2025-12-23T10:00:00.000Z"

        # Mock: always return same modified_at
        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={"data": {"gid": "123", "modified_at": modified_at}},
            )
        ]

        # First check: base TTL
        entry = make_entry("123", modified_at=modified_at, ttl=300, extension_count=0)
        result = await coordinator.check_and_get_async(entry)
        assert result is not None
        assert result.ttl == 600  # 300 * 2

        # Second check: use result from first
        result = await coordinator.check_and_get_async(result)
        assert result is not None
        assert result.ttl == 1200  # 300 * 4

        # Third check
        result = await coordinator.check_and_get_async(result)
        assert result is not None
        assert result.ttl == 2400  # 300 * 8


class TestStalenessFlowChanged:
    """Test E2E flow for changed entities."""

    @pytest.mark.asyncio
    async def test_changed_entity_returns_none(self) -> None:
        """Test that changed entity returns None for full fetch."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(
                enabled=True,
                base_ttl=300,
                coalesce_window_ms=1,
            ),
        )

        # Create expired entry with old modified_at
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z", expired=True)

        # Mock batch response: newer modified_at (changed)
        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-24T12:00:00.000Z"}
                },
            )
        ]

        # Check staleness
        result = await coordinator.check_and_get_async(entry)

        # Should return None (caller should full fetch)
        assert result is None

        # Stats should show change
        stats = coordinator.get_extension_stats()
        assert stats["changed_count"] == 1
        assert stats["unchanged_count"] == 0


class TestBatchCoalescing:
    """Test batch coalescing behavior."""

    @pytest.mark.asyncio
    async def test_multiple_requests_batched_together(self) -> None:
        """Test that concurrent requests are batched into single API call."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(
                enabled=True,
                coalesce_window_ms=50,  # 50ms window
                max_batch_size=100,
            ),
        )

        # Create multiple expired entries
        entries = [
            make_entry(str(i), modified_at="2025-12-23T10:00:00.000Z", expired=True)
            for i in range(5)
        ]

        # Mock batch response
        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": str(i), "modified_at": "2025-12-23T10:00:00.000Z"}
                },
            )
            for i in range(5)
        ]

        # Submit all concurrently
        results = await asyncio.gather(
            *[coordinator.check_and_get_async(entry) for entry in entries]
        )

        # All should succeed
        assert all(r is not None for r in results)

        # Should have been batched into single call
        assert batch_client.execute_async.call_count == 1

    @pytest.mark.asyncio
    async def test_deduplication_same_gid_concurrent(self) -> None:
        """Test that same GID requested concurrently is deduplicated."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(
                enabled=True,
                coalesce_window_ms=50,
            ),
        )

        # Same entry requested multiple times
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z", expired=True)

        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:00:00.000Z"}
                },
            )
        ]

        # Submit same entry 3 times concurrently
        results = await asyncio.gather(
            coordinator.check_and_get_async(make_entry("123")),
            coordinator.check_and_get_async(make_entry("123")),
            coordinator.check_and_get_async(make_entry("123")),
        )

        # All should get same result
        assert all(r is not None for r in results)
        assert all(r.key == "123" for r in results)

        # Only one API call for the single unique GID
        assert batch_client.execute_async.call_count == 1
        call_requests = batch_client.execute_async.call_args[0][0]
        assert len(call_requests) == 1


class TestGracefulDegradation:
    """Test graceful degradation on errors."""

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self) -> None:
        """Test that API errors return None without raising."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        entry = make_entry("123", expired=True)

        # Mock API error
        batch_client.execute_async.side_effect = Exception("Network timeout")

        result = await coordinator.check_and_get_async(entry)

        # Should return None (not raise)
        assert result is None

        # Stats should track error
        stats = coordinator.get_extension_stats()
        assert stats["error_count"] == 1

    @pytest.mark.asyncio
    async def test_deleted_entity_returns_none(self) -> None:
        """Test that deleted entity (404) returns None."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        entry = make_entry("123", expired=True)

        # Mock 404 response
        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=404,
                body={"errors": [{"message": "Not found"}]},
            )
        ]

        result = await coordinator.check_and_get_async(entry)

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_partial_batch_failure_handled(self) -> None:
        """Test that partial batch failure is handled gracefully."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=50),
        )

        entries = [make_entry(str(i), expired=True) for i in range(3)]

        # Mock: first succeeds, second fails, third succeeds
        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={"data": {"gid": "0", "modified_at": "2025-12-23T10:00:00.000Z"}},
            ),
            BatchResult(
                status_code=500,
                body={"errors": [{"message": "Internal error"}]},
            ),
            BatchResult(
                status_code=200,
                body={"data": {"gid": "2", "modified_at": "2025-12-23T10:00:00.000Z"}},
            ),
        ]

        results = await asyncio.gather(
            *[coordinator.check_and_get_async(entry) for entry in entries]
        )

        # First and third should succeed, second should be None
        assert results[0] is not None
        assert results[1] is None  # Failed
        assert results[2] is not None

    @pytest.mark.asyncio
    async def test_disabled_coordinator_returns_none(self) -> None:
        """Test that disabled coordinator returns None immediately."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=False),  # Disabled
        )

        entry = make_entry("123", expired=True)

        result = await coordinator.check_and_get_async(entry)

        # Should return None without API call
        assert result is None
        batch_client.execute_async.assert_not_called()


class TestCacheIntegration:
    """Test integration with cache provider."""

    @pytest.mark.asyncio
    async def test_extended_entry_stored_in_cache(self) -> None:
        """Test that extended entry is stored back in cache."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z", expired=True)

        batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:00:00.000Z"}
                },
            )
        ]

        result = await coordinator.check_and_get_async(entry)

        # Verify entry is in cache with extended TTL
        cached = cache.get_versioned("123", EntryType.TASK)
        assert cached is not None
        assert cached.ttl == 600  # Extended
        assert cached.metadata.get("extension_count") == 1

    @pytest.mark.asyncio
    async def test_api_calls_saved_tracked(self) -> None:
        """Test that API calls saved are tracked correctly."""
        cache = EnhancedInMemoryCacheProvider()
        batch_client = make_mock_batch_client()

        coordinator = StalenessCheckCoordinator(
            cache_provider=cache,
            batch_client=batch_client,
            settings=StalenessCheckSettings(enabled=True, coalesce_window_ms=1),
        )

        # Check 3 unchanged entries
        for i in range(3):
            entry = make_entry(str(i), modified_at="2025-12-23T10:00:00.000Z")
            batch_client.execute_async.return_value = [
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": str(i),
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
            ]
            await coordinator.check_and_get_async(entry)

        stats = coordinator.get_extension_stats()
        assert stats["api_calls_saved"] == 3  # 3 full fetches avoided
        assert stats["unchanged_count"] == 3
