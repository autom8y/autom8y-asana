# Discovery: Cache Lightweight Staleness Check Initiative

## Metadata

| Attribute | Value |
|-----------|-------|
| **Document ID** | DISCOVERY-CACHE-LIGHTWEIGHT-STALENESS |
| **Author** | Requirements Analyst |
| **Date** | 2025-12-23 |
| **Status** | Complete |
| **Related** | PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS, ADR-0131 (Phase 3 Complete), PRD-CACHE-OPT-P3 |

---

## Executive Summary

This discovery document analyzes the existing staleness detection infrastructure to inform implementation of lightweight `modified_at` checks with progressive TTL extension. The goal is 90%+ API call reduction for stable entities by replacing full API fetches with minimal `modified_at` checks when TTL expires.

**Key Findings:**

1. **Staleness infrastructure exists but is unused** - `check_entry_staleness()`, `CacheEntry.is_stale()`, and version comparison utilities are fully implemented but not integrated into the cache lookup flow
2. **Batch API exists but not for lightweight checks** - The batch client (`batch/client.py`) supports 10 actions per batch, but no batch `modified_at` check pattern exists
3. **Progressive TTL requires CacheEntry modification** - Current `CacheEntry` is immutable (`frozen=True`); TTL extension requires replacing entries
4. **No existing coalescing pattern** - Request batching uses `asyncio.gather` without time-window coalescing
5. **Only TASK and PROJECT have reliable `modified_at`** - Other entity types (SECTION, USER, CUSTOM_FIELD) lack this field

---

## Section 1: Current Staleness Detection Flow

### 1.1 Staleness Flow Diagram

```
Current Flow (TTL-only):
========================

cache.get_versioned(key, entry_type, freshness)
    |
    +-- Entry not found? --> Return None (cache miss)
    |
    +-- Entry expired (TTL)? --> Return None (cache miss)
    |
    +-- Entry found & valid? --> Return entry (cache hit)

    [NO version comparison in practice - freshness parameter exists but is not
     used by clients to trigger STRICT mode staleness checks]


Target Flow (Lightweight Staleness Check):
==========================================

cache.get(key, entry_type)
    |
    +-- Entry not found? --> Queue for full fetch
    |
    +-- Entry found & TTL not expired? --> Return entry (immediate hit)
    |
    +-- Entry found & TTL expired? --> Queue for batch staleness check
    |
    v
Batch Coalescer (50ms window)
    |
    v
Lightweight API Check (GET /tasks?opt_fields=modified_at&task_gid=...)
    |
    +-- Unchanged? --> Extend TTL progressively, return cached entry
    |
    +-- Changed? --> Queue for full fetch, reset TTL to base
```

### 1.2 Entry Points for Staleness Detection

| Location | Current Behavior | Gap |
|----------|------------------|-----|
| `TasksClient.get_async()` (L116-155) | Checks `is_expired()`, does NOT check version staleness | No version comparison |
| `BaseClient._cache_get()` (L82-120) | Checks `is_expired()` only | No `Freshness.STRICT` handling |
| `cache/loader.load_task_entry()` (L22-109) | Has staleness check infrastructure, uses `check_entry_staleness()` | Not called from clients |
| `cache/loader.load_batch_entries()` (L196-305) | Has batch staleness check, requires `current_versions` dict upfront | Requires versions before check |

### 1.3 Staleness Detection Functions (Exist but Unused)

**File: `cache/staleness.py`**

```python
# check_entry_staleness() - Lines 19-66
# Checks if a cache entry is stale based on TTL and version comparison
# Returns: True if entry is stale and should be refetched

def check_entry_staleness(
    entry: CacheEntry,
    current_modified_at: str | None,     # <-- Requires upfront modified_at
    freshness: Freshness = Freshness.EVENTUAL,
) -> bool:
    # If entry is TTL-expired, it's always stale
    if entry.is_expired():
        return True

    # For EVENTUAL freshness, TTL expiration is the only staleness check
    if freshness == Freshness.EVENTUAL:
        return False

    # For STRICT freshness, we must verify against current version
    if current_modified_at is None:
        return True  # Cannot verify without current version

    return is_stale(entry.version, current_modified_at)
```

