# ADR: Hierarchy Warming Backpressure Hardening -- Batch Pacing for Phase 1

**Status**: Accepted
**Date**: 2026-02-03
**Deciders**: Architecture team
**Context**: Post-mortem from large-section-resilience rollout; 145 HTTP 429s during CONTACTS cold-start
**Related**: [SPIKE: Hierarchy-Warming 429 Backpressure Audit](../spikes/SPIKE-hierarchy-warming-429-backpressure.md)

## Context

The large-section-resilience feature eliminated pagination-induced 429s for sections with 22,000+ tasks by introducing paced fetch with inter-page delays. However, the hierarchy warming phase that follows task accumulation produced **145 transient HTTP 429 responses** during the CONTACTS build (22,818 tasks, 2,233 unique parent GIDs).

**Root cause**: `put_batch_async(warm_hierarchy=True)` dispatches all 2,233 immediate parent fetches via a single `asyncio.gather()`. The `hierarchy_semaphore(10)` gates concurrency to 10 in-flight requests, but all 10 fire within microseconds. The token bucket rate limiter (`max_tokens=1500`, refill 25/sec) has ample capacity and never throttles bursts -- it is designed for sustained-rate compliance, not instantaneous-rate smoothing. Asana's per-second instantaneous limit triggers 429s on these micro-bursts.

All 429s retry successfully at the transport layer (`AsanaHttpClient._request()` catches `RateLimitError` and retries with exponential backoff). The hierarchy warmer never observes these errors, which means the `backoff_event` mechanism in `hierarchy_warmer.py` -- designed to adaptively slow down on 429s -- is **dead code** for transport-retried errors.

**Impact**: No data loss. All parents and ancestors resolve correctly. Cost is ~30 seconds of retry delay and 145 wasted rate-limit tokens that reduce budget available for concurrent operations.

## Decision

**Option D: Batch pacing for hierarchy warming Phase 1.**

Replace the unbounded `asyncio.gather()` dispatch in `unified.py` with batched dispatch and inter-batch sleep, mirroring the pagination pacing pattern already proven in `progressive.py`.

Three configuration constants control pacing:

| Constant | Value | Purpose |
|----------|-------|---------|
| `HIERARCHY_PACING_THRESHOLD` | 100 | Minimum unique parents before pacing activates |
| `HIERARCHY_BATCH_SIZE` | 50 | Parents dispatched per batch |
| `HIERARCHY_BATCH_DELAY` | 1.0s | Sleep between batches |

### Semaphore Interaction

Batch pacing is **additive** to the existing `hierarchy_semaphore(10)`, not a replacement. A batch of 50 parent fetches still flows through the semaphore as 5 waves of 10 concurrent requests. The inter-batch delay inserts a pause *between batches of 50*, ensuring that successive waves do not overlap at the transport layer. The semaphore continues to provide its existing concurrency ceiling within each batch.

### Phase 2 Analysis: No Changes Needed

`warm_ancestors_async` (Phase 2) already exhibits sufficient natural batching via BFS level-by-level processing. Each depth level gathers its coroutines through `_gather_with_limit()`, which uses the same `hierarchy_semaphore(10)`. Because ancestor sets are smaller per-level and processing is sequential across levels, burst density never reaches the threshold that triggers 429s. No pacing changes are required for Phase 2.

### No Checkpointing (Conscious Decision)

Unlike pagination (where mid-section failure loses 5,000+ accumulated rows), hierarchy warming is fully idempotent. Parents already resolved are cached; a Lambda timeout followed by re-invocation simply re-fetches any uncached parents at negligible cost. The complexity of a checkpoint mechanism is not justified for this workload.

## Alternatives Considered

### Option A: Reduce hierarchy concurrency to 3

Reduce `hierarchy_semaphore` from 10 to 3, limiting burst size below Asana's instantaneous tolerance.

**Rejected because**: Proportionally slows hierarchy warming for all builds (~3x slower). For 2,233 parents, estimated increase from ~90s to ~270s. Penalizes small sections unnecessarily.

