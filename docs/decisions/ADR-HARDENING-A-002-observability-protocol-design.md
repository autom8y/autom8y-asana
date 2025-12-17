# ADR-HARDENING-A-002: ObservabilityHook Protocol Design

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: SDK Team
- **Related**: PRD-HARDENING-A, TDD-HARDENING-A, ADR-0023 (CacheLoggingProvider)

## Context

The SDK lacks standardized hooks for observability integration. While `@error_handler` decorator provides correlation IDs and basic timing, there is no protocol for:

- Request-level metrics (latency, status codes)
- Rate limit events
- Circuit breaker state changes
- Retry attempts
- Custom telemetry integration (Prometheus, DataDog, OpenTelemetry)

Per Discovery Issue 14, teams want to plug in metrics libraries without modifying SDK internals. The SDK already uses `typing.Protocol` for dependency injection (see `protocols/log.py`, `protocols/cache.py`), establishing a pattern we should follow.

### Forces at Play

1. **Consistency**: Follow existing Protocol pattern in SDK
2. **Flexibility**: Support sync and async implementations
3. **Performance**: Zero-cost when no hook registered
4. **Simplicity**: Easy to implement custom hooks
5. **Future-proof**: Allow adding new hook methods without breaking existing implementations
6. **No dependencies**: Cannot require external libraries (PRD constraint)

## Decision

**Define `ObservabilityHook` as a `typing.Protocol` with async methods for request lifecycle and resilience events, plus a `NullObservabilityHook` default implementation.**

### Protocol Definition

```python
# protocols/observability.py
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Implement this protocol to receive SDK operation events for metrics,
    tracing, or logging integration. All methods are async to support
    non-blocking telemetry backends.

    The SDK calls these hooks at key points in the request lifecycle.
    Implementations should be lightweight and non-blocking to avoid
    impacting request latency.

    Example:
        class DataDogHook:
            async def on_request_start(
                self, method: str, path: str, correlation_id: str
            ) -> None:
                statsd.increment('asana.requests.started')

            async def on_request_end(
                self, method: str, path: str, status: int, duration_ms: float
            ) -> None:
                statsd.histogram('asana.request.duration', duration_ms)
                statsd.increment(f'asana.response.{status}')

            # ... implement other methods
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before an HTTP request is made.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: Request path (e.g., /tasks/123).
            correlation_id: Unique ID for request tracing.
        """
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after an HTTP request completes.

        Args:
            method: HTTP method.
            path: Request path.
            status: HTTP status code.
            duration_ms: Request duration in milliseconds.
        """
        ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        """Called when an HTTP request fails with an exception.

        Args:
            method: HTTP method.
            path: Request path.
            error: Exception that was raised.
        """
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called when rate limit (429) is encountered.

        Args:
            retry_after_seconds: Seconds until retry is allowed.
        """
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called when circuit breaker changes state.

        Args:
            old_state: Previous state (closed, open, half_open).
            new_state: New state.
        """
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before a retry attempt.

        Args:
            attempt: Current attempt number (1-indexed).
            max_attempts: Maximum attempts configured.
            error: Error that triggered the retry.
        """
        ...
```

### Null Implementation

```python
# _defaults/observability.py
from __future__ import annotations


class NullObservabilityHook:
    """No-op observability hook (default).

    This implementation satisfies ObservabilityHook protocol but performs
    no operations. Used as default when no custom hook is registered.

    All methods are effectively zero-cost since they return immediately.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        pass

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        pass

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        pass

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        pass

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        pass

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        pass
```

### Client Integration

```python
# client.py (partial)
class AsanaClient:
    def __init__(
        self,
        *,
        # ... existing params ...
        observability_hook: ObservabilityHook | None = None,
    ) -> None:
        self._observability = observability_hook or NullObservabilityHook()

    @property
    def observability(self) -> ObservabilityHook:
        """Observability hook for metrics and tracing."""
        return self._observability
```

## Rationale

### Why Protocol over ABC?

| Aspect | Protocol | ABC |
|--------|----------|-----|
| Structural typing | Yes | No |
| Inheritance required | No | Yes |
| Runtime checkable | Optional (`@runtime_checkable`) | Always |
| SDK pattern | Matches `LogProvider`, `CacheProvider` | Would break pattern |

Protocol was chosen for consistency with existing SDK patterns and to allow duck-typing (any object with matching methods works).