**Gap Analysis**: This function requires `current_modified_at` as input, which means the caller must have already fetched `modified_at` from the API. The lightweight staleness check initiative needs to invert this - check SHOULD trigger the API call, not require it as input.

**File: `cache/entry.py`**

```python
# CacheEntry.is_stale() - Lines 131-142
def is_stale(self, current_version: datetime | str) -> bool:
    """Check if entry is stale compared to current version."""
    return not self.is_current(current_version)

# CacheEntry.is_current() - Lines 103-129
def is_current(self, current_version: datetime | str) -> bool:
    """Check if cached version matches or is newer than current."""
    # ... datetime parsing and comparison ...
    return cached_version >= current_version
```

### 1.4 Freshness Modes

**File: `cache/freshness.py`**

```python
class Freshness(str, Enum):
    STRICT = "strict"    # Always validate version against source before returning
    EVENTUAL = "eventual"  # Return cached data if within TTL without validation
```

**Current Usage**: `Freshness.EVENTUAL` is the default everywhere. `STRICT` mode is defined but not actively used in production paths.

---

## Section 2: Gap Analysis

### 2.1 Staleness Detection Gaps

| Component | Exists | Missing | Effort |
|-----------|--------|---------|--------|
| `CacheEntry.is_stale()` | Yes | Not invoked in fetch flow | Low |
| `check_entry_staleness()` | Yes | Requires `current_modified_at` upfront (inverted) | Medium |
| `check_batch_staleness()` | Yes | Requires `current_versions` dict upfront | Medium |
| Version comparison (`versioning.py`) | Yes | None | N/A |
| `Freshness.STRICT` mode | Yes | Not triggered in cache lookup | Low |

### 2.2 Batch API Gaps

| Component | Exists | Missing | Effort |
|-----------|--------|---------|--------|
| `BatchClient` | Yes | No batch GET for `modified_at` | Medium |
| Batch request format | Yes | No lightweight check pattern | Medium |
| Chunk handling (10/batch) | Yes | None | N/A |
| `ModificationCheckCache` (25s TTL) | Yes | Different purpose, fixed TTL | Medium |

### 2.3 Progressive TTL Gaps

| Component | Exists | Missing | Effort |
|-----------|--------|---------|--------|
| `CacheEntry.ttl` field | Yes | Immutable, cannot update in-place | High |
| TTL configuration | Yes | No extension tracking metadata | Medium |
| TTL resolution logic | Yes | No progressive extension algorithm | Medium |
| Per-entity TTL | Yes | No extension count storage | Medium |

### 2.4 Coalescing Pattern Gaps

| Component | Exists | Missing | Effort |
|-----------|--------|---------|--------|
| `asyncio.gather` usage | Yes | No time-window coalescing | High |
| Semaphore-based concurrency | Yes | None | N/A |
| Request batching | Yes | No time-based collection window | High |

---

## Section 3: Asana API Batch Format Specification

### 3.1 Lightweight Check API Call Format

For batch `modified_at` checks, the Asana API supports fetching minimal fields via `opt_fields`:

```http
GET /tasks/{task_gid}?opt_fields=modified_at
```

**Response:**
```json
{
  "data": {
    "gid": "1234567890",
    "modified_at": "2025-12-23T10:30:00.000Z"
  }
}
```

**Bandwidth Comparison:**

| Request Type | Response Size | Fields Returned |
|--------------|---------------|-----------------|
| Full task fetch | ~5-10 KB | All fields |
| Lightweight check | ~100 bytes | `gid`, `modified_at` only |

### 3.2 Batch API Format for Multiple Tasks

The existing batch client uses Asana's `/batch` endpoint:

