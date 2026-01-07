---
artifact_id: TDD-gid-resolution-performance
title: "GID Resolution Service Performance Optimization"
created_at: "2026-01-04T23:30:00Z"
author: architect
prd_ref: PRD-gid-resolution-performance
status: draft
components:
  - name: ConcurrencyController
    type: module
    description: "Semaphore-bounded asyncio.gather for controlled parallel execution"
    dependencies:
      - name: asyncio
        type: external
  - name: BatchParentResolver
    type: module
    description: "Batched parent chain resolution eliminating N+1 API calls"
    dependencies:
      - name: UnifiedTaskStore
        type: internal
      - name: HierarchyIndex
        type: internal
  - name: AdaptiveRateLimiter
    type: module
    description: "Token bucket with 429 backoff for Asana rate limit compliance"
    dependencies:
      - name: asyncio
        type: external
  - name: CacheWarmer
    type: module
    description: "Background prefetch for cold cache mitigation"
    dependencies:
      - name: UnifiedTaskStore
        type: internal
  - name: FreshnessOptimizer
    type: module
    description: "Reduced API call frequency for freshness validation"
    dependencies:
      - name: FreshnessCoordinator
        type: internal
related_adrs:
  - ADR-0060
schema_version: "1.0"
---

# TDD: GID Resolution Service Performance Optimization

> Technical design for fixing httpx.ReadTimeout in POST /v1/resolve/unit endpoint

## 1. Problem Statement

The GID resolution service (`POST /v1/resolve/unit`) times out with `httpx.ReadTimeout` when processing batch requests. The demo at `~/Code/autom8-s2s-demo` fails consistently. Root cause analysis identifies five performance bottlenecks.

### 1.1 Current Performance Profile

| Operation | Current | Target | Gap |
|-----------|---------|--------|-----|
| 100 task extraction | ~10s | <1s | 10x |
| 100 parent resolutions | ~20s | <2s | 10x |
| Cold cache first request | >30s | <5s | 6x |
| Overall endpoint P95 | >30s | <5s | 6x |

### 1.2 Verified Root Causes

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| RC-1 | `base.py:360` | Sequential task extraction | 100 tasks x 100ms = 10s |
| RC-2 | `cascading.py:313` | N+1 parent API calls | 100 parents x 200ms = 20s |
| RC-3 | `project.py:633` | Unbounded asyncio.gather | Asana 429 rate limits |
| RC-4 | `resolver.py:464` | Cold cache penalty | First request blocks on full rebuild |
| RC-5 | `unified.py:223` | Freshness check per operation | Adds latency per cache check |
| RC-6 | `project.py:1048-1050` | Sequential delta merge loop | Changed tasks extracted one-by-one |

### 1.3 RC-3 and RC-6 Fix Specification (Architect Sign-Off)

**Status**: Approved for implementation

#### Problem Detail

**RC-3 (project.py:633)**: `_fetch_tasks_by_gids_async` spawns 2616+ concurrent API calls:
```python
results = await asyncio.gather(*[fetch_task(gid) for gid in gids])
```

**RC-6 (project.py:1048-1050)**: `_merge_delta` extracts rows sequentially:
```python
for task in changed_tasks:
    row = await self._extract_row_async(task)
    changed_rows.append(row)
```

#### Approved Solution: Use `self._concurrency_controller.gather_with_limit()`

Replace both patterns with bounded concurrent execution using the existing platform primitive.

**Rationale for `gather_with_limit()` over alternatives**:

| Alternative | Evaluation | Decision |
|-------------|------------|----------|
| Raw semaphore-bounded gather | Duplicates existing implementation; lacks chunking and observability | Rejected |
| asyncio.TaskGroup with semaphore | Python 3.11+ only; requires manual semaphore wrapping; no chunking | Rejected |
| HTTP connection pool limits | Operates at wrong layer; doesn't address coroutine memory pressure | Rejected |
| **`gather_with_limit()` from autom8y-http** | Already integrated in base.py (lines 387, 409, 610); tested; configurable; includes chunking | **Approved** |

**Consistency benefit**: Same concurrency primitive across all builders ensures predictable behavior and unified configuration via `CONCURRENCY_*` env vars.

#### RC-3 Fix Implementation

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py`
**Lines**: 632-633

**Before**:
```python
# Fetch in parallel with some concurrency limit
results = await asyncio.gather(*[fetch_task(gid) for gid in gids])
```

**After**:
```python
# Per TDD-gid-resolution-performance RC-3: Use bounded gather instead of unbounded
results = await self._concurrency_controller.gather_with_limit(
    [fetch_task(gid) for gid in gids]
)
```

**Note**: The existing `fetch_task` wrapper (lines 622-630) handles exceptions internally by returning `None`, so exception propagation behavior is preserved.

#### RC-6 Fix Implementation

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py`
**Lines**: 1047-1050

