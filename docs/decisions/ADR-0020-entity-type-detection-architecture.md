# ADR-0020: Entity Type Detection Architecture

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: SDK Team
- **Consolidated From**: ADR-0068, ADR-0094, ADR-0135
- **Related**: [reference/DETECTION.md](reference/DETECTION.md), PRD-DETECTION, TDD-DETECTION

## Context

Entity type detection enables the SDK to automatically determine entity types (Business, Unit, Contact, Offer, etc.) from Asana tasks without requiring explicit configuration. This capability is critical for two primary scenarios:

1. **Upward hierarchy traversal during hydration**: When loading a business model hierarchy from an arbitrary entry point (e.g., Contact, Offer), each parent task fetched via `Task.parent.gid` must be typed correctly to build the Business model structure.

2. **Orphaned entity recovery**: Entities missing project membership can still be identified through fallback strategies.

The detection system must balance performance (most detections complete in <1ms with zero API calls) with accuracy (95%+ success rate) while handling:
- Healthy entities with correct project membership
- Decorated names with prefixes/suffixes ([URGENT], >>, (Primary))
- Variable entity names (Business: "Acme Corp", Unit: "Premium Package")
- Container tasks with no business data (holders)

### Design Challenges

1. **Performance requirements**: Detection is in the critical path; slow detection compounds during multi-level hydration
2. **API call cost**: Structure inspection (fetching subtasks) adds ~200ms latency
3. **Naming variability**: Business/Unit have variable names; holders may be decorated
4. **Confidence levels**: Different detection strategies have different accuracy guarantees
5. **Extensibility**: Must support adding new entity types without major refactoring

## Decision

We will implement a **five-tier sequential fallback chain** with **strict ordering**, **early return**, and **structured confidence levels**:

### Tier Architecture

```
Tier 1: Project Membership Lookup (O(1), deterministic, 100% confidence)
  ↓ (if fails)
Tier 2: Name Pattern Matching (O(1), heuristic, 60% confidence)
  ↓ (if fails)
Tier 3: Parent-Child Type Inference (O(1), structural, 80% confidence)
  ↓ (if fails)
Tier 4: Structure Inspection via API (~200ms, deterministic, 95% confidence, opt-in)
  ↓ (if fails)
Tier 5: UNKNOWN Fallback
```

**Synchronous path** (Tiers 1-3): Zero API calls, <1ms latency
**Async path** (Tiers 1-4): Opt-in Tier 4 via `allow_structure_inspection=True`

### Implementation Pattern

```python
def detect_entity_type(
    task: Task,
    parent_type: EntityType | None = None,
) -> DetectionResult:
    """Synchronous detection (Tiers 1-3)."""

    # Tier 1: Project membership
    result = _detect_by_project(task)
    if result:
        return result

    # Tier 2: Name patterns
    result = _detect_by_name(task)
    if result:
        return result

    # Tier 3: Parent inference
    if parent_type:
        result = _detect_by_parent(task, parent_type)
        if result:
            return result

    # Tier 5: Unknown (skip Tier 4 in sync path)
    return _make_unknown_result(task)


async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Async detection (Tiers 1-5)."""

    # Tiers 1-3 (sync)
    result = detect_entity_type(task, parent_type)
    if result or not allow_structure_inspection:
        return result

    # Tier 4: Structure inspection (async, opt-in)
    result = await _detect_by_structure_async(task, client)
    if result:
        return result

    # Tier 5: Unknown
    return _make_unknown_result(task)
```

### Result Structure

```python
@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Outcome of entity type detection."""
    entity_type: EntityType
    confidence: float  # 0.0 to 1.0
    tier_used: int  # 1-5
    needs_healing: bool  # True if detected via Tiers 2-5
    expected_project_gid: str | None  # For self-healing

    def __bool__(self) -> bool:
        """False only for UNKNOWN type."""
        return self.entity_type != EntityType.UNKNOWN
```

