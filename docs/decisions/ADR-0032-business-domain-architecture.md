# ADR-0032: Business Domain Architecture

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0101, ADR-0105, ADR-0136
- **Related**: TDD-AUTOMATION-LAYER, PRD-TECH-DEBT-REMEDIATION

## Context

The autom8_asana business domain layer models complex hierarchical relationships (Business > Unit > ProcessHolder > Process) with pipeline-specific behavior. Three critical architectural questions shape this layer:

1. **What is the relationship between Processes and pipelines?** - Initial design assumed separate "pipeline projects"; reality proved different
2. **How should field values be seeded** when creating new entities from hierarchy cascade, source carry-through, and computed values?
3. **How should Process field organization handle** 67+ Sales fields, 41+ Onboarding fields, and 35+ Implementation fields?

These decisions affect domain model correctness, automation rule implementation, and long-term maintainability.

## Decision

We establish a **three-component business domain architecture**: canonical projects as pipelines, dedicated field seeding service, and composition-based Process field organization.

### 1. Process Pipeline Architecture

**Canonical projects ARE the pipelines. Remove ProcessProjectRegistry entirely.**

**Corrected model**:
```
INCORRECT (prior assumption):
  Process
    ├── Hierarchy: subtask of ProcessHolder
    └── Pipeline: ADDED to separate "Sales Pipeline" project

CORRECT:
  Process
    ├── Hierarchy: subtask of ProcessHolder
    └── Pipeline: MEMBER of canonical project (e.g., "Sales")
                  The canonical project HAS sections = pipeline states
```

**Key insight**: Process entities receive their project membership through:
1. Creation in the canonical project (via BusinessSeeder or API)
2. Inheritance from parent Unit context (Unit.PRIMARY_PROJECT_GID determines which canonical project)

**Evidence from domain analysis**:
- Asana project named "Sales" contains Processes in sections: Opportunity, Active, Scheduled, etc.
- These sections ARE the pipeline states
- No separate "Sales Pipeline" project exists
- The project IS both the entity registry AND the pipeline view

**Removed**:
- `ProcessProjectRegistry` singleton and all registry lookup logic (~600 lines)
- `add_to_pipeline()` method (concept was wrong)
- `move_to_state()` wrapper (use `SaveSession.move_to_section()` directly)
- `AUTOM8_PROCESS_PROJECT_*` environment variables

**Simplified implementations**:

**pipeline_state**: Extract from canonical project section membership
```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """Get current pipeline state from canonical project section membership."""
    if not self.memberships:
        return None

    # Find membership in canonical project (primary project for this entity)
    for membership in self.memberships:
        project_gid = membership.get("project", {}).get("gid")
        section_name = membership.get("section", {}).get("name")
        if section_name:
            return ProcessSection.from_name(section_name)

    return None
```

**process_type**: Derive from canonical project name matching
```python
@property
def process_type(self) -> ProcessType:
    """Derive process type from canonical project name."""
    if not self.memberships:
        return ProcessType.GENERIC

    for membership in self.memberships:
        project_name = membership.get("project", {}).get("name", "").lower()

        # Direct name matching
        for pt in ProcessType:
            if pt != ProcessType.GENERIC and pt.value in project_name:
                return pt

    return ProcessType.GENERIC
```

**Rationale**:
- **Matches actual Asana implementation**: Processes don't get "added to pipelines"; they're created as members of canonical projects
- **Eliminates configuration burden**: No need to configure pipeline project GIDs
- **Simplifies detection**: Only ProjectTypeRegistry needed (not dual registry system)
- **Removes ~1,000 lines of incorrect code**: ProcessProjectRegistry, tests, consumers
- **Cleaner mental model**: Canonical project IS the pipeline

### 2. Field Seeding Service

**Create dedicated `FieldSeeder` service separate from entity creation and rule execution.**

