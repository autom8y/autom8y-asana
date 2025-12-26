# ADR-0050: Holder Lazy Loading Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-11
- **Deciders**: Architect
- **Related**: [TDD-0015](../architecture/business-model-tdd.md), [ADR-0035](ADR-0035-unit-of-work-pattern.md)

## Context

The Business model has holder properties (`contact_holder`, `unit_holder`, etc.) that contain subtasks. When should these subtasks be fetched from the Asana API?

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Minimal initial network calls | Lazy (defer until needed) |
| Predictable async behavior | Eager or on-track (not property access) |
| Batch efficiency | On-track (batch with other operations) |
| Memory efficiency | Lazy (don't fetch unused holders) |
| Developer ergonomics | Eager (properties "just work") |
| SaveSession integration | On-track (async context available) |

### Options Considered

| Option | Timing | Async Context | Batch-Friendly |
|--------|--------|---------------|----------------|
| A: On property access | `business.contact_holder` called | Problematic | No |
| B: On SaveSession.track() | When entity registered | Yes (session is async) | Yes |
| C: On init (eager) | At Business construction | Requires async factory | Partial |

## Decision

**Fetch holder subtasks on `SaveSession.track()` with an optional `prefetch_holders=True` parameter (default True for Business entities).**

### Implementation

```python
def track(
    self,
    entity: T,
    prefetch_holders: bool = True,
) -> T:
    """Track entity with optional holder prefetch."""
    self._tracker.track(entity)

    if prefetch_holders and isinstance(entity, Business):
        self._pending_prefetch.append(entity)

    return entity
```

Prefetch is executed at the start of `commit_async()` or via explicit `await session.prefetch_holders()`.

## Rationale

### Why Option B (On Track)?

1. **Async context is available**: SaveSession is already an async context manager. Fetching at track time keeps async operations in async context.

2. **Batch-friendly**: Multiple holders can be fetched in parallel or batched:
   ```python
   # Fetch all holder subtasks for tracked businesses
   tasks = [self._fetch_holders(b) for b in pending]
   await asyncio.gather(*tasks)
   ```

3. **Predictable timing**: Developers know exactly when network calls happen - at track time, not scattered across property accesses.

4. **Optional control**: `prefetch_holders=False` skips the fetch for performance-sensitive cases.

### Why Not Option A (On Property Access)?

Creating async properties breaks Python conventions:
```python
# BAD: Requires await on property
contact_holder = await business.contact_holder  # Unintuitive

# BAD: Returns coroutine from property
holder = business.contact_holder  # Returns coroutine, not holder
```

This would require either:
- Sync blocking (blocks event loop) - Prohibited per ADR-0002
- Returning coroutines from properties - Confusing API

### Why Not Option C (On Init)?

Task construction should be cheap. Triggering network calls in `__init__` would:
- Require async factory pattern everywhere
- Fetch holders even when not needed
- Break Pydantic's `model_validate()` pattern

## Consequences

### Positive
- Predictable async behavior aligned with SaveSession
- Batch-friendly for multiple Business entities
- Explicit control via `prefetch_holders` parameter
- Works with existing async context manager pattern

### Negative
- Holders unavailable until entity tracked in session
- Adds prefetch step to commit flow
- Extra parameter for developers to learn

### Mitigation
- Provide `business.fetch_holders_async()` for standalone use outside SaveSession
- Default `prefetch_holders=True` for convenience

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] Holder properties return cached values, never trigger network calls
   - [ ] Network calls for holders only in SaveSession context
   - [ ] `prefetch_holders` parameter documented

2. **Unit tests**:
   ```python
   def test_holder_property_does_not_fetch():
       """Holder property returns None before prefetch, not coroutine."""
       business = Business.model_validate(api_response)
       assert business.contact_holder is None  # Not fetched yet

   async def test_track_prefetches_holders():
       """track() with default params fetches holders."""
       async with client.save_session() as session:
           session.track(business)
           await session.prefetch_holders()
           assert business.contact_holder is not None
   ```
