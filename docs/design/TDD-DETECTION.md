# TDD: Membership-Based Entity Type Detection

## Metadata

- **TDD ID**: TDD-DETECTION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-17
- **PRD Reference**: [PRD-DETECTION](/docs/requirements/PRD-DETECTION.md)
- **Related TDDs**: TDD-BIZMODEL, TDD-HYDRATION
- **Related ADRs**: ADR-0068 (superseded), ADR-0093, ADR-0094, ADR-0095

## Overview

This design replaces the broken name-based entity type detection system with a deterministic project-membership detection approach. The system uses a tiered fallback chain: Tier 1 (project membership) provides O(1) detection with zero API calls; Tiers 2-3 provide synchronous fallbacks; Tier 4 offers optional async structure inspection; Tier 5 returns UNKNOWN with a healing flag. Self-healing integration with SaveSession enables automatic repair of entities missing project membership.

## Requirements Summary

**From PRD-DETECTION**: 28 requirements across 4 categories:

| Category | Must | Should | Could | Total |
|----------|------|--------|-------|-------|
| Registry (FR-REG-*) | 5 | 1 | 0 | 6 |
| Detection (FR-DET-*) | 4 | 4 | 1 | 9 |
| Self-Healing (FR-HEAL-*) | 1 | 3 | 0 | 4 |
| Configuration (FR-CFG-*) | 1 | 0 | 1 | 2 |
| Compatibility (FR-COMPAT-*) | 1 | 1 | 0 | 2 |
| NFRs | 5 | 0 | 0 | 5 |

**Key Requirements**:
- FR-REG-001: O(1) registry lookup
- FR-DET-002: Tier 1 project membership detection
- FR-HEAL-001: `needs_healing` flag in detection result
- NFR-PERF-001: Tier 1 detection <1ms

## System Context

```
                              ┌─────────────────────────────────────────────────────┐
                              │                   SDK Consumers                      │
                              │  (Webhooks, Hydration, Direct Usage)                │
                              └─────────────────────┬───────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Detection System                                        │
│                                                                                      │
│  ┌──────────────────┐    ┌──────────────────────────────────────────────────────┐  │
│  │ ProjectTypeRegistry│◄───│                detect_entity_type()                  │  │
│  │                    │    │                                                      │  │
│  │ project_gid →     │    │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐     │  │
│  │    EntityType     │    │  │ Tier 1 │→ │ Tier 2 │→ │ Tier 3 │→ │ Tier 4 │→ T5 │  │
│  │                    │    │  │Project │  │ Name   │  │ Parent │  │Structure│     │  │
│  └────────┬───────────┘    │  └────────┘  └────────┘  └────────┘  └────────┘     │  │
│           │                └──────────────────────────────────────────────────────┘  │
│           │                                          │                               │
│           │ __init_subclass__                        ▼                               │
│           ▼                              ┌───────────────────────┐                   │
│  ┌────────────────────┐                  │   DetectionResult     │                   │
│  │  BusinessEntity    │                  │   - entity_type       │                   │
│  │  subclasses        │                  │   - tier_used         │                   │
│  │                    │                  │   - needs_healing     │                   │
│  │  PRIMARY_PROJECT_GID                  │   - expected_project  │                   │
│  └────────────────────┘                  └───────────┬───────────┘                   │
│                                                      │                               │
└──────────────────────────────────────────────────────┼───────────────────────────────┘
                                                       │
                                                       ▼
                              ┌─────────────────────────────────────────────────────┐
                              │                    SaveSession                       │
                              │    (auto_heal=True triggers add_to_project)         │
                              └─────────────────────────────────────────────────────┘
```

## Design

### Component Architecture

```
src/autom8_asana/models/business/
├── detection.py      # Detection functions + DetectionResult + EntityType
├── registry.py       # NEW: ProjectTypeRegistry singleton
└── base.py           # BusinessEntity.__init_subclass__ hook

src/autom8_asana/persistence/
└── session.py        # SaveSession.auto_heal integration
```

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `ProjectTypeRegistry` | Maps project GIDs to EntityType; provides O(1) lookup | `registry.py` |
| `DetectionResult` | Structured result with type, tier, healing info | `detection.py` |
| `detect_entity_type()` | Synchronous detection (Tiers 1-3) | `detection.py` |
| `detect_entity_type_async()` | Async detection (Tiers 1-5) | `detection.py` |
| `BusinessEntity.__init_subclass__` | Auto-registers entities with registry | `base.py` |
| `SaveSession.auto_heal` | Triggers healing operations on commit | `session.py` |

