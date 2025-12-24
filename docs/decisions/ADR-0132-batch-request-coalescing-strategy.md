# ADR-0132: Batch Request Coalescing Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-24
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-CACHE-LIGHTWEIGHT-STALENESS, TDD-CACHE-LIGHTWEIGHT-STALENESS, ADR-0010 (Batch Chunking Strategy), ADR-0018 (Batch Modification Checking)

## Context

The lightweight staleness check feature requires batching multiple expired cache entries into single API calls for efficiency. Without coalescing, each expired entry would trigger an individual `GET /tasks/{gid}?opt_fields=modified_at` request, negating the bandwidth savings of lightweight checks.

### Problem Statement

When multiple cache entries expire within a short time window (common in DataFrame operations where many tasks are accessed in rapid succession), the system needs to:

1. **Collect** multiple staleness check requests
2. **Batch** them into optimal groups
3. **Execute** efficiently via Asana Batch API
4. **Distribute** results back to original callers

### Forces at Play

| Force | Description |
|-------|-------------|
| **Latency** | Coalescing window adds wait time before check executes |
| **Efficiency** | Larger batches mean fewer API calls |
| **Memory** | Unbounded batches could consume excessive memory |
| **Responsiveness** | Single requests shouldn't wait indefinitely for batch companions |
| **Asana Limits** | Batch API limited to 10 actions per request |
| **Concurrent Callers** | Multiple async callers may request same GID |

### Key Questions

1. **How long** should the coalescing window be?
2. **How large** should batches be allowed to grow?
3. **When** should batches flush immediately (without waiting)?
4. **How** to handle duplicate GID requests from concurrent callers?

## Decision

**Implement time-bounded coalescing with a 50ms default window, 100-entry maximum batch size, and immediate flush on max batch reached.**

### Specific Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Coalescing Window | 50ms default | Balances latency vs batching efficiency |
| Max Batch Size | 100 entries | Memory-bounded, practical for most workloads |
| Immediate Flush | At max batch (100) | Prevents unbounded wait for large bursts |
| GID Deduplication | Within same batch | Avoids duplicate API calls for same entity |
| Timer Mechanism | asyncio.Task with sleep | Standard async pattern |
| Chunk Size | 10 (Asana limit) | Per ADR-0010 |

### Coalescing Algorithm

```python
class RequestCoalescer:
    """Batches staleness check requests within a time window.

    Algorithm:
    1. First request starts 50ms timer
    2. Subsequent requests join pending batch
    3. Batch flushes when:
       a. Timer expires (50ms)
       b. Max batch size reached (100)
    4. Results distributed to all waiting callers
    5. Same GID requested multiple times = single API call, shared result
    """

    async def request_check_async(self, entry: CacheEntry) -> str | None:
        async with self._lock:
            gid = entry.key

            # Deduplication: if GID already pending, reuse its future
            if gid in self._pending:
                existing_entry, existing_future = self._pending[gid]
                return await existing_future

            # Create new future for this request
            future: asyncio.Future[str | None] = asyncio.get_event_loop().create_future()
            self._pending[gid] = (entry, future)

            # Start timer on first request
            if self._timer_task is None or self._timer_task.done():
                self._timer_task = asyncio.create_task(self._timer_flush())

            # Immediate flush if max batch reached
            if len(self._pending) >= self.max_batch:
                await self._flush_batch()

        return await future

    async def _timer_flush(self) -> None:
        """Wait for window, then flush."""
        await asyncio.sleep(self.window_ms / 1000)
        async with self._lock:
            if self._pending:
                await self._flush_batch()
```

### Flush Flow

```
Request arrives
      |
      v
+------------------+
| Is GID pending?  |
+------------------+
      |
   +--+--+
   |     |
  YES    NO
   |     |
   v     v
Reuse   Add to pending
future  Start timer if needed
   |     |
   +--+--+
      |
      v
+----------------------+
| Is pending >= 100?   |
+----------------------+
      |
   +--+--+
   |     |
  YES    NO
   |     |
   v     v
Flush   Wait for timer
now     (50ms max)
   |     |
   +-----+
      |
      v
Execute batch check
Distribute results
Clear pending
```

## Rationale

### Why 50ms Window?

| Window | Batching Potential | Added Latency | Use Case |
|--------|-------------------|---------------|----------|
| 10ms | Low | Minimal | Low-latency single operations |
| **50ms** | **Medium-High** | **Acceptable** | **DataFrame refresh, parallel access** |
| 100ms | High | Noticeable | Extreme batch optimization |
| 250ms | Very High | Poor UX | Not recommended |

50ms provides good batching efficiency (typical DataFrame operations complete in 100-500ms, so 50ms is a small fraction) while keeping added latency imperceptible for interactive use.

### Why 100 Max Batch?

| Max Batch | Memory | Chunks | Latency Risk |
|-----------|--------|--------|--------------|
| 50 | Low | 5 | Low |
| **100** | **Medium** | **10** | **Medium** |
| 500 | High | 50 | High |
| Unlimited | Unbounded | Many | Very High |

100 entries translates to 10 Asana batch requests (10 actions each). This is:
- Sufficient for most DataFrame operations (typical project: 500-3000 tasks)
- Memory-bounded (~100KB for 100 CacheEntry references)
- Reasonable processing time (~1-2s for 10 sequential batch calls)

### Why Immediate Flush at Max?

Without immediate flush, a burst of 200+ requests would:
1. First 100 requests wait for timer (50ms)
2. Timer fires, first 100 processed
3. Remaining 100+ wait for NEW timer (another 50ms)
4. Total wait: 100ms+ for later requests

