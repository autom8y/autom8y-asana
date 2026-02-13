"""Tests for SaveSession cache invalidation.

Per TDD-CACHE-INTEGRATION Section 4.6: Tests for cache invalidation on commit.
Per ADR-0125: SaveSession invalidation (post-commit callback).
Per ADR-0127: Graceful degradation on cache errors.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.models import Task
from autom8_asana.persistence.session import SaveSession
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

# ---------------------------------------------------------------------------
# Mock Cache Provider
# ---------------------------------------------------------------------------


class MockCacheProvider(_SDKMockCacheProvider):
    """Mock cache provider for testing invalidation (extends SDK MockCacheProvider).

    Adds fail_on_invalidate flag and satellite-specific invalidate_calls tracking.
    """

    def __init__(self) -> None:
        super().__init__()
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []
        self.fail_on_invalidate: bool = False

    def get_versioned(
        self, key: str, entry_type: EntryType, freshness: object = None
    ) -> None:
        """Get entry from cache (always returns None for invalidation tests)."""
        return None

    def set_versioned(self, key: str, entry: Any) -> None:
        """Store entry in cache (no-op for invalidation tests)."""
        pass

    def invalidate(
        self, key: str, entry_types: list[EntryType] | None = None
    ) -> None:
        """Invalidate cache entry with fail simulation."""
        if self.fail_on_invalidate:
            raise ConnectionError("Cache invalidation failed")
        self.invalidate_calls.append((key, entry_types))


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_client_with_cache() -> MagicMock:
    """Create a mock AsanaClient with cache provider."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None

    # Cache provider
    mock_client._cache_provider = MockCacheProvider()

    # HTTP client for action executor
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


