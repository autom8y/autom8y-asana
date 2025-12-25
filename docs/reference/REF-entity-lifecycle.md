# Entity Lifecycle Pattern

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for entity management lifecycle in autom8_asana SDK

## Overview

The Entity Lifecycle Pattern is the canonical approach for managing business entities (Business, Contact, Unit, Offer, etc.) in the autom8_asana SDK. This pattern defines a five-phase lifecycle that all entities follow: Define → Detect → Populate → Navigate → Persist.

This pattern appears throughout the SDK codebase and is referenced in 25+ design documents. This document serves as the single source of truth for understanding and implementing entity operations.

## The Five Phases

### 1. Define

**Purpose**: Declare entity types and their structure.

**Mechanism**: Pydantic models with Task inheritance, custom field descriptors, and holder class definitions.

**Artifacts**:
- Pydantic model classes (e.g., `Business(Task)`, `Contact(Task)`)
- Holder classes (e.g., `ContactHolder`, `UnitHolder`)
- Custom field descriptors for typed access

**Code Example**:
```python
from autom8_asana.models.task import Task
from typing import ClassVar

class Business(Task):
    """Business entity - root of the business model hierarchy."""

    # Holder key map for subtask type detection
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
    }

    # Primary project for detection
    PRIMARY_PROJECT_GID: ClassVar[str] = "123456789"
```

**References**:
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md)
- [TDD-0002: Models and Pagination](../design/TDD-0002-models-pagination.md)
- [ADR-0029: Task Subclass Strategy](../decisions/ADR-0029-task-subclass-strategy.md)

---

### 2. Detect

**Purpose**: Identify entity type from an Asana task.

**Mechanism**: 5-tier detection system (Project Membership → Name Pattern → Parent Context → Structure Inspection → Unknown).

**Process**:
1. **Tier 1 (Project Membership)**: Check if task belongs to entity's primary project (O(1), zero API calls)
2. **Tier 2 (Name Pattern)**: Match task name against entity naming conventions
3. **Tier 3 (Parent Context)**: Infer type from parent task type
4. **Tier 4 (Structure Inspection)**: Async examination of subtask structure
5. **Tier 5 (Unknown)**: Return UNKNOWN with healing flag

**Code Example**:
```python
from autom8_asana.models.business.detection import detect_entity_type, DetectionResult

# Synchronous detection (Tiers 1-3)
result: DetectionResult = detect_entity_type(task)
print(f"Entity type: {result.entity_type}")
print(f"Detected via: {result.tier_used}")
print(f"Needs healing: {result.needs_healing}")

# Async detection (Tiers 1-5, includes structure inspection)
result = await detect_entity_type_async(task, client)
```

**Detection Result**:
```python
@dataclass
class DetectionResult:
    entity_type: EntityType
    tier_used: int
    needs_healing: bool
    expected_project: Optional[str] = None
```

**Performance Characteristics**:
- **Tier 1**: <1ms, no API calls (target: 95% of cases)
- **Tier 2**: <5ms, no API calls
- **Tier 3**: <10ms, may require parent fetch
- **Tier 4**: Variable, requires async subtask fetch

**References**:
- [REF-detection-tiers.md](./REF-detection-tiers.md) - Detailed tier algorithms
- [TDD-DETECTION](../design/TDD-DETECTION.md) - Detection system design
- [ADR-0093: Project-Based Detection](../decisions/ADR-0093-project-membership-detection.md)

---

### 3. Populate

**Purpose**: Hydrate entity with data from Asana.

**Mechanisms**:
- **Direct fetch**: Single entity load via `get_task(gid)`
- **Batch fetch**: Multiple entities via `BatchClient`
- **Cache-optimized fetch**: Leverage cache for frequently accessed entities
- **Hierarchy hydration**: Recursive loading of entity trees

**Hydration Strategies**:

**Lazy Loading** (default):
```python
# Fetch business only, holders populated on access
business = await client.get_business(gid)
# Triggers fetch of contacts when accessed
contacts = await business.contact_holder.contacts
```

