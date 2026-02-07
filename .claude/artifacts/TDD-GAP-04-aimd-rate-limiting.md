# TDD-GAP-04: AIMD Adaptive Rate Limiting

**Status**: DRAFT
**PRD**: PRD-GAP-04-aimd-rate-limiting (draft)
**Complexity**: SMALL
**Author**: Architect
**Date**: 2026-02-07

---

## 1. Overview

### 1.1 Problem

autom8_asana uses fixed `asyncio.Semaphore` instances (50 for reads, 15 for writes) in `AsanaHttpClient`. When Asana returns a 429 (rate limit), the individual request retries with exponential backoff, but the remaining 49 concurrent readers keep firing new requests. The system has no mechanism to reduce aggregate concurrency in response to rate limit signals.

During parallel section fetches (2600+ tasks, 8+ concurrent sections), this causes 429 cascades: each 429 triggers a 30-60s Retry-After delay while other requests continue exhausting the rate limit. The result is 80+ retry warnings and 3-5 minute fetch times instead of the expected 45 seconds.

### 1.2 Solution

Replace the fixed `asyncio.Semaphore` instances with `AsyncAdaptiveSemaphore` -- a custom async semaphore that implements AIMD (Additive Increase, Multiplicative Decrease) concurrency control, the same algorithm TCP uses for congestion control:

- **Multiplicative Decrease**: On 429, halve the concurrency window.
- **Additive Increase**: On success, grow the window by 1 (up to the configured maximum).
- **Epoch Coalescing**: Prevent N simultaneous 429s from causing N halvings by stamping each slot with a monotonic epoch.

The two-layer architecture is preserved: the existing `TokenBucketRateLimiter` governs request *rate* (tokens per second), while `AsyncAdaptiveSemaphore` governs *concurrency* (how many in-flight simultaneously). These are complementary, not competing.

### 1.3 Key Design Decisions

1. **Separate read/write AIMD controllers** -- independent `AsyncAdaptiveSemaphore` instances for reads (ceiling 50) and writes (ceiling 15). No cross-pool contamination on 429. (Stakeholder OQ-1)
2. **In-place semaphore replacement** -- swap `_read_semaphore` / `_write_semaphore` inside `AsanaHttpClient.__init__()`. No external wrapper. (Stakeholder OQ-2)
3. **Monotonic epoch coalescing** -- slots stamped at acquire time; `on_reject()` and `on_success()` ignore stale epochs. One halving per cohort. (Stakeholder OQ-4)
4. **`asyncio.Condition` + counter** -- custom primitive, not wrapping `asyncio.Semaphore`, because `asyncio.Semaphore` cannot be resized after construction. (Stakeholder OQ-5)
5. **Cooldown stubbed only** -- config fields, counter, warning log. No actual pause/drain in v1. (Stakeholder OQ-3)
6. **Build locally in autom8_asana** -- see ADR-GAP04-001 below.

### 1.4 PRD Requirement Traceability

| PRD Requirement | TDD Section | Coverage |
|-----------------|-------------|----------|
| FR-001 Adaptive Concurrency Controller | 5.1 AsyncAdaptiveSemaphore | Full |
| FR-002 Backoff Grace Period | 5.1.4 Grace Period | Full |
| FR-003 Integration with AsanaHttpClient | 6. Integration Plan | Full |
| FR-004 Configuration via ConcurrencyConfig | 5.3 AIMDConfig | Full |
| FR-005 Structured Logging | 5.6 Logging Events | Full |
| FR-006 Stats/Introspection API | 5.5 Stats API | Full |
| FR-007 Increase Interval Throttle | 5.1.5 Increase Throttle | Included (SHOULD-HAVE) |
| FR-008 Cooldown Mode | 5.4 Cooldown Stub | Stub only |
| FR-009 Token Bucket Drain | N/A | Deferred |
| NFR-001 No Deadlock | 5.3 AIMDConfig (min_concurrent) | Full |
| NFR-002 No Revocation | 5.1.2 Epoch Mechanics | Full |
| NFR-003 Async Safety | 5.1.1 Internal State | Full |
| NFR-004 Performance | 5.1.1 (O(1) operations) | Full |
| NFR-005 Testability | 5.1.1 (injectable clock) | Full |

---

## 2. Architecture

### 2.1 Two-Layer Design

```
                    +-----------------------+
                    |    AsanaHttpClient     |
                    |       _request()       |
                    +-----------+-----------+
                                |
                    +-----------v-----------+
                    |  TokenBucketRateLimiter|  <-- Layer 1: Rate Gate
                    |  1500 tokens / 60s     |      Controls request RATE
                    |  (shared, existing)    |      "How fast can I send?"
                    +-----------+-----------+
                                |
              +-----------------+-----------------+
              |                                   |
   +----------v----------+           +-----------v---------+
   | AsyncAdaptiveSemaphore|         |AsyncAdaptiveSemaphore|
   | _read_semaphore       |         | _write_semaphore     |
   | ceiling=50, floor=1   |         | ceiling=15, floor=1  |  <-- Layer 2: AIMD Controllers
   | AIMD: halve on 429    |         | AIMD: halve on 429   |      Controls CONCURRENCY
   | +1 on success         |         | +1 on success        |      "How many at once?"
   +----------+----------+           +-----------+---------+
              |                                   |
              +-----------------+-----------------+
                                |
                    +-----------v-----------+
                    |    httpx request      |
                    |  (via platform client) |
                    +-----------------------+
```

### 2.2 Request Flow (After Integration)

```
_request(method, path):
  1. circuit_breaker.check()
  2. select semaphore (read or write)
  3. slot = await semaphore.acquire()        # blocks if at AIMD limit
  4. try:
  5.   await rate_limiter.acquire()           # blocks if out of tokens
  6.   response = await platform_client.request(...)
  7.   if response.status_code == 429:
  8.     slot.reject()                         # AIMD halves window
  9.     retry...
  10.  else:
  11.    slot.succeed()                        # AIMD increments window
  12.    return data
  13. finally:
  14.   slot releases on context exit
```

### 2.3 Component Interactions

```
+------------------+     creates      +--------------------+
|  AsanaHttpClient |----------------->| AsyncAdaptiveSemaphore |
|                  |                  |   (read, ceiling=50)    |
|                  |----------------->| AsyncAdaptiveSemaphore |
|                  |     creates      |   (write, ceiling=15)   |
+--------+---------+                  +-----------+------------+
         |                                        |
         | uses                                   | produces
         v                                        v
+------------------+                  +--------------------+
|  AIMDConfig      |                  |  Slot (ctx mgr)    |
|  (dataclass)     |                  |  .reject()         |
+------------------+                  |  .succeed()        |
                                      +--------------------+
```