### Why Async Methods?

1. **Non-blocking telemetry**: Metrics backends (HTTP, gRPC) benefit from async
2. **Consistency**: SDK is async-first per ADR-0002
3. **Forward compatibility**: Easy to add async-only features later
4. **Sync compatibility**: Sync users can use `run_async()` or ignore async

### Why Null Object Pattern?

1. **No conditionals**: Call hooks unconditionally, null handles no-op case
2. **Type safety**: `self._observability` is always non-None
3. **Performance**: Method call overhead is negligible vs HTTP request
4. **Clean API**: No need for `if self._observability:` checks everywhere

## Alternatives Considered

### Alternative 1: Abstract Base Class (ABC)

- **Description**: `class ObservabilityHook(ABC)` with `@abstractmethod` decorators
- **Pros**: Explicit contract, IDE support for unimplemented methods
- **Cons**: Requires inheritance, breaks duck-typing, inconsistent with SDK patterns
- **Why not chosen**: SDK uses Protocol pattern for all injection points

### Alternative 2: Callback Dict Pattern

- **Description**: Dict of `{event_name: callable}` passed to client
- **Pros**: Simple, no class needed, familiar pattern
- **Cons**: No type safety, no IDE completion, easy to misspell event names
- **Why not chosen**: Protocol provides better developer experience

### Alternative 3: Sync-Only Methods

- **Description**: All hook methods are synchronous
- **Pros**: Simpler for sync users, no async overhead
- **Cons**: Blocking telemetry calls impact request latency
- **Why not chosen**: SDK is async-first; sync methods would block event loop

### Alternative 4: Event Emitter Pattern

- **Description**: `client.events.on('request_start', handler)`
- **Pros**: Familiar from Node.js, supports multiple handlers
- **Cons**: Dynamic registration, no type safety, magic strings
- **Why not chosen**: Protocol provides compile-time type checking

## Consequences

### Positive

- **Clean integration**: Teams can plug in Prometheus, DataDog, etc. without SDK changes
- **Type safety**: Protocol ensures implementations have correct method signatures
- **Zero overhead**: NullObservabilityHook is effectively no-op
- **Consistent pattern**: Matches existing `LogProvider`, `CacheProvider` patterns
- **Future extensibility**: New hook methods can be added to protocol

### Negative

- **Async requirement**: Sync-only consumers must wrap hooks in async adapters
- **Method overhead**: Each hook is a method call (minimal but non-zero)
- **Protocol verbose**: 6 methods to implement for full observability

### Neutral

- **Documentation**: SDK guide must explain how to implement custom hooks
- **Testing**: Need tests for hook invocation at correct lifecycle points
- **Optional integration**: Hooks are opt-in; existing code unaffected

## Compliance

To ensure this decision is followed:

1. **Transport integration**: `AsyncHTTPClient` must call hooks at request start/end/error
2. **Rate limiter integration**: `RateLimiter` must call `on_rate_limit`
3. **Circuit breaker integration**: `CircuitBreaker` must call `on_circuit_breaker_state_change`
4. **Retry integration**: `RetryHandler` must call `on_retry`
5. **Tests**: Verify hooks are called with correct arguments in each scenario

## Example Implementation

```python
# User's custom hook for Prometheus
from prometheus_client import Counter, Histogram

class PrometheusHook:
    def __init__(self):
        self.requests = Counter('asana_requests_total', 'Total requests', ['method', 'status'])
        self.latency = Histogram('asana_request_duration_seconds', 'Request latency')

    async def on_request_start(self, method: str, path: str, correlation_id: str) -> None:
        pass  # Could start a span here

    async def on_request_end(self, method: str, path: str, status: int, duration_ms: float) -> None:
        self.requests.labels(method=method, status=str(status)).inc()
        self.latency.observe(duration_ms / 1000)

    async def on_request_error(self, method: str, path: str, error: Exception) -> None:
        self.requests.labels(method=method, status='error').inc()

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        pass

    async def on_circuit_breaker_state_change(self, old_state: str, new_state: str) -> None:
        pass

    async def on_retry(self, attempt: int, max_attempts: int, error: Exception) -> None:
        pass


# Usage
client = AsanaClient(
    auth=BearerAuth(token),
    observability_hook=PrometheusHook(),
)
```
