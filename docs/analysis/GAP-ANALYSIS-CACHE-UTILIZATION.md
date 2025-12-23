# Gap Analysis: Cache Utilization Extension

**Author**: @requirements-analyst
**Date**: 2025-12-23
**Initiative**: Cache Utilization - Extend cache to all SDK clients
**Status**: Discovery Complete

---

## 1. Executive Summary

The autom8_asana SDK has a mature caching infrastructure with versioned entries, TTL management, metrics, and batch operations, but only TasksClient utilizes it. This analysis documents the exact integration pattern established in TasksClient, identifies integration points for ProjectsClient, SectionsClient, UsersClient, and CustomFieldsClient, and resolves key design questions for extending cache coverage across all SDK clients.

**Key Finding**: BaseClient already provides all necessary cache helpers (`_cache_get()`, `_cache_set()`, `_cache_invalidate()`). Extending cache to other clients requires only: (1) adding new EntryType values, (2) following the established pattern in each client's `get_async()` method, and (3) determining appropriate versioning fields and TTLs per entity type.

---

## 2. Current State Matrix

| Client | Has Cache | EntryType | TTL (seconds) | Versioning Field |
|--------|-----------|-----------|---------------|------------------|
| TasksClient | Yes | `TASK` | Entity-type TTL (60-3600) | `modified_at` |
| ProjectsClient | No | N/A | N/A | `modified_at` (available) |
| SectionsClient | No | N/A | N/A | `created_at` only |
| UsersClient | No | N/A | N/A | None |
| CustomFieldsClient | No | N/A | N/A | `created_at` only |

### EntryType Enum (Current)

Location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py`

```python
class EntryType(str, Enum):
    TASK = "task"
    SUBTASKS = "subtasks"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    DATAFRAME = "dataframe"
```

**Observation**: Entry types for PROJECT, SECTION, USER, and CUSTOM_FIELD are missing.

---

## 3. TasksClient Cache Pattern Documentation

Location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`, lines 87-140

### Step-by-Step Pattern

```python
@error_handler
async def get_async(self, task_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Task | dict[str, Any]:
    """Get a task by GID with cache support."""
    from autom8_asana.cache.entry import EntryType
    from autom8_asana.persistence.validation import validate_gid

    # Step 1: Validate input
    validate_gid(task_gid, "task_gid")

    # Step 2: Check cache first (FR-CLIENT-001)
    cached_entry = self._cache_get(task_gid, EntryType.TASK)
    if cached_entry is not None:
        # Cache hit - return cached data
        data = cached_entry.data
        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client
        return task

    # Step 3: Cache miss - fetch from API
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/tasks/{task_gid}", params=params)

    # Step 4: Store in cache with entity-type TTL
    ttl = self._resolve_entity_ttl(data)
    self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)

    # Step 5: Return model or raw dict
    if raw:
        return data
    task = Task.model_validate(data)
    task._client = self._client
    return task
```

### Key Components

1. **GID Validation**: `validate_gid()` ensures valid Asana GID format
2. **Cache Check**: `_cache_get(key, entry_type)` returns `CacheEntry | None`
3. **TTL Resolution**: `_resolve_entity_ttl(data)` uses entity detection for Business/Contact/Unit/Offer/Process types
4. **Cache Set**: `_cache_set(key, data, entry_type, ttl)` stores with versioning via `modified_at`
5. **Model Binding**: `task._client = self._client` enables SaveSession operations

### TTL Resolution (Entity-Type Specific)

Location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`, lines 142-189

```python
def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
    """Resolve TTL based on entity type detection."""
    entity_type = self._detect_entity_type(data)

    # Priority 1: Use CacheConfig.get_entity_ttl() if available
    if hasattr(self._config, "cache") and self._config.cache is not None:
        if entity_type:
            return self._config.cache.get_entity_ttl(entity_type)
        return self._config.cache.ttl.default_ttl

    # Priority 2: Hardcoded fallback
    entity_ttls = {
        "business": 3600,  # 1 hour
        "contact": 900,    # 15 minutes
        "unit": 900,       # 15 minutes
        "offer": 180,      # 3 minutes
        "process": 60,     # 1 minute
        "address": 3600,   # 1 hour
        "hours": 3600,     # 1 hour
    }
    return entity_ttls.get(entity_type.lower(), 300) if entity_type else 300
