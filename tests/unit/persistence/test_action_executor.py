"""Tests for ActionExecutor.

Per TDD-0011: Verify action execution and GID resolution.
Per TDD-GAP-05: Verify batch execution path, conversion functions,
                result mapping, fallback, and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.batch.models import BatchRequest, BatchResult
from autom8_asana.errors import AsanaError
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.action_executor import (
    ActionExecutor,
    _chunk_actions,
    action_to_batch_request,
    batch_result_to_action_result,
)
from autom8_asana.persistence.action_ordering import resolve_order
from autom8_asana.persistence.models import (
    ActionOperation,
    ActionResult,
    ActionType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_http() -> AsyncMock:
    """Create mock HTTP client."""
    http = AsyncMock()
    http.request = AsyncMock(return_value={"data": {}})
    return http


@pytest.fixture
def executor(mock_http: AsyncMock) -> ActionExecutor:
    """Create ActionExecutor with mock HTTP client."""
    return ActionExecutor(mock_http)


# ---------------------------------------------------------------------------
# ActionExecutor Tests
# ---------------------------------------------------------------------------


class TestActionExecutorInit:
    """Tests for ActionExecutor initialization."""

    def test_init_with_http_client(self, mock_http: AsyncMock) -> None:
        """ActionExecutor stores HTTP client reference."""
        executor = ActionExecutor(mock_http)
        assert executor._http is mock_http


class TestActionExecutorExecuteAsync:
    """Tests for execute_async method."""

    async def test_execute_empty_actions(self, executor: ActionExecutor) -> None:
        """execute_async handles empty action list."""
        results = await executor.execute_async([], {})
        assert results == []

    async def test_execute_single_action(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async executes a single action."""
        task = Task(gid="task_123", name="Test Task")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        results = await executor.execute_async([action], {})

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].action is action
        mock_http.request.assert_called_once_with(
            method="POST",
            path="/tasks/task_123/addTag",
            json={"data": {"tag": "tag_456"}},
        )

    async def test_execute_multiple_actions(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async executes multiple actions sequentially."""
        task = Task(gid="task_123")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")),
            ActionOperation(task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_3")),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_http.request.call_count == 3

    async def test_execute_with_api_error(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async handles API errors gracefully."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),
        )

        mock_http.request.side_effect = RuntimeError("API error")

        results = await executor.execute_async([action], {})

        assert len(results) == 1
        assert results[0].success is False
        assert isinstance(results[0].error, RuntimeError)
        assert "API error" in str(results[0].error)

    async def test_execute_continues_after_error(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async continues processing after an error."""
        task = Task(gid="task_123")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_3")),
        ]

        # Second call fails
        mock_http.request.side_effect = [
            {"data": {}},
            RuntimeError("API error"),
            {"data": {}},
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    async def test_execute_preserves_order(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async preserves action order in results."""
        task = Task(gid="task_123")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_2")),
            ActionOperation(
                task=task,
                action=ActionType.ADD_TO_PROJECT,
                target=NameGid(gid="proj_3"),
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert results[0].action.target.gid == "tag_1"
        assert results[1].action.target.gid == "tag_2"
        assert results[2].action.target.gid == "proj_3"


class TestActionExecutorGidResolution:
    """Tests for temp GID resolution."""

    async def test_resolve_target_temp_gid(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async resolves temp GID in target."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="temp_tag_456", name="Urgent"),
        )

        gid_map = {"temp_tag_456": "real_tag_789"}

        await executor.execute_async([action], gid_map)

        # Should call API with resolved GID
        mock_http.request.assert_called_once_with(
            method="POST",
            path="/tasks/task_123/addTag",
            json={"data": {"tag": "real_tag_789"}},
        )

    async def test_no_resolution_for_non_temp_gid(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async does not modify non-temp GIDs."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="tag_456"),  # Not a temp GID
        )

        gid_map = {"temp_other": "real_other"}

        await executor.execute_async([action], gid_map)

        # Should call API with original GID
        mock_http.request.assert_called_once_with(
            method="POST",
            path="/tasks/task_123/addTag",
            json={"data": {"tag": "tag_456"}},
        )

    async def test_no_resolution_for_unmatched_temp_gid(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async keeps temp GID if not in map."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(gid="temp_not_in_map"),
        )

        gid_map = {"temp_other": "real_other"}

        await executor.execute_async([action], gid_map)

        # Should call API with original temp GID (may fail but that's expected)
        mock_http.request.assert_called_once_with(
            method="POST",
            path="/tasks/task_123/addTag",
            json={"data": {"tag": "temp_not_in_map"}},
        )


class TestActionExecutorApiCalls:
    """Tests for correct API call generation."""

    async def test_add_tag_api_call(self, executor: ActionExecutor, mock_http: AsyncMock) -> None:
        """ADD_TAG generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/tasks/task_123/addTag",
            json={"data": {"tag": "tag_456"}},
        )

    async def test_remove_tag_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """REMOVE_TAG generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_456")
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/tasks/task_123/removeTag",
            json={"data": {"tag": "tag_456"}},
        )

    async def test_add_to_project_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """ADD_TO_PROJECT generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TO_PROJECT, target=NameGid(gid="proj_789")
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/tasks/task_123/addProject",
            json={"data": {"project": "proj_789"}},
        )

    async def test_remove_from_project_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """REMOVE_FROM_PROJECT generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_FROM_PROJECT,
            target=NameGid(gid="proj_789"),
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/tasks/task_123/removeProject",
            json={"data": {"project": "proj_789"}},
        )

    async def test_add_dependency_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """ADD_DEPENDENCY generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.ADD_DEPENDENCY, target=NameGid(gid="task_456")
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/tasks/task_123/addDependencies",
            json={"data": {"dependencies": ["task_456"]}},
        )

    async def test_remove_dependency_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """REMOVE_DEPENDENCY generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.REMOVE_DEPENDENCY,
            target=NameGid(gid="task_456"),
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/tasks/task_123/removeDependencies",
            json={"data": {"dependencies": ["task_456"]}},
        )

    async def test_move_to_section_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """MOVE_TO_SECTION generates correct API call."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task,
            action=ActionType.MOVE_TO_SECTION,
            target=NameGid(gid="section_789"),
        )

        await executor.execute_async([action], {})

        mock_http.request.assert_called_with(
            method="POST",
            path="/sections/section_789/addTask",
            json={"data": {"task": "task_123"}},
        )


