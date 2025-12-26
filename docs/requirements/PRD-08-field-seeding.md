# PRD-08: Field Seeding Configuration

> Consolidated PRD for field seeding configuration and gap analysis.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-FIELD-SEEDING-GAP
- **Related TDD**: TDD-09-registry-seeding
- **Stakeholders**: Operations Team, SDK Maintainers, Automation Workflows

---

## Executive Summary

Pipeline automation creates Onboarding processes from Sales processes, expecting custom field values to cascade from the entity hierarchy (Business, Unit, source Process) to new tasks. Currently, **only Launch Date is being written** - all other expected fields are absent from target Onboarding tasks.

The root cause is configuration, not code: default cascade field lists are empty or minimal, and no pipeline-specific configuration overrides them. The underlying architecture fully supports the required functionality.

---

## Problem Statement

### The Seeding Gap

When Sales processes convert to Onboarding processes, users expect these fields to auto-populate:

| Expected Field | Source Entity | Actually Seeded? |
|----------------|---------------|------------------|
| Launch Date | Computed | Yes |
| Vertical | Unit | No (in defaults, but see hydration) |
| Products | Unit | No |
| Rep | Unit/Business | No |
| Office Phone | Business | No |
| MRR | Unit | No |
| Platforms | Unit | No |
| Contact Phone | Process | No |

### Root Causes

**1. Empty Business Cascade Defaults**

```python
DEFAULT_BUSINESS_CASCADE_FIELDS: list[str] = []  # EMPTY
```

No fields from Business cascade by default. The code comment explains: "common Business fields like Office Phone, Company ID don't exist on all target projects."

**2. Minimal Unit Cascade Defaults**

```python
DEFAULT_UNIT_CASCADE_FIELDS: list[str] = ["Vertical"]  # Only Vertical
```

Products, Platforms, Booking Type, Rep, and MRR are not in defaults.

**3. Missing Pipeline-Specific Configuration**

`PipelineStage` configuration supports `business_cascade_fields`, `unit_cascade_fields`, `process_carry_through_fields`, and `field_name_mapping` - but none are configured for the onboarding pipeline.

**4. Potential Hydration Issues**

Even fields in defaults require hydrated entities. If `unit` is None or `unit.vertical` is None, nothing cascades.

### Impact

- Manual data entry required for every converted process
- Inconsistent data between Sales and Onboarding processes
- Risk of data entry errors
- Reduced automation ROI

---

## Goals and Non-Goals

### Goals

| ID | Goal | Success Metric |
|----|------|----------------|
| G1 | Configure field cascading for onboarding pipeline | All priority fields populate on conversion |
| G2 | Validate entity hierarchy hydration | Business and Unit resolved before seeding |
| G3 | Document field mapping requirements | Clear source-to-target field mapping |
| G4 | Enable pipeline-specific configuration | `PipelineStage` configured with explicit field lists |

### Non-Goals

- Changing FieldSeeder core architecture
- Adding new field types to the seeding system
- Automatic field discovery across projects
- Modifying default cascade lists globally (unless explicitly decided)

---

## Requirements

### Configuration Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CF-001 | Onboarding `PipelineStage` MUST include explicit `business_cascade_fields` | Must |
| CF-002 | Onboarding `PipelineStage` MUST include explicit `unit_cascade_fields` | Must |
| CF-003 | `Office Phone` MUST be in Business cascade configuration | Must |
| CF-004 | `Products`, `Vertical`, `MRR`, `Rep` MUST be in Unit cascade configuration | Must |
| CF-005 | `Platforms`, `Booking Type` SHOULD be in Unit cascade configuration | Should |
| CF-006 | `field_name_mapping` SHOULD be configured if source/target names differ | Should |

### Hydration Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| HY-001 | Business entity MUST be hydrated before seeding | Must |
| HY-002 | Unit entity MUST be hydrated before seeding | Must |
| HY-003 | Entity hierarchy resolution MUST log when Business/Unit is None | Must |
| HY-004 | Seeding MUST log which fields were written vs skipped | Should |

### Validation Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| VL-001 | Target project MUST have matching custom fields for cascade to succeed | Must |
| VL-002 | Field name mismatches MUST be resolvable via `field_name_mapping` | Must |
| VL-003 | Rep field MUST handle PeopleField format correctly | Must |

---

## User Stories

### US-1: Automatic Field Population on Conversion

```python
# Sales process converts to Onboarding
# Unit has: Vertical="Dental", Products=["Product A", "Product B"], Rep=assigned_user
# Business has: Office Phone="555-1234"

# After conversion, Onboarding task has:
assert onboarding_task.vertical == "Dental"
assert onboarding_task.products == ["Product A", "Product B"]
assert onboarding_task.rep == assigned_user
assert onboarding_task.office_phone == "555-1234"
assert onboarding_task.launch_date == today_date  # Still works
```

### US-2: Pipeline-Specific Configuration

```python
AutomationConfig(
    pipeline_stages={
        "onboarding": PipelineStage(
            project_gid="<onboarding_project_gid>",
            target_section="Opportunity",
            business_cascade_fields=[
                "Office Phone",
                "Company ID",
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
        ),
    },
)
```