With immediate flush:
1. First 100 requests cause immediate flush (0ms wait)
2. Next batch starts fresh timer
3. Better latency distribution

### Why GID Deduplication?

Concurrent async operations may request the same task multiple times:

```python
# Example: parallel attribute access
async def process_tasks(gids):
    # These run concurrently, may check same GIDs
    results = await asyncio.gather(
        *[client.tasks.get_async(gid) for gid in gids]
    )
```

Without deduplication:
- Same GID could appear multiple times in batch
- Wasted API calls
- Inconsistent results if entity changes mid-batch

With deduplication:
- Each GID appears once in batch
- Single API call per unique GID
- All callers for same GID get same result

## Alternatives Considered

### Alternative 1: No Coalescing (Individual Requests)

**Description**: Each expired entry triggers immediate lightweight check.

**Pros**:
- Simplest implementation
- Zero added latency
- No batching complexity

**Cons**:
- No bandwidth savings from batching
- Rate limit risk under heavy load
- Defeats purpose of lightweight checks

**Why not chosen**: Batching is fundamental to the efficiency gains of lightweight checks. Without batching, individual GET requests may exceed rate limits and provide minimal benefit over full fetches.

### Alternative 2: Count-Based Batching (No Time Window)

**Description**: Batch flushes only when reaching N entries, with timeout fallback.

```python
# Flush when batch reaches 10 OR timeout after 5s
if len(pending) >= 10:
    flush()
elif time_since_first > 5:
    flush()
```

**Pros**:
- Optimal batch sizes always
- Simpler timing logic
- Efficient for high-volume scenarios

**Cons**:
- Single request waits up to 5s for batch companions
- Poor latency for low-volume scenarios
- Unpredictable wait times

**Why not chosen**: Time-bounded coalescing provides predictable latency (max 50ms wait) regardless of request volume.

### Alternative 3: Adaptive Window (Dynamic Timing)

**Description**: Adjust window based on request rate.

```python
# More requests = shorter window
if request_rate > 100/s:
    window = 20ms
elif request_rate > 10/s:
    window = 50ms
else:
    window = 100ms
```

**Pros**:
- Optimal for all traffic patterns
- Automatic tuning
- Balances latency and efficiency

**Cons**:
- Complex implementation
- Requires rate tracking
- Harder to reason about behavior
- Over-engineered for current needs

**Why not chosen**: Fixed 50ms window with configurable override is simpler and sufficient. Adaptive tuning can be added later if needed.

### Alternative 4: Leader-Based Batching

**Description**: First request becomes "leader" that waits and executes batch.

```python
# First request in batch executes; others attach
async def request(gid):
    if no_pending_batch:
        become_leader()
        wait(50ms)
        execute_batch()
        notify_followers(results)
    else:
        attach_to_leader()
        wait_for_results()
```

**Pros**:
- Clear ownership of batch execution
- Natural synchronization
- Common pattern in distributed systems

**Cons**:
- Complex leader election
- What if leader fails/times out?
- Harder to implement correctly

**Why not chosen**: asyncio Task-based coalescing is simpler and equally effective for single-process scenarios.

## Consequences

### Positive

1. **Efficient Batching**: Multiple requests combined into single batch check
2. **Predictable Latency**: Max 50ms added wait (configurable)
3. **Memory-Bounded**: 100-entry limit prevents unbounded growth
4. **Deduplication**: Same GID checked once, results shared
5. **Responsive**: Immediate flush at max prevents long waits for large bursts

### Negative

1. **Added Latency**: 0-50ms wait for first request in batch
2. **Complexity**: Async coordination requires careful locking
3. **Debugging**: Batch timing can complicate issue diagnosis
4. **Process Restart**: Pending batch lost on crash

### Neutral

1. **Configurable**: Window and max batch can be tuned per deployment
2. **Observable**: Metrics for batch size, window utilization
3. **Testable**: Clear flush triggers enable deterministic testing

## Compliance

### How This Decision Will Be Enforced

1. **Code Review**: Changes to coalescing logic require ADR reference
2. **Unit Tests**: Test window timing, max batch, deduplication
3. **Integration Tests**: Validate batch efficiency under load
4. **Metrics**: Monitor batch sizes and window utilization

### Configuration

```python
@dataclass(frozen=True)
class StalenessCheckSettings:
    """Staleness check configuration.

    Per ADR-0132: Configurable coalescing parameters.
    """
    enabled: bool = True
    base_ttl: int = 300
    max_ttl: int = 86400
    coalesce_window_ms: int = 50  # Per ADR-0132
    max_batch_size: int = 100     # Per ADR-0132
```

### Code Location

```python
# /src/autom8_asana/cache/coalescer.py

@dataclass
class RequestCoalescer:
    """Batches staleness check requests within time window.

    Per ADR-0132: 50ms default window, 100 max batch, immediate flush at max.
    """
    window_ms: int = 50  # Per ADR-0132
    max_batch: int = 100  # Per ADR-0132
    checker: LightweightChecker

    # ... implementation ...
```

### Logging

```python
# Batch flush event
logger.debug(
    "coalesce_batch_flush",
    extra={
        "batch_size": len(pending),
        "unique_gids": len(set(gid for gid, _ in pending)),
        "coalesce_window_ms": self.window_ms,
        "flush_trigger": "timer" | "max_batch",
        "chunk_count": (len(pending) + 9) // 10,
    },
)
```

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `coalesce_batch_size` | Histogram | Entries per batch |
| `coalesce_window_utilization_ms` | Histogram | Actual wait time |
| `coalesce_flush_trigger` | Counter by label | timer vs max_batch |
| `coalesce_dedup_count` | Counter | Duplicate GID requests avoided |
