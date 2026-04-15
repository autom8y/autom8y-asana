"""Unit tests for DefaultEndpointPolicy.

Per WS-DSC TDD Section 9.1: Tests for the execution policy abstraction
in isolation with mock plug points.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.clients.data._policy import (
    DefaultEndpointPolicy,
    EndpointPolicy,
)

# ---------------------------------------------------------------------------
# Test fixtures: minimal descriptor and helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StubRetryCallbacks:
    on_retry: Any = None
    on_timeout_exhausted: Any = None
    on_http_error: Any = None


@dataclass(frozen=True)
class _StubDescriptor:
    """Minimal descriptor for policy tests."""

    request_id: str = "test-req-1"
    retry_callbacks: _StubRetryCallbacks | None = None


def _make_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def _make_policy(
    *,
    cb_check_side_effect: Exception | None = None,
    execute_response_status: int = 200,
    execute_side_effect: Exception | None = None,
    cb_error_factory: Any = None,
    error_handler: Any = None,
    success_handler: Any = None,
    pre_execute_error_handler: Any = None,
) -> tuple[DefaultEndpointPolicy, dict[str, Any]]:
    """Build a DefaultEndpointPolicy with configurable mocks.

    Returns (policy, mocks_dict) where mocks_dict contains named references
    to the injected mocks for assertion.
    """
    cb = AsyncMock()
    if cb_check_side_effect:
        cb.check.side_effect = cb_check_side_effect
    else:
        cb.check.return_value = None
    cb.record_success.return_value = None

    get_client = AsyncMock(return_value=MagicMock(name="http_client"))

    response = _make_response(execute_response_status)
    execute_with_retry = AsyncMock()
    if execute_side_effect:
        execute_with_retry.side_effect = execute_side_effect
    else:
        execute_with_retry.return_value = (response, 0)

    if cb_error_factory is None:

        def _default_cb_error_factory(e: Exception, req: Any) -> Any:
            raise RuntimeError(f"CB open: {e}") from e

        cb_error_factory = _default_cb_error_factory

    request_builder = MagicMock(return_value=MagicMock(name="make_request_callable"))

    if error_handler is None:
        error_handler = AsyncMock(return_value={"error": True})
    if success_handler is None:
        success_handler = AsyncMock(return_value={"data": "ok"})

    policy = DefaultEndpointPolicy(
        circuit_breaker=cb,
        get_client=get_client,
        execute_with_retry=execute_with_retry,
        cb_error_factory=cb_error_factory,
        request_builder=request_builder,
        error_handler=error_handler,
        success_handler=success_handler,
        pre_execute_error_handler=pre_execute_error_handler,
    )

    mocks = {
        "circuit_breaker": cb,
        "get_client": get_client,
        "execute_with_retry": execute_with_retry,
        "request_builder": request_builder,
        "error_handler": error_handler,
        "success_handler": success_handler,
        "response": response,
    }
    return policy, mocks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEndpointPolicyProtocol:
    """Verify the protocol is runtime-checkable."""

    def test_default_policy_satisfies_protocol(self) -> None:
        policy, _ = _make_policy()
        assert isinstance(policy, EndpointPolicy)


class TestExecuteHappyPath:
    """test_execute_happy_path: CB passes, 200 response, success_handler called."""

    async def test_happy_path(self) -> None:
        policy, mocks = _make_policy(execute_response_status=200)
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        result = await policy.execute(desc)

        # Circuit breaker checked and success recorded (via success_handler)
        mocks["circuit_breaker"].check.assert_awaited_once()
        # HTTP client acquired
        mocks["get_client"].assert_awaited_once()
        # execute_with_retry called
        mocks["execute_with_retry"].assert_awaited_once()
        # success_handler called with response, descriptor, elapsed_ms
        mocks["success_handler"].assert_awaited_once()
        call_args = mocks["success_handler"].call_args
        assert call_args[0][0] is mocks["response"]
        assert call_args[0][1] is desc
        assert isinstance(call_args[0][2], float)  # elapsed_ms
        # error_handler NOT called
        mocks["error_handler"].assert_not_awaited()
        assert result == {"data": "ok"}


class TestCircuitBreakerOpenRaises:
    """test_execute_circuit_breaker_open_raises: CB raises, factory raises."""

    async def test_cb_open_raises(self) -> None:
        from autom8y_http import CircuitBreakerOpenError

        cb_error = CircuitBreakerOpenError(30.0, "Circuit breaker is open")

        def raising_factory(e: Exception, req: Any) -> Any:
            raise RuntimeError("CB is open") from e

        policy, mocks = _make_policy(
            cb_check_side_effect=cb_error,
            cb_error_factory=raising_factory,
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        with pytest.raises(RuntimeError, match="CB is open"):
            await policy.execute(desc)

        # Should NOT proceed to get_client or execute
        mocks["get_client"].assert_not_awaited()
        mocks["execute_with_retry"].assert_not_awaited()


class TestCircuitBreakerOpenReturns:
    """test_execute_circuit_breaker_open_returns: batch case, returns result."""

    async def test_cb_open_returns_result(self) -> None:
        from autom8y_http import CircuitBreakerOpenError

        cb_error = CircuitBreakerOpenError(30.0, "Circuit breaker is open")
        sentinel = {"pvp1": "cb_error"}

        def returning_factory(e: Exception, req: Any) -> dict:
            return sentinel

        policy, mocks = _make_policy(
            cb_check_side_effect=cb_error,
            cb_error_factory=returning_factory,
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        result = await policy.execute(desc)

        assert result is sentinel
        mocks["get_client"].assert_not_awaited()
        mocks["execute_with_retry"].assert_not_awaited()


class TestExecuteErrorResponse:
    """test_execute_error_response: 500 response routes to error_handler."""

    async def test_error_response(self) -> None:
        error_result = {"error": "server_error"}
        error_handler = AsyncMock(return_value=error_result)

        policy, mocks = _make_policy(
            execute_response_status=500,
            error_handler=error_handler,
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        result = await policy.execute(desc)

        assert result == error_result
        error_handler.assert_awaited_once()
        call_args = error_handler.call_args
        assert call_args[0][0] is mocks["response"]
        assert call_args[0][1] is desc
        assert isinstance(call_args[0][2], float)
        mocks["success_handler"].assert_not_awaited()


class TestPreExecuteErrorHandlerReturns:
    """test_execute_pre_execute_error_handler_returns: stale fallback case."""

    async def test_pre_execute_returns_stale(self) -> None:
        stale_response = {"data": "stale"}

        def stale_handler(exc: Exception, req: Any) -> dict | None:
            if isinstance(exc, ValueError):
                return stale_response
            return None

        policy, mocks = _make_policy(
            execute_side_effect=ValueError("service down"),
            pre_execute_error_handler=stale_handler,
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        result = await policy.execute(desc)

        assert result is stale_response
        # error_handler and success_handler not called
        mocks["error_handler"].assert_not_awaited()
        mocks["success_handler"].assert_not_awaited()


class TestPreExecuteErrorHandlerNoneReraises:
    """test_execute_pre_execute_error_handler_none_reraises."""

    async def test_pre_execute_returns_none_reraises(self) -> None:
        def always_none(exc: Exception, req: Any) -> None:
            return None

        policy, mocks = _make_policy(
            execute_side_effect=ValueError("unrecoverable"),
            pre_execute_error_handler=always_none,
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        with pytest.raises(ValueError, match="unrecoverable"):
            await policy.execute(desc)

    async def test_no_pre_execute_handler_reraises(self) -> None:
        """Without pre_execute_error_handler, exceptions propagate."""
        policy, _ = _make_policy(
            execute_side_effect=ValueError("no handler"),
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        with pytest.raises(ValueError, match="no handler"):
            await policy.execute(desc)


class TestExecuteTiming:
    """test_execute_timing: elapsed_ms passed to handlers is reasonable."""

    async def test_elapsed_ms_is_positive(self) -> None:
        success_handler = AsyncMock(return_value="ok")
        policy, mocks = _make_policy(success_handler=success_handler)
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        await policy.execute(desc)

        call_args = success_handler.call_args
        elapsed_ms = call_args[0][2]
        assert elapsed_ms >= 0.0
        # Should be well under 1 second in unit tests
        assert elapsed_ms < 5000.0

    async def test_elapsed_ms_reflects_delay(self) -> None:
        """Elapsed time includes execute_with_retry delay."""

        async def slow_execute(*args: Any, **kwargs: Any) -> tuple:
            await asyncio.sleep(0.05)  # 50ms
            return _make_response(200), 0

        success_handler = AsyncMock(return_value="ok")
        cb = AsyncMock()
        cb.check.return_value = None

        policy = DefaultEndpointPolicy(
            circuit_breaker=cb,
            get_client=AsyncMock(return_value=MagicMock()),
            execute_with_retry=slow_execute,
            cb_error_factory=lambda e, r: (_ for _ in ()).throw(RuntimeError("cb")),
            request_builder=MagicMock(return_value=MagicMock()),
            error_handler=AsyncMock(),
            success_handler=success_handler,
        )
        desc = _StubDescriptor(
            retry_callbacks=_StubRetryCallbacks(
                on_timeout_exhausted=AsyncMock(),
                on_http_error=AsyncMock(),
            )
        )

        await policy.execute(desc)

        elapsed_ms = success_handler.call_args[0][2]
        assert elapsed_ms >= 40.0  # At least ~40ms (allowing margin)