**Before**:
```python
changed_rows: list[dict[str, Any]] = []
for task in changed_tasks:
    row = await self._extract_row_async(task)
    changed_rows.append(row)
```

**After**:
```python
# Per TDD-gid-resolution-performance RC-6: Use bounded gather instead of sequential loop
changed_rows = await self._concurrency_controller.gather_with_limit(
    [self._extract_row_async(task) for task in changed_tasks]
)
```

#### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Order preservation | None | N/A | `gather_with_limit()` preserves input order (verified: AC-CC-3 in platform TDD) |
| Exception behavior change | None | N/A | `fetch_task` wrapper catches exceptions internally; no propagation change |
| Chunk boundary effects | Low | Low | GID fetches are independent; no inter-chunk dependencies |
| Semaphore contention | Low | Medium | Default 25 concurrent is conservative; monitor via `get_stats()` |

#### Acceptance Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-RC3-1 | No unbounded gather in `_fetch_tasks_by_gids_async` | Code inspection |
| AC-RC3-2 | 2616 GID fetches complete without 429 errors | Integration test with large project |
| AC-RC6-1 | Delta merge uses parallel extraction | Code inspection |
| AC-RC6-2 | 100 changed tasks merge in <2s (vs ~10s sequential) | Timer in test |
| AC-BOTH-1 | `_concurrency_controller` used (not new controller instance) | Code inspection; ensures unified config |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       GID Resolution Request                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     AdaptiveRateLimiter                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐    │
│  │Token Bucket │  │ 429 Backoff  │  │ Per-PAT Rate Tracking       │    │
│  │ 1500/min    │  │ Exponential  │  │ Concurrent Request Limit    │    │
│  └─────────────┘  └──────────────┘  └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ConcurrencyController                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐    │
│  │ Semaphore   │  │ Chunk Size   │  │ asyncio.gather + limit      │    │
│  │ max=10      │  │ = 50 tasks   │  │ return_exceptions=True      │    │
│  └─────────────┘  └──────────────┘  └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  CacheWarmer    │   │ BatchParentResolver │   │ FreshnessOptimizer  │
│                 │   │                     │   │                     │
│ - Background    │   │ - Collect GIDs      │   │ - Batch validation  │
│   prefetch      │   │ - Single batch API  │   │ - TTL-based skip    │
│ - Priority      │   │ - HierarchyIndex    │   │ - Coalesced checks  │
│   queue         │   │   population        │   │                     │
└─────────────────┘   └─────────────────────┘   └─────────────────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       UnifiedTaskStore                                  │
│  ┌──────────────────┐  ┌────────────────┐  ┌─────────────────────┐     │
│  │   CacheProvider  │  │ HierarchyIndex │  │ CompletenessLevel   │     │
│  │   (Tiered)       │  │ (Parent Chain) │  │ (Field Tracking)    │     │
│  └──────────────────┘  └────────────────┘  └─────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Designs

### 3.1 ConcurrencyController (RC-1 Fix)

**Problem**: Sequential `await` in list comprehension serializes extraction.

**Current Code** (`base.py:360`):
```python
rows = [await self._extract_row_async(task) for task in tasks]
```

**Solution**: Semaphore-bounded `asyncio.gather()` with chunking.

#### 3.1.1 Interface

```python
# src/autom8_asana/dataframes/concurrency.py

from asyncio import Semaphore
from typing import TypeVar, Callable, Awaitable, Sequence

T = TypeVar("T")
R = TypeVar("R")

class ConcurrencyController:
    """Bounded parallel execution with backpressure.

    Per TDD-gid-resolution-performance: Fixes RC-1 sequential extraction.

    Attributes:
        max_concurrent: Maximum concurrent operations (default 10).
        chunk_size: Tasks processed per gather batch (default 50).

    Example:
        >>> controller = ConcurrencyController(max_concurrent=10)
        >>> results = await controller.map_async(
        ...     items=tasks,
        ...     func=extract_row_async,
        ... )
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        chunk_size: int = 50,
    ) -> None:
        self._semaphore = Semaphore(max_concurrent)
        self._chunk_size = chunk_size

    async def map_async(
        self,
        items: Sequence[T],
        func: Callable[[T], Awaitable[R]],
    ) -> list[R]:
        """Apply async function to items with bounded concurrency.

        Args:
            items: Input sequence to process.
            func: Async function to apply to each item.

        Returns:
            Results in same order as input items.

        Raises:
            Exception: Re-raises first exception from any task.
        """
        ...

    async def _bounded_call(
        self,
        func: Callable[[T], Awaitable[R]],
        item: T,
    ) -> R:
        """Execute single call with semaphore protection."""
        async with self._semaphore:
            return await func(item)
```

