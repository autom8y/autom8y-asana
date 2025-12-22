# SaveSession (Unit of Work)

> The ONE canonical guide for SaveSession patterns. All persistence and post-commit automation knowledge lives here.

---

## Table of Contents

1. [Core Pattern](#core-pattern)
2. [Tracking Modes](#tracking-modes)
3. [Prefetch (Hydration)](#prefetch-hydration)
4. [Action Operations](#action-operations)
5. [Creating New Entities](#creating-new-entities)
6. [Field Cascading](#field-cascading)
7. [Dependency Ordering](#dependency-ordering)
8. [Preview and Commit](#preview-and-commit)
9. [Post-Commit Hooks](#post-commit-hooks)
10. [Error Handling](#error-handling)
11. [Anti-Patterns](#anti-patterns)

---

## Core Pattern

SaveSession implements Unit of Work: collect entity changes, execute in optimized batches.

```python
async with client.save_session() as session:
    # 1. Track entities (prefetch holders by default for Business)
    session.track(business)
    await session.prefetch_pending()

    # 2. Navigate and modify
    for contact in business.contacts:
        print(contact.full_name)

    business.company_id = "NEW-ID"
    session.track(contact_to_update)
    contact_to_update.contact_email = "new@example.com"

    # 3. Commit all changes
    result = await session.commit_async()
```

**Key components**:
- `ChangeTracker`: Snapshots on `track()`, detects dirty at `commit()`
- `DependencyGraph`: Orders operations (parents before children)
- `ActionExecutor`: Handles action endpoints (add_tag, etc.)

---

## Tracking Modes

### Single Entity

```python
session.track(business)  # Just the business
```

### Selective

```python
session.track(business)
session.track(business.contact_holder, recursive=True)
# Business + all contacts, NOT units
```

### Full Recursive

```python
session.track(business, recursive=True)
# Business, all holders, all children at all levels
```

**Memory impact**:

| Mode | Entities | Use Case |
|------|----------|----------|
| Single | 1 | Modify business only |
| Business + holders | ~8 | Read-only navigation |
| Full hierarchy | 50-500 | Bulk updates |

---

## Prefetch (Hydration)

`track()` queues Business entities for holder prefetch. Execute with `prefetch_pending()`:

```python
session.track(business)  # prefetch_holders=True by default
# At this point: business.contacts = []

await session.prefetch_pending()
# Now: business.contacts = [Contact, Contact, ...]
```

### Skip Prefetch

For performance when you don't need children:

```python
session.track(business, prefetch_holders=False)
business.company_id = "NEW-ID"
await session.commit_async()
```

---

## Action Operations

Operations using Asana's action endpoints (not batchable via /batch):

```python
async with client.save_session() as session:
    # Tag operations
    session.add_tag(task_gid, tag_gid)
    session.remove_tag(task_gid, other_tag_gid)

    # Project operations
    session.add_to_project(task_gid, project_gid, section_gid=section_gid)
    session.remove_from_project(task_gid, old_project_gid)

    # Section operations
    session.move_to_section(task_gid, new_section_gid)

    # Dependencies
    session.add_dependency(task_gid, blocking_task_gid)

    result = await session.commit_async()
```

Action operations execute in Phase 3 of commit (after CRUD and cascade).

---

## Creating New Entities

New entities use temporary GIDs:

```python
from uuid import uuid4

async with client.save_session() as session:
    session.track(business)
    await session.prefetch_pending()

    # Create with temp GID
    new_contact = Contact(
        gid=f"temp_{uuid4()}",
        name="New Contact",
        parent=business.contact_holder,
    )
    new_contact.full_name = "Jane Smith"
    new_contact.contact_email = "jane@example.com"

    session.track(new_contact)
    result = await session.commit_async()

    # Get real GID from result
    real_gid = result.gid_map.get(new_contact.gid)
```

---

## Field Cascading

Propagate field values from parent to descendants:

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")

    await session.commit_async()
    # All Units, Offers, Processes now have "555-9999"
```

### Cascade Behavior

| `allow_override` | Behavior |
|------------------|----------|
| `False` (default) | Always overwrite |
| `True` | Skip descendants with non-null values |

### Multi-Level Cascade

```python
# Business-level: to all descendants
session.cascade_field(business, "Office Phone")

# Unit-level: to offers only
session.cascade_field(unit, "Platforms")
```

---

## Dependency Ordering

DependencyGraph ensures parents save before children (Kahn's algorithm):

```
Level 0: Business (root)
Level 1: ContactHolder, UnitHolder, LocationHolder
Level 2: Contact, Unit, Address, Hours
Level 3: OfferHolder, ProcessHolder
Level 4: Offer, Process
```

### Commit Phase Order

```
Phase 1: CRUD Operations (DependencyGraph order)
Phase 2: Cascade Operations (batch propagation)
Phase 3: Action Operations (add_tag, etc.)
```

---

## Preview and Commit

### Preview Before Commit

```python
ops, _ = session.preview()
print(f"Will execute {len(ops)} operations:")
for op in ops:
    print(f"  {op.operation}: {op.entity.name}")

if len(ops) > 100 and not confirm("Proceed?"):
    return  # Abort
```

### SaveResult

```python
result = await session.commit_async()

if result.success:
    print(f"Saved {len(result.succeeded)} entities")
    # Access new GIDs
    for temp_gid, real_gid in result.gid_map.items():
        print(f"{temp_gid} -> {real_gid}")
else:
    for failed in result.failed:
        print(f"Failed: {failed.entity.name}: {failed.error}")
```

---

## Post-Commit Hooks

Post-commit hooks are the **extension point** for the automation layer. They execute after a successful commit, enabling rule-based automation without modifying SaveSession internals.

### The Hook Protocol

```python
from typing import Protocol
from autom8_asana.persistence.models import SaveResult

class PostCommitHook(Protocol):
    """Extension point for post-commit automation."""

    async def on_commit(
        self,
        session: "SaveSession",
        result: SaveResult,
    ) -> None:
        """Called after successful commit.

        Args:
            session: The SaveSession that just committed (can spawn nested sessions)
            result: The SaveResult with succeeded/failed entities and gid_map
        """
        ...
```

### Registering Hooks

```python
from autom8_asana.automation import AutomationEngine

# Create engine with rules
engine = AutomationEngine(
    rules=[PipelineConversionRule(config), CustomRule()],
)

# Register as post-commit hook
async with client.save_session() as session:
    session.register_hook(engine)

    # ... track and modify entities ...

    result = await session.commit_async()
    # After commit succeeds, hooks execute:
    # 1. engine.on_commit() called
    # 2. Each rule evaluates changed entities
    # 3. Rules may spawn nested SaveSessions for automation changes
```

### Hook Execution Flow

```
session.commit_async()
        |
        v
    Phase 1: CRUD Operations
        |
        v
    Phase 2: Cascade Operations
        |
        v
    Phase 3: Action Operations
        |
        v
    [Commit Success]
        |
        v
    Phase 4: Post-Commit Hooks  <-- Extension Point
        |
        +---> hook1.on_commit(session, result)
        |
        +---> hook2.on_commit(session, result)
        |
        v
    Return SaveResult
```

### Hook Guidelines

| Do | Don't |
|----|-------|
| Spawn nested SaveSessions for new changes | Modify entities in the completed session |
| Filter to only relevant entity changes | Process entities that didn't change |
| Handle errors gracefully (log, don't crash) | Let exceptions bubble up unhandled |
| Keep hooks idempotent when possible | Rely on execution order between hooks |

### Automation Engine Integration

The AutomationEngine is the primary hook consumer. It orchestrates rules that respond to entity changes:

```python
class AutomationEngine:
    """Executes automation rules as a post-commit hook."""

    def __init__(self, rules: list[AutomationRule]):
        self.rules = rules

    async def on_commit(
        self,
        session: SaveSession,
        result: SaveResult,
    ) -> None:
        for entity in result.succeeded:
            for rule in self.rules:
                if await rule.should_trigger(entity, result):
                    await rule.execute(session, entity, result)
```

See [automation.md](automation.md) for complete automation patterns.

---

## Error Handling

```python
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.company_id = "NEW"

    try:
        result = await session.commit_async()

        if not result.success:
            # Partial failures
            for failed in result.failed:
                print(f"FAILED: {failed.entity.gid}: {failed.error}")

    except RateLimitError as e:
        await asyncio.sleep(e.retry_after or 60)
    except AsanaAPIError as e:
        logger.error(f"API error {e.status_code}")
```

---

## Anti-Patterns

### Accessing Before Prefetch

```python
# BAD
session.track(business)
for contact in business.contacts:  # Empty!
    print(contact.full_name)

# GOOD
session.track(business)
await session.prefetch_pending()
for contact in business.contacts:  # Populated
    print(contact.full_name)
```

### Modifying Untracked Entity

```python
# BAD
session.track(business)
contact = business.contacts[0]
contact.full_name = "Updated"  # Not saved!
await session.commit_async()

# GOOD
session.track(business)
contact = business.contacts[0]
session.track(contact)
contact.full_name = "Updated"  # Saved
await session.commit_async()
```

### Reusing Across Sessions

```python
# BAD - stale references
business = await fetch_business(client, gid)
async with client.save_session() as s1:
    s1.track(business)
    await s1.commit_async()
async with client.save_session() as s2:
    s2.track(business)  # Stale!

# GOOD - fresh per session
async with client.save_session() as s1:
    b1 = await fetch_business(client, gid)
    s1.track(b1)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `persistence/session.py` | SaveSession class |
| `persistence/tracker.py` | ChangeTracker (dirty detection) |
| `persistence/graph.py` | DependencyGraph (topological sort) |
| `persistence/pipeline.py` | SavePipeline (execution orchestration) |
| `persistence/action_executor.py` | Action endpoint execution |
| `persistence/models.py` | EntityState, PlannedOperation, SaveResult |
| `persistence/hooks.py` | PostCommitHook protocol (extension point) |
