"""Tests for sync_wrapper decorator and fail-fast behavior."""

import asyncio

import pytest

from autom8_asana.errors import SyncInAsyncContextError
from autom8_asana.transport.sync import sync_wrapper


class TestSyncWrapper:
    """Tests for sync wrapper decorator."""

    def test_sync_call_works(self) -> None:
        """Test that sync wrapper works in sync context."""

        @sync_wrapper("test_async")
        async def wrapped_func(value: int) -> int:
            return value * 2

        result = wrapped_func(21)
        assert result == 42

    def test_sync_call_with_args_and_kwargs(self) -> None:
        """Test that args and kwargs are passed through."""

        @sync_wrapper("test_async")
        async def wrapped_func(a: int, b: int, *, multiplier: int = 1) -> int:
            return (a + b) * multiplier

        result = wrapped_func(2, 3, multiplier=4)
        assert result == 20

    @pytest.mark.asyncio
    async def test_fails_in_async_context(self) -> None:
        """Test that sync wrapper fails fast in async context."""

        @sync_wrapper("test_async")
        async def wrapped_func() -> int:
            return 42

        with pytest.raises(SyncInAsyncContextError) as exc_info:
            wrapped_func()

        assert "async context" in str(exc_info.value)
        assert "test_async" in str(exc_info.value)

    def test_preserves_function_metadata(self) -> None:
        """Test that functools.wraps preserves function metadata."""

        @sync_wrapper("original_async")
        async def my_function() -> int:
            """My docstring."""
            return 42

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_handles_exceptions(self) -> None:
        """Test that exceptions from wrapped function propagate."""

        @sync_wrapper("test_async")
        async def wrapped_func() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            wrapped_func()

    @pytest.mark.asyncio
    async def test_error_message_strips_underscore(self) -> None:
        """Test that leading underscores are stripped from method name."""

        @sync_wrapper("get_async")
        async def _get_sync() -> int:
            return 42

        with pytest.raises(SyncInAsyncContextError) as exc_info:
            _get_sync()

        # Should show "get_sync" not "_get_sync"
        error_message = str(exc_info.value)
        assert "get_sync" in error_message
        assert "'_get_sync'" not in error_message


class TestSyncWrapperIntegration:
    """Integration tests for sync wrapper with realistic patterns."""

    def test_class_method_pattern(self) -> None:
        """Test the class method pattern used in clients."""

        class MockClient:
            async def get_async(self, task_id: str) -> dict:
                return {"gid": task_id, "name": "Test Task"}

            @sync_wrapper("get_async")
            async def _get_sync(self, task_id: str) -> dict:
                return await self.get_async(task_id)

            def get(self, task_id: str) -> dict:
                return self._get_sync(task_id)

        client = MockClient()
        result = client.get("12345")

        assert result == {"gid": "12345", "name": "Test Task"}

    def test_async_operations_in_wrapped_function(self) -> None:
        """Test that async operations inside work correctly."""

        async def slow_operation() -> str:
            await asyncio.sleep(0.01)
            return "done"

        @sync_wrapper("test_async")
        async def wrapped_func() -> str:
            result = await slow_operation()
            return result

        result = wrapped_func()
        assert result == "done"

    def test_multiple_wrapped_calls(self) -> None:
        """Test that multiple sync calls work correctly."""

        counter = 0

        @sync_wrapper("test_async")
        async def wrapped_func() -> int:
            nonlocal counter
            counter += 1
            return counter

        # Each call should create a new event loop
        assert wrapped_func() == 1
        assert wrapped_func() == 2
        assert wrapped_func() == 3
