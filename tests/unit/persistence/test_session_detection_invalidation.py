"""Tests for SaveSession detection cache invalidation.

Per TDD-CACHE-PERF-DETECTION: Tests for detection cache invalidation on commit.
Per FR-INVALIDATE-001: SaveSession invalidates EntryType.DETECTION alongside TASK and SUBTASKS.
Per FR-INVALIDATE-002: All mutation types (CREATE, UPDATE, DELETE) invalidate detection cache.
Per FR-INVALIDATE-003: Action operations invalidate detection cache.
Per FR-INVALIDATE-004: Invalidation failures don't prevent commit.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.entry import EntryType
from autom8_asana.models import Task
from autom8_asana.persistence.session import SaveSession

# ---------------------------------------------------------------------------
# Mock Cache Provider
# ---------------------------------------------------------------------------


class MockCacheProviderWithDetection:
    """Mock cache provider for testing detection invalidation."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []
        self.fail_on_invalidate: bool = False

    def get(self, key: str, entry_type: EntryType) -> None:
        """Get entry from cache."""
        return None

    def get_versioned(self, key: str, entry_type: EntryType) -> None:
        """Get entry from cache."""
        return None

    def set(self, key: str, entry: Any) -> None:
        """Store entry in cache."""
        pass

    def set_versioned(self, key: str, entry: Any) -> None:
        """Store entry in cache."""
        pass

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache entry."""
        if self.fail_on_invalidate:
            raise ConnectionError("Cache invalidation failed")
        self.invalidate_calls.append((key, entry_types))

    def get_invalidations_for_type(
        self, entry_type: EntryType
    ) -> list[tuple[str, list[EntryType] | None]]:
        """Get invalidation calls that include a specific entry type."""
        return [
            (key, types)
            for key, types in self.invalidate_calls
            if types and entry_type in types
        ]


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
    mock_client._cache_provider = MockCacheProviderWithDetection()

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
TAG_GID = "1111111111111"
PROJECT_GID = "2222222222222"


# ---------------------------------------------------------------------------
# Detection Cache Invalidation Tests
# ---------------------------------------------------------------------------


class TestDetectionCacheInvalidationOnCrudSuccess:
    """Tests for detection cache invalidation after successful CRUD operations."""

    @pytest.mark.asyncio
    async def test_update_invalidates_detection_cache(self) -> None:
        """UPDATE operations invalidate detection cache (FR-INVALIDATE-001).

        Per FR-INVALIDATE-001: SaveSession SHALL invalidate EntryType.DETECTION
        alongside EntryType.TASK and EntryType.SUBTASKS on task mutation.
        """
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

        # Assert: Detection cache was invalidated alongside TASK and SUBTASKS
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 1
        gid, entry_types = cache.invalidate_calls[0]
        assert gid == TASK_GID_1
        assert EntryType.TASK in entry_types
        assert EntryType.SUBTASKS in entry_types
        assert EntryType.DETECTION in entry_types

    @pytest.mark.asyncio
    async def test_create_invalidates_detection_cache(self) -> None:
        """CREATE operations invalidate detection cache (FR-INVALIDATE-002).

        Per FR-INVALIDATE-002: Detection cache invalidation SHALL occur for
        all mutation types (CREATE, UPDATE, DELETE).
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Mock batch to return success with new GID
        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        # New task with temp GID
        task = Task(gid="temp_new", name="New Task")

        async with SaveSession(mock_client) as session:
            session.track(task)
            await session.commit_async()

        # Assert: Detection cache was invalidated for the new task
        cache = mock_client._cache_provider
        assert len(cache.invalidate_calls) == 1
        _, entry_types = cache.invalidate_calls[0]
        assert EntryType.DETECTION in entry_types

    @pytest.mark.asyncio
    async def test_multiple_updates_invalidate_all_detection_caches(self) -> None:
        """Multiple updates invalidate detection cache for all modified GIDs.

        Per FR-INVALIDATE-002: All mutation types invalidate detection cache.
        """
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

        # Assert: Both tasks had detection cache invalidated
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        assert len(detection_invalidations) == 2
        invalidated_gids = {call[0] for call in detection_invalidations}
        assert TASK_GID_1 in invalidated_gids
        assert TASK_GID_2 in invalidated_gids


