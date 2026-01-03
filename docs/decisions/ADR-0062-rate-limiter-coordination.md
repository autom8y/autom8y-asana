---
artifact_id: ADR-0062
title: "Client-Scoped Shared Rate Limiter for Coordinated Request Throttling"
created_at: "2026-01-03T16:00:00Z"
author: architect
status: accepted
context: "Parallel section fetches in autom8_asana generate 80+ retry warnings because each concurrent request path has its own rate limiter instance. The aggregate request rate exceeds Asana's 1500 req/60s limit, triggering 429 errors and exponential backoff cascades."
decision: "Create a single TokenBucketRateLimiter instance per AsanaClient and inject it into the HTTP client. All requests through that client share the same rate limiter, preventing uncoordinated bursts."
consequences:
  - type: positive
    description: "Parallel section fetches (8+ concurrent) stay within 1500 req/60s limit"
  - type: positive
    description: "Retry warnings reduced from 80+ to <10 during bulk operations"
  - type: positive
    description: "No 429 errors during parallel fetch of 2614+ tasks"
  - type: positive
    description: "Rate limiter utilization improves from ~60% to >90%"
  - type: negative
    description: "Rate limiter contention may introduce minor latency during extreme concurrency"
    mitigation: "Token bucket is O(1) acquire, contention overhead is negligible"
  - type: negative
    description: "All requests through single client now share token budget"
    mitigation: "This is the desired behavior - coordinated throttling prevents overload"
  - type: neutral
    description: "Multiple AsanaClient instances still have separate rate limiters"
related_artifacts:
  - PRD-asana-http-migration-001
  - TDD-asana-http-migration-001
  - ADR-0061
tags:
  - rate-limiting
  - thundering-herd
  - concurrency
  - performance
schema_version: "1.0"
---

# ADR-0062: Client-Scoped Shared Rate Limiter for Coordinated Request Throttling

## Context

The autom8_asana SDK supports parallel fetching of tasks across project sections via `ParallelSectionFetcher`. This pattern uses `asyncio.Semaphore` to limit concurrent section fetches to 8, but does not coordinate HTTP-level rate limiting.

### The Problem

Each `AsyncHTTPClient` instance creates its own `TokenBucketRateLimiter`:

```python
class AsyncHTTPClient:
    def __init__(self, config, auth_provider, logger):
        # Creates NEW rate limiter per instance
        self._rate_limiter = TokenBucketRateLimiter(
            max_tokens=config.rate_limit.max_requests,  # 1500
            refill_period=config.rate_limit.window_seconds,  # 60
        )
```

When `ParallelSectionFetcher` runs with 8 concurrent section fetches, each section may paginate 10-20 times. The section-level semaphore controls section concurrency but not HTTP request concurrency:

```
Section 1: 15 paginated requests
Section 2: 12 paginated requests
Section 3: 18 paginated requests
...
Section 8: 14 paginated requests

Total: 100+ concurrent HTTP requests possible
```

Since all requests share the same `AsyncHTTPClient` instance and the same rate limiter, this should work. However, the current implementation creates rate limiters per-client-instance, and in high-concurrency scenarios, the token bucket cannot coordinate the burst effectively.

### Root Cause Analysis

The real issue is that:
1. Rate limiter is created inside `AsyncHTTPClient.__init__()`
2. Multiple code paths may create `AsyncHTTPClient` instances
3. Lack of explicit ownership means rate limiting is fragmented

### Observed Behavior

During a 2614-task parallel fetch:
- 80+ retry warnings logged
- 429 errors trigger exponential backoff
- Total fetch time: 45-60s (should be <30s)
- Rate limit utilization: ~60% (tokens refill while waiting for backoff)

## Decision

We will create a **single `TokenBucketRateLimiter` instance at `AsanaClient` scope** and inject it into the HTTP client.

### Ownership Model

```
AsanaClient (owns rate limiter)
    |
    +-- _shared_rate_limiter: TokenBucketRateLimiter
    |       |
    |       +-- 1500 tokens / 60 seconds
    |       +-- Shared by ALL requests through this client
    |
    +-- AsanaHttpClient (uses injected rate limiter)
    |       |
    |       +-- Does NOT create its own limiter
    |       +-- Passes to Autom8yHttpClient
    |
    +-- TasksClient, SectionsClient, etc.
            |
            +-- All use same AsanaHttpClient
            +-- All requests go through same rate limiter
```

### Implementation

```python
class AsanaClient:
    def __init__(self, ...):
        # Create SHARED rate limiter at client scope
        self._shared_rate_limiter = TokenBucketRateLimiter(
            config=RateLimiterConfig(
                max_tokens=self._config.rate_limit.max_requests,
                refill_period=float(self._config.rate_limit.window_seconds),
            ),
            logger=self._log_provider,
        )

        # Create SHARED circuit breaker at client scope
        self._shared_circuit_breaker = CircuitBreaker(
            config=CircuitBreakerConfig(
                enabled=self._config.circuit_breaker.enabled,
                failure_threshold=self._config.circuit_breaker.failure_threshold,
                recovery_timeout=self._config.circuit_breaker.recovery_timeout,
                half_open_max_calls=self._config.circuit_breaker.half_open_max_calls,
            ),
            logger=self._log_provider,
        )

        # Inject shared instances into HTTP client
        self._http = AsanaHttpClient(
            config=self._config,
            auth_provider=self._auth_provider,
            rate_limiter=self._shared_rate_limiter,      # INJECTED
            circuit_breaker=self._shared_circuit_breaker,  # INJECTED
            logger=self._log_provider,
        )
```

