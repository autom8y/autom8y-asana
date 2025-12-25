# Entity Detection Tier System

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for 5-tier entity type detection system

## Overview

The Entity Detection Tier System provides a deterministic, performance-optimized approach for identifying entity types (Business, Contact, Unit, Offer, etc.) from Asana tasks. The system uses a 5-tier fallback chain with decreasing confidence and increasing cost:

1. **Tier 1 (Project Membership)**: O(1), zero API calls, 95%+ coverage target
2. **Tier 2 (Name Pattern)**: O(1) regex, no API calls
3. **Tier 3 (Parent Context)**: O(1) parent lookup, may require fetch
4. **Tier 4 (Structure Inspection)**: Async subtask examination
5. **Tier 5 (Unknown)**: Returns UNKNOWN with healing flag

This document serves as the single source of truth for detection algorithms and their performance characteristics.

## The Five Tiers

### Tier 1: Project Membership Detection (Highest Confidence)

**Mechanism**: Check if task belongs to entity's primary project.

**Confidence**: 100%

**Performance**: <1ms, O(1) lookup, zero API calls

**Algorithm**:
```python
def detect_tier1(task: Task) -> Optional[EntityType]:
    """
    Check task's project memberships against PRIMARY_PROJECT_GID registry.

    Target: 95% of detections via Tier 1.
    """
    project_gids = {p.gid for p in task.memberships}

    for entity_type in EntityType:
        if entity_type.PRIMARY_PROJECT_GID in project_gids:
            return entity_type

    return None  # Fall through to Tier 2
```

**Example**:
```python
# Task belongs to Business primary project
task.memberships = [Membership(project={"gid": "123456789"})]

# Business entity defines PRIMARY_PROJECT_GID
class Business(Task):
    PRIMARY_PROJECT_GID: ClassVar[str] = "123456789"

# Detection result
result = detect_tier1(task)  # EntityType.BUSINESS
```

**Optimization**: Project membership is included in standard task fetch, no extra API call required.

**References**:
- [TDD-DETECTION](../design/TDD-DETECTION.md)
- [ADR-0093: Project Membership Detection](../decisions/ADR-0093-project-membership-detection.md)

---

### Tier 2: Name Pattern Detection (High Confidence)

**Mechanism**: Regex matching on task name.

**Confidence**: 70-80% (varies by pattern quality)

**Performance**: <5ms, O(1) regex match, zero API calls

**Algorithm**:
```python
import re

# Entity-specific name patterns
NAME_PATTERNS = {
    EntityType.BUSINESS: re.compile(r"^BUSINESS:", re.IGNORECASE),
    EntityType.CONTACT: re.compile(r"^CONTACT:", re.IGNORECASE),
    EntityType.UNIT: re.compile(r"^UNIT:", re.IGNORECASE),
    EntityType.OFFER: re.compile(r"^OFFER:", re.IGNORECASE),
}

def detect_tier2(task: Task) -> Optional[EntityType]:
    """
    Match task name against entity name patterns.

    Fallback when project membership is missing or ambiguous.
    """
    for entity_type, pattern in NAME_PATTERNS.items():
        if pattern.match(task.name):
            return entity_type

    return None  # Fall through to Tier 3
```

**Example**:
```python
# Task with name prefix
task.name = "BUSINESS: Acme Corp"

# Detection result
result = detect_tier2(task)  # EntityType.BUSINESS
```

**Limitations**:
- Requires consistent naming conventions
- Fails if users rename tasks
- Lower confidence than Tier 1

**When Used**: Fallback when project membership is missing (needs healing).

---

### Tier 3: Parent Context Detection (Medium Confidence)

**Mechanism**: Infer type from parent task type.

**Confidence**: 50-60% (depends on parent type)

**Performance**: <10ms, O(1) parent lookup, may require parent fetch

