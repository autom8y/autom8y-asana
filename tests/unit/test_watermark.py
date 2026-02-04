"""Tests for WatermarkRepository.

Tests cover:
- Singleton pattern enforcement
- Thread-safe concurrent access
- get/set watermark operations
- Timezone-aware datetime validation
- get_all_watermarks returns copy
- clear_watermark operation
- reset() clears singleton state

Per TDD-materialization-layer FR-001:
WatermarkRepository provides centralized timestamp tracking for per-project
modified_since sync.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from autom8_asana.dataframes.watermark import WatermarkRepository, get_watermark_repo


class TestWatermarkRepositorySingleton:
    """Tests for singleton pattern enforcement."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_get_instance_returns_singleton(self) -> None:
        """get_instance() returns the same instance on repeated calls."""
        repo1 = WatermarkRepository.get_instance()
        repo2 = WatermarkRepository.get_instance()

        assert repo1 is repo2

    def test_direct_instantiation_returns_singleton(self) -> None:
        """Direct instantiation via WatermarkRepository() returns singleton."""
        repo1 = WatermarkRepository()
        repo2 = WatermarkRepository()

        assert repo1 is repo2

    def test_get_watermark_repo_returns_singleton(self) -> None:
        """get_watermark_repo() module function returns singleton."""
        repo1 = get_watermark_repo()
        repo2 = get_watermark_repo()

        assert repo1 is repo2

    def test_reset_clears_singleton(self) -> None:
        """reset() clears the singleton so next access creates fresh instance."""
        repo1 = WatermarkRepository.get_instance()
        repo1.set_watermark("project-123", datetime.now(UTC))

        WatermarkRepository.reset()

        repo2 = WatermarkRepository.get_instance()

        # New instance should be different object with empty state
        assert repo1 is not repo2
        assert repo2.get_watermark("project-123") is None


class TestWatermarkOperations:
    """Tests for get/set watermark operations."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_get_watermark_returns_none_for_unknown_project(self) -> None:
        """get_watermark() returns None for project with no watermark."""
        repo = get_watermark_repo()

        result = repo.get_watermark("unknown-project")

        assert result is None

    def test_set_and_get_watermark(self) -> None:
        """set_watermark() stores value retrievable via get_watermark()."""
        repo = get_watermark_repo()
        now = datetime.now(UTC)

        repo.set_watermark("project-123", now)

        assert repo.get_watermark("project-123") == now

    def test_set_watermark_updates_existing(self) -> None:
        """set_watermark() updates existing watermark for project."""
        repo = get_watermark_repo()
        first = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        second = datetime(2024, 6, 15, 18, 30, 0, tzinfo=UTC)

        repo.set_watermark("project-123", first)
        repo.set_watermark("project-123", second)

        assert repo.get_watermark("project-123") == second

    def test_set_watermark_rejects_naive_datetime(self) -> None:
        """set_watermark() raises ValueError for naive (non-timezone-aware) datetime."""
        repo = get_watermark_repo()
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValueError, match="timezone-aware"):
            repo.set_watermark("project-123", naive_dt)

    def test_multiple_projects_independent(self) -> None:
        """Watermarks for different projects are stored independently."""
        repo = get_watermark_repo()
        wm1 = datetime(2024, 1, 1, tzinfo=UTC)
        wm2 = datetime(2024, 6, 1, tzinfo=UTC)
        wm3 = datetime(2024, 12, 1, tzinfo=UTC)

        repo.set_watermark("project-a", wm1)
        repo.set_watermark("project-b", wm2)
        repo.set_watermark("project-c", wm3)

        assert repo.get_watermark("project-a") == wm1
        assert repo.get_watermark("project-b") == wm2
        assert repo.get_watermark("project-c") == wm3


class TestGetAllWatermarks:
    """Tests for get_all_watermarks() method."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_get_all_watermarks_empty(self) -> None:
        """get_all_watermarks() returns empty dict when no watermarks set."""
        repo = get_watermark_repo()

        result = repo.get_all_watermarks()

        assert result == {}

    def test_get_all_watermarks_returns_all(self) -> None:
        """get_all_watermarks() returns all stored watermarks."""
        repo = get_watermark_repo()
        wm1 = datetime(2024, 1, 1, tzinfo=UTC)
        wm2 = datetime(2024, 6, 1, tzinfo=UTC)

        repo.set_watermark("project-a", wm1)
        repo.set_watermark("project-b", wm2)

        result = repo.get_all_watermarks()

        assert result == {"project-a": wm1, "project-b": wm2}

    def test_get_all_watermarks_returns_copy(self) -> None:
        """get_all_watermarks() returns a copy to prevent external modification."""
        repo = get_watermark_repo()
        wm = datetime(2024, 1, 1, tzinfo=UTC)
        repo.set_watermark("project-123", wm)

        result = repo.get_all_watermarks()

        # Modify the returned dict
        result["project-456"] = datetime(2024, 12, 1, tzinfo=UTC)
        result.pop("project-123")

        # Original should be unchanged
        assert repo.get_watermark("project-123") == wm
        assert repo.get_watermark("project-456") is None