---

## 3. Architecture Decision Records

### ADR-GAP04-001: Build Location -- Local vs Platform

**Status**: Accepted

**Context**: The stakeholder asked whether `AsyncAdaptiveSemaphore` should live in `autom8y_platform/sdks/python/autom8y-http` (extending the existing `ConcurrencyController`) or locally in `autom8_asana/transport/`.

The platform already has:
- `ConcurrencyController` in `autom8y-http/src/autom8y_http/concurrency.py` -- a fixed-size `asyncio.Semaphore` wrapper with observability.
- `ConcurrencyControllerProtocol` in `autom8y-http/src/autom8y_http/protocols.py` -- the protocol contract.
- `TokenBucketRateLimiter` -- the rate gate.

**Options Evaluated**:

| Criterion | Platform (autom8y-http) | Local (autom8_asana) |
|-----------|------------------------|----------------------|
| Reusability | High -- other satellites benefit | None -- autom8_asana only |
| Time to ship | Slow -- cross-repo release cycle | Fast -- single repo, atomic commits |
| API design risk | Higher -- must be generic enough | Lower -- can be Asana-specific |
| Protocol compliance | Must satisfy `ConcurrencyControllerProtocol` | Can define its own interface |
| Dependency coupling | Deepens platform coupling (ADR-0063 concern) | Self-contained |
| Testing | Requires platform CI + integration | Local CI only |

**Decision**: **Build locally in `autom8_asana`**, with a forward-compatible interface.

**Rationale**:

1. **Ship speed matters**: GAP-04 is a SMALL complexity item. Cross-repo coordination would triple the effort for no immediate benefit.
2. **AIMD is domain-specific**: The epoch coalescing, grace period, and cooldown stub are Asana API-specific behaviors. A generic platform primitive would either be over-abstracted or under-specified.
3. **Platform protocol does not fit**: `ConcurrencyControllerProtocol.acquire()` yields `None`. AIMD requires yielding a `Slot` with `.reject()` and `.succeed()` methods. Changing the protocol is a breaking change to all platform consumers.
4. **Promotion path exists**: If the AIMD pattern proves valuable for other satellites, the implementation can be promoted to `autom8y-http` with a new `AdaptiveConcurrencyProtocol`. The local implementation serves as a battle-tested prototype.
5. **ADR-0063 already flagged**: The existing `ConcurrencyController` was extracted to the platform without adaptive capabilities. Adding AIMD is a separate, larger design exercise for the platform team.

**Consequences**:
- Positive: Ships in one initiative, no cross-repo coordination.
- Positive: Interface can be optimized for Asana's 429 behavior.
- Negative: Not reusable by other satellites without promotion.
- Negative: Must be maintained locally.
- Mitigated: Module is self-contained (~200 LOC), well-tested, and has a clear promotion path.

---

### ADR-GAP04-002: Rate Gate Assessment -- Is TokenBucketRateLimiter Sufficient?

**Status**: Accepted

**Context**: The stakeholder asked whether the existing `TokenBucketRateLimiter` (1500 tokens / 60s) suffices as the shared rate coordination layer, or whether it needs augmentation.

**Assessment**:

The `TokenBucketRateLimiter` (platform `autom8y-http/src/autom8y_http/rate_limiter.py`) provides:
- `acquire()` -- blocking token acquisition
- `try_acquire()` -- non-blocking probe
- `available_tokens` -- approximate current capacity
- `get_stats()` -- monitoring data
- `asyncio.Lock` protection for async safety
- Monotonic clock for refill timing

**What it does well**:
- Prevents aggregate request rate from exceeding 1500/60s.
- Smooths bursts across all concurrent requests (per ADR-0062).
- Already shared at `AsanaClient` scope.

**What it does NOT do**:
- No drain/release API (FR-009, deferred).
- No awareness of 429 responses -- it is purely proactive.
- No integration with AIMD -- operates independently.

**Decision**: **The existing `TokenBucketRateLimiter` is sufficient for v1. No modifications required.**

**Rationale**:
1. Rate limiting and concurrency control are complementary layers. The token bucket prevents *rate* overload. AIMD prevents *concurrency* overload. Together they provide defense-in-depth.
2. The token bucket is proactive (prevents requests before they cause 429s). AIMD is reactive (adjusts after 429s). These are independent feedback loops.
3. FR-009 (token bucket drain on cooldown) is fully deferred. If cooldown activation shows the token bucket needs drain, that is a future enhancement.
4. The token bucket has no API surface for Asana-specific 429 integration. Adding one would couple the platform primitive to Asana behavior. That coupling does not belong in `autom8y-http`.

**Consequences**:
- Positive: No changes to platform SDK.
- Positive: Clear separation of concerns (rate vs concurrency).
- Risk: After AIMD halves concurrency and requests back off, the token bucket may accumulate tokens during the pause, enabling a burst when concurrency recovers. This is mitigated by AIMD's additive (slow) recovery -- concurrency grows by 1 per success, not instantly.

---

## 4. Existing Code Analysis

### 4.1 Current Semaphore Usage

The semaphores appear in three methods within `AsanaHttpClient`:

| Method | Semaphore Used | Line |
|--------|---------------|------|
| `_request()` | `_read_semaphore` or `_write_semaphore` (by method) | L504 `async with semaphore:` |
| `_request_paginated()` | `_read_semaphore` | L596 `async with semaphore:` |
| `post_multipart()` | `_write_semaphore` | L360 `async with semaphore:` |

**Critical observation**: The semaphore is used inside the retry loop (`while True: async with semaphore:`). This means:
- Each retry attempt re-acquires the semaphore.
- The slot is released before the retry wait.
- A 429-retry does NOT hold a slot during the `_wait_for_retry()` sleep.

This is *correct* behavior -- we want to release the slot during backoff so other requests can proceed. The AIMD integration must preserve this pattern: the Slot is acquired, the request executes, the Slot exits (triggering release + feedback), and on retry the loop re-acquires a new Slot.

### 4.2 ConcurrencyConfig

Located at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py`, lines 168-187:

```python
@dataclass(frozen=True)
class ConcurrencyConfig:
    read_limit: int = 50
    write_limit: int = 15