**Architecture**:
```python
class FieldSeeder:
    """Computes field values from hierarchy and carry-through."""

    # Cascade from Business (lowest priority)
    BUSINESS_CASCADE_FIELDS = [
        "Office Phone", "Company ID", "Business Name", "Primary Contact Phone"
    ]

    # Cascade from Unit
    UNIT_CASCADE_FIELDS = ["Vertical", "Platforms", "Booking Type"]

    # Carry-through from source Process
    PROCESS_CARRY_THROUGH_FIELDS = ["Contact Phone", "Priority", "Assigned To"]

    async def cascade_from_hierarchy_async(
        self, business: Business | None, unit: Unit | None
    ) -> dict[str, Any]:
        """Extract cascading fields from Business and Unit hierarchy."""
        fields = {}
        if business:
            for field_name in self.BUSINESS_CASCADE_FIELDS:
                value = getattr(business, field_name, None)
                if value is not None:
                    fields[field_name] = value
        if unit:
            for field_name in self.UNIT_CASCADE_FIELDS:
                value = getattr(unit, field_name, None)
                if value is not None:
                    fields[field_name] = value
        return fields

    async def carry_through_from_process_async(
        self, source_process: Process
    ) -> dict[str, Any]:
        """Extract carry-through fields from source Process."""
        fields = {}
        for field_name in self.PROCESS_CARRY_THROUGH_FIELDS:
            value = getattr(source_process, field_name, None)
            if value is not None:
                fields[field_name] = value
        return fields

    async def compute_fields_async(
        self, source_process: Process
    ) -> dict[str, Any]:
        """Compute derived values (e.g., Started At = today)."""
        return {
            "Started At": datetime.utcnow().date(),
        }

    async def seed_fields_async(
        self, business, unit, source_process
    ) -> dict[str, Any]:
        """Combine all sources: cascade + carry-through + computed."""
        fields = {}
        fields.update(await self.cascade_from_hierarchy_async(business, unit))
        fields.update(await self.carry_through_from_process_async(source_process))
        fields.update(await self.compute_fields_async(source_process))
        return fields
```

**Field precedence** (later sources override earlier):
1. Cascade from Business (lowest priority)
2. Cascade from Unit
3. Carry-through from source Process
4. Computed fields (highest priority)

**Consumer usage**:
```python
# In automation rule
seeder = FieldSeeder()
fields = await seeder.seed_fields_async(business, unit, source_process)

# Use seeded fields when creating new Process
new_process = await session.create_process_async(
    name=f"{source_process.name} - Onboarding",
    parent=unit.process_holder_gid,
    custom_fields=fields,
)
```

**Rationale**:
- **Single responsibility**: FieldSeeder only computes values; doesn't create entities
- **Testability**: Can unit test field seeding independently of entity creation
- **Reusability**: Same seeder works for any automation rule, not just pipeline conversion
- **Clarity**: Field sources (cascade vs carry-through vs computed) are explicit
- **Separation from BusinessSeeder**: BusinessSeeder creates entity hierarchy; FieldSeeder computes field values

### 3. Process Field Organization

**Use COMPOSITION with field groups on single Process class, NOT inheritance.**

All pipeline fields are defined on the single `Process` class, organized into logical field groups:

```python
class Process(BusinessEntity):
    """Process entity supporting all pipeline types.

    Fields are organized into groups:
    - Common fields: Available on all process types
    - Sales fields: Specific to Sales pipeline
    - Onboarding fields: Specific to Onboarding pipeline
    - Implementation fields: Specific to Implementation pipeline

    All fields are accessible on any Process instance. Accessing a
    field that doesn't exist on the underlying Asana task returns None.
    """

    # === COMMON FIELDS (8, shared across all pipelines) ===
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    process_notes = TextField(field_name="Process Notes")
    status = EnumField()
    priority = EnumField()
    vertical = EnumField()
    process_due_date = TextField(field_name="Due Date")
    assigned_to = PeopleField()

    # === SALES PIPELINE FIELDS (54+) ===
    # Financial
    deal_value = NumberField(field_name="Deal Value")
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField(field_name="Weekly Ad Spend")

    # Dates
    close_date = DateField(field_name="Close Date")
    demo_date = DateField(field_name="Demo Date")
    follow_up_date = DateField(field_name="Follow Up Date")

    # Stage tracking
    sales_stage = EnumField(field_name="Sales Stage")
    lead_source = EnumField(field_name="Lead Source")
    lost_reason = EnumField(field_name="Lost Reason")

    # Assignment
    rep = PeopleField(field_name="Rep")
    closer = PeopleField(field_name="Closer")

    # ... (additional Sales fields)

    # === ONBOARDING PIPELINE FIELDS (33+) ===
    onboarding_status = EnumField(field_name="Onboarding Status")
    go_live_date = DateField(field_name="Go Live Date")
    kickoff_completed = EnumField(field_name="Kickoff Completed")
    # ... (additional Onboarding fields)

    # === IMPLEMENTATION PIPELINE FIELDS (28+) ===
    implementation_status = EnumField(field_name="Implementation Status")
    delivery_date = DateField(field_name="Delivery Date")
    # ... (additional Implementation fields)
```