#### 3.1.2 Integration Points

**File**: `src/autom8_asana/dataframes/builders/base.py`

**Before** (line 360):
```python
async def _build_eager_async(self, tasks: list[Task]) -> pl.DataFrame:
    rows = [await self._extract_row_async(task) for task in tasks]
    return pl.DataFrame(rows, schema=self._schema.to_polars_schema())
```

**After**:
```python
async def _build_eager_async(self, tasks: list[Task]) -> pl.DataFrame:
    from autom8_asana.dataframes.concurrency import ConcurrencyController

    controller = ConcurrencyController(max_concurrent=10, chunk_size=50)
    rows = await controller.map_async(tasks, self._extract_row_async)
    return pl.DataFrame(rows, schema=self._schema.to_polars_schema())
```

**Same change applies to** (line 375):
```python
async def _build_lazy_async(self, tasks: list[Task]) -> pl.DataFrame:
    from autom8_asana.dataframes.concurrency import ConcurrencyController

    controller = ConcurrencyController(max_concurrent=10, chunk_size=50)
    rows = await controller.map_async(tasks, self._extract_row_async)
    lazy_frame = pl.LazyFrame(rows, schema=self._schema.to_polars_schema())
    return lazy_frame.collect()
```

#### 3.1.3 Acceptance Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-1.1 | 100 task extraction completes in <1s | Timer in test |
| AC-1.2 | Concurrent operations never exceed `max_concurrent` | Semaphore counter assertion |
| AC-1.3 | Results maintain input order | Index comparison |
| AC-1.4 | Exceptions propagate correctly | pytest.raises |

---

### 3.2 BatchParentResolver (RC-2 Fix)

**Problem**: Each cascade resolution triggers individual API call.

**Current Code** (`cascading.py:313`):
```python
parent = await self._client.tasks.get_async(parent_gid, ...)
```

**Solution**: Collect all parent GIDs upfront, fetch in single batch, populate HierarchyIndex.

#### 3.2.1 Interface

```python
# src/autom8_asana/dataframes/resolver/batch_parent.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

class BatchParentResolver:
    """Batch parent chain resolution eliminating N+1 queries.

    Per TDD-gid-resolution-performance: Fixes RC-2 cascade N+1.

    Strategy:
    1. Collect all unique parent GIDs from task list
    2. Check UnifiedTaskStore for cached parents
    3. Batch fetch missing parents via API
    4. Populate HierarchyIndex for future lookups
    5. Return parent map for cascade resolution

    Example:
        >>> resolver = BatchParentResolver(store=unified_store)
        >>> parent_map = await resolver.resolve_batch_async(
        ...     tasks=tasks,
        ...     client=client,
        ...     max_depth=5,
        ... )
        >>> # parent_map: {child_gid: [parent_task, grandparent_task, ...]}
    """

    def __init__(self, store: "UnifiedTaskStore") -> None:
        self._store = store

    async def resolve_batch_async(
        self,
        tasks: list["Task"],
        client: "AsanaClient",
        max_depth: int = 5,
    ) -> dict[str, list[dict]]:
        """Resolve parent chains for all tasks in batch.

        Args:
            tasks: Tasks needing parent resolution.
            client: AsanaClient for API calls.
            max_depth: Maximum ancestor depth.

        Returns:
            Dict mapping child GID to list of ancestor dicts.
        """
        ...

    async def _collect_parent_gids(
        self,
        tasks: list["Task"],
        max_depth: int,
    ) -> set[str]:
        """Collect all unique parent GIDs needed.

        Traverses HierarchyIndex first, then task.parent references.
        """
        ...

    async def _fetch_missing_parents(
        self,
        missing_gids: list[str],
        client: "AsanaClient",
    ) -> list[dict]:
        """Batch fetch missing parents from API.

        Uses bounded concurrency to respect rate limits.
        """
        ...
```

#### 3.2.2 Integration Strategy

**Phase 1: Pre-resolution batch fetch**

Before DataFrame extraction, call `BatchParentResolver` to populate the cache:

```python
# In ProjectDataFrameBuilder._build_with_unified_store_async

# After fetching task GIDs, before materialization:
batch_parent_resolver = BatchParentResolver(store=self._unified_store)
await batch_parent_resolver.resolve_batch_async(
    tasks=tasks_to_extract,
    client=client,
    max_depth=5,
)

# Now CascadingFieldResolver will hit cache instead of API
```

**Phase 2: CascadingFieldResolver cache-first**

