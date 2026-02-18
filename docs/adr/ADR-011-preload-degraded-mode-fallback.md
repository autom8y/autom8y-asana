# ADR-011: Progressive-to-Legacy Preload Degraded-Mode Fallback

**Status**: Accepted
**Date**: 2026-02-18
**Deciders**: Architecture review (SI-4 from ARCH-REVIEW-1)

## Context

The `_preload_dataframe_cache_progressive` function in `api/preload/progressive.py` is the primary cache-warming path. It processes projects in parallel using `ProgressiveProjectBuilder`, writing section DataFrames to S3 with resume capability.

When S3 is unavailable (`persistence.is_available == False`), the progressive path cannot function. The system falls back to the legacy preload implementation (`api/preload/legacy.py`, 613 LOC), which performs a full in-memory preload directly from the Asana API without S3 persistence or resume capability.

This fallback path:
- Was not documented in any ADR (ADR-001 through ADR-009 exist; none cover preload)
- Had no metrics tracking fallback frequency
- Has materially different performance characteristics than the progressive path
- Was flagged in REFACTORING-PLAN-WS567.md as DC-001

### Why legacy preload still exists

The legacy preload (`_preload_dataframe_cache` in `api/preload/legacy.py`) is the original cache-warming implementation. It was retained as a degraded-mode fallback when the progressive path was introduced because:

1. **S3 reliability is not yet proven** in production. The progressive path depends on S3 for section persistence, manifest tracking, and resume. If S3 is down or misconfigured, the application would start with no cached data at all.
2. **Cold start criticality**: The preload runs during FastAPI startup (`lifespan`). A cold start with no cached data causes the first user requests to trigger full project builds, which can take minutes. The legacy path, while slower and less resilient, still populates the in-memory DataFrame cache.
3. **No alternative degraded mode exists**: Without the legacy fallback, S3 unavailability means zero cached data until a user request triggers an on-demand build.

### Performance delta

| Characteristic | Progressive | Legacy |
|---------------|------------|--------|
| S3 dependency | Required | None |
| Resume on restart | Yes (manifest) | No (full refetch) |
| Section-level writes | Yes (progressive to S3) | No (all-at-once) |
| Concurrency | 3 projects parallel | Sequential projects |
| Memory profile | Bounded (per-section) | Unbounded (full project in memory) |
| Heartbeat monitoring | Yes (30s intervals) | No |
| Build result classification | Yes (per-section outcomes) | No |

## Decision

**Maintain the legacy preload as the degraded-mode fallback until S3 reliability is proven in production.**

The fallback trigger point is at `progressive.py` lines 250-264:

```python
if not persistence.is_available:
    logger.warning("preload_legacy_fallback_activated", ...)
    await _preload_dataframe_cache(app)
    return
```

### Monitoring requirements

To track how often the fallback activates and inform the decision to eventually remove it:

1. **Structured log metric**: A WARNING-level structured log with event name `preload_legacy_fallback_activated` is emitted each time the fallback triggers. This serves as the metric counter (the codebase uses structured logging as its metrics pattern -- no Prometheus/StatsD is deployed).

2. **Retirement criteria**: The legacy preload can be removed when:
   - S3 availability has been >= 99.9% for 90 consecutive days in production
   - The `preload_legacy_fallback_activated` event has not fired in 90 days
   - An alternative degraded mode is implemented (e.g., on-demand build with circuit breaker)

## Consequences

### Positive
- The application always starts with cached data, even when S3 is unavailable
- The fallback is now documented and monitored (previously invisible)
- Clear retirement criteria prevent indefinite maintenance of 613 LOC

### Negative
- 613 LOC of legacy preload must be maintained alongside the progressive path
- The two preload paths can diverge (e.g., legacy doesn't support cascade resolution via shared store)
- Legacy path has no resume capability -- container restart during legacy preload loses all progress

### Neutral
- The fallback only activates when `persistence.is_available` returns False, which requires S3 to be unreachable or misconfigured
- The `MutationInvalidator` invalidation logic is unaffected (both paths populate the same `DataFrameCache` singleton)

## References

- `src/autom8_asana/api/preload/progressive.py`: Progressive preload with fallback trigger (lines 250-264)
- `src/autom8_asana/api/preload/legacy.py`: Legacy preload implementation (613 LOC)
- REFACTORING-PLAN-WS567.md DC-001: Flagged legacy preload as active degraded-mode fallback
- ADR-010: Cache system divergence assessment (related -- documents the broader cache architecture)
