---
status: superseded
superseded_by: /docs/reference/REF-cache-invalidation.md
superseded_date: 2025-12-24
---

# TDD: Lightweight Staleness Detection with Progressive TTL Extension

## Metadata
- **TDD ID**: TDD-CACHE-LIGHTWEIGHT-STALENESS
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **PRD Reference**: [PRD-CACHE-LIGHTWEIGHT-STALENESS](/docs/requirements/PRD-CACHE-LIGHTWEIGHT-STALENESS.md)
- **Related TDDs**:
  - [TDD-CACHE-OPTIMIZATION-P3](/docs/design/TDD-CACHE-OPTIMIZATION-P3.md) - Phase 3 (GID enumeration caching)
  - [TDD-CACHE-OPTIMIZATION-P2](/docs/design/TDD-CACHE-OPTIMIZATION-P2.md) - Phase 2 (Task cache population)
  - [TDD-CACHE-PERF-FETCH-PATH](/docs/design/TDD-CACHE-PERF-FETCH-PATH.md) - Phase 1 foundation
- **Related ADRs**:
  - [ADR-0132](/docs/decisions/ADR-0132-batch-request-coalescing-strategy.md) - Batch request coalescing strategy
  - [ADR-0133](/docs/decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive TTL extension algorithm
  - [ADR-0134](/docs/decisions/ADR-0134-staleness-check-integration-pattern.md) - Staleness check integration pattern

---

## Overview

This TDD defines the architecture for lightweight staleness detection with progressive TTL extension, targeting **90%+ API call reduction** for stable entities. When cached entries expire, instead of performing full API fetches, the system performs lightweight batch `modified_at` checks. Unchanged entities receive progressive TTL extension (doubling up to 24h ceiling), while changed entities trigger full fetches.

**Key Insight**: The SDK already has staleness detection infrastructure (`check_entry_staleness()`, `CacheEntry.is_stale()`, `Freshness.STRICT`) that is fully implemented but not integrated into the cache lookup flow. This initiative activates and extends that infrastructure.

---

## Requirements Summary

Per [PRD-CACHE-LIGHTWEIGHT-STALENESS](/docs/requirements/PRD-CACHE-LIGHTWEIGHT-STALENESS.md):

| Category | Key Requirements | Priority |
|----------|-----------------|----------|
| FR-BATCH-* | 50ms coalescing window, 100 max batch, 10-action chunks | Must |
| FR-STALE-* | Lightweight `modified_at` checks, version comparison | Must |
| FR-TTL-* | Progressive doubling, 24h ceiling, immutable replacement | Must |
| FR-DEGRADE-* | Graceful fallback on check failure | Must |
| FR-OBS-* | Structured logging for all staleness operations | Must/Should |
| NFR-PERF-001 | <100ms latency for lightweight check | Must |
| NFR-PERF-002 | 90%+ API reduction for stable entities | Must |
| NFR-COMPAT-* | No breaking changes to public APIs | Must |

---

## System Context

```
                    +-----------------------------------------------------------+
                    |              Staleness Detection Flow                      |
                    +-----------------------------------------------------------+
                                              |
                                              v
+---------------+    +----------------------------------------------------------+
| SDK Consumer  |--->|                    TasksClient                            |
|               |    |  get_async() / get_batch_async()                          |
+---------------+    +----------------------------------------------------------+
                                              |
                          +-------------------+-------------------+
                          v                                       v
        +---------------------------+        +-----------------------------------+
        |      BaseClient           |        |  StalenessCheckCoordinator [NEW]  |
        |  _cache_get() [ENHANCED]  |        |  - coalescer: RequestCoalescer    |
        |  + staleness integration  |        |  - checker: LightweightChecker    |
        +---------------------------+        +-----------------------------------+
                          |                                       |
                          v                                       v
        +---------------------------+        +-----------------------------------+
        |      CacheProvider        |        |    RequestCoalescer [NEW]         |
        |  - get_versioned()        |        |  - 50ms coalescing window         |
        |  - set_versioned()        |        |  - 100 max batch size             |
        +---------------------------+        |  - Immediate flush at max         |
                                             +-----------------------------------+
                                                              |
                                                              v
                                             +-----------------------------------+
                                             |   LightweightChecker [NEW]        |
                                             |  - Batch GET modified_at          |
                                             |  - 10-action chunking             |
                                             |  - Result distribution            |
                                             +-----------------------------------+
                                                              |
                                                              v
                                             +-----------------------------------+
                                             |        BatchClient                 |
                                             |  POST /batch with opt_fields      |
                                             +-----------------------------------+
```

**Key Changes:**
- New `StalenessCheckCoordinator` orchestrates the staleness check flow
- New `RequestCoalescer` batches requests within 50ms window
- New `LightweightChecker` performs batch `modified_at` API calls
- `BaseClient._cache_get()` integrates with staleness coordinator

---

## Design

### Component Architecture

```
+-----------------------------------------------------------------------------+
|                    StalenessCheckCoordinator [NEW]                           |
|  +-----------------------------------------------------------------------+  |
|  |  Constructor                                                           |  |
|  |  + cache_provider: CacheProvider                                       |  |
|  |  + batch_client: BatchClient                                           |  |
|  |  + coalescer: RequestCoalescer                                         |  |
|  |  + settings: StalenessCheckSettings                                    |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |  Public Methods                                                        |  |
|  |  + check_and_get_async(key, entry_type) -> CacheEntry | None          |  |
|  |      # Main entry point: returns cached data or None (caller fetches) |  |
|  |  + get_extension_stats() -> dict[str, int]                            |  |
|  |      # Returns session metrics (checks, extensions, changes)          |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |  Private Methods                                                       |  |
|  |  - _process_staleness_result(entry, modified_at) -> CacheEntry | None |  |
|  |  - _extend_ttl(entry) -> CacheEntry                                   |  |
|  |  - _log_staleness_check(entry, result, timing)                        |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
|                        RequestCoalescer [NEW]                                |
|  +-----------------------------------------------------------------------+  |
|  |  Constructor                                                           |  |
|  |  + window_ms: int = 50                                                 |  |
|  |  + max_batch: int = 100                                                |  |
|  |  + checker: LightweightChecker                                         |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |  State                                                                 |  |
|  |  - _pending: dict[str, tuple[CacheEntry, asyncio.Future]]             |  |
|  |  - _lock: asyncio.Lock                                                 |  |
|  |  - _timer_task: asyncio.Task | None                                    |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |  Methods                                                               |  |
|  |  + request_check_async(entry: CacheEntry) -> str | None               |  |
|  |      # Queues entry for batch check, returns modified_at or None      |  |
|  |  - _start_timer() -> None                                             |  |
|  |  - _flush_batch() -> None                                             |  |
|  |  - _distribute_results(results: dict[str, str | None]) -> None        |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
|                       LightweightChecker [NEW]                               |
|  +-----------------------------------------------------------------------+  |
|  |  Constructor                                                           |  |
|  |  + batch_client: BatchClient                                           |  |
|  |  + chunk_size: int = 10  # Asana batch limit                          |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |  Methods                                                               |  |
|  |  + check_batch_async(entries: list[CacheEntry])                       |  |
|  |      -> dict[str, str | None]                                         |  |
|  |      # Returns gid -> modified_at (None if error/deleted)             |  |
|  |  - _build_batch_request(gids: list[str]) -> list[BatchRequest]        |  |
|  |  - _parse_batch_response(results: list[BatchResult])                  |  |
|  |      -> dict[str, str | None]                                         |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
|                   StalenessCheckSettings [NEW]                               |
|  +-----------------------------------------------------------------------+  |
|  |  Dataclass (frozen=True)                                               |  |
|  |  + enabled: bool = True                                                |  |
|  |  + base_ttl: int = 300                # 5 minutes                      |  |
|  |  + max_ttl: int = 86400               # 24 hours                       |  |
|  |  + coalesce_window_ms: int = 50                                        |  |
|  |  + max_batch_size: int = 100                                           |  |
|  +-----------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------+
```

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `StalenessCheckCoordinator` | Orchestrates staleness check flow, TTL extension | `cache/staleness_coordinator.py` |
| `RequestCoalescer` | Batches requests within time window | `cache/coalescer.py` |
| `LightweightChecker` | Performs batch `modified_at` API calls | `cache/lightweight_checker.py` |
| `StalenessCheckSettings` | Configuration dataclass | `cache/settings.py` |

---

### Data Model

#### CacheEntry Metadata Convention

Per FR-TTL-004 and ADR-0133, TTL extension tracking uses the existing `metadata` field:

```python
# CacheEntry.metadata convention for staleness checking
{
    "extension_count": 0,    # Number of TTL extensions (0 = base TTL)
    # Other metadata fields preserved
}
```

**Immutable Replacement Pattern** (per FR-TTL-006):

```python
def extend_ttl(entry: CacheEntry, settings: StalenessCheckSettings) -> CacheEntry:
    """Create new CacheEntry with extended TTL.

    Per ADR-0133: Immutable design - create new entry, don't mutate.
    """
    current_count = entry.metadata.get("extension_count", 0)
    new_count = current_count + 1

    # Progressive doubling with ceiling: min(base * 2^count, max)
    new_ttl = min(
        settings.base_ttl * (2 ** new_count),
        settings.max_ttl,
    )

    return CacheEntry(
        key=entry.key,
        data=entry.data,
        entry_type=entry.entry_type,
        version=entry.version,  # Preserved: version unchanged
        cached_at=datetime.now(timezone.utc),  # Reset: new expiration window
        ttl=new_ttl,
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": new_count},
    )
```

#### TTL Progression Table

| Extension Count | TTL (seconds) | TTL (human) | Cumulative Time |
|-----------------|---------------|-------------|-----------------|
| 0 (base) | 300 | 5 minutes | 0 |
| 1 | 600 | 10 minutes | 5 min |
| 2 | 1200 | 20 minutes | 15 min |
| 3 | 2400 | 40 minutes | 35 min |
| 4 | 4800 | 80 minutes | 1h 15min |
| 5 | 9600 | 160 minutes | 2h 35min |
| 6 | 19200 | 320 minutes | 5h 15min |
| 7 | 38400 | 640 minutes | 10h 35min |
| 8 | 76800 | 1280 minutes | 21h 15min |
| 9+ | 86400 | 1440 minutes (24h) - CEILING | 42h 15min+ |

---

### Data Flow

#### Primary Flow: Staleness Check for Expired Entry

```
+-----------------------------------------------------------------------------+
|  TasksClient.get_async(task_gid, ..., staleness_check=True)                  |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  1. BaseClient._cache_get_with_staleness(task_gid, EntryType.TASK)           |
|                                                                              |
|     +-------------------------------------------------------------------+   |
|     |  a. Check cache for entry                                          |   |
|     |     entry = cache.get_versioned(task_gid, EntryType.TASK)         |   |
|     |                                                                    |   |
|     |  b. Entry not found? -> Return None (caller fetches)              |   |
|     |                                                                    |   |
|     |  c. Entry not expired? -> Return entry immediately (cache hit)    |   |
|     |                                                                    |   |
|     |  d. Entry expired? -> Queue for staleness check                   |   |
|     |     modified_at = await coordinator.check_staleness_async(entry)  |   |
|     +-------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  2. StalenessCheckCoordinator.check_staleness_async(entry)                   |
|                                                                              |
|     +-------------------------------------------------------------------+   |
|     |  a. Queue entry to RequestCoalescer                               |   |
|     |     modified_at = await coalescer.request_check_async(entry)      |   |
|     |                                                                    |   |
|     |  b. Coalescer waits up to 50ms (or until max batch reached)       |   |
|     +-------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  3. RequestCoalescer._flush_batch()                                          |
|                                                                              |
|     +-------------------------------------------------------------------+   |
|     |  a. Collect all pending entries (deduplicated by GID)             |   |
|     |  b. Call LightweightChecker.check_batch_async(entries)            |   |
|     |  c. Distribute results to waiting futures                         |   |
|     +-------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  4. LightweightChecker.check_batch_async(entries)                            |
|                                                                              |
|     +-------------------------------------------------------------------+   |
|     |  a. Build batch requests: GET /tasks/{gid}?opt_fields=modified_at |   |
|     |  b. Chunk into groups of 10 (Asana limit)                         |   |
|     |  c. Execute via BatchClient.execute_async()                       |   |
|     |  d. Parse responses, return {gid: modified_at | None}             |   |
|     +-------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|  5. StalenessCheckCoordinator._process_staleness_result(entry, modified_at)  |
|                                                                              |
|     +-------------------------------------------------------------------+   |
|     |  CASE A: modified_at == entry.version (UNCHANGED)                 |   |
|     |    -> Extend TTL: new_entry = extend_ttl(entry, settings)        |   |
|     |    -> Update cache: cache.set_versioned(key, new_entry)          |   |
|     |    -> Return new_entry (cached data still valid)                  |   |
|     |                                                                    |   |
|     |  CASE B: modified_at != entry.version (CHANGED)                   |   |
|     |    -> Return None (caller performs full fetch)                    |   |
|     |                                                                    |   |
|     |  CASE C: modified_at is None (ERROR/DELETED)                      |   |
|     |    -> Invalidate cache: cache.invalidate(key)                    |   |
|     |    -> Return None (caller handles appropriately)                  |   |
|     +-------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------+
```

#### Sequence Diagram: Batch Coalescing

```
Caller A      Caller B      Caller C      Coalescer       Checker        API
   |             |             |              |              |            |
   |--request(t1)------------->|              |              |            |
   |             |             |   start 50ms |              |            |
   |             |--request(t2)-------------->|              |            |
   |             |             |              |              |            |
   |             |             |--request(t3)>|              |            |
   |             |             |              |              |            |
   |             |             |  [50ms expires or max batch]|            |
   |             |             |              |              |            |
   |             |             |   flush()    |              |            |
   |             |             |              |--check([t1,t2,t3])------->|
   |             |             |              |              |--POST /batch->
   |             |             |              |              |<--response--|
   |             |             |              |<--{t1:m1,t2:m2,t3:m3}-----|
   |             |             |              |              |            |
   |<--m1 (set result)---------|              |              |            |
   |             |<--m2 (set result)----------|              |            |
   |             |             |<--m3 (set result)-----------|            |
```

---

### API Contracts

#### StalenessCheckCoordinator

```python
@dataclass
class StalenessCheckCoordinator:
    """Coordinates lightweight staleness checks with progressive TTL extension.

    Per ADR-0134: This coordinator sits between cache lookup and API fetch,
    providing transparent staleness checking for expired entries.
    """

    cache_provider: CacheProvider
    batch_client: BatchClient
    settings: StalenessCheckSettings = field(default_factory=StalenessCheckSettings)
    _coalescer: RequestCoalescer = field(init=False)
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize coalescer with lightweight checker."""
        checker = LightweightChecker(
            batch_client=self.batch_client,
            chunk_size=10,
        )
        self._coalescer = RequestCoalescer(
            window_ms=self.settings.coalesce_window_ms,
            max_batch=self.settings.max_batch_size,
            checker=checker,
        )
        self._stats = {
            "total_checks": 0,
            "unchanged_count": 0,
            "changed_count": 0,
            "error_count": 0,
        }

    async def check_and_get_async(
        self,
        entry: CacheEntry,
    ) -> CacheEntry | None:
        """Check staleness and return updated entry or None.

        Per FR-STALE-001 through FR-STALE-006:
        - Queues entry for batch modified_at check
        - Returns extended-TTL entry if unchanged
        - Returns None if changed (caller should full-fetch)
        - Returns None if error/deleted (caller handles)

        Args:
            entry: Expired cache entry to check.

        Returns:
            CacheEntry with extended TTL if unchanged, None otherwise.
        """

    def get_extension_stats(self) -> dict[str, int]:
        """Return session statistics for observability.

        Per FR-OBS-006: Cumulative session metrics.

        Returns:
            Dict with total_checks, unchanged_count, changed_count, error_count.
        """
        return self._stats.copy()
```

#### RequestCoalescer

```python
@dataclass
class RequestCoalescer:
    """Batches staleness check requests within a time window.

    Per ADR-0132: Implements 50ms coalescing with immediate flush at max batch.
    """

    window_ms: int = 50
    max_batch: int = 100
    checker: LightweightChecker

    _pending: dict[str, tuple[CacheEntry, asyncio.Future[str | None]]] = field(
        default_factory=dict, init=False
    )
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _timer_task: asyncio.Task | None = field(default=None, init=False)

    async def request_check_async(self, entry: CacheEntry) -> str | None:
        """Queue entry for batch staleness check.

        Per FR-BATCH-001 through FR-BATCH-006:
        - Collects entries within window_ms window
        - Deduplicates by GID (FR-BATCH-006)
        - Flushes immediately at max_batch (FR-BATCH-005)
        - Returns modified_at or None on error/deleted

        Args:
            entry: Cache entry to check (must have entry.key = GID).

        Returns:
            modified_at string if successfully checked, None on error/deleted.
        """

    async def _start_timer(self) -> None:
        """Start coalescing timer if not running."""

    async def _flush_batch(self) -> None:
        """Execute batch check and distribute results."""

    def _distribute_results(
        self,
        results: dict[str, str | None],
    ) -> None:
        """Set results on waiting futures."""
```

#### LightweightChecker

```python
@dataclass
class LightweightChecker:
    """Performs batch modified_at checks via Asana Batch API.

    Per FR-STALE-002: Uses opt_fields=modified_at for minimal payload.
    Per FR-BATCH-003: Chunks into groups of 10 (Asana limit).
    """

    batch_client: BatchClient
    chunk_size: int = 10

    async def check_batch_async(
        self,
        entries: list[CacheEntry],
    ) -> dict[str, str | None]:
        """Check modified_at for multiple entries.

        Per FR-STALE-002, FR-BATCH-003:
        - Builds batch requests with opt_fields=modified_at
        - Chunks into groups of chunk_size
        - Returns {gid: modified_at} or {gid: None} on error

        Args:
            entries: Cache entries to check (TASK entries only).

        Returns:
            Dict mapping GID to modified_at string, or None if error/deleted.
        """

    def _build_batch_requests(self, gids: list[str]) -> list[BatchRequest]:
        """Build batch GET requests for modified_at.

        Per Appendix D of PRD: Uses GET /tasks/{gid} with opt_fields=modified_at.
        """
        return [
            BatchRequest(
                relative_path=f"/tasks/{gid}",
                method="GET",
                options={"opt_fields": "modified_at"},
            )
            for gid in gids
        ]

    def _parse_batch_response(
        self,
        results: list[BatchResult],
        gids: list[str],
    ) -> dict[str, str | None]:
        """Parse batch results to modified_at mapping.

        Per FR-DEGRADE-002, FR-DEGRADE-003:
        - Returns None for failed/malformed responses
        - Handles partial batch failures gracefully
        """
```

---

### Integration Design

#### Integration Point: BaseClient._cache_get()

Per ADR-0134, staleness checking integrates into the existing cache lookup flow:

```python
# src/autom8_asana/clients/base.py

class BaseClient:
    # ... existing code ...

    def __init__(
        self,
        http: AsyncHTTPClient,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
        staleness_coordinator: StalenessCheckCoordinator | None = None,  # NEW
    ) -> None:
        # ... existing init ...
        self._staleness_coordinator = staleness_coordinator

    async def _cache_get_with_staleness_async(
        self,
        key: str,
        entry_type: EntryType,
    ) -> CacheEntry | None:
        """Cache get with staleness checking for expired entries.

        Per ADR-0134: Enhanced cache lookup that performs lightweight
        staleness checks on expired entries before returning cache miss.

        Flow:
        1. Check cache for entry
        2. If not found -> return None (cache miss)
        3. If not expired -> return entry (cache hit)
        4. If expired AND staleness check enabled:
           a. Queue for batch modified_at check
           b. If unchanged -> extend TTL, return entry
           c. If changed -> return None (caller fetches)
        5. If expired AND staleness check disabled -> return None

        Args:
            key: Cache key (typically task GID).
            entry_type: Type of cache entry.

        Returns:
            CacheEntry if hit or unchanged, None if miss or changed.
        """
        if self._cache is None:
            return None

        try:
            entry = self._cache.get_versioned(key, entry_type)

            if entry is None:
                logger.debug("Cache miss for %s (key=%s)", entry_type.value, key)
                return None

            if not entry.is_expired():
                logger.debug("Cache hit for %s (key=%s)", entry_type.value, key)
                return entry

            # Entry expired - check staleness if coordinator available
            if self._staleness_coordinator is not None:
                # Only perform staleness check for entry types with modified_at
                if entry_type in (EntryType.TASK, EntryType.PROJECT):
                    result = await self._staleness_coordinator.check_and_get_async(entry)
                    if result is not None:
                        logger.debug(
                            "Staleness check: unchanged for %s (key=%s)",
                            entry_type.value,
                            key,
                        )
                        return result
                    logger.debug(
                        "Staleness check: changed for %s (key=%s)",
                        entry_type.value,
                        key,
                    )

            return None

        except Exception as exc:
            logger.warning(
                "Cache get failed for %s (key=%s): %s",
                entry_type.value,
                key,
                exc,
            )
            return None
```

#### Backward Compatibility Strategy

Per NFR-COMPAT-001 through NFR-COMPAT-005:

1. **Optional Coordinator**: `staleness_coordinator` is optional, defaults to None
2. **Existing Behavior Preserved**: When coordinator is None, behaves exactly as before
3. **No Method Signature Changes**: Public APIs unchanged
4. **Feature Flag**: `StalenessCheckSettings.enabled` allows runtime disable
5. **Entry Type Filtering**: Only TASK and PROJECT support staleness checks

---

### Error Handling Design

#### Graceful Degradation Matrix

| Error Scenario | Detection | Fallback | Log Level |
|---------------|-----------|----------|-----------|
| Batch API timeout | `asyncio.TimeoutError` | Full fetch for affected GIDs | WARNING |
| Batch API error | `BatchResult.success == False` | Full fetch for affected GIDs | WARNING |
| Malformed modified_at | Parse exception | Treat as changed, full fetch | WARNING |
| Entry deleted (404) | `status_code == 404` | Invalidate cache, return None | DEBUG |
| Cache unavailable | `Exception` in cache ops | Proceed to API fetch | WARNING |
| Coalescer overflow | `len(pending) > max_batch` | Immediate flush, new batch | DEBUG |

#### Partial Batch Failure Handling

Per FR-DEGRADE-003:

```python
async def check_batch_async(
    self,
    entries: list[CacheEntry],
) -> dict[str, str | None]:
    """Check batch with partial failure handling."""
    results: dict[str, str | None] = {}
    gids = [e.key for e in entries]

    # Chunk and execute
    for chunk_gids in _chunk(gids, self.chunk_size):
        requests = self._build_batch_requests(chunk_gids)

        try:
            batch_results = await self.batch_client.execute_async(requests)

            for i, result in enumerate(batch_results):
                gid = chunk_gids[i]
                if result.success and result.data:
                    modified_at = result.data.get("modified_at")
                    results[gid] = modified_at
                else:
                    # Partial failure - mark as None (will trigger full fetch)
                    results[gid] = None
                    logger.warning(
                        "staleness_check_partial_failure",
                        extra={
                            "gid": gid,
                            "status_code": result.status_code,
                            "error": result.error,
                        },
                    )
        except Exception as e:
            # Entire chunk failed - mark all as None
            for gid in chunk_gids:
                results[gid] = None
            logger.warning(
                "staleness_check_batch_failure",
                extra={
                    "chunk_size": len(chunk_gids),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

    return results
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Coalescing window | 50ms default | Balances batching efficiency vs latency overhead | [ADR-0132](/docs/decisions/ADR-0132-batch-request-coalescing-strategy.md) |
| Max batch size | 100 entries | Memory-bounded, immediate flush prevents unbounded wait | [ADR-0132](/docs/decisions/ADR-0132-batch-request-coalescing-strategy.md) |
| TTL extension algorithm | Exponential doubling with ceiling | Proven pattern, matches AWS backoff algorithms | [ADR-0133](/docs/decisions/ADR-0133-progressive-ttl-extension-algorithm.md) |
| TTL ceiling | 24 hours (86400s) | Bounds staleness risk while providing significant extension | [ADR-0133](/docs/decisions/ADR-0133-progressive-ttl-extension-algorithm.md) |
| CacheEntry immutability | Replace on extension | Preserves frozen dataclass contract, audit trail | [ADR-0133](/docs/decisions/ADR-0133-progressive-ttl-extension-algorithm.md) |
| Integration location | Coordinator pattern, BaseClient | Clean separation, testability, gradual rollout | [ADR-0134](/docs/decisions/ADR-0134-staleness-check-integration-pattern.md) |
| Entity type scope | TASK only (this phase) | Focus on highest-volume entity, defer others | PRD Scope |

---

## Complexity Assessment

**Level: Module**

This is a new subsystem within the existing cache infrastructure:

| Factor | Assessment |
|--------|-----------|
| Scope | New components within cache subsystem |
| Components | 3 new classes + settings dataclass |
| External Dependencies | Uses existing BatchClient, CacheProvider |
| Data Model Changes | Metadata convention only (no schema change) |
| Breaking Changes | None (optional coordinator parameter) |
| Test Complexity | Unit tests sufficient; integration tests for flow |

**Escalation Check:**
- No new service boundaries
- No new external integrations
- No infrastructure changes
- Stays within Module complexity

---

## Implementation Plan

### Phase 1: Core Components (Day 1)

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 1.1 Create StalenessCheckSettings | `cache/settings.py` | New dataclass | 15 min |
| 1.2 Create LightweightChecker | `cache/lightweight_checker.py` | New file | 1h |
| 1.3 Create RequestCoalescer | `cache/coalescer.py` | New file | 1.5h |
| 1.4 Create StalenessCheckCoordinator | `cache/staleness_coordinator.py` | New file | 1h |

### Phase 2: Integration (Day 1-2)

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 2.1 Add staleness_coordinator to BaseClient | `clients/base.py` | Optional param, helper method | 45 min |
| 2.2 Wire coordinator in TasksClient | `clients/tasks.py` | Use staleness-aware cache get | 30 min |
| 2.3 Add extend_ttl helper | `cache/entry.py` or `staleness_coordinator.py` | TTL extension function | 30 min |

### Phase 3: Testing (Day 2)

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 3.1 Unit tests for LightweightChecker | `test_lightweight_checker.py` | Batch format, chunking, parsing | 1h |
| 3.2 Unit tests for RequestCoalescer | `test_coalescer.py` | Window, max batch, concurrency | 1.5h |
| 3.3 Unit tests for Coordinator | `test_staleness_coordinator.py` | TTL extension, result processing | 1h |
| 3.4 Unit tests for progressive TTL | `test_progressive_ttl.py` | Doubling, ceiling, reset | 45 min |
| 3.5 Integration tests | `test_staleness_flow.py` | E2E flow validation | 1.5h |

### Phase 4: Observability & Documentation (Day 2)

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 4.1 Add structured logging | All new files | Per FR-OBS-* | 45 min |
| 4.2 Update docs/INDEX.md | `docs/INDEX.md` | Register new documents | 15 min |

### Dependency Graph

```
Phase 1.1 (Settings) ----+
                         |
Phase 1.2 (Checker) -----+----> Phase 1.4 (Coordinator) ----> Phase 2 (Integration)
                         |
Phase 1.3 (Coalescer) ---+
                                                              |
                                                              v
                                                        Phase 3 (Testing)
                                                              |
                                                              v
                                                        Phase 4 (Observability)
```

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 50ms coalescing adds latency | Low | Medium | Configurable window, immediate flush at max |
| Progressive TTL causes stale reads | Medium | Low | 24h ceiling, reset on any change |
| Concurrent access race conditions | High | Medium | asyncio.Lock in coalescer |
| Batch API rate limits | Medium | Low | Batch counts as 1 request |
| Entry replacement overhead | Low | Low | Already used pattern |
| Process restart loses extension state | Low | Medium | Acceptable; resets to base TTL |

---

## Observability

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `staleness_check_total` | Counter | Total staleness checks performed |
| `staleness_check_unchanged` | Counter | Checks that found unchanged entries |
| `staleness_check_changed` | Counter | Checks that found changed entries |
| `staleness_check_error` | Counter | Checks that failed |
| `coalesce_batch_size` | Histogram | Entries per batch |
| `coalesce_window_utilization_ms` | Histogram | Actual wait time before flush |
| `ttl_extension_count` | Histogram | Extension count at check time |
| `api_calls_saved` | Counter | Full fetches avoided |

### Logging

```python
# Staleness check result
logger.info(
    "staleness_check_result",
    extra={
        "cache_operation": "staleness_check",
        "gid": entry.key,
        "entry_type": entry.entry_type.value,
        "staleness_result": "unchanged",  # or "changed", "error", "deleted"
        "previous_ttl": entry.ttl,
        "new_ttl": new_entry.ttl,
        "extension_count": new_entry.metadata.get("extension_count", 0),
        "check_duration_ms": round(duration_ms, 2),
    },
)

# Batch coalescing
logger.debug(
    "coalesce_batch_flush",
    extra={
        "cache_operation": "staleness_check",
        "batch_size": len(batch),
        "unique_gids": len(set(gids)),
        "coalesce_window_ms": self.window_ms,
        "entries_coalesced": len(batch),
        "chunk_count": (len(batch) + 9) // 10,
    },
)

# TTL extension
logger.debug(
    "ttl_extended",
    extra={
        "cache_operation": "staleness_check",
        "gid": entry.key,
        "previous_ttl": entry.ttl,
        "new_ttl": new_ttl,
        "extension_count": new_count,
    },
)
```

---

## Testing Strategy

### Unit Tests

| Test Case | File | Validates |
|-----------|------|-----------|
| `test_coalescer_50ms_window` | `test_coalescer.py` | FR-BATCH-001 |
| `test_coalescer_max_batch_size` | `test_coalescer.py` | FR-BATCH-002 |
| `test_coalescer_immediate_flush_at_max` | `test_coalescer.py` | FR-BATCH-005 |
| `test_coalescer_gid_deduplication` | `test_coalescer.py` | FR-BATCH-006 |
| `test_coalescer_concurrent_callers` | `test_coalescer.py` | FR-BATCH-004 |
| `test_checker_batch_chunking` | `test_lightweight_checker.py` | FR-BATCH-003 |
| `test_checker_opt_fields_format` | `test_lightweight_checker.py` | FR-STALE-002 |
| `test_checker_partial_failure` | `test_lightweight_checker.py` | FR-DEGRADE-003 |
| `test_coordinator_unchanged_extends_ttl` | `test_staleness_coordinator.py` | FR-TTL-001 |
| `test_coordinator_changed_returns_none` | `test_staleness_coordinator.py` | FR-STALE-005 |
| `test_ttl_doubles_on_unchanged` | `test_progressive_ttl.py` | FR-TTL-001 |
| `test_ttl_ceiling_enforced` | `test_progressive_ttl.py` | FR-TTL-002 |
| `test_ttl_reset_on_change` | `test_progressive_ttl.py` | FR-TTL-003 |
| `test_extension_count_tracking` | `test_progressive_ttl.py` | FR-TTL-004 |
| `test_entry_immutability_preserved` | `test_progressive_ttl.py` | FR-TTL-006 |

### Integration Tests

| Test Case | File | Validates |
|-----------|------|-----------|
| `test_full_staleness_flow_unchanged` | `test_staleness_flow.py` | E2E unchanged path |
| `test_full_staleness_flow_changed` | `test_staleness_flow.py` | E2E changed path |
| `test_progressive_ttl_over_time` | `test_staleness_flow.py` | TTL progression |
| `test_batch_coalescing_under_load` | `test_staleness_flow.py` | Concurrent batching |
| `test_graceful_degradation` | `test_staleness_flow.py` | All FR-DEGRADE-* |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved in design |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Architect | Initial draft based on PRD and discovery |

---

## Appendix A: Batch API Request Format

Per PRD Appendix D:

```http
POST /batch
Content-Type: application/json

{
  "data": {
    "actions": [
      {
        "method": "GET",
        "relative_path": "/tasks/1234567890",
        "options": { "opt_fields": "modified_at" }
      },
      {
        "method": "GET",
        "relative_path": "/tasks/2345678901",
        "options": { "opt_fields": "modified_at" }
      }
    ]
  }
}
```

**Response:**
```json
[
  {
    "status_code": 200,
    "body": {
      "data": {
        "gid": "1234567890",
        "modified_at": "2025-12-23T10:30:00.000Z"
      }
    }
  },
  {
    "status_code": 200,
    "body": {
      "data": {
        "gid": "2345678901",
        "modified_at": "2025-12-23T09:15:00.000Z"
      }
    }
  }
]
```

---

## Appendix B: Key File Locations

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/autom8_asana/cache/staleness.py` | Existing staleness helpers | 19-66, 69-120 |
| `src/autom8_asana/cache/entry.py` | CacheEntry dataclass | 42-102 |
| `src/autom8_asana/cache/freshness.py` | Freshness enum | 8-29 |
| `src/autom8_asana/clients/base.py` | Base client with cache helpers | 82-120 |
| `src/autom8_asana/batch/client.py` | Batch API client | 22-62, 356-406 |
| `src/autom8_asana/cache/staleness_coordinator.py` | NEW: Coordinator | - |
| `src/autom8_asana/cache/coalescer.py` | NEW: Request coalescer | - |
| `src/autom8_asana/cache/lightweight_checker.py` | NEW: Lightweight checker | - |

---

## Appendix C: Backward Compatibility Checklist

- [ ] `BaseClient` constructor accepts new `staleness_coordinator` param as optional
- [ ] Default value `None` means no staleness checking (existing behavior preserved)
- [ ] No changes to public method return types
- [ ] No changes to public method signatures
- [ ] Existing tests pass without modification
- [ ] Graceful degradation when `staleness_coordinator=None`
- [ ] `CacheEntry` structure unchanged (metadata convention only)
