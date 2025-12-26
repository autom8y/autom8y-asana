# ADR-0038: Resilience & Graceful Degradation

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0048 (Circuit Breaker), ADR-0127 (Cache Degradation), ADR-0090 (Demo Error Handling)
- **Related**: reference/API-INTEGRATION.md

## Context

The SDK must remain resilient when infrastructure degrades or fails:
- **Asana API**: May experience 5xx errors, timeouts, or rate limit exhaustion
- **Cache layer**: Redis connection may be lost, memory exhaustion may occur
- **Network**: Transient failures, DNS issues, connection timeouts

The SDK is used in production systems where cascading failures and total unavailability are unacceptable. Both the API transport layer and optional components (cache) need graceful degradation strategies.

Forces at play:
- **Resilience**: Stop hammering failing services
- **Fast Failure**: Fail quickly when service is known-bad
- **Auto-Recovery**: Automatically detect when service recovers
- **Backward Compatibility**: Existing code must work unchanged
- **Observability**: Users need visibility into degradation state
- **Cache as Optimization**: Cache failures shouldn't break user operations

## Decision

### Circuit Breaker Pattern (Opt-In)

**Implement composition-based circuit breaker wrapping HTTP client request path.**

Circuit breaker is **opt-in** (disabled by default) for backward compatibility.

#### Architecture

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

#### State Machine

```
CLOSED → (failure_threshold reached) → OPEN
OPEN → (recovery_timeout elapsed) → HALF_OPEN
HALF_OPEN → (probe succeeds) → CLOSED
HALF_OPEN → (probe fails) → OPEN
```

#### Configuration

```python
@dataclass(frozen=True)
class CircuitBreakerConfig:
    enabled: bool = False  # Opt-in for backward compatibility
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1
```

#### Usage

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
client = AsanaClient(token="...")
```

#### Failure Criteria

Circuit breaker trips on:
- HTTP 5xx responses (server errors)
- HTTP 429 after retries exhausted
- `httpx.HTTPError` (network failures)

### Cache Graceful Degradation

**Log warnings and treat cache failures as cache misses; continue with API fallback.**

All cache operations wrapped with graceful degradation:

```python
def _cache_get(self, key: str, entry_type: EntryType) -> CacheEntry | None:
    """Check cache with graceful degradation."""
    if self._cache is None:
        return None

    try:
        entry = self._cache.get_versioned(key, entry_type)
        if entry and not entry.is_expired():
            return entry
        return None
    except Exception as exc:
        # Graceful degradation: log and return miss
        logger.warning(
            "Cache get failed for %s (key=%s): %s",
            entry_type.value,
            key,
            exc,
        )
        # Metric: cache error
        self._observability.increment("cache.errors", tags={"entry_type": entry_type.value})
        return None  # Treat as cache miss

def _cache_set(self, key: str, data: dict, entry_type: EntryType, ttl: int | None = None) -> None:
    """Store in cache with graceful degradation."""
    if self._cache is None:
        return

    try:
        entry = CacheEntry(key=key, data=data, entry_type=entry_type, ...)
        self._cache.set_versioned(key, entry)
    except Exception as exc:
        # Graceful degradation: log and continue
        logger.warning(
            "Cache set failed for %s (key=%s): %s",
            entry_type.value,
            key,
            exc,
        )
        self._observability.increment("cache.errors", tags={"entry_type": entry_type.value})
        # Operation continues - data was fetched from API successfully
```

#### Cache Degradation Behaviors

| Scenario | Behavior |
|----------|----------|
| Cache `get()` fails | Log WARNING, return `None` (miss), fetch from API |
| Cache `set()` fails | Log WARNING, continue (next request will re-fetch) |
| Cache `invalidate()` fails | Log WARNING, continue (stale data may remain) |
| Cache provider unavailable | All operations treat as if cache disabled |
| Deserialization error | Log WARNING, treat as miss, continue |

#### Why WARNING Level?

| Level | Pros | Cons |
|-------|------|------|
| DEBUG | Low noise | Invisible in production |
| INFO | Visible | Too noisy for routine failures |
| **WARNING** | Visible, actionable | May trigger alerts if frequent |
| ERROR | High visibility | Overstates severity (SDK works) |

**WARNING** is correct because:
- Cache failure is not application error
- Indicates suboptimal performance (worth investigating)
- Standard log aggregators surface WARNINGs
- Repeated warnings indicate infrastructure issue

### Demo Script Error Handling

Demo scripts use graceful degradation to guide users through recovery:

```python
async def main():
    try:
        client = AsanaClient(token=os.getenv("ASANA_TOKEN"))
        # ... demo operations
    except RateLimitError as e:
        print(f"Rate limit exceeded. Retry after {e.retry_after} seconds.")
        sys.exit(1)
    except ServerError as e:
        print(f"Asana API error: {e}. Please try again later.")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"Error: {e}")
        sys.exit(1)
