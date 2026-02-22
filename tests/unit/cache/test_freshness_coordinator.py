"""Tests for FreshnessCoordinator.

Per TDD-UNIFIED-CACHE-001: Validates batch freshness checking,
chunking by Asana batch limit, and freshness mode behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.integration.freshness_coordinator import (
    FreshnessCoordinator,
    FreshnessMode,
    FreshnessResult,
)
from autom8_asana.cache.models.entry import CacheEntry, EntryType

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def coordinator(mock_batch_client: MagicMock) -> FreshnessCoordinator:
    """Create a FreshnessCoordinator with mock batch client."""
    return FreshnessCoordinator(
        batch_client=mock_batch_client,
        coalesce_window_ms=1,
        max_batch_size=100,
    )


def make_entry(
    gid: str,
    modified_at: str = "2025-12-23T10:00:00.000Z",
    ttl: int = 300,
    cached_ago_seconds: int = 0,
) -> CacheEntry:
    """Create a test CacheEntry.

    Args:
        gid: Task GID.
        modified_at: ISO format modified_at timestamp.
        ttl: TTL in seconds.
        cached_ago_seconds: How many seconds ago it was cached (0 = now).
    """
    version = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
    cached_at = datetime.now(UTC) - timedelta(seconds=cached_ago_seconds)
    return CacheEntry(
        key=gid,
        data={"gid": gid, "name": f"Task {gid}"},
        entry_type=EntryType.TASK,
        version=version,
        cached_at=cached_at,
        ttl=ttl,
    )


def make_batch_result(
    gid: str, modified_at: str | None, success: bool = True
) -> BatchResult:
    """Create a test BatchResult.

    BatchResult uses status_code to derive success (2xx = success).
    Body is wrapped in {"data": ...} per Asana API convention.
    """
    if not success:
        return BatchResult(
            status_code=404,
            body={"errors": [{"message": "Not Found"}]},
            request_index=0,
        )
    elif modified_at:
        return BatchResult(
            status_code=200,
            body={"data": {"gid": gid, "modified_at": modified_at}},
            request_index=0,
        )
    else:
        # Success but missing modified_at
        return BatchResult(
            status_code=200,
            body={"data": {"gid": gid}},  # Missing modified_at
            request_index=0,
        )


class TestFreshnessResult:
    """Tests for FreshnessResult dataclass."""

    def test_freshness_result_immutable(self) -> None:
        """Test that FreshnessResult is immutable."""
        result = FreshnessResult(
            gid="123",
            is_fresh=True,
            cached_version=datetime.now(UTC),
            current_version=None,
            action="use_cache",
        )

        with pytest.raises(AttributeError):
            result.is_fresh = False  # type: ignore[misc]


class TestFreshnessMode:
    """Tests for FreshnessMode enum."""

    def test_mode_values(self) -> None:
        """Test FreshnessMode enum values."""
        assert FreshnessMode.STRICT.value == "strict"
        assert FreshnessMode.EVENTUAL.value == "eventual"
        assert FreshnessMode.IMMEDIATE.value == "immediate"


class TestFreshnessCoordinatorImmediate:
    """Tests for IMMEDIATE mode."""

    @pytest.mark.asyncio
    async def test_immediate_returns_fresh_without_api(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that IMMEDIATE mode returns fresh without API call."""
        entries = [make_entry("123"), make_entry("456")]

        results = await coordinator.check_batch_async(
            entries, mode=FreshnessMode.IMMEDIATE
        )

        # Should not call API
        mock_batch_client.execute_async.assert_not_called()

        # All should be fresh
        assert len(results) == 2
        for result in results:
            assert result.is_fresh is True
            assert result.action == "use_cache"
            assert result.current_version is None

    @pytest.mark.asyncio
    async def test_immediate_stats_tracking(
        self, coordinator: FreshnessCoordinator
    ) -> None:
        """Test that IMMEDIATE mode tracks stats correctly."""
        entries = [make_entry("123"), make_entry("456"), make_entry("789")]

        await coordinator.check_batch_async(entries, mode=FreshnessMode.IMMEDIATE)

        stats = coordinator.get_stats()
        assert stats["total_checks"] == 3
        assert stats["immediate_returns"] == 3
        assert stats["api_calls"] == 0


