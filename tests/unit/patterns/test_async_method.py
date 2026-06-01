"""Unit tests for @async_method decorator.

Per TDD-DESIGN-PATTERNS-D: Comprehensive tests for async/sync method generation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from autom8_asana.errors import SyncInAsyncContextError
from autom8_asana.patterns.async_method import AsyncMethodPair, async_method


class TestAsyncMethodDecorator:
    """Tests for the @async_method decorator."""

    def test_creates_async_variant(self) -> None:
        """Verify method_async is created on the class."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource."""
                return f"fetched:{gid}"

        # Verify async method exists
        assert hasattr(TestClient, "fetch_async")
        assert asyncio.iscoroutinefunction(TestClient.fetch_async)

    def test_creates_sync_variant(self) -> None:
        """Verify method (sync) is created on the class."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource."""
                return f"fetched:{gid}"

        # Verify sync method exists
        assert hasattr(TestClient, "fetch")
        assert not asyncio.iscoroutinefunction(TestClient.fetch)

    async def test_async_behavior_correct(self) -> None:
        """Verify async method executes as coroutine."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource."""
                return f"fetched:{gid}"

        client = TestClient()

        # Call async method
        result = await client.fetch_async("123")
        assert result == "fetched:123"

    def test_sync_behavior_correct(self) -> None:
        """Verify sync method blocks and returns result."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource."""
                return f"fetched:{gid}"

        client = TestClient()

        # Call sync method (not in async context)
        result = client.fetch("456")
        assert result == "fetched:456"

    def test_sync_in_async_context_raises(self) -> None:
        """Verify SyncInAsyncContextError raised when sync called from async."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource."""
                return f"fetched:{gid}"

        client = TestClient()

        async def async_caller() -> None:
            # Calling sync method from async context should raise
            client.fetch("789")

        # class-(c) RETAINED: asyncio.run establishes a running event loop so the
        # sync .fetch() call inside async_caller detects it and raises
        # SyncInAsyncContextError. Converting this test to `async def` + `await`
        # would dismantle the very loop-context the guard is asserted against.
        with pytest.raises(SyncInAsyncContextError) as exc_info:
            asyncio.run(async_caller())

        assert "fetch" in str(exc_info.value)
        assert "fetch_async" in str(exc_info.value)

    def test_preserves_docstring_async(self) -> None:
        """Verify docstring propagated to async variant."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource by GID.

                Args:
                    gid: The resource GID.

                Returns:
                    The resource data.
                """
                return f"fetched:{gid}"

        assert TestClient.fetch_async.__doc__ is not None
        assert "Fetch a resource by GID" in TestClient.fetch_async.__doc__

    def test_preserves_docstring_sync(self) -> None:
        """Verify docstring propagated to sync variant with note."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource by GID."""
                return f"fetched:{gid}"

        assert TestClient.fetch.__doc__ is not None
        assert "Fetch a resource by GID" in TestClient.fetch.__doc__
        assert "fetch_async" in TestClient.fetch.__doc__  # Reference to async

    async def test_with_kwargs(self) -> None:
        """Verify kwargs are passed correctly."""

        class TestClient:
            @async_method
            async def update(self, gid: str, *, name: str | None = None) -> dict[str, Any]:
                """Update a resource."""
                return {"gid": gid, "name": name}

        client = TestClient()

        # Async with kwargs
        result = await client.update_async("123", name="Test")
        assert result == {"gid": "123", "name": "Test"}

        # Sync with kwargs — run off-loop via to_thread; the sync wrapper raises
        # SyncInAsyncContextError if a running loop is detected (ADR-0002), so the
        # sync path must be exercised in a worker thread with no running loop.
        result = await asyncio.to_thread(client.update, "456", name="Updated")
        assert result == {"gid": "456", "name": "Updated"}

    async def test_with_multiple_args(self) -> None:
        """Verify multiple positional args work correctly."""

        class TestClient:
            @async_method
            async def move(self, task_gid: str, section_gid: str, project_gid: str) -> str:
                """Move task to section."""
                return f"{task_gid}:{section_gid}:{project_gid}"

        client = TestClient()

        result = await client.move_async("t1", "s1", "p1")
        assert result == "t1:s1:p1"

        # Sync path off-loop (ADR-0002 guard raises in a running loop).
        result = await asyncio.to_thread(client.move, "t2", "s2", "p2")
        assert result == "t2:s2:p2"

    async def test_void_return(self) -> None:
        """Verify methods with None return work correctly."""

        class TestClient:
            def __init__(self) -> None:
                self.deleted: list[str] = []

            @async_method
            async def delete(self, gid: str) -> None:
                """Delete a resource."""
                self.deleted.append(gid)

        client = TestClient()

        # Async delete
        await client.delete_async("123")
        assert "123" in client.deleted

        # Sync delete off-loop (ADR-0002 guard raises in a running loop).
        await asyncio.to_thread(client.delete, "456")
        assert "456" in client.deleted

    async def test_exception_propagation(self) -> None:
        """Verify exceptions are propagated correctly."""

        class CustomError(Exception):
            pass

        class TestClient:
            @async_method
            async def failing(self, gid: str) -> str:
                """A method that fails."""
                raise CustomError(f"Failed for {gid}")

        client = TestClient()

        # Async exception
        with pytest.raises(CustomError, match="Failed for 123"):
            await client.failing_async("123")

        # Sync exception off-loop (ADR-0002 guard raises in a running loop).
        with pytest.raises(CustomError, match="Failed for 456"):
            await asyncio.to_thread(client.failing, "456")

    def test_method_name_preserved(self) -> None:
        """Verify method names are correct."""

        class TestClient:
            @async_method
            async def get(self, gid: str) -> str:
                """Get a resource."""
                return gid

        assert TestClient.get.__name__ == "get"
        assert TestClient.get_async.__name__ == "get"  # Original function name

    def test_descriptor_class_access(self) -> None:
        """Verify descriptor returns self when accessed on class."""
        # Note: Due to __set_name__ processing, the descriptor is replaced
        # by the actual methods. This test verifies methods exist at class level.

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch resource."""
                return gid

        # Methods should be callable at class level (unbound)
        assert callable(TestClient.fetch)
        assert callable(TestClient.fetch_async)


class TestAsyncMethodWithDecorators:
    """Tests for @async_method stacked with other decorators."""

    async def test_stacked_with_mock_error_handler(self) -> None:
        """Verify @async_method works with @error_handler-like decorator."""

        call_log: list[str] = []

        def error_handler(fn):  # type: ignore
            """Mock error handler decorator."""

            async def wrapper(*args, **kwargs):  # type: ignore
                call_log.append(f"before:{fn.__name__}")
                try:
                    result = await fn(*args, **kwargs)
                    call_log.append(f"after:{fn.__name__}")
                    return result
                except Exception as e:
                    call_log.append(f"error:{fn.__name__}:{e}")
                    raise

            wrapper.__name__ = fn.__name__
            wrapper.__doc__ = fn.__doc__
            return wrapper

        class TestClient:
            @async_method
            @error_handler
            async def fetch(self, gid: str) -> str:
                """Fetch resource."""
                return f"result:{gid}"

        client = TestClient()

        # Async call
        result = await client.fetch_async("123")
        assert result == "result:123"
        assert "before:fetch" in call_log
        assert "after:fetch" in call_log

        call_log.clear()

        # Sync call off-loop (ADR-0002 guard raises in a running loop).
        result = await asyncio.to_thread(client.fetch, "456")
        assert result == "result:456"
        assert "before:fetch" in call_log
        assert "after:fetch" in call_log


class TestAsyncMethodPairClass:
    """Tests for AsyncMethodPair internals."""

    def test_doc_preserved(self) -> None:
        """Verify __doc__ is preserved on descriptor."""

        async def my_func(self: Any, gid: str) -> str:
            """My function docstring."""
            return gid

        pair = AsyncMethodPair(my_func)
        assert pair.__doc__ == "My function docstring."

    def test_name_from_function(self) -> None:
        """Verify _name is taken from function."""

        async def my_fetch(self: Any, gid: str) -> str:
            """Fetch."""
            return gid

        pair = AsyncMethodPair(my_fetch)
        assert pair._name == "my_fetch"


class TestAsyncMethodIntegration:
    """Integration tests simulating real SDK usage patterns."""

    async def test_client_pattern_simulation(self) -> None:
        """Simulate the actual SDK client pattern."""

        class MockHTTP:
            def __init__(self) -> None:
                self.deleted_paths: list[str] = []

            async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
                return {"gid": "123", "name": "Test Section", "path": path}

            async def delete(self, path: str) -> None:
                self.deleted_paths.append(path)

        class BaseClient:
            def __init__(self, http: MockHTTP) -> None:
                self._http = http

        class SectionsClient(BaseClient):
            @async_method
            async def get(self, section_gid: str, *, raw: bool = False) -> Any:
                """Get a section by GID."""
                data = await self._http.get(f"/sections/{section_gid}")
                if raw:
                    return data
                # Simulate model validation
                return {"model": True, **data}

            @async_method
            async def delete(self, section_gid: str) -> None:
                """Delete a section."""
                await self._http.delete(f"/sections/{section_gid}")

        http = MockHTTP()
        client = SectionsClient(http)

        # Test get_async
        result = await client.get_async("sec1")
        assert result["model"] is True
        assert result["gid"] == "123"

        # Test get (sync) off-loop (ADR-0002 guard raises in a running loop).
        result = await asyncio.to_thread(client.get, "sec2")
        assert result["model"] is True

        # Test get with raw=True
        result = await client.get_async("sec3", raw=True)
        assert "model" not in result
        assert result["gid"] == "123"

        # Test delete_async
        # Positive observable assertion: the void delete_async must actually
        # propagate to the underlying HTTP delete. Without this assert the
        # awaited coroutine would be a vacuous no-op under asyncio_mode=auto.
        await client.delete_async("sec4")
        assert "/sections/sec4" in http.deleted_paths

        # Test delete (sync) off-loop (ADR-0002 guard raises in a running loop).
        await asyncio.to_thread(client.delete, "sec5")
        assert "/sections/sec5" in http.deleted_paths

    async def test_inheritance_works(self) -> None:
        """Verify @async_method works with inheritance."""

        class BaseClient:
            @async_method
            async def base_method(self, gid: str) -> str:
                """Base method."""
                return f"base:{gid}"

        class DerivedClient(BaseClient):
            @async_method
            async def derived_method(self, gid: str) -> str:
                """Derived method."""
                return f"derived:{gid}"

        client = DerivedClient()

        # Base method (sync path off-loop per ADR-0002 guard).
        assert await client.base_method_async("1") == "base:1"
        assert await asyncio.to_thread(client.base_method, "2") == "base:2"

        # Derived method (sync path off-loop per ADR-0002 guard).
        assert await client.derived_method_async("3") == "derived:3"
        assert await asyncio.to_thread(client.derived_method, "4") == "derived:4"

    def test_method_override_in_subclass(self) -> None:
        """Verify method can be overridden in subclass."""

        class BaseClient:
            @async_method
            async def get(self, gid: str) -> str:
                """Base get."""
                return f"base:{gid}"

        class DerivedClient(BaseClient):
            @async_method
            async def get(self, gid: str) -> str:
                """Overridden get."""
                return f"derived:{gid}"

        base = BaseClient()
        derived = DerivedClient()

        assert base.get("1") == "base:1"
        assert derived.get("1") == "derived:1"