### Tier 1: Project Membership Lookup

**Strategy**: Check task's project memberships against `ProjectTypeRegistry`

**Characteristics**:
- O(1) lookup via dictionary
- 100% confidence (deterministic)
- Requires correct project membership
- Supports dynamic project discovery via `WorkspaceProjectRegistry`

**Implementation**:
```python
def _detect_by_project(task: Task) -> DetectionResult | None:
    """Tier 1: Project membership lookup."""
    if not task.memberships:
        return None

    project_gid = task.memberships[0].project.gid
    entity_type = get_registry().lookup(project_gid)

    if entity_type is None:
        return None

    return DetectionResult(
        entity_type=entity_type,
        confidence=1.0,
        tier_used=1,
        needs_healing=False,
        expected_project_gid=project_gid,
    )
```

### Tier 2: Name Pattern Matching

**Strategy**: Match task name against known patterns (see ADR-0021 for details)

**Characteristics**:
- O(1) string operations with cached regex
- 60% confidence (heuristic)
- Handles decorated names via stripping
- Supports singular/plural forms

**Use cases**: Holder entities ("Contacts", "Offers", "Processes")

### Tier 3: Parent-Child Type Inference

**Strategy**: Infer child type from parent type via `PARENT_CHILD_MAP`

**Characteristics**:
- O(1) dictionary lookup
- 80% confidence (structural relationships are reliable)
- Requires `parent_type` parameter
- Ideal for upward hydration where parent is already typed

**Example mapping**:
```python
PARENT_CHILD_MAP = {
    EntityType.CONTACT_HOLDER: EntityType.CONTACT,
    EntityType.OFFER_HOLDER: EntityType.OFFER,
    EntityType.UNIT: {
        # Disambiguation by name
        "offers": EntityType.OFFER_HOLDER,
        "processes": EntityType.PROCESS_HOLDER,
    },
}
```

### Tier 4: Structure Inspection

**Strategy**: Fetch subtasks and examine their names for holder indicators

**Characteristics**:
- ~200ms latency (API call required)
- 95% confidence (nearly deterministic)
- Opt-in via `allow_structure_inspection=True`
- Only available in async path

**Detection logic**:
```python
async def _detect_by_structure_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 4: Structure inspection."""
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    business_indicators = {"contacts", "units", "location"}
    if subtask_names & business_indicators:
        return _make_result(EntityType.BUSINESS, tier=4)

    # Unit has offer/process holder subtasks
    unit_indicators = {"offers", "processes"}
    if subtask_names & unit_indicators:
        return _make_result(EntityType.UNIT, tier=4)

    return None
```

### Tier 5: UNKNOWN Fallback

**Strategy**: Return UNKNOWN when all tiers fail

**Characteristics**:
- 0% confidence
- Entity can still be tracked but operations may be limited
- Indicates manual intervention or additional metadata needed

### Special Case: ProcessHolder Detection

ProcessHolder intentionally has `PRIMARY_PROJECT_GID = None` because:
1. It is purely structural with no custom fields or business data
2. Team does not manage holders in project views
3. Tier 2 (name pattern "processes") is reliable
4. Tier 3 (child of Unit) provides high-confidence fallback

Creating a project solely for detection would add operational overhead without business value.

## Rationale

### Why Sequential If-Else Over Chain of Responsibility?

| Criterion | Chain of Responsibility | Sequential If-Else |
|-----------|------------------------|-------------------|
| Code complexity | High (class per tier) | Low (function per tier) |
| Debuggability | Hard (chain traversal) | Easy (linear flow) |
| Performance | Runtime chain overhead | Zero overhead |
| Extensibility | Easy (add handler) | Moderate (add tier) |

**Sequential if-else wins** because:
- Only 5 tiers; pattern overhead unjustified
- Explicit flow easier to understand and debug
- No runtime construction cost
- Each tier is a simple function, not a class

### Why Frozen Dataclass Over Pydantic Model?

