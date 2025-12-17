"""Observability hook protocol for telemetry integration.

Per TDD-HARDENING-A/FR-OBS-001: Define ObservabilityHook protocol for
telemetry integration with the SDK.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Per FR-OBS-001: Define ObservabilityHook protocol for telemetry integration.

    Implement this protocol to receive SDK operation events for:
    - Metrics collection (request latency, error rates, rate limits)
    - Distributed tracing (request spans, correlation IDs)
    - Custom monitoring dashboards

    All methods are async to support non-blocking telemetry backends.
    Implementations should be lightweight - avoid blocking the SDK.

    Example:
        class DatadogHook:
            '''Datadog APM integration.'''

            async def on_request_start(
                self, method: str, path: str, correlation_id: str
            ) -> None:
                self.span = tracer.start_span("asana.request")
                self.span.set_tag("http.method", method)
                self.span.set_tag("http.path", path)
                self.span.set_tag("correlation_id", correlation_id)

            async def on_request_end(
                self, method: str, path: str, status: int, duration_ms: float
            ) -> None:
                self.span.set_tag("http.status_code", status)
                self.span.finish()
                statsd.histogram("asana.request.duration", duration_ms)

            # ... implement other methods ...

        client = AsanaClient(
            token="...",
            observability_hook=DatadogHook(),
        )
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before HTTP request is sent.

        Per FR-OBS-002: Hook point for request start.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: Request path (e.g., "/tasks/1234567890").
            correlation_id: Request correlation ID for tracing.
        """
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after HTTP request completes successfully.

        Per FR-OBS-003: Hook point for request completion.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: Request path (e.g., "/tasks/1234567890").
            status: HTTP status code (200, 201, 400, etc.).
            duration_ms: Request duration in milliseconds.
        """
        ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        """Called when HTTP request fails with an exception.

        Per FR-OBS-004: Hook point for request errors.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: Request path (e.g., "/tasks/1234567890").
            error: Exception that caused the failure.
        """
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called when rate limit (429) is received.

        Per FR-OBS-005: Hook point for rate limiting events.

        Args:
            retry_after_seconds: Seconds to wait before retrying
                (from Retry-After header).
        """
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called when circuit breaker state changes.

        Per FR-OBS-006: Hook point for circuit breaker transitions.

        Args:
            old_state: Previous state ("closed", "open", "half_open").
            new_state: New state ("closed", "open", "half_open").
        """
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before retry attempt.

        Per FR-OBS-007: Hook point for retry events.

        Args:
            attempt: Current attempt number (1-indexed).
            max_attempts: Maximum retry attempts configured.
            error: Exception that triggered the retry.
        """
        ...


__all__ = ["ObservabilityHook"]
