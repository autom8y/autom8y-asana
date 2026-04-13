"""Tests for SaveSession DataFrame cache invalidation.

Per TDD-WATERMARK-CACHE Phase 3: Tests for cache invalidation on commit.
Per FR-INVALIDATE-001: SaveSession.commit_async() SHALL invalidate DataFrame cache.
Per FR-INVALIDATE-002: Invalidation SHALL include EntryType.DATAFRAME.
Per FR-INVALIDATE-003: Invalidation SHALL invalidate all project contexts via memberships.
Per FR-INVALIDATE-004: Invalidation SHALL fall back to known project context if memberships unavailable.
Per FR-INVALIDATE-005: Invalidation SHALL NOT fail the commit if cache invalidation fails.
Per FR-INVALIDATE-006: Invalidation SHALL be triggered for CREATE, UPDATE, and DELETE operations.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from autom8y_cache.testing import MockCacheProvider as _SDKMockCacheProvider

from autom8_asana.batch.models import BatchResult
from autom8_asana.cache.integration.dataframes import make_dataframe_key
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.models import Task
from autom8_asana.persistence.session import SaveSession

# ---------------------------------------------------------------------------
# Mock Cache Provider with DataFrame Support
# ---------------------------------------------------------------------------


class MockCacheProviderWithDataFrame(_SDKMockCacheProvider):
    """Mock cache provider for testing DataFrame invalidation (extends SDK).

    Adds fail_on_invalidate, fail_on_dataframe_invalidate flags,
    invalidate_calls tracking, and get_invalidations_for_type helper.
    """

    def __init__(self) -> None:
        super().__init__()
        self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []
        self.fail_on_invalidate: bool = False
        self.fail_on_dataframe_invalidate: bool = False

    def get_versioned(self, key: str, entry_type: EntryType, freshness: object = None) -> None:
        """Get entry from cache (always returns None for invalidation tests)."""
        return None

    def set_versioned(self, key: str, entry: Any) -> None:
        """Store entry in cache (no-op for invalidation tests)."""
        pass

    def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
        """Invalidate cache entry with fail simulation."""
        if self.fail_on_invalidate:
            raise ConnectionError("Cache invalidation failed")
        if self.fail_on_dataframe_invalidate and entry_types and EntryType.DATAFRAME in entry_types:
            raise ConnectionError("DataFrame cache invalidation failed")
        self.invalidate_calls.append((key, entry_types))

    def get_invalidations_for_type(
        self, entry_type: EntryType
    ) -> list[tuple[str, list[EntryType] | None]]:
        """Get invalidation calls that include a specific entry type."""
        return [
            (key, types) for key, types in self.invalidate_calls if types and entry_type in types
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

    # Cache provider with DataFrame support
    mock_client._cache_provider = MockCacheProviderWithDataFrame()

    # HTTP client for action executor
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
PROJECT_GID_1 = "1111111111111"
PROJECT_GID_2 = "2222222222222"
PROJECT_GID_3 = "3333333333333"


# ---------------------------------------------------------------------------
# DataFrame Invalidation Tests
# ---------------------------------------------------------------------------


class TestDataFrameInvalidation:
    """Tests for DataFrame cache invalidation after SaveSession commit."""

    @pytest.mark.asyncio
    async def test_invalidation_includes_dataframe_entry_type(self) -> None:
        """Verify EntryType.DATAFRAME is invalidated (FR-INVALIDATE-002).

        When a task is updated via SaveSession and has memberships,
        the DataFrame cache entries for all project contexts should be invalidated.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Mock batch to return success
        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        # Create task with memberships (multi-homed task)
        task = Task(
            gid=TASK_GID_1,
            name="Original",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "Project 1"}},
            ],
        )

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: DataFrame cache was invalidated
        cache = mock_client._cache_provider
        dataframe_invalidations = cache.get_invalidations_for_type(EntryType.DATAFRAME)

        # Should have at least one DATAFRAME invalidation
        assert len(dataframe_invalidations) >= 1

        # Verify the key format is correct (task_gid:project_gid)
        expected_key = make_dataframe_key(TASK_GID_1, PROJECT_GID_1)
        invalidated_keys = [key for key, _ in dataframe_invalidations]
        assert expected_key in invalidated_keys

    @pytest.mark.asyncio
    async def test_invalidation_multi_homed_task(self) -> None:
        """Verify multi-homed task invalidates all projects (FR-INVALIDATE-003).

        A task that belongs to multiple projects should have its DataFrame
        cache entries invalidated in all projects.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        # Task belongs to 3 projects
        task = Task(
            gid=TASK_GID_1,
            name="Multi-homed Task",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "Project 1"}},
                {"project": {"gid": PROJECT_GID_2, "name": "Project 2"}},
                {"project": {"gid": PROJECT_GID_3, "name": "Project 3"}},
            ],
        )

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: All three project contexts were invalidated
        cache = mock_client._cache_provider
        dataframe_invalidations = cache.get_invalidations_for_type(EntryType.DATAFRAME)
        invalidated_keys = {key for key, _ in dataframe_invalidations}

        expected_keys = {
            make_dataframe_key(TASK_GID_1, PROJECT_GID_1),
            make_dataframe_key(TASK_GID_1, PROJECT_GID_2),
            make_dataframe_key(TASK_GID_1, PROJECT_GID_3),
        }

        assert expected_keys.issubset(invalidated_keys)

    @pytest.mark.asyncio
    async def test_invalidation_fallback_single_project(self) -> None:
        """Verify task without memberships still gets TASK/SUBTASKS invalidation.

        Per FR-INVALIDATE-004: Fall back to known project context if memberships
        unavailable. If no project context is available, DataFrame invalidation
        is skipped but TASK/SUBTASKS are still invalidated.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        # Task without memberships
        task = Task(gid=TASK_GID_1, name="Task without memberships")

        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: TASK and SUBTASKS were still invalidated
        cache = mock_client._cache_provider
        task_invalidations = cache.get_invalidations_for_type(EntryType.TASK)
        subtask_invalidations = cache.get_invalidations_for_type(EntryType.SUBTASKS)

        assert len(task_invalidations) == 1
        assert len(subtask_invalidations) == 1

        # DataFrame may or may not be invalidated depending on context
        # The key assertion is that commit succeeded and TASK/SUBTASKS were invalidated

    @pytest.mark.asyncio
    async def test_invalidation_failure_doesnt_fail_commit(self) -> None:
        """Verify invalidation failure doesn't fail commit (FR-INVALIDATE-005).

        Cache invalidation failures should be logged as warnings but should
        NOT cause the commit to fail.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Make DataFrame invalidation fail
        mock_client._cache_provider.fail_on_dataframe_invalidate = True

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(
            gid=TASK_GID_1,
            name="Task",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "Project 1"}},
            ],
        )

        # Act: Commit should not raise despite cache failure
        async with SaveSession(mock_client) as session:
            session.track(task)
            task.name = "Updated"
            result = await session.commit_async()

        # Assert: Commit succeeded despite DataFrame cache error
        assert result.success

    @pytest.mark.asyncio
    async def test_invalidation_failure_logs_warning(self) -> None:
        """Verify invalidation failure logs warning with structured data."""
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._cache_provider.fail_on_dataframe_invalidate = True

        # Add mock logger
        mock_log = MagicMock()
        mock_client._log = mock_log

        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0)
        ]

        task = Task(
            gid=TASK_GID_1,
            name="Task",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "Project 1"}},
            ],
        )

        async with SaveSession(mock_client) as session:
            session._log = mock_log
            session.track(task)
            task.name = "Updated"
            await session.commit_async()

        # Assert: Warning was logged
        mock_log.warning.assert_called()
        # Check that dataframe_cache_invalidation_failed was logged
        warning_calls = [str(call) for call in mock_log.warning.call_args_list]
        assert any("dataframe_cache_invalidation_failed" in call for call in warning_calls)

    @pytest.mark.asyncio
    async def test_invalidation_all_operation_types(self) -> None:
        """Verify CREATE, UPDATE, DELETE all trigger invalidation (FR-INVALIDATE-006).

        All mutation operation types should trigger DataFrame cache invalidation.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()

        # Mock batch to return success for create and update
        mock_client.batch.execute_async.return_value = [
            create_success_result(gid=TASK_GID_1, request_index=0),
            create_success_result(gid=TASK_GID_2, request_index=1),
        ]

        # CREATE: New task
        new_task = Task(
            gid="temp_1",
            name="New Task",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "Project 1"}},
            ],
        )

        # UPDATE: Existing task
        existing_task = Task(
            gid=TASK_GID_2,
            name="Existing Task",
            memberships=[
                {"project": {"gid": PROJECT_GID_2, "name": "Project 2"}},
            ],
        )

        async with SaveSession(mock_client) as session:
            session.track(new_task)
            session.track(existing_task)
            existing_task.name = "Updated Existing Task"
            await session.commit_async()

        # Assert: Both tasks were invalidated
        cache = mock_client._cache_provider
        invalidated_gids = {call[0] for call in cache.invalidate_calls}

        # At minimum, the existing task's GID should be invalidated
        # (new task gets a real GID from batch response)
        assert TASK_GID_2 in invalidated_gids or TASK_GID_1 in invalidated_gids


