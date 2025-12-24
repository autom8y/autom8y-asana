# ADR-0117: Post-Commit Invalidation Hook for DataFrame Cache

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-WATERMARK-CACHE, TDD-WATERMARK-CACHE, ADR-0102 (Post-Commit Hook Architecture), ADR-0021 (DataFrame Caching Strategy)

---

## Context

When a task is modified via SaveSession, the DataFrame cache entries for that task become stale. We need a mechanism to invalidate these entries to ensure subsequent `build_async()` calls return fresh data.

The challenge is that DataFrame cache keys include project context (`{task_gid}:{project_gid}`), and a task can be multi-homed (appear in multiple projects). When invalidating, we need to invalidate all project-specific cache entries for the modified task.

Existing infrastructure:
- `SaveSession._invalidate_cache_for_results()` already handles invalidation for `EntryType.TASK` and `EntryType.SUBTASKS`
- `EventSystem.emit_post_commit()` provides hook point for post-commit actions
- Tasks have a `memberships` attribute listing their project memberships

**Forces at play**:
- Immediate consistency for self-writes (SaveSession mutations)
- Eventual consistency for external changes (TTL-based, 5 minutes)
- Multi-homed tasks require multi-project invalidation
- Invalidation failures should not fail the commit
- Minimal changes to existing SaveSession flow

---

## Decision

We will **extend the existing `_invalidate_cache_for_results()` method** to include `EntryType.DATAFRAME` invalidation with project context awareness:

1. **Hook location**: Same method that handles TASK/SUBTASKS invalidation
2. **Project context**: Query `task.memberships` to get all project GIDs
3. **Fallback**: If memberships unavailable, invalidate with known project context (if any)
4. **Failure handling**: Log and continue - invalidation failure does not fail commit

```python
async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult],
) -> None:
    cache = getattr(self._client, "_cache_provider", None)
    if cache is None:
        return

    from autom8_asana.cache.entry import EntryType
    from autom8_asana.cache.dataframes import invalidate_task_dataframes

    gids_to_invalidate: set[str] = set()
    # ... existing collection logic ...

    # Existing: TASK and SUBTASKS invalidation
    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
        except Exception as exc:
            # Log and continue
            ...

    # NEW: DataFrame invalidation with project context
    for gid in gids_to_invalidate:
        try:
            entity = self._tracker.get_entity(gid)
            project_gids = self._get_project_gids_for_entity(entity)
            if project_gids:
                invalidate_task_dataframes(gid, project_gids, cache)
        except Exception as exc:
            # Log and continue - never fail commit
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

**Key design points**:
- Uses existing `invalidate_task_dataframes()` utility from `cache/dataframes.py`
- Queries memberships for multi-project awareness
- Falls back to session context if memberships unavailable
- Never fails the commit operation

---

## Rationale

**Why extend existing method rather than new hook?**

The existing `_invalidate_cache_for_results()` method:
- Already called at the right point in commit flow
- Already has access to cache provider and entity tracker
- Already handles failure gracefully
- Follows established pattern for SDK invalidation

Adding a separate hook would:
- Duplicate the entity collection logic
- Require additional coordination
- Add complexity without clear benefit

**Why query memberships?**

Tasks can be multi-homed - appearing in multiple projects simultaneously. Each project may have different custom fields, so each project-specific cache entry is independent.

Example: Task T1 in Projects P1 and P2
- Cache keys: `T1:P1` and `T1:P2`
- When T1 is modified, both must be invalidated

Without membership query, we might only invalidate the "current" project context, leaving stale entries for other projects.

**Why fallback to session context?**

Memberships may not be populated if:
- Task was created without explicit opt_fields
- Task was fetched in minimal mode
- Entity was constructed programmatically

In these cases, we have partial information. Invalidating at least the known project context is better than invalidating nothing. TTL (5 minutes) handles eventual consistency for unknown contexts.

**Why log and continue on failure?**

Invalidation failure should never fail a successful commit:
- The mutation succeeded in Asana
- Cache is a performance optimization, not correctness requirement
- Stale cache entries will expire via TTL (eventual consistency)
- Logging enables monitoring and debugging

---

## Alternatives Considered

### Alternative 1: Separate Post-Commit Hook

- **Description**: Register a new post-commit hook specifically for DataFrame invalidation
- **Pros**: Clear separation of concerns; doesn't modify existing method
- **Cons**:
  - Duplicates entity traversal logic
  - Additional hook registration complexity
  - Harder to ensure correct ordering
- **Why not chosen**: Existing method is the right place; hook would add complexity

### Alternative 2: Wildcard Invalidation (task_gid:*)

- **Description**: Invalidate all keys matching `{task_gid}:*` without knowing project GIDs
- **Pros**: No membership query needed; guaranteed to catch all
- **Cons**:
  - Requires cache provider wildcard/scan support
  - In-memory scan is O(n) over all keys
  - Redis SCAN is expensive for large keyspaces
- **Why not chosen**: Performance concerns; membership query is more targeted

### Alternative 3: Maintain Reverse Index (task -> projects)

- **Description**: Track task-to-project mappings in cache metadata
- **Pros**: Fast lookup without membership query
- **Cons**:
  - Additional storage overhead
  - Index can become stale
  - Complexity of maintaining consistency
- **Why not chosen**: Over-engineering; membership query is sufficient

### Alternative 4: Skip DataFrame Invalidation (TTL Only)

- **Description**: Rely entirely on TTL for DataFrame cache freshness
- **Pros**: Simplest implementation; no changes to SaveSession
- **Cons**:
  - 5-minute staleness window for self-writes
  - User modifies task, immediately sees stale data
  - Violates "immediate consistency for self-writes" goal
- **Why not chosen**: Unacceptable user experience for write-then-read pattern

---

## Consequences

### Positive

- **Immediate consistency**: Self-writes via SaveSession invalidate immediately
- **Multi-project awareness**: All project contexts invalidated via memberships
- **Non-invasive**: Extends existing pattern without new infrastructure
- **Failure resilient**: Invalidation failure doesn't break commit

### Negative

- **Membership dependency**: Requires memberships to be populated for full coverage
- **Partial coverage risk**: Unknown projects may have stale entries (mitigated by TTL)
- **Additional processing**: More work per commit (though O(n) in mutated entities)

### Neutral

- **Eventual consistency fallback**: External changes still rely on TTL
- **Logging overhead**: Warning logs on invalidation failure

---

## Compliance

To ensure this decision is followed:

1. **Code Review**: Verify DataFrame invalidation added to `_invalidate_cache_for_results()`
2. **Membership Query**: Verify `_get_project_gids_for_entity()` helper implemented
3. **Fallback Logic**: Verify fallback to session context when memberships unavailable
4. **Error Handling**: Verify try/except with logging, no commit failure
5. **Integration Tests**: Test invalidation after SaveSession commit
6. **Multi-Project Test**: Test task in multiple projects, verify all entries invalidated
