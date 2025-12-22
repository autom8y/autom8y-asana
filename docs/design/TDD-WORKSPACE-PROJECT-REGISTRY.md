# TDD: Workspace Project Registry

## Metadata

- **TDD ID**: TDD-WORKSPACE-PROJECT-REGISTRY
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **PRD Reference**: [PRD-WORKSPACE-PROJECT-REGISTRY](/docs/requirements/PRD-WORKSPACE-PROJECT-REGISTRY.md)
- **Related TDDs**: TDD-DETECTION
- **Related ADRs**: [ADR-0093](/docs/decisions/ADR-0093-project-type-registry.md), [ADR-0094](/docs/decisions/ADR-0094-detection-fallback-chain.md), [ADR-0108](/docs/decisions/ADR-0108-workspace-project-registry.md), [ADR-0109](/docs/decisions/ADR-0109-lazy-discovery-timing.md)

## Overview

WorkspaceProjectRegistry extends the SDK's entity detection system with dynamic project discovery, enabling Process entities in pipeline projects (Sales, Onboarding, Retention, etc.) to be detected via Tier 1 project membership lookup. It composes with the existing ProjectTypeRegistry, maintaining backward compatibility while adding runtime workspace project registration.

## Requirements Summary

From [PRD-WORKSPACE-PROJECT-REGISTRY](/docs/requirements/PRD-WORKSPACE-PROJECT-REGISTRY.md):

| Requirement | Priority | Summary |
|-------------|----------|---------|
| FR-DISC-001 | Must | Discover all projects in workspace via Asana API |
| FR-DISC-002 | Must | O(1) name-to-GID mapping after discovery |
| FR-DISC-003 | Must | Lazy or automatic discovery (explicit-only rejected) |
| FR-PIPE-001 | Must | Identify pipeline projects by ProcessType in name |
| FR-PIPE-002 | Must | Register pipeline projects as EntityType.PROCESS |
| FR-PIPE-003 | Must | Derive ProcessType from pipeline project GID |
| FR-DET-001 | Must | Tier 1 detection for pipeline projects |
| FR-DET-002 | Must | Detection API signatures unchanged |
| FR-COMPAT-001 | Must | Static PRIMARY_PROJECT_GID preserved |
| FR-COMPAT-002 | Must | Existing tests pass without modification |
| FR-REF-001 | Should | On-demand refresh capability |
| NFR-PERF-001 | Must | Discovery <3 seconds for typical workspace |
| NFR-PERF-002 | Must | O(1) name resolution after discovery |
| NFR-PERF-003 | Must | <10 MB memory for 100 projects |

## System Context

```
+------------------+     +------------------------+     +------------------+
|                  |     |                        |     |                  |
|  AsanaClient     |---->| WorkspaceProjectRegistry|---->| ProjectsClient   |
|                  |     |                        |     |   .list_async()  |
+--------+---------+     +----------+-------------+     +------------------+
         |                          |
         |                          v
         |               +----------+-------------+
         |               |                        |
         |               |  ProjectTypeRegistry   |  (Existing - ADR-0093)
         |               |  (Static Mappings)     |
         |               +------------------------+
         |
         v
+--------+---------+     +------------------------+
|                  |     |                        |
| detect_entity_   |---->| WorkspaceProjectRegistry|
| type_async()     |     |  .lookup_or_discover() |
|                  |     |                        |
+------------------+     +------------------------+
```

WorkspaceProjectRegistry sits between detection and the static ProjectTypeRegistry:
- **Composes with** ProjectTypeRegistry for static lookups
- **Extends** with dynamic pipeline project registration
- **Integrates** with async detection path for lazy discovery

## Design

### Component Architecture

```
src/autom8_asana/models/business/
    registry.py                    # Extended with WorkspaceProjectRegistry
        +-- ProjectTypeRegistry    # EXISTING - Static mappings (unchanged)
        +-- WorkspaceProjectRegistry  # NEW - Dynamic workspace discovery
        +-- get_registry()         # EXISTING - Returns ProjectTypeRegistry
        +-- get_workspace_registry()  # NEW - Returns WorkspaceProjectRegistry

    detection.py                   # Extended with async discovery hook
        +-- detect_entity_type()   # EXISTING - Sync, static registry only
        +-- detect_entity_type_async()  # MODIFIED - Triggers lazy discovery
        +-- _detect_tier1_project_membership_async()  # NEW - Async Tier 1
```

| Component | Responsibility | Owner |
|-----------|---------------|-------|
| WorkspaceProjectRegistry | Workspace discovery, pipeline identification, name-to-GID mapping | SDK |
| ProjectTypeRegistry | Static GID-to-EntityType mappings (unchanged) | SDK |
| _detect_tier1_project_membership_async | Async Tier 1 with lazy discovery | SDK |

### Data Model

