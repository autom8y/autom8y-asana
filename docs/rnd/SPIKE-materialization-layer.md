# SPIKE: DataFrame Materialization Layer

**Date**: 2026-01-01
**Status**: Complete (Revised)
**Author**: rnd-pack (Technology Scout, Integration Researcher, Moonshot Architect)
**Timebox**: 1 day (standard spike)
**Upstream**: SPIKE-entity-resolver-timeout

---

## Executive Summary

This spike evaluated architectural options for eliminating DataFrame cold-start latency and inefficient full-rebuild patterns.

**Question**: What architecture should autom8_asana adopt for efficient DataFrame caching across all services?

**Answer**: **Centralized Watermark Repository + `modified_since` Incremental Sync** with optional S3 baseline persistence.

### Key Insight (Revised)

The original analysis assumed a fixed "30s cold start" - this was incorrect. **Cold starts scale with project size**:

| Project Size | Cold Start Time |
|--------------|-----------------|
| 100 tasks | 3-5 seconds |
| 1,000 tasks | 22-30 seconds |
| 5,000 tasks | 100-150 seconds |
| 10,000+ tasks | **200-300 seconds (MINUTES)** |

The real problem is NOT about sub-millisecond latency. It's about:
1. **Multi-minute cold rebuilds** for large projects
2. **Full rebuilds on every TTL expiry** - even when only 1 task changed
3. **`modified_since` is available but unused** - the infrastructure exists, we just don't use it

---

## Context

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| First request latency | 3s-300s (scales with project size) | <5s (incremental refresh) |
| Refresh strategy | FULL rebuild on TTL expiry | Incremental via `modified_since` |
| Task scale | 100K+ tasks, 4 entity types | Extensible to 10+ entities |
| Freshness SLA | Hourly full rebuild (wasteful) | Incremental sync (efficient) |
| Infrastructure | AWS ECS, S3 | Same (no Redis needed) |

### Root Cause (Revised Understanding)

Two distinct problems:

1. **Cold Start**: `_gid_index_cache` starts empty on container boot. First request triggers full Asana API fetch (3s-300s depending on project size).

2. **Inefficient Refresh**: Every hour (TTL expiry), some unlucky request triggers a FULL rebuild - even if only 1 task changed. The `modified_since` parameter exists in `tasks.list_async()` but is **never used**.

### Code Evidence

```python
# src/autom8_asana/clients/tasks.py:574-639
async def list_async(
    self,
    ...
    modified_since: datetime | str | None = None,  # AVAILABLE BUT UNUSED
) -> list[TaskModel]:
```

```python
# src/autom8_asana/dataframes/builders/project.py
_BASE_OPT_FIELDS = [
    "modified_at",  # Already fetched! Just not used for filtering
    ...
]
```

### All DataFrame Consumers (Central Pattern)

| Consumer | Location | Impact |
|----------|----------|--------|
| Entity Resolver | `services/resolver.py` | 30s-300s cold start |
| Search Service | `services/search.py` | Same rebuild pattern |
| API Routes | `routes/*.py` | Same rebuild pattern |
| Model Methods | `models/*.py` | Same rebuild pattern |

**All consumers would benefit from centralized incremental sync.**

---

## Options Evaluated (Revised)

| Option | Description |
|--------|-------------|
| **A** | Startup Preloading Only |
| **B** | Startup Preloading + `modified_since` Incremental Sync |
| **C** | Option B + S3 Baseline Persistence |
| ~~D~~ | ~~Redis Hot Cache~~ (OVERKILL - eliminated) |
| ~~E~~ | ~~Hybrid S3 + Redis~~ (OVERKILL - eliminated) |

**Why Redis was eliminated**: 1-2 second latency is acceptable for service-to-service calls. Sub-millisecond latency via Redis adds $12+/month operational complexity for no meaningful user benefit.

---

## Comparison Matrix (Revised)

### Evaluation Criteria