### Option B: Inter-request jitter (50ms per request)

Add a 50ms `asyncio.sleep()` inside `_fetch_parent()` to spread 10 concurrent requests across a ~500ms window.

**Rejected because**: Adds 12s fixed overhead but does not structurally prevent bursts when the semaphore releases a new wave. Less predictable than batch pacing. Not consistent with established patterns in the codebase.

### Option C: Sliding window rate limiter

Replace the token bucket in `AsanaHttpClient` with a sliding-window limiter that enforces per-second limits (e.g., max 20 req/sec) rather than per-minute averages.

**Deferred, not rejected**: This is the structurally correct solution at the platform level (`autom8y_http`) but requires cross-project changes. Option D provides equivalent protection for hierarchy warming without platform-level modification. Option C remains valid future work if 429s emerge in other request patterns.

## Changes

| File | Change |
|------|--------|
| `src/autom8_asana/config.py` | Add 3 pacing constants: `HIERARCHY_PACING_THRESHOLD`, `HIERARCHY_BATCH_SIZE`, `HIERARCHY_BATCH_DELAY` |
| `src/autom8_asana/cache/unified.py` | Replace `asyncio.gather(*all_parents)` with batched dispatch loop and inter-batch sleep in Phase 1 |
| `src/autom8_asana/cache/hierarchy_warmer.py` | Remove dead code: `_is_rate_limit_error()` method, `backoff_event` parameter and all references |
| `src/autom8_asana/transport/asana_http.py` | Add structured warning log on 429 receipt (before retry) for observability |
| `tests/unit/cache/test_hierarchy_pacing.py` | New test file: pacing activation threshold, batch sizing, delay insertion |
| `tests/unit/cache/test_hierarchy_warmer.py` | Remove `backoff_event` test references to match dead-code removal |

## Consequences

### Positive

- **Eliminates 429 bursts**: Batch pacing prevents micro-burst request patterns that exceed Asana's instantaneous rate limit
- **Recovers ~30s of retry overhead**: No more wasted time on retry backoff for the CONTACTS build
- **Preserves rate budget**: 145 fewer wasted tokens available for concurrent pagination and other reads
- **Consistent pattern**: Uses the same batch-and-sleep approach proven in `progressive.py` pagination pacing
- **Tunable**: All three constants are configurable without code changes
- **Dead code removal**: Cleaning up the unreachable `backoff_event` logic reduces cognitive overhead for future maintainers

### Negative

- **~44 seconds additional wall time for large builds**: CONTACTS (2,233 parents) incurs `ceil(2233/50) - 1 = 44` inter-batch pauses at 1.0s each. This extends a 427s build to ~471s, well within the 900s Lambda timeout. Smaller builds (below `HIERARCHY_PACING_THRESHOLD=100`) are unaffected.
- **Threshold tuning may be needed**: The 100-parent threshold and 50-batch size are based on CONTACTS data. Other entity types with different parent distributions may need adjustment.

### Neutral

- **No production data model changes**: Only execution pacing is modified
- **No new dependencies**: Uses standard library `asyncio.sleep()` and existing configuration patterns

## Overhead Budget

| Entity | Unique Parents | Batches | Inter-batch Pauses | Added Time | Total Build (est.) | Lambda Headroom |
|--------|---------------|---------|---------------------|------------|-------------------|----------------|
| CONTACTS | 2,233 | 45 | 44 | ~44s | ~471s | 429s remaining |
| OFFERS | ~800 | 16 | 15 | ~15s | ~180s | 720s remaining |
| UNITS | ~400 | 8 | 7 | ~7s | ~120s | 780s remaining |

All entity types remain well within the 900s Lambda timeout.

## Rollback

Single-commit revert restores original `asyncio.gather()` dispatch and `backoff_event` code. The only observable regression would be the return of 429 retry noise in logs and ~30s of wasted retry time for large builds.