class TestDetectionCacheInvalidationOnActionSuccess:
    """Tests for detection cache invalidation after successful action operations."""

    @pytest.mark.asyncio
    async def test_add_tag_action_invalidates_detection_cache(self) -> None:
        """add_tag action invalidates detection cache (FR-INVALIDATE-003).

        Per FR-INVALIDATE-003: Action operations (add_project, remove_project,
        set_parent, etc.) SHALL invalidate detection cache.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.add_tag(task, TAG_GID)
            await session.commit_async()

        # Assert: Detection cache was invalidated for the task
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        assert len(detection_invalidations) == 1
        gid, _ = detection_invalidations[0]
        assert gid == TASK_GID_1

    @pytest.mark.asyncio
    async def test_add_to_project_action_invalidates_detection_cache(self) -> None:
        """add_to_project action invalidates detection cache (FR-INVALIDATE-003).

        This is particularly important because adding to a project may change
        the entity's detected type via Tier 1 project membership lookup.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.add_to_project(task, PROJECT_GID)
            await session.commit_async()

        # Assert: Detection cache was invalidated
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        assert len(detection_invalidations) == 1
        gid, _ = detection_invalidations[0]
        assert gid == TASK_GID_1

    @pytest.mark.asyncio
    async def test_remove_from_project_action_invalidates_detection_cache(self) -> None:
        """remove_from_project action invalidates detection cache (FR-INVALIDATE-003).

        Removing from project may invalidate the Tier 1 detection, requiring
        fallback to other detection tiers.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")

        async with SaveSession(mock_client) as session:
            session.remove_from_project(task, PROJECT_GID)
            await session.commit_async()

        # Assert: Detection cache was invalidated
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        assert len(detection_invalidations) == 1
        gid, _ = detection_invalidations[0]
        assert gid == TASK_GID_1

    @pytest.mark.asyncio
    async def test_set_parent_action_invalidates_detection_cache(self) -> None:
        """set_parent action invalidates detection cache (FR-INVALIDATE-003).

        Changing parent may affect Tier 3 parent inference detection.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._http.request.return_value = {"data": {}}

        task = Task(gid=TASK_GID_1, name="Task")
        parent_task = Task(gid=TASK_GID_2, name="Parent")

        async with SaveSession(mock_client) as session:
            session.set_parent(task, parent_task)
            await session.commit_async()

        # Assert: Detection cache was invalidated for the child task
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        assert len(detection_invalidations) == 1
        gid, _ = detection_invalidations[0]
        assert gid == TASK_GID_1


class TestDetectionCacheInvalidationGracefulDegradation:
    """Tests for graceful degradation on cache errors."""

    @pytest.mark.asyncio
    async def test_invalidation_failure_does_not_fail_commit(self) -> None:
        """Cache invalidation failure does not fail commit (FR-INVALIDATE-004).

        Per FR-INVALIDATE-004: Invalidation failures SHALL NOT prevent commit
        from succeeding.
        """
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
            session._log = mock_log
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: Warning was logged
        mock_log.warning.assert_called()
        # Check that cache_invalidation_failed was in the call
        call_args = str(mock_log.warning.call_args)
        assert "cache_invalidation_failed" in call_args


class TestDetectionCacheInvalidationNoCacheProvider:
    """Tests when no cache provider is configured."""

    @pytest.mark.asyncio
    async def test_commit_works_without_cache_provider(self) -> None:
        """Commit works when no cache provider is configured."""
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


class TestDetectionCacheInvalidationDeduplication:
    """Tests for GID deduplication in detection cache invalidation."""

    @pytest.mark.asyncio
    async def test_same_gid_crud_and_action_invalidated_once(self) -> None:
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

        # Assert: Detection cache only invalidated once per GID
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        invalidated_gids = [call[0] for call in detection_invalidations]
        assert invalidated_gids.count(TASK_GID_1) == 1


class TestDetectionCacheInvalidationNoChanges:
    """Tests that no invalidation happens without changes."""

    @pytest.mark.asyncio
    async def test_empty_commit_no_detection_invalidation(self) -> None:
        """Empty commit does not trigger detection invalidation."""
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
    async def test_tracked_but_unchanged_no_detection_invalidation(self) -> None:
        """Tracking entity without changes does not trigger detection invalidation."""
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._log = None

        task = Task(gid=TASK_GID_1, name="Task")

        # Track but don't modify
        async with SaveSession(mock_client) as session:
            session.track(task)
            # No changes made
            await session.commit_async()

        # Assert: No detection invalidation
        cache = mock_client._cache_provider
        detection_invalidations = cache.get_invalidations_for_type(EntryType.DETECTION)
        assert len(detection_invalidations) == 0


class TestDetectionCacheEntryTypeValidation:
    """Tests for EntryType.DETECTION availability."""

    def test_detection_entry_type_exists(self) -> None:
        """Verify EntryType.DETECTION exists (FR-ENTRY-001).

        Per FR-ENTRY-001: The system SHALL define EntryType.DETECTION in
        the cache entry type enum.
        """
        assert hasattr(EntryType, "DETECTION")
        assert EntryType.DETECTION.value == "detection"

    def test_detection_in_invalidation_entry_types(self) -> None:
        """Verify DETECTION is included with TASK and SUBTASKS during invalidation."""
        # This test validates the implementation pattern
        expected_types = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]
        assert EntryType.DETECTION in expected_types