```

**Graceful messages** guide users to:
- Check credentials
- Respect rate limits
- Wait for service recovery
- Report unexpected errors

## Rationale

### Why Circuit Breaker Opt-In?

**Backward compatibility** (NFR-COMPAT-002):
- Existing code must work unchanged
- No surprise behavior changes
- Users explicitly enable when ready

**Default disabled** because:
- Circuit state management adds complexity
- False positives possible (burst errors)
- Users may not understand circuit breaker failures
- Conservative approach for library

### Why Per-Client Scope (Not Shared)?

1. **Simplicity**: No shared state management
2. **Isolation**: Different clients can have different thresholds
3. **Testing**: Easier to test without global state
4. **Multi-Tenant**: One degraded workspace doesn't affect others

Shared circuit breaker rejected:
- Complex synchronization across clients
- Harder to reason about state
- Risk of false positives from unrelated failures

### Why Check Before Request?

Circuit breaker checks state **before making request**:
1. **Fast Failure**: Immediately reject when circuit is OPEN
2. **No Wasted Resources**: Don't consume rate limit tokens
3. **Clear Exception**: `CircuitBreakerOpenError` with time-to-recovery

### Why Catch All Cache Exceptions?

```python
except Exception as exc:
```

Catch broadly because:
- Cache providers may raise any exception type
- Redis: `redis.exceptions.ConnectionError`, `redis.exceptions.TimeoutError`
- InMemory: `MemoryError`, `KeyError`, `TypeError`
- Unknown providers: Any exception
- Cannot enumerate all possible failures

Do NOT catch `BaseException`:
- `KeyboardInterrupt` should propagate
- `SystemExit` should propagate

### Why Not Retry Cache Operations?

**Rejected**: Automatic retry on cache failure
```python
for attempt in range(3):
    try:
        return self._cache.get_versioned(key, entry_type)
    except Exception:
        if attempt == 2:
            raise
        time.sleep(0.1)
```

**Why rejected**:
- Retries add latency to every failure (300ms+ for 3 attempts)
- Cache miss path (API call) is faster than retrying broken cache
- Circuit breaker in provider handles transient failures

### Why Log Exception Details?

```python
logger.warning("Cache get failed for %s (key=%s): %s", entry_type.value, key, exc)
```

Include in log:
- **entry_type**: Which cache operation failed (TASK, SUBTASKS)
- **key**: Which entity was affected (task GID)
- **exc**: What went wrong (connection refused, timeout)

Enables:
- Filtering logs by entry type
- Correlating with specific tasks
- Diagnosing root cause

## Alternatives Considered

### Circuit Breaker Alternatives

#### Tenacity Library

- **Pros**: Battle-tested, feature-rich
- **Cons**: Additional dependency, less control, overkill
- **Why not chosen**: Retry already exists; only need circuit breaker

#### Global Shared Circuit Breaker

- **Pros**: One degraded API affects all clients equally
- **Cons**: Complex synchronization, false positives, hard to test, multi-tenant issues
- **Why not chosen**: Per-client is simpler and safer

#### Default-Enabled Circuit Breaker

- **Pros**: Safer defaults for production
- **Cons**: Breaking change, unexpected behavior, users may not understand
- **Why not chosen**: Backward compatibility required

### Cache Degradation Alternatives

#### Silent Failure (No Logging)

- **Pros**: Zero noise, no alert fatigue
- **Cons**: Cache problems invisible, debugging impossible, performance issues unnoticed
- **Why not chosen**: Silent failures hide real problems

#### Raise to Caller

- **Pros**: User knows exactly when cache fails, custom handling
- **Cons**: Breaks user code on cache failure, violates "cache is optimization"
- **Why not chosen**: Cache is optional; failures shouldn't propagate

#### Log at ERROR Level

- **Pros**: High visibility, triggers alerts
- **Cons**: ERROR implies application failure, creates alert fatigue, overstates severity
- **Why not chosen**: Cache failures are not application errors

#### SDK-Level Circuit Breaker for Cache

- **Pros**: Prevents repeated failures, faster when cache down
- **Cons**: Complexity, state management, may disable too aggressively, conflicts with provider circuit breakers
- **Why not chosen**: Cache providers implement own circuit breakers

## Consequences

### Positive

**Circuit Breaker**:
- Protection against cascading failures (opt-in)
- Fast failure when service known-bad
- Automatic recovery detection
- Backward compatible
- Clean separation of concerns
- Observable via event hooks

**Cache Degradation**:
- SDK continues working when cache fails
- Warnings and metrics provide visibility
- Simple implementation (no retry/circuit complexity)
- Exception details in logs
- Consistent pattern for all cache operations

**Demo Scripts**:
- Users see helpful error messages
- Clear guidance on recovery actions
- Professional error handling examples

### Negative

**Circuit Breaker**:
- Additional configuration option
- Users must explicitly enable
- Per-client scope may not fit all use cases
- Additional exception type (`CircuitBreakerOpenError`)

**Cache Degradation**:
- Log volume during sustained failures
- Metric dependency for full observability
- No automatic recovery (each call retries)

### Neutral

**Circuit Breaker**:
- State not persisted across process restarts
- No metrics export (future work)
- Recovery is time-based only (no health checks)

**Cache Degradation**:
- Minimal overhead (try/except is cheap)
- Standard exception handling pattern

## Compliance

### Enforcement

1. **Circuit Breaker**:
   - [ ] `CircuitBreakerConfig` with `enabled=False` default
   - [ ] Circuit breaker check in `AsyncHTTPClient.request()`
   - [ ] Unit tests for all state transitions
   - [ ] Event hooks: `on_state_change`, `on_failure`, `on_success`

2. **Cache Degradation**:
   - [ ] Try/except in `_cache_get` helper
   - [ ] Try/except in `_cache_set` helper
   - [ ] Try/except in `_cache_invalidate` helper
   - [ ] Metric increments for cache operations
   - [ ] Unit tests for failure scenarios
   - [ ] Integration test with mock failing cache

3. **Documentation**:
   - [ ] README section on resilience patterns
   - [ ] Cache degradation behavior documented
   - [ ] Circuit breaker configuration examples
   - [ ] Demo scripts with graceful error handling

### Testing

- Circuit breaker transitions through all states correctly
- Circuit opens after failure threshold reached
- Circuit recovers via half-open probes
- Cache failures return None without raising
- Cache failures logged at WARNING level
- Metrics incremented on cache errors
- Demo scripts handle common error scenarios gracefully