```

**Note**: This entity-type TTL resolution is Task-specific (Business entities). For Projects/Sections/Users/CustomFields, simpler fixed TTLs are appropriate.

---

## 4. Per-Client Analysis

### 4.1 ProjectsClient (P0 - High Value)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py`

#### Integration Point

**Method**: `get_async()` (lines 49-71)
**Current Implementation**:
```python
@error_handler
async def get_async(self, project_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Project | dict[str, Any]:
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/projects/{project_gid}", params=params)
    if raw:
        return data
    return Project.model_validate(data)
```

#### Versioning Field

**Field**: `modified_at` (available in Project model, line 63)
**Type**: `str | None` (ISO 8601 format)
**Status**: Fully compatible with existing versioning infrastructure

#### Recommended TTL

**Value**: 900 seconds (15 minutes)
**Rationale**: Projects change infrequently (name, settings) but not as rarely as workspace-level entities. 15 minutes balances freshness with cache efficiency. Metadata like `modified_at` changes on any task update in the project, but the Project entity fields themselves change rarely.

#### Complexity Estimate

**Effort**: Low (2-3 hours)
**Changes Required**:
1. Add `PROJECT = "project"` to EntryType enum
2. Add cache check/set pattern to `get_async()`
3. Add GID validation (copy from TasksClient)
4. No TTL detection needed - use fixed TTL

#### Recommended Implementation

```python
@error_handler
async def get_async(self, project_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Project | dict[str, Any]:
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

    # Store in cache (900s = 15 min TTL)
    self._cache_set(project_gid, data, EntryType.PROJECT, ttl=900)

    if raw:
        return data
    return Project.model_validate(data)
```

---

### 4.2 SectionsClient (P0 - High Value)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`

#### Integration Point

**Method**: `get()` via @async_method (lines 66-89)
**Current Implementation**:
```python
@async_method
@error_handler
async def get(self, section_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Section | dict[str, Any]:
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/sections/{section_gid}", params=params)
    if raw:
        return data
    return Section.model_validate(data)
```

#### Versioning Field

**Challenge**: Section model only has `created_at` (line 47), no `modified_at`

**Options**:
1. **Use `created_at`**: Sections rarely change, so `created_at` is sufficient for versioning
2. **Use current timestamp**: Fall back to cache insertion time for versioning
3. **Request `modified_at` in opt_fields**: Asana API may return it even if not modeled

**Recommendation**: Use current timestamp (Option 2). Sections are effectively immutable after creation (only name can change). The TTL-based expiration is sufficient without version-based staleness detection.

#### Recommended TTL

**Value**: 1800 seconds (30 minutes)
**Rationale**: Sections rarely change (only name updates). They're created once and used as organizational containers. 30-minute cache provides excellent hit rates.

#### Complexity Estimate

**Effort**: Low (2-3 hours)
**Changes Required**:
1. Add `SECTION = "section"` to EntryType enum
2. Add cache check/set pattern to `get()` method
3. Add GID validation
4. Handle lack of `modified_at` in `_cache_set()` (BaseClient falls back to `datetime.now()`)

---

### 4.3 UsersClient (P1 - Medium Value)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py`

#### Integration Point

**Method**: `get_async()` (lines 45-67)
**Current Implementation**:
```python
async def get_async(self, user_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> User | dict[str, Any]:
    self._log_operation("get_async", user_gid)
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/users/{user_gid}", params=params)
    if raw:
        return data
    return User.model_validate(data)
```

#### Versioning Field

**Challenge**: User model has no timestamp fields at all
**Observation**: Users are extremely stable - name, email, photo rarely change

**Recommendation**: Use current timestamp for versioning. User data is highly stable and TTL-based expiration is the primary invalidation mechanism.

#### Recommended TTL

**Value**: 3600 seconds (1 hour)
**Rationale**: User profiles (name, email, photo) change extremely rarely. 1-hour cache provides excellent efficiency with negligible staleness risk. Consider longer TTL (4 hours) for production if user lookup is a hot path.

#### Additional Consideration: `me_async()`

The `me_async()` method (lines 143-165) returns the current authenticated user. This could also benefit from caching with a special key like `"me"` or `"current_user"`.

**Recommendation**: Cache `me_async()` result with key derived from the returned GID, not the special identifier "me", to avoid cache key collision issues.

#### Complexity Estimate

**Effort**: Low (2-3 hours)
**Changes Required**:
1. Add `USER = "user"` to EntryType enum
2. Add cache check/set pattern to `get_async()`
3. Add GID validation
4. Optionally cache `me_async()` result

