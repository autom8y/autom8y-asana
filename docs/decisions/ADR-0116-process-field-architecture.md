# ADR-0116: Process Field Accessor Architecture

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-19
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-TECH-DEBT-REMEDIATION (FR-PROC-001, FR-PROC-002, FR-PROC-003, OQ-2), ADR-0081 (Custom Field Descriptors), TDD-TECH-DEBT-REMEDIATION

## Context

The Process entity currently has only 8 generic fields while actual Asana projects contain significantly more:
- **Sales pipeline**: 67+ fields
- **Onboarding pipeline**: 41+ fields
- **Implementation pipeline**: 35+ fields

**OQ-2 from PRD: How should composition vs inheritance be used for Process pipeline variants?**

### Current State

```python
class Process(BusinessEntity):
    # 8 generic fields
    started_at = TextField()
    process_completed_at = TextField(field_name="Process Completed At")
    process_notes = TextField(field_name="Process Notes")
    status = EnumField()
    priority = EnumField()
    vertical = EnumField()
    process_due_date = TextField(field_name="Due Date")
    assigned_to = PeopleField()
```

### Design Options

1. **Inheritance**: Create `SalesProcess(Process)`, `OnboardingProcess(Process)`, etc.
2. **Composition**: Add all fields to single Process class, accessed based on `process_type`
3. **Mixin composition**: Create field groups as mixins, compose into Process

### Forces

1. **Field overlap**: Many fields are shared across pipelines (e.g., `vertical`, `rep`, `close_date`)
2. **Runtime type**: Process type is determined by project membership, not at class definition
3. **SDK simplicity**: Users should not need to cast or handle multiple Process classes
4. **Type safety**: IDE autocomplete should work for pipeline-specific fields
5. **Maintenance**: 54+ Sales fields is significant; must be manageable
6. **Descriptor pattern**: Existing ADR-0081 pattern handles field access via descriptors

## Decision

**Use COMPOSITION with field groups, NOT inheritance.** All pipeline fields are defined on the single `Process` class, organized into logical field groups. Access to pipeline-specific fields works regardless of process type, returning `None` when the field doesn't exist on the underlying task.

### Architecture

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

### Why Composition Over Inheritance

1. **Runtime type determination**: Process type is determined by Asana project membership at runtime, not compile time. Creating typed subclasses would require post-hoc casting.

2. **No polymorphism benefit**: Code paths don't branch based on Process subtype. All processes are processed uniformly.

3. **Field overlap handling**: Many fields exist in multiple pipelines with same semantics. Inheritance would duplicate or require complex diamond patterns.

4. **SDK ergonomics**: Single Process class means no type narrowing needed by consumers.

5. **Descriptor behavior**: ADR-0081 descriptors gracefully return `None` when field doesn't exist on task.

### Field Organization Pattern

Fields are organized in logical groups with clear comments:

```python
class Process(BusinessEntity):
    # === COMMON FIELDS ===
    # Fields that exist on ALL process types

    # === SALES PIPELINE FIELDS ===
    # Fields specific to Sales pipeline
    # Grouped by: Financial, Dates, Stage tracking, Assignment, Contact info, etc.

    # === ONBOARDING PIPELINE FIELDS ===
    # Fields specific to Onboarding pipeline

    # === IMPLEMENTATION PIPELINE FIELDS ===
    # Fields specific to Implementation pipeline
```

### Field Naming Convention

When Asana field names conflict with Python keywords or Task properties:
- Prefix with `process_` for conflicts with Task: `process_completed_at`, `process_notes`
- Use descriptive names for pipeline fields: `sales_stage`, `onboarding_status`

### Type Checking Support

For IDE autocomplete and type checking, Process exposes all fields:

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

### Runtime Type Check Pattern

When pipeline-specific logic is needed:

```python
if process.process_type == ProcessType.SALES:
    # Access Sales-specific fields
    value = process.deal_value
    stage = process.sales_stage
elif process.process_type == ProcessType.ONBOARDING:
    # Access Onboarding-specific fields
    go_live = process.go_live_date
```

## Alternatives Considered

### Alternative A: Inheritance with Typed Subclasses

- **Description**: Create `SalesProcess(Process)`, `OnboardingProcess(Process)`, etc.
- **Pros**: Type-safe field access; clear separation; smaller classes
- **Cons**: Runtime type unknown at instantiation; requires casting; duplicate shared fields
- **Why not chosen**: Process type determined by project membership at runtime; casting burden on consumers

### Alternative B: Field Mixins Composed at Runtime

- **Description**: Dynamically compose field mixins based on process_type
- **Pros**: Smaller base class; fields only present when relevant
- **Cons**: Dynamic composition is complex; loses static type checking; metaclass magic
- **Why not chosen**: Complexity exceeds benefit; loses IDE support

### Alternative C: Separate Field Accessors per Pipeline

- **Description**: `process.sales.deal_value`, `process.onboarding.go_live_date`
- **Pros**: Clear namespace separation; smaller autocomplete
- **Cons**: Nested access is verbose; requires proxy objects; breaks existing patterns
- **Why not chosen**: Inconsistent with other entity patterns; verbose access

### Alternative D: Generic Field Access Only

- **Description**: Keep Process generic; access fields via `process.get_custom_field("Deal Value")`
- **Pros**: No maintenance burden; works for any field
- **Cons**: No type safety; no autocomplete; error-prone string-based access
- **Why not chosen**: Violates type safety goals; poor developer experience

## Consequences

### Positive

- **Single class simplicity**: No casting or type narrowing needed
- **Full IDE support**: All fields visible for autocomplete
- **Type safety**: Typed descriptors provide `None` safety
- **Graceful degradation**: Accessing non-existent field returns `None`
- **Consistent pattern**: Matches other entity field access patterns
- **Easy maintenance**: Add fields to existing class; no inheritance complexity

### Negative

- **Large class**: 80+ field descriptors on Process (mitigated by organization)
- **Field pollution**: Sales fields visible on Onboarding processes (returns `None`)
- **No compile-time type narrowing**: Can access `deal_value` on non-Sales process

### Neutral

- Process class file grows significantly (acceptable; well-organized)
- No changes to detection or hydration logic
- Field groups provide logical organization

## Compliance

- All pipeline fields MUST use descriptor pattern per ADR-0081
- Field groups MUST be clearly commented in Process class
- Fields conflicting with Task properties MUST use `process_` prefix
- Process.process_type MUST be used for pipeline-specific logic branches
- Tests MUST verify None return for fields not present on task
- Documentation MUST list which fields apply to which pipeline