### Data Model

#### DetectionResult

```python
from dataclasses import dataclass
from autom8_asana.models.business.detection import EntityType

@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Result of entity type detection.

    Per FR-DET-001: Structured result with type, tier, and healing info.

    Attributes:
        entity_type: Detected type or EntityType.UNKNOWN
        tier_used: Which detection tier succeeded (1-5)
        needs_healing: True if entity lacks expected project membership
        expected_project_gid: GID entity should have for Tier 1 detection
    """
    entity_type: EntityType
    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None

    def __bool__(self) -> bool:
        """Return False for UNKNOWN, True otherwise."""
        return self.entity_type != EntityType.UNKNOWN

    @property
    def is_deterministic(self) -> bool:
        """True if detected via project membership (Tier 1)."""
        return self.tier_used == 1
```

#### ProjectTypeRegistry

```python
from typing import ClassVar
from autom8_asana.models.business.detection import EntityType

class ProjectTypeRegistry:
    """Singleton registry mapping project GIDs to EntityType.

    Per FR-REG-001: O(1) lookup via dict.
    Per ADR-0093: Module-level singleton with test reset capability.

    The registry is populated automatically via BusinessEntity.__init_subclass__
    when entity classes are imported. Process project GIDs are registered
    separately via _register_process_projects().
    """

    _instance: ClassVar[ProjectTypeRegistry | None] = None
    _gid_to_type: dict[str, EntityType]
    _type_to_gid: dict[EntityType, str]
    _initialized: bool

    def __new__(cls) -> ProjectTypeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._gid_to_type = {}
            cls._instance._type_to_gid = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, project_gid: str, entity_type: EntityType) -> None:
        """Register a project GID to EntityType mapping.

        Per FR-REG-003: Called by __init_subclass__ for each entity.
        Per FR-REG-005: Raises ValueError on duplicate GID.

        Args:
            project_gid: Asana project GID
            entity_type: EntityType this project represents

        Raises:
            ValueError: If project_gid already registered to different type
        """
        if project_gid in self._gid_to_type:
            existing = self._gid_to_type[project_gid]
            if existing != entity_type:
                raise ValueError(
                    f"Project GID {project_gid} already registered to "
                    f"{existing.name}, cannot register to {entity_type.name}"
                )
            return  # Idempotent: same mapping already exists

        self._gid_to_type[project_gid] = entity_type
        # Only set type_to_gid if not already set (first registration wins)
        if entity_type not in self._type_to_gid:
            self._type_to_gid[entity_type] = project_gid

    def lookup(self, project_gid: str) -> EntityType | None:
        """Look up EntityType by project GID.

        Per FR-REG-001: O(1) dict lookup.

        Args:
            project_gid: Asana project GID

        Returns:
            EntityType if found, None otherwise
        """
        return self._gid_to_type.get(project_gid)

    def get_primary_gid(self, entity_type: EntityType) -> str | None:
        """Get primary project GID for an EntityType.

        Per FR-HEAL-001: Used to determine expected_project_gid for healing.

        Args:
            entity_type: The entity type

        Returns:
            Primary project GID if registered, None otherwise
        """
        return self._type_to_gid.get(entity_type)

    @classmethod
    def reset(cls) -> None:
        """Reset registry for testing.

        Per ADR-0093: Testing support via explicit reset.
        """
        cls._instance = None


# Module-level singleton accessor
def get_registry() -> ProjectTypeRegistry:
    """Get the ProjectTypeRegistry singleton."""
    return ProjectTypeRegistry()
```

#### Entity Class Updates