Modify `CascadingFieldResolver._fetch_parent_async` to check `UnifiedTaskStore` first:

```python
# In cascading.py

async def _fetch_parent_async(self, parent_gid: str) -> Task | None:
    # Check unified store first (populated by BatchParentResolver)
    if self._unified_store is not None:
        cached = await self._unified_store.get_async(
            parent_gid,
            freshness=FreshnessMode.IMMEDIATE,
        )
        if cached is not None:
            from autom8_asana.models.task import Task
            return Task.model_validate(cached)

    # Fallback to API (should rarely happen after batch prefetch)
    return await self._client.tasks.get_async(parent_gid, ...)
```

#### 3.2.3 Acceptance Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-2.1 | 100 parent resolutions complete in <2s | Timer in test |
| AC-2.2 | API calls reduced from N to ceil(N/batch_size) | Request counter mock |
| AC-2.3 | HierarchyIndex populated after batch resolve | Index.get_ancestor_chain() non-empty |
| AC-2.4 | Subsequent cascade lookups hit cache | Cache hit counter |

---

### 3.3 AdaptiveRateLimiter (RC-3 Fix)

**Problem**: Unbounded `asyncio.gather` causes 429 rate limit errors.

**Current Code** (`project.py:633`):
```python
results = await asyncio.gather(*[fetch_task(gid) for gid in gids])
```

**Solution**: Token bucket rate limiter with exponential backoff on 429.

#### 3.3.1 Interface

```python
# src/autom8_asana/clients/rate_limiter.py

import asyncio
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RateLimitConfig:
    """Rate limit configuration per Asana API limits.

    Asana limit: 1500 requests/minute per PAT.
    Safe default: 1200 requests/minute (80% headroom).
    """
    requests_per_minute: int = 1200
    burst_size: int = 50
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    backoff_multiplier: float = 2.0

class AdaptiveRateLimiter:
    """Token bucket rate limiter with 429 backoff.

    Per TDD-gid-resolution-performance: Fixes RC-3 unbounded concurrency.

    Features:
    - Token bucket for steady-state rate limiting
    - Exponential backoff on 429 responses
    - Per-PAT tracking for multi-tenant scenarios
    - Burst allowance for initial requests

    Example:
        >>> limiter = AdaptiveRateLimiter()
        >>> async with limiter.acquire():
        ...     response = await client.tasks.get_async(gid)
        >>> # Or handle 429 explicitly:
        >>> limiter.record_rate_limit(retry_after=30)
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._tokens: float = self._config.burst_size
        self._last_refill: datetime = datetime.now()
        self._backoff_until: datetime | None = None
        self._consecutive_429s: int = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> "RateLimitContext":
        """Acquire permission to make an API request.

        Returns context manager that tracks request completion.
        Blocks if rate limit would be exceeded.
        """
        ...

    def record_rate_limit(self, retry_after: int | None = None) -> None:
        """Record a 429 response and update backoff.

        Args:
            retry_after: Retry-After header value in seconds.
        """
        ...

    def record_success(self) -> None:
        """Record successful request, reset backoff counter."""
        ...

    async def _wait_for_token(self) -> None:
        """Wait until a token is available."""
        ...

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        ...
```

#### 3.3.2 Integration Points

**File**: `src/autom8_asana/dataframes/builders/project.py`

**Before** (line 633):
```python
results = await asyncio.gather(*[fetch_task(gid) for gid in gids])
```

**After**:
```python
from autom8_asana.clients.rate_limiter import AdaptiveRateLimiter

rate_limiter = AdaptiveRateLimiter()

async def rate_limited_fetch(gid: str) -> Task | None:
    async with rate_limiter.acquire():
        try:
            result = await client.tasks.get_async(gid, opt_fields=_BASE_OPT_FIELDS)
            rate_limiter.record_success()
            return result
        except AsanaRateLimitError as e:
            rate_limiter.record_rate_limit(e.retry_after)
            raise

results = await asyncio.gather(
    *[rate_limited_fetch(gid) for gid in gids],
    return_exceptions=True,
)
```

#### 3.3.3 Acceptance Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-3.1 | No 429 errors under normal load | Error counter = 0 |
| AC-3.2 | Requests/minute stays below 1500 | Rate monitoring |
| AC-3.3 | Backoff increases on consecutive 429s | Backoff duration assertion |
| AC-3.4 | Recovery after backoff period | Request succeeds post-backoff |

---

### 3.4 CacheWarmer (RC-4 Fix)

**Problem**: First request forces synchronous full cache rebuild.

**Current Code** (`resolver.py:464`):
```python
if cached_index is None or cached_index.is_stale(_INDEX_TTL_SECONDS):
    # Synchronous rebuild blocks the request
    df, new_watermark = await self._build_dataframe_incremental(...)
```