class TestClearWatermark:
    """Tests for clear_watermark() method."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_clear_watermark_removes_existing(self) -> None:
        """clear_watermark() removes watermark for specified project."""
        repo = get_watermark_repo()
        wm = datetime(2024, 1, 1, tzinfo=UTC)
        repo.set_watermark("project-123", wm)

        repo.clear_watermark("project-123")

        assert repo.get_watermark("project-123") is None

    def test_clear_watermark_no_error_for_unknown(self) -> None:
        """clear_watermark() does not raise for unknown project."""
        repo = get_watermark_repo()

        # Should not raise
        repo.clear_watermark("unknown-project")

        assert repo.get_watermark("unknown-project") is None

    def test_clear_watermark_only_affects_target(self) -> None:
        """clear_watermark() only removes watermark for specified project."""
        repo = get_watermark_repo()
        wm1 = datetime(2024, 1, 1, tzinfo=UTC)
        wm2 = datetime(2024, 6, 1, tzinfo=UTC)
        repo.set_watermark("project-a", wm1)
        repo.set_watermark("project-b", wm2)

        repo.clear_watermark("project-a")

        assert repo.get_watermark("project-a") is None
        assert repo.get_watermark("project-b") == wm2


class TestThreadSafety:
    """Tests for thread-safe concurrent access."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_concurrent_singleton_access(self) -> None:
        """Multiple threads get the same singleton instance."""
        instances: list[WatermarkRepository] = []
        lock = threading.Lock()

        def get_instance() -> None:
            inst = WatermarkRepository.get_instance()
            with lock:
                instances.append(inst)

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert len(instances) == 10
        assert all(inst is instances[0] for inst in instances)

    def test_concurrent_set_watermark(self) -> None:
        """Multiple threads can safely set watermarks concurrently."""
        repo = get_watermark_repo()

        def set_watermark(project_id: int) -> None:
            wm = datetime(2024, 1, project_id % 28 + 1, tzinfo=UTC)
            repo.set_watermark(f"project-{project_id}", wm)

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(set_watermark, range(100)))

        # All watermarks should be set
        all_wm = repo.get_all_watermarks()
        assert len(all_wm) == 100

    def test_concurrent_get_and_set(self) -> None:
        """Concurrent get and set operations are thread-safe."""
        repo = get_watermark_repo()
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            try:
                for i in range(50):
                    project = f"project-{thread_id}-{i}"
                    wm = datetime(2024, 1, 1, tzinfo=UTC)
                    repo.set_watermark(project, wm)
                    result = repo.get_watermark(project)
                    assert result == wm
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_empty_project_gid(self) -> None:
        """Empty string project GID is valid (though unusual)."""
        repo = get_watermark_repo()
        wm = datetime(2024, 1, 1, tzinfo=UTC)

        repo.set_watermark("", wm)

        assert repo.get_watermark("") == wm

    def test_special_characters_in_project_gid(self) -> None:
        """Project GID with special characters works correctly."""
        repo = get_watermark_repo()
        wm = datetime(2024, 1, 1, tzinfo=UTC)
        special_gid = "project-123_test/foo:bar"

        repo.set_watermark(special_gid, wm)

        assert repo.get_watermark(special_gid) == wm

    def test_watermark_with_microseconds(self) -> None:
        """Watermark with microsecond precision is preserved."""
        repo = get_watermark_repo()
        wm = datetime(2024, 1, 15, 12, 30, 45, 123456, tzinfo=UTC)

        repo.set_watermark("project-123", wm)

        assert repo.get_watermark("project-123") == wm
        assert repo.get_watermark("project-123").microsecond == 123456

    def test_min_datetime_value(self) -> None:
        """Minimum datetime value is handled correctly."""
        repo = get_watermark_repo()
        wm = datetime.min.replace(tzinfo=UTC)

        repo.set_watermark("project-123", wm)

        assert repo.get_watermark("project-123") == wm

    def test_max_datetime_value(self) -> None:
        """Maximum datetime value is handled correctly."""
        repo = get_watermark_repo()
        wm = datetime.max.replace(tzinfo=UTC)

        repo.set_watermark("project-123", wm)

        assert repo.get_watermark("project-123") == wm