```

This dataclass is frozen and used by `AsanaConfig`. AIMD parameters will be added here.

### 4.3 Test Compatibility Concern

The existing test `test_creates_concurrency_semaphores` (line 89-90 of `tests/unit/transport/test_asana_http.py`) checks:

```python
assert client._read_semaphore._value == 10
assert client._write_semaphore._value == 5
```

This accesses `asyncio.Semaphore._value`, a CPython internal. The `AsyncAdaptiveSemaphore` replacement must either:
- (a) Provide a `_value` property for backward compatibility, or
- (b) Update this test to use the public stats API.

**Decision**: Option (b) -- update the test to use the public API. Relying on `_value` is fragile and the test was already testing an internal. The new test will use `semaphore.ceiling` and `semaphore.current_limit` properties instead. This is a test-only change that does not violate SC-006 ("all existing transport tests pass without modification") because the test was already testing an internal implementation detail that no longer exists. SC-006 means the *behavior* must not change, not that tests testing removed internals must pass as-is.

**Important**: The SC-006 requirement must be interpreted as: public API behavior is unchanged and *meaningful* existing tests pass. The one test that inspects `_value` must be updated to inspect the equivalent public interface. This is documented here so the principal-engineer is not surprised.

---

## 5. Component Design

### 5.1 AsyncAdaptiveSemaphore

**Module**: `src/autom8_asana/transport/adaptive_semaphore.py`

This is the core primitive. It replaces `asyncio.Semaphore` with a dynamically-sized concurrency controller.

#### 5.1.1 Internal State

```
AsyncAdaptiveSemaphore:
  _config: AIMDConfig                # Immutable configuration
  _window: float                     # Current concurrency window (stored as float for fractional accumulation)
  _in_flight: int                    # Number of currently-held slots
  _epoch: int                        # Monotonic epoch counter (incremented on each decrease)
  _condition: asyncio.Condition      # Notify waiters when slots become available
  _last_decrease_time: float         # Monotonic time of last decrease (for grace period)
  _last_increase_time: float         # Monotonic time of last increase (for increase throttle, FR-007)
  _decrease_count: int               # Lifetime decrease events (for stats)
  _increase_count: int               # Lifetime increase events (for stats)
  _consecutive_rejects: int          # Consecutive 429s (for cooldown stub)
  _clock: Callable[[], float]        # Injectable clock (default: time.monotonic)
  _logger: LoggerProtocol | None     # Structured logger
  _name: str                         # "read" or "write" (for log disambiguation)
```

**Thread safety**: All state mutations occur inside `async with self._condition:` blocks. Since `asyncio.Condition` wraps an `asyncio.Lock`, this provides coroutine-level mutual exclusion. Single event loop, no threading concern.

**Performance**: `acquire()` is O(1) when below the window (lock + compare + increment). `on_reject()` and `on_success()` are O(1) (lock + arithmetic). `notify(1)` wakes at most one waiter to prevent thundering herd.

**Clock injection**: The `_clock` parameter defaults to `time.monotonic` but can be replaced in tests with a controllable clock for deterministic grace period and throttle testing.

#### 5.1.2 Epoch Mechanics

The epoch prevents N simultaneous 429s from triggering N halvings.

**How it works**:

1. When `acquire()` grants a slot, the returned `Slot` carries `slot_epoch = self._epoch`.
2. When `on_reject()` is called (429 received):
   - If `slot_epoch < self._epoch`, this slot was acquired before the most recent decrease. Its feedback is **stale** -- ignore it. Return without modifying state.
   - If `slot_epoch == self._epoch`, this is the first reject in this cohort. Halve the window. Increment `self._epoch`. This invalidates all other in-flight slots from the same cohort.
3. When `on_success()` is called:
   - If `slot_epoch < self._epoch`, this slot was acquired before the most recent decrease. Its feedback is **stale** -- ignore it. We do not want a success from the old (higher) window to undo the decrease.
   - If `slot_epoch == self._epoch`, process as additive increase.

**Example scenario**:

```
epoch=0, window=50, 50 requests in flight

Request A gets 429 -> on_reject(epoch=0):
  epoch=0 == self._epoch=0 -> PROCESS
  window = 50 * 0.5 = 25.0
  self._epoch = 1

Request B gets 429 -> on_reject(epoch=0):
  epoch=0 < self._epoch=1 -> STALE, ignore

Request C succeeds -> on_success(epoch=0):
  epoch=0 < self._epoch=1 -> STALE, ignore

Request D (acquired after decrease) succeeds -> on_success(epoch=1):
  epoch=1 == self._epoch=1 -> PROCESS
  window = min(25.0 + 1.0, 50.0) = 26.0
```

This ensures exactly one halving per burst of 429s, regardless of how many arrive simultaneously.

#### 5.1.3 Acquire / Release Protocol

```python
async def acquire(self) -> Slot:
    """Acquire a concurrency slot, blocking if at the AIMD limit.

    Returns a Slot context manager. The caller MUST use it as:
        async with semaphore.acquire() as slot:
            response = await make_request()
            if response.status_code == 429:
                slot.reject()
            else:
                slot.succeed()

    If neither reject() nor succeed() is called before exit,
    the slot releases without AIMD feedback (silent release).
    This is safe -- it just means no window adjustment for this request.
    """
    async with self._condition:
        while self._in_flight >= int(self._window):
            await self._condition.wait()
        self._in_flight += 1
        return Slot(
            semaphore=self,
            epoch=self._epoch,
        )

async def _release(self) -> None:
    """Release a slot (called by Slot.__aexit__)."""
    async with self._condition:
        self._in_flight -= 1
        self._condition.notify(1)  # Wake ONE waiter, not all
```

**Key design point**: `int(self._window)` -- the window is stored as a float (for fractional accumulation from additive increase) but admission is checked against the integer floor. This matches the stakeholder constraint: "Window stored as float, compared as int."

#### 5.1.4 Grace Period (FR-002)

After a multiplicative decrease, success signals are suppressed for `grace_period_seconds`. This prevents premature recovery while Retry-After delays are still in effect.

```python
async def _on_success(self, slot_epoch: int) -> None:
    async with self._condition:
        if slot_epoch < self._epoch:
            return  # Stale

        now = self._clock()
        if now - self._last_decrease_time < self._config.grace_period_seconds:
            return  # Grace period active, suppress increase

        # ... proceed with additive increase
```

**Default**: `grace_period_seconds = 5.0`. This is conservative -- Asana's Retry-After is typically 30-60s, so a 5s grace period merely prevents the first few successful retries from prematurely growing the window.

#### 5.1.5 Increase Throttle (FR-007, SHOULD-HAVE)

Successive additive increases are throttled to prevent rapid recovery that overshoots.

```python
        if now - self._last_increase_time < self._config.increase_interval_seconds:
            return  # Too soon since last increase

        new_window = min(self._window + self._config.additive_increase, self._config.ceiling)
        # ... log and update
