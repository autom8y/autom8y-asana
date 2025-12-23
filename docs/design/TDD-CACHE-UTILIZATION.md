# TDD: Cache Utilization - Extend Cache to All SDK Clients

## Metadata

- **TDD ID**: TDD-CACHE-UTILIZATION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: PROMPT-0-CACHE-UTILIZATION
- **Related TDDs**: TDD-CACHE-INTEGRATION, TDD-WATERMARK-CACHE
- **Related ADRs**: ADR-0118 (Rejection of Multi-Level Cache), ADR-0119 (Client Cache Integration Pattern), ADR-0120 (Batch Cache Population on Bulk Fetch)

---

## Overview

This TDD specifies the extension of cache support to ProjectsClient, SectionsClient, UsersClient, and CustomFieldsClient. The design leverages the existing TasksClient cache pattern established in TDD-CACHE-INTEGRATION, requiring only EntryType enum extension, per-client cache integration, batch population on bulk fetch operations, and metrics exposure through AsanaClient.

---

## Requirements Summary

**From PROMPT-0-CACHE-UTILIZATION**:

| Requirement | Priority | Status |
|-------------|----------|--------|
| Add cache integration to ProjectsClient.get_async() | P0 | Specified |
| Add cache integration to SectionsClient.get_async() | P0 | Specified |
| Wire bulk fetch paths to set_batch() for cache population | P0 | Specified |
| Expose CacheMetrics to SDK observability layer | P1 | Specified |
| Add cache integration to UsersClient.get_async() | P1 | Specified |
| Add cache integration to CustomFieldsClient.get_async() | P1 | Specified |
| Implement warm() for cache pre-population | P2 | Deferred |
| Cache detection results (detect_entity_type) | P1 | Out of scope (Task-specific) |

**From Discovery (GAP-ANALYSIS-CACHE-UTILIZATION.md)**:
- Section versioning: Use current timestamp (no `modified_at` available)
- User TTL: 3600 seconds (1 hour)
- CustomField caching: GID alone, not workspace-prefixed
- Batch population priority: P0 for `SectionsClient.list_for_project_async()`

---

## System Context

```
                    +------------------+
                    |   AsanaClient    |
                    |  cache_metrics   |  <-- New property
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |                    |                    |
+-------v--------+  +--------v--------+  +--------v--------+
| ProjectsClient |  | SectionsClient  |  |  TasksClient    |
|   get_async()  |  |   get_async()   |  |   get_async()   | <-- Existing
|  list_async()  |  | list_for_proj() |  |                 |
+-------+--------+  +--------+--------+  +--------+--------+
        |                    |                    |
        +--------------------+--------------------+
                             |
                    +--------v--------+
                    |   BaseClient    |
                    | _cache_get()    | <-- Existing helpers
                    | _cache_set()    |
                    | _cache_inv()    |
                    +--------+--------+
                             |
                    +--------v--------+
                    |  CacheProvider  |
                    | InMemory/Redis  |
                    +--------+--------+
                             |
                    +--------v--------+
                    |  CacheMetrics   |
                    | hits/misses     |
                    | on_event()      |
                    +-----------------+
```

The cache integration uses the existing BaseClient helpers (`_cache_get()`, `_cache_set()`, `_cache_invalidate()`) which are already implemented. Each client needs only to follow the established pattern from TasksClient.

---

## Design

### 1. EntryType Enum Extension

**File**: `src/autom8_asana/cache/entry.py`

Add four new entry types to support the additional clients:

```python
class EntryType(str, Enum):
    """Types of cache entries with distinct versioning strategies."""

    # Existing
    TASK = "task"
    SUBTASKS = "subtasks"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    DATAFRAME = "dataframe"

    # New - P0
    PROJECT = "project"
    SECTION = "section"

    # New - P1
    USER = "user"
    CUSTOM_FIELD = "custom_field"
```

**TTL Recommendations**:

| EntryType | Default TTL | Rationale |
|-----------|-------------|-----------|
| PROJECT | 900s (15 min) | Projects have `modified_at`; metadata changes infrequently |
| SECTION | 1800s (30 min) | No `modified_at`; sections rarely change after creation |
| USER | 3600s (1 hour) | No timestamps; user profiles extremely stable |
| CUSTOM_FIELD | 1800s (30 min) | Schema definitions change rarely |

### 2. Client Cache Integration Pattern

**Reference**: ADR-0119 documents the replicable pattern.