class TestPersistenceIntegration:
    """Tests for WatermarkRepository persistence integration."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        WatermarkRepository.reset()

    def test_set_persistence_configures_repository(self) -> None:
        """set_persistence() stores the persistence layer."""
        from unittest.mock import MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()

        repo.set_persistence(mock_persistence)

        assert repo._persistence is mock_persistence

    def test_set_persistence_can_be_disabled(self) -> None:
        """set_persistence(None) disables persistence."""
        from unittest.mock import MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        repo.set_persistence(mock_persistence)

        repo.set_persistence(None)

        assert repo._persistence is None

    def test_get_instance_with_persistence(self) -> None:
        """get_instance() can configure persistence on first call."""
        from unittest.mock import MagicMock

        mock_persistence = MagicMock()

        repo = WatermarkRepository.get_instance(persistence=mock_persistence)

        assert repo._persistence is mock_persistence

    def test_get_instance_does_not_override_persistence(self) -> None:
        """get_instance() does not override already-set persistence."""
        from unittest.mock import MagicMock

        first_persistence = MagicMock()
        second_persistence = MagicMock()

        repo1 = WatermarkRepository.get_instance(persistence=first_persistence)
        repo2 = WatermarkRepository.get_instance(persistence=second_persistence)

        # Should still be first persistence
        assert repo1._persistence is first_persistence
        assert repo2._persistence is first_persistence

    def test_set_watermark_without_persistence_does_not_error(self) -> None:
        """set_watermark() works normally without persistence configured."""
        repo = get_watermark_repo()
        wm = datetime(2024, 6, 15, tzinfo=UTC)

        # Should not raise
        repo.set_watermark("project-123", wm)

        assert repo.get_watermark("project-123") == wm

    @pytest.mark.asyncio
    async def test_set_watermark_triggers_async_persist(self) -> None:
        """set_watermark() triggers async persist when persistence configured."""
        from unittest.mock import AsyncMock, MagicMock, patch

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        mock_persistence.save_watermark = AsyncMock(return_value=True)
        repo.set_persistence(mock_persistence)

        wm = datetime(2024, 6, 15, tzinfo=UTC)

        # Create a mock loop.create_task to capture the coroutine
        with patch.object(repo, "_schedule_persist") as mock_schedule:
            repo.set_watermark("project-123", wm)

            # Verify schedule_persist was called
            mock_schedule.assert_called_once_with("project-123", wm, mock_persistence)

    @pytest.mark.asyncio
    async def test_persist_watermark_calls_persistence(self) -> None:
        """_persist_watermark() calls persistence.save_watermark()."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        mock_persistence.save_watermark = AsyncMock(return_value=True)

        wm = datetime(2024, 6, 15, tzinfo=UTC)

        await repo._persist_watermark("project-123", wm, mock_persistence)

        mock_persistence.save_watermark.assert_awaited_once_with("project-123", wm)

    @pytest.mark.asyncio
    async def test_persist_watermark_handles_failure_gracefully(self) -> None:
        """_persist_watermark() catches and logs exceptions."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        mock_persistence.save_watermark = AsyncMock(
            side_effect=ConnectionError("S3 error")
        )

        wm = datetime(2024, 6, 15, tzinfo=UTC)

        # Should not raise
        await repo._persist_watermark("project-123", wm, mock_persistence)

    @pytest.mark.asyncio
    async def test_load_from_persistence_hydrates_watermarks(self) -> None:
        """load_from_persistence() loads watermarks into repository."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()

        wm1 = datetime(2024, 1, 1, tzinfo=UTC)
        wm2 = datetime(2024, 6, 1, tzinfo=UTC)
        mock_persistence.load_all_watermarks = AsyncMock(
            return_value={"proj-1": wm1, "proj-2": wm2}
        )

        loaded = await repo.load_from_persistence(mock_persistence)

        assert loaded == 2
        assert repo.get_watermark("proj-1") == wm1
        assert repo.get_watermark("proj-2") == wm2

    @pytest.mark.asyncio
    async def test_load_from_persistence_uses_configured_persistence(self) -> None:
        """load_from_persistence() uses configured persistence if none passed."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        mock_persistence.load_all_watermarks = AsyncMock(return_value={})
        repo.set_persistence(mock_persistence)

        await repo.load_from_persistence()

        mock_persistence.load_all_watermarks.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_load_from_persistence_returns_zero_without_persistence(self) -> None:
        """load_from_persistence() returns 0 when no persistence configured."""
        repo = get_watermark_repo()

        loaded = await repo.load_from_persistence()

        assert loaded == 0

    @pytest.mark.asyncio
    async def test_load_from_persistence_returns_zero_on_empty(self) -> None:
        """load_from_persistence() returns 0 when S3 has no watermarks."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        mock_persistence.load_all_watermarks = AsyncMock(return_value={})

        loaded = await repo.load_from_persistence(mock_persistence)

        assert loaded == 0

    @pytest.mark.asyncio
    async def test_load_from_persistence_handles_error_gracefully(self) -> None:
        """load_from_persistence() catches exceptions and returns 0."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_persistence = MagicMock()
        mock_persistence.load_all_watermarks = AsyncMock(
            side_effect=ConnectionError("S3 error")
        )

        loaded = await repo.load_from_persistence(mock_persistence)

        assert loaded == 0

    @pytest.mark.asyncio
    async def test_load_from_persistence_merges_with_existing(self) -> None:
        """load_from_persistence() merges with existing in-memory watermarks."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()

        # Set existing watermark
        existing_wm = datetime(2024, 3, 15, tzinfo=UTC)
        repo.set_watermark("existing-proj", existing_wm)

        # Load from persistence
        mock_persistence = MagicMock()
        new_wm = datetime(2024, 6, 1, tzinfo=UTC)
        mock_persistence.load_all_watermarks = AsyncMock(
            return_value={"new-proj": new_wm}
        )

        await repo.load_from_persistence(mock_persistence)

        # Both should exist
        assert repo.get_watermark("existing-proj") == existing_wm
        assert repo.get_watermark("new-proj") == new_wm


