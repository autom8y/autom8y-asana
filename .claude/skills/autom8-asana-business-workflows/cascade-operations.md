# Cascade Operations

> SaveSession.cascade_field() and batch propagation (ADR-0054)

---

## Overview

Cascade operations propagate field values from any source entity (Business, Unit, etc.) to its descendants via batch API. This enables O(1) read access on descendant entities while maintaining a single source of truth.

**Critical Design Constraint**: `allow_override=False` is the DEFAULT. Parent value always overwrites descendant value unless override is explicitly opted-in.

---

## Multi-Level Cascading

Cascading can originate from **ANY level** in the hierarchy:

| Source | Targets | Example | Override? |
|--------|---------|---------|-----------|
| Business | Unit, Offer, Process, Contact | `office_phone` | NO (default) |
| Unit | Offer | `platforms` | YES (opt-in) |
| Unit | Offer, Process | `vertical` | NO (default) |

---

## SaveSession.cascade_field()

Queue a cascade operation for execution during commit:

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Modify cascading field
    business.office_phone = "555-9999"

    # Explicitly queue cascade
    session.cascade_field(business, "Office Phone")

    # Commit: saves Business, then cascades to descendants
    result = await session.commit_async()
```

### Method Signature

```python
def cascade_field(
    self,
    entity: AsanaResource,
    field_name: str,
    *,
    target_types: set[type] | None = None,
) -> SaveSession:
    """Queue cascade of field value to descendants.

    IMPORTANT: Cascade scope is relative to the source entity.
    - cascade_field(unit, "Platforms") only affects that unit's offers
    - cascade_field(business, "Office Phone") affects all business descendants

    The allow_override behavior is determined by the field's CascadingFieldDef:
    - allow_override=False (DEFAULT): Always overwrite descendant value
    - allow_override=True: Only overwrite if descendant value is None

    Args:
        entity: Source entity (Business, Unit, etc.)
        field_name: Custom field to cascade (e.g., "Office Phone", "Platforms")
        target_types: Optional filter of target entity types.
                     If None, uses field's declared target_types.

    Returns:
        Self for fluent chaining.

    Raises:
        SessionClosedError: If session is closed.
        ValueError: If entity has temp GID.
    """
```

---

## CascadeOperation Dataclass

Internal representation of a pending cascade:

```python
@dataclass
class CascadeOperation:
    """Represents a field cascade to be executed.

    Supports multi-level cascading from any source entity.
    """

    source: AsanaResource  # Entity whose value is being cascaded (Business, Unit, etc.)
    field_name: str        # Custom field name to cascade
    field_gid: str | None  # Resolved GID (populated during execution)
    new_value: Any         # Value to propagate
    target_types: set[type] | None  # Entity type filter (None = all descendants)
    allow_override: bool   # If True, skip descendants with non-null values
```

---

## Execution Flow

Cascades execute in Phase 2 of commit, after CRUD operations:

```
commit_async()
    |
    v
Phase 1: CRUD Operations
    - Create new entities (get real GIDs)
    - Update modified entities
    - Delete removed entities
    |
    v
Phase 2: Cascade Operations  <-- Here
    - Collect descendant GIDs
    - Resolve field name to GID
    - Batch update all descendants
    |
    v
Phase 3: Action Operations
    - add_tag, remove_tag, etc.
```

---

## CascadeExecutor

Executes cascades via batch API with override filtering:

```python
class CascadeExecutor:
    """Executes cascade operations via batch API.

    CRITICAL: Descendants are scoped to the source entity.
    - cascade from Unit X only affects Unit X's children
    - cascade from Business affects all Business descendants
    """

    async def execute(
        self,
        cascades: list[CascadeOperation],
        descendants_cache: dict[str, list[AsanaResource]] | None = None,
    ) -> list[BatchResult]:
        """Execute all pending cascade operations.

        Strategy:
        1. Collect descendant GIDs of THIS SPECIFIC source entity
        2. Apply allow_override filtering (skip non-null if opt-in)
        3. Resolve custom field name to GID
        4. Build batch update requests
        5. Execute via BatchClient (chunks of 10)
        6. Handle rate limits with exponential backoff
        """

    # Override filtering logic
    for descendant in descendants:
        # Handle allow_override behavior
        if cascade.allow_override:
            # Only update if descendant value is null
            current_value = descendant.get_custom_fields().get(cascade.field_name)
            if current_value is not None:
                continue  # Skip - descendant has override value

        # Default (allow_override=False): Always update
        all_updates.append((descendant.gid, {...}))
```

---

## Usage Patterns

### Basic Cascade (No Override - Default)

```python
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")
    await session.commit_async()
    # ALL descendants get "555-9999" regardless of current value
