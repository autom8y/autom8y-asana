# TDD-09: Registry & Field Seeding

> Consolidated TDD for workspace registry and field seeding configuration.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-WORKSPACE-PROJECT-REGISTRY, TDD-FIELD-SEEDING-CONFIG
- **Related ADRs**: ADR-0031 (Registry and Discovery Architecture), ADR-0055 (State and Discovery Patterns)

---

## Overview

This document consolidates two related systems that work together to enable pipeline automation:

1. **Workspace Project Registry**: Dynamic discovery of pipeline projects and O(1) name-to-GID resolution
2. **Field Seeding Configuration**: Cascading field values from Business/Unit hierarchy to newly created pipeline tasks

These systems enable the core automation use case: when a Sales Process moves to "Converted" section, create an Onboarding task with fields populated from the Business and Unit hierarchy.

---

## Workspace Project Registry

### Purpose

WorkspaceProjectRegistry extends the SDK's entity detection system with dynamic project discovery, enabling Process entities in pipeline projects (Sales, Onboarding, Retention, etc.) to be detected via Tier 1 project membership lookup.

### System Context

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
         |               |  ProjectTypeRegistry   |  (Existing - static)
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

### Component Architecture

```
src/autom8_asana/models/business/
    registry.py                    # Extended with WorkspaceProjectRegistry
        +-- ProjectTypeRegistry    # EXISTING - Static mappings (unchanged)
        +-- WorkspaceProjectRegistry  # NEW - Dynamic workspace discovery
        +-- get_registry()         # EXISTING - Returns ProjectTypeRegistry
        +-- get_workspace_registry()  # NEW - Returns WorkspaceProjectRegistry
```

| Component | Responsibility |
|-----------|---------------|
| WorkspaceProjectRegistry | Workspace discovery, pipeline identification, name-to-GID mapping |
| ProjectTypeRegistry | Static GID-to-EntityType mappings (unchanged) |

### Data Model

```python
class WorkspaceProjectRegistry:
    """Workspace-aware project registry with dynamic pipeline discovery.

    Per ADR-0031: Composes with ProjectTypeRegistry for static lookups.
    Lazy discovery on first unregistered GID lookup.
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

**Memory Budget** (for 100 projects):
- `_name_to_gid`: ~100 entries * ~100 bytes = ~10 KB
- `_gid_to_process_type`: ~10 entries * ~50 bytes = ~500 bytes
- Total: <1 MB (well under 10 MB target)

### API Contract

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

        Idempotent: repeated calls refresh the registry.
        Does NOT overwrite static PRIMARY_PROJECT_GID registrations.

        Raises:
            ValueError: If client.default_workspace_gid is not set.
        """

    async def lookup_or_discover_async(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> EntityType | None:
        """Look up entity type, triggering discovery if needed."""

    def lookup(self, project_gid: str) -> EntityType | None:
        """Sync lookup (static registry only, no discovery)."""

    def get_by_name(self, name: str) -> str | None:
        """Get project GID by name (O(1) after discovery).

        Case-insensitive, whitespace-normalized.
        """

    def get_process_type(self, project_gid: str) -> ProcessType | None:
        """Get ProcessType for a pipeline project."""

    def is_discovered(self) -> bool:
        """Check if workspace discovery has been performed."""

    @classmethod
    def reset(cls) -> None:
        """Reset registry for testing."""
```

### Lazy Discovery Flow

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
    |       |       |       +-- Register with ProjectTypeRegistry
    |       |
    |       +-- Mark _discovered_workspace = workspace_gid
    |       v
    +-- Retry: ProjectTypeRegistry.lookup(project_gid)
            |
            v
        Return EntityType | None