**Algorithm**:
```python
# Parent-child type relationships
PARENT_CHILD_TYPES = {
    EntityType.BUSINESS: {EntityType.CONTACT, EntityType.UNIT, EntityType.LOCATION},
    EntityType.UNIT: {EntityType.OFFER, EntityType.PROCESS},
}

def detect_tier3(task: Task, client: AsyncClient) -> Optional[EntityType]:
    """
    Infer entity type from parent task type.

    Requires parent fetch if not already loaded.
    """
    if not task.parent:
        return None  # No parent, cannot infer

    # Fetch parent if needed
    parent = await client.tasks.get_task(task.parent.gid)
    parent_type = detect_entity_type(parent)  # Recursive detection

    # Check if task name lacks entity prefix (heuristic for child type)
    if not any(pattern.match(task.name) for pattern in NAME_PATTERNS.values()):
        # Infer child type based on parent
        possible_types = PARENT_CHILD_TYPES.get(parent_type, set())

        if len(possible_types) == 1:
            return list(possible_types)[0]

        # Ambiguous: multiple possible child types
        # Could use additional heuristics (custom fields, name keywords)

    return None  # Fall through to Tier 4
```

**Example**:
```python
# Parent is Business, task has no prefix
parent.name = "BUSINESS: Acme"
task.name = "John Doe"  # No prefix, ambiguous
task.parent = parent

# Heuristic: if no prefix and parent is Business, could be Contact or Unit
# Tier 3 may return None (ambiguous) → fall through to Tier 4
```

**Performance Consideration**: May require parent fetch (1 API call).

---

### Tier 4: Structure Inspection (Low Confidence)

**Mechanism**: Async examination of subtask structure.

**Confidence**: 40-50% (depends on structure completeness)

**Performance**: Variable, requires async subtask fetch

**Algorithm**:
```python
async def detect_tier4_async(task: Task, client: AsyncClient) -> Optional[EntityType]:
    """
    Inspect subtask structure to infer entity type.

    Example: Business has specific holder structure (Contacts, Units, etc.)
    """
    # Fetch subtasks
    subtasks = await client.tasks.get_subtasks(task.gid)

    # Check for Business holder pattern
    holder_sections = {st.name for st in subtasks}

    if "Contacts" in holder_sections and "Units" in holder_sections:
        return EntityType.BUSINESS

    # Check for Unit holder pattern
    if "Offers" in holder_sections and "Processes" in holder_sections:
        return EntityType.UNIT

    return None  # Fall through to Tier 5
```

**Example**:
```python
# Task has subtasks matching Business structure
task.subtasks = [
    Task(name="Contacts"),
    Task(name="Units"),
    Task(name="Location"),
]

# Detection result
result = await detect_tier4_async(task, client)  # EntityType.BUSINESS
```

**Performance Consideration**: Requires 1 API call to fetch subtasks. Use sparingly.

**When Used**: Last resort before UNKNOWN, async context only.

---

### Tier 5: Unknown (Fallback)

**Mechanism**: Return UNKNOWN with healing flag.

**Confidence**: 0% (explicit unknown)

**Performance**: <1ms

**Algorithm**:
```python
def detect_tier5(task: Task) -> DetectionResult:
    """
    Return UNKNOWN with needs_healing=True.

    Signals that task should be added to primary project for future Tier 1 detection.
    """
    return DetectionResult(
        entity_type=EntityType.UNKNOWN,
        tier_used=5,
        needs_healing=True,
        expected_project=None,  # Cannot determine
    )
```

**Self-Healing Integration**:
```python
# Detection returns UNKNOWN with healing flag
result = detect_entity_type(task)

if result.needs_healing:
    async with SaveSession(client, auto_heal=True) as session:
        # Task automatically added to primary project during commit
        # (if explicit_type provided to track())
        await session.track(task, explicit_type=EntityType.BUSINESS)
        await session.commit()

    # Future detection will succeed via Tier 1
    result = detect_entity_type(task)  # Now succeeds
```

---

## Detection Functions

### Synchronous Detection (Tiers 1-3)

