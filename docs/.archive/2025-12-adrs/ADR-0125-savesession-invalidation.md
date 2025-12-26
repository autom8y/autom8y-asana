# ADR-0125: SaveSession Cache Invalidation Hook

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-22
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md), [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md), ADR-0102, ADR-0041

## Context

When entities are modified through `SaveSession.commit_async()`, their cached representations become stale. Without cache invalidation, subsequent `get_async()` calls would return outdated data until TTL expiration.

Current `commit_async()` flow:
```
Phase 1: CRUD operations
Phase 2: Cascade operations
Phase 3: Healing operations
Phase 4: Reset entity state
Phase 5: Automation evaluation
```

We need to add cache invalidation such that:
- Modified entities are invalidated in cache
- Action operations (add_tag, move_to_section) invalidate affected tasks
- Newly created entities optionally warm the cache
- Invalidation failures don't break the commit
- Batch invalidation is efficient (O(n) not O(n^2))

**The key question**: Where in the commit flow should cache invalidation occur, and what pattern should we use?

Forces at play:
- Invalidation must happen after operations succeed (can't invalidate on failure)
- Invalidation should happen before cascade (cascades may also need fresh reads)
- Action operations affect task state (tags, memberships)
- GIDs may change for CREATE operations (temp GID -> real GID)
- Invalidation failures must not fail the commit
- Multiple entities should be invalidated efficiently

## Decision

We will use a **post-commit callback with GID collection** pattern:

```python
async def commit_async(self) -> SaveResult:
    # Phase 1: Execute CRUD and actions
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # Phase 1.5: Cache invalidation (NEW)
    await self._invalidate_cache_for_results(crud_result, action_results)

    # Phase 2-5: Continue existing phases
    ...

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

    # From action operations
    for action_result in action_results:
        if action_result.success and action_result.action.task:
            if hasattr(action_result.action.task, 'gid'):
                gids_to_invalidate.add(action_result.action.task.gid)

    # Batch invalidate (O(n) total)
    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
        except Exception as exc:
            # Log and continue - invalidation failure is not fatal
            self._log.warning("cache_invalidation_failed", gid=gid, error=str(exc))
```

## Rationale

### Why Phase 1.5 (After CRUD, Before Cascade)?

| Position | Pros | Cons |
|----------|------|------|
| Before Phase 1 | None | Invalidates data not yet modified |
| **After Phase 1** | Data is modified, invalidation is accurate | Cascade may read stale data |
| After Phase 2 | Cascade complete | Cascade may have read stale cached data |
| After Phase 5 | Everything complete | Long delay before invalidation |

We chose **after Phase 1** because:
- CRUD operations are complete, GIDs are final
- Cascade operations may call `get_async()` on related entities
- Having fresh data available for cascade prevents inconsistencies
- Earlier invalidation reduces stale read window

### Why Post-Commit Callback Over Other Patterns?

| Pattern | Description | Pros | Cons |
|---------|-------------|------|------|
| Event-based | Emit events, cache subscribes | Loose coupling | Complex event system |
| Direct injection | Pipeline calls cache.invalidate directly | Simple | Tight coupling |
| **Post-commit callback** | Session invalidates after pipeline | Clean separation | Callback overhead |
| Per-operation | Invalidate in each CRUD operation | Immediate | Many invalidate calls |

**Post-commit callback** wins because:
- **Clean separation**: Pipeline doesn't need to know about cache
- **Batch efficiency**: Collect GIDs, invalidate once per entity
- **Consistent timing**: All invalidations happen at same point
- **Testable**: Can test invalidation logic independently

### Why Collect GIDs in a Set?

```python
gids_to_invalidate: set[str] = set()
```

Using a set ensures:
- **Deduplication**: If same task is in both CRUD and actions, invalidate once
- **O(1) lookup**: Checking if GID already collected is fast
- **Predictable iteration**: No duplicate invalidation calls

### Why Invalidate Both TASK and SUBTASKS Entry Types?

```python
cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
```

When a task is modified:
- Its own cache entry (EntryType.TASK) is stale
- If it's a subtask, parent's subtasks list may be stale (EntryType.SUBTASKS)
- Invalidating both ensures consistency for hierarchical operations

### Why Not Warm Cache on CREATE?

The decision references FR-INVALIDATE-004 (CREATE operations warm cache), but we implement this cautiously:

```python
# Optional cache warming for CREATEs
for entity in crud_result.succeeded:
    if entity._operation_type == 'CREATE':
        try:
            entry = CacheEntry(key=entity.gid, data=entity.model_dump(), ...)
            cache.set_versioned(entity.gid, entry)
        except Exception:
            pass  # Best effort
```

Cache warming is best-effort because:
- The response data may not include all opt_fields
- Entity may be immediately modified by cascade
- Failure to warm is not critical (next read will cache)

### Why Log Instead of Raise on Invalidation Failure?

Per NFR-DEGRADE-001:
```python
except Exception as exc:
    self._log.warning("cache_invalidation_failed", gid=gid, error=str(exc))
```

Invalidation failures should not:
- Fail the commit (data is already persisted)
- Raise to caller (confusing - "did my save work?")
- Silently swallow (debugging would be impossible)

Logging at WARNING level:
- Alerts operators to cache issues
- Does not block business logic
- Enables debugging via log analysis

## Alternatives Considered

### Alternative 1: Event-Based Invalidation

- **Description**: SaveSession emits events, cache provider subscribes:
  ```python
  # In SaveSession
  await self._events.emit("entity_saved", entity)

  # In CacheProvider
  def on_entity_saved(self, entity):
      self.invalidate(entity.gid, ...)
  ```
- **Pros**:
  - Loose coupling between session and cache
  - Extensible (other listeners can subscribe)
  - Follows existing event hook pattern (ADR-0041)
- **Cons**:
  - Adds complexity to event system
  - Cache needs to be registered as listener
  - Error handling across event boundary is complex
  - Events may be async, adding timing concerns
- **Why not chosen**: Over-engineering for this use case. Event system is for user hooks, not internal SDK mechanics.

### Alternative 2: Direct Injection into Pipeline

- **Description**: Pipeline receives cache provider, invalidates during execution:
  ```python
  class Pipeline:
      async def execute(self, entities, cache_provider):
          for entity in entities:
              result = await self._save(entity)
              if result.success:
                  cache_provider.invalidate(entity.gid, ...)
  ```
- **Pros**:
  - Immediate invalidation after each operation
  - Simple implementation
- **Cons**:
  - Pipeline tightly coupled to cache
  - More invalidation calls (not batched)
  - Pipeline complexity increases
  - Harder to test pipeline in isolation
- **Why not chosen**: Violates single responsibility. Pipeline should handle persistence, not caching.

### Alternative 3: Invalidation in Entity State Reset

- **Description**: Integrate invalidation into Phase 4 (entity state reset):
  ```python
  # In Phase 4
  for entity in crud_result.succeeded:
      self._tracker.mark_clean(entity)
      cache.invalidate(entity.gid, ...)  # Add here
  ```
- **Pros**:
  - No new phase needed
  - Happens at same time as state cleanup
- **Cons**:
  - Action operations not included (processed separately)
  - Mixes entity state concern with cache concern
  - Harder to batch invalidations
- **Why not chosen**: Missing action operations. Actions like add_tag also modify task state.

### Alternative 4: Pre-Commit Invalidation

- **Description**: Invalidate before executing operations:
  ```python
  async def commit_async(self):
      # Invalidate first
      for entity in self._tracker.get_dirty_entities():
          cache.invalidate(entity.gid, ...)

      # Then execute
      crud_result = await self._pipeline.execute(...)
  ```
- **Pros**:
  - Simple implementation
  - Ensures no stale reads during cascade
- **Cons**:
  - Invalidates entities that may fail to save
  - Creates window where cache is empty but data unchanged
  - GIDs may not be assigned yet (CREATE operations)
- **Why not chosen**: Incorrect timing. We should only invalidate after successful mutation.

## Consequences

### Positive

- **Clean separation**: Invalidation logic isolated in dedicated method
- **Batch efficiency**: O(n) invalidations for n entities
- **Comprehensive**: Covers CRUD and action operations
- **Resilient**: Failures logged, not propagated
- **Extensible**: Easy to add more entry types to invalidate

### Negative

- **Timing gap**: Brief window between Phase 1 and Phase 1.5 where cache is stale
- **Action coupling**: Session needs to understand ActionResult structure
- **Additional phase**: Commit flow more complex (5 phases -> effectively 6)

### Neutral

- **Performance**: Adds ~1ms per invalidated entity (acceptable)
- **Testing**: Requires mocking cache provider in session tests

## Compliance

How do we ensure this decision is followed?

1. **Code review**: Any new mutation path must trigger invalidation
2. **Testing**: Tests verify cache is invalidated after mutations
3. **Logging**: Cache invalidation events are logged for audit
4. **Documentation**: Invalidation timing documented for users

## Implementation Checklist

- [ ] Add `_invalidate_cache_for_results` method to SaveSession
- [ ] Insert Phase 1.5 call in `commit_async`
- [ ] Add logging for invalidation events
- [ ] Add unit tests for invalidation logic
- [ ] Add integration test for cache invalidation flow
- [ ] Document invalidation timing in SaveSession docstring