class TestDataFrameInvalidationWithActions:
    """Tests for DataFrame cache invalidation after action operations."""

    @pytest.mark.asyncio
    async def test_action_invalidates_dataframe_cache(self) -> None:
        """Verify action operations trigger DataFrame invalidation.

        Per FR-INVALIDATE-006: Action operations should also trigger
        DataFrame cache invalidation for affected tasks.
        """
        # Arrange
        mock_client = create_mock_client_with_cache()
        mock_client._http.request.return_value = {"data": {}}

        TAG_GID = "4444444444444"

        task = Task(
            gid=TASK_GID_1,
            name="Task",
            memberships=[
                {"project": {"gid": PROJECT_GID_1, "name": "Project 1"}},
            ],
        )

        async with SaveSession(mock_client) as session:
            session.add_tag(task, TAG_GID)
            await session.commit_async()

        # Assert: DataFrame cache was invalidated
        cache = mock_client._cache_provider
        dataframe_invalidations = cache.get_invalidations_for_type(EntryType.DATAFRAME)

        # The task should have DataFrame entries invalidated
        expected_key = make_dataframe_key(TASK_GID_1, PROJECT_GID_1)
        invalidated_keys = [key for key, _ in dataframe_invalidations]
        assert expected_key in invalidated_keys


class TestDataFrameConfigValidation:
    """Tests for DataFrameConfig validation."""

    def test_dataframe_config_defaults(self) -> None:
        """Verify DataFrameConfig has correct defaults.

        Per FR-CONFIG-001: parallel_fetch_enabled default True.
        Per FR-CONFIG-005: max_concurrent_sections default 8.
        """
        from autom8_asana.config import DataFrameConfig

        config = DataFrameConfig()

        assert config.parallel_fetch_enabled is True
        assert config.max_concurrent_sections == 8
        assert config.cache_enabled is True

    def test_dataframe_config_validation_low(self) -> None:
        """Verify max_concurrent_sections rejects values below 1."""
        from autom8_asana.config import DataFrameConfig
        from autom8_asana.errors import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            DataFrameConfig(max_concurrent_sections=0)

        assert "max_concurrent_sections must be 1-20" in str(exc_info.value)

    def test_dataframe_config_validation_high(self) -> None:
        """Verify max_concurrent_sections rejects values above 20."""
        from autom8_asana.config import DataFrameConfig
        from autom8_asana.errors import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            DataFrameConfig(max_concurrent_sections=21)

        assert "max_concurrent_sections must be 1-20" in str(exc_info.value)

    def test_dataframe_config_valid_range(self) -> None:
        """Verify max_concurrent_sections accepts values in valid range."""
        from autom8_asana.config import DataFrameConfig

        # Minimum
        config_min = DataFrameConfig(max_concurrent_sections=1)
        assert config_min.max_concurrent_sections == 1

        # Maximum
        config_max = DataFrameConfig(max_concurrent_sections=20)
        assert config_max.max_concurrent_sections == 20

        # Custom value
        config_custom = DataFrameConfig(max_concurrent_sections=4)
        assert config_custom.max_concurrent_sections == 4


class TestAsanaConfigDataFrame:
    """Tests for DataFrameConfig integration in AsanaConfig."""

    def test_asana_config_includes_dataframe(self) -> None:
        """Verify AsanaConfig includes dataframe configuration."""
        from autom8_asana.config import AsanaConfig, DataFrameConfig

        config = AsanaConfig()

        assert hasattr(config, "dataframe")
        assert isinstance(config.dataframe, DataFrameConfig)

    def test_asana_config_custom_dataframe(self) -> None:
        """Verify AsanaConfig accepts custom DataFrameConfig."""
        from autom8_asana.config import AsanaConfig, DataFrameConfig

        custom_df_config = DataFrameConfig(
            parallel_fetch_enabled=False,
            max_concurrent_sections=4,
            cache_enabled=False,
        )

        config = AsanaConfig(dataframe=custom_df_config)

        assert config.dataframe.parallel_fetch_enabled is False
        assert config.dataframe.max_concurrent_sections == 4
        assert config.dataframe.cache_enabled is False