Each client follows the same structure for `get_async()`:

```python
@error_handler
async def get_async(
    self,
    {entity}_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> {Model} | dict[str, Any]:
    """Get a {entity} by GID with cache support."""
    from autom8_asana.cache.entry import EntryType
    from autom8_asana.persistence.validation import validate_gid

    # Step 1: Validate GID
    validate_gid({entity}_gid, "{entity}_gid")

    # Step 2: Check cache first
    cached_entry = self._cache_get({entity}_gid, EntryType.{ENTRY_TYPE})
    if cached_entry is not None:
        data = cached_entry.data
        if raw:
            return data
        return {Model}.model_validate(data)

    # Step 3: Cache miss - fetch from API
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/{entities}/{{{entity}_gid}}", params=params)

    # Step 4: Store in cache with fixed TTL
    self._cache_set({entity}_gid, data, EntryType.{ENTRY_TYPE}, ttl={TTL})

    # Step 5: Return model or raw dict
    if raw:
        return data
    return {Model}.model_validate(data)
```

**Key differences from TasksClient**:
- No entity-type TTL resolution (`_resolve_entity_ttl`) - fixed TTL per client
- No `_client` reference binding (only Task models need SaveSession support)
- Versioning derived from `modified_at` when available, else `datetime.now()`

### 3. Component Specifications

#### 3.1 ProjectsClient Cache Integration

**File**: `src/autom8_asana/clients/projects.py`
**Method**: `get_async()` (lines 49-71)

**Changes**:
1. Add GID validation at method entry
2. Add cache check before API call
3. Add cache set after API response
4. Use TTL=900 (15 minutes)
5. Versioning: `modified_at` field available

**Implementation**:

```python
@error_handler
async def get_async(
    self,
    project_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Project | dict[str, Any]:
    """Get a project by GID with cache support."""
    from autom8_asana.cache.entry import EntryType
    from autom8_asana.persistence.validation import validate_gid

    validate_gid(project_gid, "project_gid")

    # Check cache first
    cached_entry = self._cache_get(project_gid, EntryType.PROJECT)
    if cached_entry is not None:
        data = cached_entry.data
        if raw:
            return data
        return Project.model_validate(data)

    # Cache miss - fetch from API
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/projects/{project_gid}", params=params)

    # Store in cache (15 min TTL)
    self._cache_set(project_gid, data, EntryType.PROJECT, ttl=900)

    if raw:
        return data
    return Project.model_validate(data)
```

#### 3.2 SectionsClient Cache Integration

**File**: `src/autom8_asana/clients/sections.py`
**Method**: `get()` via `@async_method` (lines 66-89)

**Changes**:
1. Add GID validation at method entry
2. Add cache check before API call
3. Add cache set after API response
4. Use TTL=1800 (30 minutes)
5. Versioning: `datetime.now()` (no `modified_at` available)

**Implementation**:

```python
@async_method
@error_handler
async def get(
    self,
    section_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Section | dict[str, Any]:
    """Get a section by GID with cache support."""
    from autom8_asana.cache.entry import EntryType
    from autom8_asana.persistence.validation import validate_gid

    validate_gid(section_gid, "section_gid")

    # Check cache first
    cached_entry = self._cache_get(section_gid, EntryType.SECTION)
    if cached_entry is not None:
        data = cached_entry.data
        if raw:
            return data
        return Section.model_validate(data)

    # Cache miss - fetch from API
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/sections/{section_gid}", params=params)

    # Store in cache (30 min TTL)
    self._cache_set(section_gid, data, EntryType.SECTION, ttl=1800)

    if raw:
        return data
    return Section.model_validate(data)
```

#### 3.3 UsersClient Cache Integration

**File**: `src/autom8_asana/clients/users.py`
**Method**: `get_async()` (lines 45-67)

**Changes**:
1. Add GID validation at method entry
2. Add cache check before API call
3. Add cache set after API response
4. Use TTL=3600 (1 hour)
5. Versioning: `datetime.now()` (no timestamps available)

**Note**: The `me_async()` method can optionally cache using the returned user's GID as key, not "me".

#### 3.4 CustomFieldsClient Cache Integration

**File**: `src/autom8_asana/clients/custom_fields.py`
**Method**: `get_async()` (lines 52-74)

**Changes**:
1. Add GID validation at method entry
2. Add cache check before API call
3. Add cache set after API response
4. Use TTL=1800 (30 minutes)
5. Versioning: `datetime.now()` (only `created_at` available)

