# ADR-008: Entity Creation -- Engine Delegates to Entity Model Layer

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

During lifecycle transitions, new entities must be created (Onboarding process, BackendOnboardABusiness play, AssetEdit, SourceVideographer). The stakeholder confirmed the engine should delegate entity creation to the entity model layer.

A critical constraint: dependency wiring MUST be a SEPARATE phase from entity creation because Asana API requires a valid GID before dependency links can reference the entity.

Entity creation uses two approaches (confirmed in spike):
- **Templates** for processes: Processes have subtasks, structure, and embedded configuration
- **Direct creation** for simpler entities: Field seeding from parent/sibling entities

## Decision

**The lifecycle engine delegates all entity creation to an EntityCreationService that coordinates with the entity model layer, then performs dependency wiring as a separate phase.**

### Multi-Phase Orchestration

Entity creation follows a strict phase order:

```
Phase 1: RESOLVE    -- Resolve all entities needed for creation context
Phase 2: CREATE     -- Create entity (template duplication or direct creation)
Phase 3: CONFIGURE  -- Seed fields, set assignee, move to section
Phase 4: WIRE       -- Add dependency links (requires valid GIDs from Phase 2)
Phase 5: VERIFY     -- Confirm creation succeeded, log diagnostics
```

Phases are sequential, not concurrent, because each phase depends on the previous phase's output.

### EntityCreationService

```python
class EntityCreationService:
    """Coordinates entity creation with proper phasing."""

    async def create_process_async(
        self,
        stage_config: StageConfig,
        resolution_ctx: ResolutionContext,
        trigger_process: Process,
    ) -> CreationResult:
        """Create a new process entity from template."""
        # Phase 1: Resolve
        business = await resolution_ctx.business_async()
        unit = await resolution_ctx.unit_async()
        template = await self._template_discovery.find_template_async(
            stage_config.project_gid,
            stage_config.template_section,
        )

        # Phase 2: Create
        new_task = await self._client.tasks.duplicate_async(
            template.gid,
            name=self._generate_name(template.name, business, unit),
            include=["subtasks", "notes"],
        )

        # Phase 3: Configure
        await self._configure_entity_async(new_task, stage_config, resolution_ctx)

        # Phase 4: Wire
        await self._wire_dependencies_async(new_task, stage_config, resolution_ctx)

        # Phase 5: Verify + cache
        resolution_ctx.cache_entity(new_task)
        return CreationResult(entity_gid=new_task.gid, success=True)
```

### Template vs Direct Creation

The service selects creation strategy based on entity type:

| Entity | Strategy | Rationale |
|--------|----------|-----------|
| Pipeline processes (Sales, Onboarding, etc.) | Template duplication | Processes have subtasks and structured content |
| BackendOnboardABusiness (Play) | Template duplication | Play template in BackendOnboardABusiness project |
| AssetEdit | Template duplication | Process subclass with subtask structure |
| SourceVideographer | Template duplication | Process under VideographyHolder |
| Hours, Location, simple entities | Direct creation + field seeding | No subtask structure needed |

### Dependency Wiring Rules

Wiring rules are declarative YAML alongside stage config:

```yaml
dependency_wiring:
  pipeline_default:
    dependents: [unit, offer_holder]  # Pipeline processes depend on Unit + OfferHolder
    dependencies: [open_dna_plays]     # Open plays block pipeline progress
  backend_onboard:
    dependency_of: implementation      # Play is a dependency of Implementation
  asset_edit:
    dependency_of: implementation      # AssetEdit is a dependency of Implementation
```

### Duplicate Detection

Before Phase 2, the service checks for existing entities to prevent double-creation:

```python
async def _check_duplicate_async(
    self,
    target_project_gid: str,
    business: Business,
    unit: Unit,
) -> str | None:
    """Check if entity already exists. Return GID if found."""
    # List tasks in target project matching the expected name pattern
    existing = await self._find_matching_task_async(
        target_project_gid, business.name, unit.name
    )
    return existing.gid if existing else None
```

## Alternatives Considered

### Engine Owns Creation (Rejected)

The lifecycle engine directly calls Asana API to create tasks. This tightly couples the engine to API details (template discovery, task duplication, field seeding) that belong in the entity layer.

### Atomic Create+Wire (Rejected)

Attempting to create entity and wire dependencies in a single operation. Asana API does not support this -- dependency API calls require valid GIDs, which only exist after creation completes.

### Concurrent Phase 2+3 (Rejected)

Creating entity and configuring it in parallel. Configuration (field seeding, section placement) requires the created task's GID and custom_field definitions, which are only available after creation completes.

## Consequences

### Positive

- Entity model layer owns entity semantics; engine owns orchestration
- Multi-phase design respects Asana API constraint (GID required before wiring)
- Template vs direct creation is a strategy decision per entity type, not per workflow
- Duplicate detection prevents re-creation on retry (idempotency)
- Dependency wiring rules are declarative and auditable

### Negative

- Sequential phases mean creation is not parallelizable (Phase 2 -> 3 -> 4 must be serial)
- Duplicate detection adds 1 API call per creation attempt
- Wiring rules YAML adds another configuration surface to validate

### Play Entity -- Minimum Viable Modeling

For lifecycle support, the DNA model needs:
- `dna_priority` (EnumField) -- for tier routing during init
- `intercom_link` (TextField) -- for linking to customer conversations
- `tier_reached` (EnumField) -- for section routing
- `automation` (EnumField) -- for identifying automated plays

This is 4 fields added to the existing DNA stub. No behavioral methods needed initially -- the lifecycle engine handles creation and wiring, and the resolution system handles field access.

BackendOnboardABusiness is modeled as a template-based creation in the BackendOnboardABusiness project (GID: 1207507299545000), not as a Python subclass. The legacy multi-inheritance pattern (Play extends Process + Dna) is explicitly avoided.

### Products Field Expansion

The Products MultiEnumField on Unit/Process is designed for expansion:
- Products enum values are Asana-defined (added in Asana workspace, not code)
- Products-driven entity creation uses `startswith` matching (e.g., `"video*"`)
- New products that do not trigger entity creation require zero code changes
- New products that DO trigger entity creation require one plugin addition
