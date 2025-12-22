"""Tests for SubtaskWaiter.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT and ADR-0111: Tests for polling-based
subtask readiness detection.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


from autom8_asana.automation.waiter import SubtaskWaiter


class MockPageIterator:
    """Mock PageIterator that returns a fixed list."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    async def collect(self) -> list[Any]:
        return self._items


class MockTasksClient:
    """Mock TasksClient for testing SubtaskWaiter."""

    def __init__(self) -> None:
        self.subtasks_async = MagicMock()


class MockAsanaClient:
    """Mock AsanaClient for testing SubtaskWaiter."""

    def __init__(self) -> None:
        self.tasks = MockTasksClient()


def make_mock_subtask(gid: str) -> dict[str, Any]:
    """Create a mock subtask dict."""
    return {"gid": gid}


class TestSubtaskWaiterInit:
    """Tests for SubtaskWaiter initialization."""

    def test_init_with_defaults(self) -> None:
        """SubtaskWaiter initializes with default timeout and poll_interval."""
        client = MockAsanaClient()
        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]

        assert waiter._client is client
        assert waiter._default_timeout == 2.0
        assert waiter._default_poll_interval == 0.2

    def test_init_with_custom_defaults(self) -> None:
        """SubtaskWaiter accepts custom default timeout and poll_interval."""
        client = MockAsanaClient()
        waiter = SubtaskWaiter(
            client,  # type: ignore[arg-type]
            default_timeout=5.0,
            default_poll_interval=0.5,
        )

        assert waiter._default_timeout == 5.0
        assert waiter._default_poll_interval == 0.5


class TestGetSubtaskCountAsync:
    """Tests for SubtaskWaiter.get_subtask_count_async()."""

    async def test_returns_correct_count(self) -> None:
        """get_subtask_count_async returns the number of subtasks."""
        client = MockAsanaClient()
        subtasks = [
            make_mock_subtask("1"),
            make_mock_subtask("2"),
            make_mock_subtask("3"),
        ]
        client.tasks.subtasks_async.return_value = MockPageIterator(subtasks)

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        count = await waiter.get_subtask_count_async("task_123")

        assert count == 3
        client.tasks.subtasks_async.assert_called_once_with(
            "task_123", opt_fields=["gid"]
        )

    async def test_returns_zero_for_no_subtasks(self) -> None:
        """get_subtask_count_async returns 0 when no subtasks exist."""
        client = MockAsanaClient()
        client.tasks.subtasks_async.return_value = MockPageIterator([])

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        count = await waiter.get_subtask_count_async("task_123")

        assert count == 0