```http
POST /batch
Content-Type: application/json

{
  "data": {
    "actions": [
      {
        "method": "GET",
        "relative_path": "/tasks/1234567890",
        "options": {
          "opt_fields": "modified_at"
        }
      },
      {
        "method": "GET",
        "relative_path": "/tasks/2345678901",
        "options": {
          "opt_fields": "modified_at"
        }
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

### 3.3 Batch Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Max actions per batch | 10 | ADR-0010, `batch/client.py:BATCH_SIZE_LIMIT` |
| Rate limit | Counts as 1 request per batch | Asana API docs |
| Sequential chunks | Required for large batches | ADR-0010 |

### 3.4 Alternative: Section-Based Task Listing

For projects with many tasks, an alternative approach uses section-level task listing with `opt_fields=modified_at`:

```http
GET /tasks?section={section_gid}&opt_fields=gid,modified_at
```

This returns `modified_at` for all tasks in a section in a single call, which may be more efficient than individual batch checks for large projects.

**Trade-off**: Fetches all GIDs (including unchanged), vs batch checks only for expired entries.

---

## Section 4: Progressive TTL Implementation Options

### 4.1 Option A: Replace CacheEntry on Extension (Recommended)

**Approach**: Create new `CacheEntry` with extended TTL and updated metadata.

```python
@dataclass
class CacheEntry:
    # Existing fields...
    metadata: dict[str, Any] = field(default_factory=dict)
    # Store extension_count in metadata: {"extension_count": 3}
```

**Extension Algorithm**:
```python
def extend_ttl(entry: CacheEntry, base_ttl: int = 300) -> CacheEntry:
    current_count = entry.metadata.get("extension_count", 0)
    new_count = current_count + 1

    # Double TTL: 300 -> 600 -> 1200 -> 2400 -> 4800 -> ... -> max 86400
    new_ttl = min(base_ttl * (2 ** new_count), 86400)

    return CacheEntry(
        key=entry.key,
        data=entry.data,
        entry_type=entry.entry_type,
        version=entry.version,
        cached_at=datetime.now(timezone.utc),  # Reset cached_at
        ttl=new_ttl,
        project_gid=entry.project_gid,
        metadata={**entry.metadata, "extension_count": new_count},
    )
```

**Pros**:
- Works with immutable `CacheEntry` design
- Clear audit trail via `extension_count`
- No schema changes required

**Cons**:
- Creates new object on every extension
- Requires cache write on every check (even if unchanged)

### 4.2 Option B: Add Mutable Extension Fields

**Approach**: Make `CacheEntry` mutable for TTL extension.

```python
@dataclass  # Remove frozen=True
class CacheEntry:
    # Existing fields...
    ttl: int | None = 300
    extension_count: int = 0

    def extend_ttl(self, base_ttl: int = 300) -> None:
        self.extension_count += 1
        self.ttl = min(base_ttl * (2 ** self.extension_count), 86400)
        self.cached_at = datetime.now(timezone.utc)
```

**Pros**:
- More efficient (in-place update)
- Direct mutation semantics

**Cons**:
- Breaks immutability contract
- Requires code audit for shared references
- Thread safety concerns

### 4.3 Option C: Separate TTL Extension Cache

**Approach**: Store extension metadata in separate cache, keep `CacheEntry` immutable.

```python
# In-memory extension tracker (similar to ModificationCheckCache)
class TTLExtensionTracker:
    def __init__(self):
        self._extensions: dict[str, int] = {}  # key -> extension_count
        self._lock = threading.Lock()

    def get_effective_ttl(self, key: str, base_ttl: int) -> int:
        count = self._extensions.get(key, 0)
        return min(base_ttl * (2 ** count), 86400)

    def record_extension(self, key: str) -> None:
        with self._lock:
            self._extensions[key] = self._extensions.get(key, 0) + 1
