# ADR-0015: Process Pipeline Architecture

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0093, ADR-0096, ADR-0097, ADR-0101, ADR-0135, ADR-0136
- **Related**: reference/OPERATIONS.md

## Context

Process pipelines represent business workflows (sales, onboarding, implementation) as Asana projects with section-based state progression. Processes move through pipeline stages by changing sections within their canonical project. The canonical project serves dual purposes: entity registry for detection and workflow view for state management.

Initial design incorrectly assumed separate "pipeline projects" distinct from entity registry projects. This led to implementation of ProcessProjectRegistry (~1,000 lines of unnecessary code) before discovering that canonical projects ARE the pipelines. Process entities become members of their canonical project (e.g., "Sales") through normal creation flow, and sections within that project represent pipeline states.

Key architectural questions addressed:
- How should project membership determine both EntityType and ProcessType?
- How should pipeline states be represented and extracted?
- Should ProcessHolder have a dedicated project for Tier 1 detection?
- How should pipeline-specific fields be organized: inheritance vs composition?

## Decision

### 1. Canonical Project Architecture

**The canonical project IS the pipeline. No separate "pipeline projects" exist.**

Process entities receive project membership through:
1. Creation in the canonical project (via BusinessSeeder or API)
2. Inheritance from parent Unit context (Unit.PRIMARY_PROJECT_GID determines which canonical project)

**Impact**: Eliminates ProcessProjectRegistry entirely, removing ~1,000 lines of code, configuration burden, and conceptual complexity.

### 2. Project Type Registry Pattern

**Implement module-level singleton registry (ProjectTypeRegistry) for deterministic O(1) EntityType detection.**

Implementation:
- Singleton pattern using `__new__` pattern
- Populated at import-time via `__init_subclass__` hooks on BusinessEntity subclasses
- Environment variables (ASANA_PROJECT_{ENTITY_TYPE}) override class attribute PRIMARY_PROJECT_GID
- Provides `reset()` method for test isolation

```python
class ProjectTypeRegistry:
    """Singleton registry mapping project GIDs to EntityType."""

    _instance: ClassVar[ProjectTypeRegistry | None] = None

    def __new__(cls) -> ProjectTypeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._gid_to_type = {}
            cls._instance._type_to_gid = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset for testing."""
        cls._instance = None
```

**Rationale**: O(1) dict lookup meets NFR-PERF-001 (<1ms detection). Import-time population is simple and predictable. Environment override enables different project GIDs per environment without code changes.

### 3. ProcessType Expansion and Derivation

**Expand ProcessType enum with 6 stakeholder-aligned values plus GENERIC fallback.**

```python
class ProcessType(str, Enum):
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"
    GENERIC = "generic"  # Fallback
```

**Derive ProcessType from canonical project name via simple string matching:**

```python
@property
def process_type(self) -> ProcessType:
    """Derive process type from canonical project name."""
    if not self.memberships:
        return ProcessType.GENERIC

    for membership in self.memberships:
        project_name = membership.get("project", {}).get("name", "").lower()
        for pt in ProcessType:
            if pt != ProcessType.GENERIC and pt.value in project_name:
                return pt

    return ProcessType.GENERIC
```

**Rationale**: Project name matching is O(1), deterministic, and requires no configuration. Matches actual Asana workspace naming conventions where projects are named "Sales", "Onboarding", etc. GENERIC fallback preserves backward compatibility.

### 4. ProcessSection State Machine

**Represent pipeline states via ProcessSection enum with section membership as source of truth.**

```python
class ProcessSection(str, Enum):
    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"

    @classmethod
    def from_name(cls, name: str | None) -> ProcessSection | None:
        """Normalize and match section names with alias support."""
        # Lowercase, replace spaces/hyphens with underscores
        # Support aliases: "Lost" -> DID_NOT_CONVERT
        # Return OTHER for unrecognized names
        # Return None for None input
```

**Extract pipeline state from section membership:**

