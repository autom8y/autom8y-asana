# ADR-0127: Cache Graceful Degradation Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-22
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md), [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md), ADR-0021, ADR-0079

## Context

Cache operations can fail for various reasons:
- Redis connection lost
- Memory exhaustion (InMemory provider at max_size)
- Deserialization errors (corrupt cache entry)
- Network timeouts
- Permission errors

When cache fails, the SDK must continue functioning. The Asana API is the source of truth; cache is an optimization layer. Cache failures should not prevent users from completing their work.

Per PRD-CACHE-INTEGRATION NFR-DEGRADE-001 through NFR-DEGRADE-004:
- Cache failures must log warnings without raising exceptions
- Redis unavailable must fall back gracefully
- Corrupt cache entries must be treated as misses
- Operations must succeed even if caching fails

**The key question**: What strategy should we use when cache operations fail?

Forces at play:
- User-facing operations must not fail due to cache
- Operations should be debuggable (failures visible in logs)
- Metrics should track cache health
- Silent failures hide problems
- Noisy logging creates alert fatigue
- Performance should not degrade significantly during failures

## Decision

We will use **logged warning with metric increment** for all cache failures:

```python
def _cache_get(self, key: str, entry_type: EntryType) -> CacheEntry | None:
    """Check cache with graceful degradation."""
    if self._cache is None:
        return None

    try:
        entry = self._cache.get_versioned(key, entry_type)
        if entry and not entry.is_expired():
            # Metric: cache hit
            return entry
        # Metric: cache miss (expired or not found)
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
        return None  # Treat as cache miss

def _cache_set(self, key: str, data: dict, entry_type: EntryType, ttl: int | None = None) -> None:
    """Store in cache with graceful degradation."""
    if self._cache is None:
        return

    try:
        entry = CacheEntry(key=key, data=data, entry_type=entry_type, ...)
        self._cache.set_versioned(key, entry)
        # Metric: cache write
    except Exception as exc:
        # Graceful degradation: log and continue
        logger.warning(
            "Cache set failed for %s (key=%s): %s",
            entry_type.value,
            key,
            exc,
        )
        # Metric: cache error
        # Operation continues - data was fetched from API successfully
```

Key behaviors:
1. **Catch all exceptions**: Use bare `except Exception` to catch any failure
2. **Log at WARNING**: Not ERROR (cache is optional), not DEBUG (needs visibility)
3. **Return gracefully**: `_cache_get` returns `None` (miss), `_cache_set` returns (no-op)
4. **Increment metric**: Track error rate for monitoring
5. **Continue execution**: Caller proceeds as if cache was not available

## Rationale

### Why WARNING Level (Not ERROR or DEBUG)?

| Level | Pros | Cons |
|-------|------|------|
| DEBUG | Low noise | Invisible in production |
| INFO | Visible | Too noisy for routine failures |
| **WARNING** | Visible, actionable | May trigger alerts if frequent |
| ERROR | High visibility | Overstates severity (SDK still works) |

**WARNING** is correct because:
- Cache failure is not an error in the application
- It indicates suboptimal performance (worth investigating)
- Standard log aggregators surface WARNINGs
- Repeated warnings indicate infrastructure issue

### Why Catch All Exceptions?

```python
except Exception as exc:
```

We catch broadly because:
- Cache providers may raise any exception type
- Redis: `redis.exceptions.ConnectionError`, `redis.exceptions.TimeoutError`
- InMemory: `MemoryError`, `KeyError`, `TypeError`
- Unknown providers: Any exception
- We cannot enumerate all possible failures

We do NOT catch `BaseException` because:
- `KeyboardInterrupt` should propagate
- `SystemExit` should propagate
- These indicate intentional termination

### Why Log the Exception Details?

```python
logger.warning("Cache get failed for %s (key=%s): %s", entry_type.value, key, exc)
```

Including in the log:
- **entry_type**: Which cache operation failed (TASK, SUBTASKS)
- **key**: Which entity was affected (task GID)
- **exc**: What went wrong (connection refused, timeout)

This enables:
- Filtering logs by entry type
- Correlating with specific tasks
- Diagnosing root cause

### Why Return None (Not Raise)?

```python
return None  # Treat as cache miss
```

Returning `None` instead of raising because:
- Caller expects `CacheEntry | None` return type
- `None` means cache miss, which is handled
- API fallback path already exists for misses
- No code change needed in caller

### Why Not Retry on Failure?

We considered automatic retry:
```python
for attempt in range(3):
    try:
        return self._cache.get_versioned(key, entry_type)
    except Exception:
        if attempt == 2:
            raise
        time.sleep(0.1)
```

We rejected this because:
- Retries add latency to every failure
- Three failures = 300ms+ added latency
- Cache miss path (API call) is faster than retrying broken cache
- Circuit breaker in provider handles transient failures