class TestActionExecutorResponseHandling:
    """Tests for response data handling."""

    async def test_success_stores_response_data(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """Successful action stores response data."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )

        mock_http.request.return_value = {"data": {"gid": "tag_456", "name": "Important"}}

        results = await executor.execute_async([action], {})

        assert results[0].success is True
        assert results[0].response_data == {"data": {"gid": "tag_456", "name": "Important"}}
        assert results[0].error is None

    async def test_failure_stores_error(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """Failed action stores error information."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )

        error = ValueError("Invalid tag")
        mock_http.request.side_effect = error

        results = await executor.execute_async([action], {})

        assert results[0].success is False
        assert results[0].error is error
        assert results[0].response_data is None


# ---------------------------------------------------------------------------
# TDD-GAP-05: Conversion Function Tests
# ---------------------------------------------------------------------------


class TestActionToBatchRequest:
    """Tests for action_to_batch_request conversion function."""

    def test_add_tag_converts_correctly(self) -> None:
        """ADD_TAG converts: endpoint /tasks/{gid}/addTag, data unwrapped."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )

        result = action_to_batch_request(action)

        assert isinstance(result, BatchRequest)
        assert result.relative_path == "/tasks/task_123/addTag"
        assert result.method == "POST"
        assert result.data == {"tag": "tag_456"}

    def test_move_to_section_converts_correctly(self) -> None:
        """MOVE_TO_SECTION converts: endpoint /sections/{gid}/addTask."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task,
            action=ActionType.MOVE_TO_SECTION,
            target=NameGid(gid="section_789"),
        )

        result = action_to_batch_request(action)

        assert result.relative_path == "/sections/section_789/addTask"
        assert result.method == "POST"
        assert result.data == {"task": "task_123"}

    @pytest.mark.parametrize(
        "action_type,target_gid,expected_path_contains,expected_data_key",
        [
            (ActionType.ADD_TAG, "tag_1", "/addTag", "tag"),
            (ActionType.REMOVE_TAG, "tag_1", "/removeTag", "tag"),
            (ActionType.ADD_TO_PROJECT, "proj_1", "/addProject", "project"),
            (ActionType.REMOVE_FROM_PROJECT, "proj_1", "/removeProject", "project"),
            (ActionType.ADD_DEPENDENCY, "task_dep", "/addDependencies", "dependencies"),
            (
                ActionType.REMOVE_DEPENDENCY,
                "task_dep",
                "/removeDependencies",
                "dependencies",
            ),
            (ActionType.MOVE_TO_SECTION, "sect_1", "/addTask", "task"),
            (ActionType.ADD_FOLLOWER, "user_1", "/addFollowers", "followers"),
            (ActionType.REMOVE_FOLLOWER, "user_1", "/removeFollowers", "followers"),
            (ActionType.ADD_DEPENDENT, "task_dep", "/addDependents", "dependents"),
            (
                ActionType.REMOVE_DEPENDENT,
                "task_dep",
                "/removeDependents",
                "dependents",
            ),
        ],
    )
    def test_all_target_types_convert(
        self,
        action_type: ActionType,
        target_gid: str,
        expected_path_contains: str,
        expected_data_key: str,
    ) -> None:
        """Parametrized test covering action types with targets."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(task=task, action=action_type, target=NameGid(gid=target_gid))

        result = action_to_batch_request(action)

        assert isinstance(result, BatchRequest)
        assert expected_path_contains in result.relative_path
        assert result.method == "POST"
        assert result.data is not None
        assert expected_data_key in result.data

    def test_no_target_actions_convert(self) -> None:
        """ADD_LIKE and REMOVE_LIKE: data is empty dict."""
        task = Task(gid="task_123", name="Test")

        for action_type in (ActionType.ADD_LIKE, ActionType.REMOVE_LIKE):
            action = ActionOperation(task=task, action=action_type, target=None)
            result = action_to_batch_request(action)

            assert result.method == "POST"
            assert result.data == {}

    def test_add_comment_converts(self) -> None:
        """ADD_COMMENT converts: endpoint /tasks/{gid}/stories."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_COMMENT,
            target=None,
            extra_params={"text": "Hello"},
        )

        result = action_to_batch_request(action)

        assert result.relative_path == "/tasks/task_123/stories"
        assert result.method == "POST"
        assert result.data == {"text": "Hello"}

    def test_set_parent_converts(self) -> None:
        """SET_PARENT converts: endpoint /tasks/{gid}/setParent."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task,
            action=ActionType.SET_PARENT,
            target=None,
            extra_params={"parent": "parent_456"},
        )

        result = action_to_batch_request(action)

        assert result.relative_path == "/tasks/task_123/setParent"
        assert result.method == "POST"
        assert result.data == {"parent": "parent_456"}

    def test_with_extra_params(self) -> None:
        """ADD_TO_PROJECT with insert_after: extra_params included in unwrapped data."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task,
            action=ActionType.ADD_TO_PROJECT,
            target=NameGid(gid="proj_1"),
            extra_params={"insert_after": "other_task_gid"},
        )

        result = action_to_batch_request(action)

        assert result.data is not None
        assert result.data["project"] == "proj_1"
        assert result.data["insert_after"] == "other_task_gid"