class TestWaitForSubtasksAsync:
    """Tests for SubtaskWaiter.wait_for_subtasks_async()."""

    async def test_returns_true_when_count_matches_immediately(self) -> None:
        """wait_for_subtasks_async returns True if count matches on first poll."""
        client = MockAsanaClient()
        subtasks = [make_mock_subtask("1"), make_mock_subtask("2")]
        client.tasks.subtasks_async.return_value = MockPageIterator(subtasks)

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=2,
            timeout=1.0,
        )

        assert result is True
        # Only one call needed since count matched immediately
        assert client.tasks.subtasks_async.call_count == 1

    async def test_returns_true_when_count_exceeds_expected(self) -> None:
        """wait_for_subtasks_async returns True if count exceeds expected."""
        client = MockAsanaClient()
        subtasks = [
            make_mock_subtask("1"),
            make_mock_subtask("2"),
            make_mock_subtask("3"),
        ]
        client.tasks.subtasks_async.return_value = MockPageIterator(subtasks)

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=2,  # Expect 2, but 3 exist
            timeout=1.0,
        )

        assert result is True

    async def test_polls_until_count_reached(self) -> None:
        """wait_for_subtasks_async polls until expected count is reached."""
        client = MockAsanaClient()
        # First call: 1 subtask, second call: 2 subtasks (expected)
        client.tasks.subtasks_async.side_effect = [
            MockPageIterator([make_mock_subtask("1")]),
            MockPageIterator([make_mock_subtask("1"), make_mock_subtask("2")]),
        ]

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=2,
            timeout=2.0,
            poll_interval=0.01,  # Fast polling for test
        )

        assert result is True
        assert client.tasks.subtasks_async.call_count == 2

    async def test_returns_false_on_timeout(self) -> None:
        """wait_for_subtasks_async returns False when timeout expires."""
        client = MockAsanaClient()
        # Always return 1 subtask, but expect 5
        client.tasks.subtasks_async.return_value = MockPageIterator(
            [make_mock_subtask("1")]
        )

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=5,
            timeout=0.05,  # Very short timeout
            poll_interval=0.01,
        )

        assert result is False
        # Should have polled multiple times before timing out
        assert client.tasks.subtasks_async.call_count >= 2

    async def test_logs_warning_on_timeout(self) -> None:
        """wait_for_subtasks_async logs warning when timeout expires."""
        client = MockAsanaClient()
        client.tasks.subtasks_async.return_value = MockPageIterator(
            [make_mock_subtask("1")]
        )

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]

        with patch("autom8_asana.automation.waiter.logger") as mock_logger:
            await waiter.wait_for_subtasks_async(
                "task_123",
                expected_count=5,
                timeout=0.02,
                poll_interval=0.01,
            )

            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "timeout" in warning_msg.lower()

    async def test_uses_default_timeout_when_not_specified(self) -> None:
        """wait_for_subtasks_async uses default timeout when not specified."""
        client = MockAsanaClient()
        subtasks = [make_mock_subtask("1")]
        client.tasks.subtasks_async.return_value = MockPageIterator(subtasks)

        waiter = SubtaskWaiter(
            client,  # type: ignore[arg-type]
            default_timeout=0.05,  # Short default for test
            default_poll_interval=0.01,
        )

        # This should timeout since we expect 5 but only 1 exists
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=5,
        )

        assert result is False

    async def test_uses_default_poll_interval_when_not_specified(self) -> None:
        """wait_for_subtasks_async uses default poll_interval when not specified."""
        client = MockAsanaClient()
        # Return expected count on second call
        client.tasks.subtasks_async.side_effect = [
            MockPageIterator([]),
            MockPageIterator([make_mock_subtask("1")]),
        ]

        waiter = SubtaskWaiter(
            client,  # type: ignore[arg-type]
            default_timeout=2.0,
            default_poll_interval=0.01,  # Fast for test
        )

        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=1,
        )

        assert result is True
        assert client.tasks.subtasks_async.call_count == 2

    async def test_expected_count_zero_returns_immediately(self) -> None:
        """wait_for_subtasks_async returns True immediately when expecting 0 subtasks."""
        client = MockAsanaClient()
        client.tasks.subtasks_async.return_value = MockPageIterator([])

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=0,
            timeout=1.0,
        )

        assert result is True
        assert client.tasks.subtasks_async.call_count == 1


class TestSubtaskWaiterIntegration:
    """Integration-style tests for SubtaskWaiter."""

    async def test_realistic_polling_scenario(self) -> None:
        """Test realistic polling scenario with gradual subtask creation."""
        client = MockAsanaClient()
        # Simulate subtasks being created over time
        client.tasks.subtasks_async.side_effect = [
            MockPageIterator([]),  # Poll 1: 0 subtasks
            MockPageIterator([make_mock_subtask("1")]),  # Poll 2: 1 subtask
            MockPageIterator(
                [make_mock_subtask("1"), make_mock_subtask("2")]
            ),  # Poll 3: 2 subtasks
            MockPageIterator(
                [make_mock_subtask("1"), make_mock_subtask("2"), make_mock_subtask("3")]
            ),  # Poll 4: 3 subtasks (expected)
        ]

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=3,
            timeout=2.0,
            poll_interval=0.01,
        )

        assert result is True
        assert client.tasks.subtasks_async.call_count == 4

    async def test_graceful_degradation_on_timeout(self) -> None:
        """Test that timeout does not raise exception (graceful degradation)."""
        client = MockAsanaClient()
        client.tasks.subtasks_async.return_value = MockPageIterator([])

        waiter = SubtaskWaiter(client)  # type: ignore[arg-type]

        # Should not raise, just return False
        result = await waiter.wait_for_subtasks_async(
            "task_123",
            expected_count=10,
            timeout=0.02,
            poll_interval=0.01,
        )

        assert result is False