**Solution**: Background prefetch with priority queue.

#### 3.4.1 Interface

```python
# src/autom8_asana/cache/warmer.py

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.client import AsanaClient

class WarmPriority(IntEnum):
    """Cache warming priority levels."""
    CRITICAL = 0    # User-facing request waiting
    HIGH = 1        # Frequently accessed
    NORMAL = 2      # Background maintenance
    LOW = 3         # Speculative prefetch

@dataclass
class WarmRequest:
    """Request to warm a specific cache entry."""
    project_gid: str
    entity_type: str
    priority: WarmPriority
    requested_at: float

class CacheWarmer:
    """Background cache warming with priority queue.

    Per TDD-gid-resolution-performance: Fixes RC-4 cold cache penalty.

    Features:
    - Background task processes warm queue
    - Priority-based scheduling
    - Coalescing duplicate requests
    - Graceful degradation if warming fails

    Example:
        >>> warmer = CacheWarmer(store=unified_store)
        >>> await warmer.start()
        >>> # Request warming (non-blocking)
        >>> warmer.request_warm(
        ...     project_gid="123",
        ...     entity_type="unit",
        ...     priority=WarmPriority.HIGH,
        ... )
        >>> # Or wait for specific warm (blocking)
        >>> await warmer.ensure_warm_async(
        ...     project_gid="123",
        ...     entity_type="unit",
        ...     timeout=5.0,
        ... )
    """

    def __init__(
        self,
        store: "UnifiedTaskStore",
        max_concurrent_warms: int = 2,
    ) -> None:
        self._store = store
        self._max_concurrent = max_concurrent_warms
        self._queue: asyncio.PriorityQueue[WarmRequest] = asyncio.PriorityQueue()
        self._in_progress: set[str] = set()
        self._warm_events: dict[str, asyncio.Event] = {}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background warming task."""
        ...

    async def stop(self) -> None:
        """Stop background warming task."""
        ...

    def request_warm(
        self,
        project_gid: str,
        entity_type: str,
        priority: WarmPriority = WarmPriority.NORMAL,
    ) -> None:
        """Request cache warming (non-blocking).

        Coalesces with existing request if already queued.
        """
        ...

    async def ensure_warm_async(
        self,
        project_gid: str,
        entity_type: str,
        timeout: float = 10.0,
    ) -> bool:
        """Wait for cache to be warm (blocking with timeout).

        Returns:
            True if warm completed, False if timeout.
        """
        ...

    async def _process_queue(self) -> None:
        """Background loop processing warm requests."""
        ...

    async def _warm_project(
        self,
        request: WarmRequest,
        client: "AsanaClient",
    ) -> None:
        """Execute single warm operation."""
        ...
```

#### 3.4.2 Integration Strategy

**Startup warming** - Register projects for warming at application startup:

```python
# In application startup (e.g., FastAPI lifespan)

async def lifespan(app: FastAPI):
    # Start cache warmer
    warmer = CacheWarmer(store=unified_store)
    await warmer.start()
    app.state.cache_warmer = warmer

    # Request warming for known entity projects
    registry = EntityProjectRegistry.get_instance()
    for entity_type in registry.get_all_entity_types():
        project_gid = registry.get_project_gid(entity_type)
        if project_gid:
            warmer.request_warm(
                project_gid=project_gid,
                entity_type=entity_type,
                priority=WarmPriority.HIGH,
            )

    yield

    await warmer.stop()
```

**Request-time warming** - For cold cache, warm with CRITICAL priority:

```python
# In resolver.py _get_or_build_index

if cached_index is None or cached_index.is_stale(_INDEX_TTL_SECONDS):
    # Request warming with high priority
    warmer = get_cache_warmer()  # Global or request-scoped

    # Wait up to 5s for warm to complete
    warm_complete = await warmer.ensure_warm_async(
        project_gid=project_gid,
        entity_type="unit",
        timeout=5.0,
    )

    if not warm_complete:
        # Warming still in progress, proceed with partial data
        logger.warning("cache_warm_timeout", extra={"project_gid": project_gid})
```

#### 3.4.3 Acceptance Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-4.1 | Cold cache first request <5s | Timer in test |
| AC-4.2 | Background warming doesn't block requests | Request latency unaffected |
| AC-4.3 | Priority ordering respected | Lower priority value processed first |
| AC-4.4 | Duplicate requests coalesced | Queue size assertion |

---

### 3.5 FreshnessOptimizer (RC-5 Fix)

**Problem**: Freshness check adds API call latency per operation.

**Current Code** (`unified.py:223`):
```python
results = await self._freshness.check_batch_async([entry], mode=mode)
```

