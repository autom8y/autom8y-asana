---
artifact_id: PRD-GAP-04-aimd-rate-limiting
title: "AIMD Adaptive Rate Limiting"
created_at: "2026-02-07T16:00:00Z"
author: requirements-analyst
status: draft
complexity: SMALL
impact: low
impact_categories: []
related_docs:
  - docs/GAPS/Q1/GAP-04-aimd-rate-limiting.md
  - docs/requirements/PRD-ASANA-HTTP-MIGRATION-001.md
success_criteria:
  - id: SC-001
    description: "On 429 response, concurrent request capacity is reduced within the same event loop tick"
    testable: true
    priority: must-have
  - id: SC-002
    description: "After sustained success, concurrent request capacity recovers to its configured maximum"
    testable: true
    priority: must-have
  - id: SC-003
    description: "Under simulated 429 pressure, total 429s received is lower than with fixed semaphores"
    testable: true
    priority: must-have
  - id: SC-004
    description: "Concurrent request capacity never drops below configured minimum (floor of 1)"
    testable: true
    priority: must-have
  - id: SC-005
    description: "AIMD state transitions are observable via structured logging"
    testable: true
    priority: must-have
  - id: SC-006
    description: "All existing transport tests pass without modification (backward compatible)"
    testable: true
    priority: must-have
stakeholders:
  - principal-engineer
  - qa-adversary
  - architect
schema_version: "1.0"
---

# PRD: AIMD Adaptive Rate Limiting

**PRD ID**: PRD-GAP-04
**Version**: 1.0
**Date**: 2026-02-07
**Gap Reference**: GAP-04

---

## Problem Statement

autom8_asana uses fixed concurrency semaphores (`asyncio.Semaphore(50)` for reads, `asyncio.Semaphore(15)` for writes) and a fixed-rate `TokenBucketRateLimiter` (1500 tokens/60s). These cannot adapt to API backpressure. When Asana returns a 429, the individual request retries with exponential backoff, but the other 49 concurrent readers keep firing. The system has no mechanism to reduce its aggregate request rate in response to rate limit signals.

The legacy monolith solved this with a 3-layer system: Token Bucket (rate) + AIMD (concurrency) + Cooldown/Drain (pause). That system converges to maximum sustainable throughput by halving concurrency on 429 and incrementing by 1 on success -- classic TCP congestion control applied to API calls. The result: fewer 429s overall, faster total completion time for bulk operations, and graceful degradation under pressure.

**Business impact**: During parallel section fetches (2600+ tasks, 8+ concurrent sections), the fixed concurrency allows bursts that exhaust Asana's rate limit. Each 429 triggers a retry with 30-60s Retry-After delay. Those delays cascade: while one request sleeps, others continue hitting the limit, producing more 429s. This turns a 45-second fetch into a 3-5 minute fetch with 80+ retry warnings in logs.

---

## Goals

1. Replace fixed concurrency semaphores with an adaptive mechanism that reduces concurrency on 429 and increases it on success.
2. Prevent burst-induced 429 cascades during parallel operations.
3. Provide observability into concurrency state for production debugging.
4. Maintain backward compatibility -- no changes to `AsanaHttpClient`'s public API.

## Non-Goals