**Field access pattern**:
```python
# All fields available on all Process instances
process = await Process.from_gid_async(client, gid)

# Sales fields (returns None if not a Sales process)
process.deal_value      # Decimal | None
process.close_date      # date | None
process.sales_stage     # str | None

# Onboarding fields (returns None if not an Onboarding process)
process.go_live_date    # date | None
```

**Runtime type checking pattern**:
```python
if process.process_type == ProcessType.SALES:
    # Access Sales-specific fields
    value = process.deal_value
    stage = process.sales_stage
elif process.process_type == ProcessType.ONBOARDING:
    # Access Onboarding-specific fields
    go_live = process.go_live_date
```

**Rationale**:
- **Runtime type determination**: Process type is determined by Asana project membership at runtime, not compile time. Creating typed subclasses would require post-hoc casting.
- **No polymorphism benefit**: Code paths don't branch based on Process subtype. All processes are processed uniformly.
- **Field overlap handling**: Many fields exist in multiple pipelines with same semantics. Inheritance would duplicate or require complex diamond patterns.
- **SDK ergonomics**: Single Process class means no type narrowing needed by consumers.
- **Descriptor behavior**: Custom field descriptors gracefully return `None` when field doesn't exist on underlying task.
- **Consistent with entity patterns**: Matches other entity field access patterns in the system.

**Why not inheritance**:
- Requires casting: `sales_process = cast(SalesProcess, process)` - burden on consumers
- Duplicate shared fields: Many fields (vertical, rep, close_date) exist in multiple pipelines
- No compile-time benefit: Process type unknown until runtime (project membership check)

## Consequences

### Positive

**Process Pipeline Architecture**:
- ~1,000 lines of code removed (ProcessProjectRegistry, tests, consumers)
- Simpler mental model: Canonical project IS the pipeline
- No configuration burden: No AUTOM8_PROCESS_PROJECT_* env vars
- Cleaner detection: Only ProjectTypeRegistry needed
- Preserved functionality: pipeline_state still works, ProcessSection.from_name() unchanged
- Backward compatible: ProcessType.GENERIC still valid

**Field Seeding Service**:
- Single responsibility: Computes values, doesn't create entities
- Testability: Unit test field seeding independently
- Reusability: Same seeder for any automation rule
- Clarity: Explicit field source precedence
- Separation: BusinessSeeder creates hierarchy, FieldSeeder computes values

**Process Field Organization**:
- Single class simplicity: No casting or type narrowing needed
- Full IDE support: All fields visible for autocomplete
- Type safety: Typed descriptors provide `None` safety
- Graceful degradation: Accessing non-existent field returns `None`
- Consistent pattern: Matches other entity field access patterns
- Easy maintenance: Add fields to existing class; no inheritance complexity

### Negative

**Process Pipeline Architecture**:
- move_to_state() removed: Consumers need section GIDs (minor burden)
- process_type detection is heuristic: Based on project name matching (acceptable for current domain)
- Multi-project edge case: If Process in multiple projects, behavior undefined (log warning)

**Field Seeding Service**:
- New abstraction: Another class to understand and maintain
- Coordination: Rule must orchestrate seeder + entity creation

**Process Field Organization**:
- Large class: 80+ field descriptors on Process (mitigated by organization with comments)
- Field pollution: Sales fields visible on Onboarding processes (returns `None`)
- No compile-time type narrowing: Can access `deal_value` on non-Sales process (runtime check needed)

### Neutral

**Process Pipeline Architecture**:
- ProcessType enum retained: Still useful for categorization, derived differently
- ProcessSection enum retained: from_name() parsing remains valuable
- Related ADRs need updates: Seeder and state transition patterns simplified

**Field Seeding Service**:
- Field lists require maintenance: Must update when new fields added to pipelines
- Precedence rules documented: Clear ordering prevents confusion

**Process Field Organization**:
- Process class file grows significantly (acceptable; well-organized with field groups)
- No changes to detection or hydration logic
- Field groups provide logical organization

## Implementation Notes