| Criterion | A | B | C |
|-----------|---|---|---|
| **Cold start elimination** | Partial | Full | Full |
| **Asana API efficiency** | Poor | Excellent | Excellent |
| **Operational simplicity** | Excellent | Good | Good |
| **Restart resilience** | None | None | Full |
| **Central infrastructure** | No | Yes | Yes |

### Implementation Metrics

| Metric | A | B | C |
|--------|---|---|---|
| **Effort (days)** | 1-2 | 3-4 | 5-6 |
| **Monthly Cost** | $0 | $0 | ~$0.65 |
| **Code Reuse** | 95% | 80% | 75% |
| **Confidence** | High | High | High |
| **Risk** | Low | Low | Low |

### What Each Option Solves

| Problem | A | B | C |
|---------|---|---|---|
| First request cold start | ✓ | ✓ | ✓ |
| Hourly full rebuild | ✗ | ✓ | ✓ |
| Multi-minute large project cold start | Partial | ✓ | ✓ |
| Container restart cold start | ✗ | ✗ | ✓ |
| Central pattern for all consumers | ✗ | ✓ | ✓ |

---

## Architecture Diagrams

### Current State (Problem)

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT: Full Rebuild                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Container Start          Every Hour (TTL Expiry)              │
│        │                           │                             │
│        ▼                           ▼                             │
│   ┌─────────┐              ┌─────────────────┐                  │
│   │ Cache   │              │   FULL REBUILD  │  ◀── 30s-300s    │
│   │ EMPTY   │              │  (all tasks)    │      per project │
│   └────┬────┘              └────────┬────────┘                  │
│        │                            │                            │
│        ▼                            ▼                            │
│   First Request              Some Unlucky                        │
│   = FULL BUILD               Request = SLOW                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Option B: Centralized Watermark + Incremental Sync (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│            RECOMMENDED: Watermark + modified_since              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Watermark Repository (Central)              │   │
│   │  { "unit_project": "2026-01-01T10:30:00Z", ... }        │   │
│   └─────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│              ┌──────────────┴──────────────┐                    │
│              ▼                              ▼                    │
│   ┌──────────────────┐          ┌──────────────────┐            │
│   │  Entity Resolver │          │  Search Service  │            │
│   │  (consumer)      │          │  (consumer)      │            │
│   └────────┬─────────┘          └────────┬─────────┘            │
│            │                              │                      │
│            ▼                              ▼                      │
│   ┌──────────────────────────────────────────────────────┐      │
│   │  Incremental Sync: tasks.list(modified_since=wmark) │      │
│   │  → Only fetch changed tasks (seconds, not minutes)  │      │
│   └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Option C: Add S3 Baseline (For Restart Resilience)

```
┌─────────────────────────────────────────────────────────────────┐
│            OPTIONAL: S3 Baseline + Watermark Sync               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Container Restart                 Normal Refresh              │
│        │                                 │                       │
│        ▼                                 ▼                       │
│   ┌─────────────┐                 ┌─────────────────┐           │
│   │  Load from  │                 │   Incremental   │           │
│   │  S3 (1-2s)  │                 │   modified_since│           │
│   └──────┬──────┘                 └────────┬────────┘           │
│          │                                  │                    │
│          ▼                                  ▼                    │
│   ┌─────────────┐                 ┌─────────────────┐           │
│   │  Incremental│                 │  Merge deltas   │           │
│   │  catch-up   │                 │  into DataFrame │           │
│   └─────────────┘                 └─────────────────┘           │
│                                                                  │
│   Monthly cost: ~$0.65 (S3 storage + minimal requests)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Estimates

| Component | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Infrastructure | $0 | $0 | ~$0.65/mo |
| S3 Storage | - | - | $0.28 |
| S3 Requests | - | - | $0.36 |
| Redis/ElastiCache | - | - | $0 |
| **Monthly Total** | **$0** | **$0** | **~$0.65** |
| **Annual Total** | **$0** | **$0** | **~$7.80** |

---

## Recommendation

### Single-Phase Approach: Option B (Watermark + Incremental Sync)

**Goal**: Eliminate both cold-start latency AND inefficient hourly full rebuilds with centralized infrastructure that benefits all DataFrame consumers.

**Why Option B over Option A**:
- Option A only fixes first-request cold start
- Option A still does FULL rebuilds every hour (30s-300s penalty)
- Option B fixes BOTH problems with only 1-2 days more effort

**Why Option B over Option C**:
- 1-2 containers with rare restarts means S3 persistence provides minimal benefit
- Option C can be added later if restart frequency increases

### Implementation

#### Phase 1: Watermark Repository (1 day)

```python
# src/autom8_asana/dataframes/watermark.py (NEW)
from datetime import datetime
from typing import Dict

class WatermarkRepository:
    """Centralized watermark tracking for incremental sync."""

    def __init__(self):
        self._watermarks: Dict[str, datetime] = {}

    def get_watermark(self, project_gid: str) -> datetime | None:
        """Get last sync timestamp for project."""
        return self._watermarks.get(project_gid)

    def set_watermark(self, project_gid: str, timestamp: datetime) -> None:
        """Update watermark after successful sync."""
        self._watermarks[project_gid] = timestamp

# Global instance (or inject via app.state)
_watermark_repo = WatermarkRepository()
```

#### Phase 2: Incremental Sync in DataFrame Builder (2 days)

```python
# src/autom8_asana/dataframes/builders/project.py
async def refresh_incremental(
    self,
    client: AsanaClient,
    watermark: datetime | None,
) -> pl.DataFrame:
    """Fetch only tasks modified since watermark."""
    if watermark is None:
        # First sync - full fetch
        return await self.build_with_parallel_fetch_async(client)

    # Incremental fetch - only changed tasks
    modified_tasks = await client.tasks.list_async(
        project_gid=self.project.gid,
        modified_since=watermark,  # <-- KEY: Use the available parameter!
    )

    # Merge into existing DataFrame
    return self._merge_deltas(modified_tasks)
```

#### Phase 3: Wire into Resolver (1 day)

```python
# src/autom8_asana/services/resolver.py
async def _get_or_build_index(self, project_gid, client):
    from autom8_asana.dataframes.watermark import _watermark_repo

    cached_index = _gid_index_cache.get(project_gid)
    watermark = _watermark_repo.get_watermark(project_gid)

    if cached_index is not None and not cached_index.is_stale(_INDEX_TTL_SECONDS):
        return cached_index

    # INCREMENTAL refresh instead of full rebuild
    df = await self._refresh_dataframe_incremental(project_gid, client, watermark)

    # Update watermark to now
    _watermark_repo.set_watermark(project_gid, datetime.utcnow())

    # Build index from updated DataFrame
    ...
```

### Changes Required

1. Create `WatermarkRepository` class (`dataframes/watermark.py`)
2. Add `refresh_incremental()` to `ProjectDataFrameBuilder`
3. Update `_get_or_build_index()` to use incremental sync
4. Add startup preloading to `main.py` lifespan
5. Update health check to return 503 until ready

### Metrics (Expected)

| Metric | Before | After |
|--------|--------|-------|
| Cold start (first request) | 30s-300s | 0ms |
| Hourly refresh | 30s-300s FULL | 1-5s INCREMENTAL |
| API calls per refresh | 100% tasks | ~1-5% changed |
| Affected consumers | All services | All services ✓ |
| Monthly cost | $0 | $0 |
| Effort | - | 3-4 days |

---

## Why Not Other Options

| Option | Disqualifier |
|--------|--------------|
| **A (Startup Only)** | Doesn't fix hourly full rebuild - just shifts 30s-300s to startup |
| **C (+ S3 Baseline)** | Nice-to-have but unnecessary with 1-2 containers, rare restarts |
| **Redis Hot Cache** | OVERKILL: 1-2s latency is fine; $12+/month for no user benefit |
| **Webhooks** | At-most-once delivery; eventual consistency adds complexity |

---

## Migration Plan

### Week 1: Full Implementation (3-4 days)

| Day | Task | Owner |
|-----|------|-------|
| 1 | Create `WatermarkRepository` class | Engineer |
| 1 | Add startup preloading to `main.py` | Engineer |
| 2 | Implement `refresh_incremental()` in builder | Engineer |
| 2 | Add delta merge logic for DataFrames | Engineer |
| 3 | Wire incremental sync into resolver | Engineer |
| 3 | Update health check for "warming" state | Engineer |
| 4 | Testing, deployment to staging | QA |
| 4 | Deploy to production | DevOps |

**Rollback**: Remove watermark usage, revert to full rebuild (2-way door)

---

## Success Criteria

### Implementation Complete

- [ ] First request latency < 500ms after container ready
- [ ] Container starts within ECS health check timeout (60s)
- [ ] Hourly refresh completes in < 5 seconds (not 30s-300s)
- [ ] Asana API calls reduced by 90%+ (incremental sync)
- [ ] WatermarkRepository tracks all project sync timestamps
- [ ] All DataFrame consumers benefit from central pattern

---

## Observable Signals (Post-Implementation)

| Signal | Threshold | Action |
|--------|-----------|--------|
| Task count | >500K | Scale optimization (partitioning) |
| Incremental refresh time P95 | >10s | Investigate watermark gaps |
| modified_since miss rate | >10% | Check watermark persistence |
| User staleness complaints | >3/month | Consider webhooks or shorter TTL |
| Asana API announcements | Streaming/GraphQL | Evaluate early adoption |

---

## Artifacts Produced

| Artifact | Path | Agent |
|----------|------|-------|
| Tech Assessment | `docs/rnd/SCOUT-dataframe-materialization.md` | Technology Scout |
| Integration Map | `docs/rnd/INTEGRATE-dataframe-materialization.md` | Integration Researcher |
| Moonshot Plan | `docs/rnd/MOONSHOT-dataframe-materialization.md` | Moonshot Architect |
| Spike Report (Revised) | `docs/rnd/SPIKE-materialization-layer.md` | Orchestrator |

---

## Follow-Up Actions

1. **Immediate**: Begin implementation (Watermark Repository + Incremental Sync)
2. **Week 1**: Complete all phases, deploy to production
3. **Week 2**: Monitor metrics, validate 90%+ API reduction
4. **Future (if needed)**: Add S3 baseline persistence for restart resilience

---

## References

### Codebase (Key Files)
- `src/autom8_asana/services/resolver.py` - `_gid_index_cache`, `GidLookupIndex`, `_get_or_build_index()`
- `src/autom8_asana/clients/tasks.py:574-639` - `list_async()` with `modified_since` parameter
- `src/autom8_asana/dataframes/builders/project.py` - `ProjectDataFrameBuilder`, `_BASE_OPT_FIELDS`
- `src/autom8_asana/dataframes/builders/parallel_fetch.py` - `ParallelSectionFetcher`
- `src/autom8_asana/dataframes/cache_integration.py` - `is_version_current()` pattern

### Asana API
- [Asana Rate Limits](https://developers.asana.com/docs/rate-limits)
- [Tasks API - modified_since parameter](https://developers.asana.com/docs/get-tasks-from-a-project)

### Related Spikes
- `docs/spikes/SPIKE-entity-resolver-timeout.md` - Original timeout investigation

---

## Revision History

| Date | Change | Reason |
|------|--------|--------|
| 2026-01-01 | Initial spike | Over-engineered with Redis hot cache |
| 2026-01-01 | **Revised** | Corrected understanding: cold starts scale 3s-300s, `modified_since` is available but unused, central infrastructure benefits all consumers |

---

*Spike completed and revised by rnd-pack team | 2026-01-01*