---

### 4.4 CustomFieldsClient (P1 - Medium Value)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/custom_fields.py`

#### Integration Point

**Method**: `get_async()` (lines 52-74)
**Current Implementation**:
```python
@error_handler
async def get_async(self, custom_field_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> CustomField | dict[str, Any]:
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/custom_fields/{custom_field_gid}", params=params)
    if raw:
        return data
    return CustomField.model_validate(data)
```

#### Versioning Field

**Field**: `created_at` only (line 111)
**Challenge**: No `modified_at` in CustomField model

**Recommendation**: Use current timestamp for versioning. Custom field definitions are workspace-level configurations that change rarely.

#### Caching Scope

**Question**: Should custom fields be cached globally or workspace-scoped?

**Analysis**:
- Custom fields are workspace-scoped in Asana
- The same GID always refers to the same custom field
- Cache key should be the GID alone (not workspace-prefixed)

**Recommendation**: Cache by GID alone. Custom field GIDs are globally unique within an Asana instance.

#### Recommended TTL

**Value**: 1800 seconds (30 minutes)
**Rationale**: Custom field definitions (name, type, enum options) change infrequently. Schema changes require intentional admin action. 30-minute cache is conservative; production could use 1 hour.

#### Complexity Estimate

**Effort**: Low-Medium (3-4 hours)
**Changes Required**:
1. Add `CUSTOM_FIELD = "custom_field"` to EntryType enum
2. Add cache check/set pattern to `get_async()`
3. Add GID validation
4. Consider caching `list_for_workspace_async()` results (batch population opportunity)

---

## 5. EntryType Extensions Required

### New Entry Types

Add to `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py`:

```python
class EntryType(str, Enum):
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

### Justification

| EntryType | Justification |
|-----------|---------------|
| `PROJECT` | Enables caching of project metadata lookups |
| `SECTION` | Enables caching of section lookups (used heavily in DataFrame operations) |
| `USER` | Enables caching of user profile lookups (assignee resolution, etc.) |
| `CUSTOM_FIELD` | Enables caching of custom field definitions (schema lookups) |

---

## 6. Batch Population Opportunities

### Current Infrastructure

Location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py`

```python
def set_batch(self, entries: dict[str, CacheEntry]) -> None:
    """Store multiple entries in single operation."""
    ...
```

Both `NullCacheProvider` and `InMemoryCacheProvider` implement `set_batch()`.

### Opportunities by Client

#### ProjectsClient.list_async()

**Location**: Lines 433-481
**Opportunity**: When `list_async()` fetches projects, populate cache with each project:

```python
async def fetch_page(offset: str | None) -> tuple[list[Project], str | None]:
    params = self._build_opt_fields(opt_fields)
    # ... existing params setup ...
    data, next_offset = await self._http.get_paginated("/projects", params=params)

    # Batch populate cache
    if self._cache:
        entries = {}
        for p in data:
            entry = CacheEntry(
                key=p["gid"],
                data=p,
                entry_type=EntryType.PROJECT,
                version=datetime.now(timezone.utc),
                ttl=900,
            )
            entries[p["gid"]] = entry
        self._cache.set_batch(entries)

    projects = [Project.model_validate(p) for p in data]
    return projects, next_offset
```

#### SectionsClient.list_for_project_async()

**Location**: Lines 244-282
**Opportunity**: Cache sections when listing for a project (common pattern in DataFrame operations)

#### UsersClient.list_for_workspace_async()

**Location**: Lines 216-254
**Opportunity**: Pre-populate user cache when listing workspace users

#### CustomFieldsClient.list_for_workspace_async()

**Location**: Lines 470-510
**Opportunity**: Cache custom field definitions when listing workspace fields

### Implementation Priority

1. **P0**: `SectionsClient.list_for_project_async()` - Direct benefit for parallel fetch operations
2. **P1**: `ProjectsClient.list_async()` - Moderate benefit for workspace-wide operations
3. **P2**: `UsersClient.list_for_workspace_async()` - Lower priority, but good for assignee resolution
4. **P2**: `CustomFieldsClient.list_for_workspace_async()` - Useful for schema warming

---

## 7. Metrics Exposure Options

### Current Infrastructure

Location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/metrics.py`

```python
class CacheMetrics:
    """Thread-safe cache metrics aggregator."""

    @property
    def hits(self) -> int: ...
    @property
    def misses(self) -> int: ...
    @property
    def hit_rate(self) -> float: ...
    @property
    def api_calls_saved(self) -> int: ...

    def on_event(self, callback: Callable[[CacheEvent], None]) -> None:
        """Register callback for cache events."""
        ...

    def snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current metrics."""
        ...
```

### Exposure Options

#### Option 1: AsanaClient Property (Recommended)

```python
class AsanaClient:
    @property
    def cache_metrics(self) -> CacheMetrics | None:
        """Access cache metrics for observability."""
        if self._cache_provider:
            return self._cache_provider.get_metrics()
        return None
```

**Advantages**:
- Simple, discoverable API
- Consistent with existing SDK patterns
- No new dependencies

#### Option 2: Callback Integration

```python
# User code
client = AsanaClient(...)
client.cache_metrics.on_event(lambda e: cloudwatch.put_metric(e.event_type, 1))
```

**Advantages**:
- Real-time event streaming
- Integration with external monitoring (CloudWatch, DataDog)

#### Option 3: Observability Provider Integration

Wire `CacheMetrics` events to existing `LogProvider`:

```python
def _setup_cache_metrics(self) -> None:
    if self._cache_provider and self._log_provider:
        metrics = self._cache_provider.get_metrics()
        metrics.on_event(lambda e: self._log_provider.info(
            f"Cache {e.event_type}: {e.key} ({e.latency_ms:.2f}ms)"
        ))
```

### Recommendation

Implement Option 1 (property access) first, with Option 2 (callbacks) available for advanced users. Option 3 can be added later for automatic structured logging.

---

## 8. Warming Implementation Notes

### Current State

Location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/cache.py`

```python
def warm(self, gids: list[str], entry_types: list[EntryType] | None = None) -> WarmResult:
    """Pre-populate cache (not implemented)."""
    from autom8_asana.protocols.cache import WarmResult
    return WarmResult(warmed=0, failed=0, skipped=len(gids))
```

Both `NullCacheProvider` and `InMemoryCacheProvider` have stub implementations that skip all GIDs.

### Implementation Requirements

For `warm()` to be functional:

1. **Access to HTTP client**: Warming needs to fetch data from Asana API
2. **Entry type resolution**: Different entry types require different API endpoints
3. **Batch efficiency**: Use pagination and concurrent requests for large GID lists

### Proposed Implementation Pattern

```python
async def warm_async(
    self,
    client: AsanaClient,
    gids: list[str],
    entry_types: list[EntryType] | None = None,
) -> WarmResult:
    """Pre-populate cache for specified GIDs."""
    entry_types = entry_types or [EntryType.TASK]
    warmed, failed, skipped = 0, 0, 0

    for gid in gids:
        for entry_type in entry_types:
            # Check if already cached
            if self.get_versioned(gid, entry_type):
                skipped += 1
                continue

            try:
                # Fetch based on entry type
                if entry_type == EntryType.TASK:
                    await client.tasks.get_async(gid)  # Auto-caches
                elif entry_type == EntryType.PROJECT:
                    await client.projects.get_async(gid)
                # ... etc
                warmed += 1
            except Exception:
                failed += 1

    return WarmResult(warmed=warmed, failed=failed, skipped=skipped)
```

### Warming Use Cases

1. **DataFrame operations**: Pre-warm task cache before large extractions
2. **Batch operations**: Pre-warm before SaveSession with many tasks
3. **Session startup**: Pre-warm frequently accessed projects/sections

---

## 9. Risk Assessment

### Risk 1: Cache Key Collision

**Risk**: Different entity types sharing GID namespace could collide
**Likelihood**: Very Low - EntryType is part of internal key (`{gid}:{entry_type}`)
**Mitigation**: Already handled by InMemoryCacheProvider's internal key format

### Risk 2: Stale Data on Concurrent Modifications

**Risk**: Cached entity returned while another client modifies it
**Likelihood**: Medium - Expected in distributed systems
**Mitigation**:
- TTL-based expiration limits staleness window
- Users can call with `use_cache=False` for critical reads
- Consider adding `invalidate_on_write` pattern for update operations

### Risk 3: Memory Pressure from Additional Cache Entries

**Risk**: Caching Projects/Sections/Users/CustomFields increases memory usage
**Likelihood**: Low - These entities are smaller than Task entities
**Mitigation**:
- InMemoryCacheProvider has max_size eviction (default 10,000)
- Additional entry types share the same size limit
- Monitor with CacheMetrics

### Risk 4: Section Versioning Without modified_at

**Risk**: Sections cached without proper version tracking
**Likelihood**: Low - Sections rarely change
**Mitigation**:
- Use TTL-based expiration as primary invalidation
- Accept that section cache may be slightly stale (30-minute window)
- Document behavior in PRD

### Risk 5: Custom Field Schema Changes

**Risk**: Custom field definition changes (enum options added) cached with stale data
**Likelihood**: Low - Schema changes are admin actions
**Mitigation**:
- 30-minute TTL limits impact window
- Provide manual invalidation API: `client.cache.invalidate(gid, [EntryType.CUSTOM_FIELD])`
- Document that schema changes may take up to TTL to propagate

---

## 10. Open Questions Resolution

### Q1: Section Versioning Without modified_at

**Resolution**: Use current timestamp for versioning. TTL-based expiration (30 minutes) is the primary invalidation mechanism. Sections are effectively immutable containers; name changes are rare.

**Architect Input Needed**: None - decision is within requirements scope.

### Q2: User TTL Duration

**Resolution**: 1 hour (3600 seconds) is appropriate. Users (name, email, photo) change extremely rarely. Consider making this configurable via CacheConfig for production optimization.

**Architect Input Needed**: None - can be adjusted without architectural changes.

### Q3: CustomField Caching Scope

**Resolution**: Cache by GID alone, not workspace-prefixed. Custom field GIDs are globally unique within an Asana instance. Workspace scoping is not necessary.

**Architect Input Needed**: None - straightforward design decision.

### Q4: Cache Key Prefix Strategy

**Resolution**: Existing pattern of `{gid}:{entry_type}` in InMemoryCacheProvider is sufficient. No prefix needed as GIDs are unique and entry_type provides namespace separation.

**Architect Input Needed**: None - existing pattern works.

### Q5: Batch Population Priority

**Resolution**:
- P0: `SectionsClient.list_for_project_async()` - Direct benefit for parallel fetch
- P1: Other list methods

**Architect Input Needed**: Confirm this aligns with performance optimization goals for DataFrame extraction.

---

## 11. Summary Recommendations

### Phase 1 (P0 - Immediate)

1. **Add EntryType values**: PROJECT, SECTION
2. **Implement ProjectsClient caching**: `get_async()` with 900s TTL
3. **Implement SectionsClient caching**: `get()` with 1800s TTL
4. **Add batch population**: `SectionsClient.list_for_project_async()`

### Phase 2 (P1 - Near-term)

1. **Add EntryType values**: USER, CUSTOM_FIELD
2. **Implement UsersClient caching**: `get_async()` with 3600s TTL
3. **Implement CustomFieldsClient caching**: `get_async()` with 1800s TTL
4. **Expose CacheMetrics**: Add `AsanaClient.cache_metrics` property

### Phase 3 (P2 - Future)

1. **Add batch population**: Remaining list methods
2. **Implement warm()**: Functional cache warming with API calls
3. **Add invalidation hooks**: Invalidate cache on update/delete operations

### Estimated Total Effort

- **Phase 1**: 1-2 days
- **Phase 2**: 1-2 days
- **Phase 3**: 2-3 days

---

## 12. Files to Modify

### Core Changes

| File | Change |
|------|--------|
| `src/autom8_asana/cache/entry.py` | Add PROJECT, SECTION, USER, CUSTOM_FIELD to EntryType |
| `src/autom8_asana/clients/projects.py` | Add cache pattern to `get_async()` |
| `src/autom8_asana/clients/sections.py` | Add cache pattern to `get()` |
| `src/autom8_asana/clients/users.py` | Add cache pattern to `get_async()` |
| `src/autom8_asana/clients/custom_fields.py` | Add cache pattern to `get_async()` |

### Optional Enhancements

| File | Change |
|------|--------|
| `src/autom8_asana/client.py` | Add `cache_metrics` property |
| `src/autom8_asana/config.py` | Add per-entity-type TTL config for non-Task entities |
| `src/autom8_asana/_defaults/cache.py` | Implement functional `warm()` |

---

## 13. Handoff to Architect

This discovery document provides sufficient detail for the Architect to:

1. Design the implementation approach for cache extension
2. Define integration patterns in TDD
3. Make any necessary ADR decisions for edge cases

**Blocking Questions Resolved**: All key design questions have recommendations that can proceed without further discovery.

**Scope Confirmed**: Per ADR-0118, this analysis excludes multi-level cache hierarchy and aggregate caching patterns.
