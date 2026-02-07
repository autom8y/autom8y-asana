"""Tests for ActionExecutor.

Per TDD-0011: Verify action execution and GID resolution.
Per TDD-GAP-05: Verify batch execution path, conversion functions,
                result mapping, fallback, and edge cases.
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

    @pytest.mark.asyncio
    async def test_execute_empty_actions(self, executor: ActionExecutor) -> None:
        """execute_async handles empty action list."""
        results = await executor.execute_async([], {})
        assert results == []

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_execute_multiple_actions(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async executes multiple actions sequentially."""
        task = Task(gid="task_123")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")
            ),
            ActionOperation(
                task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_3")
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_http.request.call_count == 3

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_execute_continues_after_error(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async continues processing after an error."""
        task = Task(gid="task_123")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_3")
            ),
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

    @pytest.mark.asyncio
    async def test_execute_preserves_order(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """execute_async preserves action order in results."""
        task = Task(gid="task_123")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.REMOVE_TAG, target=NameGid(gid="tag_2")
            ),
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_add_tag_api_call(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_success_stores_response_data(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """Successful action stores response data."""
        task = Task(gid="task_123")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_456")
        )

        mock_http.request.return_value = {
            "data": {"gid": "tag_456", "name": "Important"}
        }

        results = await executor.execute_async([action], {})

        assert results[0].success is True
        assert results[0].response_data == {
            "data": {"gid": "tag_456", "name": "Important"}
        }
        assert results[0].error is None

    @pytest.mark.asyncio
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
        action = ActionOperation(
            task=task, action=action_type, target=NameGid(gid=target_gid)
        )

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
                task=Task(gid=f"t{i}"), action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
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
                task=Task(gid=f"t{i}"), action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
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
                task=Task(gid=f"t{i}"), action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
            )
            for i in range(25)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 25
        assert all(r.success for r in results)
        assert mock_batch_client.execute_async.call_count == 3

    @pytest.mark.asyncio
    async def test_sub_threshold_single_action(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """1 action -> sequential path (direct HTTP), batch_client not called."""
        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
        )

        results = await executor.execute_async([action], {})

        assert len(results) == 1
        assert results[0].success is True
        mock_batch_client.execute_async.assert_not_called()
        mock_http_for_batch.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_batch_client_uses_sequential(
        self, mock_http_for_batch: AsyncMock
    ) -> None:
        """batch_client=None -> sequential path for any count."""
        executor = ActionExecutor(mock_http_for_batch, None)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
            )
            for i in range(5)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 5
        assert all(r.success for r in results)
        assert mock_http_for_batch.request.call_count == 5

    @pytest.mark.asyncio
    async def test_preserves_result_order(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """10 mixed actions -> results in same order as input."""
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
            )
            for i in range(10)
        ]

        # Return results with identifiable data
        mock_batch_client.execute_async.return_value = [
            BatchResult(status_code=200, body={"data": {"gid": f"result_{i}"}})
            for i in range(10)
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        results = await executor.execute_async(actions, {})

        assert len(results) == 10
        for i, result in enumerate(results):
            assert result.action.target.gid == f"tag_{i}"
            assert result.response_data == {"gid": f"result_{i}"}

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_chunk_fallback_on_batch_exception(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """batch_client.execute_async raises -> chunk falls back to sequential."""
        mock_batch_client.execute_async.side_effect = ConnectionError("Network error")

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # HTTP should have been called for fallback
        assert mock_http_for_batch.request.call_count == 2

    @pytest.mark.asyncio
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
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
            )
            for i in range(15)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 15
        assert all(r.success for r in results)
        # Chunk 1: batch call failed, fell back to 10 HTTP calls
        # Chunk 2: batch call succeeded
        assert mock_batch_client.execute_async.call_count == 2
        assert mock_http_for_batch.request.call_count == 10

    @pytest.mark.asyncio
    async def test_chunk_fallback_produces_same_shape(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """Fallback results have identical ActionResult shape as batch results."""
        mock_batch_client.execute_async.side_effect = ConnectionError("fail")

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")
            ),
        ]

        results = await executor.execute_async(actions, {})

        for result in results:
            assert isinstance(result, ActionResult)
            assert hasattr(result, "action")
            assert hasattr(result, "success")
            assert hasattr(result, "error")
            assert hasattr(result, "response_data")

    @pytest.mark.asyncio
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
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")
            ),
        ]

        await executor.execute_async(actions, {})

        # Verify warning log was emitted
        mock_log.warning.assert_called()
        call_args = mock_log.warning.call_args
        assert call_args[0][0] == "action_batch_chunk_fallback"
        assert call_args[1]["error_type"] == "ConnectionError"

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_ec_001_zero_actions(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-001: Empty list -> empty results, no batch call."""
        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)

        results = await executor.execute_async([], {})

        assert results == []
        mock_batch_client.execute_async.assert_not_called()
        mock_http_for_batch.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_ec_002_single_action_bypasses_batch(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-002: 1 action -> sequential, batch_client.execute_async not called."""
        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        action = ActionOperation(
            task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
        )

        results = await executor.execute_async([action], {})

        assert len(results) == 1
        assert results[0].success is True
        mock_batch_client.execute_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_ec_003_all_actions_fail_in_chunk(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-003: All BatchResults have success=False -> all failed ActionResults."""
        mock_batch_client.execute_async.return_value = [
            _make_batch_result(False) for _ in range(3)
        ]

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid=f"tag_{i}")
            )
            for i in range(3)
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert all(not r.success for r in results)
        assert all(isinstance(r.error, AsanaError) for r in results)

    @pytest.mark.asyncio
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
                task=task, action=ActionType.ADD_TO_PROJECT, target=NameGid(gid="proj_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Both should be in same batch call (single tier)
        mock_batch_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
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
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        mock_batch_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_ec_006_batch_429_fallback(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-006: batch_client raises (simulating exhausted 429 retries) -> fallback."""
        from autom8_asana.exceptions import RateLimitError

        mock_batch_client.execute_async.side_effect = RateLimitError(
            "Rate limited", retry_after=30
        )

        executor = ActionExecutor(mock_http_for_batch, mock_batch_client)
        task = Task(gid="task_1", name="Test")
        actions = [
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_1")
            ),
            ActionOperation(
                task=task, action=ActionType.ADD_TAG, target=NameGid(gid="tag_2")
            ),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 2
        assert all(r.success for r in results)
        # Fell back to sequential
        assert mock_http_for_batch.request.call_count == 2

    @pytest.mark.asyncio
    async def test_ec_007_comment_ordering_preserved(
        self, mock_http_for_batch: AsyncMock, mock_batch_client: AsyncMock
    ) -> None:
        """EC-007: 5 ADD_COMMENT on same task -> all in tier 0, order preserved."""
        mock_batch_client.execute_async.return_value = [
            BatchResult(status_code=200, body={"data": {"gid": f"story_{i}"}})
            for i in range(5)
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

    @pytest.mark.asyncio
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
