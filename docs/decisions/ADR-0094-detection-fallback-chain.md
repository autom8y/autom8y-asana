# ADR-0094: Detection Fallback Chain Design

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-DETECTION, TDD-DETECTION, ADR-0068 (superseded), ADR-0093

## Context

Entity type detection must handle multiple scenarios with different data availability:

1. **Healthy entities**: Have correct project membership (Tier 1)
2. **Entities with decorated names**: Project missing but name contains type keywords (Tier 2)
3. **Child entities with known parents**: Type inferable from parent type (Tier 3)
4. **Entities with structure clues**: Subtask patterns indicate type (Tier 4, requires API)
5. **Unknown entities**: Cannot determine type (Tier 5)

**Key design questions:**

1. **Pattern choice**: Chain of Responsibility vs simple if-else vs strategy pattern?
2. **Short-circuit behavior**: How to exit early when a tier succeeds?
3. **Result structure**: What information does each tier provide?
4. **Async handling**: How to handle Tier 4 which requires API calls?

### Forces

1. **Performance**: Most detections should complete in Tier 1 (<1ms)
2. **Simplicity**: Detection logic should be easy to understand and debug
3. **Extensibility**: Should be possible to add new tiers without major refactoring
4. **Type safety**: Return type should be consistent across all paths
5. **Observability**: Must know which tier succeeded for metrics/debugging
6. **Zero API calls**: Tiers 1-3 must not require network calls

## Decision

We will implement a **simple sequential if-else chain with early return** pattern, using a **frozen dataclass** for results, with **Tier 4 gated behind an async flag**.

### Pattern: Sequential If-Else with Early Return

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

    # Tier 4: Structure inspection (async)
    result = await _detect_by_structure_async(task, client)
    if result:
        return result

    # Tier 5: Unknown
    return _make_unknown_result(task)
```

### Result Structure: Frozen Dataclass

```python
@dataclass(frozen=True, slots=True)
class DetectionResult:
    entity_type: EntityType
    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None

    def __bool__(self) -> bool:
        return self.entity_type != EntityType.UNKNOWN
```

**Why frozen dataclass?**
- Immutable: result cannot be accidentally modified
- Lightweight: no Pydantic validation overhead
- Slots: memory-efficient
- `__bool__`: enables `if result:` pattern for truthy UNKNOWN handling

### Tier Implementations

Each tier function returns `DetectionResult | None`:
- `None`: tier cannot determine type, continue to next
- `DetectionResult`: tier succeeded, return immediately

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
        tier_used=1,
        needs_healing=False,
        expected_project_gid=project_gid,
    )


def _detect_by_name(task: Task) -> DetectionResult | None:
    """Tier 2: Name pattern matching."""
    if not task.name:
        return None

    name_lower = task.name.lower()

    # Contains-based matching (not exact)
    for pattern, entity_type in NAME_PATTERNS.items():
        if pattern in name_lower:
            expected_gid = get_registry().get_primary_gid(entity_type)
            return DetectionResult(
                entity_type=entity_type,
                tier_used=2,
                needs_healing=True,
                expected_project_gid=expected_gid,
            )

    return None


def _detect_by_parent(task: Task, parent_type: EntityType) -> DetectionResult | None:
    """Tier 3: Parent type inference."""
    inferred = PARENT_CHILD_MAP.get(parent_type)
    if inferred is None:
        return None

    # Handle parent types that need name disambiguation
    if isinstance(inferred, dict):
        inferred = _disambiguate_by_name(task.name, inferred)
        if inferred is None:
            return None

    expected_gid = get_registry().get_primary_gid(inferred)
    return DetectionResult(
        entity_type=inferred,
        tier_used=3,
        needs_healing=True,
        expected_project_gid=expected_gid,
    )
```

### Async Gate for Tier 4

Tier 4 is disabled by default because it requires an API call:

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,  # Default: disabled
) -> DetectionResult:
```

Consumer must explicitly opt-in to structure inspection when they expect sync tiers to fail and are willing to pay the API cost.

## Rationale

**Why sequential if-else over Chain of Responsibility?**
- Only 5 tiers; CoR adds complexity without benefit
- Explicit flow is easier to debug
- No runtime chain construction overhead
- Each tier is a simple function, not a class

**Why not Strategy Pattern?**
- Strategy implies selecting one approach; we need ordered fallback
- Would require additional orchestrator to try strategies in sequence
- Overkill for fixed, small number of tiers

**Why frozen dataclass over Pydantic model?**
- DetectionResult is a simple data container, not a model with validation
- Pydantic overhead (~10x slower construction) unnecessary
- Frozen ensures immutability without Pydantic's `allow_mutation=False`
- Integration point with Pydantic models is at entity level, not detection

**Why `__bool__` returns False for UNKNOWN?**
- Enables natural `if result:` checks
- UNKNOWN is the only "falsy" result
- Consistent with Python's truthy/falsy conventions

**Why separate sync and async functions?**
- Sync function covers 80%+ of cases (Tiers 1-3)
- Async only needed when Tier 4 is desired
- Avoids forcing all callers to be async
- Clear API contract: sync = no API calls, async = may call API

## Alternatives Considered

### Alternative A: Chain of Responsibility Pattern

- **Description**: Each tier is a Handler class with `handle()` and `next` reference
- **Pros**: Classic pattern for fallback chains; easily extensible
- **Cons**: Heavyweight for 5 tiers; runtime chain construction; harder to debug
- **Why not chosen**: Simple if-else is sufficient and more explicit

### Alternative B: Single Async Function with Flags

- **Description**: One function `detect_entity_type_async(include_tier_4=False)`
- **Pros**: Single entry point
- **Cons**: Forces all callers to be async even for sync-capable tiers
- **Why not chosen**: Sync callers shouldn't need to await for Tier 1-3

### Alternative C: Pydantic Model for DetectionResult

- **Description**: `class DetectionResult(BaseModel): ...`
- **Pros**: Consistent with other SDK models; validation
- **Cons**: Validation overhead unnecessary; immutability harder; heavier
- **Why not chosen**: Dataclass is lighter and sufficient

### Alternative D: Return EntityType Directly (No Structured Result)

- **Description**: Functions return `EntityType | None`
- **Pros**: Simpler; matches legacy signature
- **Cons**: Loses tier/healing metadata; can't optimize healing; poor observability
- **Why not chosen**: Structured result enables self-healing and debugging

## Consequences

### Positive

- **Simple**: Clear sequential flow, easy to understand
- **Debuggable**: Can add breakpoints at any tier
- **Observable**: `tier_used` enables metrics on detection paths
- **Type-safe**: Consistent return type; `__bool__` for truthy checks
- **Performance**: Early return avoids unnecessary computation
- **Flexible async**: Tier 4 opt-in keeps sync path fast

### Negative

- **Hardcoded order**: Tier order is fixed in code (acceptable; order is semantic)
- **Duplicate sync logic**: Async function calls sync function then continues (minor)
- **Limited extensibility**: Adding Tier 6+ requires code change (unlikely scenario)

### Neutral

- Detection logic remains centralized in `detection.py`
- Compatible with existing function signatures via overloads
- No changes to entity model structure

## Compliance

- Detection functions MUST be in `src/autom8_asana/models/business/detection.py`
- Sync `detect_entity_type()` MUST NOT make API calls
- Async `detect_entity_type_async()` MUST only call API if `allow_structure_inspection=True`
- `DetectionResult.tier_used` MUST be logged for observability
- Tests MUST cover each tier in isolation and full chain
- `detect_by_name()` legacy function MUST emit `DeprecationWarning`