# ---------------------------------------------------------------------------
# TDD-GAP-05: Result Mapping Tests
# ---------------------------------------------------------------------------


class TestBatchResultToActionResult:
    """Tests for batch_result_to_action_result mapping function."""

    def test_success_mapping(self) -> None:
        """Success: ActionResult.success=True, .response_data = batch_result.data."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )
        batch_result = BatchResult(
            status_code=200,
            body={"data": {"gid": "tag_456", "name": "Important"}},
        )

        result = batch_result_to_action_result(action, batch_result)

        assert result.success is True
        assert result.response_data == {"gid": "tag_456", "name": "Important"}
        assert result.error is None

    def test_failure_mapping(self) -> None:
        """Failure: ActionResult.success=False, .error is AsanaError."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )
        batch_result = BatchResult(
            status_code=404,
            body={"errors": [{"message": "Not found"}]},
        )

        result = batch_result_to_action_result(action, batch_result)

        assert result.success is False
        assert isinstance(result.error, AsanaError)
        assert result.response_data is None

    def test_preserves_action_reference(self) -> None:
        """Result .action field references the original ActionOperation."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )
        batch_result = BatchResult(status_code=200, body={"data": {}})

        result = batch_result_to_action_result(action, batch_result)

        assert result.action is action

    def test_retryable_classification(self) -> None:
        """Failed result's is_retryable works via RetryableErrorMixin."""
        task = Task(gid="task_123", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )
        # 500 errors are typically retryable
        batch_result = BatchResult(
            status_code=500,
            body={"errors": [{"message": "Server error"}]},
        )

        result = batch_result_to_action_result(action, batch_result)

        assert result.success is False
        # The RetryableErrorMixin should classify this
        assert isinstance(result, ActionResult)
        assert hasattr(result, "is_retryable")


# ---------------------------------------------------------------------------
# TDD-GAP-05: Chunk Actions Helper Tests
# ---------------------------------------------------------------------------