- **Performance**: DetectionResult constructed frequently; dataclass is ~10x faster
- **Immutability**: Frozen ensures result cannot be accidentally modified
- **Simplicity**: No validation needed (values come from controlled code paths)
- **Memory**: Slots reduce memory footprint

### Why Separate Sync and Async Functions?

- **Performance**: 80%+ of detections succeed in Tiers 1-3 (sync path)
- **Clear contract**: Sync = zero API calls, Async = may call API
- **Ergonomics**: Sync callers don't need to await for fast path
- **Opt-in safety**: Tier 4 requires explicit `allow_structure_inspection=True`

### Why Tier Ordering Matters

Order prioritizes **speed and reliability**:
1. **Tier 1 first**: Deterministic and O(1) - always try first
2. **Tier 2 before Tier 3**: Name patterns work without parent context
3. **Tier 3 before Tier 4**: Avoid API call when parent provides strong signal
4. **Tier 4 last**: Most expensive operation, try all cheaper options first

## Alternatives Considered

### Alternative A: Single Async Function with Tier Flags

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    enable_tier_4: bool = False,
)
```

**Why not chosen**: Forces all callers to be async even for Tier 1-3 fast path

### Alternative B: Strategy Pattern with Runtime Selection

**Why not chosen**: Strategy implies selecting one approach; we need ordered fallback

### Alternative C: GID-to-Type Registry Cache

**Why not chosen**: Doesn't solve initial detection problem; adds staleness complexity

### Alternative D: Custom Field Type Marker

**Why not chosen**: Requires data migration across all existing tasks; uses custom field slot

## Consequences

### Positive

- **Fast path optimization**: 80%+ of detections complete in <1ms without API calls
- **Observable**: `tier_used` enables metrics on detection path distribution
- **Type-safe**: Consistent return type with `__bool__` for truthy checks
- **Debuggable**: Linear flow with clear tier boundaries
- **Extensible**: Can add Tier 6+ if needed (unlikely)
- **Self-healing ready**: `needs_healing` flag enables automatic repair

### Negative

- **Hardcoded tier order**: Adding new tiers requires code change (acceptable; order is semantic)
- **Duplicate sync logic**: Async function calls sync function then continues (minor DRY violation)
- **Tier 4 opt-in burden**: Callers must know when structure inspection is beneficial

### Neutral

- Detection logic centralized in `detection/` package
- Compatible with existing function signatures via overloads
- No changes to entity model structure

## Compliance

How do we ensure this decision is followed?

1. **Sync function MUST NOT make API calls** - verified by unit tests
2. **Async function MUST only call API when `allow_structure_inspection=True`** - verified by mocking
3. **Tiers MUST be tried in order 1→2→3→4→5** - verified by result tier_used
4. **DetectionResult.tier_used MUST be logged** - enables observability metrics
5. **Each tier MUST have isolated unit tests** - verify tier-specific behavior
6. **Integration tests MUST cover full chain** - verify early return and fallback

## Implementation Notes

**When to use which tier**:

- **Tier 1**: Preferred for all entities with correct project membership
- **Tier 2**: Fallback for holder entities with decorated names
- **Tier 3**: Ideal for upward hydration where parent is already typed
- **Tier 4**: Last resort for Business/Unit with variable names
- **Tier 5**: Indicates need for manual intervention or metadata

**Performance considerations**:

- Tiers 1-3 must complete without API calls
- Regex patterns compiled with `lru_cache`
- Discovery triggered on first unknown GID (not at startup)
- Cache detection results only for Tier 4 (see ADR-0023)

**Error handling**:

```python
result = await detect_entity_type_async(task, client, allow_structure_inspection=True)

if result.entity_type == EntityType.UNKNOWN:
    logger.warning(
        "Could not detect type",
        task_gid=task.gid,
        tier_used=result.tier_used,
        name=task.name,
    )
    # Fallback: prompt user or use default type
```