#### WorkspaceProjectRegistry State

```python
class WorkspaceProjectRegistry:
    """Workspace-aware project registry with dynamic pipeline discovery.

    Per ADR-0108: Composes with ProjectTypeRegistry for static lookups.
    Per ADR-0109: Lazy discovery on first unregistered GID lookup.
    """

    _instance: ClassVar[WorkspaceProjectRegistry | None] = None

    # Composed registry (delegation)
    _type_registry: ProjectTypeRegistry

    # Name-to-GID mapping (normalized lowercase name -> GID)
    _name_to_gid: dict[str, str]

    # Pipeline project metadata (GID -> ProcessType)
    _gid_to_process_type: dict[str, ProcessType]

    # Discovery state
    _discovered_workspace: str | None  # None = not yet discovered
```

#### Memory Budget (NFR-PERF-003)

For 100 projects:
- `_name_to_gid`: ~100 entries * ~100 bytes = ~10 KB
- `_gid_to_process_type`: ~10 entries (pipeline projects) * ~50 bytes = ~500 bytes
- Total: <1 MB (well under 10 MB target)

### API Contracts

#### WorkspaceProjectRegistry Public Interface

```python
class WorkspaceProjectRegistry:
    """Workspace project discovery and pipeline registration.

    Example:
        # Lazy discovery (recommended)
        registry = get_workspace_registry()
        entity_type = await registry.lookup_or_discover_async(project_gid, client)

        # Eager discovery (optional)
        await registry.discover_async(client)
        gid = registry.get_by_name("Sales Pipeline")

        # ProcessType lookup
        process_type = registry.get_process_type(project_gid)
    """

    async def discover_async(self, client: AsanaClient) -> None:
        """Discover all projects in client's default workspace.

        Per FR-DISC-001: Fetches all workspace projects.
        Per FR-DISC-002: Populates name-to-GID mapping.
        Per FR-PIPE-001/002: Identifies and registers pipeline projects.

        Idempotent: repeated calls refresh the registry.
        Does NOT overwrite static PRIMARY_PROJECT_GID registrations.

        Args:
            client: AsanaClient with default_workspace_gid set.

        Raises:
            ValueError: If client.default_workspace_gid is not set.
        """

    async def lookup_or_discover_async(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> EntityType | None:
        """Look up entity type, triggering discovery if needed.

        Per ADR-0109: Lazy discovery on first unregistered GID.

        Args:
            project_gid: Asana project GID.
            client: AsanaClient for discovery if needed.

        Returns:
            EntityType if found in static or dynamic registry, None otherwise.
        """

    def lookup(self, project_gid: str) -> EntityType | None:
        """Sync lookup (static registry only, no discovery).

        Per FR-DET-002: Detection API unchanged.

        Args:
            project_gid: Asana project GID.

        Returns:
            EntityType if in static registry, None otherwise.
        """

    def get_by_name(self, name: str) -> str | None:
        """Get project GID by name (O(1) after discovery).

        Per FR-DISC-002: Case-insensitive, whitespace-normalized.

        Args:
            name: Project name.

        Returns:
            Project GID if found, None otherwise.
        """

    def get_process_type(self, project_gid: str) -> ProcessType | None:
        """Get ProcessType for a pipeline project.

        Per FR-PIPE-003: Returns ProcessType that matched project name.

        Args:
            project_gid: Pipeline project GID.

        Returns:
            ProcessType if GID is a registered pipeline project, None otherwise.
        """

    def is_discovered(self) -> bool:
        """Check if workspace discovery has been performed.

        Returns:
            True if discover_async() has been called, False otherwise.
        """

    @classmethod
    def reset(cls) -> None:
        """Reset registry for testing.

        Per ADR-0093 pattern: Test isolation via explicit reset.
        """
```

#### Detection Integration

```python
# In detection.py

async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Async detection with lazy workspace discovery.

    Per FR-DET-001: Pipeline projects detected via Tier 1.
    Per FR-DET-002: Signature unchanged.

    Tier 1 in async path uses WorkspaceProjectRegistry for
    lazy discovery of pipeline projects.
    """
    # NEW: Async Tier 1 with lazy discovery
    result = await _detect_tier1_project_membership_async(task, client)
    if result:
        return result

    # Existing: Tiers 2-5 (unchanged)
    result = detect_entity_type(task, parent_type)
    # ... rest unchanged
```

### Data Flow

#### Lazy Discovery Flow