```python
def detect_entity_type(task: Task) -> DetectionResult:
    """
    Synchronous entity type detection using Tiers 1-3.

    Use this for:
    - Fast detection in sync contexts
    - When async is not available
    - When Tier 1-2 coverage is expected

    Returns:
        DetectionResult with entity_type, tier_used, needs_healing
    """
    # Tier 1: Project membership (target: 95% coverage)
    if result := detect_tier1(task):
        return DetectionResult(
            entity_type=result,
            tier_used=1,
            needs_healing=False,
        )

    # Tier 2: Name pattern
    if result := detect_tier2(task):
        return DetectionResult(
            entity_type=result,
            tier_used=2,
            needs_healing=True,  # Missing project membership
            expected_project=result.PRIMARY_PROJECT_GID,
        )

    # Tier 3: Parent context (synchronous, may fail if parent not loaded)
    if task.parent and task.parent.resource_type == "task":
        parent_result = detect_entity_type(task.parent)
        if inferred := infer_from_parent(task, parent_result.entity_type):
            return DetectionResult(
                entity_type=inferred,
                tier_used=3,
                needs_healing=True,
                expected_project=inferred.PRIMARY_PROJECT_GID,
            )

    # Tier 5: Unknown (skip Tier 4 in sync context)
    return detect_tier5(task)
```

### Asynchronous Detection (Tiers 1-5)

```python
async def detect_entity_type_async(
    task: Task,
    client: AsyncClient,
) -> DetectionResult:
    """
    Asynchronous entity type detection using all 5 tiers.

    Use this for:
    - Maximum detection accuracy
    - When async context is available
    - When Tier 4 structure inspection is acceptable

    Returns:
        DetectionResult with entity_type, tier_used, needs_healing
    """
    # Tiers 1-3: Same as synchronous
    sync_result = detect_entity_type(task)

    if sync_result.entity_type != EntityType.UNKNOWN:
        return sync_result

    # Tier 4: Structure inspection (async)
    if result := await detect_tier4_async(task, client):
        return DetectionResult(
            entity_type=result,
            tier_used=4,
            needs_healing=True,
            expected_project=result.PRIMARY_PROJECT_GID,
        )

    # Tier 5: Unknown
    return detect_tier5(task)
```

---

## Detection Result

```python
@dataclass
class DetectionResult:
    """
    Structured result from entity type detection.

    Attributes:
        entity_type: Detected entity type (or UNKNOWN)
        tier_used: Which tier succeeded (1-5)
        needs_healing: True if task missing project membership
        expected_project: Primary project GID for healing (if applicable)
    """
    entity_type: EntityType
    tier_used: int
    needs_healing: bool
    expected_project: Optional[str] = None

    @property
    def is_confident(self) -> bool:
        """High confidence if Tier 1 or 2."""
        return self.tier_used in (1, 2)

    @property
    def requires_async(self) -> bool:
        """True if Tier 4 was used (async structure inspection)."""
        return self.tier_used == 4
```

---

## Performance Characteristics

### Target Distribution

| Tier | Target % | Actual % (Goal) | Performance | API Calls |
|------|----------|-----------------|-------------|-----------|
| Tier 1 | 95% | 95%+ | <1ms | 0 |
| Tier 2 | 4% | <5% | <5ms | 0 |
| Tier 3 | 1% | <2% | <10ms | 0-1 (parent fetch) |
| Tier 4 | <1% | <1% | Variable | 1 (subtask fetch) |
| Tier 5 | <1% | <1% | <1ms | 0 |

### Optimization Strategies

**Maximize Tier 1 Coverage**:
1. Ensure all entities define `PRIMARY_PROJECT_GID`
2. Use auto-heal to add tasks to primary project
3. Validate project membership on entity creation

**Minimize Tier 3-4 Usage**:
- Tier 3 may require parent fetch (1 API call)
- Tier 4 requires subtask fetch (1 API call)
- Use sparingly, prefer Tier 1-2

**Auto-Healing**:
```python
# Heal Tier 2-5 detections by adding to primary project
async with SaveSession(client, auto_heal=True) as session:
    result = detect_entity_type(task)

    if result.needs_healing:
        # track() with explicit type triggers healing
        await session.track(task, explicit_type=result.entity_type)
        await session.commit()  # Adds task to primary project

# Future detection now succeeds via Tier 1
```