- Modifying the `autom8y-http` platform SDK (this is autom8_asana-local).
- Replacing or modifying the existing `TokenBucketRateLimiter` (rate limiting and concurrency control are complementary layers).
- Changing the `CircuitBreaker` behavior (429s are rate limit signals, not failures -- they should NOT feed into circuit breaker counters).
- Inbound rate limiting (`SlowAPI` on autom8_asana's own API endpoints).
- Optimizing the `ExponentialBackoffRetry` parameters.
- Per-method-type cooldown/drain (legacy had read/write/batch cooldowns -- this can be deferred unless the architect determines it is essential for correctness).

---

## User Stories

### US-001: Adaptive Concurrency Under Rate Limiting

**As a** developer running parallel Asana API operations
**I want** the system to automatically reduce its concurrency when rate limited
**So that** bulk operations complete faster with fewer retries

**Acceptance Criteria:**
- [ ] When a 429 is received, the effective concurrency limit decreases
- [ ] When requests succeed, the effective concurrency limit gradually increases
- [ ] The concurrency limit never exceeds its configured maximum
- [ ] The concurrency limit never drops below its configured minimum

### US-002: Stable Convergence

**As a** service operator
**I want** the concurrency controller to converge to a stable throughput
**So that** the system finds and maintains the maximum sustainable request rate

**Acceptance Criteria:**
- [ ] Under constant API capacity, the concurrency level stabilizes near the maximum
- [ ] Under reduced API capacity (sustained 429s), the concurrency level stabilizes at a lower value
- [ ] No oscillation between extreme high and extreme low concurrency

### US-003: Observable AIMD State

**As a** service operator debugging production rate limiting
**I want** to see the current concurrency limit and AIMD state transitions in logs
**So that** I can understand why requests are being throttled

**Acceptance Criteria:**
- [ ] AIMD decrease events are logged with before/after concurrency values
- [ ] AIMD increase events are logged (at DEBUG level to avoid noise)
- [ ] Current concurrency state is accessible programmatically (for metrics/health endpoints)

---

## Functional Requirements

### Must Have

#### FR-001: Adaptive Concurrency Controller

A controller that manages a dynamic concurrency limit with AIMD behavior:

- **Multiplicative decrease**: On rate limit signal (429), reduce the concurrency limit by a multiplicative factor (e.g., halve it).
- **Additive increase**: On success signal, increase the concurrency limit by a fixed step.
- **Bounds**: Concurrency limit is bounded by a configurable minimum (floor) and maximum (ceiling). Minimum must be at least 1 to prevent deadlock.
- **Gating**: New requests must wait when the number of in-flight requests equals the current dynamic limit.

The controller must work with `asyncio` (not threading primitives).

#### FR-002: Backoff Grace Period

After a multiplicative decrease, success signals must be suppressed for a configurable grace period. This prevents premature recovery while Retry-After delays are still in effect. Without this, a single success immediately after a decrease would start increasing concurrency while other requests are still backed off.

#### FR-003: Integration with AsanaHttpClient

The adaptive controller replaces the fixed `asyncio.Semaphore` instances (`_read_semaphore`, `_write_semaphore`) in `AsanaHttpClient`. The 429 detection path in `_request()` must signal the controller. The success path must signal the controller.

This must not change `AsanaHttpClient`'s public API (`.get()`, `.post()`, `.put()`, `.delete()`, `.get_paginated()`, `.request()`).

#### FR-004: Configuration via ConcurrencyConfig

The existing `ConcurrencyConfig` dataclass (`read_limit`, `write_limit`) should continue to define the **maximum** concurrency values. AIMD-specific parameters (minimum, increase step, decrease factor, grace period) should be configurable but have sensible defaults.

#### FR-005: Structured Logging for State Transitions

AIMD state changes must be logged via structured logging:

- `aimd_decrease`: Emitted on multiplicative decrease. Include `before`, `after`, `trigger` (e.g., "429"), `operation_type` (read/write).
- `aimd_increase`: Emitted on additive increase (DEBUG level). Include `before`, `after`, `operation_type`.
- `aimd_at_minimum`: Emitted when concurrency hits the floor (WARNING level).

#### FR-006: Stats/Introspection API

The controller must expose its current state for programmatic access:

- Current concurrency limit
- Number of in-flight requests
- Number of decreases since creation
- Number of increases since creation
- Whether grace period is active

This enables future metrics export and health endpoint integration.

### Should Have

#### FR-007: Increase Interval Throttle

Successive additive increases should be throttled to prevent rapid recovery that overshoots the sustainable rate. The legacy system used a minimum 2.0s between increases. The architect should determine whether this is necessary or whether the grace period (FR-002) is sufficient.

#### FR-008: Cooldown Mode

After N consecutive 429s within a time window, enter a cooldown state that pauses new request acquisition for a configurable duration. During cooldown, in-flight requests are allowed to complete (drain). This prevents the system from continuing to hammer an overloaded API when multiplicative decrease alone is insufficient.

The legacy system maintained separate cooldown timestamps for read, write, and batch operations.

### Could Have

#### FR-009: Token Bucket Drain on Cooldown Entry

When entering cooldown, drain accumulated tokens from the `TokenBucketRateLimiter` to prevent a burst when cooldown exits. The legacy system drained tokens at both cooldown entry and exit to prevent "lazy refill" bursts. This may require extending the platform rate limiter or handling it at the concurrency layer.

---

## Non-Functional Requirements

### NFR-001: No Deadlock

The concurrency minimum must be at least 1. The legacy system discovered that `min_concurrent=2` for batch caused death spirals when both permits were held by blocked requests. The architect should consider whether `min_concurrent=1` is universally safe or whether read/write require different minimums.

### NFR-002: No Revocation of Active Permits

When the concurrency limit decreases, requests already in flight must be allowed to complete. The controller only affects *new* request admission. Canceling in-flight requests would cause data corruption in paginated fetches.

### NFR-003: Async Safety

The controller must be safe under concurrent access from multiple coroutines within a single event loop. It does not need to be thread-safe (autom8_asana is single-threaded async).

### NFR-004: Performance

Acquiring a concurrency permit should add negligible latency (< 1ms) in the common case (concurrency not exhausted). The AIMD calculation itself should be O(1).

### NFR-005: Testability

The controller must be testable in isolation (unit tests with simulated success/failure sequences) without requiring real HTTP requests or real asyncio sleep. Time-dependent behavior (grace period, increase interval) should accept an injectable clock or be testable via time manipulation.

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| 429 received when already at minimum concurrency | Stay at minimum, do not decrease further, log warning |
| Rapid burst of N simultaneous 429s | Single multiplicative decrease (not N decreases), or bounded decrease |
| Success during grace period | Suppressed -- no increase until grace period expires |
| All in-flight requests receive 429 simultaneously | Decrease once, all requests retry with backoff, system recovers |
| No requests for extended period, then burst | Concurrency limit should be at its last value (no decay), token bucket governs rate |
| Client close/restart | State resets to initial maximum (no persistence required) |
| Single 429 among thousands of successes | Decrease, then recover quickly via additive increase |
| 429 with Retry-After: 120 (large delay) | Retry policy handles the delay; AIMD handles the concurrency reduction. Both are independent. |
| Concurrent paginated fetches sharing the controller | All pages for all fetches compete for the same concurrency pool (correct behavior) |
| Write request 429 affects read concurrency? | Only if architect chooses a shared controller. If separate, only the relevant pool is affected. |

---

## Success Criteria

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| SC-001 | On 429, concurrent capacity decreases within the same tick | Unit test: signal 429, assert limit < previous limit |
| SC-002 | After sustained success, capacity recovers to maximum | Unit test: decrease then signal N successes, assert limit == max |
| SC-003 | Under 429 pressure, fewer total 429s than fixed semaphore | Benchmark or simulation test comparing adaptive vs fixed |
| SC-004 | Concurrency never drops below minimum | Unit test: signal repeated 429s, assert limit >= min |
| SC-005 | AIMD state transitions logged with structured fields | Unit test: capture log output, assert event names and fields present |
| SC-006 | All existing transport tests pass | CI: `pytest tests/unit/transport/ -x` passes with no modifications |

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Contributing AIMD upstream to autom8y-http | Start local with a clean interface; promotion is a future decision |
| Modifying TokenBucketRateLimiter (drain, release) | Concurrency control and rate control are complementary; avoid coupling them initially |
| Per-endpoint rate limiting | Asana's rate limit is per-token, not per-endpoint |
| Downstream semaphore adaptation (hierarchy warming, parallel fetch, DataServiceClient) | Those semaphores protect different resources; AIMD applies to Asana API concurrency only |
| Persistent AIMD state across restarts | Convergence is fast; fresh start at max is acceptable |
| Dashboard or Grafana integration | Metrics export is deferred; FR-006 provides the hook |
| Tuning default parameter values | Defaults should be reasonable; production tuning is operational, not a requirement |

---

## Open Questions

These are genuine design decisions for the architect -- not implementation details.

| ID | Question | Context | Recommendation |
|----|----------|---------|----------------|
| OQ-1 | Should read and write operations use separate AIMD controllers or a shared one? | Legacy used 3 separate instances (read/write/batch). Asana's rate limit is per-token (shared across all operations), which argues for shared. But write 429s may have different backoff characteristics than read 429s. | Lean toward separate (matches legacy learning), but architect should evaluate |
| OQ-2 | Where should the AIMD controller sit -- inside AsanaHttpClient replacing the semaphore, or as an external wrapper? | Replacing the semaphore is the minimal change. An external wrapper gives more flexibility but adds a layer. | Architect's call on coupling vs simplicity |
| OQ-3 | Is cooldown/drain (FR-008) necessary for v1, or can it be deferred? | The legacy system had cooldown as a critical layer. But AIMD alone (without cooldown) may be sufficient if the multiplicative decrease is aggressive enough. | Ship AIMD first (FR-001-006), add cooldown if production data shows it is needed |
| OQ-4 | How should multiple simultaneous 429s be coalesced? | If 10 requests all get 429 in the same batch, should that trigger 10 halvings or 1? 10 halvings would instantly crater to minimum. | Likely needs a dedup window or single-decrease-per-tick rule |
| OQ-5 | What async primitive should replace asyncio.Semaphore? | asyncio.Semaphore cannot be resized after construction. Options include asyncio.Condition wrapping a counter, or a custom AsyncAdaptiveSemaphore. | Architect should evaluate; the legacy used threading.Condition |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| AsanaHttpClient transport layer | Stable | PRD-ASANA-HTTP-MIGRATION-001 is implemented; this builds on top |
| autom8y-http TokenBucketRateLimiter | Stable | Used as-is; no modifications required |
| ConcurrencyConfig in config.py | Stable | Extended with AIMD parameters, backward compatible |
| Legacy AIMD reference code | Available | ~360 LOC in monolith's `utils/threading/adaptive_concurrency.py` |
| Legacy test suite | Available | ~616 LOC in monolith's `test_adaptive_concurrency.py` for porting |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AIMD parameters are wrong for Asana's rate limit profile | Medium | Medium | Conservative defaults (start at max, halve on 429, increment by 1); tuneable via config |
| asyncio.Semaphore replacement introduces subtle concurrency bugs | Low | High | Port legacy threading tests to async; adversarial testing with concurrent coroutines |
| Minimum concurrency = 1 causes starvation for paginated fetches | Low | Medium | Legacy discovered this for batch; test with paginated fetch under sustained 429 pressure |
| Token bucket burst after AIMD recovery | Low | Medium | Deferred (FR-009); AIMD recovery is additive (slow), so burst risk is low |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-04-aimd-rate-limiting.md` | Pending |
| Gap Brief | `/Users/tomtenuta/Code/autom8_asana/docs/GAPS/Q1/GAP-04-aimd-rate-limiting.md` | Read |
| Gap Index | `/Users/tomtenuta/Code/autom8_asana/docs/GAPS/Q1/INDEX.md` | Read |
| HTTP Migration PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-ASANA-HTTP-MIGRATION-001.md` | Read |
| AsanaHttpClient | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/asana_http.py` | Read |
| ConfigTranslator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/config_translator.py` | Read |
| ConcurrencyConfig | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Read (grep) |
