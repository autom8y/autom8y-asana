# Composite SaveSession

> Tracking and saving hierarchical business entities (ADR-0053)

---

## The Challenge

Business entities form hierarchies:

```
Business
    +-- ContactHolder
    |       +-- Contact (owner)
    |       +-- Contact
    +-- UnitHolder
            +-- Unit
                    +-- OfferHolder
                    +-- ProcessHolder
```

When saving, we need:
1. Correct order (parents before children)
2. Explicit control (don't save unintended changes)
3. Efficient batching

---

## Recursive Tracking

Track entire hierarchy with `recursive=True`:

```python
async with client.save_session() as session:
    # Tracks: Business, all holders, all children
    session.track(business, recursive=True)

    # Now all entities are tracked
    business.company_id = "NEW-ID"
    business.contacts[0].full_name = "Updated"
    business.units[0].mrr = Decimal("6000")

    # All changes saved
    result = await session.commit_async()
```

---

## Implementation

```python
class SaveSession:
    def track(
        self,
        entity: T,
        recursive: bool = False,
        prefetch_holders: bool = True,
    ) -> T:
        """Track entity for change detection.

        Args:
            entity: AsanaResource to track
            recursive: If True, track all children recursively
            prefetch_holders: If True and Business, fetch holders

        Returns:
            The tracked entity (for chaining)
        """
        self._tracker.track(entity)

        if recursive:
            self._track_recursive(entity)

        if prefetch_holders and isinstance(entity, Business):
            self._pending_prefetch.append(entity)

        return entity

    def _track_recursive(self, entity: Task) -> None:
        """Recursively track all children."""
        # Track holders if entity has HOLDER_KEY_MAP
        if hasattr(entity, 'HOLDER_KEY_MAP'):
            for holder_name in entity.HOLDER_KEY_MAP:
                holder = getattr(entity, f'_{holder_name}', None)
                if holder is not None:
                    self._tracker.track(holder)
                    self._track_recursive(holder)

        # Track direct children
        children = getattr(entity, '_children', [])
        if hasattr(entity, '_contacts'):
            children = entity._contacts
        elif hasattr(entity, '_units'):
            children = entity._units

        for child in children:
            self._tracker.track(child)
            self._track_recursive(child)
```

---

## Dependency Graph Integration

DependencyGraph orders saves by parent relationships:

```python
# Simplified flow
1. ChangeTracker.get_dirty_entities()
   -> [business, contact, unit]

2. DependencyGraph.build(dirty_entities)
   -> Analyzes .parent references

3. DependencyGraph.get_save_order()
   -> [[business], [contact, unit]]  # Levels

4. SavePipeline.execute()
   -> Level 0: Save business
   -> Level 1: Save contact, unit (can batch)
```

---

## Selective Tracking

Track specific branches instead of full tree:

```python
async with client.save_session() as session:
    # Track business only
    session.track(business)

    # Track contacts branch recursively
    session.track(business.contact_holder, recursive=True)

    # Units NOT tracked
    business.units[0].mrr = Decimal("999")  # This change is IGNORED

    # Only business and contacts saved
    await session.commit_async()
```

---

## Prefetch and Track Flow

```
1. session.track(business)
   - ChangeTracker snapshots business
   - Business added to prefetch queue

2. await session.prefetch_pending()
   - Fetch business subtasks (holders)
   - business._populate_holders()
   - Fetch holder subtasks (children)
   - holder._populate_children()

3. session.track(contact)
   - ChangeTracker snapshots contact
   - Contact ready for modification

4. contact.full_name = "Updated"
   - CustomFieldAccessor records change

5. await session.commit_async()
   - ChangeTracker finds dirty entities
   - DependencyGraph orders them
   - SavePipeline executes in order
```

---

## Memory Considerations

| Tracking Mode | Entities Tracked | Memory Impact |
|---------------|------------------|---------------|
| Single entity | 1 | Minimal |
| Business + holders | ~8 | Low |
| Full hierarchy | 50-500 | Medium |
| Deep recursive | 500-5000 | High |

### Best Practice

Track only what you modify:

```python
# Instead of
session.track(business, recursive=True)  # Tracks everything

# Do this
session.track(business)
session.track(specific_contact)
session.track(specific_unit)
```

---

## Preview Before Commit

Always preview for complex hierarchies:

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Make changes
    business.company_id = "NEW"
    for contact in business.contacts:
        contact.campaign = "Q4"

    # Preview
    ops, _ = session.preview()
    print(f"Will save {len(ops)} entities:")
    for op in ops:
        print(f"  {op.operation}: {op.entity.name}")

    # Confirm before commit
    if confirm("Proceed?"):
        await session.commit_async()
```

---

## Handling New Entities

New entities in hierarchy:

```python
from uuid import uuid4

async with client.save_session() as session:
    session.track(business)

    # Create new contact
    new_contact = Contact(
        gid=f"temp_{uuid4()}",
        name="New Contact",
        parent=business.contact_holder,
    )
    new_contact.full_name = "John Smith"

    # Track new entity
    session.track(new_contact)

    # DependencyGraph ensures:
    # 1. Business saved first (if changed)
    # 2. ContactHolder exists
    # 3. New contact created with parent reference

    result = await session.commit_async()

    # Get real GID
    real_gid = result.gid_map.get(new_contact.gid)
```

---

## Error Handling

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Make changes
    business.company_id = "NEW"

    try:
        result = await session.commit_async()

        if result.success:
            print(f"Saved {len(result.succeeded)} entities")
        else:
            # Some operations failed
            for failed in result.failed:
                print(f"Failed: {failed.entity.name}: {failed.error}")

    except AsanaAPIError as e:
        print(f"API error: {e.status_code}")
        # Changes not saved, can retry
```

---

## Cascade Integration (ADR-0054)

Cascading fields propagate values to descendants during commit:

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Modify cascading field
    business.office_phone = "555-9999"

    # Explicitly request cascade
    session.cascade_field(business, "Office Phone")

    # Commit flow:
    # 1. Save Business (Phase 1: CRUD)
    # 2. Cascade to all Units, Offers, Processes (Phase 2: Cascades)
    result = await session.commit_async()
```

### Commit Phase Order

```
Phase 1: CRUD Operations
    - DependencyGraph orders by parent relationships
    - Creates/updates/deletes entities
    |
    v
Phase 2: Cascade Operations  <-- NEW
    - Propagates cascading field values to descendants
    - Uses BatchClient for efficiency
    |
    v
Phase 3: Action Operations
    - add_tag, remove_tag, etc.
```

### Cascade with New Entities

New entities (temp GID) cannot be cascade sources. Cascade after creation:

```python
async with client.save_session() as session:
    # Create new business
    business = Business(gid=f"temp_{uuid4()}", name="New Business")
    business.office_phone = "555-9999"
    session.track(business)

    # Commit to get real GID
    await session.commit_async()

    # Now cascade in fresh session
async with client.save_session() as session:
    session.track(business)
    session.cascade_field(business, "Office Phone")
    await session.commit_async()
```

See [cascade-operations.md](cascade-operations.md) for full cascade patterns.

---

## Related

- [workflow-patterns.md](workflow-patterns.md) - Common save patterns
- [batch-operation-patterns.md](batch-operation-patterns.md) - Batch operations
- [patterns-workflows.md](patterns-workflows.md) - Best practices
- [cascade-operations.md](cascade-operations.md) - Cascade field propagation (ADR-0054)
