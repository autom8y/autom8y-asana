# SaveSession Lifecycle

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for SaveSession Unit of Work pattern

## Overview

SaveSession implements the Unit of Work pattern for batched Asana API operations in the autom8_asana SDK. It provides Django-ORM-style deferred saves where multiple model changes are collected and executed in optimized batches rather than immediately persisting each change.

The SaveSession lifecycle follows four phases: **Track → Modify → Commit → Validate**. This document serves as the single source of truth for understanding and using SaveSession.

## The Four Phases

### 1. Track

**Purpose**: Monitor entity changes through explicit registration.

**Mechanism**: Snapshot-based dirty detection via `model_dump()`.

**API**:
```python
async with SaveSession(client) as session:
    # Track existing entity (has GID)
    entity = await session.track(entity_gid)

    # Track new entity (no GID, will be created)
    new_entity = Task(name="New Task")
    session.track(new_entity)

    # Track with prefetch (eager load holders)
    business = await session.track(business_gid, prefetch=True)
```

**Tracking Behavior**:
- **Opt-in model**: Entities must be explicitly tracked via `track()`
- **Snapshot capture**: Initial state saved via `model_dump()`
- **State assignment**: Entity state set to NEW (no GID) or CLEAN (has GID)
- **Deduplication**: Same entity tracked once (subsequent `track()` calls ignored)

**Entity States**:
```python
class EntityState(Enum):
    NEW      = "new"       # No GID, will be created
    CLEAN    = "clean"     # Tracked, unmodified since snapshot
    MODIFIED = "modified"  # Has changes pending
    DELETED  = "deleted"   # Marked for deletion
```

**State Transitions During Track**:
```
Untracked Entity
    │
    ├─ Has GID? ─── YES ──→ CLEAN state
    │
    └─ No GID?  ─── YES ──→ NEW state
```

**Examples**:
```python
# Track existing entity
task = await session.track("123456789")  # State: CLEAN

# Track new entity
new_task = Task(name="New Task")
session.track(new_task)  # State: NEW

# Check entity state
state = session.get_state(task)
print(state)  # EntityState.CLEAN
```

**References**:
- [ADR-0035: Unit of Work Pattern](../decisions/ADR-0035-unit-of-work-pattern.md)
- [ADR-0036: Change Tracking Strategy](../decisions/ADR-0036-change-tracking-strategy.md)

---

### 2. Modify

**Purpose**: Make changes to tracked entities.

**Mechanism**: Direct modification with automatic dirty detection.

**Change Detection**:
- Compare current state to snapshot via `model_dump()`
- Only modified fields included in update payload
- Custom field changes tracked separately
- State transitions: CLEAN → MODIFIED, NEW → NEW (already pending)

**Modification Operations**:

**Field Updates**:
```python
async with SaveSession(client) as session:
    task = await session.track(task_gid)

    # Modify scalar fields
    task.name = "Updated Name"
    task.notes = "Updated Notes"

    # Modify custom fields
    task.custom_fields["Status"] = "Active"
    task.custom_fields["Priority"] = "High"

    # State automatically transitions to MODIFIED
```

**Relationship Updates**:
```python
# Set parent relationship
child_task.parent = parent_task  # Dependency edge created

# Change project membership
task.projects = [project1, project2]
```

**Cascade Operations** (Business Model):
```python
# Cascade custom field to children
business.cascade_field("Status", "Active", target_holder="contact_holder")
# All contacts in contact_holder updated
```

**Deletion**:
```python
# Mark entity for deletion
session.delete(entity)  # State: DELETED
```

**State Transitions During Modify**:
```
CLEAN Entity
    │
    │ Modify field
    │
    ▼
MODIFIED Entity
    │
    │ delete()
    │
    ▼
DELETED Entity
```

**Get Changes**:
```python
# View pending changes before commit
changes = session.get_changes(task)
print(changes)
# {
#   "name": ("Old Name", "Updated Name"),
#   "custom_fields.Status": (None, "Active")
# }
```

**References**:
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md) - Cascade operations
- [ADR-0054: Cascading Custom Fields](../decisions/ADR-0054-cascading-custom-fields.md)

---

### 3. Commit

**Purpose**: Persist all changes to Asana in dependency order.

