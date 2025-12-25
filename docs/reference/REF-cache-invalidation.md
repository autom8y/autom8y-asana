# REF: Cache Invalidation and Staleness Detection

## Metadata

**Document ID**: REF-CACHE-INVALIDATION
**Type**: Reference
**Status**: Active
**Created**: 2025-12-24
**Supersedes**: PRD-CACHE-LIGHTWEIGHT-STALENESS, PRD-WATERMARK-CACHE, TDD-CACHE-LIGHTWEIGHT-STALENESS

---

## Overview

The autom8_asana SDK uses a multi-layered staleness detection strategy combining TTL expiration, version-based validation, and lightweight incremental checks. The system balances freshness guarantees with API efficiency, achieving >90% API call reduction for stable entities.

### Key Concepts

- **TTL (Time-to-Live)**: Fixed expiration time from cache write
- **Progressive TTL**: Exponentially increasing TTL for stable entities
- **Versioning**: `modified_at` timestamp comparison for staleness detection
- **Lightweight Checks**: Batch `modified_at` validation without full payload
- **Freshness Modes**: STRICT (validate before return) vs EVENTUAL (trust TTL)

---

## Invalidation Strategies

### Explicit Invalidation (Write-Through)

Mutations via SaveSession trigger immediate cache invalidation:

```python
session = SaveSession(client)
session.track(task)
task.name = "Updated Name"

await session.commit_async()

# Automatically invalidates:
# 1. EntryType.TASK for task.gid
# 2. EntryType.DATAFRAME for task.gid:project_gid (all projects)
# 3. EntryType.DETECTION for task.gid
# 4. EntryType.SUBTASKS for task.gid (if has subtasks)
```

#### Invalidation Scope

| Operation | Invalidated Entry Types | Key Pattern |
|-----------|------------------------|-------------|
| CREATE | TASK, DATAFRAME, DETECTION | New GID assigned by API |
| UPDATE | TASK, DATAFRAME, DETECTION, SUBTASKS* | Mutated task GID |
| DELETE | TASK, DATAFRAME, DETECTION, SUBTASKS* | Deleted task GID |
| Actions (add_tag, etc.) | TASK, DATAFRAME | Affected task GID |

*SUBTASKS invalidated only if task has children

#### Multi-Project Invalidation

Tasks can be members of multiple projects. Invalidation must handle all contexts:

```python
# Task is multi-homed in Projects A and B
task.memberships = [
    {"project": {"gid": "project_a"}},
    {"project": {"gid": "project_b"}},
]

# Invalidates:
# - {task_gid}:project_a
# - {task_gid}:project_b
```

**Requirement**: Fetch tasks with `opt_fields=memberships.project.gid` to enable full invalidation.

**Fallback**: If memberships unavailable, invalidate only the operation context project.

### TTL Expiration

Time-based automatic expiration.

#### Default TTLs by Entry Type

| Entry Type | TTL | Rationale |
|------------|-----|-----------|
| TASK (generic) | 300s (5 min) | Balanced freshness vs. cache hit rate |
| TASK (Business) | 3600s (1 hour) | Stable hierarchy entities change infrequently |
| TASK (Contact/Unit) | 900s (15 min) | Moderate change frequency |
| TASK (Offer) | 180s (3 min) | High churn in sales pipeline |
| TASK (Process) | 60s (1 min) | Very frequent state transitions |
| STORIES | 600s (10 min) | Comments less dynamic than tasks |
| DATAFRAME | 300s (5 min) | Matches task TTL for consistency |
| DETECTION | 300s (5 min) | Subtask structure stable between mutations |
| PROJECT_SECTIONS | 1800s (30 min) | Section structure changes rarely |
| GID_ENUMERATION | 300s (5 min) | Task-section membership more dynamic |

#### Entity-Type TTL Resolution

Entity type detection drives TTL selection:

```python
def _resolve_entity_ttl(task: Task, config: CacheConfig) -> int:
    """Resolve TTL based on entity type."""
    # Explicit override from config
    if task.entity_type in config.ttl.entity_type_ttls:
        return config.ttl.entity_type_ttls[task.entity_type]

    # Entity-type defaults
    if task.entity_type == "business":
        return 3600  # 1 hour
    elif task.entity_type in ("contact", "unit"):
        return 900   # 15 min
    elif task.entity_type == "offer":
        return 180   # 3 min
    elif task.entity_type == "process":
        return 60    # 1 min

    # Global default
    return config.ttl.default_ttl  # 300s
```

---

## Staleness Detection Algorithms

### Version-Based Validation (STRICT Mode)

Compare cached `version` against API `modified_at`:

```python
# Cache entry
entry = cache.get("task_gid", EntryType.TASK)
# entry.version = datetime(2025, 12, 23, 10, 0, 0, tzinfo=UTC)

# API response
fresh_task = await client.tasks.get_async("task_gid", raw=True)
# fresh_task["modified_at"] = "2025-12-23T11:30:00.000Z"

# Comparison
cached_version = entry.version
api_version = datetime.fromisoformat(fresh_task["modified_at"])

if api_version > cached_version:
    # Stale: Return fresh data, update cache
    pass
else:
    # Fresh: Return cached data, no API call
    pass
```

### Lightweight Batch Staleness Check

Instead of full payload fetches, check `modified_at` via batch API:

#### Algorithm

1. **Coalescing Window**: Collect expired entries within 50ms window
2. **Batch API Call**: Single request with `opt_fields=modified_at` only
3. **Version Comparison**: Compare each result against cached version
4. **Selective Fetch**: Full payload only for changed entities
5. **TTL Extension**: Double TTL for unchanged entities

#### Request Coalescing

```python
# Time 0ms: Task A expires, queued
# Time 20ms: Task B expires, queued
# Time 45ms: Task C expires, queued
# Time 50ms: Window closes, batch submitted

# Single batch API call
POST /batch
{
  "data": {
    "actions": [
      {"method": "GET", "relative_path": "/tasks/A", "options": {"opt_fields": "modified_at"}},
      {"method": "GET", "relative_path": "/tasks/B", "options": {"opt_fields": "modified_at"}},
      {"method": "GET", "relative_path": "/tasks/C", "options": {"opt_fields": "modified_at"}}
    ]
  }
}

# Response: ~100 bytes per task (vs ~5KB full payload)
```

#### Batch API Constraints

- **Max 10 actions per request**: Batches >10 automatically chunked
- **Counts as 1 API request** for rate limiting
- **Concurrent caller deduplication**: Same GID requested by multiple callers returns single result

### Progressive TTL Extension

Stable entities exponentially extend their TTL:

#### Extension Algorithm

```python
def extend_ttl(entry: CacheEntry, max_ttl: int = 86400) -> CacheEntry:
    """Double TTL on each successful staleness check."""

    current_ttl = entry.ttl
    extension_count = entry.metadata.get("extension_count", 0)

    # Double the TTL
    new_ttl = min(current_ttl * 2, max_ttl)

    # Create new entry (immutable design)
    return CacheEntry(
        data=entry.data,
        entry_type=entry.entry_type,
        version=entry.version,  # Unchanged
        cached_at=datetime.utcnow(),  # Reset expiration window
        ttl=new_ttl,
        metadata={
            **entry.metadata,
            "extension_count": extension_count + 1,
        },
    )
```

#### Progression Table

| Extension | TTL | Cumulative Time | API Calls (vs Fixed) |
|-----------|-----|-----------------|----------------------|
| 0 (base) | 300s (5 min) | 0 | 24 (2h period) |
| 1 | 600s (10 min) | 5 min | 12 |
| 2 | 1200s (20 min) | 15 min | 6 |
| 3 | 2400s (40 min) | 35 min | 3 |
| 4 | 4800s (80 min) | 1h 15min | 2 |
| 5 | 9600s (160 min) | 2h 35min | 1 |
| 6+ | 86400s (24h) | Ceiling reached | Minimal |

**API Call Reduction**: 79% for 2-hour stable entity (5 calls vs 24 with fixed TTL)

#### TTL Reset on Change

Detected changes reset TTL to base value:

```python
# Extension count 4, TTL = 4800s
entry = cache.get("task_gid", EntryType.TASK)

# Lightweight check detects change
if api_modified_at > entry.version:
    # Full fetch, reset to base
    new_entry = CacheEntry(
        ...,
        ttl=300,  # Back to base
        metadata={"extension_count": 0},  # Reset counter
    )
```

---

## Freshness Modes

### EVENTUAL (Default)

Trust TTL without version validation:

```python
entry = cache.get("task_gid", EntryType.TASK)

if entry and not entry.is_expired():
    # Return immediately, no API call
    return entry.data
else:
    # Fetch from API, update cache
    pass
```

**Guarantees**: Data at most TTL seconds stale
**Performance**: <5ms cache hits
**Use Cases**: Dashboards, reporting, batch processing

### STRICT

Validate version before returning cached data:

```python
entry = cache.get("task_gid", EntryType.TASK)

if entry:
    # Lightweight check: Compare versions
    api_modified_at = await check_version_async(task_gid)

    if api_modified_at == entry.version:
        # Version matches, extend TTL, return cached
        cache.set(task_gid, extend_ttl(entry))
        return entry.data
    else:
        # Version mismatch, full fetch
        fresh_data = await client.tasks.get_async(task_gid)
        cache.set(task_gid, make_entry(fresh_data, ttl=300))
        return fresh_data
else:
    # Cache miss, full fetch
    pass
```

**Guarantees**: Always current data (assuming `modified_at` is reliable)
**Performance**: <100ms for lightweight check, ~200ms for changed entity
**Use Cases**: Critical operations, audit trails, real-time views

---

## Incremental Fetching (Stories)