**Solution**: TTL-based skip, coalesced batch validation, and mode-aware optimization.

#### 3.5.1 Optimizations

**Optimization 1: TTL-based skip**

If entry is within TTL (e.g., 60s), skip freshness check entirely:

```python
# In UnifiedTaskStore.get_async

FRESHNESS_TTL_SECONDS = 60  # Skip check if cached within this window

if mode != FreshnessMode.STRICT:
    # Check if entry is fresh enough to skip validation
    age_seconds = (datetime.now(timezone.utc) - entry.cached_at).total_seconds()
    if age_seconds < FRESHNESS_TTL_SECONDS:
        self._stats["freshness_skipped"] += 1
        return entry.data

# Proceed with freshness check only if beyond TTL
results = await self._freshness.check_batch_async([entry], mode=mode)
```

**Optimization 2: Batch coalescing in FreshnessCoordinator**

Already implemented with `coalesce_window_ms=50`, but increase for higher throughput:

```python
# In UnifiedTaskStore.__post_init__

self._freshness = FreshnessCoordinator(
    batch_client=self.batch_client,
    coalesce_window_ms=100,  # Increase from 50 to 100
    max_batch_size=100,      # Max Asana batch size
)
```

**Optimization 3: EVENTUAL mode with reduced frequency**

For batch operations, use EVENTUAL mode which checks TTL before API:

```python
# In ProjectDataFrameBuilder._build_with_unified_store_async

cached_data = await self._unified_store.get_batch_async(
    all_task_gids,
    freshness=FreshnessMode.EVENTUAL,  # TTL-based, not STRICT
    required_level=CompletenessLevel.STANDARD,
)
```

#### 3.5.2 Interface Changes

```python
# In src/autom8_asana/cache/unified.py

# Add configuration
FRESHNESS_SKIP_TTL_SECONDS = 60  # Skip freshness check if within TTL

async def get_async(
    self,
    gid: str,
    freshness: FreshnessMode | None = None,
    required_level: CompletenessLevel = CompletenessLevel.STANDARD,
) -> dict[str, Any] | None:
    """Get single task, respecting freshness mode and completeness.

    Per TDD-gid-resolution-performance: Adds TTL-based freshness skip
    to reduce API calls for recently cached entries.
    """
    mode = freshness or self.freshness_mode

    entry = self.cache.get_versioned(gid, EntryType.TASK)
    if entry is None:
        self._stats["get_misses"] += 1
        return None

    # Check completeness
    if not is_entry_sufficient(entry, required_level):
        self._stats["get_misses"] += 1
        self._stats["completeness_misses"] += 1
        return None

    # IMMEDIATE mode: return without validation
    if mode == FreshnessMode.IMMEDIATE:
        self._stats["get_hits"] += 1
        return entry.data

    # TTL-based skip for non-STRICT modes
    if mode != FreshnessMode.STRICT:
        age_seconds = (datetime.now(timezone.utc) - entry.cached_at).total_seconds()
        if age_seconds < FRESHNESS_SKIP_TTL_SECONDS:
            self._stats["get_hits"] += 1
            self._stats["freshness_skipped"] += 1
            return entry.data

    # Full freshness check
    results = await self._freshness.check_batch_async([entry], mode=mode)
    if results and results[0].is_fresh:
        self._stats["get_hits"] += 1
        return entry.data

    self._stats["get_misses"] += 1
    return None
```

#### 3.5.3 Acceptance Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-5.1 | Freshness checks reduced by 80%+ | Counter comparison |
| AC-5.2 | TTL skip works for entries <60s old | Age-based test |
| AC-5.3 | STRICT mode still validates every request | Mode=STRICT test |
| AC-5.4 | Batch coalescing groups multiple checks | Single API call for N entries |

---

## 4. Data Flow: Optimized Resolution Path