**Mechanism**: Dependency graph resolution, batch API calls, GID resolution.

**Commit Process**:

#### Step 1: Validation
```
Validate
├─ Cycle detection in dependency graph
├─ Required field validation
├─ State consistency checks
└─ Hook: pre_save events
```

#### Step 2: Dependency Graph Construction
```python
# Kahn's Algorithm for Topological Sort
# Groups entities into dependency levels

Level 0: [parent_task]          # No dependencies
Level 1: [child1, child2]        # Depend on Level 0
Level 2: [grandchild1]           # Depends on Level 1
```

**Dependency Types**:
- **Parent-child**: Child depends on parent GID
- **Reference**: Entity A references entity B's GID
- **Custom field**: Field value references another entity

**Placeholder GID Resolution**:
```python
# New entities assigned temporary GIDs
new_task = Task(name="New")  # Temp GID: "temp_001"
child_task = Task(name="Child", parent=new_task)

# After parent created:
# new_task.gid = "987654321" (real GID from Asana)
# child_task.parent updated to "987654321"
```

#### Step 3: Batch Execution
```python
# Entities grouped by dependency level
# Each level executed sequentially
# Within level: batched in chunks of 10

for level in dependency_levels:
    chunks = chunk_operations(level, size=10)
    for chunk in chunks:
        batch_request = build_batch_request(chunk)
        batch_result = await batch_client.execute(batch_request)
        correlate_results(chunk, batch_result)
```

**Batch Execution Strategy**:
- **Fixed batch size**: 10 operations per chunk (per ADR-0039)
- **Sequential levels**: Level N+1 waits for Level N
- **Parallel within level**: Operations within level can execute concurrently
- **Delegation**: Uses existing `BatchClient` from TDD-0005

#### Step 4: Result Correlation
```
Correlate Results
├─ Match responses to entities (via temp GID or real GID)
├─ Update entity GIDs (for CREATE operations)
├─ Clear dirty state (for successful operations)
├─ Collect failures (for partial failure reporting)
└─ Hook: post_save events
```

**Commit API**:
```python
# Async commit
result = await session.commit()

# Sync commit (wrapper)
result = session.commit_sync()

# Check results
if result.is_success:
    print("All operations successful")
else:
    print(f"Successful: {len(result.successful)}")
    print(f"Failed: {len(result.failed)}")
    for error in result.failed:
        print(f"  {error.entity}: {error.message}")
```

**SaveResult**:
```python
@dataclass
class SaveResult:
    successful: list[AsanaResource]  # Successfully saved
    failed: list[SaveError]           # Failed operations
    is_success: bool                  # True if no failures

@dataclass
class SaveError:
    entity: AsanaResource
    operation: OperationType  # CREATE, UPDATE, DELETE
    error: Exception
    message: str
```

**References**:
- [ADR-0037: Dependency Graph Algorithm](../decisions/ADR-0037-dependency-graph-algorithm.md)
- [ADR-0039: Batch Execution Strategy](../decisions/ADR-0039-batch-execution-strategy.md)
- [ADR-0040: Partial Failure Handling](../decisions/ADR-0040-partial-failure-handling.md)
- [TDD-0005: Batch API](../design/TDD-0005-batch-api.md)

---

### 4. Validate

**Purpose**: Verify all changes applied correctly.

**Mechanism**: Partial failure handling with commit-and-report semantics.

**Validation Behavior**:
- **Successful operations**: Committed, GIDs updated, state cleared
- **Failed operations**: Reported in `SaveResult.failed`
- **No rollback**: Partial failure does not undo successful operations

**Partial Failure Handling**:
```python
async with SaveSession(client) as session:
    # Track 3 entities
    await session.track(entity1)
    await session.track(entity2)
    await session.track(entity3)

    # Modify all
    entity1.name = "Updated 1"
    entity2.name = "Updated 2"  # Will fail (e.g., permission denied)
    entity3.name = "Updated 3"

    # Commit
    result = await session.commit()

    # Result:
    # result.successful = [entity1, entity3]
    # result.failed = [SaveError(entity2, UPDATE, PermissionError, "...")]
    # result.is_success = False
```

**Commit-and-Report Semantics** (per ADR-0040):
1. Execute batch operations
2. Successful operations are committed (no rollback)
3. Failed operations collected in `SaveResult.failed`
4. Application decides how to handle partial failure