### Pipeline Architecture Cleanup

**Removed**:
```python
# Delete entirely
src/autom8_asana/models/business/process_registry.py
tests/unit/models/business/test_process_registry.py

# Remove from BusinessSeeder
# - ProcessProjectRegistry import
# - registry.get_project_gid(process_type) lookup
# - session.add_to_project(proc, project_gid) for pipeline
# - section_gid lookup and move_to_section

# Update SeederResult
@dataclass
class SeederResult:
    # ... other fields ...
    # REMOVED: added_to_pipeline: bool
```

**Simplified**:
```python
# Process inherits project membership from hierarchy
# No special "add to pipeline" operation needed
async def seed_async(...):
    process = await session.create_async(
        name=name,
        parent=process_holder.gid,
        # Process becomes member of canonical project through hierarchy
    )
    return SeederResult(process=process, ...)
```

### Field Seeding Integration

```python
# Example automation rule using FieldSeeder
class PipelineConversionRule(AutomationRule):
    async def execute_async(self, trigger: Trigger, session: SaveSession) -> RuleResult:
        source_process = trigger.entity

        # Get hierarchy context
        business = await self._get_business_async(source_process)
        unit = await self._get_unit_async(source_process)

        # Compute seeded fields
        seeder = FieldSeeder()
        fields = await seeder.seed_fields_async(business, unit, source_process)

        # Create new Process with seeded fields
        new_process = await session.create_process_async(
            name=f"{source_process.name} - Onboarding",
            parent=unit.process_holder_gid,
            custom_fields=fields,
        )

        return RuleResult(actions=[CreateAction(new_process)])
```

### Process Field Access Example

```python
# Type-safe field access with runtime checks
async def process_sales_opportunity(process: Process) -> None:
    if process.process_type != ProcessType.SALES:
        raise ValueError("Expected Sales process")

    # Sales-specific fields
    deal_value: Decimal | None = process.deal_value
    close_date: date | None = process.close_date
    sales_stage: str | None = process.sales_stage

    if deal_value and deal_value > 10000:
        # High-value deal logic
        ...
```

## Compliance

### Pipeline Architecture Validation
- [ ] ProcessProjectRegistry deleted
- [ ] Detection uses only ProjectTypeRegistry
- [ ] add_to_pipeline() removed
- [ ] pipeline_state simplified (no registry lookup)
- [ ] process_type derives from project name
- [ ] move_to_state() removed
- [ ] BusinessSeeder simplified (no pipeline logic)
- [ ] All tests pass after cleanup

### Field Seeding Requirements
- FieldSeeder MUST have three methods: cascade_from_hierarchy_async, carry_through_from_process_async, compute_fields_async
- seed_fields_async MUST apply precedence: Business < Unit < Process < Computed
- Field lists MUST be documented with source entity
- Tests MUST verify precedence ordering

### Process Field Organization Standards
- All pipeline fields MUST use descriptor pattern per ADR-0081
- Field groups MUST be clearly commented in Process class
- Fields conflicting with Task properties MUST use `process_` prefix
- Process.process_type MUST be used for pipeline-specific logic branches
- Tests MUST verify None return for fields not present on task
- Documentation MUST list which fields apply to which pipeline

## Related Decisions

**Foundation**: See ADR-0029 for AsanaResource entity boundary that Process extends.

**Registry**: See ADR-0031 for entity registry and workspace discovery that Process detection uses.

**Patterns**: See ADR-SUMMARY-PATTERNS for custom field descriptors and cascading field patterns.

**Automation**: See TDD-AUTOMATION-LAYER for automation rule patterns that use FieldSeeder.

## References

**Original ADRs**:
- ADR-0101: Process Pipeline Architecture Correction (2025-12-17)
- ADR-0105: Field Seeding Architecture (2025-12-17)
- ADR-0136: Process Field Architecture (2025-12-19)

**Technical Design**:
- TDD-AUTOMATION-LAYER: Automation rule execution
- TDD-TECH-DEBT-REMEDIATION: Process field expansion

**Requirements**:
- PRD-AUTOMATION-LAYER FR-005: Field seeding from hierarchy
- PRD-TECH-DEBT-REMEDIATION FR-PROC-001, FR-PROC-002, FR-PROC-003
- ADR-0081: Custom Field Descriptors
- ADR-0054: Cascading Custom Fields
