"""Tests for RequestCoalescer.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Validates window timing, max batch,
deduplication, and concurrent callers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.coalescer import RequestCoalescer
from autom8_asana.cache.entry import CacheEntry, EntryType


@pytest.fixture
def mock_checker() -> MagicMock:
    """Create a mock LightweightChecker."""
    checker = MagicMock()
    checker.check_batch_async = AsyncMock(return_value={})
    return checker


@pytest.fixture
def coalescer(mock_checker: MagicMock) -> RequestCoalescer:
    """Create a RequestCoalescer with mock checker."""
    return RequestCoalescer(
        checker=mock_checker,
        window_ms=50,
        max_batch=100,
    )


def make_entry(gid: str, modified_at: str = "2025-12-23T10:00:00.000Z") -> CacheEntry:
    """Create a test CacheEntry."""
    return CacheEntry(
        key=gid,
        data={"gid": gid, "name": f"Task {gid}"},
        entry_type=EntryType.TASK,
        version=datetime.fromisoformat(modified_at.replace("Z", "+00:00")),
        cached_at=datetime.now(timezone.utc),
        ttl=300,
    )


class TestRequestCoalescer:
    """Tests for RequestCoalescer."""

    @pytest.mark.asyncio
    async def test_single_request_waits_for_window(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that single request waits for coalescing window."""
        entry = make_entry("123")
        mock_checker.check_batch_async.return_value = {"123": "2025-12-23T10:30:00.000Z"}

        result = await coalescer.request_check_async(entry)

        assert result == "2025-12-23T10:30:00.000Z"
        mock_checker.check_batch_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_requests_batched_together(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that concurrent requests are batched together."""
        entries = [make_entry(str(i)) for i in range(5)]
        mock_checker.check_batch_async.return_value = {
            str(i): f"2025-12-23T{10+i}:00:00.000Z" for i in range(5)
        }

        # Submit all requests concurrently
        results = await asyncio.gather(
            *[coalescer.request_check_async(entry) for entry in entries]
        )

        # All should get results
        assert len(results) == 5
        # Should have been a single batch call
        assert mock_checker.check_batch_async.call_count == 1
        # Batch should contain all 5 entries
        call_entries = mock_checker.check_batch_async.call_args[0][0]
        assert len(call_entries) == 5

    @pytest.mark.asyncio
    async def test_deduplication_same_gid(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that duplicate GIDs are deduplicated (FR-BATCH-006)."""
        entry1 = make_entry("123")
        entry2 = make_entry("123")  # Same GID
        entry3 = make_entry("456")

        mock_checker.check_batch_async.return_value = {
            "123": "2025-12-23T10:30:00.000Z",
            "456": "2025-12-23T11:00:00.000Z",
        }

        results = await asyncio.gather(
            coalescer.request_check_async(entry1),
            coalescer.request_check_async(entry2),
            coalescer.request_check_async(entry3),
        )

        # Both requests for "123" get same result
        assert results[0] == "2025-12-23T10:30:00.000Z"
        assert results[1] == "2025-12-23T10:30:00.000Z"
        assert results[2] == "2025-12-23T11:00:00.000Z"

        # Only 2 unique GIDs in batch
        call_entries = mock_checker.check_batch_async.call_args[0][0]
        gids = [e.key for e in call_entries]
        assert len(gids) == 2
        assert set(gids) == {"123", "456"}

        # Stats should track deduplication
        stats = coalescer.get_stats()
        assert stats["total_deduped"] == 1

    @pytest.mark.asyncio
    async def test_max_batch_immediate_flush(
        self, mock_checker: MagicMock
    ) -> None:
        """Test that reaching max batch triggers immediate flush (FR-BATCH-005)."""
        # Create coalescer with small max batch
        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=5000,  # Long window
            max_batch=5,  # Small batch
        )

        entries = [make_entry(str(i)) for i in range(5)]
        mock_checker.check_batch_async.return_value = {
            str(i): "2025-12-23T10:00:00.000Z" for i in range(5)
        }

        # All 5 requests should trigger immediate flush (not wait 5 seconds)
        start = asyncio.get_event_loop().time()
        results = await asyncio.gather(
            *[coalescer.request_check_async(entry) for entry in entries]
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Should complete quickly (not wait for 5 second window)
        assert elapsed < 1.0
        assert len(results) == 5
        mock_checker.check_batch_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_batches_sequential(
        self, mock_checker: MagicMock
    ) -> None:
        """Test that multiple batches are processed sequentially."""
        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=10,
            max_batch=3,
        )

        # Create responses for multiple batches
        mock_checker.check_batch_async.side_effect = [
            {"0": "t0", "1": "t1", "2": "t2"},
            {"3": "t3", "4": "t4"},
        ]

        # First batch - will trigger immediate flush at max
        first_batch = [make_entry(str(i)) for i in range(3)]
        results1 = await asyncio.gather(
            *[coalescer.request_check_async(entry) for entry in first_batch]
        )

        # Wait a bit for the first batch to complete
        await asyncio.sleep(0.05)

        # Second batch
        second_batch = [make_entry(str(i)) for i in range(3, 5)]
        results2 = await asyncio.gather(
            *[coalescer.request_check_async(entry) for entry in second_batch]
        )

        assert results1 == ["t0", "t1", "t2"]
        assert results2 == ["t3", "t4"]
        assert mock_checker.check_batch_async.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_failure_sets_none_results(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that batch failure sets None for all results."""
        entries = [make_entry(str(i)) for i in range(3)]
        mock_checker.check_batch_async.side_effect = Exception("Network error")

        results = await asyncio.gather(
            *[coalescer.request_check_async(entry) for entry in entries]
        )

        # All results should be None
        assert results == [None, None, None]

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that statistics are tracked correctly."""
        entries = [make_entry(str(i)) for i in range(5)]
        mock_checker.check_batch_async.return_value = {
            str(i): "2025-12-23T10:00:00.000Z" for i in range(5)
        }

        await asyncio.gather(
            *[coalescer.request_check_async(entry) for entry in entries]
        )

        stats = coalescer.get_stats()
        assert stats["total_requests"] == 5
        assert stats["total_batches"] == 1
        assert stats["total_deduped"] == 0

    @pytest.mark.asyncio
    async def test_flush_pending(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that flush_pending forces immediate flush."""
        entry = make_entry("123")
        mock_checker.check_batch_async.return_value = {"123": "2025-12-23T10:30:00.000Z"}

        # Start a request but don't wait for it
        task = asyncio.create_task(coalescer.request_check_async(entry))

        # Force flush
        await asyncio.sleep(0.01)  # Let the request queue
        await coalescer.flush_pending()

        # Request should complete
        result = await task
        assert result == "2025-12-23T10:30:00.000Z"

    @pytest.mark.asyncio
    async def test_window_timing(self, mock_checker: MagicMock) -> None:
        """Test that window timing works correctly."""
        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=100,  # 100ms window
            max_batch=100,
        )

        entry = make_entry("123")
        mock_checker.check_batch_async.return_value = {"123": "2025-12-23T10:30:00.000Z"}

        start = asyncio.get_event_loop().time()
        await coalescer.request_check_async(entry)
        elapsed = (asyncio.get_event_loop().time() - start) * 1000

        # Should take approximately 100ms (window time)
        # Allow some tolerance for timing variations
        assert 50 < elapsed < 200

    @pytest.mark.asyncio
    async def test_concurrent_callers_get_same_result_for_same_gid(
        self, coalescer: RequestCoalescer, mock_checker: MagicMock
    ) -> None:
        """Test that concurrent callers for same GID share result."""
        entry = make_entry("123")
        mock_checker.check_batch_async.return_value = {"123": "2025-12-23T10:30:00.000Z"}

        # Many concurrent requests for same GID
        results = await asyncio.gather(
            *[coalescer.request_check_async(make_entry("123")) for _ in range(10)]
        )

        # All should get same result
        assert all(r == "2025-12-23T10:30:00.000Z" for r in results)

        # Only one API call should have been made
        assert mock_checker.check_batch_async.call_count == 1

        # Only one entry in the batch
        call_entries = mock_checker.check_batch_async.call_args[0][0]
        assert len(call_entries) == 1


class TestRequestCoalescerConfiguration:
    """Tests for coalescer configuration."""

    def test_default_configuration(self, mock_checker: MagicMock) -> None:
        """Test default configuration values."""
        coalescer = RequestCoalescer(checker=mock_checker)
        assert coalescer.window_ms == 50
        assert coalescer.max_batch == 100

    def test_custom_configuration(self, mock_checker: MagicMock) -> None:
        """Test custom configuration values."""
        coalescer = RequestCoalescer(
            checker=mock_checker,
            window_ms=100,
            max_batch=50,
        )
        assert coalescer.window_ms == 100
        assert coalescer.max_batch == 50
