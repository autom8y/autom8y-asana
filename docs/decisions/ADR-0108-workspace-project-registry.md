# ADR-0108: WorkspaceProjectRegistry Architecture

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-18
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-WORKSPACE-PROJECT-REGISTRY, ADR-0093 (ProjectTypeRegistry), ADR-0094 (Detection Fallback Chain)

## Context

The current `ProjectTypeRegistry` (ADR-0093) maps project GIDs to EntityTypes at import time via static `PRIMARY_PROJECT_GID` class attributes. This works for entities with dedicated projects (Business, Contact, Unit, Offer) but **fails for Process entities** which exist in multiple pipeline projects (Sales, Onboarding, Retention, etc.).

Process entities return `EntityType.UNKNOWN` because:
1. `Process.PRIMARY_PROJECT_GID = None` (cannot statically map to multiple projects)
2. Pipeline project GIDs are not registered at import time
3. No mechanism exists to dynamically discover workspace projects

**Key design questions:**
1. Should WorkspaceProjectRegistry be a separate class or extend ProjectTypeRegistry?
2. What is the optimal discovery timing (lazy vs eager)?
3. Should the registry be per-client instance or module singleton?
4. How should ProcessType be derived from project names?

### Forces

1. **PRD Constraint**: Detection API signatures must remain unchanged (FR-DET-002)
2. **PRD Constraint**: Static PRIMARY_PROJECT_GID must take precedence (FR-COMPAT-001)
3. **PRD Constraint**: Single workspace for V1 (multi-workspace is future scope)
4. **PRD Constraint**: O(1) name resolution after discovery (NFR-PERF-002)
5. **User Decision**: Discovery must not impede DX (explicit-call-only rejected)
6. **User Decision**: Projects are stable (no frequent spin-up/spin-down)
7. **Existing Pattern**: NameResolver uses session-scoped caching (per-SaveSession)
8. **Existing Pattern**: ProjectTypeRegistry is module-level singleton

## Decision

We will implement **WorkspaceProjectRegistry as a composition wrapper around ProjectTypeRegistry**, using a **module-level singleton** with **lazy discovery triggered on first unregistered GID lookup**.

### Key Design Choices

#### 1. Composition over Extension

WorkspaceProjectRegistry will **compose with** (not extend) ProjectTypeRegistry:
- Delegates Tier 1 lookup to existing `ProjectTypeRegistry.lookup()`
- Adds workspace discovery and pipeline project registration
- Maintains clear separation: static vs dynamic registrations

```python
class WorkspaceProjectRegistry:
    """Workspace-aware project registry with dynamic pipeline discovery."""

    _instance: ClassVar[WorkspaceProjectRegistry | None] = None

    def __init__(self) -> None:
        self._type_registry = get_registry()  # Compose with existing
        self._name_to_gid: dict[str, str] = {}  # Normalized name -> GID
        self._gid_to_process_type: dict[str, ProcessType] = {}  # Pipeline GID -> type
        self._discovered_workspace: str | None = None
```

#### 2. Module-Level Singleton

Registry will be a module-level singleton (like ProjectTypeRegistry):
- Projects are stable per user decision - no instance-per-client needed
- Consistent with existing ProjectTypeRegistry pattern
- Test isolation via `reset()` class method
- Discovery state persists across SaveSession boundaries

#### 3. Lazy Discovery Timing

Discovery is triggered **on first detection call for an unregistered project GID**:
- No explicit initialization required (good DX per user decision)
- First detection may incur API call latency (one-time cost)
- Subsequent lookups are O(1)
- Explicit `discover_async()` available for eager initialization

```python
async def lookup_or_discover_async(
    self,
    project_gid: str,
    client: AsanaClient,
) -> EntityType | None:
    """Look up entity type, triggering discovery if needed."""
    # Try static registry first
    result = self._type_registry.lookup(project_gid)
    if result is not None:
        return result

    # Trigger discovery if not already done
    if self._discovered_workspace is None:
        await self.discover_async(client)
        return self._type_registry.lookup(project_gid)

    return None
```

#### 4. ProcessType Derivation via Contains Matching

Pipeline projects are identified by case-insensitive **contains matching** of ProcessType values in project names:
- "Sales Pipeline" matches `ProcessType.SALES`
- "Client Onboarding" matches `ProcessType.ONBOARDING`
- Word boundaries are NOT enforced (simpler, handles variations like "Sales-Pipeline")
- Override mechanism available via environment variable for edge cases

