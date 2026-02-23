"""Execution policy for DataServiceClient endpoints.

Abstracts the 8-step orchestration scaffold (S2-S8) into a reusable
DefaultEndpointPolicy. Endpoints provide a request descriptor and
pluggable behaviors; the policy owns the circuit-breaker -> retry ->
error-handling -> parse pipeline.

Per WS-DSC TDD Sections 2-4: Protocol + Generic implementation.

This module is NOT part of the public API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from autom8y_http import CircuitBreakerOpenError, Response

    from autom8_asana.clients.data._retry import RetryCallbacks

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

T_contra = TypeVar("T_contra", contravariant=True)  # Request descriptor
R_co = TypeVar("R_co", covariant=True)  # Response type


@runtime_checkable
class EndpointPolicy(Protocol[T_contra, R_co]):
    """Protocol for endpoint execution policies.

    Encapsulates the circuit-breaker -> retry -> error-handling -> parse
    pipeline. Endpoints provide a request descriptor; the policy returns
    the parsed response.

    Type Parameters:
        T_contra: Request descriptor type (contravariant).
        R_co: Parsed response type (covariant).
    """

    async def execute(self, request: T_contra) -> R_co:
        """Execute the endpoint pipeline.

        Args:
            request: Endpoint-specific request descriptor.

        Returns:
            Parsed domain response.

        Raises:
            Domain-specific errors (InsightsServiceError, ExportError, etc.)
        """
        ...


# ---------------------------------------------------------------------------
# Request Descriptors
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SimpleRequestDescriptor:
    """Descriptor for simple GET endpoints (appointments, leads)."""

    path: str
    params: dict[str, str]
    request_id: str
    cache_key: str
    factory_label: str  # e.g., "appointments", "leads"
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class ReconciliationRequestDescriptor:
    """Descriptor for POST /insights/reconciliation/execute."""

    path: str
    body: dict[str, Any]
    request_id: str
    cache_key: str
    factory_label: str
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class ExportRequestDescriptor:
    """Descriptor for GET /messages/export."""

    path: str
    params: dict[str, str]
    masked_phone: str
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class InsightsRequestDescriptor:
    """Descriptor for POST /data-service/insights."""

    path: str
    request_body: dict[str, Any]
    request_id: str
    cache_key: str
    factory: str
    retry_callbacks: RetryCallbacks


@dataclass(frozen=True, slots=True)
class BatchRequestDescriptor:
    """Descriptor for POST /data-service/insights (batch)."""

    path: str
    request_body: dict[str, Any]
    request_id: str
    pvp_list: list[Any]  # list[PhoneVerticalPair]
    pvp_by_key: dict[str, Any]  # dict[str, PhoneVerticalPair]
    retry_callbacks: RetryCallbacks


# ---------------------------------------------------------------------------
# Default Implementation
# ---------------------------------------------------------------------------

T = TypeVar("T")  # Request descriptor
R = TypeVar("R")  # Response type


class DefaultEndpointPolicy(Generic[T, R]):
    """Default implementation of the endpoint execution policy.

    Encapsulates steps S2-S8 of the orchestration scaffold.
    Endpoint-specific behavior is injected via constructor callables.

    Constructor Parameters:
        circuit_breaker: CircuitBreaker instance for check/record.
        get_client: Async callable returning the HTTP client.
        execute_with_retry: The client._execute_with_retry bound method.
        cb_error_factory: Converts CircuitBreakerOpenError to domain error.
            If it *raises*, the exception propagates (normal path).
            If it *returns*, the value is returned as an early short-circuit
            (batch path -- non-raising).
        request_builder: (http_client, descriptor) -> make_request callable.
        error_handler: Async callable for HTTP error responses (status >= 400).
        success_handler: Async callable for successful responses.
        pre_execute_error_handler: Optional. Handles exceptions from
            execute_with_retry (e.g., insights stale fallback). Returns R
            to short-circuit, or None to re-raise.
    """

    def __init__(
        self,
        *,
        circuit_breaker: Any,
        get_client: Callable[[], Awaitable[Any]],
        execute_with_retry: Callable[..., Awaitable[tuple[Response, int]]],
        cb_error_factory: Callable[[CircuitBreakerOpenError, T], R],
        request_builder: Callable[[Any, T], Callable[[], Awaitable[Response]]],
        error_handler: Callable[[Response, T, float], Awaitable[R]],
        success_handler: Callable[[Response, T, float], Awaitable[R]],
        pre_execute_error_handler: Callable[[Exception, T], R | None] | None = None,
    ) -> None:
        self._circuit_breaker = circuit_breaker
        self._get_client = get_client
        self._execute_with_retry = execute_with_retry
        self._cb_error_factory = cb_error_factory
        self._request_builder = request_builder
        self._error_handler = error_handler
        self._success_handler = success_handler
        self._pre_execute_error_handler = pre_execute_error_handler

    async def execute(self, request: T) -> R:
        """Execute the endpoint pipeline (S2-S8)."""
        from autom8y_http import CircuitBreakerOpenError as _CBOpenError

        # S2: Circuit breaker check
        try:
            await self._circuit_breaker.check()
        except _CBOpenError as e:
            # cb_error_factory either raises (normal) or returns (batch)
            return self._cb_error_factory(e, request)

        # S3: Acquire HTTP client
        http_client = await self._get_client()

        # Timing
        start_time = time.monotonic()

        # S4-S5: Build request + execute with retry
        make_request = self._request_builder(http_client, request)
        callbacks = request.retry_callbacks  # type: ignore[attr-error]
        try:
            response, _attempt = await self._execute_with_retry(
                make_request,
                on_retry=callbacks.on_retry,
                on_timeout_exhausted=callbacks.on_timeout_exhausted,
                on_http_error=callbacks.on_http_error,
            )
        except Exception as exc:
            if self._pre_execute_error_handler is not None:
                result = self._pre_execute_error_handler(exc, request)
                if result is not None:
                    return result
            raise

        elapsed_ms = (time.monotonic() - start_time) * 1000

        # S6: Error path
        if response.status_code >= 400:
            return await self._error_handler(response, request, elapsed_ms)

        # S7-S8: Success path
        return await self._success_handler(response, request, elapsed_ms)