class TestFreshnessCoordinatorEventual:
    """Tests for EVENTUAL mode."""

    @pytest.mark.asyncio
    async def test_eventual_non_expired_returns_fresh(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that EVENTUAL mode returns fresh for non-expired entries."""
        # Entry cached just now with 300s TTL - not expired
        entry = make_entry("123", ttl=300, cached_ago_seconds=0)

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.EVENTUAL
        )

        # Should not call API
        mock_batch_client.execute_async.assert_not_called()

        assert len(results) == 1
        assert results[0].is_fresh is True
        assert results[0].action == "use_cache"

    @pytest.mark.asyncio
    async def test_eventual_expired_checks_api(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that EVENTUAL mode checks API for expired entries."""
        # Entry cached 400s ago with 300s TTL - expired
        entry = make_entry("123", ttl=300, cached_ago_seconds=400)

        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", "2025-12-23T10:00:00.000Z")
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.EVENTUAL
        )

        # Should call API
        mock_batch_client.execute_async.assert_called_once()

        assert len(results) == 1
        # Version unchanged so should be fresh
        assert results[0].is_fresh is True
        assert results[0].action == "extend_ttl"

    @pytest.mark.asyncio
    async def test_eventual_mixed_expired_non_expired(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test EVENTUAL with mix of expired and non-expired entries."""
        # Fresh entry
        fresh_entry = make_entry("fresh", ttl=300, cached_ago_seconds=0)
        # Expired entry
        expired_entry = make_entry("expired", ttl=300, cached_ago_seconds=400)

        mock_batch_client.execute_async.return_value = [
            make_batch_result("expired", "2025-12-23T10:00:00.000Z")
        ]

        results = await coordinator.check_batch_async(
            [fresh_entry, expired_entry], mode=FreshnessMode.EVENTUAL
        )

        assert len(results) == 2

        # Both should be fresh (fresh never checked, expired version unchanged)
        fresh_results = [r for r in results if r.gid == "fresh"]
        expired_results = [r for r in results if r.gid == "expired"]

        assert fresh_results[0].is_fresh is True
        assert fresh_results[0].action == "use_cache"

        assert expired_results[0].is_fresh is True
        assert expired_results[0].action == "extend_ttl"


class TestFreshnessCoordinatorStrict:
    """Tests for STRICT mode."""

    @pytest.mark.asyncio
    async def test_strict_always_checks_api(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that STRICT mode always checks API even for non-expired."""
        # Non-expired entry
        entry = make_entry("123", ttl=300, cached_ago_seconds=0)

        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", "2025-12-23T10:00:00.000Z")
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        # Should call API
        mock_batch_client.execute_async.assert_called_once()

        assert len(results) == 1
        assert results[0].is_fresh is True

    @pytest.mark.asyncio
    async def test_strict_detects_changed(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that STRICT mode detects changed entries."""
        entry = make_entry("123", modified_at="2025-12-23T10:00:00.000Z")

        # Return newer modified_at
        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", "2025-12-23T12:00:00.000Z")  # 2 hours later
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert len(results) == 1
        assert results[0].is_fresh is False
        assert results[0].action == "fetch"


class TestFreshnessCoordinatorBatching:
    """Tests for batch chunking behavior."""

    @pytest.mark.asyncio
    async def test_chunks_by_asana_limit(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that requests are chunked by Asana batch limit (10)."""
        # Create 25 expired entries to force batching
        entries = [
            make_entry(f"task-{i}", ttl=1, cached_ago_seconds=100) for i in range(25)
        ]

        # Mock successful responses
        def create_results(requests: list) -> list[BatchResult]:
            return [
                make_batch_result(f"task-{i}", "2025-12-23T10:00:00.000Z")
                for i in range(len(requests))
            ]

        mock_batch_client.execute_async.side_effect = [
            create_results(range(10)),  # First chunk
            create_results(range(10)),  # Second chunk
            create_results(range(5)),  # Third chunk (5 remaining)
        ]

        await coordinator.check_batch_async(entries, mode=FreshnessMode.STRICT)

        # Should make 3 API calls (chunks of 10, 10, 5)
        assert mock_batch_client.execute_async.call_count == 3

        stats = coordinator.get_stats()
        assert stats["api_calls"] == 3

    @pytest.mark.asyncio
    async def test_empty_entries_no_api_call(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that empty entries list doesn't call API."""
        results = await coordinator.check_batch_async([], mode=FreshnessMode.STRICT)

        mock_batch_client.execute_async.assert_not_called()
        assert results == []


class TestFreshnessCoordinatorErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_batch_failure_returns_fetch(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that batch API failure results in fetch action."""
        entry = make_entry("123", ttl=1, cached_ago_seconds=100)

        mock_batch_client.execute_async.side_effect = ConnectionError("Network error")

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert len(results) == 1
        assert results[0].is_fresh is False
        assert results[0].action == "fetch"

    @pytest.mark.asyncio
    async def test_deleted_entity_returns_fetch(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that 404 (deleted) results in fetch action."""
        entry = make_entry("123", ttl=1, cached_ago_seconds=100)

        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", None, success=False)
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert len(results) == 1
        assert results[0].is_fresh is False
        assert results[0].action == "fetch"

    @pytest.mark.asyncio
    async def test_missing_modified_at_returns_fetch(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that missing modified_at in response results in fetch action."""
        entry = make_entry("123", ttl=1, cached_ago_seconds=100)

        # Response missing modified_at field (uses helper with None modified_at)
        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", None, success=True)
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert len(results) == 1
        assert results[0].is_fresh is False
        assert results[0].action == "fetch"

    @pytest.mark.asyncio
    async def test_no_batch_client_returns_fetch(self) -> None:
        """Test that missing batch client results in fetch action."""
        coordinator = FreshnessCoordinator(batch_client=None)
        entry = make_entry("123", ttl=1, cached_ago_seconds=100)

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert len(results) == 1
        assert results[0].is_fresh is False
        assert results[0].action == "fetch"


class TestFreshnessCoordinatorHierarchy:
    """Tests for hierarchy-based freshness checking."""

    @pytest.mark.asyncio
    async def test_check_hierarchy_immediate(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test hierarchy check with IMMEDIATE mode."""
        entry = make_entry("root-123")

        result = await coordinator.check_hierarchy_async(
            "root-123", root_entry=entry, mode=FreshnessMode.IMMEDIATE
        )

        mock_batch_client.execute_async.assert_not_called()
        assert result.is_fresh is True
        assert result.action == "use_cache"

    @pytest.mark.asyncio
    async def test_check_hierarchy_eventual_non_expired(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test hierarchy check with EVENTUAL mode and non-expired entry."""
        entry = make_entry("root-123", ttl=300, cached_ago_seconds=0)

        result = await coordinator.check_hierarchy_async(
            "root-123", root_entry=entry, mode=FreshnessMode.EVENTUAL
        )

        mock_batch_client.execute_async.assert_not_called()
        assert result.is_fresh is True
        assert result.action == "use_cache"

    @pytest.mark.asyncio
    async def test_check_hierarchy_strict_unchanged(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test hierarchy check with STRICT mode and unchanged entry."""
        entry = make_entry("root-123", modified_at="2025-12-23T10:00:00.000Z")

        mock_batch_client.execute_async.return_value = [
            make_batch_result("root-123", "2025-12-23T10:00:00.000Z")
        ]

        result = await coordinator.check_hierarchy_async(
            "root-123", root_entry=entry, mode=FreshnessMode.STRICT
        )

        mock_batch_client.execute_async.assert_called_once()
        assert result.is_fresh is True
        assert result.action == "extend_ttl"

    @pytest.mark.asyncio
    async def test_check_hierarchy_strict_changed(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test hierarchy check with STRICT mode and changed entry."""
        entry = make_entry("root-123", modified_at="2025-12-23T10:00:00.000Z")

        mock_batch_client.execute_async.return_value = [
            make_batch_result("root-123", "2025-12-23T12:00:00.000Z")  # Changed
        ]

        result = await coordinator.check_hierarchy_async(
            "root-123", root_entry=entry, mode=FreshnessMode.STRICT
        )

        assert result.is_fresh is False
        assert result.action == "fetch"

    @pytest.mark.asyncio
    async def test_check_hierarchy_no_batch_client(self) -> None:
        """Test hierarchy check with no batch client."""
        coordinator = FreshnessCoordinator(batch_client=None)
        entry = make_entry("root-123")

        result = await coordinator.check_hierarchy_async(
            "root-123", root_entry=entry, mode=FreshnessMode.STRICT
        )

        assert result.is_fresh is False
        assert result.action == "fetch"

    @pytest.mark.asyncio
    async def test_check_hierarchy_api_error(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test hierarchy check handles API errors gracefully."""
        entry = make_entry("root-123", ttl=1, cached_ago_seconds=100)

        mock_batch_client.execute_async.side_effect = ConnectionError("Network error")

        result = await coordinator.check_hierarchy_async(
            "root-123", root_entry=entry, mode=FreshnessMode.EVENTUAL
        )

        assert result.is_fresh is False
        assert result.action == "fetch"


class TestFreshnessCoordinatorStats:
    """Tests for statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that stats are tracked correctly."""
        # Create mix of entries
        fresh_entry = make_entry("fresh", ttl=300, cached_ago_seconds=0)
        stale_entry = make_entry(
            "stale",
            modified_at="2025-12-23T10:00:00.000Z",
            ttl=1,
            cached_ago_seconds=100,
        )

        mock_batch_client.execute_async.return_value = [
            # Stale entry has new version
            make_batch_result("stale", "2025-12-23T12:00:00.000Z")
        ]

        await coordinator.check_batch_async(
            [fresh_entry, stale_entry], mode=FreshnessMode.EVENTUAL
        )

        stats = coordinator.get_stats()
        assert stats["total_checks"] == 2
        assert stats["fresh_count"] == 1  # fresh_entry
        assert stats["stale_count"] == 1  # stale_entry changed
        assert stats["api_calls"] == 1

    @pytest.mark.asyncio
    async def test_reset_stats(self, coordinator: FreshnessCoordinator) -> None:
        """Test that reset_stats clears all statistics."""
        entries = [make_entry("123")]
        await coordinator.check_batch_async(entries, mode=FreshnessMode.IMMEDIATE)

        assert coordinator.get_stats()["total_checks"] > 0

        coordinator.reset_stats()

        stats = coordinator.get_stats()
        for value in stats.values():
            assert value == 0


class TestFreshnessCoordinatorVersionComparison:
    """Tests for version comparison logic."""

    @pytest.mark.asyncio
    async def test_same_version_is_fresh(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that same version is considered fresh."""
        entry = make_entry(
            "123", modified_at="2025-12-23T10:00:00.000Z", ttl=1, cached_ago_seconds=100
        )

        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", "2025-12-23T10:00:00.000Z")
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert results[0].is_fresh is True

    @pytest.mark.asyncio
    async def test_older_api_version_is_fresh(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that cached version newer than API is considered fresh."""
        # Cached version is newer (shouldn't happen in practice but test the logic)
        entry = make_entry(
            "123", modified_at="2025-12-23T12:00:00.000Z", ttl=1, cached_ago_seconds=100
        )

        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", "2025-12-23T10:00:00.000Z")  # API says older
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        # Cached is newer or equal, so fresh
        assert results[0].is_fresh is True

    @pytest.mark.asyncio
    async def test_newer_api_version_is_stale(
        self, coordinator: FreshnessCoordinator, mock_batch_client: MagicMock
    ) -> None:
        """Test that newer API version means cached is stale."""
        entry = make_entry(
            "123", modified_at="2025-12-23T10:00:00.000Z", ttl=1, cached_ago_seconds=100
        )

        mock_batch_client.execute_async.return_value = [
            make_batch_result("123", "2025-12-23T14:00:00.000Z")  # 4 hours newer
        ]

        results = await coordinator.check_batch_async(
            [entry], mode=FreshnessMode.STRICT
        )

        assert results[0].is_fresh is False
        assert results[0].current_version is not None