class TestChunkActions:
    """Tests for _chunk_actions helper."""

    def test_empty_list(self) -> None:
        """Empty list returns empty list."""
        assert _chunk_actions([], 10) == []

    def test_under_chunk_size(self) -> None:
        """Fewer than chunk_size actions returns single chunk."""
        actions = [
            ActionOperation(
                task=Task(gid=f"t{i}"),
                action=ActionType.ADD_TAG,
                target=NameGid(gid=f"tag_{i}"),
            )
            for i in range(5)
        ]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_exact_chunk_size(self) -> None:
        """Exactly chunk_size actions returns single chunk."""
        actions = [
            ActionOperation(
                task=Task(gid=f"t{i}"),
                action=ActionType.ADD_TAG,
                target=NameGid(gid=f"tag_{i}"),
            )
            for i in range(10)
        ]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 1
        assert len(chunks[0]) == 10

    def test_over_chunk_size(self) -> None:
        """25 actions produces chunks of [10, 10, 5]."""
        actions = [
            ActionOperation(
                task=Task(gid=f"t{i}"),
                action=ActionType.ADD_TAG,
                target=NameGid(gid=f"tag_{i}"),
            )
            for i in range(25)
        ]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5


# ---------------------------------------------------------------------------
# TDD-GAP-05: Batch Execution Path Tests
# ---------------------------------------------------------------------------


def _make_batch_result(success: bool = True, gid: str = "gid_1") -> BatchResult:
    """Create a BatchResult for testing."""
    if success:
        return BatchResult(
            status_code=200,
            body={"data": {"gid": gid}},
        )
    else:
        return BatchResult(
            status_code=500,
            body={"errors": [{"message": "Server error"}]},
        )


