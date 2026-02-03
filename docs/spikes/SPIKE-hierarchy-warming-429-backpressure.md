# SPIKE: Hierarchy-Warming 429 Backpressure Audit

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Complete |
| **Date** | 2026-02-03 |
| **Trigger** | 145 transient 429s during contact entity cold-start |
| **Scope** | Research only (no production code) |

---

## 1. Question

Why do 145 HTTP 429 responses occur during hierarchy warming (`put_batch_async(warm_hierarchy=True)`) despite internal rate limiting and concurrency controls?

## 2. Context

The large-section-resilience paced pagination **eliminated cost-based 429s** during paginated section fetches (22,836 rows, 0 pagination throttle errors). However, the hierarchy warming phase that runs after task accumulation produced 145 transient 429s from individual `GET /tasks/{gid}` requests for parent task resolution.

## 3. Findings

### 3.1 Request Path Trace

```
ProgressiveProjectBuilder._fetch_and_persist_section()
  └─ self._populate_store_with_tasks(tasks)           # 22,818 tasks
       └─ UnifiedTaskStore.put_batch_async(warm_hierarchy=True)
            │
            ├─ Phase 1: Immediate parent fetches
            │   └─ asyncio.gather(*[_fetch_immediate_parent(gid) for gid in 2,233 parents])
            │       └─ per-fetch: async with hierarchy_semaphore(10)
            │           └─ tasks_client.get_async(gid)
            │               └─ AsanaHttpClient._request()
            │                   └─ async with read_semaphore(50)
            │                       └─ rate_limiter.acquire()  # token bucket: 1500/60s
            │                           └─ httpx GET /tasks/{gid}
            │
            └─ Phase 2: Ancestor warming (warm_ancestors_async)
                └─ Per depth level: _gather_with_limit(coroutines, semaphore=hierarchy_sem(10))
                    └─ _fetch_parent(gid) → tasks_client.get_async(gid)
                        └─ same HTTP pipeline as above
```

### 3.2 Backpressure Mechanism Inventory

| Layer | Mechanism | Limit | Scope |
|-------|-----------|-------|-------|
| **UnifiedStore** | `_hierarchy_semaphore` | 10 concurrent | Per-store instance; gates immediate parent fetches and ancestor warming |
| **HierarchyWarmer** | `_DEFAULT_MAX_CONCURRENT` | 5 concurrent | Default, but overridden to 10 by `UnifiedStore.hierarchy_concurrency` |
| **AsanaHttpClient** | `_read_semaphore` | 50 concurrent | All GET requests (pagination + hierarchy + any other reads) |
| **AsanaHttpClient** | `_write_semaphore` | 15 concurrent | All mutation requests |
| **AsanaHttpClient** | `TokenBucketRateLimiter` | 1500 tokens / 60s (25/sec avg) | All requests through the HTTP client |
| **AsanaHttpClient** | Retry with backoff | 5 retries, 0.5s base | Per-request; catches 429 and retries |

### 3.3 Concurrency Analysis for CONTACTS Build

**Phase 1: Immediate parent fetches**
- 2,233 unique parent GIDs identified
- All dispatched via `asyncio.gather()` simultaneously
- Gated by `hierarchy_semaphore(10)` -- max 10 in-flight at once
- Each acquires `read_semaphore(50)` -- always available (10 << 50)
- Each acquires 1 token from rate limiter (25 tokens/sec refill)

**Phase 2: Ancestor warming**
- 8,385 ancestor GIDs identified (but most already cached from Phase 1)
- 2,205 actually fetched (cache misses)
- Uses same `hierarchy_semaphore(10)` via `global_semaphore` parameter
- Processes level-by-level with `_gather_with_limit()`

**Effective throughput**: With semaphore=10 and token bucket refilling at 25/sec, the system can burst 10 requests simultaneously then must wait for tokens. The steady-state rate is governed by the token bucket, but bursts within a semaphore batch can exceed Asana's instantaneous tolerance.

### 3.4 Root Cause

**Failure mode: Token bucket burst + concurrent request overlap.**

The token bucket (`max_tokens=1500`) starts full. When 10 requests acquire the semaphore simultaneously:

1. All 10 call `rate_limiter.acquire()` nearly simultaneously
2. The bucket has plenty of tokens (1500 available at start)
3. All 10 tokens are consumed within microseconds
4. 10 HTTP requests fire within the same millisecond
5. Asana's per-second instantaneous limit triggers 429

The token bucket prevents **sustained rate** violations (average ≤25 req/sec) but cannot prevent **burst** violations (10 requests in 1ms). The bucket capacity of 1500 means it never throttles bursts -- it's designed to absorb them.