```python
# In base.py - BusinessEntity.__init_subclass__ enhancement

import os
from typing import ClassVar

class BusinessEntity(Task):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # ... existing ref discovery code ...

        # NEW: Register with ProjectTypeRegistry (ADR-0093)
        _register_entity_with_registry(cls)


def _register_entity_with_registry(cls: type) -> None:
    """Register entity class with ProjectTypeRegistry.

    Per FR-REG-003: Auto-population via __init_subclass__.
    Per FR-REG-004: Environment variable override.
    """
    from autom8_asana.models.business.registry import get_registry
    from autom8_asana.models.business.detection import EntityType

    # Derive entity type from class name
    entity_type = _class_name_to_entity_type(cls.__name__)
    if entity_type is None:
        return  # Not a known entity type

    # Get project GID (env var override, then class default)
    env_var = f"ASANA_PROJECT_{entity_type.name}"
    project_gid = os.environ.get(env_var) or getattr(cls, "PRIMARY_PROJECT_GID", None)

    if not project_gid:
        return  # No project GID for this entity (e.g., LocationHolder)

    # Skip empty env var values
    if project_gid.strip() == "":
        return

    registry = get_registry()
    registry.register(project_gid, entity_type)


def _class_name_to_entity_type(class_name: str) -> EntityType | None:
    """Convert class name to EntityType.

    Examples:
        Business -> EntityType.BUSINESS
        ContactHolder -> EntityType.CONTACT_HOLDER
        DNAHolder -> EntityType.DNA_HOLDER
    """
    from autom8_asana.models.business.detection import EntityType

    # Handle special cases
    SPECIAL_CASES = {
        "DNAHolder": "DNA_HOLDER",
        "ReconciliationHolder": "RECONCILIATIONS_HOLDER",
    }

    if class_name in SPECIAL_CASES:
        type_name = SPECIAL_CASES[class_name]
    else:
        # Convert CamelCase to UPPER_SNAKE_CASE
        import re
        type_name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).upper()

    try:
        return EntityType[type_name]
    except KeyError:
        return None
```

### API Contracts

#### Detection Functions

```python
from autom8_asana.models.task import Task
from autom8_asana.client import AsanaClient

def detect_entity_type(
    task: Task,
    parent_type: EntityType | None = None,
) -> DetectionResult:
    """Synchronous entity type detection (Tiers 1-3).

    Per FR-DET-007: Synchronous function for zero-API-call detection.

    Executes tiers in order, returning on first success:
    1. Project membership lookup (O(1), no API)
    2. Name pattern matching (string ops, no API)
    3. Parent type inference (logic only, no API)

    If all tiers fail, returns UNKNOWN with needs_healing=True.

    Args:
        task: Task to detect type for
        parent_type: Known parent type for Tier 3 inference

    Returns:
        DetectionResult with detected type and metadata
    """

async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Asynchronous entity type detection (Tiers 1-5).

    Per FR-DET-008: Async function with optional Tier 4.

    Executes synchronous tiers first, then optionally Tier 4:
    1-3. Same as detect_entity_type()
    4. Structure inspection (requires API call, disabled by default)
    5. UNKNOWN fallback

    Args:
        task: Task to detect type for
        client: AsanaClient for Tier 4 API calls
        parent_type: Known parent type for Tier 3 inference
        allow_structure_inspection: Enable Tier 4 (default: False)

    Returns:
        DetectionResult with detected type and metadata
    """

# Backward compatibility (FR-COMPAT-001)
def detect_by_name(name: str | None) -> EntityType | None:
    """Legacy name-based detection (emits DeprecationWarning).

    Per FR-COMPAT-002: Deprecated, use detect_entity_type() instead.
    """
```

#### SaveSession Healing Integration