### US-3: Field Name Mapping

```python
# Source project uses "Unit MRR", target uses "MRR"
PipelineStage(
    field_name_mapping={
        "Unit MRR": "MRR",
        "Business Phone": "Office Phone",
    },
)
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Vertical populates on conversion | 100% | Integration test |
| Products populates on conversion | 100% | Integration test |
| Office Phone populates on conversion | 100% | Integration test |
| Rep populates on conversion | 100% | Integration test |
| Launch Date continues working | 100% | Regression test |
| Seeding logs show field writes | All fields logged | Log inspection |

---

## Dependencies

### Upstream

| Dependency | Status | Impact |
|------------|--------|--------|
| FieldSeeder implementation | Stable | Core seeding logic |
| PipelineStage configuration | Stable | Configuration structure |
| Entity hierarchy resolution | Stable | Business/Unit hydration |
| Custom field accessor | Stable | Field read/write operations |

### Downstream

| Initiative | Reason |
|------------|--------|
| Additional pipeline automation | Uses same seeding pattern |
| Contact field seeding | Extends carry-through configuration |

---

## Entity Field Inventory

### Business Cascade Candidates

| Field | Type | CascadingFields Target | Recommendation |
|-------|------|------------------------|----------------|
| `office_phone` | TextField | Unit, Offer, Process, Contact | Add to cascade |
| `company_id` | TextField | All descendants | Add to cascade |
| `rep` | PeopleField | N/A (used for assignee) | Add to cascade |

### Unit Cascade Candidates

| Field | Type | CascadingFields Target | Recommendation |
|-------|------|------------------------|----------------|
| `vertical` | EnumField | Offer, Process | Already in defaults |
| `products` | MultiEnumField | N/A | Add to cascade |
| `platforms` | MultiEnumField | Offer | Add to cascade |
| `booking_type` | EnumField | Offer | Add to cascade |
| `rep` | PeopleField | N/A (used for assignee) | Add to cascade |
| `mrr` | NumberField | N/A | Add to cascade |

### Process Carry-Through Candidates

| Field | Type | Current Default | Recommendation |
|-------|------|-----------------|----------------|
| `contact_phone` | TextField | Yes | Keep |
| `priority` | EnumField | Yes | Keep |
| `source` | TextField | No | Add if available |
| `medium` | TextField | No | Add if available |

---

## Solution Options

### Option A: Configure PipelineStage (Recommended)

Update `AutomationConfig` with explicit field lists for the onboarding pipeline. This is targeted and does not affect other pipelines.

**Pros**: Precise control, no side effects, clear intent
**Cons**: Requires explicit configuration per pipeline

### Option B: Update FieldSeeder Defaults

Expand `DEFAULT_BUSINESS_CASCADE_FIELDS` and `DEFAULT_UNIT_CASCADE_FIELDS` to include commonly needed fields.

**Pros**: Benefits all pipelines automatically
**Cons**: May cascade fields to projects that lack them, causing errors

**Recommendation**: Option A for targeted fix, with Option B considered for future standardization.

---

## Test Strategy

### Configuration Verification

```python
# Verify PipelineStage is configured with field lists
stage = config.get_pipeline_stage("onboarding")
assert stage.business_cascade_fields is not None
assert "Office Phone" in stage.business_cascade_fields
assert stage.unit_cascade_fields is not None
assert "Products" in stage.unit_cascade_fields
```

### Integration Test

1. Create Sales process with Unit that has:
   - Vertical = "Dental"
   - Products = ["Product A", "Product B"]
   - Rep = assigned user
2. Move Sales process to Converted section
3. Verify new Onboarding task has:
   - Vertical = "Dental"
   - Products = ["Product A", "Product B"]
   - Rep = same assigned user
   - Launch Date = today's date

### Logging Verification

```
[SEEDING] seed_fields_async called - Business: <gid>, Unit: <gid>
[SEEDING] Cascade fields collected: {"Vertical": "Dental", "Products": [...], ...}
[SEEDING] WriteResult: written=["Vertical", "Products", ...], skipped=[]
```

---

## Open Questions

| Question | Owner | Status |
|----------|-------|--------|
| What PipelineStage configuration is currently being used? | Engineering | Open |
| Are Business and Unit being hydrated before seeding? | Engineering | Open |
| Should defaults be updated globally or per-pipeline? | Product | Open |
| Are there field name differences between projects? | Product | Open |

---

## Code References

| Component | Location |
|-----------|----------|
| FieldSeeder | `src/autom8_asana/automation/seeding.py` |
| PipelineConversionRule | `src/autom8_asana/automation/pipeline.py` |
| PipelineStage Config | `src/autom8_asana/automation/config.py` |
| Business Model | `src/autom8_asana/models/business/business.py` |
| Unit Model | `src/autom8_asana/models/business/unit.py` |
| Process Model | `src/autom8_asana/models/business/process.py` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from PRD-FIELD-SEEDING-GAP |
