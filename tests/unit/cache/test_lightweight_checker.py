"""Tests for LightweightChecker.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Validates batch format, chunking,
response parsing, and partial failure handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.lightweight_checker import (
    ASANA_BATCH_LIMIT,
    LightweightChecker,
    _chunk,
)


@pytest.fixture
def mock_batch_client() -> MagicMock:
    """Create a mock BatchClient."""
    client = MagicMock()
    client.execute_async = AsyncMock(return_value=[])
    return client


@pytest.fixture
def checker(mock_batch_client: MagicMock) -> LightweightChecker:
    """Create a LightweightChecker with mock batch client."""
    return LightweightChecker(batch_client=mock_batch_client)


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


class TestLightweightChecker:
    """Tests for LightweightChecker."""

    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty_dict(
        self, checker: LightweightChecker
    ) -> None:
        """Test that empty batch returns empty dict."""
        result = await checker.check_batch_async([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_builds_correct_batch_requests(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that batch requests have correct format with opt_fields=modified_at."""
        entries = [make_entry("123"), make_entry("456")]

        mock_batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:00:00.000Z"}
                },
            ),
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "456", "modified_at": "2025-12-23T11:00:00.000Z"}
                },
            ),
        ]

        await checker.check_batch_async(entries)

        # Verify execute_async was called
        mock_batch_client.execute_async.assert_called_once()
        requests = mock_batch_client.execute_async.call_args[0][0]

        # Verify request format (per FR-STALE-002)
        assert len(requests) == 2
        assert requests[0].relative_path == "/tasks/123"
        assert requests[0].method == "GET"
        assert requests[0].options == {"opt_fields": "modified_at"}
        assert requests[1].relative_path == "/tasks/456"
        assert requests[1].method == "GET"

    @pytest.mark.asyncio
    async def test_parses_successful_responses(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test parsing of successful batch responses."""
        entries = [make_entry("123"), make_entry("456")]

        mock_batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:30:00.000Z"}
                },
            ),
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "456", "modified_at": "2025-12-24T08:15:00.000Z"}
                },
            ),
        ]

        result = await checker.check_batch_async(entries)

        assert result == {
            "123": "2025-12-23T10:30:00.000Z",
            "456": "2025-12-24T08:15:00.000Z",
        }

    @pytest.mark.asyncio
    async def test_handles_deleted_entity_404(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that 404 responses return None for deleted entities."""
        entries = [make_entry("123"), make_entry("456")]

        mock_batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:30:00.000Z"}
                },
            ),
            BatchResult(
                status_code=404,
                body={"errors": [{"message": "Not found"}]},
            ),
        ]

        result = await checker.check_batch_async(entries)

        assert result["123"] == "2025-12-23T10:30:00.000Z"
        assert result["456"] is None

    @pytest.mark.asyncio
    async def test_handles_partial_failure(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that partial failures are handled gracefully (FR-DEGRADE-003)."""
        entries = [make_entry("123"), make_entry("456"), make_entry("789")]

        mock_batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "123", "modified_at": "2025-12-23T10:30:00.000Z"}
                },
            ),
            BatchResult(
                status_code=500,
                body={"errors": [{"message": "Internal error"}]},
            ),
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": "789", "modified_at": "2025-12-24T09:00:00.000Z"}
                },
            ),
        ]

        result = await checker.check_batch_async(entries)

        assert result["123"] == "2025-12-23T10:30:00.000Z"
        assert result["456"] is None  # Failed
        assert result["789"] == "2025-12-24T09:00:00.000Z"

    @pytest.mark.asyncio
    async def test_handles_malformed_response(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that malformed responses return None."""
        entries = [make_entry("123")]

        mock_batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={"data": {"gid": "123"}},  # Missing modified_at
            ),
        ]

        result = await checker.check_batch_async(entries)

        assert result["123"] is None

    @pytest.mark.asyncio
    async def test_chunks_large_batches(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that batches larger than 10 are chunked (FR-BATCH-003)."""
        # Create 25 entries (should be 3 chunks: 10, 10, 5)
        entries = [make_entry(str(i)) for i in range(25)]

        # Mock responses for each chunk
        def make_response(gids: list[str]) -> list[BatchResult]:
            return [
                BatchResult(
                    status_code=200,
                    body={
                        "data": {"gid": gid, "modified_at": "2025-12-23T10:00:00.000Z"}
                    },
                )
                for gid in gids
            ]

        # Return different responses for each call
        mock_batch_client.execute_async.side_effect = [
            make_response([str(i) for i in range(10)]),
            make_response([str(i) for i in range(10, 20)]),
            make_response([str(i) for i in range(20, 25)]),
        ]

        result = await checker.check_batch_async(entries)

        # Verify 3 chunks were executed
        assert mock_batch_client.execute_async.call_count == 3

        # Verify first chunk has 10 items
        first_call_requests = mock_batch_client.execute_async.call_args_list[0][0][0]
        assert len(first_call_requests) == 10

        # Verify last chunk has 5 items
        last_call_requests = mock_batch_client.execute_async.call_args_list[2][0][0]
        assert len(last_call_requests) == 5

        # Verify all 25 results are present
        assert len(result) == 25

    @pytest.mark.asyncio
    async def test_chunk_failure_doesnt_affect_other_chunks(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that one chunk failing doesn't affect other chunks."""
        entries = [make_entry(str(i)) for i in range(15)]

        # First chunk succeeds, second fails
        mock_batch_client.execute_async.side_effect = [
            [
                BatchResult(
                    status_code=200,
                    body={
                        "data": {
                            "gid": str(i),
                            "modified_at": "2025-12-23T10:00:00.000Z",
                        }
                    },
                )
                for i in range(10)
            ],
            Exception("Network error"),
        ]

        result = await checker.check_batch_async(entries)

        # First 10 should succeed
        for i in range(10):
            assert result[str(i)] == "2025-12-23T10:00:00.000Z"

        # Last 5 should be None due to chunk failure
        for i in range(10, 15):
            assert result[str(i)] is None

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, checker: LightweightChecker, mock_batch_client: MagicMock
    ) -> None:
        """Test that stats are tracked correctly."""
        entries = [make_entry(str(i)) for i in range(5)]

        mock_batch_client.execute_async.return_value = [
            BatchResult(
                status_code=200,
                body={
                    "data": {"gid": str(i), "modified_at": "2025-12-23T10:00:00.000Z"}
                },
            )
            for i in range(5)
        ]

        await checker.check_batch_async(entries)

        stats = checker.get_stats()
        assert stats["total_checks"] == 5
        assert stats["total_api_calls"] == 1  # One chunk for 5 entries


class TestChunkFunction:
    """Tests for the _chunk helper function."""

    def test_empty_list(self) -> None:
        """Test chunking empty list."""
        assert _chunk([], 10) == []

    def test_single_item(self) -> None:
        """Test chunking single item."""
        assert _chunk(["a"], 10) == [["a"]]

    def test_exact_chunk_size(self) -> None:
        """Test chunking exact multiple of chunk size."""
        items = ["a", "b", "c", "d"]
        assert _chunk(items, 2) == [["a", "b"], ["c", "d"]]

    def test_partial_last_chunk(self) -> None:
        """Test chunking with partial last chunk."""
        items = ["a", "b", "c", "d", "e"]
        assert _chunk(items, 2) == [["a", "b"], ["c", "d"], ["e"]]

    def test_chunk_larger_than_list(self) -> None:
        """Test chunk size larger than list."""
        items = ["a", "b"]
        assert _chunk(items, 10) == [["a", "b"]]

    def test_asana_batch_limit(self) -> None:
        """Test chunking at Asana's 10-action limit."""
        items = [str(i) for i in range(25)]
        chunks = _chunk(items, ASANA_BATCH_LIMIT)

        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5
