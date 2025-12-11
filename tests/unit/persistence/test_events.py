"""Tests for EventSystem.

Per TDD-0010: Verify event hook registration and emission per ADR-0041.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.events import EventSystem
from autom8_asana.persistence.models import OperationType


# ---------------------------------------------------------------------------
# Hook Registration Tests
# ---------------------------------------------------------------------------


class TestHookRegistration:
    """Tests for hook registration operations."""

    def test_register_pre_save_hook(self) -> None:
        """register_pre_save() adds hook to pre_save list."""
        events = EventSystem()
        called = []

        @events.register_pre_save
        def hook(entity: Task, op: OperationType) -> None:
            called.append((entity, op))

        # Hook should be registered
        assert len(events._pre_save_hooks) == 1
        assert events._pre_save_hooks[0] is hook

    def test_register_post_save_hook(self) -> None:
        """register_post_save() adds hook to post_save list."""
        events = EventSystem()
        called = []

        @events.register_post_save
        def hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append((entity, op, data))

        # Hook should be registered
        assert len(events._post_save_hooks) == 1
        assert events._post_save_hooks[0] is hook

    def test_register_error_hook(self) -> None:
        """register_error() adds hook to error list."""
        events = EventSystem()
        called = []

        @events.register_error
        def hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append((entity, op, err))

        # Hook should be registered
        assert len(events._error_hooks) == 1
        assert events._error_hooks[0] is hook

    def test_register_multiple_hooks(self) -> None:
        """Multiple hooks can be registered for same event."""
        events = EventSystem()

        @events.register_pre_save
        def hook1(entity: Task, op: OperationType) -> None:
            pass

        @events.register_pre_save
        def hook2(entity: Task, op: OperationType) -> None:
            pass

        assert len(events._pre_save_hooks) == 2

    def test_clear_hooks(self) -> None:
        """clear_hooks() removes all registered hooks."""
        events = EventSystem()

        @events.register_pre_save
        def hook1(entity: Task, op: OperationType) -> None:
            pass

        @events.register_post_save
        def hook2(entity: Task, op: OperationType, data: dict) -> None:
            pass

        @events.register_error
        def hook3(entity: Task, op: OperationType, err: Exception) -> None:
            pass

        events.clear_hooks()

        assert len(events._pre_save_hooks) == 0
        assert len(events._post_save_hooks) == 0
        assert len(events._error_hooks) == 0


# ---------------------------------------------------------------------------
# Pre-Save Emission Tests
# ---------------------------------------------------------------------------


class TestPreSaveEmission:
    """Tests for pre-save event emission."""

    @pytest.mark.asyncio
    async def test_emit_pre_save_sync_hook(self) -> None:
        """emit_pre_save() calls sync hooks correctly."""
        events = EventSystem()
        called: list[tuple[Task, OperationType]] = []

        @events.register_pre_save
        def hook(entity: Task, op: OperationType) -> None:
            called.append((entity, op))

        task = Task(gid="123", name="Test")
        await events.emit_pre_save(task, OperationType.CREATE)

        assert len(called) == 1
        assert called[0][0] is task
        assert called[0][1] == OperationType.CREATE

    @pytest.mark.asyncio
    async def test_emit_pre_save_async_hook(self) -> None:
        """emit_pre_save() calls async hooks correctly."""
        events = EventSystem()
        called: list[tuple[Task, OperationType]] = []

        @events.register_pre_save
        async def hook(entity: Task, op: OperationType) -> None:
            called.append((entity, op))

        task = Task(gid="123", name="Test")
        await events.emit_pre_save(task, OperationType.UPDATE)

        assert len(called) == 1
        assert called[0][0] is task
        assert called[0][1] == OperationType.UPDATE

    @pytest.mark.asyncio
    async def test_emit_pre_save_mixed_hooks(self) -> None:
        """emit_pre_save() handles mix of sync and async hooks."""
        events = EventSystem()
        called: list[str] = []

        @events.register_pre_save
        def sync_hook(entity: Task, op: OperationType) -> None:
            called.append("sync")

        @events.register_pre_save
        async def async_hook(entity: Task, op: OperationType) -> None:
            called.append("async")

        task = Task(gid="123", name="Test")
        await events.emit_pre_save(task, OperationType.DELETE)

        assert called == ["sync", "async"]

    @pytest.mark.asyncio
    async def test_pre_save_can_abort_by_raising(self) -> None:
        """Pre-save hook can abort save by raising exception."""
        events = EventSystem()

        @events.register_pre_save
        def hook(entity: Task, op: OperationType) -> None:
            raise ValueError("Validation failed")

        task = Task(gid="123", name="Test")

        with pytest.raises(ValueError, match="Validation failed"):
            await events.emit_pre_save(task, OperationType.CREATE)

    @pytest.mark.asyncio
    async def test_pre_save_hooks_called_in_order(self) -> None:
        """Pre-save hooks are called in registration order."""
        events = EventSystem()
        order: list[int] = []

        @events.register_pre_save
        def hook1(entity: Task, op: OperationType) -> None:
            order.append(1)

        @events.register_pre_save
        def hook2(entity: Task, op: OperationType) -> None:
            order.append(2)

        @events.register_pre_save
        def hook3(entity: Task, op: OperationType) -> None:
            order.append(3)

        task = Task(gid="123")
        await events.emit_pre_save(task, OperationType.UPDATE)

        assert order == [1, 2, 3]


# ---------------------------------------------------------------------------
# Post-Save Emission Tests
# ---------------------------------------------------------------------------


class TestPostSaveEmission:
    """Tests for post-save event emission."""

    @pytest.mark.asyncio
    async def test_emit_post_save_sync_hook(self) -> None:
        """emit_post_save() calls sync hooks with data."""
        events = EventSystem()
        called: list[tuple[Task, OperationType, dict]] = []

        @events.register_post_save
        def hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append((entity, op, data))

        task = Task(gid="123", name="Test")
        data = {"gid": "123", "name": "Test"}
        await events.emit_post_save(task, OperationType.CREATE, data)

        assert len(called) == 1
        assert called[0][0] is task
        assert called[0][1] == OperationType.CREATE
        assert called[0][2] == data

    @pytest.mark.asyncio
    async def test_emit_post_save_async_hook(self) -> None:
        """emit_post_save() calls async hooks correctly."""
        events = EventSystem()
        called: list[tuple[Task, OperationType, dict]] = []

        @events.register_post_save
        async def hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append((entity, op, data))

        task = Task(gid="123")
        data = {"gid": "123"}
        await events.emit_post_save(task, OperationType.UPDATE, data)

        assert len(called) == 1
        assert called[0][0] is task

    @pytest.mark.asyncio
    async def test_emit_post_save_swallows_exceptions(self) -> None:
        """emit_post_save() swallows exceptions from hooks."""
        events = EventSystem()
        called: list[str] = []

        @events.register_post_save
        def failing_hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append("before_error")
            raise RuntimeError("Hook failed")

        @events.register_post_save
        def second_hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append("second")

        task = Task(gid="123")

        # Should not raise
        await events.emit_post_save(task, OperationType.CREATE, {})

        # Both hooks should have been called (exception swallowed)
        assert called == ["before_error", "second"]

    @pytest.mark.asyncio
    async def test_emit_post_save_swallows_async_exceptions(self) -> None:
        """emit_post_save() swallows exceptions from async hooks."""
        events = EventSystem()
        called: list[str] = []

        @events.register_post_save
        async def failing_hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append("before_error")
            raise RuntimeError("Async hook failed")

        @events.register_post_save
        async def second_hook(entity: Task, op: OperationType, data: dict) -> None:
            called.append("second")

        task = Task(gid="123")
        await events.emit_post_save(task, OperationType.CREATE, {})

        assert called == ["before_error", "second"]


# ---------------------------------------------------------------------------
# Error Emission Tests
# ---------------------------------------------------------------------------


class TestErrorEmission:
    """Tests for error event emission."""

    @pytest.mark.asyncio
    async def test_emit_error_sync_hook(self) -> None:
        """emit_error() calls sync hooks with exception."""
        events = EventSystem()
        called: list[tuple[Task, OperationType, Exception]] = []

        @events.register_error
        def hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append((entity, op, err))

        task = Task(gid="123")
        error = ValueError("Test error")
        await events.emit_error(task, OperationType.CREATE, error)

        assert len(called) == 1
        assert called[0][0] is task
        assert called[0][1] == OperationType.CREATE
        assert called[0][2] is error

    @pytest.mark.asyncio
    async def test_emit_error_async_hook(self) -> None:
        """emit_error() calls async hooks correctly."""
        events = EventSystem()
        called: list[tuple[Task, OperationType, Exception]] = []

        @events.register_error
        async def hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append((entity, op, err))

        task = Task(gid="123")
        error = ValueError("Test error")
        await events.emit_error(task, OperationType.UPDATE, error)

        assert len(called) == 1
        assert called[0][2] is error

    @pytest.mark.asyncio
    async def test_emit_error_swallows_exceptions(self) -> None:
        """emit_error() swallows exceptions from hooks."""
        events = EventSystem()
        called: list[str] = []

        @events.register_error
        def failing_hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append("before_error")
            raise RuntimeError("Error hook failed")

        @events.register_error
        def second_hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append("second")

        task = Task(gid="123")
        error = ValueError("Original error")

        # Should not raise
        await events.emit_error(task, OperationType.DELETE, error)

        assert called == ["before_error", "second"]

    @pytest.mark.asyncio
    async def test_emit_error_swallows_async_exceptions(self) -> None:
        """emit_error() swallows exceptions from async hooks."""
        events = EventSystem()
        called: list[str] = []

        @events.register_error
        async def failing_hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append("before_error")
            raise RuntimeError("Async error hook failed")

        @events.register_error
        async def second_hook(entity: Task, op: OperationType, err: Exception) -> None:
            called.append("second")

        task = Task(gid="123")
        error = ValueError("Original error")
        await events.emit_error(task, OperationType.DELETE, error)

        assert called == ["before_error", "second"]


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_emit_with_no_hooks(self) -> None:
        """Emission with no hooks does not raise."""
        events = EventSystem()
        task = Task(gid="123")

        # Should not raise
        await events.emit_pre_save(task, OperationType.CREATE)
        await events.emit_post_save(task, OperationType.CREATE, {})
        await events.emit_error(task, OperationType.CREATE, ValueError("test"))

    @pytest.mark.asyncio
    async def test_emit_with_none_data(self) -> None:
        """post_save can receive None data."""
        events = EventSystem()
        received: list[tuple[Task, OperationType, None]] = []

        @events.register_post_save
        def hook(entity: Task, op: OperationType, data: None) -> None:
            received.append((entity, op, data))

        task = Task(gid="123")
        await events.emit_post_save(task, OperationType.DELETE, None)

        assert len(received) == 1
        assert received[0][2] is None