```
┌─────────────────────────────────────────────────────────────────────────┐
│  POST /v1/resolve/unit  (100 criteria)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. CacheWarmer.ensure_warm_async(project_gid, "unit", timeout=5s)      │
│     - If warm: continue immediately                                      │
│     - If cold: wait up to 5s, then proceed with partial data            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. UnifiedTaskStore.get_batch_async(task_gids, EVENTUAL)               │
│     - TTL check: skip freshness if <60s old                             │
│     - Batch check: coalesce multiple into single API call               │
│     - Returns: {gid: task_data | None}                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. BatchParentResolver.resolve_batch_async(tasks, max_depth=5)         │
│     - Collect unique parent GIDs from all tasks                         │
│     - Single batch API call for missing parents                         │
│     - Populate HierarchyIndex for future lookups                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. ConcurrencyController.map_async(tasks, extract_row)                 │
│     - Semaphore(10) limits concurrent extractions                       │
│     - Chunks of 50 tasks per gather batch                               │
│     - Cascade resolution hits cache (populated in step 3)               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. GidLookupIndex.get_gids(criteria)                                   │
│     - O(1) lookup per criterion                                         │
│     - Returns: [ResolutionResult(gid=...), ...]                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Performance Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| 100 task extraction | ~10s | <1s | 10x |
| 100 parent resolutions | ~20s | <2s | 10x |
| Cold cache first request | >30s | <5s | 6x |
| Warm cache request | ~5s | <500ms | 10x |
| P95 endpoint latency | >30s | <5s | 6x |
| 429 rate limit errors | Frequent | 0 | 100% reduction |
| API calls per 100 tasks | ~200 | ~20 | 10x reduction |

---

## 6. Migration Strategy

### Phase 1: ConcurrencyController (RC-1)
**Risk**: Low - Pure performance optimization, no behavior change
**Rollback**: Remove import, revert to list comprehension

1. Add `src/autom8_asana/dataframes/concurrency.py`
2. Update `base.py` lines 360, 375
3. Verify: 100 task extraction <1s

### Phase 2: AdaptiveRateLimiter (RC-3)
**Risk**: Low - Adds protection, doesn't change success path
**Rollback**: Remove rate limiter wrapping

1. Add `src/autom8_asana/clients/rate_limiter.py`
2. Update `project.py` line 633
3. Verify: No 429 errors under load

### Phase 3: BatchParentResolver (RC-2)
**Risk**: Medium - Changes data flow, requires cache coordination
**Rollback**: Remove batch prefetch, revert to on-demand fetch

1. Add `src/autom8_asana/dataframes/resolver/batch_parent.py`
2. Update `cascading.py` to check cache first
3. Add prefetch call to `project.py`
4. Verify: 100 parent resolutions <2s

### Phase 4: FreshnessOptimizer (RC-5)
**Risk**: Low - Reduces API calls, maintains correctness
**Rollback**: Remove TTL skip logic

1. Add TTL-based skip to `unified.py`
2. Increase coalesce window
3. Verify: Freshness checks reduced 80%+

### Phase 5: CacheWarmer (RC-4)
**Risk**: Medium - Background process, lifecycle management
**Rollback**: Disable warmer, fall back to on-demand

1. Add `src/autom8_asana/cache/warmer.py`
2. Add startup warming in application lifespan
3. Add ensure_warm_async to resolver
4. Verify: Cold cache first request <5s

---

## 7. Test Plan

### 7.1 Unit Tests

```python
# tests/unit/dataframes/test_concurrency.py

class TestConcurrencyController:
    async def test_map_async_maintains_order(self):
        """Results are returned in same order as input."""
        ...

    async def test_semaphore_limits_concurrency(self):
        """Never exceeds max_concurrent simultaneous operations."""
        ...

    async def test_exception_propagation(self):
        """First exception from any task is raised."""
        ...

# tests/unit/clients/test_rate_limiter.py

class TestAdaptiveRateLimiter:
    async def test_token_bucket_refill(self):
        """Tokens refill at configured rate."""
        ...

    async def test_backoff_on_429(self):
        """Exponential backoff on rate limit errors."""
        ...

    async def test_success_resets_backoff(self):
        """Successful request resets consecutive 429 counter."""
        ...
```

### 7.2 Integration Tests

```python
# tests/integration/test_gid_resolution_performance.py

class TestGidResolutionPerformance:
    async def test_100_task_extraction_under_1s(self, client):
        """100 task extraction completes in <1s."""
        start = time.perf_counter()
        df = await builder.build_with_parallel_fetch_async(client)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0
        assert len(df) == 100

    async def test_cold_cache_under_5s(self, client):
        """Cold cache first request completes in <5s."""
        # Clear all caches
        unified_store.cache.clear()
        _gid_index_cache.clear()

        start = time.perf_counter()
        results = await resolver.resolve(criteria, project_gid, client)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0

    async def test_no_429_errors(self, client, load_generator):
        """No rate limit errors under sustained load."""
        errors = []
        async for result in load_generator.run(requests=500):
            if result.error and "429" in str(result.error):
                errors.append(result)
        assert len(errors) == 0
```

### 7.3 Benchmark Tests

```python
# tests/benchmark/test_resolution_benchmark.py

@pytest.mark.benchmark
class TestResolutionBenchmark:
    def test_baseline_performance(self, benchmark, client):
        """Establish baseline for regression detection."""
        result = benchmark(
            lambda: asyncio.run(
                resolver.resolve(criteria_100, project_gid, client)
            )
        )
        assert result.stats.mean < 5.0  # 5s target
