"""Tests for hierarchy warming pacing (batched dispatch).

Per ADR-hierarchy-backpressure-hardening: Validates that Phase 1 immediate
parent fetches use batched pacing when parent count exceeds threshold,
preventing 429 bursts from unbounded asyncio.gather().
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.providers.unified import UnifiedTaskStore
from autom8_asana.settings import reset_settings

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import EntryType


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
        freshness_mode=FreshnessIntent.EVENTUAL,
    )


class TestHierarchyPacingThreshold:
    """Tests for pacing activation based on parent count threshold."""

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

    async def test_sleep_uses_configured_delay(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """Sleep calls use HIERARCHY_BATCH_DELAY value."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with (
            patch(
                "autom8_asana.cache.providers.unified.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            patch.dict(os.environ, {"ASANA_PACING_HIERARCHY_BATCH_DELAY": "2.5"}),
        ):
            reset_settings()
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 2.5
        reset_settings()


class TestHierarchyPacingResults:
    """Tests for correct parent fetch results regardless of pacing mode."""

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

    async def test_all_parents_fetched_with_pacing(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """All parents are fetched correctly in paced mode."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )

        # All 120 unique parents should have been fetched
        assert mock_tasks_client.get_async.call_count == 120

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
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i % 110}") for i in range(200)]

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
            await store.put_batch_async(
                tasks,
                warm_hierarchy=True,
                tasks_client=mock_tasks_client,
            )

        # Only 110 unique parents should have been fetched
        assert mock_tasks_client.get_async.call_count == 110


class TestHierarchyPacingLogging:
    """Tests for structured log events emitted during paced hierarchy warming."""

    async def test_pacing_enabled_log_emitted(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """hierarchy_pacing_enabled log is emitted when pacing activates."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
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

    async def test_warming_complete_log_emitted(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """hierarchy_warming_complete log is emitted after paced warming."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
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

    async def test_batch_pause_log_emitted(
        self,
        store: UnifiedTaskStore,
        mock_tasks_client: MagicMock,
    ) -> None:
        """hierarchy_batch_pause log is emitted between batches."""
        tasks = [_make_task(f"task-{i}", parent_gid=f"parent-{i}") for i in range(120)]

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
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


class TestPacingBoundaryConditions:
    """Exact boundary probes around HIERARCHY_PACING_THRESHOLD (100)."""

    async def test_exactly_100_parents_no_pacing(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """Exactly 100 unique parents: threshold is >, not >=, so no pacing."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(100)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)
            mock_sleep.assert_not_called()

        assert mock_tasks_client.get_async.call_count == 100

    async def test_exactly_101_parents_pacing_activates(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """101 unique parents: pacing must activate (> 100 threshold)."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(101)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)
            # 101 / 50 = 3 batches (50, 50, 1) -> 2 pauses
            assert mock_sleep.call_count == 2

        assert mock_tasks_client.get_async.call_count == 101

    async def test_zero_parents_no_fetches_no_pacing(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """Zero tasks with parents: no fetches, no pacing, no crash."""
        tasks = [_make_task(f"t-{i}") for i in range(10)]  # no parent_gid

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)
            mock_sleep.assert_not_called()

        mock_tasks_client.get_async.assert_not_called()

    async def test_single_parent_no_pacing(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """One task with one parent: minimal case, no pacing."""
        tasks = [_make_task("only-task", parent_gid="only-parent")]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)
            mock_sleep.assert_not_called()

        assert mock_tasks_client.get_async.call_count == 1


class TestPacingBatchEdgeCases:
    """Batch arithmetic edge cases for divisible, non-divisible, and overflow sizes."""

    async def test_not_divisible_151_parents_four_batches(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """151 parents / 50 = 4 batches (50,50,50,1), 3 pauses."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(151)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)
            assert mock_sleep.call_count == 3

        assert mock_tasks_client.get_async.call_count == 151

    async def test_single_batch_above_threshold_with_large_batch_size(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """With HIERARCHY_BATCH_SIZE=200 > 101, only 1 batch, 0 pauses."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(101)]

        with (
            patch(
                "autom8_asana.cache.providers.unified.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            patch.dict(os.environ, {"ASANA_PACING_HIERARCHY_BATCH_SIZE": "200"}),
        ):
            reset_settings()
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)
            mock_sleep.assert_not_called()
        reset_settings()

    async def test_all_parents_fetched_after_batching_250(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """250 parents: all fetched exactly once regardless of batch splitting."""
        n = 250
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(n)]

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=mock_tasks_client)

        fetched_gids = [call.args[0] for call in mock_tasks_client.get_async.call_args_list]
        assert len(fetched_gids) == n
        assert len(set(fetched_gids)) == n


class TestPacingErrorResilience:
    """Verify batch failures do not abort subsequent batches."""

    async def test_partial_failure_continues_subsequent_batches(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Some fetches failing in batch 1 don't prevent batch 2 from executing."""
        n = 120  # 3 batches of 50, 50, 20
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(n)]

        call_count = 0

        async def _flaky_get(gid: str, **kwargs):  # noqa: ANN003
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise ConnectionError("Simulated transient error")
            return _make_parent_response(gid)

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_flaky_get)

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=client)
            # At least 2 batch-pacing sleeps, plus retry backoff sleeps
            assert mock_sleep.call_count >= 2

        # Phase 1 attempts all 120 (with retries for failures), Phase 2 re-attempts uncached
        assert client.get_async.call_count >= n

    async def test_all_fetches_fail_no_crash(self, store: UnifiedTaskStore) -> None:
        """Every fetch failing does not raise an exception."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(110)]

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=ConnectionError("Total failure"))

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=client)

        # With retry (max 3 attempts per parent), 110 parents * 3 = 330 calls
        assert client.get_async.call_count >= 110 * 3

    async def test_failure_in_last_batch_handled_gracefully(self, store: UnifiedTaskStore) -> None:
        """Failures in the final (remainder) batch are handled gracefully."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(110)]

        call_index = 0

        async def _fail_last_batch(gid: str, **kwargs):  # noqa: ANN003
            nonlocal call_index
            call_index += 1
            if 100 < call_index <= 110:  # Fail batch 3 items
                raise ConnectionError("Last batch explodes")
            return _make_parent_response(gid)

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_fail_last_batch)

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=client)

        # With retry, last batch failures get retried → more than 110 calls
        assert client.get_async.call_count >= 110


