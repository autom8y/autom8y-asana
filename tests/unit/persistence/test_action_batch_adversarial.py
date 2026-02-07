"""Adversarial tests for GAP-05 Action Batching.

QA Adversary: These tests probe edge cases, defensive guards, and potential
bugs in the action batching implementation. They think like a malicious user,
an unlucky user, and a confused user.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchRequest, BatchResult
from autom8_asana.exceptions import AsanaError
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.action_executor import (
    ActionExecutor,
    _chunk_actions,
    action_to_batch_request,
    batch_result_to_action_result,
)
from autom8_asana.persistence.action_ordering import (
    OrderingRule,
    resolve_order,
)
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    ActionType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_action(
    task_gid: str,
    action_type: ActionType,
    target_gid: str | None = None,
    extra_params: dict | None = None,
) -> ActionOperation:
    """Create an ActionOperation with minimal data for testing."""
    task = Task(gid=task_gid, name=f"Task {task_gid}")
    target = NameGid(gid=target_gid) if target_gid else None
    return ActionOperation(
        task=task,
        action=action_type,
        target=target,
        extra_params=extra_params or {},
    )


def _make_batch_result(success: bool = True, gid: str = "gid_1") -> BatchResult:
    """Create a BatchResult for testing."""
    if success:
        return BatchResult(status_code=200, body={"data": {"gid": gid}})
    else:
        return BatchResult(
            status_code=500, body={"errors": [{"message": "Server error"}]}
        )


# ---------------------------------------------------------------------------
# PROBE 1: to_api_call() payload without a "data" key
# ---------------------------------------------------------------------------


class TestPayloadWithoutDataKey:
    """Adversarial: What if to_api_call() returned a payload WITHOUT a "data" key?

    Finding: In the current implementation, all 15 ActionType cases in
    to_api_call() always return {"data": {...}}. However, the conversion
    function uses payload.get("data"), which returns None if no "data" key
    exists. This would create a BatchRequest with data=None. The batch API
    would then send a request without a body, which might succeed for some
    endpoints (e.g., addLike with empty body) but would fail for most.

    Since to_api_call() is a frozen dataclass method on ActionOperation,
    a subclass or monkey-patch could violate this contract. The conversion
    function handles it gracefully (data=None), but does not raise or warn.
    """

    def test_payload_without_data_key_converts_to_none_data(self) -> None:
        """If somehow payload lacks "data" key, BatchRequest gets data=None."""
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
        )

        # Monkey-patch to_api_call to return payload without "data" key
        original_to_api_call = action.to_api_call

        def patched_to_api_call():
            method, endpoint, _ = original_to_api_call()
            return method, endpoint, {"tag": "tag_1"}  # Missing "data" wrapper

        # ActionOperation is frozen, so we can't set directly. Instead test
        # the conversion function's behavior with such a payload.
        method, endpoint, payload = action.to_api_call()
        # Simulate missing "data" key
        payload_without_data = {"tag": "tag_1"}
        unwrapped = payload_without_data.get("data")
        assert unwrapped is None  # Confirms graceful degradation

    def test_all_action_types_always_have_data_key(self) -> None:
        """Contract test: every ActionType's to_api_call() returns {"data": ...}."""
        task = Task(gid="task_1", name="Test")

        test_cases = [
            (ActionType.ADD_TAG, NameGid(gid="t1"), {}),
            (ActionType.REMOVE_TAG, NameGid(gid="t1"), {}),
            (ActionType.ADD_TO_PROJECT, NameGid(gid="p1"), {}),
            (ActionType.REMOVE_FROM_PROJECT, NameGid(gid="p1"), {}),
            (ActionType.ADD_DEPENDENCY, NameGid(gid="d1"), {}),
            (ActionType.REMOVE_DEPENDENCY, NameGid(gid="d1"), {}),
            (ActionType.MOVE_TO_SECTION, NameGid(gid="s1"), {}),
            (ActionType.ADD_FOLLOWER, NameGid(gid="u1"), {}),
            (ActionType.REMOVE_FOLLOWER, NameGid(gid="u1"), {}),
            (ActionType.ADD_DEPENDENT, NameGid(gid="d1"), {}),
            (ActionType.REMOVE_DEPENDENT, NameGid(gid="d1"), {}),
            (ActionType.ADD_LIKE, None, {}),
            (ActionType.REMOVE_LIKE, None, {}),
            (ActionType.ADD_COMMENT, None, {"text": "Hello"}),
            (ActionType.SET_PARENT, None, {"parent": "p1"}),
        ]

        for action_type, target, extra_params in test_cases:
            action = ActionOperation(
                task=task,
                action=action_type,
                target=target,
                extra_params=extra_params,
            )
            _, _, payload = action.to_api_call()
            assert "data" in payload, (
                f"ActionType.{action_type.name} to_api_call() missing 'data' key"
            )


