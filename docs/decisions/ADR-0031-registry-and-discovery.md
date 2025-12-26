# ADR-0031: Registry and Discovery Architecture

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0080, ADR-0108, ADR-0142
- **Related**: TDD-HARDENING-F (GID-Based Entity Identity), PRD-WORKSPACE-PROJECT-REGISTRY

## Context

The autom8_asana system requires mechanisms for tracking entity identity, discovering workspace projects, and detecting entity types. Three architectural questions drive these decisions:

1. **What is the scope of the entity registry?** - Per-session, per-client, or global?
2. **How do we discover pipeline projects dynamically?** - Static registration works for dedicated entity projects but fails for Processes in multiple pipeline projects
3. **How do we organize detection logic?** - A 1,125-line monolith violates single responsibility and creates maintenance burden

These decisions affect memory usage, session isolation, entity lifecycle, and codebase maintainability.

## Decision

We establish a **three-component registry and discovery architecture**: per-session entity tracking, dynamic workspace discovery, and modular detection organization.

### 1. Per-Session Entity Registry

**Registry scoped to `SaveSession` instance, not global or client-scoped.**

Each `SaveSession` has its own independent `ChangeTracker` with its own entity registry:

```python
class SaveSession:
    def __init__(self, client: AsanaClient, ...) -> None:
        # Each session gets its own tracker instance
        self._tracker = ChangeTracker()
```

**Lifecycle**:
```
Session A created    --> Tracker A created (empty)
Session A tracks X   --> X in Tracker A
Session B created    --> Tracker B created (empty, independent)
Session B tracks X   --> X in Tracker B (independent copy)
Session A commits    --> X saved, Tracker A marks clean
Session A exits      --> Tracker A garbage collected
```

**Implications**:
- Entities tracked in Session A are not visible in Session B
- Same GID can be tracked independently in multiple sessions
- Registry is garbage collected when session exits
- No cross-session synchronization or locks needed

**Rationale**:
- **Matches ORM patterns**: SQLAlchemy, Django ORM use session-scoped identity maps
- **Predictable isolation**: Sessions don't interfere with each other
- **Clear lifecycle**: Registry lives and dies with session
- **No concurrency complexity**: No locks or synchronization needed
- **Memory bounded**: Registry size bounded by single session's entities

**Why not global**: Unpredictable side effects (tracking in one session affects another), memory growth unbounded, cleanup complexity, concurrency hazards.

**Why not client-scoped**: Still has sharing problems (multiple sessions per client would share), client lifecycle unclear, most of global's problems remain.

### 2. Workspace Project Registry with Dynamic Discovery

**`WorkspaceProjectRegistry` as composition wrapper with lazy discovery triggered on first unregistered GID lookup.**

**Architecture**:
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

**Key Design Choices**:

**Composition over extension**:
- Delegates Tier 1 lookup to existing `ProjectTypeRegistry`
- Adds workspace discovery and pipeline project registration
- Maintains clear separation: static vs dynamic registrations

**Module-level singleton**:
- Projects are stable per user decision - no instance-per-client needed
- Consistent with existing `ProjectTypeRegistry` pattern
- Test isolation via `reset()` class method
- Discovery state persists across SaveSession boundaries

**Lazy discovery timing**:
- Discovery triggered on first detection call for unregistered project GID
- No explicit initialization required (good DX)
- First detection may incur API call latency (~1-3 seconds, one-time cost)
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

**ProcessType derivation via contains matching**:
- Pipeline projects identified by case-insensitive contains matching of ProcessType values in project names
- "Sales Pipeline" matches `ProcessType.SALES`
- "Client Onboarding" matches `ProcessType.ONBOARDING`
- Word boundaries NOT enforced (simpler, handles variations)
- Override mechanism available via environment variable

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

**Integration points**:
- **Async detection**: `_detect_tier1_project_membership()` uses `lookup_or_discover_async()`
- **Sync detection**: Uses only static registry (no async discovery)
- **Name resolution**: `get_by_name()` provides O(1) lookup after discovery

**Rationale**:
- **Composition provides cleaner separation**: Static registrations (import-time) vs dynamic registrations (runtime)
- **Module-level singleton matches established pattern**: Projects are stable (user decision), no instance-per-client overhead
- **Lazy discovery provides good DX**: No explicit initialization required, zero API calls if workspace projects not needed
- **Contains matching handles variations**: Simpler implementation, handles "Sales Pipeline", "Sales-Pipeline", "ActiveSales"

### 3. Detection Package Structure

**Convert `detection.py` from single 1,125-line file to package directory with 7 focused modules.**