```

**Pros**:
- Preserves `CacheEntry` immutability
- Minimal cache write overhead
- Clear separation of concerns

**Cons**:
- New component to maintain
- Extension state lost on process restart
- Must be thread-safe

### 4.4 Recommendation

**Option A (Replace CacheEntry)** is recommended because:
1. Works with existing immutable design
2. Uses existing `metadata` field (no schema change)
3. Extension count persists across Redis/cache restarts
4. Audit trail for debugging

---

## Section 5: Entity Type Support Matrix

### 5.1 Entities with `modified_at` Field

| EntryType | Has `modified_at` | Can Use Lightweight Check | Notes |
|-----------|-------------------|---------------------------|-------|
| TASK | Yes | Yes | Primary target |
| PROJECT | Yes | Yes | Secondary target |
| SUBTASKS | Derived from parent | Yes (via parent) | Check parent task |
| DEPENDENCIES | Derived from task | Yes (via task) | Check owning task |
| DEPENDENTS | Derived from task | Yes (via task) | Check owning task |
| STORIES | No (has timestamp per story) | No | Use story timestamp logic |
| ATTACHMENTS | Derived from task | Yes (via task) | Check owning task |
| DATAFRAME | Composite | No | Aggregate of tasks |

### 5.2 Entities WITHOUT `modified_at` Field

| EntryType | Staleness Strategy | Recommendation |
|-----------|-------------------|----------------|
| SECTION | No `modified_at` | TTL-only (30 min per ADR-0131) |
| USER | No `modified_at` | TTL-only (stable data) |
| CUSTOM_FIELD | No `modified_at` | TTL-only (rarely changes) |
| PROJECT_SECTIONS | No `modified_at` | TTL-only (30 min per ADR-0131) |
| GID_ENUMERATION | No `modified_at` | TTL-only (5 min per ADR-0131) |
| DETECTION | Uses task.modified_at | Yes (via task) | Piggyback on task check |

### 5.3 Scope for This Initiative

**In Scope**: TASK entities only (per PROMPT-0 constraint)

**Rationale**: Tasks are the primary unit of work and have the highest volume. Nested attributes (subtasks, dependencies) follow their own TTL and can leverage parent task staleness checks in future phases.

---

## Section 6: Existing Coalescing Patterns

### 6.1 Current Batching Patterns

**Pattern 1: `asyncio.gather` for Parallel Execution**

Location: `parallel_fetch.py`, `loader.py`, `resolution.py`

```python
# From parallel_fetch.py:160-164
results = await asyncio.gather(
    *[self._fetch_section(section.gid, semaphore) for section in sections],
    return_exceptions=True,
)
```

**Characteristics**:
- No time-based coalescing
- All requests known upfront
- Semaphore controls concurrency

**Pattern 2: `ModificationCheckCache` (25s TTL)**

Location: `cache/batch.py`

```python
# From batch.py:270-320
async def fetch_task_modifications(
    gids: list[str],
    batch_api: Callable[[list[str]], Awaitable[dict[str, str]]],
    cache_ttl: float = DEFAULT_MODIFICATION_CHECK_TTL,
) -> dict[str, str]:
    cache = get_modification_cache(ttl=cache_ttl)
    cached, uncached = cache.get_many(gids)

    if not uncached:
        return cached  # All cached, no API call

    fetched = await batch_api(uncached)
    cache.set_many(fetched)

    return {**cached, **fetched}
```

**Characteristics**:
- Fixed 25s TTL (per ADR-0018)
- Per-process isolation (not shared across ECS tasks)
- Thread-safe with `threading.Lock`
- Requires caller to provide batch API function

### 6.2 Gap: Time-Window Coalescing

**What's Missing**: A pattern that:
1. Collects incoming requests over a time window (e.g., 50ms)
2. Groups them into a single batch
3. Makes one API call for all collected requests
4. Distributes results back to original callers

**Proposed Pattern** (for implementation):

```python
class RequestCoalescer:
    """Coalesces requests within a time window into batches."""

    def __init__(self, window_ms: int = 50, max_batch: int = 100):
        self._window_ms = window_ms
        self._max_batch = max_batch
        self._pending: list[tuple[str, asyncio.Future]] = []
        self._lock = asyncio.Lock()
        self._timer_task: asyncio.Task | None = None

    async def request(self, gid: str) -> str:
        """Add request to batch, returns modified_at when ready."""
        future: asyncio.Future = asyncio.Future()

        async with self._lock:
            self._pending.append((gid, future))

            # Start timer if not running
            if self._timer_task is None or self._timer_task.done():
                self._timer_task = asyncio.create_task(
                    self._flush_after_delay()
                )

            # Flush if batch full
            if len(self._pending) >= self._max_batch:
                await self._flush()

        return await future

    async def _flush_after_delay(self) -> None:
        await asyncio.sleep(self._window_ms / 1000)
        async with self._lock:
            await self._flush()

    async def _flush(self) -> None:
        if not self._pending:
            return

        # Extract pending requests
        batch = self._pending[:self._max_batch]
        self._pending = self._pending[self._max_batch:]

        gids = [gid for gid, _ in batch]
        futures = [future for _, future in batch]

        # Make batch API call
        try:
            results = await self._fetch_batch(gids)
            for i, (gid, future) in enumerate(batch):
                if gid in results:
                    future.set_result(results[gid])
                else:
                    future.set_exception(KeyError(f"No result for {gid}"))
        except Exception as e:
            for _, future in batch:
                future.set_exception(e)