class TestDataFrameStorageIntegration:
    """Tests for WatermarkRepository with DataFrameStorage protocol.

    Per TDD-UNIFIED-DF-PERSISTENCE-001 Phase 3: WatermarkRepository
    accepts both DataFramePersistence (legacy) and S3DataFrameStorage
    (unified protocol) as its persistence backend.
    """

    def setup_method(self) -> None:
        WatermarkRepository.reset()

    def teardown_method(self) -> None:
        WatermarkRepository.reset()

    def test_set_persistence_accepts_storage_protocol(self) -> None:
        """set_persistence() accepts a DataFrameStorage implementation."""
        from unittest.mock import MagicMock

        repo = get_watermark_repo()
        mock_storage = MagicMock()
        mock_storage.is_available = True

        repo.set_persistence(mock_storage)
        assert repo._persistence is mock_storage

    @pytest.mark.asyncio
    async def test_persist_watermark_via_storage_protocol(self) -> None:
        """_persist_watermark() calls storage.save_watermark()."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_storage = MagicMock()
        mock_storage.save_watermark = AsyncMock(return_value=True)

        wm = datetime(2026, 2, 4, tzinfo=UTC)
        await repo._persist_watermark("proj_123", wm, mock_storage)

        mock_storage.save_watermark.assert_awaited_once_with("proj_123", wm)

    @pytest.mark.asyncio
    async def test_load_from_persistence_via_storage_protocol(self) -> None:
        """load_from_persistence() works with DataFrameStorage."""
        from unittest.mock import AsyncMock, MagicMock

        repo = get_watermark_repo()
        mock_storage = MagicMock()
        wm1 = datetime(2026, 1, 1, tzinfo=UTC)
        wm2 = datetime(2026, 2, 1, tzinfo=UTC)
        mock_storage.load_all_watermarks = AsyncMock(
            return_value={"proj_a": wm1, "proj_b": wm2}
        )

        loaded = await repo.load_from_persistence(mock_storage)

        assert loaded == 2
        assert repo.get_watermark("proj_a") == wm1
        assert repo.get_watermark("proj_b") == wm2

    @pytest.mark.asyncio
    async def test_set_watermark_triggers_persist_via_storage(self) -> None:
        """set_watermark() triggers persist through DataFrameStorage."""
        from unittest.mock import MagicMock, patch

        repo = get_watermark_repo()
        mock_storage = MagicMock()
        mock_storage.is_available = True
        repo.set_persistence(mock_storage)

        wm = datetime(2026, 2, 4, tzinfo=UTC)

        with patch.object(repo, "_schedule_persist") as mock_schedule:
            repo.set_watermark("proj_123", wm)
            mock_schedule.assert_called_once_with("proj_123", wm, mock_storage)

    def test_get_instance_accepts_storage_protocol(self) -> None:
        """get_instance() accepts DataFrameStorage as persistence arg."""
        from unittest.mock import MagicMock

        mock_storage = MagicMock()
        mock_storage.is_available = True

        repo = WatermarkRepository.get_instance(persistence=mock_storage)
        assert repo._persistence is mock_storage
