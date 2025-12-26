# ADR-0057: Resilience and Hook Patterns

## Metadata
- **Status**: Accepted
- **Consolidated From**: ADR-0048 (Circuit Breaker Pattern), ADR-0041 (Sync Hooks with Async Support), ADR-0091 (RetryableErrorMixin)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Related**: [reference/PATTERNS.md](reference/PATTERNS.md), ADR-0052 (ObservabilityHook Protocol)

---

## Context

The SDK needs patterns for:
1. **Resilience**: Protect against cascading failures when Asana API is degraded
2. **Event lifecycle hooks**: Extensible synchronous/async hooks for SaveSession and observability
3. **Error classification**: Declarative retry classification for exceptions

**Forces at play**:
- **Backward compatibility**: Existing code must work unchanged
- **Opt-in design**: Features disabled by default
- **Testability**: Components must be mockable
- **Performance**: Minimal overhead when disabled
- **Observability**: Clear visibility into circuit state and hook execution

---

## Decision

Use **composition-based circuit breaker**, **protocol-based hooks** with sync-first design, and **mixin-based error classification**.

### 1. Circuit Breaker Pattern

**Composition-based circuit breaker wrapping HTTP client request path.**

**State Machine**:

```
CLOSED → (failure_threshold reached) → OPEN
OPEN → (recovery_timeout elapsed) → HALF_OPEN
HALF_OPEN → (probe succeeds) → CLOSED
HALF_OPEN → (probe fails) → OPEN
```

**Architecture**:

```
┌─────────────────────────────────────────────┐
│              AsyncHTTPClient                │
│  ┌────────────────────────────────────────┐│
│  │         CircuitBreaker.check()         ││
│  │  ┌──────────────────────────────────┐  ││
│  │  │       RetryHandler.execute()     │  ││
│  │  │  ┌────────────────────────────┐  │  ││
│  │  │  │    RateLimiter.acquire()   │  │  ││
│  │  │  │  ┌──────────────────────┐  │  │  ││
│  │  │  │  │   HTTP Request       │  │  │  ││
│  │  │  │  └──────────────────────┘  │  │  ││
│  │  │  └────────────────────────────┘  │  ││
│  │  └──────────────────────────────────┘  ││
│  └────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Configuration**:

```python
@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Configuration for circuit breaker.

    Per ADR-0057: Opt-in circuit breaker with composition pattern.

    Attributes:
        enabled: Feature flag (default: False for backward compat).
        failure_threshold: Consecutive failures to trigger OPEN.
        recovery_timeout: Seconds to wait in OPEN before HALF_OPEN.
        half_open_max_calls: Max concurrent calls in HALF_OPEN.

    Example:
        # Enable with defaults
        client = AsanaClient(
            circuit_breaker=CircuitBreakerConfig(enabled=True)
        )

        # Custom thresholds
        client = AsanaClient(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=3,
                recovery_timeout=30.0
            )
        )
    """
    enabled: bool = False  # Opt-in (backward compatible)
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1
```

**Usage**:

```python
# Opt-in to circuit breaker
client = AsanaClient(
    token="...",
    circuit_breaker=CircuitBreakerConfig(enabled=True)
)

# Default: disabled (backward compatible)
client = AsanaClient(token="...")  # No circuit breaker
```

**Scope**: Per-client instance (not shared across clients).

**Triggers**:
- HTTP 5xx responses (server errors)
- HTTP 429 after retries exhausted
- `httpx.HTTPError` (network failures)

**Check Before Request**:

```python
async def request(self, method: str, path: str, **kwargs) -> dict:
    """Make HTTP request with circuit breaker protection.

    Per ADR-0057: Check circuit breaker before request for fast failure.
    """
    # 1. Check circuit breaker state
    if self._circuit_breaker and self._circuit_breaker.enabled:
        self._circuit_breaker.check()  # Raises CircuitBreakerOpenError if OPEN

    try:
        # 2. Make request (via retry handler, rate limiter)
        response = await self._http.request(method, path, **kwargs)

        # 3. Record success
        if self._circuit_breaker:
            self._circuit_breaker.record_success()

        return response

    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        # 4. Record failure
        if self._circuit_breaker:
            self._circuit_breaker.record_failure()
        raise
```

**Exception**:

```python
class CircuitBreakerOpenError(AsanaError):
    """Raised when circuit breaker is OPEN.

    Attributes:
        retry_after: Seconds until recovery timeout expires.

    Example:
        try:
            await client.tasks.get_async("123")
        except CircuitBreakerOpenError as exc:
            logger.warning(f"Circuit open, retry in {exc.retry_after}s")
    """
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker open, retry after {retry_after:.1f}s")
```

**Rationale**:
- **Composition**: Clean separation, testable in isolation
- **Per-client scope**: No shared state, easier testing
- **Opt-in**: Backward compatible (disabled by default)
- **Check before request**: Fast failure, no wasted rate limit tokens
- **Network errors included**: Protection against both API and network failures

### 2. Synchronous Event Hooks

**Protocol-based hooks with sync-first design and async support.**

```python
@runtime_checkable
class SaveSessionHook(Protocol):
    """Protocol for SaveSession lifecycle hooks.

    Per ADR-0057: Sync-first with optional async variants.

    Implement to receive SaveSession events for logging, metrics,
    cache invalidation, or custom business logic.

    Example:
        class CacheInvalidationHook:
            def on_commit_end(
                self, session: SaveSession, result: CommitResult
            ) -> None:
                # Invalidate cache for modified entities
                for entity in result.created + result.updated:
                    cache.invalidate(entity.gid)

            def on_error(
                self, session: SaveSession, error: Exception
            ) -> None:
                logger.error(f"Commit failed: {error}")
    """

    def on_commit_start(self, session: SaveSession) -> None:
        """Called before commit begins (synchronous).

        Args:
            session: SaveSession about to commit.
        """
        ...

    def on_commit_end(
        self, session: SaveSession, result: CommitResult
    ) -> None:
        """Called after commit succeeds (synchronous).

        Args:
            session: SaveSession that committed.
            result: CommitResult with created/updated entities.
        """
        ...

    def on_error(self, session: SaveSession, error: Exception) -> None:
        """Called when commit fails (synchronous).

        Args:
            session: SaveSession that failed.
            error: Exception that occurred.
        """
        ...

    # Optional async variants
    async def on_commit_start_async(self, session: SaveSession) -> None:
        """Async variant of on_commit_start (optional)."""
        ...

    async def on_commit_end_async(
        self, session: SaveSession, result: CommitResult
    ) -> None:
        """Async variant of on_commit_end (optional)."""
        ...

    async def on_error_async(
        self, session: SaveSession, error: Exception
    ) -> None:
        """Async variant of on_error (optional)."""
        ...
```

**Hook Invocation**:

```python
async def commit_async(self) -> CommitResult:
    """Commit all pending operations with hook support.

    Per ADR-0057: Invokes hooks at lifecycle points.
    """
    # Invoke sync hook
    if self._hook:
        self._hook.on_commit_start(self)

    # Invoke async hook if available
    if self._hook and hasattr(self._hook, "on_commit_start_async"):
        await self._hook.on_commit_start_async(self)

    try:
        # Execute commit
        result = await self._execute_commit()

        # Invoke hooks on success
        if self._hook:
            self._hook.on_commit_end(self, result)
            if hasattr(self._hook, "on_commit_end_async"):
                await self._hook.on_commit_end_async(self, result)

        return result

    except Exception as exc:
        # Invoke hooks on error
        if self._hook:
            self._hook.on_error(self, exc)
            if hasattr(self._hook, "on_error_async"):
                await self._hook.on_error_async(self, exc)
        raise
```

**Use Cases**:
- **Logging**: Log commit details
- **Metrics**: Track commit duration, success rate
- **Cache invalidation**: Invalidate modified entities
- **Audit trail**: Record state changes

**Rationale**:
- **Sync-first**: Primary methods synchronous for simplicity
- **Async support**: Optional async variants for I/O (HTTP, gRPC backends)
- **Protocol**: Enables duck-typing, no inheritance required
- **hasattr check**: Gracefully handles sync-only implementations

### 3. RetryableErrorMixin

**Declarative retry classification via mixin.**

```python
class RetryableErrorMixin:
    """Mixin that marks errors as retryable.

    Per ADR-0057: Declarative retry classification.

    Add to exception classes that should be retried by RetryHandler.

    Example:
        class RateLimitError(AsanaError, RetryableErrorMixin):
            is_retryable: bool = True

        class ValidationError(AsanaError):
            is_retryable: bool = False  # Not retryable
    """
    is_retryable: bool = True
```

**Exception Hierarchy**:

```python
class AsanaError(Exception):
    """Base exception for SDK errors."""
    is_retryable: bool = False  # Default: not retryable


# Retryable errors
class RateLimitError(AsanaError, RetryableErrorMixin):
    """HTTP 429 rate limit exceeded (retryable)."""
    is_retryable: bool = True


class ServerError(AsanaError, RetryableErrorMixin):
    """HTTP 5xx server error (retryable)."""
    is_retryable: bool = True


class NetworkError(AsanaError, RetryableErrorMixin):
    """Network failure (retryable)."""
    is_retryable: bool = True


# Non-retryable errors
class ValidationError(AsanaError):
    """Input validation failed (not retryable)."""
    is_retryable: bool = False


class AuthenticationError(AsanaError):
    """Authentication failed (not retryable)."""
    is_retryable: bool = False


class NotFoundError(AsanaError):
    """Resource not found (not retryable)."""
    is_retryable: bool = False
```

**RetryHandler Integration**:

```python
async def execute(self, request_fn, *args, **kwargs):
    """Execute request with retry logic.

    Per ADR-0057: Check is_retryable attribute to determine retry.
    """
    attempts = 0

    while attempts < self._max_attempts:
        try:
            return await request_fn(*args, **kwargs)
        except Exception as exc:
            attempts += 1

            # Check if error is retryable
            is_retryable = getattr(exc, "is_retryable", False)

            if not is_retryable or attempts >= self._max_attempts:
                raise

            # Calculate backoff
            backoff = self._calculate_backoff(attempts)

            logger.warning(
                "retry_attempt",
                extra={
                    "attempt": attempts,
                    "max_attempts": self._max_attempts,
                    "error": str(exc),
                    "backoff_seconds": backoff
                }
            )

            await asyncio.sleep(backoff)

    raise  # Max attempts exhausted
```

**Rationale**:
- **Declarative**: Retry classification via class attribute
- **Mixin**: Adds `is_retryable` without deep hierarchy
- **Simple check**: `getattr(exc, "is_retryable", False)`
- **Flexible**: Can override per-instance if needed

---

## Rationale

### Why Composition for Circuit Breaker?

| Approach | Pros | Cons |
|----------|------|------|
| **Composition** | **Clean separation, testable, optional** | No coupling issues |
| Inheritance | Standard OOP | Tight coupling, hard to disable |
| Decorator | Functional | Complex with async, magic behavior |
| Middleware | Pluggable | Overkill for single component |

Composition provides clean separation and easy conditional enablement.

### Why Per-Client Scope?

| Scope | Pros | Cons |
|-------|------|------|
| **Per-client** | **Isolation, simple, testable** | No shared state tracking |
| Global shared | Single state | Complex synchronization, false positives |
| Thread-local | Per-thread | Complex lifecycle |

Per-client is simplest and safest for multi-tenant scenarios.

### Why Opt-In (Not Default-Enabled)?

**Backward compatibility requirement**:
- Existing code must work unchanged
- No surprise behavior changes
- Users explicitly enable when ready

**Default-enabled alternative rejected**:
- Breaking change for existing users
- Unexpected failures
- Users may not understand CircuitBreakerOpenError

### Why Sync-First Hooks?

**Primary methods synchronous**:
- Simplicity for sync users
- No async overhead for simple cases
- Common use cases (logging) don't need async

**Async support via optional methods**:
- HTTP/gRPC backends benefit from async
- Opt-in via additional method implementation
- `hasattr` check handles sync-only implementations

**Alternative** (async-only hooks):
- **Rejected**: Blocks event loop for sync operations
- Sync users must use `run_async()` or ignore hooks

### Why Mixin for Error Classification?

| Approach | Pros | Cons |
|----------|------|------|
| **Mixin** | **Simple, declarative, no hierarchy** | Multiple inheritance |
| ABC hierarchy | Clear inheritance | Deep hierarchy, rigid |
| Exception attributes | Flexible | Must set on every instance |
| Callback dict | Dynamic | No type safety, error-prone |

Mixin adds `is_retryable` flag without deep hierarchy.

---

## Alternatives Considered

### Circuit Breaker Alternatives

#### Alternative 1: Tenacity Library

- **Description**: Use `tenacity` library's built-in circuit breaker
- **Pros**: Battle-tested, feature-rich
- **Cons**: Additional dependency, less control, overkill
- **Why not chosen**: RetryHandler already exists; only need circuit breaker

#### Alternative 2: Global Shared Circuit Breaker

- **Description**: Single circuit breaker shared across all clients
- **Pros**: One degraded API affects all clients equally
- **Cons**: Complex synchronization, false positives, hard to test, multi-tenant issues
- **Why not chosen**: Per-client simpler and safer

#### Alternative 3: Subclass RetryHandler

- **Description**: Add circuit breaker logic to RetryHandler via inheritance
- **Pros**: Single class handles both
- **Cons**: Violates single responsibility, harder to test, tight coupling
- **Why not chosen**: Composition cleaner

#### Alternative 4: Default-Enabled

- **Description**: Circuit breaker enabled by default
- **Pros**: Safer defaults
- **Cons**: Breaking change, unexpected behavior
- **Why not chosen**: Backward compatibility required

### Hook Alternatives

#### Alternative 1: Callback Dict Pattern

- **Description**: `{event_name: callable}` passed to session
- **Pros**: Simple, no class needed
- **Cons**: No type safety, no IDE completion, easy to misspell
- **Why not chosen**: Protocol provides better developer experience

#### Alternative 2: Async-Only Methods

- **Description**: All hook methods async
- **Pros**: Simpler for async users
- **Cons**: Blocks event loop for sync operations
- **Why not chosen**: Sync methods work for common cases (logging)

#### Alternative 3: Event Emitter Pattern

- **Description**: `session.events.on('commit_start', handler)`
- **Pros**: Familiar from Node.js, multiple handlers
- **Cons**: Dynamic registration, no type safety, magic strings
- **Why not chosen**: Protocol provides compile-time checking

### Error Classification Alternatives

#### Alternative 1: ABC Hierarchy

- **Description**: Retryable exceptions inherit from `RetryableError(ABC)`
- **Pros**: Clear inheritance, explicit contract
- **Cons**: Deep hierarchy, rigid, forces inheritance
- **Why not chosen**: Mixin is simpler without hierarchy

#### Alternative 2: Exception Attributes

- **Description**: Set `exc.is_retryable = True` on instances
- **Pros**: Flexible, per-instance control
- **Cons**: Must set on every raise, error-prone, no class-level default
- **Why not chosen**: Class attribute cleaner

#### Alternative 3: Callback Registry

- **Description**: Register `{ExceptionClass: is_retryable}` mapping
- **Pros**: Centralized configuration
- **Cons**: Global state, registry maintenance burden
- **Why not chosen**: Declarative class attribute clearer

---

## Consequences

### Positive

1. **Circuit Breaker**:
   - Protection against cascading failures
   - Fast failure when service known-bad
   - Automatic recovery detection
   - Backward compatible (opt-in)
   - Clean separation of concerns
   - Observable via hooks

2. **Event Hooks**:
   - Clean integration for logging, metrics, cache invalidation
   - Type safety via Protocol
   - Sync-first with async support
   - No coupling to hook implementation

3. **RetryableErrorMixin**:
   - Declarative classification
   - Simple `getattr` check
   - No deep hierarchy
   - Flexible (can override per-instance)

### Negative

1. **Circuit Breaker**:
   - Additional configuration option
   - Users must explicitly enable
   - Per-client scope may not fit all cases
   - Additional exception type (CircuitBreakerOpenError)

2. **Event Hooks**:
   - Async requirement for I/O hooks
   - Method overhead (minimal)
   - Protocol verbose (multiple methods)

3. **RetryableErrorMixin**:
   - Multiple inheritance (mixin pattern)
   - Must remember to add mixin to retryable errors

### Neutral

1. **Circuit Breaker**:
   - State not persisted across restarts
   - No metrics export (future work)
   - Recovery is time-based only (no health checks)

2. **Event Hooks**:
   - Optional integration
   - Documentation must explain usage

3. **RetryableErrorMixin**:
   - Simple pattern, easy to understand

---

## Compliance

### How This Decision Will Be Enforced

1. **Circuit Breaker**:
   - [ ] `CircuitBreakerConfig` with `enabled=False` default
   - [ ] Integration in AsyncHTTPClient.request()
   - [ ] Unit tests for all state transitions
   - [ ] Event hooks for state changes

2. **Event Hooks**:
   - [ ] SaveSession accepts optional hook parameter
   - [ ] Hooks invoked at lifecycle points
   - [ ] `hasattr` check for async variants
   - [ ] Tests verify hook invocation

3. **RetryableErrorMixin**:
   - [ ] Retryable errors use mixin
   - [ ] Non-retryable errors do not use mixin
   - [ ] RetryHandler checks `is_retryable` attribute
   - [ ] Tests verify retry behavior

---

## Usage Examples

### Circuit Breaker

```python
# Enable with defaults
client = AsanaClient(
    token="...",
    circuit_breaker=CircuitBreakerConfig(enabled=True)
)

# Custom configuration
client = AsanaClient(
    token="...",
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=3,
        recovery_timeout=30.0
    )
)

# Handle circuit breaker errors
try:
    task = await client.tasks.get_async("123")
except CircuitBreakerOpenError as exc:
    logger.warning(f"Circuit open, retry in {exc.retry_after}s")
    # Implement fallback logic
```

### Event Hooks

```python
class MetricsHook:
    def on_commit_start(self, session: SaveSession) -> None:
        statsd.increment('savesession.commit.started')

    def on_commit_end(self, session: SaveSession, result: CommitResult) -> None:
        statsd.increment('savesession.commit.success')
        statsd.histogram('savesession.entities.created', len(result.created))

    def on_error(self, session: SaveSession, error: Exception) -> None:
        statsd.increment('savesession.commit.error')

    # Optional async variant
    async def on_commit_end_async(
        self, session: SaveSession, result: CommitResult
    ) -> None:
        # Send metrics to async HTTP backend
        await metrics_client.send({
            'event': 'commit_success',
            'created': len(result.created),
            'updated': len(result.updated)
        })

# Usage
async with client.save_session(hook=MetricsHook()) as session:
    session.track(business)
    await session.commit_async()
```

### Error Classification

```python
# Define retryable error
class TemporaryAPIError(AsanaError, RetryableErrorMixin):
    is_retryable: bool = True

# Define non-retryable error
class InvalidGIDError(AsanaError):
    is_retryable: bool = False

# RetryHandler automatically retries TemporaryAPIError
try:
    await client.tasks.get_async("123")
except TemporaryAPIError:
    # Retries exhausted
    pass
except InvalidGIDError:
    # Not retried (fails immediately)
    pass
```

---

**Related**: ADR-0052 (ObservabilityHook Protocol), ADR-SUMMARY-OPERATIONS (resilience), reference/PATTERNS.md (full catalog)

**Supersedes**: Individual ADRs ADR-0048, ADR-0041, ADR-0091
