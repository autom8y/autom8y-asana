"""Unit tests for @async_method decorator.

Per TDD-DESIGN-PATTERNS-D: Comprehensive tests for async/sync method generation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from autom8_asana.exceptions import SyncInAsyncContextError
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

    def test_async_behavior_correct(self) -> None:
        """Verify async method executes as coroutine."""

        class TestClient:
            @async_method
            async def fetch(self, gid: str) -> str:
                """Fetch a resource."""
                return f"fetched:{gid}"

        client = TestClient()

        # Call async method
        result = asyncio.run(client.fetch_async("123"))
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

    def test_with_kwargs(self) -> None:
        """Verify kwargs are passed correctly."""

        class TestClient:
            @async_method
            async def update(
                self, gid: str, *, name: str | None = None
            ) -> dict[str, Any]:
                """Update a resource."""
                return {"gid": gid, "name": name}

        client = TestClient()

        # Async with kwargs
        result = asyncio.run(client.update_async("123", name="Test"))
        assert result == {"gid": "123", "name": "Test"}

        # Sync with kwargs
        result = client.update("456", name="Updated")
        assert result == {"gid": "456", "name": "Updated"}

    def test_with_multiple_args(self) -> None:
        """Verify multiple positional args work correctly."""

        class TestClient:
            @async_method
            async def move(
                self, task_gid: str, section_gid: str, project_gid: str
            ) -> str:
                """Move task to section."""
                return f"{task_gid}:{section_gid}:{project_gid}"

        client = TestClient()

        result = asyncio.run(client.move_async("t1", "s1", "p1"))
        assert result == "t1:s1:p1"

        result = client.move("t2", "s2", "p2")
        assert result == "t2:s2:p2"

    def test_void_return(self) -> None:
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
        asyncio.run(client.delete_async("123"))
        assert "123" in client.deleted

        # Sync delete
        client.delete("456")
        assert "456" in client.deleted

    def test_exception_propagation(self) -> None:
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
            asyncio.run(client.failing_async("123"))

        # Sync exception
        with pytest.raises(CustomError, match="Failed for 456"):
            client.failing("456")

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

    def test_stacked_with_mock_error_handler(self) -> None:
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
        result = asyncio.run(client.fetch_async("123"))
        assert result == "result:123"
        assert "before:fetch" in call_log
        assert "after:fetch" in call_log

        call_log.clear()

        # Sync call
        result = client.fetch("456")
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

    def test_client_pattern_simulation(self) -> None:
        """Simulate the actual SDK client pattern."""

        class MockHTTP:
            async def get(
                self, path: str, params: dict[str, Any] | None = None
            ) -> dict[str, Any]:
                return {"gid": "123", "name": "Test Section", "path": path}

            async def delete(self, path: str) -> None:
                pass

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
        result = asyncio.run(client.get_async("sec1"))
        assert result["model"] is True
        assert result["gid"] == "123"

        # Test get (sync)
        result = client.get("sec2")
        assert result["model"] is True

        # Test get with raw=True
        result = asyncio.run(client.get_async("sec3", raw=True))
        assert "model" not in result
        assert result["gid"] == "123"

        # Test delete_async
        asyncio.run(client.delete_async("sec4"))

        # Test delete (sync)
        client.delete("sec5")

    def test_inheritance_works(self) -> None:
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

        # Base method
        assert asyncio.run(client.base_method_async("1")) == "base:1"
        assert client.base_method("2") == "base:2"

        # Derived method
        assert asyncio.run(client.derived_method_async("3")) == "derived:3"
        assert client.derived_method("4") == "derived:4"

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
