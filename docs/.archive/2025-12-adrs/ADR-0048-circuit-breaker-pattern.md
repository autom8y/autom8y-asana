# ADR-0048: Circuit Breaker Pattern for Transport Layer

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0009 (FR-RETRY-005 through FR-RETRY-010), TDD-0014

## Context

The SDK needs resilience against cascading failures when the Asana API is degraded or unavailable. PRD-0009 requires circuit breaker functionality to complement the existing retry handler.

**Current State:**
- `RetryHandler` exists with exponential backoff and jitter
- `TokenBucketRateLimiter` exists for rate limiting
- No circuit breaker for cascading failure prevention

**Forces at play:**

1. **Resilience**: Stop hammering a failing service
2. **Fast Failure**: Fail quickly when service is known-bad
3. **Auto-Recovery**: Automatically detect when service recovers
4. **Backward Compatibility**: Existing code must continue to work unchanged
5. **Observability**: Users need visibility into circuit state

**Problem**: How should circuit breaker be implemented and integrated?

## Decision

Implement a **composition-based circuit breaker** that wraps the HTTP client request path. Circuit breaker is **opt-in** (disabled by default) for backward compatibility.

**Architecture:**

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

**State Machine:**

```
CLOSED → (failure_threshold reached) → OPEN
OPEN → (recovery_timeout elapsed) → HALF_OPEN
HALF_OPEN → (probe succeeds) → CLOSED
HALF_OPEN → (probe fails) → OPEN
```

**Scope:** Per-client instance (not shared across clients).

**Configuration:**

```python
@dataclass(frozen=True)
class CircuitBreakerConfig:
    enabled: bool = False  # Opt-in
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1
```

**Usage:**

```python
# Opt-in to circuit breaker
client = AsanaClient(
    token="...",
    circuit_breaker=CircuitBreakerConfig(enabled=True)
)

# With custom settings
client = AsanaClient(
    token="...",
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=3,
        recovery_timeout=30.0,
    )
)

# Default: circuit breaker disabled (backward compatible)
client = AsanaClient(token="...")  # No circuit breaker
```

## Rationale

### Why Composition (Not Inheritance/Decorator)

1. **Clear Responsibility**: CircuitBreaker is a standalone component
2. **Testable**: Can unit test circuit breaker in isolation
3. **Optional**: Easy to conditionally enable/disable
4. **No Coupling**: Doesn't require modifying RetryHandler or RateLimiter

### Why Per-Client Scope (Not Shared)

1. **Simplicity**: No shared state management
2. **Isolation**: Different clients can have different thresholds
3. **Testing**: Easier to test without global state
4. **Multi-Tenant**: One degraded workspace doesn't affect others

Alternative (shared circuit breaker) was rejected because:
- Complex synchronization across clients
- Harder to reason about state
- Risk of false positives from unrelated failures

### Why Opt-In (Not Default-Enabled)

NFR-COMPAT-002 requires backward compatibility:
- Existing code must work unchanged
- No surprise behavior changes
- Users explicitly enable when ready

### Why Check Before Request (Not After)

Circuit breaker checks state before making request:
1. **Fast Failure**: Immediately reject when circuit is OPEN
2. **No Wasted Resources**: Don't consume rate limit tokens
3. **Clear Exception**: `CircuitBreakerOpenError` with time-to-recovery

### Why Include Network Errors

Circuit breaker should trip on:
- HTTP 5xx responses (server errors)
- HTTP 429 after retries exhausted
- `httpx.HTTPError` (network failures)

This provides protection against both API errors and network issues.

## Alternatives Considered

### Alternative 1: Tenacity Library

- **Description**: Use `tenacity` library's built-in circuit breaker
- **Pros**: Battle-tested, feature-rich
- **Cons**:
  - Additional dependency
  - Less control over integration
  - Overkill for our simple needs
- **Why not chosen**: Retry already exists; only need circuit breaker

### Alternative 2: Global Shared Circuit Breaker

- **Description**: Single circuit breaker shared across all clients
- **Pros**: One degraded API affects all clients equally
- **Cons**:
  - Complex synchronization
  - False positives from unrelated errors
  - Hard to test
  - Multi-tenant issues
- **Why not chosen**: Per-client is simpler and safer

### Alternative 3: Subclass RetryHandler

- **Description**: Add circuit breaker logic to RetryHandler via inheritance
- **Pros**: Single class handles both
- **Cons**:
  - Violates single responsibility
  - Harder to test independently
  - Tight coupling
- **Why not chosen**: Composition is cleaner

### Alternative 4: Middleware Pattern

- **Description**: Implement as HTTP middleware layer
- **Pros**: Familiar pattern, pluggable
- **Cons**:
  - More complex architecture
  - Requires middleware infrastructure
  - Overkill for single component
- **Why not chosen**: Simple composition is sufficient

### Alternative 5: Default-Enabled Circuit Breaker

- **Description**: Circuit breaker enabled by default
- **Pros**: Safer defaults for production
- **Cons**:
  - Breaking change for existing users
  - Unexpected behavior
  - Users may not understand failures
- **Why not chosen**: Backward compatibility required (NFR-COMPAT-002)

## Consequences

### Positive
- Protection against cascading failures
- Fast failure when service is known-bad
- Automatic recovery detection
- Backward compatible (opt-in)
- Clean separation of concerns
- Observable via event hooks

### Negative
- Additional configuration option
- Users must explicitly enable
- Per-client scope may not fit all use cases
- Additional exception type (CircuitBreakerOpenError)

### Neutral
- State is not persisted across process restarts
- No metrics export (future work)
- Recovery is time-based only (no health checks)

## Compliance

How do we ensure this decision is followed?

1. **API Design**: `CircuitBreakerConfig` with `enabled=False` default
2. **Integration**: Circuit breaker check in AsyncHTTPClient.request()
3. **Testing**: Unit tests for all state transitions
4. **Documentation**: README section on resilience patterns
5. **Event Hooks**: on_state_change, on_failure, on_success callbacks