```python
def _identify_pipeline_projects(self, projects: list[Project]) -> None:
    """Identify and register pipeline projects."""
    for project in projects:
        name_lower = project.name.lower() if project.name else ""

        for process_type in ProcessType:
            if process_type == ProcessType.GENERIC:
                continue
            if process_type.value in name_lower:
                self._register_pipeline_project(project.gid, process_type)
                break
```

### Integration Points

1. **Detection Integration**: `_detect_tier1_project_membership()` will use `WorkspaceProjectRegistry.lookup_or_discover_async()` for async path
2. **Sync Detection**: Sync `detect_entity_type()` uses only static registry (no async discovery)
3. **Name Resolution**: `get_by_name()` provides O(1) lookup after discovery

## Rationale

**Why composition over extension?**
- Separation of concerns: ProjectTypeRegistry handles static mappings, WorkspaceProjectRegistry adds dynamic discovery
- Lower risk: existing detection code continues to work unchanged
- Clearer mental model: static registrations (import-time) vs dynamic registrations (runtime)

**Why module-level singleton over per-client instance?**
- Projects are stable (user decision) - workspace state doesn't change during session
- Consistent with existing ProjectTypeRegistry pattern
- Simpler: no need to pass registry through call chains
- Test isolation via `reset()` is proven pattern

**Why lazy discovery over eager (client init)?**
- No explicit initialization required (better DX)
- Zero API calls if workspace projects not needed (e.g., working with known GIDs)
- One-time cost amortized across session
- Explicit `discover_async()` available if eager initialization preferred

**Why contains matching over word boundary matching?**
- Simpler implementation: `value in name.lower()`
- Handles variations: "Sales Pipeline", "Sales-Pipeline", "ActiveSales"
- Edge cases handled by environment variable override
- PRD explicitly states contains is acceptable with override mechanism

## Alternatives Considered

### Alternative A: Extend ProjectTypeRegistry

- **Description**: Add discovery methods directly to ProjectTypeRegistry
- **Pros**: Single registry class; simpler mental model
- **Cons**: Mixes static and dynamic concerns; harder to maintain separation
- **Why not chosen**: Composition provides cleaner separation of static vs dynamic

### Alternative B: Per-Client Instance Registry

- **Description**: Each AsanaClient has its own WorkspaceProjectRegistry instance
- **Pros**: Clean lifecycle tied to client; supports multi-workspace
- **Cons**: Requires passing registry through call chains; more complex
- **Why not chosen**: Projects are stable; multi-workspace is out of scope for V1

### Alternative C: Eager Discovery at Client Init

- **Description**: Discover workspace projects when AsanaClient is created
- **Pros**: Predictable timing; no surprise latency on first detection
- **Cons**: API call even if not needed; slower client init
- **Why not chosen**: Lazy is better DX; eager available as explicit option

### Alternative D: Replace NameResolver with WorkspaceProjectRegistry

- **Description**: Consolidate NameResolver into WorkspaceProjectRegistry
- **Pros**: Single source of truth for project name/GID mapping
- **Cons**: NameResolver handles more than projects (tags, sections, users); scope creep
- **Why not chosen**: Separate concern; NameResolver consolidation is separate initiative

## Consequences

### Positive

- **Process detection works**: Pipeline projects registered dynamically
- **No API changes**: Detection signatures unchanged (FR-DET-002)
- **Static precedence preserved**: PRIMARY_PROJECT_GID takes priority (FR-COMPAT-001)
- **Good DX**: No explicit initialization required
- **O(1) lookup**: Name-to-GID after discovery (NFR-PERF-002)
- **Testable**: `reset()` method for test isolation

### Negative

- **First detection latency**: Lazy discovery adds ~1-3 seconds on first unregistered GID
- **Singleton global state**: Mutable state shared across sessions (mitigated by reset())
- **Contains matching imprecision**: "Salesforce" would match "sales" (acceptable per PRD; override available)

### Neutral

- Discovery only runs once per process lifetime (projects are stable)
- Sync detection path unchanged (only static registry)
- Existing tests pass without modification

## Compliance

- WorkspaceProjectRegistry MUST be implemented in `src/autom8_asana/models/business/registry.py`
- MUST delegate static lookups to existing ProjectTypeRegistry
- MUST trigger discovery lazily on first unregistered GID lookup
- MUST support explicit `discover_async()` for eager initialization
- MUST preserve static PRIMARY_PROJECT_GID precedence
- MUST provide `reset()` for test isolation
- Tests MUST use `WorkspaceProjectRegistry.reset()` fixture