class TestPacingConcurrencyInteraction:
    """Semaphore limits concurrency within paced batches."""

    async def test_semaphore_limits_concurrency_within_batch(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """Semaphore of 10 ensures concurrent fetches never exceed 10."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _tracking_get(gid: str, **kwargs):  # noqa: ANN003
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.001)
            async with lock:
                current_concurrent -= 1
            return _make_parent_response(gid)

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_tracking_get)

        with patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock):
            await store.put_batch_async(
                [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(120)],
                warm_hierarchy=True,
                tasks_client=client,
            )

        assert max_concurrent <= 10, f"Max concurrency was {max_concurrent}, expected <= 10"


class TestPacingConfigConstants:
    """Configuration constants have sane values and types."""

    def test_threshold_is_positive_int(self) -> None:
        from autom8_asana.config import HIERARCHY_PACING_THRESHOLD

        assert isinstance(HIERARCHY_PACING_THRESHOLD, int)
        assert HIERARCHY_PACING_THRESHOLD > 0

    def test_batch_size_is_positive_int(self) -> None:
        from autom8_asana.config import HIERARCHY_BATCH_SIZE

        assert isinstance(HIERARCHY_BATCH_SIZE, int)
        assert HIERARCHY_BATCH_SIZE >= 1

    def test_batch_delay_is_non_negative_float(self) -> None:
        from autom8_asana.config import HIERARCHY_BATCH_DELAY

        assert isinstance(HIERARCHY_BATCH_DELAY, (int, float))
        assert HIERARCHY_BATCH_DELAY >= 0.0

    def test_batch_size_less_than_threshold(self) -> None:
        """Batch size should be smaller than threshold, otherwise pacing is pointless."""
        from autom8_asana.config import HIERARCHY_BATCH_SIZE, HIERARCHY_PACING_THRESHOLD

        assert HIERARCHY_BATCH_SIZE < HIERARCHY_PACING_THRESHOLD, (
            f"BATCH_SIZE ({HIERARCHY_BATCH_SIZE}) >= THRESHOLD ({HIERARCHY_PACING_THRESHOLD}) "
            "makes pacing pointless"
        )


# =============================================================================
# Retry resilience tests (TDD-CASCADE-RESUME-FIX)
# =============================================================================


class TestFetchImmediateParentRetry:
    """Verify retry with exponential backoff in _fetch_immediate_parent."""

    @pytest.fixture
    def store(self) -> UnifiedTaskStore:
        """Create a store with mocked cache and hierarchy."""
        mock_cache = MagicMock()
        mock_cache.get_versioned.return_value = None  # Parent not cached
        mock_cache.set_batch.return_value = None

        store = UnifiedTaskStore.__new__(UnifiedTaskStore)
        store.cache = mock_cache
        store._hierarchy = MagicMock()
        store._hierarchy_semaphore = asyncio.Semaphore(10)
        store._stats = {"parent_chain_lookups": 0}
        store._tasks_client = None
        store._freshness_intent = FreshnessIntent.IMMEDIATE
        return store

    async def test_retry_succeeds_on_second_attempt(self, store: UnifiedTaskStore) -> None:
        """First attempt fails with transient error, second succeeds."""
        mock_client = MagicMock()
        parent_resp = _make_parent_response("p1")

        # First call raises, second succeeds
        mock_client.get_async = AsyncMock(
            side_effect=[ConnectionError("rate limited"), parent_resp]
        )
        store.put_async = AsyncMock()

        tasks = [_make_task("c1", parent_gid="p1")]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await store._fetch_immediate_parents(tasks, mock_client)

        assert result == 1
        assert mock_client.get_async.call_count == 2
        store._hierarchy.register.assert_called_once()

    async def test_all_retries_exhausted(self, store: UnifiedTaskStore) -> None:
        """All 3 attempts fail — returns 0, does not crash."""
        mock_client = MagicMock()
        mock_client.get_async = AsyncMock(side_effect=ConnectionError("persistent failure"))

        tasks = [_make_task("c1", parent_gid="p1")]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await store._fetch_immediate_parents(tasks, mock_client)

        assert result == 0
        assert mock_client.get_async.call_count == 3
        store._hierarchy.register.assert_not_called()

    async def test_success_on_first_attempt_no_retry(self, store: UnifiedTaskStore) -> None:
        """Successful first attempt does not trigger any retries."""
        mock_client = MagicMock()
        parent_resp = _make_parent_response("p1")
        mock_client.get_async = AsyncMock(return_value=parent_resp)
        store.put_async = AsyncMock()

        tasks = [_make_task("c1", parent_gid="p1")]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await store._fetch_immediate_parents(tasks, mock_client)

        assert result == 1
        assert mock_client.get_async.call_count == 1
        mock_sleep.assert_not_called()