### Why Track Metrics?

```python
# Metric: cache error
self._observability.increment("cache.errors", tags={"entry_type": entry_type.value})
```

Metrics enable:
- Alerting on error rate thresholds
- Dashboards showing cache health
- Capacity planning (miss rate → API load)
- SLA monitoring

### Why Different Handling for Get vs Set?

Both use same strategy, but semantic difference:

**Cache Get Failure**:
- Return `None` (cache miss)
- Caller will fetch from API
- User gets correct (fresh) data
- Slightly slower response

**Cache Set Failure**:
- Return without storing
- Next request will re-fetch from API
- User unaffected (this request already has data)
- Future requests slightly slower until cache works

Both cases:
- Log warning
- Increment metric
- Continue execution

## Alternatives Considered

### Alternative 1: Silent Failure (No Logging)

- **Description**: Catch exceptions silently, return None/continue:
  ```python
  except Exception:
      return None  # Silent
  ```
- **Pros**:
  - Zero noise in logs
  - No alert fatigue
  - Simplest implementation
- **Cons**:
  - Cache problems invisible
  - Debugging impossible
  - Performance issues go unnoticed
- **Why not chosen**: Silent failures hide real problems. We need visibility into cache health.

### Alternative 2: Raise to Caller

- **Description**: Let cache exceptions propagate to the SDK user:
  ```python
  # No try/except - let it raise
  entry = self._cache.get_versioned(key, entry_type)
  ```
- **Pros**:
  - User knows exactly when cache fails
  - Can implement custom handling
  - No hidden behavior
- **Cons**:
  - Breaks user code on cache failure
  - User must handle cache exceptions
  - Violates "cache is optimization" principle
- **Why not chosen**: Cache is optional enhancement. Failures should not propagate to users.

### Alternative 3: Log at ERROR Level

- **Description**: Log cache failures as errors:
  ```python
  logger.error("Cache operation failed: %s", exc)
  ```
- **Pros**:
  - High visibility
  - Triggers error alerts
  - Unmissable
- **Cons**:
  - ERROR implies application failure
  - Creates alert fatigue (cache flapping)
  - Overstates severity
- **Why not chosen**: Cache failures are not application errors. SDK continues functioning correctly.

### Alternative 4: Metric-Only (No Logging)

- **Description**: Increment metrics but don't log:
  ```python
  except Exception:
      self._metrics.increment("cache.errors")
      return None  # No log
  ```
- **Pros**:
  - Clean logs
  - Metrics capture trends
  - Alerting via metrics
- **Cons**:
  - No request-level debugging
  - Metrics may not be configured
  - Exception details lost
- **Why not chosen**: Logs provide request-level debugging that metrics cannot. Both are valuable.

### Alternative 5: Circuit Breaker Pattern

- **Description**: Stop trying cache after N failures:
  ```python
  if self._cache_circuit_open:
      return None  # Skip cache entirely

  try:
      return self._cache.get_versioned(key, entry_type)
  except Exception:
      self._cache_failures += 1
      if self._cache_failures > 5:
          self._cache_circuit_open = True
      return None
  ```
- **Pros**:
  - Prevents repeated failures
  - Faster response when cache is down
  - Reduces load on failing cache
- **Cons**:
  - Adds complexity
  - Circuit state management needed
  - May disable cache too aggressively
  - Requires recovery mechanism
- **Why not chosen**: Cache providers (especially Redis) implement their own circuit breakers. SDK-level circuit breaker would be redundant and may conflict.

## Consequences

### Positive

- **Resilient**: SDK continues working when cache fails
- **Observable**: Warnings and metrics provide visibility
- **Simple**: No complex retry/circuit breaker logic
- **Debuggable**: Exception details in logs
- **Consistent**: Same pattern for all cache operations

### Negative

- **Log volume**: Sustained cache failure generates many warnings
- **Metric dependency**: Full observability requires metric setup
- **No automatic recovery**: Each call retries (no circuit breaker)

### Neutral

- **Performance**: Minimal overhead (try/except is cheap)
- **Code pattern**: Standard exception handling

## Compliance

How do we ensure this decision is followed?

1. **Code review**: All cache operations must use try/except pattern
2. **Linting**: Consider custom lint rule for unhandled cache calls
3. **Testing**: Unit tests verify graceful degradation
4. **Monitoring**: Alert on cache error rate exceeding threshold

## Implementation Checklist

- [ ] Implement try/except in `_cache_get` helper
- [ ] Implement try/except in `_cache_set` helper
- [ ] Implement try/except in `_cache_invalidate` helper
- [ ] Add metric increments for cache operations
- [ ] Add unit tests for failure scenarios
- [ ] Add integration test with mock failing cache
- [ ] Document degradation behavior in user guide
- [ ] Set up alerting on cache error rate
