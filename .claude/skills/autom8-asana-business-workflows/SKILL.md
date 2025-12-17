# Business Model Workflows

> SaveSession patterns, composite tracking, batch operations, hooks

---

## Activation Triggers

**Use this skill when**:
- Working with SaveSession for business entity hierarchies
- Implementing composite entity tracking (recursive=True)
- Designing batch operations for bulk updates
- Understanding dependency ordering for saves
- Implementing pre/post save hooks

**Keywords**: SaveSession, composite, cascading, batch operation, bulk update, save, commit, create business, recursive, track, preview, dependency order, hooks, cascade_field, CascadeOperation, CascadeExecutor, propagate, allow_override, multi-level cascade, scope-limited cascade, target_types, no override, override opt-in

**File patterns**: `**/workflows/*.py`, `**/operations/*.py`, `**/persistence/session.py`

---

## Architecture Decision: Optional Recursive Tracking (ADR-0053)

**Decision**: Provide optional recursive tracking via `track(entity, recursive=True)` flag, defaulting to `recursive=False`.

```python
# Track only business
session.track(business)  # recursive=False by default

# Track entire hierarchy
session.track(business, recursive=True)
```

Benefits:
- Explicit control over what's tracked
- Debug-friendly via `preview()`
- Works with existing DependencyGraph ordering
- Memory footprint controlled by developer

---

## Quick Reference

| I need to... | See |
|--------------|-----|
| Track composite hierarchies | [composite-savesession.md](composite-savesession.md) |
| Common save patterns | [workflow-patterns.md](workflow-patterns.md) |
| Batch operations | [batch-operation-patterns.md](batch-operation-patterns.md) |
| Pre/post save hooks | [operation-hooks.md](operation-hooks.md) |
| Best practices | [patterns-workflows.md](patterns-workflows.md) |
| Cascade field propagation | [cascade-operations.md](cascade-operations.md) |

---

## Core Pattern: SaveSession with Business Entities

```python
async with client.save_session() as session:
    # Track business (prefetch holders by default)
    session.track(business)

    # Wait for holder prefetch
    await session.prefetch_pending()

    # Track specific entities to modify
    contact = business.contacts[0]
    session.track(contact)

    # Make modifications
    business.company_id = "NEW-ID"
    contact.full_name = "Updated Name"

    # Preview before committing
    ops, _ = session.preview()
    for op in ops:
        print(f"{op.operation}: {op.entity.name}")

    # Commit all changes
    result = await session.commit_async()
```

---

## Tracking Modes

| Mode | Code | Tracks |
|------|------|--------|
| Single | `session.track(business)` | Business only |
| Recursive | `session.track(business, recursive=True)` | Entire hierarchy |
| Selective | Multiple `track()` calls | Specific entities |

```python
# Selective tracking example
session.track(business)
session.track(business.contact_holder, recursive=True)
# Tracks business + all contacts, but NOT units
```

---

## Save Order

DependencyGraph ensures correct order using Kahn's algorithm:

```
Level 0: Business (root)
Level 1: ContactHolder, UnitHolder, LocationHolder
Level 2: Contact, Unit, Address, Hours (Address/Hours are siblings)
Level 3: OfferHolder, ProcessHolder
Level 4: Offer, Process
```

Parents saved before children. New entities created, then relationships established.

---

## Progressive References

| Document | Lines | Content |
|----------|-------|---------|
| [composite-savesession.md](composite-savesession.md) | ~180 | recursive tracking, prefetch, dependency ordering |
| [workflow-patterns.md](workflow-patterns.md) | ~150 | Create, update, bulk import patterns |
| [batch-operation-patterns.md](batch-operation-patterns.md) | ~130 | Batch create, bulk update, tag operations |
| [operation-hooks.md](operation-hooks.md) | ~100 | Pre/post save hooks, validation |
| [patterns-workflows.md](patterns-workflows.md) | ~80 | Entry points, error handling, observability |
| [cascade-operations.md](cascade-operations.md) | ~150 | cascade_field(), batch propagation (ADR-0054) |

---

## When to Use Other Skills

| Need | Use Instead |
|------|-------------|
| Model definitions and fields | [autom8-asana-business-schemas](../autom8-asana-business-schemas/) |
| Holder pattern and navigation | [autom8-asana-business-relationships](../autom8-asana-business-relationships/) |
| Custom field type handling | [autom8-asana-business-fields](../autom8-asana-business-fields/) |
| Core SDK SaveSession | [autom8-asana-domain](../autom8-asana-domain/) |