```python
class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
        auto_heal: bool = False,  # NEW: FR-HEAL-002
    ) -> None:
        """Initialize save session.

        Args:
            client: AsanaClient instance
            batch_size: Maximum operations per batch
            max_concurrent: Maximum concurrent requests
            auto_heal: If True, add missing project memberships on commit
        """
        self._auto_heal = auto_heal
        self._healing_operations: list[HealingOperation] = []

    def track(
        self,
        entity: AsanaResource,
        heal: bool | None = None,  # NEW: FR-HEAL-002 per-entity override
    ) -> None:
        """Track entity for persistence.

        Args:
            entity: Entity to track
            heal: Override auto_heal for this entity (None = use session default)
        """


@dataclass
class HealingOperation:
    """Pending healing operation."""
    entity_gid: str
    expected_project_gid: str


@dataclass
class HealingFailure:
    """Failed healing operation."""
    entity_gid: str
    expected_project_gid: str
    error: Exception


@dataclass
class SaveResult:
    # ... existing fields ...

    # NEW: FR-HEAL-004
    healed_entities: list[str] = field(default_factory=list)
    healing_failures: list[HealingFailure] = field(default_factory=list)
```

### Data Flow

#### Detection Flow (Tiers 1-5)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          detect_entity_type_async()                          │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TIER 1: Project Membership                                                  │
│                                                                              │
│  task.memberships[0].project.gid                                             │
│           │                                                                  │
│           ▼                                                                  │
│  registry.lookup(project_gid)                                                │
│           │                                                                  │
│     ┌─────┴─────┐                                                            │
│     │           │                                                            │
│  Found       Not Found                                                       │
│     │           │                                                            │
│     ▼           ▼                                                            │
│  RETURN     Continue to Tier 2                                               │
│  (tier=1,   (needs_healing may be set)                                       │
│   healing=                                                                    │
│   False)                                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TIER 2: Name Pattern Matching                                               │
│                                                                              │
│  task.name.lower()                                                           │
│           │                                                                  │
│           ▼                                                                  │
│  Contains "contacts" → CONTACT_HOLDER                                        │
│  Contains "units"    → UNIT_HOLDER                                           │
│  Contains "offers"   → OFFER_HOLDER                                          │
│  Contains "processes"→ PROCESS_HOLDER                                        │
│  ... etc                                                                     │
│           │                                                                  │
│     ┌─────┴─────┐                                                            │
│  Matched     No Match                                                        │
│     │           │                                                            │
│     ▼           ▼                                                            │
│  RETURN     Continue to Tier 3                                               │
│  (tier=2,                                                                    │
│   healing=                                                                   │
│   True)                                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TIER 3: Parent Type Inference                                               │
│                                                                              │
│  parent_type provided?                                                       │
│           │                                                                  │
│     ┌─────┴─────┐                                                            │
│    Yes         No                                                            │
│     │           │                                                            │
│     ▼           ▼                                                            │
│  Infer type  Continue to Tier 4                                              │
│  from parent                                                                 │
│     │                                                                        │
│  parent=CONTACT_HOLDER → CONTACT                                             │
│  parent=UNIT_HOLDER    → UNIT                                                │
│  parent=OFFER_HOLDER   → OFFER                                               │
│  parent=BUSINESS       → infer by name                                       │
│  ... etc                                                                     │
│           │                                                                  │
│     ┌─────┴─────┐                                                            │
│  Inferred   Cannot Infer                                                     │
│     │           │                                                            │
│     ▼           ▼                                                            │
│  RETURN     Continue to Tier 4                                               │
│  (tier=3,                                                                    │
│   healing=                                                                   │
│   True)                                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TIER 4: Structure Inspection (ASYNC, optional)                              │
│                                                                              │
│  allow_structure_inspection?                                                 │
│           │                                                                  │
│     ┌─────┴─────┐                                                            │
│   True        False                                                          │
│     │           │                                                            │
│     ▼           ▼                                                            │
│  Fetch       Skip to Tier 5                                                  │
│  subtasks                                                                    │
│     │                                                                        │
│     ▼                                                                        │
│  subtask_names = {s.name.lower() for s in subtasks}                          │
│  {"contacts","units","location"} → BUSINESS                                  │
│  {"offers","processes"}          → UNIT                                      │
│           │                                                                  │
│     ┌─────┴─────┐                                                            │
│  Detected   No Match                                                         │
│     │           │                                                            │
│     ▼           ▼                                                            │
│  RETURN     Continue to Tier 5                                               │
│  (tier=4,                                                                    │
│   healing=                                                                   │
│   True)                                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  TIER 5: Unknown Fallback                                                    │
│                                                                              │
│  Log warning: "Unable to detect type for task {gid}"                         │
│                                                                              │
│  RETURN DetectionResult(                                                     │
│      entity_type=EntityType.UNKNOWN,                                         │
│      tier_used=5,                                                            │
│      needs_healing=True,                                                     │
│      expected_project_gid=None                                               │
│  )                                                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### Self-Healing Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     SaveSession.commit_async()                               │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  For each tracked entity where heal=True:                                    │
│                                                                              │
│  1. Get entity's detection result (if BusinessEntity)                        │
│  2. If needs_healing=True and expected_project_gid:                          │
│     → Create HealingOperation(entity.gid, expected_project_gid)              │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Execute normal save operations                                              │
│  (CREATE, UPDATE, DELETE via batch API)                                      │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Execute healing operations via add_to_project action:                       │
│                                                                              │
│  for healing_op in healing_operations:                                       │
│      try:                                                                    │
│          await client.tasks.add_to_project_async(                            │
│              healing_op.entity_gid,                                          │
│              project_gid=healing_op.expected_project_gid                     │
│          )                                                                   │
│          result.healed_entities.append(healing_op.entity_gid)                │
│      except Exception as e:                                                  │
│          result.healing_failures.append(                                     │
│              HealingFailure(healing_op.entity_gid,                           │
│                           healing_op.expected_project_gid, e)                │
│          )                                                                   │
│          logger.warning("Healing failed for %s: %s",                         │
│                        healing_op.entity_gid, e)                             │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Return SaveResult with healed_entities and healing_failures                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Registry data structure | Module-level singleton dict | O(1) lookup, simple, testable via reset() | ADR-0093 |
| Registry population timing | Import-time via `__init_subclass__` | Simplest; no explicit init needed; env vars read at import | ADR-0093 |
| DetectionResult model | Frozen dataclass (not Pydantic) | Lightweight, immutable, no validation overhead | ADR-0094 |
| Fallback chain pattern | Sequential if-else with early return | Simple, debuggable; Chain of Responsibility overkill | ADR-0094 |
| Healing trigger | tier_used > 1 | Deterministic; Tier 1 = healthy, Tiers 2-5 = needs healing | ADR-0095 |
| Healing execution | Additive only (add_to_project) | Safe; removing memberships could break workflows | ADR-0095 |