---

## Common Patterns

### Pattern: Detect Before Casting

```python
# Detect entity type before casting to specific model
task = await client.tasks.get_task(task_gid)

result = detect_entity_type(task)

if result.entity_type == EntityType.BUSINESS:
    business = await client.get_business(task.gid)
elif result.entity_type == EntityType.CONTACT:
    contact = await client.get_contact(task.gid)
else:
    raise UnknownEntityTypeError(task.gid)
```

### Pattern: Batch Detection

```python
# Detect types for multiple tasks
tasks = await client.batch_get_tasks(gids)

detections = {
    task.gid: detect_entity_type(task)
    for task in tasks
}

# Group by entity type
businesses = [t for t, r in detections.items() if r.entity_type == EntityType.BUSINESS]
contacts = [t for t, r in detections.items() if r.entity_type == EntityType.CONTACT]
```

### Pattern: Healing Workflow

```python
# Detect and heal in single operation
result = detect_entity_type(task)

if result.needs_healing:
    async with SaveSession(client, auto_heal=True) as session:
        await session.track(task, explicit_type=result.entity_type)
        await session.commit()

    # Verify healing succeeded
    result_after = detect_entity_type(task)
    assert result_after.tier_used == 1
    assert not result_after.needs_healing
```

---

## Anti-Patterns

### Anti-Pattern: Assuming Entity Type

```python
# ❌ BAD: Assume task is Business without detection
task = await client.tasks.get_task(gid)
business = Business(**task.dict())  # May not be a Business!
```

**Do This Instead**:
```python
# ✓ GOOD: Detect before casting
task = await client.tasks.get_task(gid)
result = detect_entity_type(task)

if result.entity_type == EntityType.BUSINESS:
    business = await client.get_business(task.gid)
else:
    raise TypeError(f"Expected Business, got {result.entity_type}")
```

### Anti-Pattern: Ignoring Healing Opportunities

```python
# ❌ BAD: Ignore needs_healing flag
result = detect_entity_type(task)
# Continue without healing, future detections will be slow
```

**Do This Instead**:
```python
# ✓ GOOD: Heal when possible
result = detect_entity_type(task)

if result.needs_healing and result.entity_type != EntityType.UNKNOWN:
    await heal_task(task, result.entity_type)
```

---

## Testing Recommendations

### Unit Tests

```python
def test_tier1_project_membership():
    task = Task(
        gid="123",
        name="Test",
        memberships=[Membership(project={"gid": Business.PRIMARY_PROJECT_GID})]
    )

    result = detect_entity_type(task)

    assert result.entity_type == EntityType.BUSINESS
    assert result.tier_used == 1
    assert not result.needs_healing

def test_tier2_name_pattern():
    task = Task(gid="123", name="BUSINESS: Acme", memberships=[])

    result = detect_entity_type(task)

    assert result.entity_type == EntityType.BUSINESS
    assert result.tier_used == 2
    assert result.needs_healing
```

### Integration Tests

```python
async def test_detection_with_real_api(async_client):
    # Create business in Asana
    business = await async_client.tasks.create_task({
        "name": "BUSINESS: Test",
        "projects": [Business.PRIMARY_PROJECT_GID],
    })

    # Detect should succeed via Tier 1
    result = detect_entity_type(business)

    assert result.entity_type == EntityType.BUSINESS
    assert result.tier_used == 1
```

---

## See Also

- [REF-entity-lifecycle.md](./REF-entity-lifecycle.md) - Complete entity lifecycle (phase 2: Detect)
- [TDD-DETECTION](../design/TDD-DETECTION.md) - Full detection system design
- [ADR-0093: Project Membership Detection](../decisions/ADR-0093-project-membership-detection.md)
- [ADR-0094: Detection Tier Fallback Strategy](../decisions/ADR-0094-detection-tier-fallback.md)