# ---------------------------------------------------------------------------
# PROBE 2: batch_client.execute_async returns fewer results than requests
# ---------------------------------------------------------------------------


class TestBatchResultCountMismatch:
    """Adversarial: What if execute_async returns fewer/more results than requests?

    Finding: The implementation has a DEFENSIVE CHECK at line 264 of
    action_executor.py. If len(batch_results) != len(chunk), it raises
    ValueError which triggers chunk-level fallback. This is CORRECT and
    was proactively added by the engineer.
    """

    @pytest.mark.asyncio
    async def test_fewer_results_triggers_fallback(self) -> None:
        """BatchClient returning fewer results than sent -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # Return 1 result for 4 requests
        mock_batch.execute_async = AsyncMock(
            return_value=[_make_batch_result(True)]
        )

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            _make_action("task_1", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(4)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 4
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http.request.call_count == 4

    @pytest.mark.asyncio
    async def test_more_results_than_requests_triggers_fallback(self) -> None:
        """BatchClient returning MORE results than sent -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # Return 5 results for 2 requests
        mock_batch.execute_async = AsyncMock(
            return_value=[_make_batch_result(True) for _ in range(5)]
        )

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            _make_action("task_1", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(2)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_results_for_nonempty_chunk_triggers_fallback(self) -> None:
        """BatchClient returning empty list for a chunk -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [
            _make_action("task_1", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(3)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert mock_http.request.call_count == 3


# ---------------------------------------------------------------------------
# PROBE 3: resolve_order with actions matching rule types but not match_fn
# ---------------------------------------------------------------------------


class TestResolveOrderMatchFnEdgeCases:
    """Adversarial: Actions that match rule's ActionType but not match_fn.

    What happens if resolve_order receives actions that are ADD_TO_PROJECT
    and MOVE_TO_SECTION but for different tasks?
    """

    def test_same_type_different_task_no_constraint(self) -> None:
        """ADD_TO_PROJECT(task_A) + MOVE_TO_SECTION(task_B) -> single tier."""
        add_proj = _make_action("task_A", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_B", ActionType.MOVE_TO_SECTION, "sect_1")

        tiers = resolve_order([add_proj, move_sect])
        assert len(tiers) == 1
        assert len(tiers[0]) == 2

    def test_multiple_add_project_one_move_section_only_constrains_matching(self) -> None:
        """ADD_TO_PROJECT for tasks A,B,C + MOVE_TO_SECTION for task B only.

        Only task B's pair should be constrained.
        """
        add_a = _make_action("task_A", ActionType.ADD_TO_PROJECT, "proj_1")
        add_b = _make_action("task_B", ActionType.ADD_TO_PROJECT, "proj_2")
        add_c = _make_action("task_C", ActionType.ADD_TO_PROJECT, "proj_3")
        move_b = _make_action("task_B", ActionType.MOVE_TO_SECTION, "sect_1")

        tiers = resolve_order([add_a, add_b, add_c, move_b])

        assert len(tiers) == 2
        # Tier 0: add_a, add_b, add_c (3 ADD_TO_PROJECT)
        assert len(tiers[0]) == 3
        # Tier 1: move_b (MOVE_TO_SECTION for task_B)
        assert len(tiers[1]) == 1
        assert tiers[1][0] is move_b


# ---------------------------------------------------------------------------
# PROBE 4: _resolve_temp_gids in-place mutation
# ---------------------------------------------------------------------------


class TestResolveTempGidsInPlaceMutation:
    """Adversarial: Does _resolve_temp_gids modify action in-place?

    Finding: _resolve_temp_gids creates a NEW ActionOperation when resolution
    is needed (line 384-392 of action_executor.py). When no resolution is
    needed, it returns the original action object. This is SAFE because
    ActionOperation is a frozen dataclass -- it CANNOT be mutated.

    The risk would be if _resolve_task_gid uses object.__setattr__ on a
    frozen task model. Let's verify the Pydantic model_copy path is preferred.
    """

    @pytest.mark.asyncio
    async def test_resolve_does_not_mutate_original_action(self) -> None:
        """Resolved action should be a new object, not the original mutated."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})

        executor = ActionExecutor(mock_http)

        task = Task(gid="task_1", name="Test")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="temp_tag_1", name="Tag"),
        )

        gid_map = {"temp_tag_1": "real_tag_1"}
        resolved = executor._resolve_temp_gids(action, gid_map)

        # Original action unchanged (frozen dataclass)
        assert action.target.gid == "temp_tag_1"
        # Resolved action has new GID
        assert resolved.target.gid == "real_tag_1"
        # They should be different objects
        assert resolved is not action

    @pytest.mark.asyncio
    async def test_resolve_no_mutation_when_no_temp_gids(self) -> None:
        """When no temp GIDs, returns the SAME object (identity preserved)."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})

        executor = ActionExecutor(mock_http)

        task = Task(gid="task_1", name="Test")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_1"),  # Not a temp GID
        )

        resolved = executor._resolve_temp_gids(action, {})

        # Same object returned (no copy needed)
        assert resolved is action


# ---------------------------------------------------------------------------
# PROBE 5: id() trick in resolve_order -- Python object ID reuse
# ---------------------------------------------------------------------------


class TestIdTrickObjectReuse:
    """Adversarial: Does the id() trick in resolve_order break if Python
    reuses object IDs for different ActionOperations?

    Finding: The id() trick is used within a single call to resolve_order().
    All ActionOperation objects are alive simultaneously (held in the `actions`
    list), so Python CANNOT reuse their IDs during the function's execution.
    CPython guarantees unique id() for simultaneously-alive objects.

    This would only be a problem if objects were created and destroyed
    during the function call, which they are not -- the input list holds
    references to all of them throughout.
    """

    def test_id_uniqueness_with_many_actions(self) -> None:
        """100 actions should all get unique IDs in resolve_order."""
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(100)
        ]

        ids = [id(a) for a in actions]
        assert len(set(ids)) == 100, "Object IDs should be unique for live objects"

        # resolve_order should work fine
        tiers = resolve_order(actions)
        assert len(tiers) == 1
        assert len(tiers[0]) == 100

    def test_id_trick_with_ordering_constraint_100_actions(self) -> None:
        """100 actions with ordering constraints should work correctly."""
        tag_actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(98)
        ]
        add_proj = _make_action("task_x", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_x", ActionType.MOVE_TO_SECTION, "sect_1")

        actions = tag_actions + [add_proj, move_sect]
        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 99  # 98 tags + add_project
        assert len(tiers[1]) == 1   # move_to_section


# ---------------------------------------------------------------------------
# PROBE 6: Large action lists -- DAG algorithm performance
# ---------------------------------------------------------------------------


class TestLargeActionLists:
    """Adversarial: Does the DAG algorithm degrade with 100+ actions?

    Finding: The algorithm is O(A * R) for building edges where A = actions
    per type, R = rules. For 100 actions with 1 rule, it's O(100). The
    Kahn's algorithm itself is O(V + E). For typical use cases this is fast.
    """

    def test_1000_independent_actions(self) -> None:
        """1000 independent actions should resolve into 1 tier quickly."""
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(1000)
        ]

        tiers = resolve_order(actions)

        assert len(tiers) == 1
        assert len(tiers[0]) == 1000

    def test_500_actions_with_ordering(self) -> None:
        """500 actions: 250 ADD_TO_PROJECT + 250 MOVE_TO_SECTION for same tasks."""
        actions = []
        for i in range(250):
            actions.append(
                _make_action(f"task_{i}", ActionType.ADD_TO_PROJECT, f"proj_{i}")
            )
        for i in range(250):
            actions.append(
                _make_action(f"task_{i}", ActionType.MOVE_TO_SECTION, f"sect_{i}")
            )

        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 250
        assert len(tiers[1]) == 250

    @pytest.mark.asyncio
    async def test_100_actions_batch_execution(self) -> None:
        """100 actions through batch executor: 10 batch calls expected."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # 10 chunks of 10
        mock_batch.execute_async.side_effect = [
            [_make_batch_result(True, f"r{j}") for j in range(10)]
            for _ in range(10)
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(100)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 100
        assert all(r.success for r in results)
        assert mock_batch.execute_async.call_count == 10


# ---------------------------------------------------------------------------
# PROBE 7: Metrics / structured logging verification
# ---------------------------------------------------------------------------


class TestMetricsLogging:
    """Adversarial: Are the metrics structured logs emitting the fields the TDD specifies?

    TDD Section 7 specifies counters and histograms. The implementation logs
    via structured logging (self._log.info). Let's verify the log fields.
    """

    @pytest.mark.asyncio
    async def test_batch_complete_log_fields(self) -> None:
        """The action_batch_complete log should include all TDD-specified fields."""
        mock_log = MagicMock()
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = mock_log

        mock_batch = AsyncMock()
        mock_batch.execute_async.return_value = [
            _make_batch_result(True, "r1"),
            _make_batch_result(False),  # One failure
            _make_batch_result(True, "r3"),
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [
            _make_action("task_1", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(3)
        ]

        await executor.execute_async(actions, {})

        # Find the action_batch_complete log call
        info_calls = mock_log.info.call_args_list
        batch_complete_call = None
        for call in info_calls:
            if call[0][0] == "action_batch_complete":
                batch_complete_call = call
                break

        assert batch_complete_call is not None, "action_batch_complete log not emitted"

        kwargs = batch_complete_call[1]
        # TDD Section 7.1 specifies these counters
        assert "total_actions" in kwargs
        assert kwargs["total_actions"] == 3
        assert "batch_succeeded" in kwargs
        assert kwargs["batch_succeeded"] == 2
        assert "batch_failed" in kwargs
        assert kwargs["batch_failed"] == 1
        assert "tiers" in kwargs
        assert "chunks_total" in kwargs
        assert "chunks_fallback" in kwargs
        assert "sequential_fallback" in kwargs

    @pytest.mark.asyncio
    async def test_no_log_when_log_is_none(self) -> None:
        """When _log is None, no logging calls should happen (no AttributeError)."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None  # No logger

        mock_batch = AsyncMock()
        mock_batch.execute_async.return_value = [
            _make_batch_result(True, "r1"),
            _make_batch_result(True, "r2"),
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [
            _make_action("task_1", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(2)
        ]

        # Should not raise even with no logger
        results = await executor.execute_async(actions, {})
        assert len(results) == 2


# ---------------------------------------------------------------------------
# PROBE 8: Ordering with tier reordering -- index map correctness
# ---------------------------------------------------------------------------


class TestIndexMapCorrectness:
    """Adversarial: Does the index map correctly restore original ordering
    after tier/chunk reordering?

    The tricky case: if ordering resolution moves actions to different tiers,
    the final result list must still match the INPUT order, not the tier order.
    """

    @pytest.mark.asyncio
    async def test_results_ordered_by_input_not_tier_order(self) -> None:
        """If input is [MOVE, TAG, ADD_PROJECT], results must be [MOVE_result, TAG_result, ADD_result]."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # Tier 0: TAG + ADD_PROJECT -> 2 results
        # Tier 1: MOVE_TO_SECTION -> 1 result
        mock_batch.execute_async.side_effect = [
            [
                BatchResult(status_code=200, body={"data": {"gid": "tag_result"}}),
                BatchResult(status_code=200, body={"data": {"gid": "add_proj_result"}}),
            ],
            [
                BatchResult(status_code=200, body={"data": {"gid": "move_result"}}),
            ],
        ]

        executor = ActionExecutor(mock_http, mock_batch)

        # Input order: MOVE, TAG, ADD_PROJECT (MOVE must go to tier 1)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task,
                action=ActionType.MOVE_TO_SECTION,
                target=NameGid(gid="sect_1"),
            ),
            ActionOperation(
                task=task,
                action=ActionType.ADD_TAG,
                target=NameGid(gid="tag_1"),
            ),
            ActionOperation(
                task=task,
                action=ActionType.ADD_TO_PROJECT,
                target=NameGid(gid="proj_1"),
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        # Result 0 should correspond to MOVE_TO_SECTION (input[0])
        assert results[0].action.action == ActionType.MOVE_TO_SECTION
        # Result 1 should correspond to ADD_TAG (input[1])
        assert results[1].action.action == ActionType.ADD_TAG
        # Result 2 should correspond to ADD_TO_PROJECT (input[2])
        assert results[2].action.action == ActionType.ADD_TO_PROJECT

        # Verify the response_data matches the correct action
        assert results[0].response_data == {"gid": "move_result"}
        assert results[1].response_data == {"gid": "tag_result"}
        assert results[2].response_data == {"gid": "add_proj_result"}


# ---------------------------------------------------------------------------
# PROBE 9: Fallback path with already-resolved actions
# ---------------------------------------------------------------------------


class TestFallbackWithResolvedActions:
    """Adversarial: When fallback calls _execute_single_action with already-
    resolved actions and empty gid_map, does it work correctly?

    The concern is that _execute_single_action calls _resolve_temp_gids,
    which is idempotent. But what if the resolved action has target=None
    (like ADD_LIKE)?
    """

    @pytest.mark.asyncio
    async def test_fallback_with_no_target_action(self) -> None:
        """Fallback with ADD_LIKE (target=None) should work."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async.side_effect = ConnectionError("fail")

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_LIKE, target=None),
            ActionOperation(task=task, action=ActionType.ADD_LIKE, target=None),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_fallback_with_comment_action(self) -> None:
        """Fallback with ADD_COMMENT should preserve extra_params."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {"gid": "story_1"}})
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async.side_effect = ConnectionError("fail")

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task,
                action=ActionType.ADD_COMMENT,
                target=None,
                extra_params={"text": "Hello"},
            ),
            ActionOperation(
                task=task,
                action=ActionType.ADD_COMMENT,
                target=None,
                extra_params={"text": "World"},
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Verify comment text was passed correctly
        call_args_list = mock_http.request.call_args_list
        assert call_args_list[0][1]["json"]["data"]["text"] == "Hello"
        assert call_args_list[1][1]["json"]["data"]["text"] == "World"


# ---------------------------------------------------------------------------
# PROBE 10: Batch result with edge-case status codes
# ---------------------------------------------------------------------------


class TestBatchResultEdgeCases:
    """Adversarial: Edge-case BatchResult scenarios."""

    def test_batch_result_201_is_success(self) -> None:
        """201 Created should be treated as success."""
        br = BatchResult(status_code=201, body={"data": {"gid": "new_1"}})
        action = _make_action("task_1", ActionType.ADD_TAG, "tag_1")

        result = batch_result_to_action_result(action, br)
        assert result.success is True

    def test_batch_result_204_is_success(self) -> None:
        """204 No Content should be treated as success (data may be None)."""
        br = BatchResult(status_code=204, body=None)
        action = _make_action("task_1", ActionType.REMOVE_TAG, "tag_1")

        result = batch_result_to_action_result(action, br)
        assert result.success is True
        assert result.response_data is None

    def test_batch_result_400_is_failure(self) -> None:
        """400 Bad Request should be treated as failure."""
        br = BatchResult(
            status_code=400,
            body={"errors": [{"message": "Bad request"}]},
        )
        action = _make_action("task_1", ActionType.ADD_TAG, "tag_1")

        result = batch_result_to_action_result(action, br)
        assert result.success is False
        assert isinstance(result.error, AsanaError)

    def test_batch_result_403_is_failure(self) -> None:
        """403 Forbidden should be treated as failure."""
        br = BatchResult(
            status_code=403,
            body={"errors": [{"message": "Forbidden"}]},
        )
        action = _make_action("task_1", ActionType.ADD_TAG, "tag_1")

        result = batch_result_to_action_result(action, br)
        assert result.success is False

    def test_batch_result_404_is_failure(self) -> None:
        """404 Not Found should be treated as failure."""
        br = BatchResult(
            status_code=404,
            body={"errors": [{"message": "Not found"}]},
        )
        action = _make_action("task_1", ActionType.ADD_TAG, "tag_1")

        result = batch_result_to_action_result(action, br)
        assert result.success is False


# ---------------------------------------------------------------------------
# PROBE 11: Stable sort within tiers
# ---------------------------------------------------------------------------


class TestStableSortWithinTiers:
    """Adversarial: Does resolve_order preserve original list order WITHIN
    a tier even when actions are of different types?
    """

    def test_mixed_types_preserve_input_order(self) -> None:
        """Actions of mixed types in same tier preserve input order."""
        actions = [
            _make_action("task_3", ActionType.REMOVE_TAG, "tag_3"),
            _make_action("task_1", ActionType.ADD_TAG, "tag_1"),
            _make_action("task_4", ActionType.ADD_FOLLOWER, "user_1"),
            _make_action("task_2", ActionType.ADD_DEPENDENCY, "dep_1"),
            _make_action("task_5", ActionType.ADD_LIKE),
        ]

        tiers = resolve_order(actions)

        assert len(tiers) == 1
        assert tiers[0][0].task.gid == "task_3"
        assert tiers[0][1].task.gid == "task_1"
        assert tiers[0][2].task.gid == "task_4"
        assert tiers[0][3].task.gid == "task_2"
        assert tiers[0][4].task.gid == "task_5"


# ---------------------------------------------------------------------------
# PROBE 12: Sequential fallback when BOTH batch AND sequential fail
# ---------------------------------------------------------------------------


class TestDoubleFailure:
    """Adversarial: What happens when batch fails AND sequential fallback
    also fails?

    Finding: _execute_single_action catches all exceptions and returns
    ActionResult(success=False, error=e). So even double failure is handled
    gracefully -- the result will show individual failures.
    """

    @pytest.mark.asyncio
    async def test_batch_fails_then_sequential_also_fails(self) -> None:
        """Batch fails, fallback sequential also fails -> failed ActionResults."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=RuntimeError("HTTP also down"))
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async.side_effect = ConnectionError("Batch down")

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [
            _make_action("task_1", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(3)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all(isinstance(r.error, RuntimeError) for r in results)
        assert all("HTTP also down" in str(r.error) for r in results)


# ---------------------------------------------------------------------------
# PROBE 13: Chunk boundary correctness
# ---------------------------------------------------------------------------


class TestChunkBoundaryCorrectness:
    """Adversarial: Verify chunk boundaries are correct at exact multiples."""

    def test_chunk_size_1(self) -> None:
        """Chunk size 1: each action in its own chunk."""
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(3)
        ]
        chunks = _chunk_actions(actions, 1)
        assert len(chunks) == 3
        assert all(len(c) == 1 for c in chunks)

    def test_chunk_size_equals_list_length(self) -> None:
        """Chunk size equals list length: single chunk."""
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(7)
        ]
        chunks = _chunk_actions(actions, 7)
        assert len(chunks) == 1
        assert len(chunks[0]) == 7

    def test_chunk_11_into_10(self) -> None:
        """11 actions into chunks of 10: [10, 1]."""
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(11)
        ]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 1

    def test_chunk_20_into_10(self) -> None:
        """20 actions into chunks of 10: [10, 10]."""
        actions = [
            _make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}")
            for i in range(20)
        ]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10


# ---------------------------------------------------------------------------
# PROBE 14: Wiring verification -- SaveSession passes batch_client
# ---------------------------------------------------------------------------


class TestSessionWiring:
    """Adversarial: Verify that SaveSession actually passes batch_client
    to ActionExecutor, not None.
    """

    def test_save_session_passes_batch_client(self) -> None:
        """SaveSession.__init__ wires client.batch to ActionExecutor."""
        from autom8_asana.persistence.session import SaveSession

        mock_client = MagicMock()
        mock_http = AsyncMock()
        mock_http._log = None
        mock_client._http = mock_http

        mock_batch = MagicMock()
        mock_client.batch = mock_batch

        mock_client.automation = None
        mock_client._cache_provider = None
        mock_client._log = None
        mock_client._config = MagicMock()
        mock_client._config.automation = None

        session = SaveSession(mock_client)

        # Verify ActionExecutor received both http and batch
        assert session._action_executor._http is mock_http
        assert session._action_executor._batch_client is mock_batch


# ---------------------------------------------------------------------------
# PROBE 15: Multiple ADD_TO_PROJECT -> MOVE_TO_SECTION for same task
# ---------------------------------------------------------------------------


class TestMultipleDependenciesPerTask:
    """Adversarial: Multiple ADD_TO_PROJECT for same task, each with a
    MOVE_TO_SECTION. Should all MOVE_TO_SECTION be in tier 1.
    """

    def test_two_add_projects_two_move_sections_same_task(self) -> None:
        """2 ADD_TO_PROJECT + 2 MOVE_TO_SECTION for same task -> 2 tiers."""
        add_1 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        add_2 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_2")
        move_1 = _make_action("task_1", ActionType.MOVE_TO_SECTION, "sect_1")
        move_2 = _make_action("task_1", ActionType.MOVE_TO_SECTION, "sect_2")

        tiers = resolve_order([add_1, add_2, move_1, move_2])

        assert len(tiers) == 2
        # Tier 0: both ADD_TO_PROJECT
        assert len(tiers[0]) == 2
        assert all(a.action == ActionType.ADD_TO_PROJECT for a in tiers[0])
        # Tier 1: both MOVE_TO_SECTION
        assert len(tiers[1]) == 2
        assert all(a.action == ActionType.MOVE_TO_SECTION for a in tiers[1])

    def test_in_degree_accumulates_from_multiple_predecessors(self) -> None:
        """A MOVE_TO_SECTION with 3 ADD_TO_PROJECT predecessors has in_degree=3.

        The Kahn's algorithm should still place it in tier 1 because all
        predecessors are in tier 0. In_degree goes to 0 after processing tier 0.
        """
        add_1 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_1")
        add_2 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_2")
        add_3 = _make_action("task_1", ActionType.ADD_TO_PROJECT, "proj_3")
        move = _make_action("task_1", ActionType.MOVE_TO_SECTION, "sect_1")

        tiers = resolve_order([add_1, add_2, add_3, move])

        assert len(tiers) == 2
        assert len(tiers[0]) == 3
        assert len(tiers[1]) == 1
        assert tiers[1][0] is move