```

### ProcessType Matching

Pipeline projects are identified by case-insensitive contains matching:

| ProcessType | Match Pattern | Example Project Names |
|-------------|---------------|----------------------|
| SALES | `"sales" in name.lower()` | "Sales Pipeline", "Active Sales" |
| OUTREACH | `"outreach" in name.lower()` | "Outreach Campaigns", "Email Outreach" |
| ONBOARDING | `"onboarding" in name.lower()` | "Client Onboarding", "Onboarding Process" |
| IMPLEMENTATION | `"implementation" in name.lower()` | "Implementation", "Service Implementation" |
| RETENTION | `"retention" in name.lower()` | "Retention Pipeline", "Client Retention" |
| REACTIVATION | `"reactivation" in name.lower()` | "Reactivation", "Customer Reactivation" |

**Edge Cases**:
- If multiple ProcessTypes match, first match wins (order: SALES, OUTREACH, ONBOARDING, etc.)
- `GENERIC` is never matched from project names
- Override via environment variable: `ASANA_PIPELINE_{PROCESS_TYPE}={GID}`

---

## Field Seeding Configuration

### Purpose

Configure which custom fields cascade from Business and Unit entities to newly created pipeline tasks during conversion events.

### System Context

```
                    Pipeline Conversion Flow
                    ========================

    [Sales Process] ---(section=Converted)---> [PipelineConversionRule]
                                                       |
                                                       v
                                              [TemplateDiscovery]
                                                       |
                                                       v
                                              [Task Duplication]
                                                       |
                                                       v
                                              [FieldSeeder]
                                                       |
           +-------------------------------------------+
           |                   |                       |
           v                   v                       v
    [Business Cascade]   [Unit Cascade]   [Process Carry-Through]
           |                   |                       |
           +-------------------+-----------------------+
                               |
                               v
                      [write_fields_async()]
                               |
                               v
                      [Onboarding Task Updated]
```

### Component Responsibilities

| Component | Responsibility | Configuration Point |
|-----------|----------------|---------------------|
| `FieldSeeder` | Collect and write cascade/carry-through fields | Uses configured field lists |
| `PipelineStage` | Configuration for target project and field lists | **Configure here** |
| `PipelineConversionRule` | Orchestrates conversion, creates FieldSeeder | Passes stage config to FieldSeeder |
| `AutomationConfig` | Holds pipeline_stages map | Container for PipelineStage |

### Design Decision: Configure PipelineStage

**Chosen Approach**: Configure explicit field lists in `PipelineStage` for each pipeline.

**Rationale**:
1. **Safety**: Does not affect other pipelines or future pipelines
2. **Explicitness**: Field lists are visible in the configuration
3. **Flexibility**: Different pipelines can have different field lists
4. **Target-Aware**: Only fields that exist on the target project should be listed

**Rejected Alternative**: Update `FieldSeeder.DEFAULT_*_CASCADE_FIELDS`
- Risk: Affects all pipelines globally
- Problem: Fields may not exist on all target projects

### Field Configuration Example

```python
"onboarding": PipelineStage(
    project_gid=onboarding_project_gid,
    target_section="Opportunity",
    due_date_offset_days=7,
    business_cascade_fields=[
        "Office Phone",
    ],
    unit_cascade_fields=[
        "Vertical",
        "Products",
        "MRR",
        "Rep",
        "Platforms",
        "Booking Type",
    ],
    process_carry_through_fields=[
        "Contact Phone",
        "Priority",
    ],
    field_name_mapping={},  # Source -> target if names differ
),
```

### Available Fields by Entity

#### Business Model Fields

| Field | Descriptor | Cascading |
|-------|------------|-----------|
| `office_phone` | TextField | Yes |
| `company_id` | TextField | Yes (verify target has it) |
| `rep` | PeopleField | Used for assignee resolution |

#### Unit Model Fields

| Field | Descriptor | Notes |
|-------|------------|-------|
| `vertical` | EnumField | CascadingFields.VERTICAL |
| `products` | MultiEnumField | Multiple values supported |
| `mrr` | NumberField | Note: uppercase field_name="MRR" |
| `rep` | PeopleField | Cascade for Rep field |
| `platforms` | MultiEnumField | CascadingFields.PLATFORMS |
| `booking_type` | EnumField | CascadingFields.BOOKING_TYPE |

#### Process Model Fields (Carry-Through)

| Field | Type | Notes |
|-------|------|-------|
| `contact_phone` | TextField | Via Contact entity |
| `priority` | EnumField | Process-level field |

---

## Discovery Patterns

### Lazy vs Eager Discovery

**Lazy Discovery (Recommended)**:
```python
# No explicit init needed - discovery triggers on first unregistered GID
client = AsanaClient(token="...")
task = await client.tasks.get_async(task_gid)
result = await detect_entity_type_async(task, client)  # Triggers discovery
```

**Eager Discovery** (for predictable timing):
```python
# Explicit discovery before detection
registry = get_workspace_registry()
await registry.discover_async(client)  # One-time cost upfront

# All subsequent lookups are O(1)
for task_gid in task_gids:
    task = await client.tasks.get_async(task_gid)
    result = await detect_entity_type_async(task, client)
```

### Name Resolution

```python
# Get project GID by name (after discovery)
registry = get_workspace_registry()
await registry.discover_async(client)