## Complexity Assessment

**Complexity Level**: Module

**Justification**:
- Single clear responsibility: entity type detection
- Clean API surface: 2 public functions, 2 data classes, 1 registry
- No external service dependencies (except Asana API for Tier 4)
- No persistence requirements beyond registry singleton
- Fits within existing module structure (`models/business/`)

**Why not Script?**
- Multiple components with clear boundaries (registry, detection, result)
- Integration with SaveSession required

**Why not Service?**
- No independent deployment needed
- No cross-process coordination
- No complex configuration management

## Implementation Plan

### Phase 1: Registry and Tier 1 (Must-Have Core)

**Deliverables**:
- `registry.py` with ProjectTypeRegistry
- `DetectionResult` dataclass
- `detect_by_project()` (Tier 1 implementation)
- `__init_subclass__` hook enhancement
- PRIMARY_PROJECT_GID values on all entity classes
- Environment variable override support

**Requirements Addressed**: FR-REG-001, FR-REG-002, FR-REG-003, FR-REG-004, FR-DET-001, FR-DET-002, FR-DET-007

**Estimate**: 4-6 hours

**Dependencies**: None

### Phase 2: Fallback Tiers 2-3 (Must/Should)

**Deliverables**:
- `detect_by_name()` refactored for contains matching
- `detect_by_parent()` implementation
- Unified `detect_entity_type()` function
- Process project GID registration

**Requirements Addressed**: FR-REG-006, FR-DET-003, FR-DET-004, FR-DET-006

**Estimate**: 2-3 hours

**Dependencies**: Phase 1

### Phase 3: Async Detection and Tier 4 (Should)

**Deliverables**:
- `detect_entity_type_async()` function
- Optional structure inspection (Tier 4)
- Backward-compatible signature overloads

**Requirements Addressed**: FR-DET-005, FR-DET-008, FR-COMPAT-001

**Estimate**: 2 hours