```

**Default**: `increase_interval_seconds = 2.0`. This matches the legacy system's 2.0s minimum between increases. The interval ensures that window growth of +1 every 2s takes ~50 seconds to recover from a halving of window=50 to window=25 -- approximately matching a typical Retry-After period.

#### 5.1.6 Multiplicative Decrease

```python
async def _on_reject(self, slot_epoch: int) -> None:
    async with self._condition:
        if slot_epoch < self._epoch:
            return  # Stale

        old_window = self._window
        self._window = max(
            self._window * self._config.multiplicative_decrease,
            self._config.floor,
        )
        self._epoch += 1
        self._last_decrease_time = self._clock()
        self._decrease_count += 1
        self._consecutive_rejects += 1

        # Cooldown stub check
        if self._consecutive_rejects >= self._config.cooldown_trigger:
            if self._logger:
                self._logger.warning(
                    "aimd_cooldown_threshold_reached",
                    name=self._name,
                    consecutive_rejects=self._consecutive_rejects,
                    cooldown_trigger=self._config.cooldown_trigger,
                    note="cooldown_not_active_in_v1",
                )

        if self._logger:
            level = "warning" if self._window <= self._config.floor else "info"
            log_fn = self._logger.warning if level == "warning" else self._logger.info
            log_fn(
                "aimd_decrease",
                name=self._name,
                before=old_window,
                after=self._window,
                epoch=self._epoch,
                trigger="429",
            )
            if self._window <= self._config.floor:
                self._logger.warning(
                    "aimd_at_minimum",
                    name=self._name,
                    floor=self._config.floor,
                )
```

### 5.2 Slot Context Manager

**Defined in**: `src/autom8_asana/transport/adaptive_semaphore.py` (same module)

```
Slot:
  _semaphore: AsyncAdaptiveSemaphore   # Back-reference for release and feedback
  _epoch: int                          # Epoch at acquire time
  _status: Literal["pending", "rejected", "succeeded", "released"]
```

**Lifecycle**:

```
acquire() -> Slot(status="pending")
  |
  +-- slot.reject()   -> status="rejected",  calls semaphore._on_reject(epoch)
  +-- slot.succeed()  -> status="succeeded", calls semaphore._on_success(epoch)
  |
  __aexit__() -> calls semaphore._release() regardless of status
                 If status still "pending", no AIMD feedback given.
```

**Interface**:

```python
class Slot:
    async def __aenter__(self) -> Slot:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._semaphore._release()

    def reject(self) -> None:
        """Signal 429 received. Triggers multiplicative decrease (if epoch is current)."""
        if self._status != "pending":
            return  # Idempotent
        self._status = "rejected"
        # Schedule the async callback
        asyncio.get_event_loop().create_task(self._semaphore._on_reject(self._epoch))

    def succeed(self) -> None:
        """Signal success. Triggers additive increase (if epoch is current)."""
        if self._status != "pending":
            return  # Idempotent
        self._status = "succeeded"
        asyncio.get_event_loop().create_task(self._semaphore._on_success(self._epoch))
```

**Design note on sync vs async**: `reject()` and `succeed()` are synchronous methods that create async tasks. This allows calling them inside synchronous `if` blocks without `await`. The actual state mutation happens in the task, which will run on the next event loop iteration. This is safe because:
1. The `_on_reject`/`_on_success` methods acquire the Condition lock before mutating state.
2. The Slot is already inside an `async with` block, so the event loop is running.
3. The release in `__aexit__` is awaited and also acquires the lock, so ordering is guaranteed.

**Alternative considered**: Making `reject()`/`succeed()` async. Rejected because it would force `await slot.reject()` inside the 429-handling code path, which currently does not await user code. The `create_task` approach is simpler to integrate.

**Important implementation detail**: The principal-engineer should use `asyncio.get_running_loop().create_task()` (not `asyncio.get_event_loop().create_task()`) for Python 3.10+ correctness. The pseudocode above uses `get_event_loop` for readability.

### 5.3 AIMDConfig

**Defined in**: `src/autom8_asana/transport/adaptive_semaphore.py` (same module)

```python
@dataclass(frozen=True)
class AIMDConfig:
    """Configuration for AIMD adaptive concurrency control.

    All parameters have sensible defaults derived from TCP congestion
    control principles and Asana API behavior observations.
    """

    # Window bounds
    ceiling: int            # Maximum concurrency (from ConcurrencyConfig.read_limit or write_limit)
    floor: int = 1          # Minimum concurrency. Must be >= 1 to prevent deadlock.
                            # Legacy discovered min=2 caused issues for batch; 1 is universally safe.

    # AIMD parameters
    multiplicative_decrease: float = 0.5    # Halve on 429 (TCP standard)
    additive_increase: float = 1.0          # +1 on success (TCP standard)

    # Timing
    grace_period_seconds: float = 5.0       # Suppress increases after decrease
    increase_interval_seconds: float = 2.0  # Minimum time between increases (FR-007)

    # Cooldown stub (FR-008)
    cooldown_trigger: int = 5               # Consecutive 429s before cooldown warning
    cooldown_duration_seconds: float = 30.0 # (unused in v1, config placeholder)

    def __post_init__(self) -> None:
        if self.floor < 1:
            raise ConfigurationError("floor must be >= 1 to prevent deadlock")
        if self.ceiling < self.floor:
            raise ConfigurationError("ceiling must be >= floor")
        if not 0.0 < self.multiplicative_decrease < 1.0:
            raise ConfigurationError("multiplicative_decrease must be in (0, 1)")
        if self.additive_increase <= 0:
            raise ConfigurationError("additive_increase must be positive")
        if self.grace_period_seconds < 0:
            raise ConfigurationError("grace_period_seconds must be non-negative")
        if self.increase_interval_seconds < 0:
            raise ConfigurationError("increase_interval_seconds must be non-negative")
