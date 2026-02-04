# TDD: DataFrame Build Coalescing

**TDD ID**: TDD-BUILD-COALESCING-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**Sprint**: S4-003
**PRD Reference**: Architectural Opportunities Initiative, Sprint 4
**Spike References**: S0-006 (Concurrent Build Frequency Analysis)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Current Architecture Analysis](#current-architecture-analysis)
5. [Proposed Architecture](#proposed-architecture)
6. [Component Design: BuildCoordinator](#component-design-buildcoordinator)
7. [Coalescing Key Design](#coalescing-key-design)
8. [Staleness-Aware Coalescing Rules](#staleness-aware-coalescing-rules)
9. [Timeout and Cancellation Semantics](#timeout-and-cancellation-semantics)
10. [Deadlock Prevention Analysis](#deadlock-prevention-analysis)
11. [Integration with Existing Build Pipeline](#integration-with-existing-build-pipeline)
12. [Metrics and Observability](#metrics-and-observability)
13. [Implementation Phases](#implementation-phases)
14. [Interface Contracts](#interface-contracts)
15. [Data Flow Diagrams](#data-flow-diagrams)
16. [Test Strategy](#test-strategy)
17. [Risk Assessment](#risk-assessment)
18. [ADRs](#adrs)
19. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies a `BuildCoordinator` that unifies DataFrame build deduplication across all code paths in `autom8_asana`. Currently, the existing `DataFrameCacheCoalescer` (in `cache/dataframe/coalescer.py`) correctly prevents thundering herd for the `@dataframe_cache` decorator path, but three secondary build paths bypass it entirely. This design wraps the `DataFrameCacheCoalescer` with a higher-level coordinator that intercepts **all** build triggers, integrates with `MutationInvalidator` staleness signals, and surfaces coalescing metrics.

### Solution Summary

| Component | Purpose |
|-----------|---------|
| `BuildCoordinator` | Single entry point for all DataFrame build requests; deduplicates using asyncio futures |
| `CoalescingKey` | Named tuple `(project_gid, entity_type)` for build identity |
| `BuildRequest` | Metadata about a build request (caller, staleness context, timestamp) |
| `BuildResult` | Typed result carrying DataFrame or error, shared across coalesced waiters |
| Staleness gate | Rejects coalescing when `MutationInvalidator` has soft-invalidated the in-flight build's data |

---

## Problem Statement

### Current State

Per spike S0-006 (Concurrent Build Frequency Analysis), there are **six entry points** that can trigger a DataFrame build for a given `(project_gid, entity_type)`:

1. **Resolve endpoint** (`POST /v1/resolve/{entity_type}`) -- through `@dataframe_cache` decorator
2. **Query endpoint** (`POST /v1/query/{entity_type}`) -- through `UniversalResolutionStrategy._get_dataframe()`
3. **Query rows endpoint** (`POST /v1/query/{entity_type}/rows`) -- through `QueryEngine` -> `EntityQueryService`
4. **Admin cache refresh** (`POST /v1/admin/cache/refresh`) -- through `_perform_cache_refresh()` background task
5. **Startup preload** (`_preload_dataframe_cache_progressive()`) -- through `ProgressiveProjectBuilder`
6. **SWR background refresh** (`_trigger_swr_refresh()`) -- through coalescer-aware `asyncio.create_task`

### The Dual-Path Gap

S0-006 Section 2.2 identifies two distinct build mechanisms with **no mutual coordination**:

| Path | Mechanism | Coalescing? |
|------|-----------|-------------|
| Resolve endpoint | `@dataframe_cache` decorator -> `DataFrameCacheCoalescer.try_acquire_async()` | YES |
| Query/SWR endpoints | `UniversalResolutionStrategy._get_dataframe()` -> delegates to legacy strategy -> decorator | YES (indirectly) |
| `_build_entity_dataframe()` direct | `UniversalResolutionStrategy._build_entity_dataframe()` called by `CacheWarmer` | NO |
| Admin refresh | `ProgressiveProjectBuilder.build_progressive_async()` directly | NO |
| Startup preload | `ProgressiveProjectBuilder.build_progressive_async()` directly | NO (gated by health check) |

The query path delegates to the legacy strategy's `resolve()` method, which enters the `@dataframe_cache` decorator. This means the **coalescer does protect the query path indirectly**. However:

- `_build_entity_dataframe()` when called by `CacheWarmer` bypasses the coalescer entirely
- Admin refresh creates a `ProgressiveProjectBuilder` directly with no lock
- If a mutation invalidation fires during an in-flight build, the build result is stale -- but the coalescer does not check for this

### Impact

Per S0-006 Section 4.2:

| Impact | Severity | Notes |
|--------|----------|-------|
| Duplicate Asana API calls | MEDIUM | Each build fetches all tasks from all sections; rate limit risk |
| Memory spike | LOW-MEDIUM | Two concurrent builds roughly double memory for that entity (~5-50MB) |
| Serving stale data post-mutation | MEDIUM | Coalesced build started before mutation, result served to all waiters |
| Asana API rate limiting | MEDIUM | Multiple concurrent builds multiply API calls |

### Risk Assessment from S0-006

Overall risk: **LOW** -- the existing coalescer handles the primary paths. The real value of A3 is:
1. Unifying all build paths through a single coordinator
2. Staleness-aware coalescing (do not serve pre-mutation build results)
3. Surfacing coalescing metrics for operational visibility

---

## Goals and Non-Goals

### Goals

| ID | Goal | Gap Addressed |
|----|------|---------------|
| G1 | All DataFrame build paths go through a single `BuildCoordinator` | Eliminates uncoordinated builds from warmer, admin, and direct calls |
| G2 | Concurrent callers for the same `(project_gid, entity_type)` await a single build result | Extends existing coalescer behavior to all paths |
| G3 | Mutation-invalidated builds are not coalesced -- new build triggered | Prevents serving stale data to waiters when mutation fires mid-build |
| G4 | Timeout-bounded waits with explicit cancellation semantics | Prevents unbounded waits; callers get clear timeout errors |
| G5 | Metrics for coalesced vs. new builds, wait times, timeout rates | Enables operational monitoring of build coordination |
| G6 | No deadlocks under any combination of concurrent callers | Proven safe through analysis and adversarial tests |

### Non-Goals

| ID | Non-Goal | Reasoning |
|----|----------|-----------|
| NG1 | Cross-process build coordination (DynamoDB locks) | Single ECS task architecture; unnecessary complexity |
| NG2 | API gateway-level request deduplication | Each request is distinct; coalescing happens at build level |
| NG3 | Cross-entity-type build coordination | Entity types have different project GIDs; coalescer keys are already distinct |
| NG4 | Replacing `DataFrameCacheCoalescer` | Wrap and extend, do not replace; preserve existing proven behavior |

---

## Current Architecture Analysis

### DataFrameCacheCoalescer (Existing)

Location: `src/autom8_asana/cache/dataframe/coalescer.py`

The existing coalescer implements a first-builds-others-wait pattern:

```
try_acquire_async(key) -> bool
  |
  +-- True: caller builds, then calls release_async(key, success)
  |
  +-- False: caller calls wait_async(key, timeout) -> bool
              |
              +-- True: build succeeded, read from cache
              +-- False: timeout or failure
```

**Strengths**: Correct asyncio.Event-based notification, timeout support, statistics tracking.

**Limitations**:
- Only accessible through `DataFrameCache.acquire_build_lock_async()` -- not usable by direct `ProgressiveProjectBuilder` callers
- No staleness awareness -- if a mutation fires between acquire and release, all waiters receive pre-mutation data
- No cancellation semantics -- timed-out waiters cannot signal the builder to abort
- Cleanup delay (5 seconds) can allow brief window where stale BuildState is readable

### MutationInvalidator (Existing)

Location: `src/autom8_asana/cache/integration/mutation_invalidator.py`

Fire-and-forget invalidation from REST mutation endpoints. Relevant interactions:
- `invalidate_project()` calls `DataFrameCache.invalidate_project()` which clears memory tier
- Soft invalidation applies `staleness_hint` to `FreshnessStamp` without evicting

**Key insight**: If a mutation fires while a build is in-flight, the build will complete and `put_async()` will overwrite the invalidation with a stale result. The `BuildCoordinator` must detect this race.

---

## Proposed Architecture

### High-Level Design

```
                 All Build Callers
                       |
                       v
              +------------------+
              | BuildCoordinator |  <-- Single entry point
              +------------------+
                  |          |
        +---------+          +---------+
        |                              |
   [key in-flight?]              [key NOT in-flight]
        |                              |
   [staleness check]            [create Future]
        |         |                    |
   [stale]    [fresh]            [execute build]
        |         |                    |
   [new build] [await]           [put result in Future]
                  |                    |
             [return result]     [notify all waiters]
```

### Integration Points

```
BEFORE (6 entry points, 2 coordination mechanisms):

  resolve -> decorator -> coalescer ---|
  query -> universal -> legacy -> decorator -> coalescer ---|-- DataFrameCacheCoalescer
  SWR -> coalescer.is_building() check -> coalescer ---|
  warmer -> _build_entity_dataframe() --- UNCOORDINATED
  admin -> ProgressiveProjectBuilder --- UNCOORDINATED
  startup -> ProgressiveProjectBuilder --- UNCOORDINATED (health-gated)


AFTER (6 entry points, 1 coordination mechanism):

  resolve -> decorator -> BuildCoordinator ---|
  query -> universal -> BuildCoordinator ---|
  SWR -> BuildCoordinator ---|
  warmer -> BuildCoordinator ---|                          -- BuildCoordinator
  admin -> BuildCoordinator ---|                              (wraps coalescer)
  startup -> BuildCoordinator ---|
```

---

## Component Design: BuildCoordinator

### Class Definition

```python
# Location: src/autom8_asana/cache/dataframe/build_coordinator.py

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Awaitable

if TYPE_CHECKING:
    import polars as pl
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp


class BuildOutcome(str, Enum):
    """Outcome of a build request."""
    BUILT = "built"           # This caller performed the build
    COALESCED = "coalesced"   # This caller waited on an existing build
    TIMED_OUT = "timed_out"   # Wait exceeded timeout
    FAILED = "failed"         # Build failed with exception
    STALE_REJECTED = "stale_rejected"  # In-flight build was stale; new build started


CoalescingKey = tuple[str, str]  # (project_gid, entity_type)


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Result of a coordinated build."""
    outcome: BuildOutcome
    dataframe: pl.DataFrame | None = None
    watermark: datetime | None = None
    build_duration_ms: float = 0.0
    waiter_count: int = 0
    error: Exception | None = None


@dataclass
class _InFlightBuild:
    """Internal state for a build in progress."""
    future: asyncio.Future[BuildResult]
    started_at: datetime
    waiter_count: int = 0
    invalidated: bool = False  # Set by staleness gate


@dataclass
class BuildCoordinator:
    """Coordinates DataFrame builds to prevent duplicate concurrent work.

    Single entry point for all build requests. Uses asyncio.Future (not Event)
    for result sharing: the builder sets the Future result, and all waiters
    receive the same BuildResult object.

    Attributes:
        coalescer: Underlying DataFrameCacheCoalescer for backward compatibility.
        default_timeout_seconds: Default maximum wait for coalesced builds.
        max_concurrent_builds: Maximum number of simultaneous builds across all keys.
    """

    coalescer: DataFrameCacheCoalescer
    default_timeout_seconds: float = 60.0
    max_concurrent_builds: int = 4

    # Internal state
    _in_flight: dict[CoalescingKey, _InFlightBuild] = field(
        default_factory=dict, init=False
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _build_semaphore: asyncio.Semaphore | None = field(default=None, init=False)
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._build_semaphore = asyncio.Semaphore(self.max_concurrent_builds)
        self._stats = {
            "builds_started": 0,
            "builds_coalesced": 0,
            "builds_succeeded": 0,
            "builds_failed": 0,
            "builds_timed_out": 0,
            "builds_stale_rejected": 0,
        }

    async def build_or_wait_async(
        self,
        key: CoalescingKey,
        build_fn: Callable[[], Awaitable[tuple[pl.DataFrame, datetime]]],
        *,
        timeout_seconds: float | None = None,
        caller: str = "unknown",
    ) -> BuildResult:
        """Request a build, coalescing with any in-flight build for the same key.

        If no build is in-flight for this key, starts one using build_fn.
        If a build is already in-flight AND not staleness-rejected, waits
        for it to complete and returns the same result.

        Args:
            key: (project_gid, entity_type) tuple.
            build_fn: Async callable that performs the build.
                Must return (DataFrame, watermark) tuple.
            timeout_seconds: Maximum wait time. None uses default.
            caller: Identifier for logging (e.g., "decorator", "warmer").

        Returns:
            BuildResult with outcome, DataFrame, and metadata.
        """
        ...

    def mark_invalidated(self, project_gid: str, entity_type: str | None = None) -> int:
        """Mark in-flight builds as invalidated due to mutation.

        Called by MutationInvalidator when a mutation affects a project.
        If entity_type is None, marks all entity types for the project.

        Returns:
            Number of in-flight builds marked invalidated.
        """
        ...

    def is_building(self, key: CoalescingKey) -> bool:
        """Check if a build is in-flight for this key."""
        ...

    def get_stats(self) -> dict[str, int]:
        """Get coordinator statistics."""
        ...
```

### Algorithm: build_or_wait_async

```
async def build_or_wait_async(key, build_fn, timeout, caller):
    timeout = timeout or self.default_timeout_seconds

    async with self._lock:
        if key in self._in_flight:
            existing = self._in_flight[key]
            if not existing.invalidated:
                # Coalesce: wait on existing build
                existing.waiter_count += 1
                self._stats["builds_coalesced"] += 1
                future = existing.future
            else:
                # Existing build is stale -- let it finish but do not
                # wait on it. Start a new build instead.
                self._stats["builds_stale_rejected"] += 1
                # Fall through to start new build
                future = None
        else:
            future = None

        if future is not None:
            # Release lock, then wait
            pass  # see wait path below
        else:
            # Start new build
            loop = asyncio.get_running_loop()
            new_future = loop.create_future()
            self._in_flight[key] = _InFlightBuild(
                future=new_future,
                started_at=datetime.now(UTC),
            )
            self._stats["builds_started"] += 1

    if future is not None:
        # WAIT PATH: await existing future with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.shield(future),
                timeout=timeout,
            )
            return BuildResult(
                outcome=BuildOutcome.COALESCED,
                dataframe=result.dataframe,
                watermark=result.watermark,
                build_duration_ms=result.build_duration_ms,
                waiter_count=result.waiter_count,
            )
        except asyncio.TimeoutError:
            self._stats["builds_timed_out"] += 1
            async with self._lock:
                if key in self._in_flight:
                    self._in_flight[key].waiter_count -= 1
            return BuildResult(outcome=BuildOutcome.TIMED_OUT)

    # BUILD PATH: this caller performs the build
    start = time.perf_counter()
    try:
        async with self._build_semaphore:
            df, watermark = await build_fn()

        duration_ms = (time.perf_counter() - start) * 1000

        result = BuildResult(
            outcome=BuildOutcome.BUILT,
            dataframe=df,
            watermark=watermark,
            build_duration_ms=duration_ms,
        )

        async with self._lock:
            if key in self._in_flight:
                in_flight = self._in_flight[key]
                result = BuildResult(
                    outcome=BuildOutcome.BUILT,
                    dataframe=df,
                    watermark=watermark,
                    build_duration_ms=duration_ms,
                    waiter_count=in_flight.waiter_count,
                )
                in_flight.future.set_result(result)
                del self._in_flight[key]

        self._stats["builds_succeeded"] += 1
        return result

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        result = BuildResult(
            outcome=BuildOutcome.FAILED,
            build_duration_ms=duration_ms,
            error=exc,
        )
        async with self._lock:
            if key in self._in_flight:
                self._in_flight[key].future.set_result(result)
                del self._in_flight[key]
        self._stats["builds_failed"] += 1
        return result
```

### Design Decisions in the Algorithm

1. **`asyncio.Future` instead of `asyncio.Event`**: The existing coalescer uses `Event` which only signals "done" -- waiters must then re-read the cache. `Future` carries the result directly, avoiding a cache read race where the entry could have been evicted between signal and read.

2. **`asyncio.shield()` on wait**: Prevents cancellation of the shared future if one waiter times out. The build continues for other waiters.

3. **`Semaphore` for global concurrency**: Limits total concurrent builds (default 4) to prevent resource exhaustion when many different keys trigger builds simultaneously. This is distinct from per-section semaphores in `ParallelSectionFetcher`.

4. **Stale rejection creates new build, does not cancel existing**: When `mark_invalidated()` sets a build as stale, any NEW waiter gets a fresh build. Existing waiters still receive the stale result -- they were already committed to it, and the cache layer will handle freshness classification downstream.

---

## Coalescing Key Design

### Key Structure

```python
CoalescingKey = tuple[str, str]  # (project_gid, entity_type)
```

### Key Construction

```python
def make_coalescing_key(project_gid: str, entity_type: str) -> CoalescingKey:
    """Create a coalescing key for build coordination.

    Args:
        project_gid: Asana project GID (e.g., "1234567890").
        entity_type: Entity type string (e.g., "unit", "offer", "business").

    Returns:
        Tuple suitable as dict key.
    """
    return (project_gid, entity_type)
```

### Why Not Include More in the Key?

| Candidate | Included? | Reasoning |
|-----------|-----------|-----------|
| `project_gid` | YES | Different projects have different data |
| `entity_type` | YES | Different entity types have different schemas and builders |
| `schema_version` | NO | Schema changes invalidate all caches at deployment time, not per-request |
| `freshness_level` | NO | Freshness is a property of the result, not the build identity |
| `caller_id` | NO | Build identity should not depend on who triggers it |

---

## Staleness-Aware Coalescing Rules

### The Race Condition

```
Time  Build (started T0)              MutationInvalidator
----  -------------------------       ---------------------------
T0    build_fn() starts
T1    fetching sections...            POST /tasks/{gid} -> update
T2    fetching tasks...               fire_and_forget(MutationEvent)
T3    ...                             invalidate_project(project_gid)
T4    build complete                  ...
T5    put_async(stale_df)             (memory tier already cleared at T3)
T6    waiters receive stale_df        (stale data re-cached at T5!)
```

### Solution: Invalidation Flag

When `MutationInvalidator.invalidate_project()` fires, it also calls `BuildCoordinator.mark_invalidated()`:

```python
def mark_invalidated(self, project_gid: str, entity_type: str | None = None) -> int:
    """Mark in-flight builds as invalidated.

    Does NOT cancel the build -- it continues to completion so existing
    waiters are not orphaned. But new arrivals for the same key will
    start a fresh build instead of coalescing.

    The build result carries `invalidated=True` in metadata so the
    cache layer can decide whether to store it (LKG) or discard.
    """
    count = 0
    # No async lock needed -- _in_flight reads are safe under GIL for
    # the boolean flag set. The _lock is only needed for structural
    # mutations (add/remove keys).
    for key, build in self._in_flight.items():
        if key[0] == project_gid:
            if entity_type is None or key[1] == entity_type:
                build.invalidated = True
                count += 1
    return count
```

### Coalescing Rules Matrix

| In-flight state | New request action | Reasoning |
|-----------------|-------------------|-----------|
| No build in-flight | Start new build | Normal case |
| Build in-flight, NOT invalidated | Wait on existing build | Coalescing: avoid duplicate work |
| Build in-flight, invalidated | Start new build (do not wait) | Mutation makes in-flight result stale |
| Build just completed, in cleanup window | Check cache; start new build if miss | Cleanup delay means state may linger |

### Integration with MutationInvalidator

The `MutationInvalidator._invalidate_project_dataframes()` method gains one additional call:

```python
async def _invalidate_project_dataframes(self, project_gids: list[str]) -> None:
    if not self._dataframe_cache:
        return
    for project_gid in project_gids:
        try:
            self._dataframe_cache.invalidate_project(project_gid)
        except Exception as exc:
            logger.warning(...)

        # NEW: mark in-flight builds as invalidated
        if self._build_coordinator is not None:
            marked = self._build_coordinator.mark_invalidated(project_gid)
            if marked > 0:
                logger.info(
                    "in_flight_builds_invalidated",
                    extra={"project_gid": project_gid, "count": marked},
                )
```

---

## Timeout and Cancellation Semantics

### Timeout Strategy

| Parameter | Default | Configurable? | Reasoning |
|-----------|---------|---------------|-----------|
| `default_timeout_seconds` | 60s | YES (constructor) | Matches existing coalescer; cold builds can take 30-50s |
| Per-call `timeout_seconds` | None (use default) | YES (per call) | Decorator path uses 30s; warmer can use longer |
| `max_concurrent_builds` | 4 | YES (constructor) | Bounds resource usage; 4 covers typical 3-4 entity types |

### Timeout Behavior

When a waiter times out:

1. The waiter receives `BuildResult(outcome=BuildOutcome.TIMED_OUT)`
2. The in-flight build continues (not cancelled)
3. The waiter's count is decremented on the `_InFlightBuild`
4. The caller is responsible for error handling (e.g., 503 response)

### Cancellation Semantics

**Explicit cancellation is NOT supported.** Rationale:

- Build cancellation would require cooperative cancellation in `ProgressiveProjectBuilder`, `ParallelSectionFetcher`, and all Asana API clients
- Partial builds leave cache in inconsistent state
- The cost of a redundant build (wasted API calls) is lower than the cost of implementing cancellation through the entire stack
- Timeouts provide implicit cancellation for callers without affecting the build itself

### asyncio.shield Usage

The `asyncio.shield(future)` in the wait path prevents a cancelled waiter from cancelling the shared future. Without shield, if one waiter's task is cancelled (e.g., HTTP client disconnect), the future itself would be cancelled, orphaning all other waiters.

---

## Deadlock Prevention Analysis

### Potential Deadlock Vectors

| Vector | Analysis | Mitigation |
|--------|----------|------------|
| `_lock` held during `build_fn()` | **Not possible**: lock is released before build starts | By design: lock only held for dict operations |
| `_lock` + `_build_semaphore` ordering | `_lock` acquired first, `_build_semaphore` acquired after release | Consistent ordering; no circular dependency |
| `build_fn()` calls `build_or_wait_async()` recursively | Could deadlock if same key re-enters | **Prevented**: `build_fn` is a pure build callable, not a coordinator method |
| Multiple keys creating circular waits | Not possible: waiters only wait on their own key's future | No cross-key dependencies |
| `mark_invalidated()` while `_lock` held | `mark_invalidated()` does NOT acquire `_lock` for the boolean flag set | Safe: boolean write is atomic under GIL; structural mutations use lock |
| `_build_semaphore` starvation | If 4 builds are stuck, new builds queue | Timeout on wait path prevents unbounded blocking; semaphore has no priority inversion |

### Lock Ordering Rules

1. `_lock` is always acquired FIRST when both `_lock` and `_build_semaphore` are needed
2. `_lock` is NEVER held during `build_fn()` execution
3. `_lock` is NEVER held during `asyncio.wait_for()` on the future
4. `mark_invalidated()` uses NO locks (boolean flag set only)

### Proof of Deadlock Freedom

The system has exactly two synchronization primitives: `_lock` (asyncio.Lock) and `_build_semaphore` (asyncio.Semaphore). They are never held simultaneously:

```
build_or_wait_async():
  acquire _lock
    check/modify _in_flight dict
  release _lock        <-- _lock released

  acquire _build_semaphore  <-- only after _lock released
    execute build_fn()
  release _build_semaphore

  acquire _lock
    set future result, cleanup
  release _lock
```

No code path acquires `_lock` while holding `_build_semaphore` or vice versa in a way that could create circular wait.

---

## Integration with Existing Build Pipeline

### Phase 1: Wrap the Decorator Path

The `@dataframe_cache` decorator (`cache/dataframe/decorator.py`) currently calls `DataFrameCache.acquire_build_lock_async()` directly. Update it to call `BuildCoordinator.build_or_wait_async()` instead:

```python
# In decorator.py: cached_resolve()

# BEFORE:
acquired = await cache.acquire_build_lock_async(project_gid, entity_type)
if not acquired:
    entry = await cache.wait_for_build_async(project_gid, entity_type, timeout_seconds=30.0)
    ...

# AFTER:
coordinator = cache.build_coordinator  # New property on DataFrameCache
key = (project_gid, entity_type)

async def _do_build():
    build_func = getattr(self, build_method, None)
    ...
    build_result = await build_func(project_gid, client)
    ...
    await cache.put_async(project_gid, entity_type, df, watermark)
    return df, watermark

result = await coordinator.build_or_wait_async(
    key, _do_build, timeout_seconds=30.0, caller="decorator"
)

if result.outcome == BuildOutcome.TIMED_OUT:
    raise HTTPException(status_code=503, detail=...)
elif result.outcome == BuildOutcome.FAILED:
    raise HTTPException(status_code=503, detail=...)
else:
    self._cached_dataframe = result.dataframe
    return await original_resolve(self, criteria, project_gid, client)
```

### Phase 2: Wrap UniversalResolutionStrategy

The `_get_dataframe()` method on `UniversalResolutionStrategy` (lines 396-459) currently has its own cache-check-then-build logic. Replace the build path:

```python
# In universal_strategy.py: _get_dataframe()

# BEFORE (line 430-457): direct legacy_strategy.resolve([]) call
# AFTER:
coordinator = cache.build_coordinator
key = (project_gid, self.entity_type)

async def _do_build():
    df = await self._build_entity_dataframe(project_gid, client)
    watermark = datetime.now(UTC)
    if df is not None:
        await cache.put_async(project_gid, self.entity_type, df, watermark)
    return df, watermark

result = await coordinator.build_or_wait_async(
    key, _do_build, timeout_seconds=60.0, caller="universal_strategy"
)

if result.outcome in (BuildOutcome.BUILT, BuildOutcome.COALESCED):
    return result.dataframe
return None
```

### Phase 3: Wrap CacheWarmer and Admin Refresh

Both `CacheWarmer` and admin refresh call `_build_entity_dataframe()` or `ProgressiveProjectBuilder` directly. Wrap these calls:

```python
# In warmer.py and admin.py:
coordinator = dataframe_cache.build_coordinator
key = (project_gid, entity_type)

async def _do_build():
    # existing build logic
    ...
    return df, watermark

result = await coordinator.build_or_wait_async(
    key, _do_build, timeout_seconds=120.0, caller="warmer"
)
```

### Phase 4: Integrate MutationInvalidator

Add `BuildCoordinator` reference to `MutationInvalidator.__init__()`:

```python
class MutationInvalidator:
    def __init__(
        self,
        cache_provider: CacheProvider,
        dataframe_cache: DataFrameCache | None = None,
        soft_config: SoftInvalidationConfig | None = None,
        build_coordinator: BuildCoordinator | None = None,  # NEW
    ) -> None:
        ...
        self._build_coordinator = build_coordinator
```

### Backward Compatibility

- `DataFrameCacheCoalescer` remains intact and functional
- `DataFrameCache.acquire_build_lock_async()` and related methods remain available (deprecated)
- `BuildCoordinator` wraps but does not replace the coalescer
- Phase 1 can be deployed independently; other phases follow incrementally

---

## Metrics and Observability

### Statistics Tracked

```python
_stats = {
    "builds_started": 0,       # New builds initiated
    "builds_coalesced": 0,     # Requests that waited on existing build
    "builds_succeeded": 0,     # Builds completed successfully
    "builds_failed": 0,        # Builds that raised exceptions
    "builds_timed_out": 0,     # Waiters that exceeded timeout
    "builds_stale_rejected": 0, # Coalescing rejected due to staleness
}
```

### Logging Events

| Event | Level | When |
|-------|-------|------|
| `build_coordinator_started` | INFO | New build begins |
| `build_coordinator_coalesced` | DEBUG | Request coalesced with existing build |
| `build_coordinator_completed` | INFO | Build finished (includes duration_ms, waiter_count) |
| `build_coordinator_failed` | ERROR | Build raised exception |
| `build_coordinator_timeout` | WARNING | Waiter timed out |
| `build_coordinator_stale_rejected` | INFO | Coalescing rejected due to invalidation |
| `in_flight_builds_invalidated` | INFO | MutationInvalidator marked builds stale |

### Structured Log Format

```python
logger.info(
    "build_coordinator_completed",
    extra={
        "project_gid": key[0],
        "entity_type": key[1],
        "outcome": result.outcome.value,
        "build_duration_ms": result.build_duration_ms,
        "waiter_count": result.waiter_count,
        "caller": caller,
    },
)
```

---

## Implementation Phases

| Phase | Scope | Files Modified | Risk |
|-------|-------|----------------|------|
| 1 | `BuildCoordinator` class + unit tests | `cache/dataframe/build_coordinator.py` (new), tests | LOW: new code, no integration yet |
| 2 | Integrate with `@dataframe_cache` decorator | `cache/dataframe/decorator.py`, `cache/integration/dataframe_cache.py` | MEDIUM: changes primary build path |
| 3 | Integrate with `UniversalResolutionStrategy._get_dataframe()` | `services/universal_strategy.py` | MEDIUM: changes query build path |
| 4 | Integrate with `MutationInvalidator` | `cache/integration/mutation_invalidator.py` | LOW: additive change |
| 5 | Integrate with `CacheWarmer` and admin refresh | `cache/dataframe/warmer.py`, `api/routes/admin.py` | LOW: additive change to low-frequency paths |
| 6 | Deprecate direct `DataFrameCacheCoalescer` usage | `cache/integration/dataframe_cache.py` | LOW: API preserved, implementations delegate |

---

## Interface Contracts

### BuildCoordinator Public API

```python
class BuildCoordinator:
    async def build_or_wait_async(
        self,
        key: CoalescingKey,
        build_fn: Callable[[], Awaitable[tuple[pl.DataFrame, datetime]]],
        *,
        timeout_seconds: float | None = None,
        caller: str = "unknown",
    ) -> BuildResult: ...

    def mark_invalidated(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> int: ...

    def is_building(self, key: CoalescingKey) -> bool: ...

    def get_stats(self) -> dict[str, int]: ...

    async def force_cleanup(self, key: CoalescingKey) -> None: ...
```

### BuildResult Data Contract

```python
@dataclass(frozen=True, slots=True)
class BuildResult:
    outcome: BuildOutcome          # BUILT, COALESCED, TIMED_OUT, FAILED, STALE_REJECTED
    dataframe: pl.DataFrame | None  # None on timeout/failure
    watermark: datetime | None      # None on timeout/failure
    build_duration_ms: float        # 0 for coalesced/timeout
    waiter_count: int               # Number of coalesced waiters
    error: Exception | None         # Set on FAILED outcome
```

### DataFrameCache Extension

```python
class DataFrameCache:
    @property
    def build_coordinator(self) -> BuildCoordinator:
        """Get the BuildCoordinator instance.

        Lazily created on first access. Uses the existing coalescer
        internally for backward compatibility.
        """
        ...
```

---

## Data Flow Diagrams

### Normal Coalescing (No Staleness)

```
Caller A                    BuildCoordinator              Caller B
   |                              |                          |
   |-- build_or_wait(key, fn) -->|                          |
   |                              |-- [no in-flight]        |
   |                              |-- create Future         |
   |                              |-- start build_fn()      |
   |                              |                          |-- build_or_wait(key, fn) -->|
   |                              |                          |                             |
   |                              |<- [key in-flight] ------+                             |
   |                              |   wait on Future                                      |
   |                              |                                                       |
   |<-- build_fn() completes     |                                                       |
   |                              |-- set Future result                                   |
   |                              |                          |<-- Future resolved ---------|
   |                              |                          |                             |
   |<-- BuildResult(BUILT) ------|                          |<-- BuildResult(COALESCED) --|
```

### Staleness Rejection

```
Caller A                    BuildCoordinator     MutationInvalidator    Caller C
   |                              |                      |                 |
   |-- build_or_wait(key, fn) -->|                      |                 |
   |                              |-- start build       |                 |
   |                              |                      |                 |
   |                              |       mark_invalidated(proj) ------->|
   |                              |       [build.invalidated = True]      |
   |                              |                      |                 |
   |                              |                      |     build_or_wait(key, fn) -->|
   |                              |                      |     [in-flight, invalidated]  |
   |                              |                      |     START NEW BUILD           |
   |                              |                      |                               |
   |<-- build completes (stale)  |                      |                               |
   |    BuildResult(BUILT)        |                      |                               |
   |                              |                      |     new build completes (fresh)|
   |                              |                      |     BuildResult(BUILT)         |
```

---

## Test Strategy

### Unit Tests (Phase 1)

Location: `tests/unit/cache/test_build_coordinator.py`

| Test | Description | Key Assertions |
|------|-------------|----------------|
| `test_single_build_no_coalescing` | One caller, no contention | `outcome == BUILT`, `waiter_count == 0` |
| `test_two_callers_coalesced` | Two concurrent callers, same key | First: `BUILT`, Second: `COALESCED` |
| `test_different_keys_independent` | Two callers, different keys | Both: `BUILT` (no coalescing) |
| `test_timeout_returns_timed_out` | Waiter exceeds timeout | `outcome == TIMED_OUT`, `dataframe is None` |
| `test_build_failure_propagates` | `build_fn` raises exception | `outcome == FAILED`, `error is not None` |
| `test_shield_prevents_waiter_cancellation` | Cancel one waiter, others still receive result | Remaining waiter: `COALESCED` |
| `test_staleness_rejection` | `mark_invalidated()` during build | New caller: `BUILT` (not coalesced) |
| `test_staleness_existing_waiters_still_receive` | Invalidation does not orphan existing waiters | Pre-invalidation waiter receives result |
| `test_max_concurrent_builds_honored` | Start 6 builds, max=4 | At most 4 concurrent; others queue |
| `test_stats_accuracy` | Run mixed scenario, check stats | All counters accurate |
| `test_is_building_during_build` | Check `is_building()` while build in-flight | Returns True during, False after |
| `test_cleanup_after_completion` | Build completes, check `_in_flight` | Key removed from `_in_flight` |

### Concurrent Stress Tests

| Test | Description | Assertions |
|------|-------------|------------|
| `test_100_concurrent_same_key` | 100 `asyncio.gather()` calls for same key | Exactly 1 `BUILT`, 99 `COALESCED`, all receive same DataFrame |
| `test_rapid_invalidation_cycles` | Build -> invalidate -> build -> invalidate, 10 cycles | No deadlock, no orphaned futures, all builds complete |
| `test_mixed_keys_under_contention` | 50 callers across 5 different keys | Each key has exactly 1 builder, proper coalescing per key |
| `test_timeout_under_slow_build` | `build_fn` sleeps 5s, waiter timeout 1s | Waiter gets `TIMED_OUT`, builder eventually completes |

### Integration Tests (Phase 2-5)

| Test | Scope | Description |
|------|-------|-------------|
| `test_decorator_uses_coordinator` | Phase 2 | `@dataframe_cache` decorator routes through `BuildCoordinator` |
| `test_universal_strategy_uses_coordinator` | Phase 3 | `_get_dataframe()` uses coordinator for build |
| `test_mutation_marks_in_flight_stale` | Phase 4 | `MutationInvalidator.fire_and_forget()` marks builds invalidated |
| `test_warmer_uses_coordinator` | Phase 5 | `CacheWarmer` build goes through coordinator |
| `test_admin_refresh_uses_coordinator` | Phase 5 | Admin refresh goes through coordinator |

### Adversarial Tests

| Test | Scenario | Expected Behavior |
|------|----------|-------------------|
| `test_build_fn_hangs_forever` | `build_fn` never returns | All waiters time out; `_in_flight` entry persists until `force_cleanup()` |
| `test_concurrent_mark_invalidated` | 10 concurrent `mark_invalidated()` calls | No crash, boolean flag set idempotently |
| `test_build_fn_raises_after_invalidation` | Build marked stale, then build_fn raises | `FAILED` result, new build can start cleanly |
| `test_event_loop_shutdown_during_build` | Simulate shutdown | Graceful handling, no unhandled exceptions |

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Regression in decorator path** | MEDIUM | HIGH | Phase 2 is the riskiest change; extensive integration tests; feature flag for rollback |
| **asyncio.Future edge cases** | LOW | MEDIUM | `shield()` for cancellation safety; extensive concurrent tests |
| **Stale data served despite invalidation** | LOW | MEDIUM | `mark_invalidated()` called synchronously before response returns |
| **Memory leak from orphaned _InFlightBuild** | LOW | LOW | `force_cleanup()` method; periodic sweep in health check |
| **Performance overhead of coordinator lock** | VERY LOW | LOW | Lock held for microseconds (dict operations only); no I/O under lock |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Increased complexity** | CERTAIN | LOW | BuildCoordinator is 150-200 LOC; well-documented; single responsibility |
| **Debugging build attribution** | LOW | LOW | `caller` parameter in logs identifies which code path triggered build |
| **Rollback difficulty** | LOW | MEDIUM | Each phase is independently deployable; `DataFrameCacheCoalescer` preserved |

### Rollback Strategy

Each phase can be rolled back independently:
- Phase 1: No production impact (new module only)
- Phase 2: Revert decorator to direct coalescer calls
- Phase 3: Revert `_get_dataframe()` to legacy strategy delegation
- Phase 4: Remove `build_coordinator` param from `MutationInvalidator`
- Phase 5: Revert warmer/admin to direct `ProgressiveProjectBuilder` calls

---

## ADRs

### ADR-BC-001: Future-Based vs Event-Based Coalescing

**Context**: The existing `DataFrameCacheCoalescer` uses `asyncio.Event` for waiter notification. Waiters are notified that a build completed, then must re-read the cache to get the result.

**Decision**: Use `asyncio.Future` for result sharing in `BuildCoordinator`.

**Rationale**:
- `Future` carries the result directly -- no cache re-read race
- `Future` naturally propagates exceptions
- `asyncio.shield(future)` provides clean cancellation isolation
- Eliminates the window between Event.set() and cache read where eviction could occur

**Consequences**:
- (+) Eliminates cache-read race condition for coalesced waiters
- (+) Single atomic result delivery
- (-) Slightly more complex error handling (must set_result or set_exception)
- (-) Future can only be resolved once (intentional -- build produces one result)

**Status**: ACCEPTED

### ADR-BC-002: Wrap-and-Extend vs Replace Coalescer

**Context**: Should `BuildCoordinator` replace `DataFrameCacheCoalescer` or wrap it?

**Decision**: Wrap and extend. `DataFrameCacheCoalescer` is preserved for backward compatibility; `BuildCoordinator` is the new recommended entry point.

**Rationale**:
- Existing coalescer is proven correct for the decorator path
- Replacement would require modifying all consumers simultaneously (risky big-bang)
- Wrap-and-extend allows incremental migration across phases
- Deprecation gives consumers time to migrate

**Consequences**:
- (+) Zero-risk Phase 1 deployment
- (+) Incremental migration reduces blast radius
- (-) Temporary dual abstraction (coalescer + coordinator) until migration complete
- (-) Must keep coalescer and coordinator in sync during transition

**Status**: ACCEPTED

### ADR-BC-003: Staleness Rejection Strategy

**Context**: When a mutation fires during an in-flight build, should the build be cancelled, or should new arrivals get a fresh build?

**Decision**: New arrivals get a fresh build. In-flight build continues to completion for existing waiters.

**Rationale**:
- Cancellation requires cooperative support through the entire build stack (builders, API clients, persistence)
- Existing waiters are already committed -- giving them a stale result is better than orphaning them with no result
- The stale result can be served as LKG (Last Known Good) with degradation warning
- Fresh build for new arrivals ensures post-mutation data is served going forward

**Consequences**:
- (+) No cancellation complexity in build stack
- (+) Existing waiters are never orphaned
- (+) Clean separation: staleness is a property of arrival time, not build identity
- (-) Brief window where stale data is served to pre-mutation waiters
- (-) Two builds may run concurrently for the same key (one stale, one fresh)

**Status**: ACCEPTED

### ADR-BC-004: Global Build Concurrency Limit

**Context**: Should the coordinator limit total concurrent builds across all keys?

**Decision**: Yes, via `asyncio.Semaphore(max_concurrent_builds=4)`.

**Rationale**:
- Each build consumes significant resources: Asana API calls, memory for DataFrame construction, S3 writes
- Without a limit, a cache cold-start (schema change, deployment) could trigger builds for all entity types simultaneously
- 4 is the typical number of entity types (unit, offer, business, contact); allows all to build concurrently in normal operation
- Startup preload already uses `Semaphore(3)` for similar reasons

**Consequences**:
- (+) Bounded resource usage during mass invalidation events
- (+) Prevents Asana API rate limiting from concurrent builds
- (-) If >4 keys need building simultaneously, some queue behind the semaphore
- (-) Additional latency for queued builds (bounded by timeout)

**Status**: ACCEPTED

---

## Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| All build paths go through BuildCoordinator | Code audit: no direct `ProgressiveProjectBuilder` calls outside coordinator | 100% coverage |
| No duplicate concurrent builds for same key | `builds_coalesced` stat > 0 in staging load test | Verified |
| Mutation invalidation prevents stale coalescing | Integration test: mutation mid-build -> new caller gets fresh data | Pass |
| No deadlocks under concurrent load | 100-caller stress test completes without hang | < 5s total |
| Build coordinator overhead < 1ms | Measure lock acquisition time in production logs | < 1ms p99 |
| All existing tests pass | Full test suite after each phase | 0 failures |
| Rollback possible per phase | Each phase independently revertable | Verified |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dataframe-build-coalescing.md` | YES |
| Existing coalescer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/coalescer.py` | YES (Read) |
| Existing decorator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | YES (Read) |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` | YES (Read) |
| MutationInvalidator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/mutation_invalidator.py` | YES (Read) |
| FreshnessStamp | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/freshness_stamp.py` | YES (Read) |
| UniversalResolutionStrategy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | YES (Read) |
| ParallelSectionFetcher | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py` | YES (Read) |
| SectionFreshnessProber | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/freshness.py` | YES (Read) |
| Exception hierarchy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py` | YES (Read) |
| Spike S0-006 | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-006-concurrent-build-analysis.md` | YES (Read) |
| DataFrameCacheIntegration | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py` | YES (Read) |