**Cache Key**: GID alone (not workspace-prefixed). CustomField GIDs are globally unique.

### 4. Batch Cache Population

**Reference**: ADR-0120 documents this pattern.

When `list_for_project_async()` or similar bulk methods fetch multiple entities, populate individual cache entries using `set_batch()`.

#### 4.1 SectionsClient.list_for_project_async() - P0

**File**: `src/autom8_asana/clients/sections.py`
**Method**: `list_for_project_async()` (lines 244-282)

**Pattern**:

```python
def list_for_project_async(
    self,
    project_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Section]:
    """List sections in a project with cache population."""
    from autom8_asana.cache.entry import CacheEntry, EntryType
    from datetime import datetime, timezone

    self._log_operation("list_for_project_async", project_gid)

    async def fetch_page(offset: str | None) -> tuple[list[Section], str | None]:
        params = self._build_opt_fields(opt_fields)
        params["limit"] = min(limit, 100)
        if offset:
            params["offset"] = offset

        data, next_offset = await self._http.get_paginated(
            f"/projects/{project_gid}/sections", params=params
        )

        # Batch populate cache
        if self._cache and data:
            entries = {}
            now = datetime.now(timezone.utc)
            for s in data:
                entry = CacheEntry(
                    key=s["gid"],
                    data=s,
                    entry_type=EntryType.SECTION,
                    version=now,
                    ttl=1800,
                )
                entries[s["gid"]] = entry
            self._cache.set_batch(entries)

        sections = [Section.model_validate(s) for s in data]
        return sections, next_offset

    return PageIterator(fetch_page, page_size=min(limit, 100))
```

#### 4.2 Future Batch Population (P1/P2)

| Method | Client | Priority | Notes |
|--------|--------|----------|-------|
| `list_async()` | ProjectsClient | P1 | Workspace-wide project listing |
| `list_for_workspace_async()` | UsersClient | P2 | User directory warm |
| `list_for_workspace_async()` | CustomFieldsClient | P2 | Schema warming |

### 5. Metrics Exposure

**File**: `src/autom8_asana/client.py`

Add a `cache_metrics` property to expose CacheMetrics from the cache provider:

```python
@property
def cache_metrics(self) -> "CacheMetrics | None":
    """Access cache metrics for observability.

    Per TDD-CACHE-UTILIZATION: Exposes cache hit/miss rates,
    API calls saved, and event callbacks for monitoring integration.

    Returns:
        CacheMetrics instance if caching is enabled, None otherwise.

    Example:
        >>> client = AsanaClient()
        >>> if client.cache_metrics:
        ...     print(f"Hit rate: {client.cache_metrics.hit_rate_percent:.1f}%")
        ...     print(f"API calls saved: {client.cache_metrics.api_calls_saved}")
        ...
        ...     # Register callback for monitoring
        ...     client.cache_metrics.on_event(lambda e: log_event(e))
    """
    if self._cache_provider is None:
        return None
    return self._cache_provider.get_metrics()
```

**Type hint import** (in TYPE_CHECKING block):