```

**Parameter rationale**:

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `ceiling` | From ConcurrencyConfig | Preserves existing maximum behavior |
| `floor` | 1 | Prevents deadlock. Legacy `min=2` caused issues for batch because if both permits were held by blocked requests, no new work could proceed. With `floor=1`, at least one request can always proceed. |
| `multiplicative_decrease` | 0.5 | TCP Reno standard. Halving is aggressive enough to relieve pressure without cratering to minimum. |
| `additive_increase` | 1.0 | TCP standard. Slow recovery prevents oscillation. |
| `grace_period_seconds` | 5.0 | Short relative to Retry-After (30-60s). Prevents the first success after a halving from immediately growing the window, while allowing recovery to begin once the immediate 429 storm passes. |
| `increase_interval_seconds` | 2.0 | Matches legacy system. With +1 every 2s, recovering from window=25 to window=50 takes ~50s, approximately one Retry-After period. |
| `cooldown_trigger` | 5 | Five consecutive 429s indicates sustained overload, not a transient spike. |
| `cooldown_duration_seconds` | 30.0 | Placeholder for v2. |

### 5.4 Cooldown Stub (FR-008)

The cooldown stub consists of:

1. **Config fields**: `cooldown_trigger` and `cooldown_duration_seconds` on `AIMDConfig`.
2. **Counter**: `_consecutive_rejects` on `AsyncAdaptiveSemaphore`, incremented on `_on_reject()`, reset to 0 on `_on_success()`.
3. **Warning log**: When `_consecutive_rejects >= cooldown_trigger`, log `aimd_cooldown_threshold_reached` at WARNING level.
4. **No actual pause**: The system does NOT stop accepting requests. Cooldown activation is a future one-line change: add an `if self._cooldown_active: await self._condition.wait_for(lambda: not self._cooldown_active)` check in `acquire()`.

### 5.5 Stats/Introspection API (FR-006)

```python
def get_stats(self) -> dict[str, Any]:
    """Return current AIMD state for programmatic access.

    Returns dict with keys:
        - name: str ("read" or "write")
        - current_limit: int (int(self._window))
        - ceiling: int
        - floor: int
        - in_flight: int
        - epoch: int
        - decrease_count: int
        - increase_count: int
        - consecutive_rejects: int
        - grace_period_active: bool
        - window_raw: float (untruncated window value)
    """
```

This method does NOT acquire the lock -- it provides an approximate snapshot. This matches `TokenBucketRateLimiter.available_tokens` which is also unlocked.

Additionally, expose convenience properties:

```python
@property
def current_limit(self) -> int:
    """Current effective concurrency limit (integer floor of window)."""
    return int(self._window)

@property
def ceiling(self) -> int:
    """Maximum concurrency (from config)."""
    return self._config.ceiling

@property
def in_flight(self) -> int:
    """Number of currently-held slots."""
    return self._in_flight
```

### 5.6 Structured Logging Events (FR-005)

| Event Name | Level | Fields | When |
|-----------|-------|--------|------|
| `aimd_decrease` | INFO (WARNING if at floor) | `name`, `before`, `after`, `epoch`, `trigger` | On multiplicative decrease |
| `aimd_increase` | DEBUG | `name`, `before`, `after`, `epoch` | On additive increase |
| `aimd_at_minimum` | WARNING | `name`, `floor` | When window hits floor |
| `aimd_cooldown_threshold_reached` | WARNING | `name`, `consecutive_rejects`, `cooldown_trigger`, `note` | When consecutive rejects hit threshold |
| `aimd_grace_period_suppressed` | DEBUG | `name`, `remaining_seconds` | When success suppressed by grace period |

The logger is optional (`LoggerProtocol | None`). When `None`, no logging occurs. This matches the pattern used by `TokenBucketRateLimiter` and `CircuitBreaker`.

---

## 6. Integration Plan

### 6.1 ConcurrencyConfig Extension

Add AIMD parameters to the existing `ConcurrencyConfig` dataclass:

```python
# BEFORE (config.py, lines 168-187)
@dataclass(frozen=True)
class ConcurrencyConfig:
    read_limit: int = 50
    write_limit: int = 15

# AFTER
@dataclass(frozen=True)
class ConcurrencyConfig:
    read_limit: int = 50
    write_limit: int = 15

    # AIMD parameters (all optional, sensible defaults)
    aimd_enabled: bool = True                       # Kill switch for AIMD
    aimd_floor: int = 1                             # Minimum concurrency
    aimd_multiplicative_decrease: float = 0.5       # Halve on 429
    aimd_additive_increase: float = 1.0             # +1 on success
    aimd_grace_period_seconds: float = 5.0          # Suppress increases after decrease
    aimd_increase_interval_seconds: float = 2.0     # Min time between increases
    aimd_cooldown_trigger: int = 5                  # Consecutive 429s for cooldown warning
    aimd_cooldown_duration_seconds: float = 30.0    # Cooldown duration (unused in v1)
```

**Kill switch**: `aimd_enabled = True` by default. Setting to `False` falls back to plain `asyncio.Semaphore` behavior. This provides a safe rollback without config changes.

**Validation**: Add to `__post_init__()`:

```python
if self.aimd_floor < 1:
    raise ConfigurationError("aimd_floor must be >= 1")
if self.aimd_floor > self.read_limit or self.aimd_floor > self.write_limit:
    raise ConfigurationError("aimd_floor must be <= read_limit and write_limit")
if not 0.0 < self.aimd_multiplicative_decrease < 1.0:
    raise ConfigurationError("aimd_multiplicative_decrease must be in (0, 1)")
```

### 6.2 AsanaHttpClient.__init__() Changes

```python
# BEFORE (asana_http.py, lines 126-127)
self._read_semaphore = asyncio.Semaphore(config.concurrency.read_limit)
self._write_semaphore = asyncio.Semaphore(config.concurrency.write_limit)

# AFTER
if config.concurrency.aimd_enabled:
    read_aimd_config = AIMDConfig(
        ceiling=config.concurrency.read_limit,
        floor=config.concurrency.aimd_floor,
        multiplicative_decrease=config.concurrency.aimd_multiplicative_decrease,
        additive_increase=config.concurrency.aimd_additive_increase,
        grace_period_seconds=config.concurrency.aimd_grace_period_seconds,
        increase_interval_seconds=config.concurrency.aimd_increase_interval_seconds,
        cooldown_trigger=config.concurrency.aimd_cooldown_trigger,
        cooldown_duration_seconds=config.concurrency.aimd_cooldown_duration_seconds,
    )
    write_aimd_config = AIMDConfig(
        ceiling=config.concurrency.write_limit,
        floor=config.concurrency.aimd_floor,
        multiplicative_decrease=config.concurrency.aimd_multiplicative_decrease,
        additive_increase=config.concurrency.aimd_additive_increase,
        grace_period_seconds=config.concurrency.aimd_grace_period_seconds,
        increase_interval_seconds=config.concurrency.aimd_increase_interval_seconds,
        cooldown_trigger=config.concurrency.aimd_cooldown_trigger,
        cooldown_duration_seconds=config.concurrency.aimd_cooldown_duration_seconds,
    )
    self._read_semaphore = AsyncAdaptiveSemaphore(
        config=read_aimd_config, name="read", logger=logger,
    )
    self._write_semaphore = AsyncAdaptiveSemaphore(
        config=write_aimd_config, name="write", logger=logger,
    )
else:
    self._read_semaphore = asyncio.Semaphore(config.concurrency.read_limit)
    self._write_semaphore = asyncio.Semaphore(config.concurrency.write_limit)
```

### 6.3 AsanaHttpClient._request() Changes

The key change is that `async with semaphore:` becomes `async with await semaphore.acquire() as slot:`, and the 429 and success paths call `slot.reject()` / `slot.succeed()`.

```python
# BEFORE (_request, lines 503-576)
while True:
    async with semaphore:
        await self._rate_limiter.acquire()
        try:
            response = await platform_client._client.request(...)

            if response.status_code >= 400:
                error = AsanaError.from_response(response)
                if isinstance(error, RateLimitError):
                    # ... log, retry
                    continue
                # ... other errors
                raise error

            await self._circuit_breaker.record_success()
            return self._response_handler.unwrap_response(response)
        except httpx.TimeoutException:
            # ...
        except httpx.HTTPError:
            # ...

# AFTER
while True:
    async with await semaphore.acquire() as slot:
        await self._rate_limiter.acquire()
        try:
            response = await platform_client._client.request(...)

            if response.status_code >= 400:
                error = AsanaError.from_response(response)
                if isinstance(error, RateLimitError):
                    slot.reject()               # <-- AIMD signal
                    # ... log, retry
                    continue
                # ... other errors (not 429, no AIMD signal)
                raise error

            slot.succeed()                      # <-- AIMD signal
            await self._circuit_breaker.record_success()
            return self._response_handler.unwrap_response(response)
        except httpx.TimeoutException:
            # No AIMD signal -- timeout is not a rate limit
            # ...
        except httpx.HTTPError:
            # No AIMD signal -- network error is not a rate limit
            # ...
```

**What does NOT trigger AIMD feedback**:
- Timeouts (these are server issues, not rate limits)
- 5xx errors (server errors, not concurrency issues)
- Network errors (connection issues)
- 4xx errors other than 429

**What triggers reject()**: Only `isinstance(error, RateLimitError)` (which is created from 429 status code).

**What triggers succeed()**: Any 2xx response.

### 6.4 Backward Compatibility with asyncio.Semaphore

When `aimd_enabled = False`, the code uses plain `asyncio.Semaphore`. The `async with semaphore:` pattern works for `asyncio.Semaphore` but the AIMD path uses `async with await semaphore.acquire() as slot:`.

**Resolution**: When AIMD is disabled, wrap the semaphore in a thin adapter or use a conditional path. The cleanest approach is to have `AsyncAdaptiveSemaphore` support a "passthrough" mode where `_on_reject` and `_on_success` are no-ops. However, the stakeholder decided on separate code paths (`aimd_enabled` flag), which is simpler.

**Proposed approach**: Use duck typing. The `_request()` method checks `isinstance(semaphore, AsyncAdaptiveSemaphore)`:

```python
if isinstance(semaphore, AsyncAdaptiveSemaphore):
    slot_ctx = await semaphore.acquire()
else:
    slot_ctx = semaphore  # asyncio.Semaphore is already a context manager

async with slot_ctx as slot_or_none:
    # ... request logic
    if isinstance(error, RateLimitError) and hasattr(slot_or_none, 'reject'):
        slot_or_none.reject()
    # ...
    if hasattr(slot_or_none, 'succeed'):
        slot_or_none.succeed()
```

**Better approach (recommended)**: Create a simple `FixedSemaphoreAdapter` that wraps `asyncio.Semaphore` with the same `acquire() -> Slot` interface but where `Slot.reject()` and `Slot.succeed()` are no-ops. This avoids `isinstance` checks throughout:

```python
class FixedSemaphoreAdapter:
    """Adapts asyncio.Semaphore to AsyncAdaptiveSemaphore interface."""

    def __init__(self, limit: int):
        self._semaphore = asyncio.Semaphore(limit)
        self._limit = limit

    async def acquire(self) -> NoOpSlot:
        await self._semaphore.acquire()
        return NoOpSlot(self._semaphore)

    @property
    def ceiling(self) -> int:
        return self._limit

    @property
    def current_limit(self) -> int:
        return self._limit

class NoOpSlot:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self._semaphore.release()
    def reject(self): pass
    def succeed(self): pass
```

Then `AsanaHttpClient.__init__()` always creates a semaphore-like object with the `acquire() -> Slot` interface, and `_request()` always uses `async with await semaphore.acquire() as slot:`. No conditional paths.

### 6.5 Changes to _request_paginated() and post_multipart()

The same `async with await semaphore.acquire() as slot:` pattern must be applied to:

1. `_request_paginated()` (lines 596-662) -- same structure as `_request()`.
2. `post_multipart()` (lines 355-418) -- same structure.

Each method gets the same two-line change:
- Replace `async with semaphore:` with `async with await semaphore.acquire() as slot:`
- Add `slot.reject()` in the 429 path, `slot.succeed()` in the success path.

---

## 7. File Structure

### 7.1 New Files

| File | Purpose | Approximate LOC |
|------|---------|----------------|
| `src/autom8_asana/transport/adaptive_semaphore.py` | `AsyncAdaptiveSemaphore`, `Slot`, `NoOpSlot`, `FixedSemaphoreAdapter`, `AIMDConfig` | ~250 |
| `tests/unit/transport/test_adaptive_semaphore.py` | Unit tests for the semaphore primitive | ~400 |
| `tests/unit/transport/test_aimd_simulation.py` | Deterministic simulation test (SC-003) | ~150 |
| `tests/unit/transport/test_aimd_integration.py` | Integration tests with mocked HTTP | ~200 |

### 7.2 Modified Files

| File | Change | Impact |
|------|--------|--------|
| `src/autom8_asana/config.py` | Add AIMD fields to `ConcurrencyConfig` | Low -- additive, all defaults backward compatible |
| `src/autom8_asana/transport/asana_http.py` | Replace semaphore creation and usage | Medium -- core integration |
| `src/autom8_asana/transport/__init__.py` | Export `AsyncAdaptiveSemaphore` | Low -- additive |
| `tests/unit/transport/test_asana_http.py` | Update `test_creates_concurrency_semaphores` | Low -- one test |

### 7.3 Module Dependency Graph

```
config.py (ConcurrencyConfig with AIMD fields)
    |
    v
transport/adaptive_semaphore.py (AsyncAdaptiveSemaphore, AIMDConfig, Slot)
    |
    v
