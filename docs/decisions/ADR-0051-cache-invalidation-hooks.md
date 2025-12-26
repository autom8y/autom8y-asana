# ADR-0051: Cache Invalidation Hooks

## Metadata
- **Status**: Accepted
- **Author**: Tech Writer (consolidation)
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0125, ADR-0137, ADR-0124
- **Related**: reference/CACHE.md, ADR-0046 (Cache Protocol Extension), ADR-0047 (Two-Tier Architecture)

## Context

When entities are modified through `SaveSession.commit_async()` or SDK client methods, cached representations become stale. Without invalidation, subsequent reads return outdated data until TTL expiration—potentially 5 minutes to 24 hours depending on entity type and progressive TTL state.

**Write-Then-Read Pattern Problem**:
1. User modifies task via `SaveSession.commit_async()`
2. User immediately fetches same task via `TasksClient.get_async()`
3. Cache returns stale pre-modification data (cached before write)
4. User sees old data despite successful save

**Multi-Homed Task Complexity**:
Tasks can exist in multiple projects simultaneously. DataFrame cache keys include project context (`{task_gid}:{project_gid}`). Modifying a task must invalidate cache entries for all projects containing that task.

**Commit Flow Context**:
```
SaveSession.commit_async():
    Phase 1: CRUD operations
    Phase 2: Cascade operations
    Phase 3: Healing operations
    Phase 4: Reset entity state
    Phase 5: Automation evaluation
```

## Decision

**Implement post-commit invalidation hooks at two levels: SaveSession for write operations, BaseClient helpers for read-path integration.**

### Part 1: SaveSession Post-Commit Hook

Insert invalidation callback after Phase 1 (CRUD + actions), before Phase 2 (cascade):

```python
async def commit_async(self) -> SaveResult:
    # Phase 1: Execute CRUD and actions
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # Phase 1.5: Cache invalidation (NEW)
    await self._invalidate_cache_for_results(crud_result, action_results)

    # Phase 2-5: Continue existing phases
    ...
```

Invalidation implementation with multi-project awareness:

```python
async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult],
) -> None:
    """Invalidate cache for successfully mutated entities."""
    if not self._client._cache_provider:
        return

    cache = self._client._cache_provider

    # Collect all GIDs to invalidate (O(n) collection)
    gids_to_invalidate: set[str] = set()

    # From CRUD operations
    for entity in crud_result.succeeded:
        if hasattr(entity, 'gid') and entity.gid:
            gids_to_invalidate.add(entity.gid)

    # From action operations (add_tag, move_to_section, etc.)
    for action_result in action_results:
        if action_result.success and action_result.action.task:
            if hasattr(action_result.action.task, 'gid'):
                gids_to_invalidate.add(action_result.action.task.gid)

    # Invalidate TASK and SUBTASKS entry types
    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
        except Exception as exc:
            # Log and continue - invalidation failure is not fatal
            self._log.warning("cache_invalidation_failed", gid=gid, error=str(exc))

    # Invalidate DATAFRAME entries with multi-project awareness
    for gid in gids_to_invalidate:
        try:
            entity = self._tracker.get_entity(gid)
            project_gids = self._get_project_gids_for_entity(entity)
            if project_gids:
                # Invalidate task-project pairs across all projects
                for project_gid in project_gids:
                    cache.invalidate(
                        f"{gid}:{project_gid}",
                        [EntryType.DATAFRAME],
                    )
        except Exception as exc:
            if self._log:
                self._log.warning(
                    "dataframe_cache_invalidation_failed",
                    gid=gid,
                    error=str(exc),
                )

def _get_project_gids_for_entity(self, entity: Any) -> list[str]:
    """Extract project GIDs from entity memberships."""
    if entity and hasattr(entity, "memberships") and entity.memberships:
        return [
            m.get("project", {}).get("gid")
            for m in entity.memberships
            if m.get("project", {}).get("gid")
        ]
    # Fallback: use session's current project context if available
    if self._current_project_gid:
        return [self._current_project_gid]
    return []
```

### Part 2: BaseClient Helper Methods

Provide reusable cache helpers for client integration:

```python
class BaseClient:
    """Base class with reusable cache helper methods."""

    def _cache_get(self, key: str, entry_type: EntryType) -> CacheEntry | None:
        """Check cache with graceful degradation."""
        if self._cache is None:
            return None
        try:
            entry = self._cache.get_versioned(key, entry_type)
            if entry and not entry.is_expired():
                return entry
            return None
        except Exception as exc:
            logger.warning("Cache get failed: %s", exc)
            return None

    def _cache_set(
        self,
        key: str,
        data: dict,
        entry_type: EntryType,
        ttl: int | None = None,
    ) -> None:
        """Store in cache with graceful degradation."""
        if self._cache is None:
            return
        try:
            entry = CacheEntry(
                key=key,
                data=data,
                entry_type=entry_type,
                ttl=ttl or 300,
                ...
            )
            self._cache.set_versioned(key, entry)
        except Exception as exc:
            logger.warning("Cache set failed: %s", exc)

    def _cache_invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache with graceful degradation."""
        if self._cache is None:
            return
        try:
            self._cache.invalidate(key, entry_types)
        except Exception as exc:
            logger.warning("Cache invalidate failed: %s", exc)
```

Client integration using inline pattern:

```python
class TasksClient(BaseClient):
    async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
        # Check cache first
        cached_entry = self._cache_get(task_gid, EntryType.TASK)
        if cached_entry is not None:
            data = cached_entry.data
            if raw:
                return data
            task = Task.model_validate(data)
            task._client = self._client
            return task

        # Cache miss: fetch from API
        data = await self._http.get(f"/tasks/{task_gid}", ...)

        # Store in cache
        ttl = self._resolve_entity_ttl(data)
        self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)

        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client
        return task
```

## Rationale

### Why Phase 1.5 (After CRUD, Before Cascade)?

| Position | Pros | Cons |
|----------|------|------|
| Before Phase 1 | None | Invalidates data not yet modified |
| **After Phase 1** | **Data modified, GIDs final** | **Best timing** |
| After Phase 2 | Cascade complete | Cascade may read stale cached data |
| After Phase 5 | Everything complete | Long delay creates stale read window |

After Phase 1 ensures:
- CRUD operations complete, GIDs are final (CREATE temp→real conversion done)
- Cascade operations can read fresh data if they call `get_async()`
- Earlier invalidation reduces stale read window

### Why Post-Commit Callback Over Other Patterns?

| Pattern | Pros | Cons |
|---------|------|------|
| Event-based | Loose coupling | Complex event system |
| Direct injection | Simple | Tight coupling, pipeline knows about cache |
| **Post-commit callback** | **Clean separation, batch efficiency** | **Callback overhead** |
| Per-operation | Immediate | Many invalidate calls, not batched |

Post-commit callback wins:
- **Clean separation**: Pipeline doesn't know about cache
- **Batch efficiency**: Collect GIDs, invalidate once per entity
- **Consistent timing**: All invalidations at same point
- **Testable**: Independent testing of invalidation logic

### Why Collect GIDs in a Set?

```python
gids_to_invalidate: set[str] = set()
```

Using set ensures:
- **Deduplication**: Same task in CRUD and actions invalidated once
- **O(1) lookup**: Fast membership checking
- **Predictable iteration**: No duplicate invalidation calls

### Why Invalidate Both TASK and SUBTASKS?

```python
cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
```

When task modified:
- Its own cache entry (EntryType.TASK) is stale
- If it's a subtask, parent's subtasks list may be stale (EntryType.SUBTASKS)
- Invalidating both ensures consistency for hierarchical operations

### Why Query Memberships for Multi-Project Invalidation?

Tasks can be multi-homed - appearing in multiple projects simultaneously. Each project may have different custom fields, so each project-specific cache entry is independent.

Example: Task T1 in Projects P1 and P2
- Cache keys: `T1:P1` and `T1:P2`
- When T1 modified, both must be invalidated

Without membership query, only "current" project context invalidated, leaving stale entries for other projects.

### Why Fallback to Session Context?

Memberships may not be populated if:
- Task created without explicit opt_fields
- Task fetched in minimal mode
- Entity constructed programmatically

Fallback invalidates at least the known project context. TTL (5 minutes) handles eventual consistency for unknown contexts.

### Why Log Instead of Raise on Invalidation Failure?