**Structure**:
```
src/autom8_asana/models/business/
    detection/                    # Package (replaces detection.py)
        __init__.py               # Re-exports for backward compatibility (~50 lines)
        types.py                  # Types and constants (~170 lines)
        config.py                 # Configuration data (~230 lines)
        tier1.py                  # Project membership detection (~180 lines)
        tier2.py                  # Name pattern detection (~150 lines)
        tier3.py                  # Parent inference detection (~60 lines)
        tier4.py                  # Structure inspection detection (~80 lines)
        facade.py                 # Unified detection orchestration (~200 lines)
```

**Module dependency layering**:
```
                    +-----------+
                    |  types.py |  (no dependencies - pure types)
                    +-----------+
                          |
                    +-----------+
                    | config.py |  (imports types.py only)
                    +-----------+
                          |
          +---------------+---------------+
          |               |               |
    +-----------+   +-----------+   +-----------+
    | tier1.py  |   | tier2.py  |   | tier3.py  |
    +-----------+   +-----------+   +-----------+
          |               |               |
          |         +-----------+         |
          |         | tier4.py  |         |
          |         +-----------+         |
          |               |               |
          +---------------+---------------+
                          |
                    +-----------+
                    | facade.py |  (imports all tiers)
                    +-----------+
                          |
                    +-----------+
                    |__init__.py|  (re-exports all public symbols)
                    +-----------+
```

**Re-export strategy**:
`__init__.py` re-exports all 22 symbols from `__all__` plus 5 private functions used by tests:

```python
# detection/__init__.py
from autom8_asana.models.business.detection.types import (
    EntityType, EntityTypeInfo, DetectionResult,
    CONFIDENCE_TIER_1, CONFIDENCE_TIER_2, CONFIDENCE_TIER_3,
)
from autom8_asana.models.business.detection.config import (
    ENTITY_TYPE_INFO, NAME_PATTERNS, HOLDER_NAME_MAP,
)
from autom8_asana.models.business.detection.facade import (
    detect_entity_type, detect_entity_type_async,
)

__all__ = [
    # All 22 original exports + 5 private functions for test compatibility
]
```

**Module boundaries follow natural structure**:
1. **types.py**: Types have zero dependencies - pure definitions
2. **config.py**: Configuration depends only on types
3. **tier{1-4}.py**: Each tier is logically independent with distinct responsibilities
   - Tier 1: Registry lookup (sync + async variants)
   - Tier 2: String pattern matching (word boundaries, stripping)
   - Tier 3: Parent-child inference (PARENT_CHILD_MAP)
   - Tier 4: Async structure inspection (API call)
4. **facade.py**: Orchestrates tiers - natural aggregation point

**Rationale**:
- **Single responsibility**: Each module has one concern (60-230 line files vs 1,125)
- **Reduced cognitive load**: Engineers work with focused modules
- **Better code review**: Changes scoped to concern-specific files
- **Easier onboarding**: Module names indicate purpose
- **Merge conflict reduction**: Parallel work on different tiers possible
- **Backward compatibility**: All existing imports continue to work

## Consequences

### Positive

**Per-Session Entity Registry**:
- Session isolation: Sessions are truly independent units of work
- Predictable memory: Registry bounded by session lifetime
- Simple mental model: Track in session, commit session, done
- No synchronization: Thread-safe without locks (sessions not shared)
- ORM familiarity: Developers familiar with Django/SQLAlchemy feel at home

**Workspace Project Registry**:
- Process detection works: Pipeline projects registered dynamically
- No API changes: Detection signatures unchanged
- Static precedence preserved: PRIMARY_PROJECT_GID takes priority
- Good DX: No explicit initialization required
- O(1) lookup: Name-to-GID after discovery
- Testable: `reset()` method for test isolation

**Detection Package Structure**:
- Improved maintainability: Each module has single responsibility
- Reduced cognitive load: 60-230 line files vs 1,125
- Better code review: Changes scoped to concern-specific files
- Easier onboarding: Module names indicate purpose
- Test isolation opportunity: Can test tiers independently
- Merge conflict reduction: Parallel work possible

### Negative

**Per-Session Entity Registry**:
- No cross-session deduplication: Same entity tracked twice across sessions means duplicate work (*Mitigation: Sessions should be short-lived*)
- Re-track after session exit: New session requires re-tracking entities (*Mitigation: Expected behavior; sessions are work units*)

**Workspace Project Registry**:
- First detection latency: Lazy discovery adds ~1-3 seconds on first unregistered GID
- Singleton global state: Mutable state shared across sessions (mitigated by reset())
- Contains matching imprecision: "Salesforce" would match "sales" (acceptable per requirements; override available)

