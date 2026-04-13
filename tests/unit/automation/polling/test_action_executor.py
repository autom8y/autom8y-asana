"""Tests for polling automation action executor.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for ActionExecutor that executes
actions on tasks matching automation rule conditions.

Covers:
- Each action type executes correct API method
- Invalid action type raises ValueError
- Missing required params raises ValueError
- API errors wrapped in ActionResult with success=False
- ActionResult contains correct metadata
- Logging is called for success/failure
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.polling.action_executor import (
    ActionExecutor,
    ActionResult,
)
from autom8_asana.automation.polling.config_schema import ActionConfig


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_action_result_success_defaults(self) -> None:
        """ActionResult has correct defaults for success case."""
        result = ActionResult(
            success=True,
            action_type="add_tag",
            task_gid="task-123",
        )

        assert result.success is True
        assert result.action_type == "add_tag"
        assert result.task_gid == "task-123"
        assert result.error is None
        assert result.details == {}

    def test_action_result_failure_with_error(self) -> None:
        """ActionResult captures error message on failure."""
        result = ActionResult(
            success=False,
            action_type="add_comment",
            task_gid="task-456",
            error="API rate limit exceeded",
        )

        assert result.success is False
        assert result.error == "API rate limit exceeded"

    def test_action_result_with_details(self) -> None:
        """ActionResult captures execution details."""
        result = ActionResult(
            success=True,
            action_type="change_section",
            task_gid="task-789",
            details={"section_gid": "section-999"},
        )

        assert result.details == {"section_gid": "section-999"}


class TestActionExecutorAddTag:
    """Tests for add_tag action execution."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with tags sub-client."""
        client = MagicMock()
        client.tags = MagicMock()
        client.tags.add_to_task_async = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> ActionExecutor:
        """Create ActionExecutor with mock client."""
        return ActionExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_add_tag_executes_correct_api_method(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """add_tag action calls tags.add_to_task_async with correct params."""
        action = ActionConfig(type="add_tag", params={"tag_gid": "tag-123"})

        result = await executor.execute_async("task-456", action)

        assert result.success is True
        assert result.action_type == "add_tag"
        assert result.task_gid == "task-456"
        mock_client.tags.add_to_task_async.assert_called_once_with("task-456", tag="tag-123")

    @pytest.mark.asyncio
    async def test_add_tag_returns_details_on_success(
        self,
        executor: ActionExecutor,
    ) -> None:
        """add_tag action returns params in details on success."""
        action = ActionConfig(type="add_tag", params={"tag_gid": "tag-999"})

        result = await executor.execute_async("task-111", action)

        assert result.details == {"tag_gid": "tag-999"}

    @pytest.mark.asyncio
    async def test_add_tag_handles_api_error(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """add_tag action wraps API error in ActionResult."""
        mock_client.tags.add_to_task_async.side_effect = Exception("Tag not found")
        action = ActionConfig(type="add_tag", params={"tag_gid": "invalid-tag"})

        result = await executor.execute_async("task-456", action)

        assert result.success is False
        assert result.error == "Tag not found"
        assert result.action_type == "add_tag"
        assert result.task_gid == "task-456"


class TestActionExecutorAddComment:
    """Tests for add_comment action execution."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with stories sub-client."""
        client = MagicMock()
        client.stories = MagicMock()
        client.stories.create_comment_async = AsyncMock(return_value=MagicMock())
        return client

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> ActionExecutor:
        """Create ActionExecutor with mock client."""
        return ActionExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_add_comment_executes_correct_api_method(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """add_comment action calls stories.create_comment_async."""
        action = ActionConfig(
            type="add_comment",
            params={"text": "This task has been escalated."},
        )

        result = await executor.execute_async("task-789", action)

        assert result.success is True
        assert result.action_type == "add_comment"
        mock_client.stories.create_comment_async.assert_called_once_with(
            task="task-789", text="This task has been escalated."
        )

    @pytest.mark.asyncio
    async def test_add_comment_handles_api_error(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """add_comment action wraps API error in ActionResult."""
        mock_client.stories.create_comment_async.side_effect = Exception("Task not found")
        action = ActionConfig(type="add_comment", params={"text": "Test comment"})

        result = await executor.execute_async("invalid-task", action)

        assert result.success is False
        assert result.error == "Task not found"


class TestActionExecutorChangeSection:
    """Tests for change_section action execution."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with sections sub-client."""
        client = MagicMock()
        client.sections = MagicMock()
        client.sections.add_task_async = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> ActionExecutor:
        """Create ActionExecutor with mock client."""
        return ActionExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_change_section_executes_correct_api_method(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """change_section action calls sections.add_task_async."""
        action = ActionConfig(
            type="change_section",
            params={"section_gid": "section-archive"},
        )

        result = await executor.execute_async("task-old", action)

        assert result.success is True
        assert result.action_type == "change_section"
        mock_client.sections.add_task_async.assert_called_once_with(
            "section-archive", task="task-old"
        )

    @pytest.mark.asyncio
    async def test_change_section_handles_api_error(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """change_section action wraps API error in ActionResult."""
        mock_client.sections.add_task_async.side_effect = Exception("Section not found")
        action = ActionConfig(type="change_section", params={"section_gid": "invalid-section"})

        result = await executor.execute_async("task-123", action)

        assert result.success is False
        assert result.error == "Section not found"


class TestActionExecutorValidation:
    """Tests for action validation."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create basic mock client."""
        return MagicMock()

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> ActionExecutor:
        """Create ActionExecutor with mock client."""
        return ActionExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_invalid_action_type_raises_value_error(
        self,
        executor: ActionExecutor,
    ) -> None:
        """Unsupported action type raises ValueError."""
        action = ActionConfig(type="delete_task", params={})

        with pytest.raises(ValueError) as exc_info:
            await executor.execute_async("task-123", action)

        assert "Unsupported action type: 'delete_task'" in str(exc_info.value)
        assert "add_tag" in str(exc_info.value)  # Lists supported types

    @pytest.mark.asyncio
    async def test_missing_required_params_raises_value_error_add_tag(
        self,
        executor: ActionExecutor,
    ) -> None:
        """add_tag without tag_gid raises ValueError."""
        action = ActionConfig(type="add_tag", params={})

        with pytest.raises(ValueError) as exc_info:
            await executor.execute_async("task-123", action)

        assert "Missing required params" in str(exc_info.value)
        assert "tag_gid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_required_params_raises_value_error_add_comment(
        self,
        executor: ActionExecutor,
    ) -> None:
        """add_comment without text raises ValueError."""
        action = ActionConfig(type="add_comment", params={})

        with pytest.raises(ValueError) as exc_info:
            await executor.execute_async("task-123", action)

        assert "Missing required params" in str(exc_info.value)
        assert "text" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_required_params_raises_value_error_change_section(
        self,
        executor: ActionExecutor,
    ) -> None:
        """change_section without section_gid raises ValueError."""
        action = ActionConfig(type="change_section", params={})

        with pytest.raises(ValueError) as exc_info:
            await executor.execute_async("task-123", action)

        assert "Missing required params" in str(exc_info.value)
        assert "section_gid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extra_params_allowed(
        self,
        executor: ActionExecutor,
    ) -> None:
        """Extra params beyond required ones are allowed."""
        # Mock the client to have the required sub-client
        executor._client.tags = MagicMock()
        executor._client.tags.add_to_task_async = AsyncMock()

        action = ActionConfig(
            type="add_tag",
            params={
                "tag_gid": "tag-123",
                "extra_param": "ignored",
            },
        )

        # Should not raise
        result = await executor.execute_async("task-456", action)

        assert result.success is True


class TestActionExecutorLogging:
    """Tests for action executor logging."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client with all sub-clients."""
        client = MagicMock()
        client.tags = MagicMock()
        client.tags.add_to_task_async = AsyncMock()
        client.stories = MagicMock()
        client.stories.create_comment_async = AsyncMock()
        client.sections = MagicMock()
        client.sections.add_task_async = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_logs_action_start_and_success(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Executor logs action start and success."""
        with patch(
            "autom8_asana.automation.polling.action_executor.StructuredLogger"
        ) as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger_class.get_logger.return_value = mock_logger

            executor = ActionExecutor(mock_client)
            action = ActionConfig(type="add_tag", params={"tag_gid": "tag-123"})

            await executor.execute_async("task-456", action)

            # Should log start and success
            assert mock_logger.info.call_count == 2
            start_call = mock_logger.info.call_args_list[0]
            assert start_call[0][0] == "action_execution_started"

            success_call = mock_logger.info.call_args_list[1]
            assert success_call[0][0] == "action_execution_succeeded"

    @pytest.mark.asyncio
    async def test_logs_action_failure(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Executor logs action failure."""
        mock_client.tags.add_to_task_async.side_effect = Exception("API Error")

        with patch(
            "autom8_asana.automation.polling.action_executor.StructuredLogger"
        ) as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger_class.get_logger.return_value = mock_logger

            executor = ActionExecutor(mock_client)
            action = ActionConfig(type="add_tag", params={"tag_gid": "tag-123"})

            await executor.execute_async("task-456", action)

            # Should log start and failure
            mock_logger.info.assert_called_once()  # Start only
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert error_call[0][0] == "action_execution_failed"


class TestActionExecutorIsolation:
    """Tests for action error isolation."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock client."""
        client = MagicMock()
        client.tags = MagicMock()
        client.tags.add_to_task_async = AsyncMock()
        return client

    @pytest.fixture
    def executor(self, mock_client: MagicMock) -> ActionExecutor:
        """Create ActionExecutor."""
        return ActionExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_failed_action_does_not_prevent_subsequent_actions(
        self,
        executor: ActionExecutor,
        mock_client: MagicMock,
    ) -> None:
        """One action failure does not prevent other actions from executing."""
        # First call fails, second succeeds
        mock_client.tags.add_to_task_async.side_effect = [
            Exception("First failed"),
            None,  # Success
        ]

        action = ActionConfig(type="add_tag", params={"tag_gid": "tag-123"})

        # First execution - fails
        result1 = await executor.execute_async("task-1", action)
        assert result1.success is False

        # Second execution - succeeds (not affected by first failure)
        result2 = await executor.execute_async("task-2", action)
        assert result2.success is True

        # Both calls were made
        assert mock_client.tags.add_to_task_async.call_count == 2