def create_mock_client_without_cache() -> MagicMock:
    """Create a mock AsanaClient without cache provider."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None
    mock_client._cache_provider = None

    # HTTP client
    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


def create_success_result(
    gid: str = "123",
    request_index: int = 0,
) -> BatchResult:
    """Create a successful BatchResult."""
    return BatchResult(
        status_code=200,
        body={"data": {"gid": gid, "name": "Test"}},
        request_index=request_index,
    )


TASK_GID_1 = "1234567890123"
TASK_GID_2 = "9876543210987"
TASK_GID_3 = "5555555555555"
TAG_GID = "1111111111111"
SECTION_GID = "2222222222222"


# ---------------------------------------------------------------------------
# Invalidation Tests
# ---------------------------------------------------------------------------


class TestCacheInvalidationOnCrudSuccess:
    """Tests for cache invalidation after successful CRUD operations."""

    @pytest.mark.asyncio
    async def test_update_invalidates_cache(self) -> None:
        """UPDATE operations invalidate cache (FR-INVALIDATE-002)."""
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Mock batch to return success
        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(gid=TASK_GID_1, name="Original")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: Cache was invalidated for the updated task
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 1
        gid, entry_types = cache.invalidate_calls[0]
        assert gid == TASK_GID_1
        assert EntryType.TASK in entry_types
        assert EntryType.SUBTASKS in entry_types

    @pytest.mark.asyncio
    async def test_multiple_updates_batch_invalidate(self) -> None:
        """Multiple updates invalidate all modified GIDs (FR-INVALIDATE-005)."""
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Mock batch to return success for multiple tasks
        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0),
            create_success_result(gid=TASK_GID_2, request_index=1),
        ]

        task1 = Task(gid=TASK_GID_1, name="Task 1")
        task2 = Task(gid=TASK_GID_2, name="Task 2")

        async with SaveSession(mock_client) as session:
            session.track(task1)
            session.track(task2)
            task1.name = "Updated 1"
            task2.name = "Updated 2"
            await session.commit_async()

        # Assert: Both tasks were invalidated
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 2
        invalidated_gids = {call[0] for call in cache.invalidate_calls}
        assert TASK_GID_1 in invalidated_gids
        assert TASK_GID_2 in invalidated_gids


class TestCacheInvalidationOnActionSuccess:
    """Tests for cache invalidation after successful action operations."""

    @pytest.mark.asyncio
    async def test_add_tag_action_invalidates_cache(self) -> None:
        """add_tag action invalidates cache (FR-INVALIDATE-006)."""
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Mock HTTP for action execution
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.add_tag(task, TAG_GID)
            await session.commit_async()

        # Assert: Cache was invalidated for the task
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 1
        gid, _ = cache.invalidate_calls[0]
        assert gid == TASK_GID_1

    @pytest.mark.asyncio
    async def test_move_to_section_action_invalidates_cache(self) -> None:
        """move_to_section action invalidates cache (FR-INVALIDATE-006)."""
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.move_to_section(task, SECTION_GID)
            await session.commit_async()

        # Assert: Cache was invalidated
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 1
        gid, _ = cache.invalidate_calls[0]
        assert gid == TASK_GID_1


class TestCacheInvalidationDeduplication:
    """Tests for GID deduplication in invalidation."""

    @pytest.mark.asyncio
    async def test_same_gid_invalidated_once(self) -> None:
        """Same GID in CRUD and action is only invalidated once."""
        # Arrange
        mock_client = create_mock_client_with_cache()

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            session.add_tag(task, TAG_GID)
            await session.commit_async()

        # Assert: GID only invalidated once (set deduplication)
        cache = mock_client._cache_provider
        invalidated_gids = [call[0] for call in cache.invalidate_calls]
        assert invalidated_gids.count(TASK_GID_1) == 1


class TestNoCacheProvider:
    """Tests when no cache provider is configured."""

    @pytest.mark.asyncio
    async def test_commit_works_without_cache(self) -> None:
        """commit_async works when no cache provider configured."""
        # Arrange
        mock_client = create_mock_client_without_cache()

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(gid=TASK_GID_1, name="Task")

        # Act: Should not raise
        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()

        # Assert: Commit succeeded
        assert result.success


class TestGracefulDegradation:
    """Tests for graceful degradation on cache errors."""

    @pytest.mark.asyncio
    async def test_invalidation_failure_does_not_fail_commit(self) -> None:
        """Cache invalidation failure does not fail commit (NFR-DEGRADE-001)."""
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Make cache fail on invalidate
        mock_client._cache_provider.fail_on_invalidate = True

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(gid=TASK_GID_1, name="Task")

        # Act: Should not raise despite cache failure
        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()

        # Assert: Commit succeeded despite cache error
        assert result.success

    @pytest.mark.asyncio
    async def test_invalidation_failure_logs_warning(self) -> None:
        """Cache invalidation failure logs warning."""
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._cache_provider.fail_on_invalidate = True

        # Add mock logger
        mock_log = MagicMock()
        mock_client._log = mock_log

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session._log = mock_log  # Set logger on session
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: Warning was logged
        mock_log.warning.assert_called()
        # Check that cache_invalidation_failed was in the call
        call_args = mock_log.warning.call_args
        assert "cache_invalidation_failed" in str(call_args)


class TestNoChangesNoInvalidation:
    """Tests that no invalidation happens without changes."""

    @pytest.mark.asyncio
    async def test_empty_commit_no_invalidation(self) -> None:
        """Empty commit does not trigger invalidation."""
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._log = None

        # Act: Commit with no tracked entities
        async with SaveSession(mock_client) as session:
            await session.commit_async()

        # Assert: No invalidation calls
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 0

    @pytest.mark.asyncio
    async def test_tracked_but_unchanged_no_invalidation(self) -> None:
        """Tracking entity without changes does not trigger invalidation."""
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._log = None

        task = Task(gid=TASK_GID_1, name="Task")

        # Track but don't modify
        async with SaveSession(mock_client) as session:
            session.track(task)
            # No changes made
            await session.commit_async()

        # Assert: No invalidation (no batch operations = no succeeded entities)
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 0


class TestInvalidationEntryTypes:
    """Tests for correct entry types being invalidated."""

    @pytest.mark.asyncio
    async def test_invalidates_task_and_subtasks_types(self) -> None:
        """Invalidation includes TASK, SUBTASKS, and DETECTION entry types.

        Per FR-INVALIDATE-001 (TDD-CACHE-PERF-DETECTION): EntryType.DETECTION
        is invalidated alongside TASK and SUBTASKS on task mutation.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: TASK, SUBTASKS, and DETECTION types invalidated
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 1
        _, entry_types = cache.invalidate_calls[0]
        assert EntryType.TASK in entry_types
        assert EntryType.SUBTASKS in entry_types
        assert EntryType.DETECTION in entry_types