**Retry Strategy**:
```python
# Manual retry of failed operations
result = await session.commit()

if not result.is_success:
    # Re-track failed entities
    for error in result.failed:
        session.track(error.entity)

    # Retry commit
    retry_result = await session.commit()
```

**Self-Healing Integration**:
```python
# Auto-heal entities missing project membership
async with SaveSession(client, auto_heal=True) as session:
    task = await session.track(task_gid)

    # If task.needs_healing=True (from detection)
    # Automatically add task to primary project during commit
    result = await session.commit()
```

**References**:
- [ADR-0040: Partial Failure Handling](../decisions/ADR-0040-partial-failure-handling.md)
- [TDD-DETECTION](../design/TDD-DETECTION.md) - Self-healing integration

---

## Complete SaveSession Example

```python
from autom8_asana import AsyncClient
from autom8_asana.models.business import Business, Contact
from autom8_asana.persistence import SaveSession

async def savesession_lifecycle_example():
    async with AsyncClient() as client:
        async with SaveSession(client) as session:
            # === 1. TRACK ===
            # Track existing business
            business = await session.track("123456789")
            print(f"State: {session.get_state(business)}")  # CLEAN

            # Track new contact
            new_contact = Contact(
                name="John Doe",
                parent=business  # Dependency: contact depends on business
            )
            session.track(new_contact)
            print(f"State: {session.get_state(new_contact)}")  # NEW

            # === 2. MODIFY ===
            # Modify business
            business.name = "Updated Business Name"
            business.custom_fields["Status"] = "Active"
            print(f"State: {session.get_state(business)}")  # MODIFIED

            # Modify new contact
            new_contact.custom_fields["Email"] = "john@example.com"

            # View pending changes
            changes = session.get_changes(business)
            print(f"Changes: {changes}")

            # === 3. COMMIT ===
            # Dry run preview
            planned = session.preview()
            print(f"Planned operations: {len(planned)}")
            for op in planned:
                print(f"  {op.operation}: {op.entity.name}")

            # Execute commit
            result = await session.commit()

            # === 4. VALIDATE ===
            if result.is_success:
                print("All operations successful")
                print(f"New contact GID: {new_contact.gid}")  # Real GID assigned
            else:
                print(f"Partial failure:")
                print(f"  Successful: {len(result.successful)}")
                print(f"  Failed: {len(result.failed)}")
                for error in result.failed:
                    print(f"    {error.entity.name}: {error.message}")
```

---

## Dependency Graph Algorithm

SaveSession uses **Kahn's Algorithm** for topological sorting to determine save order.

### Algorithm Overview

```python
def topological_sort(entities) -> list[list[Entity]]:
    """
    Returns list of dependency levels.
    Level 0 has no dependencies.
    Level N depends only on levels < N.
    """
    # Build adjacency list and in-degree count
    graph = defaultdict(list)
    in_degree = defaultdict(int)

    for entity in entities:
        for dependency in entity.dependencies:
            graph[dependency].append(entity)
            in_degree[entity] += 1

    # Process entities with zero in-degree
    levels = []
    current_level = [e for e in entities if in_degree[e] == 0]

    while current_level:
        levels.append(current_level)
        next_level = []

        for entity in current_level:
            for neighbor in graph[entity]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_level.append(neighbor)

        current_level = next_level

    # Cycle detection
    if sum(len(level) for level in levels) != len(entities):
        raise CyclicDependencyError()

    return levels
```

### Dependency Types

**Parent-Child Dependencies**:
```python
parent = Task(name="Parent")
child = Task(name="Child", parent=parent)

# Dependency edge: child → parent
# Save order: parent first, then child
```

**Reference Dependencies**:
```python
task_a = Task(name="A")
task_b = Task(name="B", custom_fields={"Depends On": task_a})

# Dependency edge: task_b → task_a
# Save order: task_a first, then task_b
```

**Cross-Holder Dependencies**:
```python
business = Business(name="Acme")
contact = Contact(name="John", parent=business)
unit = Unit(name="Unit A", parent=business)
offer = Offer(name="Offer 1", parent=unit)

# Dependency graph:
#   business (Level 0)
#   ├── contact (Level 1)
#   └── unit (Level 1)
#       └── offer (Level 2)
```

### Complexity

- **Time**: O(V + E) where V = entities, E = dependency edges
- **Space**: O(V + E) for adjacency list and in-degree map

**References**:
- [ADR-0037: Dependency Graph Algorithm](../decisions/ADR-0037-dependency-graph-algorithm.md)

---

## Advanced Patterns

### Pattern: Nested Hierarchies

```python
async with SaveSession(client) as session:
    # Create entire business hierarchy in one session
    business = Business(name="Acme Corp")
    session.track(business)

    # Level 1: Direct children
    contact1 = Contact(name="Owner", parent=business)
    contact2 = Contact(name="Employee", parent=business)
    unit = Unit(name="Unit A", parent=business)
    session.track(contact1)
    session.track(contact2)
    session.track(unit)

    # Level 2: Nested children
    offer = Offer(name="Offer 1", parent=unit)
    session.track(offer)

    # Single commit saves all in dependency order
    result = await session.commit()
    # Order: business → [contact1, contact2, unit] → offer
```

### Pattern: Bulk Update with Dependencies

```python
async with SaveSession(client) as session:
    # Update multiple businesses and their contacts
    businesses = await client.batch_get_businesses(gids)

    for business in businesses:
        await session.track(business, prefetch=True)

        # Update business
        business.custom_fields["Status"] = "Active"

        # Update all contacts
        contacts = await business.contact_holder.contacts
        for contact in contacts:
            contact.custom_fields["Status"] = "Active"

    # Single commit for all changes
    result = await session.commit()
```

### Pattern: Conditional Creation

```python
async with SaveSession(client) as session:
    business = await session.track(business_gid)

    # Conditionally create contact if doesn't exist
    contacts = await business.contact_holder.contacts
    owner = next((c for c in contacts if c.is_owner), None)

    if not owner:
        owner = Contact(name="Default Owner", parent=business)
        owner.custom_fields["Position"] = "Owner"
        session.track(owner)

    result = await session.commit()
```

### Pattern: Dry Run Preview

```python
async with SaveSession(client) as session:
    # Track and modify entities
    task1 = await session.track(task1_gid)
    task1.name = "Updated"

    task2 = Task(name="New Task")
    session.track(task2)

    # Preview operations without executing
    planned = session.preview()

    print("Planned operations:")
    for op in planned:
        print(f"  {op.operation}: {op.entity.name}")
        print(f"    Fields: {op.fields}")

    # Decide whether to commit
    if user_confirms():
        result = await session.commit()
```

---

## Error Handling

### Common Errors

**CyclicDependencyError**:
```python
# Cycle: A depends on B, B depends on A
try:
    result = await session.commit()
except CyclicDependencyError as e:
    print(f"Cycle detected: {e.cycle}")
```

**ValidationError**:
```python
# Missing required fields
task = Task()  # No name!
session.track(task)

try:
    result = await session.commit()
except ValidationError as e:
    print(f"Validation failed: {e.errors}")
```

**PartialFailureError**:
```python
# Some operations succeed, some fail
result = await session.commit()

if not result.is_success:
    for error in result.failed:
        if isinstance(error.error, PermissionError):
            print(f"Permission denied: {error.entity.name}")
        elif isinstance(error.error, NotFoundError):
            print(f"Not found: {error.entity.name}")
        else:
            print(f"Unknown error: {error.message}")
```

### Error Recovery Strategies

**Retry Failed Operations**:
```python
result = await session.commit()

if not result.is_success:
    # Retry only failed operations
    for error in result.failed:
        session.track(error.entity)

    retry_result = await session.commit()
```

**Manual Rollback** (application-level):
```python
result = await session.commit()

if not result.is_success:
    # Manually revert successful changes (if needed)
    for entity in result.successful:
        revert_changes(entity)
```

**Compensation Pattern**:
```python
result = await session.commit()

if not result.is_success:
    # Create compensating operations
    async with SaveSession(client) as compensation_session:
        for entity in result.successful:
            compensation_session.delete(entity)
        await compensation_session.commit()
```

---

## Event Hooks

SaveSession supports event hooks for observability and custom logic.

### Hook Types