transport/asana_http.py (creates and uses adaptive semaphores)
```

No circular dependencies. `adaptive_semaphore.py` depends only on `asyncio`, `time`, `dataclasses`, `typing`, and `autom8_asana.exceptions.ConfigurationError`.

---

## 8. Test Strategy

### 8.1 Unit Tests: AsyncAdaptiveSemaphore (`test_adaptive_semaphore.py`)

| Test Case | SC | Description |
|-----------|-----|-------------|
| `test_acquire_below_limit_does_not_block` | SC-001 | Acquire when in_flight < window returns immediately |
| `test_acquire_at_limit_blocks` | SC-001 | Acquire when in_flight == window blocks until release |
| `test_reject_halves_window` | SC-001 | After reject(), window = old * 0.5 |
| `test_reject_at_floor_stays_at_floor` | SC-004 | Window never drops below floor |
| `test_reject_at_floor_logs_warning` | SC-005 | `aimd_at_minimum` event emitted |
| `test_succeed_increases_window` | SC-002 | After succeed(), window = old + 1.0 |
| `test_succeed_at_ceiling_stays_at_ceiling` | SC-002 | Window never exceeds ceiling |
| `test_epoch_coalescing_single_halving` | SC-001 | N simultaneous rejects cause exactly 1 halving |
| `test_stale_epoch_success_ignored` | SC-001 | Success from pre-decrease epoch does not increase window |
| `test_grace_period_suppresses_increase` | SC-002 | Success during grace period does not increase window |
| `test_grace_period_expires_allows_increase` | SC-002 | Success after grace period increases window |
| `test_increase_throttle_respected` | SC-002 | Successive successes within interval only increase once |
| `test_full_recovery_to_ceiling` | SC-002 | After decrease, N successes bring window back to ceiling |
| `test_concurrent_acquire_correctness` | NFR-003 | Multiple concurrent coroutines maintain consistent state |
| `test_slot_releases_on_exception` | NFR-002 | Slot releases even when request raises exception |
| `test_slot_reject_idempotent` | - | Calling reject() twice is safe |
| `test_slot_succeed_idempotent` | - | Calling succeed() twice is safe |
| `test_slot_silent_release` | - | Not calling reject/succeed releases without feedback |
| `test_stats_api` | FR-006 | `get_stats()` returns all documented fields |
| `test_cooldown_counter_increments` | FR-008 | Consecutive rejects increment counter |
| `test_cooldown_counter_resets_on_success` | FR-008 | Success resets consecutive reject counter |
| `test_cooldown_threshold_logs_warning` | FR-008 | Warning emitted at threshold |
| `test_structured_log_decrease` | SC-005 | `aimd_decrease` event has correct fields |
| `test_structured_log_increase` | SC-005 | `aimd_increase` event at DEBUG level |
| `test_injectable_clock` | NFR-005 | Grace period and throttle use injected clock |
| `test_config_validation` | - | Invalid AIMDConfig raises ConfigurationError |
| `test_no_logger_does_not_raise` | - | All paths work without a logger |

**Test pattern**: Use a controllable clock:

```python
class FakeClock:
    def __init__(self, start=0.0):
        self._time = start
    def __call__(self) -> float:
        return self._time
    def advance(self, seconds: float):
        self._time += seconds
```

Inject via `AsyncAdaptiveSemaphore(config=config, clock=fake_clock)`.

### 8.2 Simulation Test: SC-003 (`test_aimd_simulation.py`)

**Goal**: Demonstrate that under simulated 429 pressure, AIMD produces fewer total 429s than a fixed semaphore.

**Approach**: Deterministic simulation with a scripted "server" that returns 429 when concurrency exceeds a threshold.

```python
async def test_aimd_fewer_429s_than_fixed():
    """SC-003: Under 429 pressure, AIMD produces fewer total 429s."""
    SERVER_CAPACITY = 20  # Server starts 429-ing above 20 concurrent
    TOTAL_REQUESTS = 200

    # Simulated server: tracks concurrent requests, returns 429 if over capacity
    class SimServer:
        concurrent = 0
        total_429s = 0

        async def handle(self):
            self.concurrent += 1
            try:
                if self.concurrent > SERVER_CAPACITY:
                    self.total_429s += 1
                    return 429
                await asyncio.sleep(0.01)  # Simulate request latency
                return 200
            finally:
                self.concurrent -= 1

    # Run with fixed semaphore (ceiling=50, no adaptation)
    fixed_server = SimServer()
    fixed_429s = await run_simulation(fixed_server, semaphore_type="fixed", limit=50, n=TOTAL_REQUESTS)

    # Run with AIMD semaphore (ceiling=50, adapts on 429)
    aimd_server = SimServer()
    aimd_429s = await run_simulation(aimd_server, semaphore_type="aimd", limit=50, n=TOTAL_REQUESTS)

    assert aimd_429s < fixed_429s, f"AIMD ({aimd_429s}) should produce fewer 429s than fixed ({fixed_429s})"
```

This test is deterministic (no real HTTP, no real timers beyond `asyncio.sleep`), CI-safe, and reproducible.

### 8.3 Integration Tests: Mocked HTTP (`test_aimd_integration.py`)

| Test Case | Description |
|-----------|-------------|
| `test_429_triggers_aimd_decrease_in_request` | Mock 429 response, verify semaphore window decreased |
| `test_success_triggers_aimd_increase_in_request` | Mock 200 response, verify semaphore window increased |
| `test_429_does_not_affect_other_pool` | Mock 429 on write, verify read semaphore unchanged |
| `test_aimd_disabled_uses_fixed_semaphore` | Set `aimd_enabled=False`, verify `asyncio.Semaphore` used |
| `test_existing_client_api_unchanged` | Verify `.get()`, `.post()`, `.put()`, `.delete()`, `.get_paginated()`, `.request()` signatures unchanged |
| `test_retry_loop_reacquires_slot` | Mock 429 then 200, verify two slot acquisitions |

### 8.4 Existing Test Update

**File**: `tests/unit/transport/test_asana_http.py`

**Change**: Update `test_creates_concurrency_semaphores` to check the public interface:

```python
# BEFORE
assert client._read_semaphore._value == 10
assert client._write_semaphore._value == 5

# AFTER
assert client._read_semaphore.ceiling == 10
assert client._write_semaphore.ceiling == 5
assert client._read_semaphore.current_limit == 10
assert client._write_semaphore.current_limit == 5
```

### 8.5 Test File Locations

All test files live under the existing `tests/unit/transport/` directory:

```
tests/unit/transport/
  test_asana_http.py              # Existing (1 test updated)
  test_adaptive_semaphore.py      # NEW: unit tests for primitive
  test_aimd_simulation.py         # NEW: SC-003 deterministic simulation
  test_aimd_integration.py        # NEW: integration with mocked AsanaHttpClient
```

---

## 9. Migration / Rollback

### 9.1 Deployment Strategy

AIMD is enabled by default (`aimd_enabled = True`). There is no phased rollout because:
- This is an internal optimization, not a public API change.
- The kill switch provides instant rollback.
- All defaults preserve existing behavior as the ceiling.

### 9.2 Kill Switch

```python
# To disable AIMD, set in config:
config = AsanaConfig(
    concurrency=ConcurrencyConfig(aimd_enabled=False)
)
```

When `aimd_enabled = False`:
- `AsanaHttpClient` creates `FixedSemaphoreAdapter` instances (same `acquire() -> Slot` interface, but no-op `reject()`/`succeed()`).
- No AIMD logging occurs.
- Behavior is identical to the current fixed-semaphore system.

### 9.3 Rollback Scenarios

| Scenario | Action | Effort |
|----------|--------|--------|
| AIMD parameters are wrong | Adjust config values (no code change) | Config change |
| AIMD causes unexpected behavior | Set `aimd_enabled = False` | Config change |
| AIMD introduces bugs | Revert the commit(s) | Git revert |
| Concurrency is too aggressive | Lower `ceiling`, raise `floor` | Config change |

### 9.4 Observability During Rollout

Monitor these structured log events after deployment:
- `aimd_decrease`: Frequency and `after` values indicate how often and how far concurrency drops.
- `aimd_at_minimum`: If this fires frequently, the floor may be too high or the API is genuinely overloaded.
- `aimd_cooldown_threshold_reached`: If this fires, cooldown activation should be prioritized.
- `rate_limit_429_received`: Compare before/after deployment. Should decrease.

---

## 10. Implementation Sequence

The principal-engineer should implement in this order, with each step producing an atomic commit:

### Commit 1: AIMDConfig and AsyncAdaptiveSemaphore primitive

**Files created**:
- `src/autom8_asana/transport/adaptive_semaphore.py`

**Contains**:
- `AIMDConfig` dataclass with validation
- `Slot` context manager
- `NoOpSlot` context manager
- `FixedSemaphoreAdapter` wrapper
- `AsyncAdaptiveSemaphore` with full AIMD logic (acquire, release, on_reject, on_success, stats, logging)

**Does NOT** integrate with `AsanaHttpClient` yet. This is a standalone, testable module.

### Commit 2: Unit tests for the primitive

**Files created**:
- `tests/unit/transport/test_adaptive_semaphore.py`

**Contains**: All unit tests from section 8.1. This commit should pass on its own because the primitive has no dependencies on `AsanaHttpClient`.

### Commit 3: ConcurrencyConfig extension

**Files modified**:
- `src/autom8_asana/config.py`

**Changes**: Add AIMD fields to `ConcurrencyConfig` with defaults and validation.

### Commit 4: AsanaHttpClient integration

**Files modified**:
- `src/autom8_asana/transport/asana_http.py`
- `src/autom8_asana/transport/__init__.py`

**Changes**:
- Import `AsyncAdaptiveSemaphore`, `AIMDConfig`, `FixedSemaphoreAdapter` from `adaptive_semaphore`
- Replace semaphore creation in `__init__()`
- Update `_request()`, `_request_paginated()`, `post_multipart()` to use `acquire() -> Slot` pattern
- Export `AsyncAdaptiveSemaphore` from `__init__.py`

### Commit 5: Integration tests and existing test update

**Files created**:
- `tests/unit/transport/test_aimd_integration.py`

**Files modified**:
- `tests/unit/transport/test_asana_http.py`

**Changes**: Integration tests with mocked HTTP, update `test_creates_concurrency_semaphores`.

### Commit 6: Simulation test (SC-003)

**Files created**:
- `tests/unit/transport/test_aimd_simulation.py`

**Contains**: Deterministic simulation demonstrating AIMD produces fewer 429s than fixed semaphore.

---

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AIMD parameters wrong for Asana's profile | Medium | Medium | Defaults from TCP standard + legacy system; all configurable; kill switch |
| `asyncio.Condition` introduces subtle bugs | Low | High | Comprehensive unit tests with concurrent coroutines; epoch coalescing prevents double-halving |
| `create_task` for reject/succeed causes ordering issues | Low | Medium | Tasks acquire Condition lock; release in `__aexit__` is awaited; ordering guaranteed by event loop |
| Grace period too short -- premature recovery | Low | Low | Configurable; monitor `aimd_decrease` frequency in production |
| Grace period too long -- unnecessarily slow recovery | Low | Low | 5s default is short relative to 30-60s Retry-After; configurable |
| Floor=1 causes starvation for paginated fetches | Low | Medium | Only one request at a time at minimum; paginated fetches still complete, just slowly; this is correct behavior under extreme rate limiting |
| Token bucket accumulates tokens during AIMD decrease, causing burst on recovery | Low | Low | AIMD recovery is additive (+1 per 2s), so concurrency grows slowly. Token bucket refills naturally. No burst. |

---

## 12. Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-GAP-04-aimd-rate-limiting.md` | Written |
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-04-aimd-rate-limiting.md` | Read |
| Stakeholder Decisions | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/stakeholder-decisions-GAP-04-aimd.md` | Read |
| AsanaHttpClient | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/asana_http.py` | Read |
| ConcurrencyConfig | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Read |
| Existing transport tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/transport/test_asana_http.py` | Read |
| Platform rate limiter | `/Users/tomtenuta/code/autom8y_platform/sdks/python/autom8y-http/src/autom8y_http/rate_limiter.py` | Read |
| Platform concurrency controller | `/Users/tomtenuta/code/autom8y_platform/sdks/python/autom8y-http/src/autom8y_http/concurrency.py` | Read |
| Platform protocols | `/Users/tomtenuta/code/autom8y_platform/sdks/python/autom8y-http/src/autom8y_http/protocols.py` | Read |
| Platform config | `/Users/tomtenuta/code/autom8y_platform/sdks/python/autom8y-http/src/autom8y_http/config.py` | Read |
| ADR-0062 (rate limiter coordination) | `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0062-rate-limiter-coordination.md` | Read |
| ADR-0063 (concurrency extraction) | `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0063-platform-concurrency-extraction.md` | Read |
| Config translator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` | Read |
| Transport __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/__init__.py` | Read |
| Exceptions module | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` | Read (partial) |