```

### Unit-Level Cascade (With Override Opt-In)

```python
async with client.save_session() as session:
    session.track(unit, recursive=True)

    unit.platforms = ["Google", "Meta"]
    session.cascade_field(unit, "Platforms")

    await session.commit_async()

    # Results:
    # - Offers with platforms=None: Updated to ["Google", "Meta"]
    # - Offers with existing platforms: KEPT their original value
```

### Multiple Cascades (Same Source)

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    business.office_phone = "555-9999"
    business.company_id = "NEW-123"

    # Cascade both fields (executed in single batch pass)
    session.cascade_field(business, "Office Phone")
    session.cascade_field(business, "Company ID")

    await session.commit_async()
```

### Multi-Level Cascade (Different Sources)

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Business-level cascade (no override)
    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")  # -> Unit, Offer, Process

    # Unit-level cascade (with override for platforms)
    for unit in business.units:
        unit.platforms = ["Google"]
        session.cascade_field(unit, "Platforms")  # -> Offers only

    await session.commit_async()
    # Business cascade: ALL descendants get office_phone
    # Unit cascades: Only offers with null platforms get updated
```

### Scope-Limited Cascade

```python
async with client.save_session() as session:
    # Load two different units
    session.track(unit_retail, recursive=True)
    session.track(unit_industrial, recursive=True)

    # Change platforms on retail unit only
    unit_retail.platforms = ["Google Shopping", "Amazon"]
    session.cascade_field(unit_retail, "Platforms")

    await session.commit_async()

    # Result:
    # - unit_retail's offers: Updated (respecting allow_override)
    # - unit_industrial's offers: UNCHANGED (not in scope)
```

### Filtered Cascade (Override Target Types)

```python
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.office_phone = "555-9999"

    # Only cascade to Units and Offers (not Processes)
    session.cascade_field(
        business,
        "Office Phone",
        target_types={Unit, Offer},  # Explicit filter
    )

    await session.commit_async()
```

### Fluent Chaining

```python
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.office_phone = "555-9999"
    business.company_id = "NEW-123"

    (session
        .cascade_field(business, "Office Phone")
        .cascade_field(business, "Company ID"))

    await session.commit_async()
```

---

## Rate Limit Handling

Cascades use BatchClient which handles rate limits per ADR-0010:

- Chunks requests into batches of 10 (Asana limit)
- Exponential backoff on 429 responses
- Partial failure reporting in SaveResult

```python
result = await session.commit_async()

if result.partial:
    # Some cascade updates failed
    for err in result.failed:
        print(f"Failed: {err.entity.gid}: {err.error}")
```

---

## Performance Considerations

| Hierarchy Size | Batch Calls | Expected Time |
|----------------|-------------|---------------|
| 50 descendants | 5 | ~2-3 seconds |
| 100 descendants | 10 | ~4-5 seconds |
| 500 descendants | 50 | ~15-20 seconds |

### Optimizations

1. **Descendants Cache**: If `track(business, recursive=True)` was used, descendants are already in memory
2. **Parallel Field Cascades**: Multiple `cascade_field()` calls combined into single batch pass
3. **Target Filtering**: Reduce scope with specific target types

---

## Error Handling

### Entity Without Real GID

```python
# New entity with temp GID - cannot cascade from it
new_business = Business(gid="temp_1", name="New Business")
session.track(new_business)

try:
    session.cascade_field(new_business, "Office Phone")
except ValueError as e:
    print(f"Expected: {e}")  # Cannot cascade from temp GID

# Solution: cascade after entity is created
result = await session.commit_async()
# Now entity has real GID, can cascade in next session
```

### Partial Failures

```python
result = await session.commit_async()

if not result.success:
    for failed in result.failed:
        if isinstance(failed.error, RateLimitError):
            # Queue for retry
            pass
        else:
            # Log permanent failure
            pass
```

---

## Reconciliation

For detecting and repairing cascade drift:

```python
reconciler = CascadeReconciler(client)

async with client.save_session() as session:
    # Check for stale values
    drifts = await reconciler.check_consistency(
        business,
        "Office Phone",
    )

    if drifts:
        print(f"Found {len(drifts)} entities with stale values")
        await reconciler.repair(session, drifts)
        await session.commit_async()
```

---

## Related

- [ADR-0054](../../../../docs/decisions/ADR-0054-cascading-custom-fields.md) - Full decision record
- [composite-savesession.md](composite-savesession.md) - SaveSession commit flow
- [batch-operation-patterns.md](batch-operation-patterns.md) - Batch API patterns
- [cascading-inherited-fields.md](../autom8-asana-business-fields/cascading-inherited-fields.md) - Field declaration patterns
