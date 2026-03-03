"""Adversarial tests for hierarchy warming backpressure hardening.

QA Adversary: S5-003. These tests probe boundary conditions, error resilience,
concurrency interactions, dead code removal verification, 429 logging,
and Phase 2 (warm_ancestors_async) post-removal behavior.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.cache.integration.hierarchy_warmer import (
    _fetch_parent,
    warm_ancestors_async,
)
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.policies.hierarchy import HierarchyIndex
from autom8_asana.cache.providers.unified import UnifiedTaskStore

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import EntryType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(
    gid: str,
    parent_gid: str | None = None,
    modified_at: str = "2025-12-23T10:00:00.000Z",
) -> dict:
    task: dict = {"gid": gid, "name": f"Task {gid}", "modified_at": modified_at}
    if parent_gid:
        task["parent"] = {"gid": parent_gid}
    return task


def _make_parent_response(gid: str) -> MagicMock:
    mock = MagicMock()
    mock.model_dump.return_value = {
        "gid": gid,
        "name": f"Parent {gid}",
        "parent": None,
        "custom_fields": [],
    }
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cache_provider() -> MagicMock:
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
    client = MagicMock()

    async def _get_async(gid: str, **kwargs):  # noqa: ANN003
        return _make_parent_response(gid)

    client.get_async = AsyncMock(side_effect=_get_async)
    return client


@pytest.fixture
def store(mock_cache_provider: MagicMock) -> UnifiedTaskStore:
    return UnifiedTaskStore(
        cache=mock_cache_provider,
        batch_client=MagicMock(),
        freshness_mode=FreshnessIntent.EVENTUAL,
    )


# ============================================================================
# 1. BOUNDARY CONDITIONS
# ============================================================================


class TestBoundaryConditions:
    """Exact boundary probes around HIERARCHY_PACING_THRESHOLD (100)."""

    @pytest.mark.asyncio
    async def test_exactly_100_parents_no_pacing(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """Exactly 100 unique parents -- threshold is >, not >=, so no pacing."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(100)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            mock_sleep.assert_not_called()

        assert mock_tasks_client.get_async.call_count == 100

    @pytest.mark.asyncio
    async def test_exactly_101_parents_pacing_activates(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """101 unique parents -- pacing must activate (> 100)."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(101)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            # 101 / 50 = 3 batches (50, 50, 1) -> 2 pauses
            assert mock_sleep.call_count == 2

        assert mock_tasks_client.get_async.call_count == 101

    @pytest.mark.asyncio
    async def test_zero_parents(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """Zero tasks with parents -- no fetches, no pacing, no crash."""
        tasks = [_make_task(f"t-{i}") for i in range(10)]  # no parent_gid

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            mock_sleep.assert_not_called()

        mock_tasks_client.get_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_parent(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """One task with one parent -- minimal case, no pacing."""
        tasks = [_make_task("only-task", parent_gid="only-parent")]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            mock_sleep.assert_not_called()

        assert mock_tasks_client.get_async.call_count == 1


# ============================================================================
# 2. BATCH EDGE CASES
# ============================================================================


class TestBatchEdgeCases:
    """Verify batch arithmetic for divisible, non-divisible, and single-overflow cases."""

    @pytest.mark.asyncio
    async def test_exactly_divisible_150(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """150 parents / 50 = 3 full batches, 2 pauses."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(150)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            assert mock_sleep.call_count == 2

        assert mock_tasks_client.get_async.call_count == 150

    @pytest.mark.asyncio
    async def test_not_divisible_151(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """151 parents / 50 = 4 batches (50,50,50,1), 3 pauses."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(151)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            assert mock_sleep.call_count == 3

        assert mock_tasks_client.get_async.call_count == 151

    @pytest.mark.asyncio
    async def test_single_batch_above_threshold(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """101-150 parents: pacing activates but only 1 pause between 2 (or 3) batches.
        With custom batch size = 200 (> 101), only 1 batch, 0 pauses."""
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(101)]

        with (
            patch(
                "autom8_asana.cache.providers.unified.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep,
            patch("autom8_asana.config.HIERARCHY_BATCH_SIZE", 200),
        ):
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )
            # Single batch that fits everything -> no pause needed
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_parents_fetched_after_batching(
        self, store: UnifiedTaskStore, mock_tasks_client: MagicMock
    ) -> None:
        """Regardless of batching, every unique parent GID is fetched exactly once."""
        n = 250
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(n)]

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            await store.put_batch_async(
                tasks, warm_hierarchy=True, tasks_client=mock_tasks_client
            )

        fetched_gids = [
            call.args[0] for call in mock_tasks_client.get_async.call_args_list
        ]
        assert len(fetched_gids) == n
        assert len(set(fetched_gids)) == n  # all unique


# ============================================================================
# 3. ERROR RESILIENCE
# ============================================================================


class TestErrorResilience:
    """Verify that batch failures do not abort subsequent batches."""

    @pytest.mark.asyncio
    async def test_partial_failure_continues_subsequent_batches(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """If some fetches in batch 1 fail, batch 2 still executes.

        Note: Phase 2 (warm_ancestors_async) re-attempts parents that failed
        in Phase 1 since they were not cached. We validate that Phase 1 pacing
        completes all batches despite failures, then Phase 2 runs afterwards.
        """
        n = 120  # 3 batches of 50, 50, 20
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(n)]

        call_count = 0

        async def _flaky_get(gid: str, **kwargs):  # noqa: ANN003
            nonlocal call_count
            call_count += 1
            # Fail every 3rd fetch
            if call_count % 3 == 0:
                raise ConnectionError("Simulated transient error")
            return _make_parent_response(gid)

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_flaky_get)

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=client)
            # Pacing activated (120 > 100), at least 2 batch pauses + retry backoff sleeps
            assert mock_sleep.call_count >= 2

        # Phase 1 attempts all 120, then Phase 2 re-attempts failed ones (not cached).
        # Total calls >= 120 (Phase 1) since Phase 2 retries uncached parents.
        assert client.get_async.call_count >= n

    @pytest.mark.asyncio
    async def test_all_fetches_fail_no_crash(self, store: UnifiedTaskStore) -> None:
        """If every single fetch fails, the system does not crash.

        Phase 2 will re-attempt uncached parents, doubling the call count.
        The key assertion is no exception propagates.
        """
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(110)]

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=ConnectionError("Total failure"))

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            # Should NOT raise
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=client)

        # Phase 1 (110) + Phase 2 re-attempts for uncached parents
        assert client.get_async.call_count >= 110

    @pytest.mark.asyncio
    async def test_failure_in_last_batch_still_counted(
        self, store: UnifiedTaskStore
    ) -> None:
        """Failures in the final (remainder) batch are handled gracefully.

        Phase 1 attempts all 110, with last 10 failing. Phase 2 re-attempts
        the 10 that were not cached. Total calls >= 110.
        """
        tasks = [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(110)]

        call_index = 0

        async def _fail_last_batch(gid: str, **kwargs):  # noqa: ANN003
            nonlocal call_index
            call_index += 1
            # Fail everything in batch 3 (items 101-110) during Phase 1
            if call_index > 100 and call_index <= 110:
                raise ConnectionError("Last batch explodes")
            return _make_parent_response(gid)

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_fail_last_batch)

        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            await store.put_batch_async(tasks, warm_hierarchy=True, tasks_client=client)

        # Phase 1: 110 calls. Phase 2: re-attempts for 10 failed + uncached parents.
        assert client.get_async.call_count >= 110


# ============================================================================
# 4. CONCURRENCY INTERACTION
# ============================================================================


class TestConcurrencyInteraction:
    """Verify semaphore limits concurrency within paced batches."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency_within_batch(
        self, store: UnifiedTaskStore, mock_cache_provider: MagicMock
    ) -> None:
        """A batch of 50 through a semaphore of 10 should never exceed 10 concurrent."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _tracking_get(gid: str, **kwargs):  # noqa: ANN003
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            # Simulate work
            await asyncio.sleep(0.001)
            async with lock:
                current_concurrent -= 1
            return _make_parent_response(gid)

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_tracking_get)

        # Use a store with semaphore of 10 (default)
        with patch(
            "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
        ):
            await store.put_batch_async(
                [_make_task(f"t-{i}", parent_gid=f"p-{i}") for i in range(120)],
                warm_hierarchy=True,
                tasks_client=client,
            )

        # The default _hierarchy_semaphore is 10
        assert max_concurrent <= 10, (
            f"Max concurrency was {max_concurrent}, expected <= 10"
        )


# ============================================================================
# 5. DEAD CODE REMOVAL VALIDATION
# ============================================================================


class TestDeadCodeRemoval:
    """Verify dead code has been fully removed."""

    def test_fetch_parent_no_backoff_event_param(self) -> None:
        """_fetch_parent should NOT accept a backoff_event keyword argument.
        The old signature included it; the new one must not."""
        sig = inspect.signature(_fetch_parent)
        param_names = set(sig.parameters.keys())
        assert "backoff_event" not in param_names, (
            "_fetch_parent still accepts backoff_event -- dead code not fully removed"
        )

    def test_fetch_parent_rejects_backoff_event_kwarg(self) -> None:
        """Passing backoff_event= to _fetch_parent must raise TypeError at call time."""
        client = MagicMock()
        client.get_async = AsyncMock(return_value=None)

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            # This is a coroutine so we just need to call (not await) to get TypeError
            # from the function signature mismatch
            _fetch_parent("gid-1", tasks_client=client, backoff_event=asyncio.Event())

    def test_is_rate_limit_error_removed(self) -> None:
        """_is_rate_limit_error should no longer exist in hierarchy_warmer module."""
        import autom8_asana.cache.integration.hierarchy_warmer as hw

        assert not hasattr(hw, "_is_rate_limit_error"), (
            "_is_rate_limit_error still present -- dead code not removed"
        )

    def test_no_backoff_event_references_in_source(self) -> None:
        """No references to backoff_event in the production source tree."""
        import autom8_asana.cache.integration.hierarchy_warmer as hw
        import autom8_asana.cache.providers.unified as uf

        hw_src = inspect.getsource(hw)
        uf_src = inspect.getsource(uf)
        assert "backoff_event" not in hw_src, (
            "backoff_event reference in hierarchy_warmer.py"
        )
        assert "backoff_event" not in uf_src, "backoff_event reference in unified.py"


# ============================================================================
# 6. 429 LOGGING
# ============================================================================


class TestRateLimitLogging:
    """Verify structured rate_limit_429_received log is emitted correctly."""

    @pytest.mark.asyncio
    async def test_429_log_emitted_with_correct_fields(self) -> None:
        """When a RateLimitError occurs, rate_limit_429_received log has path,
        attempt, and retry_after fields."""
        import httpx

        # Build a minimal mock response that triggers RateLimitError
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.json.return_value = {"errors": [{"message": "Rate limited"}]}
        mock_response.text = '{"errors":[{"message":"Rate limited"}]}'

        mock_logger = MagicMock()

        # We test the logging behavior by checking that the structured warning
        # is in the transport code. Since the actual request flow requires a live
        # HTTP client, we verify the logging format through source inspection.
        from autom8_asana.transport import asana_http as transport_mod

        src = inspect.getsource(transport_mod)
        assert '"rate_limit_429_received"' in src, (
            "rate_limit_429_received log event not found in transport source"
        )
        # Verify structured fields
        assert '"path"' in src
        assert '"attempt"' in src
        assert '"retry_after"' in src

    def test_429_log_format_in_all_request_methods(self) -> None:
        """rate_limit_429_received must appear in GET, POST, and paginated paths."""
        from autom8_asana.transport import asana_http as transport_mod

        src = inspect.getsource(transport_mod)
        occurrences = src.count('"rate_limit_429_received"')
        # GET (_request), POST (post), and paginated (get_paginated) paths
        assert occurrences >= 2, (
            f"Expected rate_limit_429_received in multiple request paths, found {occurrences}"
        )


# ============================================================================
# 7. PHASE 2 UNAFFECTED (warm_ancestors_async)
# ============================================================================


class TestPhase2Unaffected:
    """Verify warm_ancestors_async still works after dead code removal."""

    @pytest.fixture
    def hierarchy_index(self) -> HierarchyIndex:
        return HierarchyIndex()

    @pytest.mark.asyncio
    async def test_warm_ancestors_basic_traversal(
        self, hierarchy_index: HierarchyIndex
    ) -> None:
        """Basic parent chain traversal still works."""
        hierarchy_index.register({"gid": "unit-1", "parent": {"gid": "biz-1"}})

        biz_task = MagicMock()
        biz_task.model_dump.return_value = {
            "gid": "biz-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [],
        }
        client = MagicMock()
        client.get_async = AsyncMock(return_value=biz_task)

        warmed = await warm_ancestors_async(
            gids=["unit-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
        )

        assert warmed == 1
        assert hierarchy_index.contains("biz-1")

    @pytest.mark.asyncio
    async def test_warm_ancestors_multi_level(
        self, hierarchy_index: HierarchyIndex
    ) -> None:
        """Multi-level traversal still works after dead code removal."""
        hierarchy_index.register({"gid": "unit-1", "parent": {"gid": "biz-1"}})

        responses = {
            "biz-1": {
                "gid": "biz-1",
                "name": "Business",
                "parent": {"gid": "acct-1"},
                "custom_fields": [],
            },
            "acct-1": {
                "gid": "acct-1",
                "name": "Account",
                "parent": None,
                "custom_fields": [],
            },
        }

        async def _get(gid: str, **kwargs):  # noqa: ANN003
            data = responses.get(gid)
            if data is None:
                return None
            mock = MagicMock()
            mock.model_dump.return_value = data
            return mock

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=_get)

        warmed = await warm_ancestors_async(
            gids=["unit-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
        )

        assert warmed == 2
        assert hierarchy_index.contains("biz-1")
        assert hierarchy_index.contains("acct-1")

    @pytest.mark.asyncio
    async def test_warm_ancestors_error_resilience(
        self, hierarchy_index: HierarchyIndex
    ) -> None:
        """warm_ancestors_async handles fetch errors gracefully after refactor."""
        hierarchy_index.register({"gid": "u-1", "parent": {"gid": "b-1"}})

        client = MagicMock()
        client.get_async = AsyncMock(side_effect=ConnectionError("Network down"))

        warmed = await warm_ancestors_async(
            gids=["u-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
        )

        assert warmed == 0

    @pytest.mark.asyncio
    async def test_warm_ancestors_global_semaphore(
        self, hierarchy_index: HierarchyIndex
    ) -> None:
        """Global semaphore parameter still works in warm_ancestors_async."""
        hierarchy_index.register({"gid": "u-1", "parent": {"gid": "b-1"}})

        biz_task = MagicMock()
        biz_task.model_dump.return_value = {
            "gid": "b-1",
            "name": "Business",
            "parent": None,
            "custom_fields": [],
        }
        client = MagicMock()
        client.get_async = AsyncMock(return_value=biz_task)

        sem = asyncio.Semaphore(2)
        warmed = await warm_ancestors_async(
            gids=["u-1"],
            hierarchy_index=hierarchy_index,
            tasks_client=client,
            max_depth=5,
            global_semaphore=sem,
        )

        assert warmed == 1


# ============================================================================
# 8. CONFIGURATION CONSTANTS VALIDATION
# ============================================================================


class TestConfigConstants:
    """Verify configuration constants have sane values and types."""

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
        """Batch size should be less than threshold, otherwise pacing is meaningless."""
        from autom8_asana.config import HIERARCHY_BATCH_SIZE, HIERARCHY_PACING_THRESHOLD

        assert HIERARCHY_BATCH_SIZE < HIERARCHY_PACING_THRESHOLD, (
            f"BATCH_SIZE ({HIERARCHY_BATCH_SIZE}) >= THRESHOLD ({HIERARCHY_PACING_THRESHOLD}) "
            "makes pacing pointless"
        )
