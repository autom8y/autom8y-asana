"""Tests for hierarchy warming pacing (batched dispatch).

Per ADR-hierarchy-backpressure-hardening: Validates that Phase 1 immediate
parent fetches use batched pacing when parent count exceeds threshold,
preventing 429 bursts from unbounded asyncio.gather().
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.cache.providers.unified import UnifiedTaskStore


def _make_task(
    gid: str,
    parent_gid: str | None = None,
    modified_at: str = "2025-12-23T10:00:00.000Z",
) -> dict:
    """Create a minimal test task dict."""
    task: dict = {
        "gid": gid,
        "name": f"Task {gid}",
        "modified_at": modified_at,
    }
    if parent_gid:
        task["parent"] = {"gid": parent_gid}
    return task


def _make_parent_response(gid: str) -> MagicMock:
    """Create a mock parent task response from tasks_client.get_async."""
    mock = MagicMock()
    mock.model_dump.return_value = {
        "gid": gid,
        "name": f"Parent {gid}",
        "parent": None,
        "custom_fields": [],
    }
    return mock


@pytest.fixture
def mock_cache_provider() -> MagicMock:
    """Create a mock CacheProvider that tracks cached entries.

    After set_versioned or set_batch, subsequent get_versioned calls
    return a sentinel so Phase 2 (warm_ancestors) skips re-fetching.
    """
    provider = MagicMock()
    _stored: dict[str, object] = {}

    def _get_versioned(gid: str, entry_type: EntryType) -> object | None:
        return _stored.get(gid)

    def _set_versioned(gid: str, entry: object, **kwargs: object) -> None:
        _stored[gid] = entry

    def _set_batch(entries: dict, **kwargs: object) -> None:
        for gid, entry in entries.items():
            _stored[gid] = entry

    provider.get_versioned = MagicMock(side_effect=_get_versioned)
    provider.set_versioned = MagicMock(side_effect=_set_versioned)
    provider.get_batch = MagicMock(return_value={})
    provider.set_batch = MagicMock(side_effect=_set_batch)
    provider.invalidate = MagicMock()
    return provider


@pytest.fixture
def mock_tasks_client() -> MagicMock:
    """Create a mock TasksClient that returns parent responses."""
    client = MagicMock()

    # Default: return a parent task for any GID
    async def _get_async(gid: str, **kwargs):  # noqa: ANN003
        return _make_parent_response(gid)

    client.get_async = AsyncMock(side_effect=_get_async)
    return client


@pytest.fixture
def store(mock_cache_provider: MagicMock) -> UnifiedTaskStore:
    """Create a UnifiedTaskStore with mocks."""
    return UnifiedTaskStore(
        cache=mock_cache_provider,
        batch_client=MagicMock(),
        freshness_mode=FreshnessMode.EVENTUAL,
    )


class TestHierarchyPacingThreshold:
    """Tests for pacing activation based on parent count threshold."""

    @pytest.mark.asyncio
    async def test_small_section_no_pacing(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Sections with fewer than HIERARCHY_PACING_THRESHOLD parents
        use unbounded asyncio.gather (no sleep calls)."""
        # Create 50 tasks each with a unique parent (below threshold of 100)
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(50)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )
            # No sleep should be called for small sections
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_large_section_pacing_activates(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Sections with more than HIERARCHY_PACING_THRESHOLD parents
        activate batched pacing with sleep between batches."""
        # Create 120 tasks each with a unique parent (above threshold of 100)
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )
            # With 120 parents and batch size 50: 3 batches, 2 pauses
            assert mock_sleep.call_count == 2


class TestHierarchyBatchSizing:
    """Tests for correct batch sizing and delay insertion."""

    @pytest.mark.asyncio
    async def test_batch_count_calculation(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Verify the correct number of batches and pauses for various sizes."""
        # 150 parents / 50 per batch = 3 batches, 2 pauses
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(150)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )
            assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_exact_batch_boundary_no_trailing_sleep(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """When parent count is exact multiple of batch size, no trailing sleep."""
        # 200 parents / 50 per batch = 4 batches, 3 pauses (no pause after last)
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(200)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )
            assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    async def test_sleep_uses_configured_delay(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Sleep calls use HIERARCHY_BATCH_DELAY value."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            with patch("autom8_asana.config.HIERARCHY_BATCH_DELAY", 2.5):
                await store.put_batch_async(
                    tasks,
                    warm_hierarchy=True,
                    tasks_client=mock_tasks_client,
                )
                for call in mock_sleep.call_args_list:
                    assert call[0][0] == 2.5


class TestHierarchyPacingResults:
    """Tests for correct parent fetch results regardless of pacing mode."""

    @pytest.mark.asyncio
    async def test_all_parents_fetched_without_pacing(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """All parents are fetched correctly in non-paced mode."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(30)]

        await store.put_batch_async(
            tasks,
            warm_hierarchy=True,
            tasks_client=mock_tasks_client,
        )

        # All 30 unique parents should have been fetched
        assert mock_tasks_client.get_async.call_count == 30

    @pytest.mark.asyncio
    async def test_all_parents_fetched_with_pacing(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """All parents are fetched correctly in paced mode."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )

        # All 120 unique parents should have been fetched
        assert mock_tasks_client.get_async.call_count == 120

    @pytest.mark.asyncio
    async def test_deduplication_preserves_with_pacing(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Parent deduplication works correctly in paced mode.

        Multiple tasks sharing the same parent should result in only
        one fetch per unique parent GID.
        """
        # 200 tasks all sharing 110 unique parents (above threshold)
        tasks = [
            _make_task(f"task-{i}", parent_gid=f"parent-{i % 110}") for i in range(200)
        ]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )

        # Only 110 unique parents should have been fetched
        assert mock_tasks_client.get_async.call_count == 110


class TestHierarchyPacingLogging:
    """Tests for structured log events emitted during paced hierarchy warming."""

    @pytest.mark.asyncio
    async def test_pacing_enabled_log_emitted(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """hierarchy_pacing_enabled log is emitted when pacing activates."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            with patch("autom8_asana.cache.providers.unified.logger") as mock_logger:
                await store.put_batch_async(
                    tasks,
                    warm_hierarchy=True,
                    tasks_client=mock_tasks_client,
                )

                # Find the hierarchy_pacing_enabled log call
                info_calls = [
                    c
                    for c in mock_logger.info.call_args_list
                    if c[0][0] == "hierarchy_pacing_enabled"
                ]
                assert len(info_calls) == 1
                extra = info_calls[0][1]["extra"]
                assert extra["parent_count"] == 120
                assert extra["batch_size"] == 50
                assert extra["batch_delay"] == 1.0

    @pytest.mark.asyncio
    async def test_warming_complete_log_emitted(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """hierarchy_warming_complete log is emitted after paced warming."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            with patch("autom8_asana.cache.providers.unified.logger") as mock_logger:
                await store.put_batch_async(
                    tasks,
                    warm_hierarchy=True,
                    tasks_client=mock_tasks_client,
                )

                # Find the hierarchy_warming_complete log call
                info_calls = [
                    c
                    for c in mock_logger.info.call_args_list
                    if c[0][0] == "hierarchy_warming_complete"
                ]
                assert len(info_calls) == 1
                extra = info_calls[0][1]["extra"]
                assert extra["parents_fetched"] == 120
                assert extra["total_parents"] == 120
                assert extra["batches"] == 3  # ceil(120/50) = 3

    @pytest.mark.asyncio
    async def test_batch_pause_log_emitted(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """hierarchy_batch_pause log is emitted between batches."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            with patch("autom8_asana.cache.providers.unified.logger") as mock_logger:
                await store.put_batch_async(
                    tasks,
                    warm_hierarchy=True,
                    tasks_client=mock_tasks_client,
                )

                # Find the hierarchy_batch_pause log calls
                debug_calls = [
                    c
                    for c in mock_logger.debug.call_args_list
                    if c[0][0] == "hierarchy_batch_pause"
                ]
                # 3 batches = 2 pauses
                assert len(debug_calls) == 2

    @pytest.mark.asyncio
    async def test_no_pacing_logs_for_small_section(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """No pacing-specific logs are emitted for sections below threshold."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(50)]

        with patch("autom8_asana.cache.providers.unified.logger") as mock_logger:
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )

            # No pacing-specific log events
            info_calls = [
                c
                for c in mock_logger.info.call_args_list
                if c[0][0] in ("hierarchy_pacing_enabled", "hierarchy_warming_complete")
            ]
            assert len(info_calls) == 0