sales_gid = registry.get_by_name("Sales Pipeline")  # O(1) lookup
```

### Template Discovery Pattern

From ADR-0055, templates are discovered via fuzzy section matching:

```python
class TemplateDiscovery:
    async def find_template_section_async(
        self, project_gid: str
    ) -> Section | None:
        """Find template section via fuzzy name matching.

        Patterns matched (case-insensitive):
        - "template"
        - "templates"
        - "template tasks"
        - "process templates"
        """
```

---

## Testing Strategy

### Unit Testing

**WorkspaceProjectRegistry**:
- Registry in isolation with mocked ProjectsClient
- Pipeline identification logic with various project names
- Name-to-GID lookup (case insensitivity, whitespace)
- ProcessType derivation from pipeline GIDs
- Idempotent discovery behavior
- Reset for test isolation

**Field Seeding**:
- Existing tests in `tests/unit/models/business/` cover FieldSeeder
- No new unit tests required for configuration-only changes

### Integration Testing

**Registry**:
- End-to-end detection with pipeline projects
- Lazy discovery triggering on first unregistered GID
- Static vs dynamic registration precedence
- Existing detection tests pass unchanged

**Field Seeding** (manual verification):
1. Create Sales Process with populated Unit fields
2. Move to "Converted" section
3. Verify Onboarding task has cascaded fields

### Test Fixture Pattern

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
    registry._name_to_gid = {
        "sales pipeline": "sales_gid_123",
        "onboarding": "onboarding_gid_456",
    }
    registry._gid_to_process_type = {
        "sales_gid_123": ProcessType.SALES,
        "onboarding_gid_456": ProcessType.ONBOARDING,
    }
    registry._discovered_workspace = "workspace_123"
    return registry
```

### Performance Testing

- Discovery time for workspace with 50, 100, 200 projects
- Memory usage measurement (<10 MB for 100 projects)
- O(1) lookup verification after discovery

---

## Observability

### Registry Metrics

- `workspace_registry.discovery_time_seconds`: Time to complete discovery
- `workspace_registry.projects_discovered`: Number of projects found
- `workspace_registry.pipeline_projects_registered`: Number of pipeline projects

### Registry Logging

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
```

### Field Seeding Logging

```
[SEEDING] seed_fields_async called - Business: {name}, Unit: {name}, Process: {name}
[SEEDING] Cascade fields collected: {dict}
[SEEDING] Carry-through fields collected: {dict}
[SEEDING] Computed fields: {dict}
[SEEDING] Final seeded fields: {dict}
[SEEDING] WriteResult: written=[fields], skipped=[fields]
```

**Success Criteria**:
- `Cascade fields collected` includes configured fields
- `WriteResult: written=[...]` includes the configured fields
- `skipped=[]` is empty or contains only intentionally omitted fields

---

## Risks & Mitigations

### Registry Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Contains matching too greedy ("Salesforce" matches "sales") | Med | Low | Environment variable override; documented limitation |
| First detection latency surprises users | Low | Med | Document discovery timing; provide explicit `discover_async()` |
| Discovery fails (API error, rate limit) | Med | Low | Log warning; fall through to Tier 2+ detection |

### Field Seeding Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Field name mismatch | Fields silently skipped | Medium | Verify field names against target project |
| Enum value mismatch | Field skipped with warning | Medium | FieldSeeder logs enum resolution failures |
| Rep field empty | Assignee not set | Low | Separate assignee logic handles this |

---

## Cross-References

**Architecture Decisions**:
- [ADR-0031: Registry and Discovery Architecture](../decisions/ADR-0031-registry-and-discovery.md)
- [ADR-0055: State and Discovery Patterns](../decisions/ADR-0055-state-discovery-patterns.md)

**Related TDDs**:
- [TDD-08: Business Domain](TDD-08-business-domain.md) - Business entity definitions
- [TDD-06: Custom Fields](TDD-06-custom-fields.md) - Custom field infrastructure

**Requirements** (archived):
- PRD-WORKSPACE-PROJECT-REGISTRY
- PRD-FIELD-SEEDING-GAP

---

## Implementation Estimates

| Component | Deliverable | Estimate |
|-----------|-------------|----------|
| Registry | WorkspaceProjectRegistry class | 2 hours |
| Registry | `discover_async()` implementation | 2 hours |
| Registry | Detection integration | 2 hours |
| Registry | Unit and integration tests | 4 hours |
| Seeding | PipelineStage configuration update | 30 min |
| Seeding | Field name verification | 30 min |

**Total**: ~11 hours (1.5 developer days)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from TDD-WORKSPACE-PROJECT-REGISTRY and TDD-FIELD-SEEDING-CONFIG |
