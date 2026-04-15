"""Tests for observability module.

Per TDD-0007: Tests for correlation ID generation, CorrelationContext,
and @error_handler decorator.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.observability import (
    CorrelationContext,
    error_handler,
    generate_correlation_id,
)


class TestGenerateCorrelationId:
    """Tests for correlation ID generation."""

    def test_format(self) -> None:
        """Correlation ID should match format sdk-{hex8}-{hex4}."""
        cid = generate_correlation_id()
        # Format: sdk-{8 hex chars}-{4 hex chars}
        pattern = r"^sdk-[a-f0-9]{8}-[a-f0-9]{4}$"
        assert re.match(pattern, cid), f"ID '{cid}' does not match expected format"

    def test_length(self) -> None:
        """Correlation ID should be 18 characters."""
        cid = generate_correlation_id()
        # sdk- (4) + 8 hex + - (1) + 4 hex = 17 chars
        assert len(cid) == 17, f"ID length is {len(cid)}, expected 17"

    def test_uniqueness(self) -> None:
        """Correlation IDs should be highly unique.

        With 4 hex random chars (65536 possibilities) and timestamp component,
        we expect very high uniqueness. Allow minor collisions due to
        birthday problem at high volume (~7% collision probability for 100 samples).
        """
        ids = [generate_correlation_id() for _ in range(100)]
        unique_ids = set(ids)
        # Allow up to 2 collisions in 100 samples due to birthday problem
        # with 65536 possibilities and same-millisecond timestamp
        assert len(unique_ids) >= 98, (
            f"Too many collisions: {len(unique_ids)} unique out of {len(ids)}"
        )

    def test_prefix(self) -> None:
        """Correlation ID should start with 'sdk-'."""
        cid = generate_correlation_id()
        assert cid.startswith("sdk-"), f"ID '{cid}' does not start with 'sdk-'"


class TestCorrelationContext:
    """Tests for CorrelationContext dataclass."""

    def test_generate_creates_context(self) -> None:
        """CorrelationContext.generate creates valid context."""
        ctx = CorrelationContext.generate("TasksClient.get_async")
        assert ctx.correlation_id.startswith("sdk-")
        assert ctx.operation == "TasksClient.get_async"
        assert ctx.started_at > 0
        assert ctx.resource_gid is None
        assert ctx.asana_request_id is None

    def test_generate_with_resource_gid(self) -> None:
        """CorrelationContext.generate includes resource GID."""
        ctx = CorrelationContext.generate("TasksClient.get_async", resource_gid="123")
        assert ctx.resource_gid == "123"

    def test_with_asana_request_id(self) -> None:
        """with_asana_request_id returns new context with request ID."""
        ctx = CorrelationContext.generate("TasksClient.get_async")
        new_ctx = ctx.with_asana_request_id("req-abc-123")

        # Original unchanged
        assert ctx.asana_request_id is None

        # New context has request ID
        assert new_ctx.asana_request_id == "req-abc-123"
        assert new_ctx.correlation_id == ctx.correlation_id
        assert new_ctx.operation == ctx.operation

    def test_format_log_prefix(self) -> None:
        """format_log_prefix returns bracketed correlation ID."""
        ctx = CorrelationContext(
            correlation_id="sdk-12345678-abcd",
            operation="TasksClient.get_async",
            started_at=time.monotonic(),
        )
        assert ctx.format_log_prefix() == "[sdk-12345678-abcd]"

    def test_format_operation_without_gid(self) -> None:
        """format_operation returns operation with empty parens when no GID."""
        ctx = CorrelationContext(
            correlation_id="sdk-12345678-abcd",
            operation="TasksClient.get_async",
            started_at=time.monotonic(),
        )
        assert ctx.format_operation() == "TasksClient.get_async()"

    def test_format_operation_with_gid(self) -> None:
        """format_operation includes GID in parens."""
        ctx = CorrelationContext(
            correlation_id="sdk-12345678-abcd",
            operation="TasksClient.get_async",
            started_at=time.monotonic(),
            resource_gid="task123",
        )
        assert ctx.format_operation() == "TasksClient.get_async(task123)"

    def test_immutability(self) -> None:
        """CorrelationContext should be immutable."""
        ctx = CorrelationContext(
            correlation_id="sdk-12345678-abcd",
            operation="TasksClient.get_async",
            started_at=time.monotonic(),
        )
        with pytest.raises(AttributeError):
            ctx.correlation_id = "new-id"  # type: ignore[misc]


class TestErrorHandler:
    """Tests for @error_handler decorator."""

    @pytest.fixture
    def mock_log_provider(self) -> MagicMock:
        """Create a mock log provider."""
        return MagicMock()

    async def test_decorator_logs_start_and_completion(self, mock_log_provider: MagicMock) -> None:
        """Decorator should log operation start and completion."""

        class TestClient:
            _log = mock_log_provider

            @error_handler
            async def get_async(self, task_gid: str) -> dict[str, Any]:
                return {"gid": task_gid}

        client = TestClient()
        result = await client.get_async("123")

        assert result == {"gid": "123"}

        # Check debug logs were called
        assert mock_log_provider.debug.call_count == 2

        # Check start message
        start_call = mock_log_provider.debug.call_args_list[0]
        start_msg = start_call[0][0]
        assert "starting" in start_msg
        assert "TestClient.get_async" in start_msg
        assert "123" in start_msg

        # Check completion message
        complete_call = mock_log_provider.debug.call_args_list[1]
        complete_msg = complete_call[0][0]
        assert "completed" in complete_msg
        assert "ms" in complete_msg

    async def test_decorator_logs_error_on_exception(self, mock_log_provider: MagicMock) -> None:
        """Decorator should log error when exception occurs."""

        class TestClient:
            _log = mock_log_provider

            @error_handler
            async def get_async(self, task_gid: str) -> dict[str, Any]:
                raise ValueError("Task not found")

        client = TestClient()

        with pytest.raises(ValueError, match="Task not found"):
            await client.get_async("123")

        # Should have logged start and error
        assert mock_log_provider.debug.call_count == 1  # start only
        assert mock_log_provider.error.call_count == 1

        # Check error message
        error_call = mock_log_provider.error.call_args_list[0]
        error_msg = error_call[0][0]
        assert "failed" in error_msg
        assert "Task not found" in error_msg

    async def test_decorator_enriches_exception(self, mock_log_provider: MagicMock) -> None:
        """Decorator should add correlation_id and operation to exceptions."""

        class TestClient:
            _log = mock_log_provider

            @error_handler
            async def get_async(self, task_gid: str) -> dict[str, Any]:
                raise ValueError("Task not found")

        client = TestClient()

        with pytest.raises(ValueError) as exc_info:
            await client.get_async("123")

        exc = exc_info.value

        # Exception should have correlation context
        assert hasattr(exc, "correlation_id")
        assert hasattr(exc, "operation")
        assert exc.correlation_id.startswith("sdk-")  # type: ignore[attr-defined]
        assert exc.operation == "TestClient.get_async"  # type: ignore[attr-defined]

    async def test_decorator_without_log_provider(self) -> None:
        """Decorator should work when _log is None."""

        class TestClient:
            _log = None

            @error_handler
            async def get_async(self, task_gid: str) -> dict[str, Any]:
                return {"gid": task_gid}

        client = TestClient()
        result = await client.get_async("123")

        assert result == {"gid": "123"}

    def test_decorator_preserves_function_metadata(self) -> None:
        """Decorator should preserve function name and docstring."""

        class TestClient:
            _log = None

            @error_handler
            async def get_async(self, task_gid: str) -> dict[str, Any]:
                """Get a task by GID."""
                return {"gid": task_gid}

        client = TestClient()

        # functools.wraps should preserve these
        assert client.get_async.__name__ == "get_async"
        assert client.get_async.__doc__ == "Get a task by GID."

    async def test_decorator_measures_timing(self, mock_log_provider: MagicMock) -> None:
        """Decorator should measure elapsed time."""

        class TestClient:
            _log = mock_log_provider

            @error_handler
            async def slow_method(self) -> str:
                await asyncio.sleep(0.1)  # 100ms
                return "done"

        client = TestClient()
        await client.slow_method()

        # Check that completion message includes timing
        complete_call = mock_log_provider.debug.call_args_list[1]
        complete_msg = complete_call[0][0]

        # Extract timing from message (e.g., "completed in 105ms")
        import re

        match = re.search(r"(\d+)ms", complete_msg)
        assert match is not None, "Timing not found in completion message"

        elapsed_ms = int(match.group(1))
        assert elapsed_ms >= 100, f"Elapsed time {elapsed_ms}ms should be >= 100ms"

    async def test_correlation_id_uniqueness_across_calls(
        self, mock_log_provider: MagicMock
    ) -> None:
        """Each call should generate a unique correlation ID."""

        class TestClient:
            _log = mock_log_provider

            @error_handler
            async def get_async(self, task_gid: str) -> dict[str, Any]:
                return {"gid": task_gid}

        client = TestClient()

        # Make multiple calls
        for _ in range(3):
            await client.get_async("123")

        # Extract correlation IDs from log messages
        ids = []
        for call in mock_log_provider.debug.call_args_list:
            msg = call[0][0]
            match = re.search(r"\[(sdk-[a-f0-9-]+)\]", msg)
            if match:
                ids.append(match.group(1))

        # Should have 6 messages (2 per call: start + complete)
        assert len(ids) == 6

        # Each pair should have same ID, but pairs should be different
        unique_ids = set(ids)
        assert len(unique_ids) == 3, "Expected 3 unique correlation IDs for 3 calls"


class TestCorrelationIdFormat:
    """Tests verifying correlation ID format per ADR-0013."""

    def test_timestamp_component_is_current(self) -> None:
        """Timestamp component should be based on current time."""
        before = int(time.time() * 1000) & 0xFFFFFFFF
        cid = generate_correlation_id()
        after = int(time.time() * 1000) & 0xFFFFFFFF

        # Extract timestamp from ID
        # Format: sdk-{timestamp hex}-{random hex}
        parts = cid.split("-")
        timestamp_hex = parts[1]
        timestamp = int(timestamp_hex, 16)

        # Timestamp should be within range
        assert before <= timestamp <= after, (
            f"Timestamp {timestamp} not in range [{before}, {after}]"
        )

    def test_random_component_varies(self) -> None:
        """Random component should vary between calls."""
        ids = [generate_correlation_id() for _ in range(100)]

        # Extract random parts
        random_parts = [cid.split("-")[2] for cid in ids]
        unique_random = set(random_parts)

        # Should have high uniqueness (allowing some collision in 100 samples)
        assert len(unique_random) >= 90, (
            f"Only {len(unique_random)} unique random components in 100 IDs"
        )