```
detect_entity_type_async(task, client)
    |
    v
_detect_tier1_project_membership_async(task, client)
    |
    +-- Extract project_gid from task.memberships
    |
    v
WorkspaceProjectRegistry.lookup_or_discover_async(project_gid, client)
    |
    +-- Is GID in static registry? (ProjectTypeRegistry.lookup)
    |       |
    |      YES --> Return EntityType
    |       |
    |      NO
    |       v
    +-- Has discovery been performed?
    |       |
    |      YES --> Return None (truly unknown)
    |       |
    |      NO
    |       v
    +-- discover_async(client)
    |       |
    |       +-- Fetch projects: client.projects.list_async(workspace=...)
    |       |
    |       +-- For each project:
    |       |       +-- Add to _name_to_gid (normalized)
    |       |       +-- If name contains ProcessType value:
    |       |       |       +-- Add to _gid_to_process_type
    |       |       |       +-- Register with ProjectTypeRegistry (if not static)
    |       |
    |       +-- Mark _discovered_workspace = workspace_gid
    |       v
    +-- Retry: ProjectTypeRegistry.lookup(project_gid)
            |
            v
        Return EntityType | None
```

#### Name Resolution Flow

```
get_by_name("Sales Pipeline")
    |
    v
Normalize: "sales pipeline" (lowercase, strip)
    |
    v
Lookup: _name_to_gid.get("sales pipeline")
    |
    +-- Found --> Return GID
    |
    +-- Not found --> Return None
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Registry architecture | Composition with ProjectTypeRegistry | Separation of static vs dynamic concerns | ADR-0108 |
| Instance model | Module-level singleton | Projects stable; consistent with existing pattern | ADR-0108 |
| Discovery timing | Lazy on first unregistered GID | Good DX; explicit-only rejected by PRD | ADR-0109 |
| ProcessType matching | Case-insensitive contains | Simpler; handles variations; override available | ADR-0108 |
| Sync detection | Static registry only | No API calls in sync path; existing guarantee | ADR-0109 |

## Complexity Assessment

**Level**: Module

**Justification**:
- Clear API surface (WorkspaceProjectRegistry class)
- Limited scope: workspace discovery + pipeline registration
- Composes with existing infrastructure (ProjectTypeRegistry, ProjectsClient)
- No new dependencies or infrastructure requirements
- Single module addition with minimal integration points

This is NOT a Service because:
- No external API contract (internal SDK component)
- No independent deployment
- No configuration beyond environment variables

## Implementation Plan

### Phase 1: Core Registry (Must Have)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| WorkspaceProjectRegistry class skeleton | None | 2 hours |
| `discover_async()` implementation | ProjectsClient | 2 hours |
| `lookup_or_discover_async()` implementation | discover_async | 1 hour |
| `get_by_name()` implementation | discover_async | 30 min |
| `get_process_type()` implementation | discover_async | 30 min |
| Unit tests for registry | All above | 2 hours |

### Phase 2: Detection Integration (Must Have)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `_detect_tier1_project_membership_async()` | Phase 1 | 1 hour |
| Modify `detect_entity_type_async()` | Above | 1 hour |
| Integration tests | All above | 2 hours |
| Existing test verification | All above | 1 hour |

### Phase 3: Enhancements (Should Have)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `refresh_async()` method | Phase 1 | 30 min |
| Environment variable overrides | Phase 1 | 1 hour |
| Performance benchmarks | All phases | 1 hour |

**Total Estimate**: 14 hours (2 developer days)

### Migration Strategy

No migration required:
- Existing detection code continues to work unchanged
- New async detection path adds lazy discovery transparently
- Static PRIMARY_PROJECT_GID registrations preserved
- Backward compatible: no API changes

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Contains matching too greedy ("Salesforce" matches "sales") | Med | Low | Environment variable override for edge cases; documented limitation |
| First detection latency surprises users | Low | Med | Document in discovery timing; provide explicit `discover_async()` |
| Discovery fails (API error, rate limit) | Med | Low | Log warning; fall through to Tier 2+ detection gracefully |
| Memory pressure with many projects | Low | Low | Only store GID and name; <1 MB for 100 projects |
| Race condition during discovery | Low | Low | Discovery is idempotent; single-threaded Python |

## Observability

### Metrics

- `workspace_registry.discovery_time_seconds`: Time to complete discovery
- `workspace_registry.projects_discovered`: Number of projects found
- `workspace_registry.pipeline_projects_registered`: Number of pipeline projects

### Logging

```python
# Discovery
logger.info(
    "Workspace discovery complete",
    extra={
        "workspace_gid": workspace_gid,
        "projects_count": len(projects),
        "pipeline_projects": len(self._gid_to_process_type),
        "duration_seconds": elapsed,
    },
)

# Pipeline registration
logger.debug(
    "Registered pipeline project",
    extra={
        "project_gid": project.gid,
        "project_name": project.name,
        "process_type": process_type.value,
    },
)