```python
if TYPE_CHECKING:
    from autom8_asana.cache.metrics import CacheMetrics
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Section versioning | Timestamp-based | No `modified_at` in Asana API; TTL is primary invalidation | ADR-0119 |
| User TTL | 3600s | User profiles rarely change | GAP-ANALYSIS |
| CustomField key format | GID only | GIDs are globally unique | GAP-ANALYSIS |
| Batch population trigger | During list iteration | Minimal overhead, opportunistic warming | ADR-0120 |
| Metrics exposure | Property accessor | Simple, discoverable, consistent with SDK patterns | - |

---

## Complexity Assessment

**Level**: Module

**Justification**:
- Replicates established pattern (no new architecture)
- Extends existing enum with 4 values
- Adds ~30 lines per client (4 clients = ~120 lines)
- Single new property on AsanaClient
- No new dependencies or infrastructure

**Escalation triggers not present**:
- No new external APIs
- No new configuration schemas
- No new data stores
- No cross-service coordination

---

## Implementation Plan

### Phase 1: Core Infrastructure (P0)

| Deliverable | Files | Estimate |
|-------------|-------|----------|
| EntryType extension | `cache/entry.py` | 15 min |
| ProjectsClient caching | `clients/projects.py` | 30 min |
| SectionsClient caching | `clients/sections.py` | 30 min |
| Section batch population | `clients/sections.py` | 30 min |
| Unit tests | `tests/unit/clients/` | 1 hour |

**Phase 1 Total**: ~3 hours

### Phase 2: Extended Clients & Metrics (P1)

| Deliverable | Files | Estimate |
|-------------|-------|----------|
| UsersClient caching | `clients/users.py` | 30 min |
| CustomFieldsClient caching | `clients/custom_fields.py` | 30 min |
| cache_metrics property | `client.py` | 15 min |
| Unit tests | `tests/unit/` | 1 hour |
| Integration tests | `tests/integration/` | 1 hour |

**Phase 2 Total**: ~3.5 hours

### Phase 3: Future Enhancements (P2)

| Deliverable | Files | Estimate |
|-------------|-------|----------|
| ProjectsClient batch population | `clients/projects.py` | 30 min |
| UsersClient batch population | `clients/users.py` | 30 min |
| CustomFieldsClient batch population | `clients/custom_fields.py` | 30 min |
| warm() implementation | `_defaults/cache.py` | 2 hours |

**Phase 3 Total**: ~3.5 hours (deferred)

---

## Migration Strategy

No migration needed. Changes are additive:
- New EntryType values don't affect existing entries
- Cache integration is invisible to existing API consumers
- Existing `raw=True` behavior unchanged
- No breaking changes to public APIs

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Section staleness (no `modified_at`) | Low | Medium | 30-min TTL limits staleness window; document behavior |
| Memory pressure from additional entries | Low | Low | InMemoryCacheProvider has eviction; entries share limit |
| Cache provider errors | Low | Low | BaseClient helpers already have graceful degradation |
| Batch population overhead | Low | Low | set_batch() is atomic; minimal per-item overhead |

---

## Observability

### Metrics

Via `AsanaClient.cache_metrics`:
- `hits`: Total cache hits
- `misses`: Total cache misses
- `hit_rate`: Ratio (0.0 to 1.0)
- `hit_rate_percent`: Percentage (0.0 to 100.0)
- `api_calls_saved`: Count of avoided API calls
- `average_latency_ms`: Operation latency

### Logging

BaseClient helpers already log at DEBUG level:
- `"Cache hit for {entry_type} (key={key})"`
- `"Cache set for {entry_type} (key={key}, ttl={ttl})"`
- `"Cache invalidated (key={key}, types={types})"`

### Alerting

Not required for cache integration. Cache failures degrade gracefully to API calls.

---

## Testing Strategy

### Unit Tests

**Coverage targets**:
- Each client's `get_async()` cache flow
- Cache hit path (returns cached data)
- Cache miss path (calls API, stores result)
- Batch population on list operations
- Metrics property access

**Test structure**:
```
tests/unit/clients/
    test_projects_cache.py
    test_sections_cache.py
    test_users_cache.py
    test_custom_fields_cache.py
tests/unit/
    test_client_cache_metrics.py
```

### Integration Tests

- End-to-end cache hit/miss with InMemoryCacheProvider
- Verify TTL expiration behavior
- Metrics accumulation across operations

### Performance Tests (Optional)

- Batch population throughput
- Memory footprint with large cache

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should me_async() cache by returned GID? | Engineer | Phase 2 | Yes, cache using returned user GID |
| Should update/delete invalidate cache? | Architect | Phase 1 | Yes, per ADR-0117 (existing) |

---

## Appendix: File Changes Summary

### Modified Files

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `src/autom8_asana/cache/entry.py` | Add EntryType values | +4 |
| `src/autom8_asana/clients/projects.py` | Add cache integration | +20 |
| `src/autom8_asana/clients/sections.py` | Add cache integration + batch | +40 |
| `src/autom8_asana/clients/users.py` | Add cache integration | +20 |
| `src/autom8_asana/clients/custom_fields.py` | Add cache integration | +20 |
| `src/autom8_asana/client.py` | Add cache_metrics property | +15 |

### New Files

| File | Purpose |
|------|---------|
| `tests/unit/clients/test_projects_cache.py` | ProjectsClient cache tests |
| `tests/unit/clients/test_sections_cache.py` | SectionsClient cache tests |
| `tests/unit/clients/test_users_cache.py` | UsersClient cache tests |
| `tests/unit/clients/test_custom_fields_cache.py` | CustomFieldsClient cache tests |
| `tests/unit/test_client_cache_metrics.py` | AsanaClient.cache_metrics tests |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft |
