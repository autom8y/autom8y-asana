"""Tests for ActionExecutor.

Per TDD-0011: Verify action execution and GID resolution.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.action_executor import ActionExecutor
from autom8_asana.persistence.models import (
    ActionType,
    ActionOperation,
    ActionResult,
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
    async def test_execute_empty_actions(
        self, executor: ActionExecutor
    ) -> None:
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
            target_gid="tag_456",
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
            ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_1"),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_2"),
            ActionOperation(task=task, action=ActionType.REMOVE_TAG, target_gid="tag_3"),
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
            target_gid="tag_456",
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
            ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_1"),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_2"),
            ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_3"),
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
            ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_1"),
            ActionOperation(task=task, action=ActionType.REMOVE_TAG, target_gid="tag_2"),
            ActionOperation(task=task, action=ActionType.ADD_TO_PROJECT, target_gid="proj_3"),
        ]

        results = await executor.execute_async(actions, {})

        assert len(results) == 3
        assert results[0].action.target_gid == "tag_1"
        assert results[1].action.target_gid == "tag_2"
        assert results[2].action.target_gid == "proj_3"


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
            target_gid="temp_tag_456",
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
            target_gid="tag_456",  # Not a temp GID
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
            target_gid="temp_not_in_map",
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
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_456")

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
        action = ActionOperation(task=task, action=ActionType.REMOVE_TAG, target_gid="tag_456")

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
            task=task, action=ActionType.ADD_TO_PROJECT, target_gid="proj_789"
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
            task=task, action=ActionType.REMOVE_FROM_PROJECT, target_gid="proj_789"
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
            task=task, action=ActionType.ADD_DEPENDENCY, target_gid="task_456"
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
            task=task, action=ActionType.REMOVE_DEPENDENCY, target_gid="task_456"
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
            task=task, action=ActionType.MOVE_TO_SECTION, target_gid="section_789"
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
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_456")

        mock_http.request.return_value = {"data": {"gid": "tag_456", "name": "Important"}}

        results = await executor.execute_async([action], {})

        assert results[0].success is True
        assert results[0].response_data == {"data": {"gid": "tag_456", "name": "Important"}}
        assert results[0].error is None

    @pytest.mark.asyncio
    async def test_failure_stores_error(
        self, executor: ActionExecutor, mock_http: AsyncMock
    ) -> None:
        """Failed action stores error information."""
        task = Task(gid="task_123")
        action = ActionOperation(task=task, action=ActionType.ADD_TAG, target_gid="tag_456")

        error = ValueError("Invalid tag")
        mock_http.request.side_effect = error

        results = await executor.execute_async([action], {})

        assert results[0].success is False
        assert results[0].error is error
        assert results[0].response_data is None
