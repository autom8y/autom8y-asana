"""Tests for boundary conditions and edge cases.

Per GA Readiness Phase 2: Verify fail-fast validation and actionable error messages.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.exceptions import ValidationError
from autom8_asana.persistence.session import SaveSession
from autom8_asana.persistence.tracker import ChangeTracker


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def create_mock_client() -> MagicMock:
    """Create a mock AsanaClient with mock batch client and http client."""
    mock_client = MagicMock()
    mock_batch = MagicMock()
    mock_batch.execute_async = AsyncMock(return_value=[])
    mock_client.batch = mock_batch
    mock_client._log = None

    mock_http = AsyncMock()
    mock_http.request = AsyncMock(return_value={"data": {}})
    mock_client._http = mock_http

    return mock_client


def create_mock_client_with_logger() -> MagicMock:
    """Create a mock AsanaClient with a mock logger."""
    mock_client = create_mock_client()
    mock_log = MagicMock()
    mock_client._log = mock_log
    return mock_client




# ---------------------------------------------------------------------------
# Input Boundary Tests
# ---------------------------------------------------------------------------


class TestInputBoundaries:
    """Tests for input value boundaries."""

    def test_empty_task_name_can_be_tracked(self) -> None:
        """Empty task name is allowed (API may reject, but tracking works)."""
        tracker = ChangeTracker()
        task = Task(gid="123456", name="")

        # Should not raise at track time
        tracker.track(task)

        state = tracker.get_state(task)
        assert state is not None

    def test_none_in_optional_field_is_valid(self) -> None:
        """None in optional fields is valid."""
        tracker = ChangeTracker()
        task = Task(gid="123456", name="Test", notes=None, due_on=None)

        # Should not raise
        tracker.track(task)

        changes = tracker.get_changes(task)
        assert changes == {}

    def test_very_long_name_can_be_tracked(self) -> None:
        """Very long name can be tracked (API may have limits)."""
        tracker = ChangeTracker()
        long_name = "A" * 10000
        task = Task(gid="123456", name=long_name)

        # Should not raise at track time
        tracker.track(task)

        state = tracker.get_state(task)
        assert state is not None

    def test_unicode_characters_handled(self) -> None:
        """Unicode characters in names are handled correctly."""
        tracker = ChangeTracker()
        task = Task(gid="123456", name="Test Task")

        tracker.track(task)
        task.name = "Update"

        changes = tracker.get_changes(task)
        assert "name" in changes
        assert changes["name"] == ("Test Task", "Update")

    def test_emoji_handled(self) -> None:
        """Emoji characters in fields are handled correctly."""
        tracker = ChangeTracker()
        task = Task(gid="123456", name="Task with emoji")

        tracker.track(task)
        task.name = "Updated task"

        changes = tracker.get_changes(task)
        assert "name" in changes


# ---------------------------------------------------------------------------
# Empty Session Tests
# ---------------------------------------------------------------------------


class TestEmptySession:
    """Tests for empty session handling."""

    @pytest.mark.asyncio
    async def test_empty_session_commit_logs_warning(self) -> None:
        """Committing empty session logs a warning."""
        mock_client = create_mock_client_with_logger()

        async with SaveSession(mock_client) as session:
            # Don't track anything
            result = await session.commit_async()

        # Should return empty result
        assert result.success is True
        assert result.total_count == 0

        # Should log warning
        mock_client._log.warning.assert_called_once()
        call_args = mock_client._log.warning.call_args
        assert "commit_empty_session" in call_args[0]
        assert "track()" in str(call_args)

    @pytest.mark.asyncio
    async def test_empty_session_returns_empty_result(self) -> None:
        """Committing empty session returns SaveResult with no operations."""
        mock_client = create_mock_client()

        async with SaveSession(mock_client) as session:
            result = await session.commit_async()

        assert result.succeeded == []
        assert result.failed == []
        assert result.total_count == 0


# ---------------------------------------------------------------------------
# Large Batch Tests
# ---------------------------------------------------------------------------


class TestLargeBatch:
    """Tests for large batch handling."""

    def test_large_batch_can_be_tracked(self) -> None:
        """1000 entities can be tracked without error."""
        tracker = ChangeTracker()

        tasks = [Task(gid=str(i), name=f"Task {i}") for i in range(1000, 2000)]

        for task in tasks:
            tracker.track(task)

        # All should be tracked
        dirty = tracker.get_dirty_entities()
        # All are CLEAN since they have real GIDs and no modifications
        assert len(dirty) == 0

        # Modify all tasks
        for task in tasks:
            task.name = f"Modified {task.name}"

        dirty = tracker.get_dirty_entities()
        assert len(dirty) == 1000

    def test_session_tracks_many_entities(self) -> None:
        """Session can track many entities."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            for i in range(1000, 2000):
                task = Task(gid=str(i), name=f"Task {i}")
                session.track(task)

            # All tasks tracked successfully
            # (we can't easily inspect internal state, but no exception means success)


# ---------------------------------------------------------------------------
# Session Validation Integration Tests
# ---------------------------------------------------------------------------


class TestSessionValidation:
    """Tests for validation through SaveSession."""

    def test_session_track_accepts_valid_gid(self) -> None:
        """Session.track() accepts valid GID."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            task = Task(gid="123456789", name="Test")

            # Should not raise
            result = session.track(task)
            assert result is task

    def test_session_track_accepts_temp_gid(self) -> None:
        """Session.track() accepts temp_* GID for new entities."""
        mock_client = create_mock_client()

        with SaveSession(mock_client) as session:
            task = Task(gid="temp_1", name="New Task")

            # Should not raise
            result = session.track(task)
            assert result is task