Stories use a different staleness strategy due to append-only semantics:

### Last Fetched Watermark

```python
# First fetch
stories = await client.stories.list_for_task_cached_async("task_gid")
# Cache entry:
# {
#   "data": [...],
#   "metadata": {"last_fetched": "2025-12-23T10:00:00.000Z"}
# }

# Second fetch (incremental)
stories = await client.stories.list_for_task_cached_async("task_gid")
# API call: GET /tasks/{task_gid}/stories?since=2025-12-23T10:00:00.000Z
# Returns only new stories since last fetch
# Merges with cached stories, updates last_fetched
```

### Story Merging

```python
def _merge_stories(
    cached: list[dict],
    new: list[dict],
) -> list[dict]:
    """Merge cached and new stories, deduplicate by GID."""

    # Create GID->story map (new stories take precedence)
    by_gid = {s["gid"]: s for s in cached}
    by_gid.update({s["gid"]: s for s in new})

    # Sort by created_at (oldest first)
    return sorted(by_gid.values(), key=lambda s: s["created_at"])
```

---

## Invalidation Failure Handling

Cache invalidation failures must not break commits:

```python
async def commit_async(self):
    """Commit mutations, invalidate cache."""

    # Perform CRUD operations
    result = await self._execute_crud_async()

    # Invalidate cache (best-effort)
    try:
        self._invalidate_cache_for_results(result)
    except Exception as e:
        # Log warning, do not raise
        logger.warning(f"Cache invalidation failed: {e}")

    return result  # Commit succeeds regardless
```

**Consequences of Failure**:
- Stale entries may persist until TTL expiration
- Next mutation invalidates correctly
- Eventual consistency maintained via TTL

---

## Batch Modification Checking (Legacy Pattern)

The legacy autom8 system used batch staleness checks with 25-second in-memory TTL. This pattern is preserved for compatibility:

### In-Memory Check Cache

```python
# Process-local cache of batch check results
check_cache: dict[str, tuple[datetime, set[str]]] = {}
# key: batch_key (hash of GID set)
# value: (check_time, stale_gids)

def check_batch_staleness(gids: list[str]) -> set[str]:
    """Check batch for staleness with 25s TTL."""

    batch_key = hash(frozenset(gids))

    # Check in-memory cache
    if batch_key in check_cache:
        check_time, stale_gids = check_cache[batch_key]
        if (datetime.utcnow() - check_time).total_seconds() < 25:
            return stale_gids  # Return cached result

    # Batch API call for fresh check
    stale_gids = _batch_modified_at_check(gids)

    # Update in-memory cache
    check_cache[batch_key] = (datetime.utcnow(), stale_gids)

    return stale_gids
```

**Use Case**: Dataframe extraction with partial cache hits
**Performance**: Avoids redundant batch checks within 25s window

---

## Configuration

### TTL Settings

```python
class TTLSettings:
    """TTL configuration for cache entries."""

    default_ttl: int = 300  # 5 minutes
    entity_type_ttls: dict[str, int] = {
        "business": 3600,
        "contact": 900,
        "unit": 900,
        "offer": 180,
        "process": 60,
    }
    staleness_check_base_ttl: int = 300
    staleness_check_max_ttl: int = 86400  # 24 hours
```

### Staleness Check Configuration

```python
class CacheConfig:
    """Cache configuration."""

    enable_staleness_checks: bool = True
    staleness_check_coalesce_window_ms: int = 50
    staleness_check_batch_size: int = 100
```

---

## Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Lightweight check latency | <100ms | ~80ms |
| Batch efficiency (entries/API call) | >10 | ~15 |
| API call reduction (2h stable entity) | >75% | 79% |
| TTL progression to 24h | <12 hours | ~10.5 hours |
| Changed entity detection accuracy | 100% | 100% |

---

## Observability

### Staleness Check Logging

```python
{
    "event": "staleness_check_result",
    "task_gid": "1234567890",
    "result": "unchanged",  # unchanged | changed | error | deleted
    "previous_ttl": 600,
    "new_ttl": 1200,
    "extension_count": 2,
}

{
    "event": "batch_staleness_check",
    "batch_size": 50,
    "chunk_count": 5,
    "unchanged_count": 45,
    "changed_count": 5,
    "api_calls_saved": 45,
}
```

---

## Related Documents

- [REF-cache-architecture.md](REF-cache-architecture.md) - Overall cache architecture
- [REF-cache-patterns.md](REF-cache-patterns.md) - Usage patterns and optimization
- [ADR-0019](../decisions/ADR-0019-staleness-detection-algorithm.md) - Staleness detection algorithm
- [ADR-0133](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive TTL design
- [ADR-0134](../decisions/ADR-0134-staleness-check-integration-pattern.md) - Integration pattern

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Tech Writer | Initial consolidation from PRD-CACHE-LIGHTWEIGHT-STALENESS, TDD-CACHE-LIGHTWEIGHT-STALENESS |
