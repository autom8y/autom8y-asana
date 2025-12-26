# ADR-0093: Project-to-EntityType Registry Pattern

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-DETECTION, TDD-DETECTION, ADR-0068 (superseded), ADR-0080

## Context

The current entity type detection system (ADR-0068) uses name-based heuristics that fail in production because holder names are decorated with business context (e.g., "Duong Chiropractic Inc - Chiropractic Offers" instead of "offers").

The legacy autom8 system uses **project membership** as the source of truth. Each entity type has a dedicated Asana project, and membership in that project determines type. This is deterministic and O(1) with a registry lookup.

**Key design questions:**

1. **Data structure**: How to store the project GID to EntityType mapping?
2. **Population timing**: When should the registry be populated?
3. **Override hierarchy**: How do environment variables interact with code defaults?
4. **Testing**: How to reset/mock the registry for tests?

### Forces

1. **O(1) lookup required**: NFR-PERF-001 mandates <1ms detection
2. **Import-time safety**: No side effects during module import
3. **Environment override**: FR-REG-004 requires env var override for project GIDs
4. **Testing isolation**: Tests must be able to reset registry state
5. **Single source of truth**: Registry should be the canonical mapping
6. **Idempotent population**: Re-importing should not duplicate entries

## Decision

We will implement a **module-level singleton registry** using a class with `__new__` singleton pattern, populated **at import-time via `__init_subclass__`** hooks on `BusinessEntity` subclasses.

### Registry Implementation

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

### Population Mechanism

```python
# In BusinessEntity.__init_subclass__
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)

    # Get entity type from class name
    entity_type = _class_name_to_entity_type(cls.__name__)
    if entity_type is None:
        return

    # Check env var first, then class attribute
    env_var = f"ASANA_PROJECT_{entity_type.name}"
    project_gid = os.environ.get(env_var) or cls.PRIMARY_PROJECT_GID

    if project_gid:
        get_registry().register(project_gid, entity_type)
```

### Override Hierarchy

1. Environment variable `ASANA_PROJECT_{ENTITY_TYPE}` (highest priority)
2. Class attribute `PRIMARY_PROJECT_GID`
3. No registration if both are None/empty

### Testing Support

```python
# In test fixtures
@pytest.fixture
def clean_registry():
    ProjectTypeRegistry.reset()
    yield
    ProjectTypeRegistry.reset()
```

## Rationale

**Why singleton class over module-level dict?**
- Encapsulates registration logic and validation
- Provides `reset()` method for testing
- Can add logging/metrics to register() calls
- Type-safe accessor functions

**Why import-time population over lazy/explicit init?**
- Simplest: no explicit init call needed
- All entity classes auto-register when their module is imported
- Environment variables are read once at import (predictable)
- Compatible with existing import structure

**Why `__init_subclass__` over metaclass?**
- Already used by BusinessEntity for ref discovery (ADR-0076)
- Simpler than metaclass; no compatibility concerns
- Runs after Pydantic model setup completes

**Why env var override pattern?**
- 12-factor app compatibility
- Different project GIDs per environment (dev/staging/prod)
- No code changes needed for environment-specific configuration

## Alternatives Considered

### Alternative A: Lazy Initialization on First Access

- **Description**: Registry populated when first lookup is called
- **Pros**: No import-time side effects; all entity imports guaranteed complete
- **Cons**: First lookup is slow; threading concerns; harder to debug missing registrations
- **Why not chosen**: Import-time is simpler; `__init_subclass__` runs after class creation (safe)

### Alternative B: Explicit Registry.initialize() Call

- **Description**: Consumer must call `Registry.initialize()` before detection
- **Pros**: Explicit lifecycle; can pass configuration
- **Cons**: Easy to forget; breaks existing code patterns; adds boilerplate
- **Why not chosen**: Implicit import-time is sufficient; no configuration needed

### Alternative C: Module-Level Dict (No Class)

- **Description**: `_REGISTRY: dict[str, EntityType] = {}` at module level
- **Pros**: Simpler; no singleton pattern
- **Cons**: No encapsulation; reset requires clearing dict (less isolated); no validation logic
- **Why not chosen**: Class provides better encapsulation and testability

### Alternative D: ADR-0080 Entity Registry Extension

- **Description**: Extend existing EntityRegistry to include project GID mapping
- **Pros**: Reuses existing infrastructure
- **Cons**: EntityRegistry serves different purpose (type -> class mapping); mixing concerns
- **Why not chosen**: Separate concerns; ProjectTypeRegistry is project GID -> type, not type -> class

## Consequences

### Positive

- **O(1) detection**: Dict lookup is constant time
- **Deterministic**: Project GID unambiguously maps to type
- **Testable**: `reset()` method enables test isolation
- **Environment-aware**: Env vars override defaults without code changes
- **Self-documenting**: PRIMARY_PROJECT_GID on each class shows its project
- **Idempotent**: Re-importing doesn't cause issues

### Negative

- **Import order dependency**: If business entity module not imported, it's not registered (acceptable; models imported via `__init__.py`)
- **Global state**: Singleton is mutable global state (mitigated by reset() for tests)
- **Env var timing**: Env vars must be set before module import (standard pattern)

### Neutral

- Registry is populated during normal import flow
- No API changes to existing detection functions
- Compatible with existing entity class structure

## Compliance

- Registry MUST be implemented in `src/autom8_asana/models/business/registry.py`
- All `BusinessEntity` subclasses with a project MUST define `PRIMARY_PROJECT_GID`
- Environment variable pattern MUST be `ASANA_PROJECT_{ENTITY_TYPE}`
- Tests MUST use `ProjectTypeRegistry.reset()` fixture for isolation
- `register()` MUST raise `ValueError` on duplicate GID with different type