**Detection Package Structure**:
- More files: 7 files instead of 1 (acceptable trade-off for clarity)
- One-time migration effort: Must extract carefully to preserve behavior
- Slightly longer import chains: Internal imports span files (mitigated by re-exports)

### Neutral

**Per-Session Entity Registry**:
- Users can still implement own cross-session coordination if needed
- `find_by_gid()` only works within same session (by design)
- Temp GID transitions are session-local

**Workspace Project Registry**:
- Discovery only runs once per process lifetime (projects are stable)
- Sync detection path unchanged (only static registry)
- Existing tests pass without modification

**Detection Package Structure**:
- No API changes: All existing imports continue to work
- No behavior changes: Pure structural refactoring
- Test updates optional: Tests can use new paths in follow-up work

## Implementation Notes

### Session Isolation Example

```python
async def demonstrate_isolation():
    """Sessions are isolated - same GID tracked independently."""

    # Session A tracks and modifies task
    async with SaveSession(client) as session_a:
        task_a = await client.tasks.get_async("12345")
        session_a.track(task_a)
        task_a.name = "Name from A"

        # Session B tracks same GID independently
        async with SaveSession(client) as session_b:
            # session_b.find_by_gid("12345") returns None
            # because B has its own empty registry
            assert session_b.find_by_gid("12345") is None

            task_b = await client.tasks.get_async("12345")
            session_b.track(task_b)
            task_b.notes = "Notes from B"

            # Session B commits its version
            await session_b.commit_async()

        # Session A commits its version (overwrites notes)
        await session_a.commit_async()

    # This is by design: sessions are isolated work units
```

### Workspace Registry Integration

```python
# Async detection uses dynamic discovery
from autom8_asana.models.business.registry import get_workspace_registry

registry = get_workspace_registry()
entity_type = await registry.lookup_or_discover_async(project_gid, client)

# Sync detection uses static registry only
from autom8_asana.models.business.registry import get_registry

registry = get_registry()
entity_type = registry.lookup(project_gid)  # No async discovery
```

### Detection Package Migration

```python
# Before (still works):
from autom8_asana.models.business.detection import EntityType, detect_entity_type

# After (also works, more explicit):
from autom8_asana.models.business.detection.types import EntityType
from autom8_asana.models.business.detection.facade import detect_entity_type
```

## Compliance

### Entity Registry Validation
- [ ] Each `SaveSession` creates its own `ChangeTracker`
- [ ] Tracking in Session A doesn't affect Session B's `find_by_gid()`
- [ ] Session exit clears its registry (no memory leak)
- [ ] Concurrent sessions don't interfere

### Workspace Registry Requirements
- WorkspaceProjectRegistry MUST be implemented in `src/autom8_asana/models/business/registry.py`
- MUST delegate static lookups to existing ProjectTypeRegistry
- MUST trigger discovery lazily on first unregistered GID lookup
- MUST support explicit `discover_async()` for eager initialization
- MUST preserve static PRIMARY_PROJECT_GID precedence
- MUST provide `reset()` for test isolation
- Tests MUST use `WorkspaceProjectRegistry.reset()` fixture

### Detection Package Checks
- **CI verification**: All tests must pass after module extraction
- **Import validation**: `python -c "from autom8_asana.models.business.detection import *"` succeeds
- **Line count check**: `wc -l detection/*.py` shows all modules <250 lines
- **mypy check**: `mypy src/autom8_asana/models/business/detection/` passes
- **Circular import check**: Modules import without error on fresh Python session

## Related Decisions

**Foundation**: See ADR-0029 for AsanaResource entity boundary that registry tracks.

**Cache**: See ADR-0030 for cache infrastructure that SaveSession integrates with.

**Business Domain**: See ADR-0032 for business entity patterns that use detection and registry.

**Patterns**: See ADR-SUMMARY-PATTERNS for entity detection patterns and registry patterns.

## References

**Original ADRs**:
- ADR-0080: Entity Registry Scope (2025-12-16)
- ADR-0108: Workspace Project Registry (2025-12-18)
- ADR-0142: Detection Package Structure (2025-12-19)

**Technical Design**:
- TDD-HARDENING-F: GID-Based Entity Identity
- TDD-SPRINT-3-DETECTION-DECOMPOSITION

**Requirements**:
- PRD-HARDENING-F: GID-based tracking
- PRD-WORKSPACE-PROJECT-REGISTRY: Dynamic project discovery
- FR-DET-002: Detection API signatures unchanged
- NFR-PERF-002: O(1) name resolution after discovery