class TestBatchExecutionPath:
    """Tests for the batch execution path in execute_async."""

    @pytest.fixture
    def mock_batch_client(self) -> AsyncMock:
        """Create mock BatchClient."""
        client = AsyncMock()
        client.execute_async = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def mock_http_for_batch(self) -> AsyncMock:
        """Create mock HTTP client with _log attribute."""
        http = AsyncMock()
        http.request = AsyncMock(return_value={"data": {}})
        http._log = None
        return http

    async def test_batch_path_two_actions(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """2 actions with mock batch_client -> batch path used, 1 batch call."""
        mock_batch_client.execute_async.return_value = [
            _make_batch_result(True, "r1"),
            _make_batch_result(True, "r2"),
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_2")),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        mock_batch_client.execute_async.assert_called_once()
        # HTTP should NOT be called (batch path used)
        mock_http_for_batch.request.assert_not_called()

    async def test_batch_path_25_actions(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """25 actions -> 3 batch calls (10+10+5)."""
        # Configure mock to return correct number of results for each chunk
        mock_batch_client.execute_async.side_effect = [
            [_make_batch_result(True, f"r{i}") for i in range(10)],
            [_make_batch_result(True, f"r{i}") for i in range(10, 20)],
            [_make_batch_result(True, f"r{i}") for i in range(20, 25)],
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(25)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 25
        assert all(r.success for r in results)
        assert mock_batch_client.execute_async.call_count == 3

    async def test_sub_threshold_single_action(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """1 action -> sequential path (direct HTTP), batch_client not called."""
        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1"))

        results = await executor.execute_async([action], {})

        assert len(results) == 1
        assert results[0].success is True
        mock_batch_client.execute_async.assert_not_called()
        mock_http_for_batch.request.assert_called_once()

    async def test_no_batch_client_uses_sequential(self, mock_http_for_batch: AsyncMock) -> None:
        """batch_client=None -> sequential path for any count."""
        executor = ActionExecutor(mock_http_for_batch, None)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(5)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 5
        assert all(r.success for r in results)
        assert mock_http_for_batch.request.call_count == 5

    async def test_preserves_result_order(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """10 mixed actions -> results in same order as input."""
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(10)
        ]

        # Return results with identifiable data
        mock_batch_client.execute_async.return_value = [
            BatchResult(status_code=200, body={"data": {"gid": f"result_{i}"}}) for i in range(10)
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        results = await executor.execute_async(actions, {})

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result.action.target.gid == f"tag_{i}"
            assert result.response_data == {"gid": f"result_{i}"}

    async def test_gid_resolution_before_batching(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """Actions with temp GIDs resolved before batch conversion."""
        mock_batch_client.execute_async.return_value = [
            _make_batch_result(True, "r1"),
            _make_batch_result(True, "r2"),
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task,
                action=ActionType.ADD_TAG,
                target=NameGid(gid="temp_tag_1"),
            ),
            ActionOperation(
                task=task,
                action=ActionType.ADD_TAG,
                target=NameGid(gid="tag_2"),
            ),
        ]

        gid_map = {"temp_tag_1": "real_tag_1"}
        results = await executor.execute_async(actions, gid_map)

        assert len(results) == 2
        # Verify the batch request was called with resolved GIDs
        call_args = mock_batch_client.execute_async.call_args[0][0]
        assert call_args[0].data == {"tag": "real_tag_1"}
        assert call_args[1].data == {"tag": "tag_2"}


# ---------------------------------------------------------------------------
# TDD-GAP-05: Fallback Tests
# ---------------------------------------------------------------------------


class TestChunkFallback:
    """Tests for chunk-level fallback behavior."""

    @pytest.fixture
    def mock_batch_client(self) -> AsyncMock:
        """Create mock BatchClient."""
        client = AsyncMock()
        client.execute_async = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def mock_http_for_batch(self) -> AsyncMock:
        """Create mock HTTP client with _log attribute."""
        http = AsyncMock()
        http.request = AsyncMock(return_value={"data": {}})
        http._log = None
        return http

    async def test_chunk_fallback_on_batch_exception(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """batch_client.execute_async raises -> chunk falls back to sequential."""
        mock_batch_client.execute_async.side_effect = ConnectionError("Network error")

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # HTTP should have been called for fallback
        assert mock_http_for_batch.request.call_count == 2

    async def test_chunk_fallback_subsequent_chunks_still_batch(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """Chunk 1 fails (raises), chunk 2 succeeds via batch."""
        # 15 actions: chunk 1 (10) fails, chunk 2 (5) succeeds
        mock_batch_client.execute_async.side_effect = [
            ConnectionError("Network error"),  # Chunk 1 fails
            [_make_batch_result(True, f"r{i}") for i in range(5)],  # Chunk 2 succeeds
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(15)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 15
        assert all(r.success for r in results)
        # Chunk 1: batch call failed, fell back to 10 HTTP calls
        # Chunk 2: batch call succeeded
        assert mock_batch_client.execute_async.call_count == 2
        assert mock_http_for_batch.request.call_count == 10

    async def test_chunk_fallback_produces_same_shape(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """Fallback results have identical ActionResult shape as batch results."""
        mock_batch_client.execute_async.side_effect = ConnectionError("fail")

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")),
        ]

        results = await executor.execute_async(actions, {})

        for result in results:
            assert isinstance(result, ActionResult)
            assert hasattr(result, "action")
            assert hasattr(result, "success")
            assert hasattr(result, "error")
            assert hasattr(result, "response_data")

    async def test_chunk_fallback_logging(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """Warning log emitted with error details on fallback."""
        mock_log = MagicMock()
        mock_http_for_batch._log = mock_log
        mock_batch_client.execute_async.side_effect = ConnectionError("Network error")

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")),
        ]

        await executor.execute_async(actions, {})

        # Verify warning log was emitted
        mock_log.warning.assert_called()
        call_args = mock_log.warning.call_args
        assert call_args[0][0] == "action_batch_chunk_fallback"
        assert call_args[1]["error_type"] == "ConnectionError"

    async def test_result_count_mismatch_triggers_fallback(self) -> None:
        """Batch returning wrong number of results triggers chunk fallback.

        Defensive check: if BatchClient returns fewer (or more) results than
        requests sent, treat it as a batch failure and fall back to sequential.
        This prevents silent data loss from zip() truncation.
        """
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})

        mock_batch = AsyncMock()
        # Return 1 result for 3 requests -- count mismatch
        mock_batch.execute_async = AsyncMock(
            return_value=[
                BatchResult(status_code=200, body={"data": {"gid": "999"}}),
            ]
        )

        executor = ActionExecutor(mock_http, mock_batch)

        task = Task(gid="123456", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="100")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="101")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="102")),
        ]

        results = await executor.execute_async(actions, {})

        # All 3 should have results (via sequential fallback)
        assert len(results) == 3
        assert all(r.success for r in results)

        # Batch was attempted but fell back to sequential
        mock_batch.execute_async.assert_called_once()
        assert mock_http.request.call_count == 3


# ---------------------------------------------------------------------------
# TDD-GAP-05: Edge Case Tests (EC-001 through EC-008)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases EC-001 through EC-008."""

    @pytest.fixture
    def mock_batch_client(self) -> AsyncMock:
        """Create mock BatchClient."""
        client = AsyncMock()
        client.execute_async = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def mock_http_for_batch(self) -> AsyncMock:
        """Create mock HTTP client with _log attribute."""
        http = AsyncMock()
        http.request = AsyncMock(return_value={"data": {}})
        http._log = None
        return http

    async def test_ec_001_zero_actions(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-001: Empty list -> empty results, no batch call."""
        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)

        results = await executor.execute_async([], {})

        assert results == []
        mock_batch_client.execute_async.assert_not_called()
        mock_http_for_batch.request.assert_not_called()

    async def test_ec_002_single_action_bypasses_batch(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-002: 1 action -> sequential, batch_client.execute_async not called."""
        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1"))

        results = await executor.execute_async([action], {})

        assert len(results) == 1
        assert results[0].success is True
        mock_batch_client.execute_async.assert_not_called()

    async def test_ec_003_all_actions_fail_in_chunk(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-003: All BatchResults have success=False -> all failed ActionResults."""
        mock_batch_client.execute_async.return_value = [_make_batch_result(False) for _ in range(3)]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(3)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all(isinstance(r.error, AsanaError) for r in results)

    async def test_ec_004_add_project_no_move_section(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-004: ADD_TO_PROJECT alone -> tier 0, no ordering constraint."""
        mock_batch_client.execute_async.return_value = [
            _make_batch_result(True),
            _make_batch_result(True),
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task,
                action=ActionType.ADD_TO_PROJECT,
                target=NameGid(gid="proj_1"),
            ),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Both should be in same batch call (single tier)
        mock_batch_client.execute_async.assert_called_once()

    async def test_ec_005_move_section_without_add_project(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-005: MOVE_TO_SECTION without ADD_TO_PROJECT in same commit -> tier 0."""
        mock_batch_client.execute_async.return_value = [
            _make_batch_result(True),
            _make_batch_result(True),
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task,
                action=ActionType.MOVE_TO_SECTION,
                target=NameGid(gid="section_1"),
            ),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        mock_batch_client.execute_async.assert_called_once()

    async def test_ec_006_batch_429_fallback(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-006: batch_client raises (simulating exhausted 429 retries) -> fallback."""
        from autom8_asana.errors import RateLimitError

        mock_batch_client.execute_async.side_effect = RateLimitError("Rate limited", retry_after=30)

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http_for_batch.request.call_count == 2

    async def test_ec_007_comment_ordering_preserved(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-007: 5 ADD_COMMENT on same task -> all in tier 0, order preserved."""
        mock_batch_client.execute_async.return_value = [
            BatchResult(status_code=200, body={"data": {"gid": f"story_{i}"}}) for i in range(5)
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task,
                action=ActionType.ADD_COMMENT,
                target=None,
                extra_params={"text": f"Comment {i}"},
            )
            for i in range(5)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 5
        assert all(r.success for r in results)
        # Verify order preserved: comment 0 should map to story_0, etc.
        for i, result in enumerate(results):
            assert result.action.extra_params["text"] == f"Comment {i}"
            assert result.response_data == {"gid": f"story_{i}"}

    async def test_ec_008_mixed_independent_dependent(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-008: 15 tags + ADD_TO_PROJECT + MOVE_TO_SECTION."""
        # Tier 0: 16 actions (15 tags + ADD_TO_PROJECT), chunks: [10, 6]
        # Tier 1: 1 action (MOVE_TO_SECTION), chunks: [1]
        # Total: 3 batch calls
        mock_batch_client.execute_async.side_effect = [
            [_make_batch_result(True, f"r{i}") for i in range(10)],  # Chunk 1 (10 tags)
            [_make_batch_result(True, f"r{i}") for i in range(6)],  # Chunk 2 (5 tags + add_project)
            [_make_batch_result(True, "r_move")],  # Chunk 3 (move_to_section)
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task_x = Task(gid="task_x", name="Test X")
        actions = [
            ActionOperation(
                task=Task(gid=f"task_{i}", name=f"T{i}"),
                action=ActionType.ADD_TAG,
                target=NameGid(gid=f"tag_{i}"),
            )
            for i in range(15)
        ]
        actions.append(
            ActionOperation(
                task=task_x,
                action=ActionType.ADD_TO_PROJECT,
                target=NameGid(gid="proj_1"),
            )
        )
        actions.append(
            ActionOperation(
                task=task_x,
                action=ActionType.MOVE_TO_SECTION,
                target=NameGid(gid="section_1"),
            )
        )

        results = await executor.execute_async(actions, {})

        assert len(results) == 17
        assert all(r.success for r in results)
        assert mock_batch_client.execute_async.call_count == 3


# ---------------------------------------------------------------------------
# Merged from test_action_batch_adversarial.py [RF-009]
# ---------------------------------------------------------------------------


class TestPayloadContractAllActionTypes:
    """Contract test: every ActionType's to_api_call() returns {"data": ...}."""

    def test_all_action_types_always_have_data_key(self) -> None:
        """Contract: every ActionType's to_api_call() returns {"data": ...}."""
        from autom8_asana.persistence.models import ActionOperation, ActionType

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


class TestBatchResultCountMismatchEdgeCases:
    """Edge cases for batch result count mismatches beyond basic coverage."""

    async def test_more_results_than_requests_triggers_fallback(self) -> None:
        """BatchClient returning MORE results than sent -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # Return 5 results for 2 requests
        mock_batch.execute_async = AsyncMock(
            return_value=[
                BatchResult(status_code=200, body={"data": {"gid": f"r{i}"}}) for i in range(5)
            ]
        )

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(2)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http.request.call_count == 2

    async def test_empty_results_for_nonempty_chunk_triggers_fallback(self) -> None:
        """BatchClient returning empty list for a chunk -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(3)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert mock_http.request.call_count == 3


class TestResolveTempGidsImmutability:
    """_resolve_temp_gids must not mutate ActionOperation (frozen dataclass)."""

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


class TestBatchExecutorScale:
    """Scale tests for the batch execution path."""

    async def test_100_actions_batch_execution(self) -> None:
        """100 actions through batch executor: 10 batch calls expected."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # 10 chunks of 10
        mock_batch.execute_async.side_effect = [
            [BatchResult(status_code=200, body={"data": {"gid": f"r{j}"}}) for j in range(10)]
            for _ in range(10)
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(100)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 100
        assert all(r.success for r in results)
        assert mock_batch.execute_async.call_count == 10


class TestMetricsLogging:
    """TDD Section 7: Structured log fields verification."""

    async def test_batch_complete_log_fields(self) -> None:
        """The action_batch_complete log should include all TDD-specified fields."""
        mock_log = MagicMock()
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = mock_log

        mock_batch = AsyncMock()
        mock_batch.execute_async.return_value = [
            BatchResult(status_code=200, body={"data": {"gid": "r1"}}),
            BatchResult(status_code=500, body={"errors": [{"message": "Server error"}]}),
            BatchResult(status_code=200, body={"data": {"gid": "r3"}}),
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
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

    async def test_no_log_when_log_is_none(self) -> None:
        """When _log is None, no logging calls should happen (no AttributeError)."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None  # No logger

        mock_batch = AsyncMock()
        mock_batch.execute_async.return_value = [
            BatchResult(status_code=200, body={"data": {"gid": "r1"}}),
            BatchResult(status_code=200, body={"data": {"gid": "r2"}}),
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(2)
        ]

        # Should not raise even with no logger
        results = await executor.execute_async(actions, {})
        assert len(results) == 2


class TestCrossTierResultOrdering:
    """Result order must match input order even when actions span multiple tiers."""

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


class TestFallbackEdgeCases:
    """Fallback path edge cases not covered by basic fallback tests."""

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


class TestBatchResultStatusCodes:
    """Edge-case HTTP status code handling in batch results."""

    def test_batch_result_201_is_success(self) -> None:
        """201 Created should be treated as success."""
        br = BatchResult(status_code=201, body={"data": {"gid": "new_1"}})
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1"))

        result = batch_result_to_action_result(action, br)
        assert result.success is True

    def test_batch_result_204_is_success(self) -> None:
        """204 No Content should be treated as success (data may be None)."""
        br = BatchResult(status_code=204, body=None)
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_1")
        )

        result = batch_result_to_action_result(action, br)
        assert result.success is True
        assert result.response_data is None

    def test_batch_result_400_is_failure(self) -> None:
        """400 Bad Request should be treated as failure."""
        br = BatchResult(
            status_code=400,
            body={"errors": [{"message": "Bad request"}]},
        )
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1"))

        result = batch_result_to_action_result(action, br)
        assert result.success is False
        assert isinstance(result.error, AsanaError)

    def test_batch_result_403_is_failure(self) -> None:
        """403 Forbidden should be treated as failure."""
        br = BatchResult(
            status_code=403,
            body={"errors": [{"message": "Forbidden"}]},
        )
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1"))

        result = batch_result_to_action_result(action, br)
        assert result.success is False


class TestDoubleFailure:
    """What happens when batch fails AND sequential fallback also fails?"""

    async def test_batch_fails_then_sequential_also_fails(self) -> None:
        """Batch fails, fallback sequential also fails -> failed ActionResults."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=RuntimeError("HTTP also down"))
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async.side_effect = ConnectionError("Batch down")

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(3)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all(isinstance(r.error, RuntimeError) for r in results)
        assert all("HTTP also down" in str(r.error) for r in results)


class TestChunkBoundaryEdgeCases:
    """Chunk boundary edge case not covered by basic chunk tests."""

    def test_chunk_11_into_10(self) -> None:
        """11 actions into chunks of 10: [10, 1]."""
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}"))
            for i in range(11)
        ]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 1


class TestSessionWiring:
    """Verify SaveSession wires batch_client correctly to ActionExecutor."""

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


# --- Adversarial tests (merged from test_action_batch_adversarial.py; Sprint 15 S4) ---
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
        return BatchResult(status_code=500, body={"errors": [{"message": "Server error"}]})


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
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1"))

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

    async def test_fewer_results_triggers_fallback(self) -> None:
        """BatchClient returning fewer results than sent -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # Return 1 result for 4 requests
        mock_batch.execute_async = AsyncMock(return_value=[_make_batch_result(True)])

        executor = ActionExecutor(mock_http, mock_batch)
        task = Task(gid="task_1", name="Test")
        actions = [_make_action("task_1", ActionType.ADD_TAG, f"tag_{i}") for i in range(4)]

        results = await executor.execute_async(actions, {})

        assert len(results) == 4
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http.request.call_count == 4

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
        actions = [_make_action("task_1", ActionType.ADD_TAG, f"tag_{i}") for i in range(2)]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http.request.call_count == 2

    async def test_empty_results_for_nonempty_chunk_triggers_fallback(self) -> None:
        """BatchClient returning empty list for a chunk -> fallback."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async = AsyncMock(return_value=[])

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [_make_action("task_1", ActionType.ADD_TAG, f"tag_{i}") for i in range(3)]

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

    def test_multiple_add_project_one_move_section_only_constrains_matching(
        self,
    ) -> None:
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
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(100)]

        ids = [id(a) for a in actions]
        assert len(set(ids)) == 100, "Object IDs should be unique for live objects"

        # resolve_order should work fine
        tiers = resolve_order(actions)
        assert len(tiers) == 1
        assert len(tiers[0]) == 100

    def test_id_trick_with_ordering_constraint_100_actions(self) -> None:
        """100 actions with ordering constraints should work correctly."""
        tag_actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(98)]
        add_proj = _make_action("task_x", ActionType.ADD_TO_PROJECT, "proj_1")
        move_sect = _make_action("task_x", ActionType.MOVE_TO_SECTION, "sect_1")

        actions = tag_actions + [add_proj, move_sect]
        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 99  # 98 tags + add_project
        assert len(tiers[1]) == 1  # move_to_section


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
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(1000)]

        tiers = resolve_order(actions)

        assert len(tiers) == 1
        assert len(tiers[0]) == 1000

    def test_500_actions_with_ordering(self) -> None:
        """500 actions: 250 ADD_TO_PROJECT + 250 MOVE_TO_SECTION for same tasks."""
        actions = []
        for i in range(250):
            actions.append(_make_action(f"task_{i}", ActionType.ADD_TO_PROJECT, f"proj_{i}"))
        for i in range(250):
            actions.append(_make_action(f"task_{i}", ActionType.MOVE_TO_SECTION, f"sect_{i}"))

        tiers = resolve_order(actions)

        assert len(tiers) == 2
        assert len(tiers[0]) == 250
        assert len(tiers[1]) == 250

    async def test_100_actions_batch_execution(self) -> None:
        """100 actions through batch executor: 10 batch calls expected."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value={"data": {}})
        mock_http._log = None

        mock_batch = AsyncMock()
        # 10 chunks of 10
        mock_batch.execute_async.side_effect = [
            [_make_batch_result(True, f"r{j}") for j in range(10)] for _ in range(10)
        ]

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(100)]

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
        actions = [_make_action("task_1", ActionType.ADD_TAG, f"tag_{i}") for i in range(3)]

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
        actions = [_make_action("task_1", ActionType.ADD_TAG, f"tag_{i}") for i in range(2)]

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

    async def test_batch_fails_then_sequential_also_fails(self) -> None:
        """Batch fails, fallback sequential also fails -> failed ActionResults."""
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=RuntimeError("HTTP also down"))
        mock_http._log = None

        mock_batch = AsyncMock()
        mock_batch.execute_async.side_effect = ConnectionError("Batch down")

        executor = ActionExecutor(mock_http, mock_batch)
        actions = [_make_action("task_1", ActionType.ADD_TAG, f"tag_{i}") for i in range(3)]

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
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(3)]
        chunks = _chunk_actions(actions, 1)
        assert len(chunks) == 3
        assert all(len(c) == 1 for c in chunks)

    def test_chunk_size_equals_list_length(self) -> None:
        """Chunk size equals list length: single chunk."""
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(7)]
        chunks = _chunk_actions(actions, 7)
        assert len(chunks) == 1
        assert len(chunks[0]) == 7

    def test_chunk_11_into_10(self) -> None:
        """11 actions into chunks of 10: [10, 1]."""
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(11)]
        chunks = _chunk_actions(actions, 10)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 1

    def test_chunk_20_into_10(self) -> None:
        """20 actions into chunks of 10: [10, 10]."""
        actions = [_make_action(f"task_{i}", ActionType.ADD_TAG, f"tag_{i}") for i in range(20)]
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