```

---

## 8. Observability

### 8.1 Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `gid_resolution_duration_seconds` | Histogram | entity_type, cache_status | End-to-end resolution time |
| `cache_hit_rate` | Gauge | cache_layer | Hit rate per cache layer |
| `rate_limit_backoffs_total` | Counter | - | 429 backoff events |
| `concurrent_extractions` | Gauge | - | Current concurrent extraction count |
| `parent_batch_size` | Histogram | - | Parent GIDs per batch fetch |

### 8.2 Structured Logging

```python
logger.info(
    "gid_resolution_completed",
    extra={
        "entity_type": "unit",
        "criteria_count": 100,
        "cache_hit_count": 85,
        "cache_miss_count": 15,
        "parent_batch_fetches": 2,
        "duration_ms": 1250,
        "warm_wait_ms": 0,
    },
)
```

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Semaphore deadlock | Low | High | Timeout on acquire, structured logging |
| Rate limiter too aggressive | Medium | Medium | Configurable limits, monitoring |
| Cache warmer memory leak | Low | Medium | Bounded queue size, cleanup on stop |
| Batch fetch partial failure | Medium | Low | return_exceptions=True, graceful degradation |
| Freshness skip causes stale data | Low | Medium | TTL tuning, STRICT mode for critical paths |

---

## 10. Future Enhancements

1. **Predictive warming**: ML model to predict access patterns and pre-warm
2. **Distributed rate limiting**: Redis-based for multi-instance deployments
3. **Adaptive concurrency**: Auto-tune semaphore based on observed latency
4. **Query planner**: Optimize batch fetch order based on HierarchyIndex topology

---

## Appendix A: Configuration Reference

```python
# Recommended production configuration

CONCURRENCY_CONFIG = {
    "max_concurrent": 10,      # Semaphore limit
    "chunk_size": 50,          # Tasks per gather batch
}

RATE_LIMIT_CONFIG = {
    "requests_per_minute": 1200,  # 80% of Asana limit
    "burst_size": 50,             # Initial burst allowance
    "backoff_base": 1.0,          # Initial backoff seconds
    "backoff_max": 60.0,          # Maximum backoff seconds
    "backoff_multiplier": 2.0,    # Exponential factor
}

CACHE_WARMER_CONFIG = {
    "max_concurrent_warms": 2,    # Background warm concurrency
    "warm_timeout": 5.0,          # Max wait for ensure_warm_async
}

FRESHNESS_CONFIG = {
    "skip_ttl_seconds": 60,       # Skip freshness check if <60s old
    "coalesce_window_ms": 100,    # Batch coalescing window
}
```

---

## Appendix B: File Change Summary

| File | Changes |
|------|---------|
| `src/autom8_asana/dataframes/concurrency.py` | NEW - ConcurrencyController (SUPERSEDED - use autom8y-http) |
| `src/autom8_asana/clients/rate_limiter.py` | NEW - AdaptiveRateLimiter |
| `src/autom8_asana/dataframes/resolver/batch_parent.py` | NEW - BatchParentResolver |
| `src/autom8_asana/cache/warmer.py` | NEW - CacheWarmer |
| `src/autom8_asana/dataframes/builders/base.py` | MODIFY - Use ConcurrencyController (DONE - integrated) |
| `src/autom8_asana/dataframes/builders/project.py` | MODIFY - RC-3: Replace line 633 unbounded gather with `_concurrency_controller.gather_with_limit()`. RC-6: Replace lines 1048-1050 sequential loop with `_concurrency_controller.gather_with_limit()`. |
| `src/autom8_asana/dataframes/resolver/cascading.py` | MODIFY - Cache-first parent lookup |
| `src/autom8_asana/cache/unified.py` | MODIFY - TTL-based freshness skip |
| `src/autom8_asana/services/resolver.py` | MODIFY - Cache warmer integration |

### Appendix B.1: RC-3/RC-6 Implementation Priority

These fixes are **Phase 1** - they use existing infrastructure and require no new modules:

| Priority | Root Cause | Fix | Complexity | Risk |
|----------|------------|-----|------------|------|
| **P0** | RC-3 | Replace unbounded gather at project.py:633 | Low (1 line) | Low |
| **P0** | RC-6 | Replace sequential loop at project.py:1048-1050 | Low (3 lines) | Low |
| P1 | RC-1 | Already fixed in base.py (lines 387, 409, 610) | Done | N/A |
| P2 | RC-2 | BatchParentResolver | Medium | Medium |
| P3 | RC-4 | CacheWarmer | Medium | Medium |
| P3 | RC-5 | FreshnessOptimizer | Low | Low |