```

---

## Section 7: Integration Points

### 7.1 Recommended Integration Location

**Primary**: `TaskCacheCoordinator` or new `StalenessCheckCoordinator`

The existing `TaskCacheCoordinator` (if it exists) or a new coordinator should orchestrate:
1. Cache lookup
2. TTL expiration detection
3. Lightweight staleness check queuing
4. Progressive TTL extension

### 7.2 Cache Provider Protocol Extensions

The current `CacheProvider` protocol supports:
- `get_versioned()` / `set_versioned()` - Single entry operations
- `get_batch()` / `set_batch()` - Batch operations
- `check_freshness()` - Exists but requires `current_version` upfront

**Potential New Method**:
```python
def extend_ttl(
    self,
    key: str,
    entry_type: EntryType,
    new_ttl: int,
    metadata_updates: dict[str, Any] | None = None,
) -> bool:
    """Extend TTL for an existing entry without full replacement."""
```

### 7.3 Client Integration

**Option 1**: Modify `BaseClient._cache_get()`

```python
def _cache_get(
    self,
    key: str,
    entry_type: EntryType,
    enable_staleness_check: bool = True,  # NEW parameter
) -> CacheEntry | None:
    # ... existing logic ...

    # NEW: If expired but staleness check enabled, queue for batch check
    if entry is not None and entry.is_expired() and enable_staleness_check:
        return self._queue_staleness_check(entry)
```

**Option 2**: Higher-level coordinator (recommended)

Introduce `StalenessCheckCoordinator` that wraps cache operations and manages batch checking transparently.

---

## Section 8: Recommended Integration Points

### 8.1 New Components Required

| Component | Purpose | Location |
|-----------|---------|----------|
| `StalenessCheckCoordinator` | Orchestrates lightweight checks | `cache/staleness_coordinator.py` |
| `RequestCoalescer` | Batches requests within time window | `cache/coalescer.py` |
| `LightweightChecker` | Performs batch `modified_at` API calls | `cache/lightweight_check.py` |

### 8.2 Existing Components to Modify

| Component | Modification | Effort |
|-----------|--------------|--------|
| `CacheEntry` | Add `extension_count` to metadata convention | Low |
| `TasksClient._cache_get()` | Integrate with staleness coordinator | Medium |
| `Freshness` enum | Consider new mode `LIGHTWEIGHT` or use `STRICT` | Low |
| `check_entry_staleness()` | Invert to return action (extend/fetch) | Medium |

### 8.3 Wire-Up Flow

```
TasksClient.get_async()
    |
    v
StalenessCheckCoordinator.get_or_check(key, entry_type)
    |
    +-- Cache hit (not expired) --> Return immediately
    |
    +-- Cache miss --> Return None, caller fetches
    |
    +-- Cache expired --> Queue to RequestCoalescer
                              |
                              v (50ms window)
                          LightweightChecker.check_batch(gids)
                              |
                              +-- Unchanged --> extend_ttl(), return cached
                              +-- Changed --> Return None, caller fetches