# Name resolution
logger.debug(
    "Resolved project name to GID",
    extra={
        "name": name,
        "project_gid": gid,
    },
)
```

### Alerting

- Alert if discovery takes >10 seconds (unusual workspace size)
- Alert if discovery fails repeatedly (API issues)

## Testing Strategy

### Unit Testing

- WorkspaceProjectRegistry in isolation with mocked ProjectsClient
- Pipeline identification logic with various project names
- Name-to-GID lookup (case insensitivity, whitespace)
- ProcessType derivation from pipeline GIDs
- Idempotent discovery behavior
- Reset for test isolation

### Integration Testing

- End-to-end detection with pipeline projects
- Lazy discovery triggering on first unregistered GID
- Static vs dynamic registration precedence
- Existing detection tests pass unchanged

### Performance Testing

- Discovery time for workspace with 50, 100, 200 projects
- Memory usage measurement
- O(1) lookup verification after discovery

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Q1: Separate class or extend ProjectTypeRegistry?~~ | Architect | Resolved | Composition - ADR-0108 |
| ~~Q2: Lazy discovery trigger point?~~ | Architect | Resolved | On first unregistered GID in async path - ADR-0109 |
| ~~Q3: Per-client or singleton?~~ | Architect | Resolved | Module-level singleton - ADR-0108 |
| ~~Q4: Word boundary matching?~~ | Architect | Resolved | Contains matching with override - ADR-0108 |

All open questions from PRD have been resolved in the technical design.

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Architect | Initial TDD from PRD-WORKSPACE-PROJECT-REGISTRY |

---

## Appendix A: ProcessType to Project Name Matching

Per FR-PIPE-001 and ADR-0108:

| ProcessType | Match Pattern | Example Project Names |
|-------------|---------------|----------------------|
| SALES | `"sales" in name.lower()` | "Sales Pipeline", "Active Sales", "Sales-Process" |
| OUTREACH | `"outreach" in name.lower()` | "Outreach Campaigns", "Email Outreach" |
| ONBOARDING | `"onboarding" in name.lower()` | "Client Onboarding", "Onboarding Process" |
| IMPLEMENTATION | `"implementation" in name.lower()` | "Implementation", "Service Implementation" |
| RETENTION | `"retention" in name.lower()` | "Retention Pipeline", "Client Retention" |
| REACTIVATION | `"reactivation" in name.lower()` | "Reactivation", "Customer Reactivation" |

**Edge Case Handling**:
- If multiple ProcessTypes match, first match wins (order: SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION)
- `GENERIC` is never matched from project names
- Override via environment variable: `ASANA_PIPELINE_{PROCESS_TYPE}={GID}`

---

## Appendix B: Complete API Examples

### Basic Usage (Lazy Discovery)

```python
from autom8_asana.client import AsanaClient
from autom8_asana.models.business.detection import detect_entity_type_async
from autom8_asana.models.business.registry import get_workspace_registry

# Lazy discovery (recommended - no explicit init needed)
client = AsanaClient(token="...")

# First detection for pipeline task triggers discovery automatically
task = await client.tasks.get_async(task_gid)
result = await detect_entity_type_async(task, client)

if result.entity_type == EntityType.PROCESS:
    process = Process.model_validate(task.model_dump())
    print(f"Process in {process.process_type.value} pipeline")
```

### Eager Discovery

```python
# Explicit discovery (optional - for predictable timing)
client = AsanaClient(token="...")
registry = get_workspace_registry()

# Discover before detection
await registry.discover_async(client)

# All lookups are now O(1), no surprise latency
for task_gid in task_gids:
    task = await client.tasks.get_async(task_gid)
    result = await detect_entity_type_async(task, client)
```

### Name Resolution

```python
# Get project GID by name (after discovery)
registry = get_workspace_registry()
await registry.discover_async(client)

sales_gid = registry.get_by_name("Sales Pipeline")
if sales_gid:
    print(f"Sales project GID: {sales_gid}")
```

### ProcessType Lookup

```python
# Get ProcessType for a pipeline project
registry = get_workspace_registry()
await registry.discover_async(client)

process_type = registry.get_process_type(project_gid)
if process_type:
    print(f"Pipeline type: {process_type.value}")
else:
    print("Not a pipeline project")
```

---

## Appendix C: Test Fixture Pattern

```python
import pytest
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
)

@pytest.fixture
def clean_registries():
    """Reset both registries for test isolation."""
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()
    yield
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()

@pytest.fixture
def discovered_registry(clean_registries, mock_client):
    """Registry with mocked discovery complete."""
    registry = get_workspace_registry()
    # Mock discovery with test projects
    registry._name_to_gid = {
        "sales pipeline": "sales_gid_123",
        "onboarding": "onboarding_gid_456",
        "businesses": "business_gid_789",
    }
    registry._gid_to_process_type = {
        "sales_gid_123": ProcessType.SALES,
        "onboarding_gid_456": ProcessType.ONBOARDING,
    }
    registry._discovered_workspace = "workspace_123"
    return registry
```