```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """Get current pipeline state from canonical project section membership."""
    if not self.memberships:
        return None

    for membership in self.memberships:
        section_name = membership.get("section", {}).get("name")
        if section_name:
            return ProcessSection.from_name(section_name)

    return None
```

**Do NOT enforce state transition rules in SDK** - consumers implement business logic. SDK provides primitives, not workflow engine.

**Rationale**: Section membership is the canonical representation in Asana board view. from_name() normalization handles decorated names gracefully. State transition enforcement belongs in consumers, not the SDK data layer. OTHER fallback handles custom sections.

### 5. ProcessHolder Detection Strategy

**ProcessHolder SHALL NOT have a dedicated project (PRIMARY_PROJECT_GID = None).**

Detection relies on:
- Tier 2: Name pattern ("processes") - 60% confidence
- Tier 3: Parent inference from Unit - 80% confidence

```python
class ProcessHolder(Task, HolderMixin["Process"]):
    """Holder task containing Process children.

    PRIMARY_PROJECT_GID is intentionally None because ProcessHolder
    is a container task that exists only to group Process entities
    under a Unit. It has no custom fields and is not managed as a
    project member. Detection relies on:
    - Tier 2: Name pattern "processes"
    - Tier 3: Parent inference from Unit

    This is consistent with LocationHolder and UnitHolder, which
    also lack dedicated projects.
    """

    PRIMARY_PROJECT_GID: ClassVar[str | None] = None
```

**Rationale**: ProcessHolder is purely structural with no custom fields or business data. Team does not manage ProcessHolders in project views - they are navigation containers. Tier 3 inference from Unit parent is highly reliable. Consistent with LocationHolder and UnitHolder (both None).

### 6. Process Field Architecture: Composition Over Inheritance

**Use COMPOSITION with field groups. All pipeline fields defined on single Process class.**

```python
class Process(BusinessEntity):
    """Process entity supporting all pipeline types.

    Fields are organized into groups:
    - Common fields: Available on all process types (8 fields)
    - Sales fields: Specific to Sales pipeline (54+ fields)
    - Onboarding fields: Specific to Onboarding pipeline (33+ fields)
    - Implementation fields: Specific to Implementation pipeline (28+ fields)

    All fields are accessible on any Process instance. Accessing a
    field that doesn't exist on the underlying Asana task returns None.
    """

    # === COMMON FIELDS (8) ===
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    status = EnumField()
    priority = EnumField()
    # ...

    # === SALES PIPELINE FIELDS (54+) ===
    deal_value = NumberField(field_name="Deal Value")
    close_date = DateField(field_name="Close Date")
    sales_stage = EnumField(field_name="Sales Stage")
    # ...

    # === ONBOARDING PIPELINE FIELDS (33+) ===
    go_live_date = DateField(field_name="Go Live Date")
    # ...

    # === IMPLEMENTATION PIPELINE FIELDS (28+) ===
    delivery_date = DateField(field_name="Delivery Date")
    # ...
```

**Rationale**:
- Process type determined by project membership at runtime, not compile time
- No polymorphism benefit - all processes are processed uniformly
- Many fields overlap across pipelines
- Single Process class avoids casting burden
- ADR-0081 descriptors gracefully return None when field doesn't exist on task
- Runtime type checking via `process.process_type == ProcessType.SALES` when needed

## Alternatives Considered

### Alternative A: Separate Pipeline Projects with Dual Membership

- **Description**: Maintain ProcessProjectRegistry; Processes added to both hierarchy and pipeline projects
- **Pros**: Explicit separation of concerns
- **Cons**: Architecture was based on incorrect understanding; ~1,000 lines of unnecessary code; configuration burden
- **Why not chosen**: Canonical project IS the pipeline; dual membership not needed

### Alternative B: Process Subclasses per Type