**Dependencies**: Phase 2

### Phase 4: Self-Healing Integration (Should)

**Deliverables**:
- SaveSession `auto_heal` parameter
- Healing operation execution
- SaveResult healing fields
- Per-entity heal override

**Requirements Addressed**: FR-HEAL-001, FR-HEAL-002, FR-HEAL-003, FR-HEAL-004

**Estimate**: 3-4 hours

**Dependencies**: Phase 1

### Phase 5: Validation and Compatibility (Should/Could)

**Deliverables**:
- `validate_registry()` function
- Deprecation warnings on legacy functions
- Strict configuration mode
- Documentation updates

**Requirements Addressed**: FR-REG-005, FR-CFG-002, FR-COMPAT-002

**Estimate**: 2 hours

**Dependencies**: Phases 1-4

### Migration Strategy

1. **No breaking changes**: All existing function signatures preserved
2. **Gradual adoption**: New detection returns `DetectionResult`; legacy functions wrap and return simple `EntityType`
3. **Deprecation warnings**: Legacy `detect_by_name()` emits warning, suggests `detect_entity_type()`
4. **Test preservation**: Existing tests pass without modification

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Missing project GIDs in config | High (detection fails to Tier 2) | Medium | Hardcoded defaults; env var override; validation function |
| Entity in wrong project | Medium (type mismatch) | Low | Self-healing adds correct project; doesn't remove |
| LocationHolder/ProcessHolder detection | Medium (fallback needed) | High | Tier 2/3 fallback designed for these special cases |
| Import order issues with registry | Medium (incomplete registry) | Low | Registry populated lazily; import order doesn't matter |
| Performance regression | Low (O(1) faster than current) | Low | Benchmark tests; registry lookup is single dict access |
| Healing API failures | Low (non-critical) | Low | Healing failures logged, don't fail commit |

## Observability

### Metrics

- `detection.tier_used` histogram: Distribution of which tier succeeded
- `detection.duration_ms` histogram: Detection latency by tier
- `healing.operations_total` counter: Total healing operations attempted
- `healing.failures_total` counter: Failed healing operations

### Logging

```python
# Tier 1 success (debug)
logger.debug("Detected %s via project membership", entity_type.name,
             extra={"task_gid": task.gid, "project_gid": project_gid, "tier": 1})

# Tier 2-4 success (debug)
logger.debug("Detected %s via %s", entity_type.name, tier_name,
             extra={"task_gid": task.gid, "tier": tier_used})

# Tier 5 failure (warning)
logger.warning("Unable to detect type for task %s", task.gid,
               extra={"task_name": task.name, "memberships": memberships})

# Healing success (info)
logger.info("Healed entity %s: added to project %s", entity_gid, project_gid)

# Healing failure (warning)
logger.warning("Healing failed for entity %s", entity_gid,
               extra={"expected_project": project_gid, "error": str(e)})
```

### Alerting

- Alert if `detection.tier_used == 5` (UNKNOWN) exceeds 5% of detections
- Alert if `healing.failures_total` exceeds 10 in 5 minutes

## Testing Strategy

### Unit Tests

- Registry registration and lookup
- Duplicate GID detection
- Environment variable override
- Each detection tier in isolation
- DetectionResult properties (`__bool__`, `is_deterministic`)
- Class name to EntityType conversion

### Integration Tests

- Full detection chain with real task structures
- Self-healing with SaveSession
- Backward compatibility with existing detection callers

### Performance Tests

- Tier 1 detection latency (<1ms target)
- Registry initialization time (<10ms target)
- 1000 detection benchmark

### Edge Case Tests

- Task with no memberships
- Task with unknown project GID
- Empty/None task name
- LocationHolder/ProcessHolder detection paths
- Process multi-project mapping

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Registry population timing~~ | Architect | TDD Session | Import-time via __init_subclass__ |
| ~~DetectionResult as dataclass or Pydantic~~ | Architect | TDD Session | Frozen dataclass (lightweight) |
| ~~Fallback chain pattern~~ | Architect | TDD Session | Simple if-else (ADR-0094) |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Architect | Initial design based on PRD-DETECTION |