```

---

## Section 9: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Coalescing adds latency (50ms wait) | Medium | Low | Make window configurable, monitor P99 |
| Batch API rate limits | Low | Medium | Batch counts as 1 request per ADR-0018 |
| Progressive TTL causes stale reads | Low | Medium | Max ceiling 24h, reset on any change |
| Thread safety in coalescer | Medium | High | Use `asyncio.Lock`, thorough testing |
| Process restart loses extension state | Medium | Low | Acceptable trade-off; resets to base TTL |
| `CacheEntry` replacement overhead | Low | Low | Already used for cache population |

---

## Section 10: Open Questions for Requirements Phase

### Resolved Questions

1. **Batch API format** - Confirmed: Use existing `/batch` endpoint with `opt_fields=modified_at`
2. **TTL storage** - Recommendation: Use `metadata` field in `CacheEntry`
3. **Entity type filtering** - Confirmed: Only TASK for this phase (per PROMPT-0)
4. **Coalescing implementation** - Recommendation: New `RequestCoalescer` with asyncio

### Questions Requiring User/Stakeholder Input

1. **First-session activation**: Should lightweight checks be enabled by default or require opt-in?
2. **Per-entity type ceiling**: Should different entity types have different max TTL ceilings?
3. **Freshness mode**: Use existing `STRICT` mode or introduce new `LIGHTWEIGHT` mode?

### Questions for Architecture Phase

1. **Coordinator placement**: Where in the call hierarchy should `StalenessCheckCoordinator` sit?
2. **Batch API error handling**: How to handle partial failures in batch `modified_at` checks?
3. **Metrics instrumentation**: What metrics/counters are required for observability?

---

## Section 11: Appendices

### Appendix A: File Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| `cache/staleness.py` | Staleness detection helpers | 19-66, 69-120, 123-147 |
| `cache/entry.py` | CacheEntry dataclass | 42-102, 103-142 |
| `cache/freshness.py` | Freshness enum | 8-29 |
| `cache/versioning.py` | Version comparison | 8-45, 48-61, 80-101 |
| `cache/batch.py` | Modification check cache | 41-63, 270-320 |
| `cache/loader.py` | Multi-entry loading | 22-109, 196-305 |
| `clients/base.py` | Base client with cache helpers | 82-120, 122-179 |
| `clients/tasks.py` | Task client | 116-155 |
| `batch/client.py` | Batch API client | 22-62, 65-130, 356-406 |
| `config.py` | TTL configuration | 52-62, 277-416 |

### Appendix B: TTL Configuration Reference

| Entity Type | Default TTL | Location |
|-------------|-------------|----------|
| Generic Task | 300s (5 min) | `config.py:52` |
| Business | 3600s (1 hour) | `config.py:55` |
| Contact | 900s (15 min) | `config.py:56` |
| Unit | 900s (15 min) | `config.py:57` |
| Offer | 180s (3 min) | `config.py:58` |
| Process | 60s (1 min) | `config.py:59` |
| PROJECT_SECTIONS | 1800s (30 min) | `parallel_fetch.py:119` |
| GID_ENUMERATION | 300s (5 min) | `parallel_fetch.py:120` |

### Appendix C: Related ADRs and PRDs

| Document | Relevance |
|----------|-----------|
| ADR-0018 | Batch modification checking (25s TTL pattern) |
| ADR-0019 | Staleness detection algorithm |
| ADR-0026 | Two-tier cache architecture |
| ADR-0131 | GID enumeration cache strategy (Phase 3) |
| PRD-CACHE-OPT-P3 | Phase 3 requirements (GID caching) |
| PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS | Initiative specification |

---

## Conclusion

The autom8_asana SDK has comprehensive staleness detection infrastructure that is defined but not actively used in the cache lookup flow. Implementing lightweight staleness checks requires:

1. **Inverting the staleness check flow** - Currently requires `modified_at` upfront; should trigger the check
2. **Adding request coalescing** - No time-window batching exists; need new component
3. **Implementing progressive TTL** - Use `CacheEntry.metadata` for extension tracking
4. **Integrating batch API** - Existing batch client can be extended for GET requests

The infrastructure is well-designed and the gaps are addressable with targeted modifications rather than architectural overhaul.

---

*Document prepared by Requirements Analyst for Session 1: Discovery Phase*
*Next: Session 2 - Requirements Definition (PRD-CACHE-LIGHTWEIGHT-STALENESS)*