- **Description**: Create SalesProcess, OnboardingProcess, etc. subclasses
- **Pros**: Type safety via class hierarchy; smaller classes
- **Cons**: Process type unknown at instantiation; requires casting; duplicate shared fields
- **Why not chosen**: Over-engineering; composition provides sufficient organization without casting burden

### Alternative C: ProcessHolder Has Dedicated Project

- **Description**: Create Asana project to hold ProcessHolder tasks for Tier 1 detection
- **Pros**: Deterministic O(1) detection; consistent with OfferHolder pattern
- **Cons**: Operational overhead; project serves no business purpose; team doesn't manage holders in project views
- **Why not chosen**: ProcessHolder is purely structural; creating project for detection alone is unnecessary

### Alternative D: State Machine with Transition Validation

- **Description**: Define valid state transitions per ProcessType; raise error on invalid moves
- **Pros**: Prevents invalid states; self-documenting rules
- **Cons**: SDK must know all business rules; inflexible; different workflows have different rules
- **Why not chosen**: Business logic belongs in consumers; SDK is data layer, not workflow engine

## Consequences

### Positive

- ~1,000 lines of code removed (ProcessProjectRegistry, tests, consumers)
- Simpler mental model: canonical project IS the pipeline
- No configuration burden: no ASANA_PROCESS_PROJECT_* env vars
- Cleaner detection: only ProjectTypeRegistry needed
- O(1) detection via dict lookup (<1ms)
- Deterministic: project GID unambiguously maps to type
- Clear type differentiation for pipeline processes via ProcessSection enum
- Single Process class simplicity - no casting needed
- Full IDE support for all fields with autocomplete
- Graceful degradation: accessing non-existent field returns None

### Negative

- ProcessType detection is heuristic based on project name matching (acceptable for current domain)
- Multi-project edge case: if Process in multiple projects, behavior uses first membership with section
- Large Process class: 80+ field descriptors (mitigated by organization into commented groups)
- Field pollution: Sales fields visible on Onboarding processes (returns None)
- ProcessHolder relies on Tier 2/3 detection (60-80% confidence vs 100% with project)

### Neutral

- ProcessType enum grows from 1 to 7 values
- ProcessSection enum provides type safety but not transition enforcement
- ProcessHolder.PRIMARY_PROJECT_GID remains None (intentional, documented)
- Process class file grows significantly (acceptable; well-organized)

## Implementation Guidance

### When building process pipelines:

1. Use ProjectTypeRegistry for EntityType.PROCESS detection via project membership
2. Derive ProcessType from canonical project name matching (no separate registry)
3. Extract pipeline_state from section membership in canonical project
4. Use ProcessSection.from_name() for robust section name matching
5. No state transition validation in SDK - implement in consumer logic

### When detecting ProcessHolder:

1. Confirm PRIMARY_PROJECT_GID = None is intentional
2. Strengthen Tier 2 pattern matching for decorated names
3. Prefer Tier 3: when hydrating from Unit, provide parent_type=EntityType.UNIT

### When accessing Process fields:

1. All fields accessible on any Process instance
2. Use process.process_type for pipeline-specific logic branches
3. Expect None for fields not present on underlying task
4. Organize new fields into appropriate group with clear comments

## Compliance

- [ ] ProjectTypeRegistry implemented as singleton with __init_subclass__ population
- [ ] All BusinessEntity subclasses with project define PRIMARY_PROJECT_GID
- [ ] Environment variable pattern is ASANA_PROJECT_{ENTITY_TYPE}
- [ ] ProcessType enum has 7 values (6 pipelines + GENERIC)
- [ ] ProcessSection enum has 7 values with from_name() classmethod
- [ ] ProcessSection.from_name() is case-insensitive with alias support
- [ ] ProcessHolder.PRIMARY_PROJECT_GID = None with documented rationale
- [ ] Process uses composition with field groups, not inheritance
- [ ] All pipeline fields use descriptor pattern per ADR-0081
- [ ] Tests verify ProcessHolder detection via Tier 2 and Tier 3
- [ ] Tests verify None return for fields not present on task