**Eager Loading** (via SaveSession):
```python
async with SaveSession(client) as session:
    # Fetches business + all holders in single operation
    business = await session.track(business_gid, prefetch=True)
```

**Batch Hydration**:
```python
# Efficiently hydrate multiple entities
businesses = await client.batch_get_businesses([gid1, gid2, gid3])
```

**Performance Considerations**:
- Use cache-optimized fetch for frequently accessed entities
- Batch operations when hydrating multiple entities
- Prefetch holders in SaveSession to avoid N+1 queries
- Progressive TTL extends cache lifetime for stable data

**References**:
- [TDD-0017: Hierarchy Hydration](../design/TDD-0017-hierarchy-hydration.md)
- [REF-batch-operations.md](./REF-batch-operations.md)
- [REF-cache-architecture.md](./REF-cache-architecture.md)
- [ADR-0031: Lazy vs Eager Evaluation](../decisions/ADR-0031-lazy-eager-evaluation.md)

---

### 4. Navigate

**Purpose**: Traverse entity relationships and holder hierarchies.

**Navigation Patterns**:

**Downward Navigation** (Parent → Children):
```python
# Business → Holders
business = await client.get_business(gid)
contacts = await business.contact_holder.contacts
units = await business.unit_holder.units

# Unit → Nested Holders
unit = units[0]
offers = await unit.offer_holder.offers
```

**Upward Navigation** (Child → Parent):
```python
# Contact → Business (via bidirectional reference)
contact = await client.get_contact(contact_gid)
business = contact.business

# Unit → ContactHolder → Business
unit = await client.get_unit(unit_gid)
contact_holder = unit.contact_holder
business = contact_holder.business
```

**Lateral Navigation** (Siblings):
```python
# Navigate between contacts in same holder
contact_holder = business.contact_holder
owner = next(c for c in contact_holder.contacts if c.is_owner)
other_contacts = [c for c in contact_holder.contacts if not c.is_owner]
```

**Bidirectional Reference Caching**:
- Parent references cached on child for O(1) access
- Cache invalidated when hierarchy changes
- Prevents circular dependencies via weak references

**Multi-Homing Considerations**:
- Asana tasks can belong to multiple projects
- Business entities typically belong to one primary project
- Use `PRIMARY_PROJECT_GID` for canonical project membership

**References**:
- [REF-asana-hierarchy.md](./REF-asana-hierarchy.md) - Asana resource hierarchy
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md)
- [ADR-0050: Holder Lazy Loading Strategy](../decisions/ADR-0050-holder-lazy-loading-strategy.md)
- [ADR-0052: Bidirectional Reference Caching](../decisions/ADR-0052-bidirectional-reference-caching.md)

---

### 5. Persist

**Purpose**: Save entity changes back to Asana.

**Mechanism**: SaveSession Unit of Work pattern with dependency tracking.

**Lifecycle**: Track → Modify → Commit → Validate

**Basic Usage**:
```python
async with SaveSession(client) as session:
    # Track entities for change detection
    business = await session.track(business_gid)

    # Modify entities (changes tracked via snapshots)
    business.name = "Updated Business Name"
    business.custom_fields["CompanyId"] = "NEW-123"

    # Create new entities with placeholder GIDs
    new_contact = Contact(name="New Contact", parent=business)
    session.track(new_contact)

    # Commit persists all changes in dependency order
    result = await session.commit()

    # Check results
    print(f"Successful: {len(result.successful)}")
    print(f"Failed: {len(result.failed)}")
```

**Dependency Resolution**:
- SaveSession builds dependency graph using Kahn's algorithm
- Entities saved in topological order (parents before children)
- Placeholder GIDs resolved after parent creation
- Cross-holder dependencies handled automatically

**Change Detection**:
- Snapshot-based dirty detection via `model_dump()`
- Only modified fields included in update payload
- Custom field changes tracked separately