```python
except Exception as exc:
    self._log.warning("cache_invalidation_failed", gid=gid, error=str(exc))
```

Per NFR-DEGRADE-001, invalidation failures should not:
- Fail the commit (data already persisted successfully)
- Raise to caller (confusing - "did my save work?")
- Silently swallow (debugging impossible)

Logging at WARNING level:
- Alerts operators to cache issues
- Does not block business logic
- Enables debugging via log analysis

### Why Inline Client Pattern Over Decorator?

Decorator pattern considered but rejected:
- Loses `raw` parameter handling complexity
- Type hints may be lost or require workarounds
- Harder to customize TTL per response
- Different cache key strategies hard to express

Inline pattern:
- Cache check visible in method body (code review clarity)
- Reusable helpers in BaseClient
- Type safety preserved
- Flexible per-method customization

## Alternatives Considered

### Alternative 1: Event-Based Invalidation
**Rejected**: Over-engineering for internal SDK mechanics. Event system is for user hooks, not internal coordination.

### Alternative 2: Direct Injection into Pipeline
**Rejected**: Violates single responsibility. Pipeline should handle persistence, not caching.

### Alternative 3: Invalidation in State Reset (Phase 4)
**Rejected**: Missing action operations. Actions like add_tag also modify task state but processed separately.

### Alternative 4: Pre-Commit Invalidation
**Rejected**: Invalidates entities that may fail to save. Creates window where cache empty but data unchanged. GIDs may not be assigned yet.

### Alternative 5: Wildcard Invalidation (task_gid:*)
**Rejected**: Requires cache provider wildcard/scan support. Redis SCAN expensive for large keyspaces.

### Alternative 6: Maintain Reverse Index (task→projects)
**Rejected**: Additional storage overhead. Index can become stale. Over-engineering.

### Alternative 7: Decorator Pattern for Clients
**Rejected**: Loses type hints, complex for `raw` parameter handling, prevents per-method TTL customization.

## Consequences

### Positive
- Immediate consistency for self-writes via SaveSession
- Multi-project awareness: All project contexts invalidated via memberships
- Clean separation: Invalidation logic isolated in dedicated method
- Batch efficiency: O(n) invalidations for n entities
- Comprehensive: Covers CRUD, action operations, DataFrame entries
- Resilient: Failures logged, not propagated
- Reusable helpers: BaseClient methods used across all clients
- Type safety: No wrapper functions losing type info
- Graceful degradation: Cache failures never prevent operations

### Negative
- Timing gap: Brief window between Phase 1 and 1.5 where cache stale
- Action coupling: Session understands ActionResult structure
- Additional phase: Commit flow more complex (5→6 phases effectively)
- Membership dependency: Requires memberships populated for full coverage
- Partial coverage risk: Unknown projects may have stale entries (mitigated by TTL)
- Code duplication: Cache check pattern repeated in each cached method
- Manual integration: Each new cacheable method must add cache logic

### Neutral
- Performance: Adds ~1ms per invalidated entity (acceptable)
- Testing: Requires mocking cache provider in session tests
- Logging overhead: Warning logs on invalidation failure
- Eventual consistency fallback: External changes still rely on TTL

## Impact

Production metrics with invalidation hooks:
- Write-then-read staleness: 5min-24h window → <1s (immediate invalidation)
- Multi-homed task correctness: 100% (all project contexts invalidated)
- SaveSession commit overhead: +1-5ms for invalidation (acceptable)

Combined with other cache features:
- Two-tier architecture (ADR-0047): Durability for invalidated data
- Progressive TTL (ADR-0048): Stable entities reach ceiling, modified entities reset
- Entity-aware TTL (ADR-0050): Invalidated Process entities get 60s TTL, Business get 3600s

## Compliance

**Enforcement mechanisms**:
1. Code review: New mutation paths trigger invalidation, cache logic uses BaseClient helpers
2. Testing: Tests verify cache invalidated after mutations, cache hit/miss behavior
3. Monitoring: Cache invalidation events logged, metrics on invalidation_count, invalidation_failures
4. Documentation: Invalidation timing documented for SaveSession

**Configuration**: None required - invalidation hooks are behavioral pattern, not configurable feature.