### Scope Justification

**Why client-scoped, not global?**

1. **Isolation**: Multiple `AsanaClient` instances (different tokens, different workspaces) should have independent rate limits
2. **Testing**: Unit tests can create isolated clients without global state
3. **Multi-tenancy**: Services handling multiple Asana accounts need per-account limits

**Why not request-scoped?**

1. Defeats the purpose - each request would have its own limiter
2. No coordination between concurrent requests

**Why not session-scoped (e.g., per-thread)?**

1. asyncio is single-threaded by design
2. Thread-local storage doesn't make sense for async code
3. Would require complex lifecycle management

## Consequences

### Positive

1. **Coordinated throttling**: All concurrent requests share the same token bucket, preventing aggregate rate from exceeding limit.

2. **Fewer 429 errors**: Proactive rate limiting waits for tokens before sending, rather than reactive backoff after rejection.

3. **Reduced retry warnings**: Fewer 429s means fewer retries, reducing log noise from 80+ to <10.

4. **Better utilization**: Tokens are consumed smoothly rather than in bursts followed by backoff delays.

5. **Predictable performance**: Parallel fetch completes in consistent time (<30s) rather than variable time (45-60s with backoff).

### Negative

1. **Potential contention**: High concurrency (100+ simultaneous requests) may see minor latency from lock acquisition in token bucket.

   **Mitigation**: Token bucket acquire is O(1) - just check/decrement counter. Lock hold time is microseconds.

2. **Shared budget**: A misbehaving code path could exhaust tokens, starving other paths.

   **Mitigation**: This is the correct behavior - all requests ARE subject to the same API limit. Better to queue than to 429.

### Neutral

1. **Multiple clients separate**: Two `AsanaClient` instances have separate rate limiters. This matches the mental model (different clients, different limits).

2. **No cross-process coordination**: If running multiple processes (e.g., parallel workers), each has its own rate limiter.

   **Note**: Cross-process coordination would require distributed rate limiting (Redis-backed), which is explicitly out of scope per PRD.

## Alternatives Considered

### Alternative A: Global Singleton Rate Limiter

Create a module-level rate limiter shared by all `AsanaClient` instances.

```python
# autom8_asana/_global.py
_global_rate_limiter = TokenBucketRateLimiter(...)

class AsanaClient:
    def __init__(self):
        self._http = AsanaHttpClient(
            rate_limiter=_global_rate_limiter,  # Global
        )
```

**Rejected because**:
- Conflates separate accounts (different tokens should have separate limits)
- Complicates testing (global state)
- Harder to reason about limit allocation

### Alternative B: Increase Token Bucket Size

Configure larger token bucket to absorb bursts.

```python
# Instead of 1500/60s, use 3000/60s with smoothing
rate_limiter = TokenBucketRateLimiter(max_tokens=3000, ...)
```

**Rejected because**:
- Asana's actual limit is 1500/60s - exceeding risks 429s
- Larger bucket allows bigger bursts, not fewer
- Doesn't address coordination problem

### Alternative C: HTTP-Level Semaphore

Add semaphore to limit concurrent in-flight HTTP requests.

```python
class AsyncHTTPClient:
    def __init__(self):
        self._http_semaphore = asyncio.Semaphore(50)  # Max 50 concurrent

    async def request(self, ...):
        async with self._http_semaphore:
            await self._rate_limiter.acquire()
            return await self._client.request(...)
```

**Rejected because**:
- Adds complexity without solving rate coordination
- Semaphore limits concurrency, not rate
- Could actually reduce throughput unnecessarily

### Alternative D: Adaptive Rate Limiting

Dynamically adjust rate based on 429 responses.

```python
async def request(self, ...):
    response = await self._client.request(...)
    if response.status_code == 429:
        self._rate_limiter.reduce_rate(0.8)  # Back off 20%
    else:
        self._rate_limiter.increase_rate(1.1)  # Speed up 10%
```

**Rejected because**:
- Complex to implement correctly
- Still reactive (after 429, not before)
- Asana's limit is well-documented (1500/60s)

## Verification

To verify this decision achieves its goals:

1. **Unit test**: Assert single rate limiter instance across all clients
   ```python
   def test_shared_rate_limiter():
       client = AsanaClient(token=...)
       assert client._http._rate_limiter is client._shared_rate_limiter
   ```

2. **Integration test**: Parallel fetch without 429s
   ```python
   async def test_parallel_fetch_no_429():
       client = AsanaClient(token=...)
       with log_capture() as logs:
           await parallel_section_fetch(2614_tasks)
       assert not any("429" in log for log in logs)
   ```

3. **Benchmark**: Retry warnings < 10
   ```python
   async def test_retry_warning_count():
       with log_capture() as logs:
           await parallel_section_fetch()
       retry_logs = [l for l in logs if "retry" in l.lower()]
       assert len(retry_logs) < 10
   ```

## References

- PRD-ASANA-HTTP-MIGRATION-001: Requirements specifying coordination goals
- TDD-ASANA-HTTP-MIGRATION-001: Technical design with implementation details
- ADR-0061: Companion decision on wrapper strategy
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket): Rate limiting algorithm background
- Asana API Rate Limits: 1500 requests per 60 seconds per PAT