**Partial Failure Handling**:
- Commit-and-report semantics (don't rollback on partial failure)
- Failed operations returned in `result.failed`
- Successful operations committed and GIDs updated

**Self-Healing Integration**:
```python
async with SaveSession(client, auto_heal=True) as session:
    # Entities with needs_healing=True automatically added to primary project
    business = await session.track(business_gid)
    await session.commit()  # Healing operations included
```

**References**:
- [REF-savesession-lifecycle.md](./REF-savesession-lifecycle.md) - Detailed SaveSession reference
- [TDD-0010: Save Orchestration](../design/TDD-0010-save-orchestration.md)
- [ADR-0035: Unit of Work Pattern](../decisions/ADR-0035-unit-of-work-pattern.md)
- [ADR-0036: Change Tracking Strategy](../decisions/ADR-0036-change-tracking-strategy.md)
- [ADR-0037: Dependency Graph Algorithm](../decisions/ADR-0037-dependency-graph-algorithm.md)

---

## Complete Lifecycle Example

```python
from autom8_asana import AsyncClient
from autom8_asana.models.business import Business, Contact
from autom8_asana.persistence import SaveSession

async def complete_entity_lifecycle():
    async with AsyncClient() as client:
        # === 1. DEFINE ===
        # Entity models already defined in SDK

        # === 2. DETECT ===
        from autom8_asana.models.business.detection import detect_entity_type

        task = await client.tasks.get_task(task_gid="123456789")
        detection = detect_entity_type(task)

        if detection.entity_type == EntityType.BUSINESS:
            # === 3. POPULATE ===
            business = await client.get_business(task.gid)

            # === 4. NAVIGATE ===
            contact_holder = business.contact_holder
            contacts = await contact_holder.contacts
            owner = next(c for c in contacts if c.is_owner)

            # === 5. PERSIST ===
            async with SaveSession(client) as session:
                # Track existing entity
                await session.track(business)

                # Modify
                business.custom_fields["Status"] = "Active"

                # Create new related entity
                new_contact = Contact(
                    name="New Contact",
                    parent=business,
                    custom_fields={"Position": "Engineer"}
                )
                session.track(new_contact)

                # Commit all changes
                result = await session.commit()

                if result.is_success:
                    print(f"All operations successful")
                    print(f"New contact GID: {new_contact.gid}")
                else:
                    print(f"Partial failure: {result.failed}")
```

---

## Lifecycle State Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ENTITY LIFECYCLE                             │
└─────────────────────────────────────────────────────────────────┘

    [Definition]
         │
         │ Class definition, schema declaration
         │
         ▼
    [Detection] ◄─────────────────────────────────┐
         │                                        │
         │ Tier 1-5 detection chain              │ Re-detection
         │                                        │ if needed
         ▼                                        │
    [Population] ────────────────┐               │
         │                       │               │
         │ Fetch from Asana     │ Cache hit     │
         │                       │               │
         ▼                       ▼               │
    [Navigation] ◄──── [Cached Entity]           │
         │                                        │
         │ Traverse relationships                │
         │                                        │
         ▼                                        │
    [Modification]                                │
         │                                        │
         │ Track changes via snapshot            │
         │                                        │
         ▼                                        │
    [Persistence]                                 │
         │                                        │
         │ SaveSession commit                    │
         │                                        │
         ▼                                        │
    [Validation] ─────────────────────────────────┘
         │
         │ Verify changes applied
         │
         ▼
    [Complete]
```

---

## Common Patterns

### Pattern: Create Entity Hierarchy

```python
async with SaveSession(client) as session:
    # Create parent
    business = Business(name="Acme Corp")
    session.track(business)

    # Create children (placeholder GIDs auto-resolved)
    contact = Contact(name="John Doe", parent=business)
    session.track(contact)

    unit = Unit(name="Unit A", parent=business)
    session.track(unit)

    # SaveSession handles dependency order automatically
    await session.commit()
```

### Pattern: Bulk Update with Navigation

```python
# Fetch all businesses
businesses = await client.batch_get_businesses(gids)

async with SaveSession(client) as session:
    for business in businesses:
        await session.track(business, prefetch=True)

        # Navigate to contacts
        contacts = await business.contact_holder.contacts

        # Update all contacts
        for contact in contacts:
            contact.custom_fields["Status"] = "Active"

    # Single commit for all changes
    result = await session.commit()
```

### Pattern: Conditional Healing

```python
# Detect with healing flag
result = await detect_entity_type_async(task, client)

if result.needs_healing:
    async with SaveSession(client, auto_heal=True) as session:
        # Entity automatically added to primary project during commit
        entity = await session.track(task.gid)
        await session.commit()
```

---

## Anti-Patterns

### Anti-Pattern: Immediate Saves (Don't Do This)

```python
# ❌ BAD: Individual saves defeat batching
for business in businesses:
    business.name = f"Updated {business.name}"
    await client.tasks.update_task(business.gid, {"name": business.name})
```

**Why**: Defeats dependency resolution, batching, and change tracking.

**Do This Instead**:
```python
# ✓ GOOD: Batch via SaveSession
async with SaveSession(client) as session:
    for business in businesses:
        await session.track(business)
        business.name = f"Updated {business.name}"
    await session.commit()
```

### Anti-Pattern: Synchronous Property Access (Don't Do This)

```python
# ❌ BAD: Accessing async property in sync context
business = get_business_sync(gid)
contacts = business.contact_holder.contacts  # Error: awaitable not awaited
```

**Why**: Holder properties require async fetch.

**Do This Instead**:
```python
# ✓ GOOD: Use async context
business = await client.get_business(gid)
contacts = await business.contact_holder.contacts
```

### Anti-Pattern: Skipping Detection (Don't Do This)

```python
# ❌ BAD: Assuming entity type without detection
task = await client.tasks.get_task(gid)
business = Business(**task.dict())  # May not be a Business!
```

**Why**: No validation that task is actually a Business entity.

**Do This Instead**:
```python
# ✓ GOOD: Detect before casting
task = await client.tasks.get_task(gid)
result = detect_entity_type(task)
if result.entity_type == EntityType.BUSINESS:
    business = await client.get_business(task.gid)
```

---

## Performance Considerations

### Detection Performance
- **Target**: 95% of detections via Tier 1 (project membership)
- **Optimization**: Ensure PRIMARY_PROJECT_GID set for all entity types
- **Healing**: Auto-heal missing project membership to improve future detection

### Population Performance
- **Cache**: Leverage cache for frequently accessed entities
- **Batching**: Use batch operations for multiple entities
- **Prefetch**: Use `prefetch=True` in SaveSession.track() to avoid N+1

### Navigation Performance
- **Lazy Loading**: Default behavior minimizes initial fetch cost
- **Eager Loading**: Use when full hierarchy is needed
- **Caching**: Bidirectional references cached to avoid redundant fetches

### Persistence Performance
- **Batching**: SaveSession batches operations (max 10 per chunk)
- **Dependency Graph**: Kahn's algorithm O(V+E) complexity
- **Partial Failure**: Commit successful operations even if some fail

---

## Testing Recommendations

### Unit Tests
- Test each phase independently
- Mock Asana API responses
- Verify detection tiers in isolation
- Test dependency graph construction

### Integration Tests
- Test complete lifecycle with real API
- Verify batch operations
- Test error handling and partial failure
- Validate cache integration

### Performance Tests
- Benchmark detection tier performance
- Measure batch operation throughput
- Test cache hit rates
- Profile SaveSession commit time

---

## See Also

- [REF-detection-tiers.md](./REF-detection-tiers.md) - 5-tier detection system details
- [REF-savesession-lifecycle.md](./REF-savesession-lifecycle.md) - SaveSession Track→Modify→Commit→Validate
- [REF-batch-operations.md](./REF-batch-operations.md) - Batch operation patterns
- [REF-asana-hierarchy.md](./REF-asana-hierarchy.md) - Asana resource hierarchy
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md)
- [TDD-0010: Save Orchestration](../design/TDD-0010-save-orchestration.md)
- [TDD-DETECTION](../design/TDD-DETECTION.md)