**Pre-Save**:
```python
def log_pre_save(entity, operation):
    print(f"About to {operation}: {entity.name}")

session.on_pre_save(log_pre_save)
```

**Post-Save**:
```python
def log_post_save(entity, operation, result):
    if result.success:
        print(f"Saved {entity.name}: {entity.gid}")

session.on_post_save(log_post_save)
```

**On Error**:
```python
def log_error(entity, operation, error):
    print(f"Error saving {entity.name}: {error}")

session.on_error(log_error)
```

**References**:
- [ADR-0041: Event Hook System](../decisions/ADR-0041-event-hook-system.md)

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `track()` | O(1) | Snapshot capture via `model_dump()` |
| `get_changes()` | O(F) | F = number of fields |
| `get_dependency_order()` | O(V + E) | Kahn's algorithm |
| `commit()` | O(V + E + N/B) | V+E = graph, N/B = batch calls |

Where:
- V = number of entities
- E = number of dependency edges
- F = number of fields
- N = number of operations
- B = batch size (default 10)

### API Call Optimization

**Without SaveSession** (naive):
```python
# N API calls for N entities
for task in tasks:
    await client.tasks.update_task(task.gid, {"name": task.name})
# Cost: N API calls
```

**With SaveSession**:
```python
async with SaveSession(client) as session:
    for task in tasks:
        await session.track(task)
        task.name = f"Updated {task.name}"
    await session.commit()
# Cost: ceil(N / 10) batch API calls
```

**Reduction**: N calls → ceil(N / 10) calls = **90% reduction** for N=100

### Memory Overhead

- **Snapshot storage**: ~1KB per tracked entity (full `model_dump()`)
- **Dependency graph**: ~100 bytes per edge
- **Total**: O(V) memory overhead

---

## Testing Recommendations

### Unit Tests

```python
def test_track_new_entity():
    session = SaveSession(client)
    entity = Task(name="Test")

    session.track(entity)

    assert session.get_state(entity) == EntityState.NEW
    assert session.is_tracked(entity)

def test_dirty_detection():
    session = SaveSession(client)
    entity = Task(gid="123", name="Original")

    session.track(entity)
    entity.name = "Modified"

    assert session.get_state(entity) == EntityState.MODIFIED
    changes = session.get_changes(entity)
    assert changes["name"] == ("Original", "Modified")

def test_dependency_ordering():
    session = SaveSession(client)
    parent = Task(name="Parent")
    child = Task(name="Child", parent=parent)

    session.track(parent)
    session.track(child)

    order = session.get_dependency_order()
    assert order.index(parent) < order.index(child)
```

### Integration Tests

```python
async def test_commit_creates_entity(async_client):
    async with SaveSession(async_client) as session:
        task = Task(name="Integration Test")
        session.track(task)

        result = await session.commit()

        assert result.is_success
        assert task.gid is not None
        assert task.gid.startswith("123")  # Real GID

async def test_partial_failure_handling(async_client):
    async with SaveSession(async_client) as session:
        valid_task = Task(name="Valid")
        invalid_task = Task()  # Missing required field

        session.track(valid_task)
        session.track(invalid_task)

        result = await session.commit()

        assert not result.is_success
        assert len(result.successful) == 1
        assert len(result.failed) == 1
```

---

## See Also

- [REF-entity-lifecycle.md](./REF-entity-lifecycle.md) - Complete entity lifecycle (Define→Detect→Populate→Navigate→Persist)
- [REF-batch-operations.md](./REF-batch-operations.md) - Batch operation patterns
- [TDD-0010: Save Orchestration](../design/TDD-0010-save-orchestration.md) - Full design document
- [ADR-0035: Unit of Work Pattern](../decisions/ADR-0035-unit-of-work-pattern.md)
- [ADR-0036: Change Tracking Strategy](../decisions/ADR-0036-change-tracking-strategy.md)
- [ADR-0037: Dependency Graph Algorithm](../decisions/ADR-0037-dependency-graph-algorithm.md)
- [ADR-0038: Save Concurrency Model](../decisions/ADR-0038-save-concurrency-model.md)
- [ADR-0039: Batch Execution Strategy](../decisions/ADR-0039-batch-execution-strategy.md)
- [ADR-0040: Partial Failure Handling](../decisions/ADR-0040-partial-failure-handling.md)