**Contributing factor**: The `read_semaphore(50)` is irrelevant because the hierarchy semaphore (10) is always the tighter constraint. However, during hierarchy warming, the pagination is also active (paced fetch is running concurrently on the same HTTP client). This means paginated `GET /tasks?section=...` requests share the same rate limiter as hierarchy `GET /tasks/{gid}` requests, reducing the effective token budget available for hierarchy warming.

### 3.5 429 Behavior in Production

The 429s are **handled silently** at the transport layer:

```
AsanaHttpClient._request():
  response.status_code == 429
  → RateLimitError raised
  → retry_waiting (attempt=1, delay=0.48s)
  → retry succeeds on next attempt
  → hierarchy warmer never sees the error
```

The `backoff_event` in the hierarchy warmer was never set because the 429s are caught and retried *inside* `tasks_client.get_async()` before they can propagate. This means the hierarchy warmer's adaptive backoff (`asyncio.sleep(2.0)` on 429) is **dead code** for transport-retried 429s.

### 3.6 Impact Assessment

| Aspect | Impact |
|--------|--------|
| **Data correctness** | None -- all 2,233 parents and 2,205 ancestors fetched successfully after retries |
| **Build time** | +~30s from retry delays (145 retries × ~0.5s avg backoff) |
| **Rate limit budget** | 145 wasted request slots (145 retries = 290 total requests for 145 tasks) |
| **Risk** | Low -- retries succeed, but consumes rate budget that could delay other concurrent requests |

## 4. Root Cause Hypothesis Confirmed

**Underprovisioned + Leaky abstraction (combination of 2 and 3).**

- The hierarchy semaphore (10) was sized for small sections, not for 22,818-task sections that generate 2,233 unique parent fetches
- The token bucket allows burst starts (1500 tokens available) rather than smoothing request rate
- The retry layer silently handles 429s, masking the burst problem from the hierarchy warmer's own backoff logic

## 5. Minimal Fix Options

### Option A: Reduce hierarchy concurrency to 3 (simplest)

```python
# In unified.py line 73
hierarchy_concurrency: int = 3  # Was 10; reduces burst size
```

**Trade-off**: Slows hierarchy warming proportionally (~3x slower for large sections). For 2,233 parents, changes from ~90s to ~270s.

### Option B: Add inter-request jitter in hierarchy warmer

```python
# In _fetch_parent(), add small delay between requests
async def _fetch_parent(gid, tasks_client, backoff_event):
    await asyncio.sleep(0.05)  # 50ms jitter, spreads 10 concurrent to ~500ms window
    task = await tasks_client.get_async(gid, opt_fields=...)
```

**Trade-off**: Adds 50ms per request but prevents simultaneous burst. 2,233 parents × 50ms / 10 concurrent = ~12s overhead.

### Option C: Sliding window rate limiter (most correct)

Replace token bucket with a sliding-window limiter that enforces per-second limits (e.g., max 20 req/sec) rather than per-minute averages. This prevents burst violations structurally.

**Trade-off**: Requires changing the platform `autom8y_http` rate limiter or wrapping it.

### Option D: Batch hierarchy warming with pacing (mirrors pagination fix)

Apply the same pacing pattern used for pagination: process parents in batches of N with delays between batches. This is the hierarchy analog of the large-section-resilience pacing.

```python
# In put_batch_async, batch the parent_gids_needed
HIERARCHY_BATCH_SIZE = 50
HIERARCHY_BATCH_DELAY = 1.0

for i in range(0, len(parent_gids_needed), HIERARCHY_BATCH_SIZE):
    batch = list(parent_gids_needed)[i:i + HIERARCHY_BATCH_SIZE]
    results = await asyncio.gather(*[_fetch_immediate_parent(gid) for gid in batch])
    if i + HIERARCHY_BATCH_SIZE < len(parent_gids_needed):
        await asyncio.sleep(HIERARCHY_BATCH_DELAY)
```

**Trade-off**: Adds ~44s for CONTACTS (2233 parents / 50 per batch × 1s delay), but completely eliminates 429s. Consistent with established pacing pattern.

### Recommendation

**Option D** (batch pacing) is the recommended fix. It:
- Uses the same pattern already proven by pagination pacing
- Is localized to `put_batch_async()` (single method change)
- Is tunable via constants (batch size, delay)
- Completely eliminates burst violations
- Adds acceptable overhead (~44s on a 427s build)

Option A (reduce to 3) is the quick fix for immediate relief if Option D is deferred.

## 6. Follow-Up Actions

| Action | Priority | Effort |
|--------|----------|--------|
| Implement Option D (batch pacing for hierarchy warming) | P2 | SCRIPT (~30 LOC) |
| Audit `backoff_event` dead code in hierarchy warmer | P3 | SCRIPT (~10 LOC) |
| Consider sliding-window rate limiter for platform | P4 | MODULE |
| Add 429 counter metric to CloudWatch dashboard | P3 | SCRIPT |
