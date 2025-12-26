# TDD: Field Seeding Configuration for Pipeline Conversion

## Metadata
- **TDD ID**: TDD-FIELD-SEEDING-CONFIG
- **Status**: Draft
- **Author**: Architect Agent
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **PRD Reference**: [PRD-FIELD-SEEDING-GAP](/docs/requirements/PRD-FIELD-SEEDING-GAP.md)
- **Related TDDs**: None
- **Related ADRs**: ADR-0105 (Field Seeding Architecture), ADR-0112 (Custom Field GID Resolution)

---

## Overview

The field seeding configuration for Sales -> Onboarding pipeline conversion needs explicit field lists in the `PipelineStage` configuration. Currently, only `Launch Date` is written because the default cascade field lists are empty/minimal. This TDD specifies the exact configuration changes needed to cascade fields from Business and Unit hierarchy to the newly created Onboarding tasks.

---

## Requirements Summary

Per PRD-FIELD-SEEDING-GAP:

| Requirement | Description |
|-------------|-------------|
| **Must Have** | Vertical, Products, Office Phone, Rep, Launch Date cascade to Onboarding |
| **Should Have** | MRR, Platforms, Contact Phone cascade to Onboarding |
| **Nice to Have** | Source, Medium, Content carry-through from Contact/Process |

**Root Cause Identified**: `DEFAULT_BUSINESS_CASCADE_FIELDS = []` (empty) and `DEFAULT_UNIT_CASCADE_FIELDS = ["Vertical"]` (minimal).

---

## System Context

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

The `PipelineStage` configuration in `AutomationConfig` controls which fields are passed to `FieldSeeder`. The demo script at `scripts/example_pipeline_automation.py` creates a `PipelineStage` without explicit field lists, causing it to fall back to the (empty/minimal) class-level defaults.

---

## Design

### Component Architecture

| Component | Responsibility | Current State |
|-----------|----------------|---------------|
| `FieldSeeder` | Collect and write cascade/carry-through fields | Works correctly; uses configured field lists |
| `PipelineStage` | Configuration for target project and field lists | **Not populated with field lists** |
| `PipelineConversionRule` | Orchestrates conversion, creates FieldSeeder | Passes stage config to FieldSeeder correctly |
| `AutomationConfig` | Holds pipeline_stages map | **PipelineStage needs field lists** |

### Design Decision: Configure PipelineStage (Not FieldSeeder Defaults)

**Chosen Approach**: Configure explicit field lists in `PipelineStage` for the onboarding pipeline.

**Rationale**:
1. **Safety**: Does not affect other pipelines or future pipelines
2. **Explicitness**: Field lists are visible in the configuration, not hidden in class defaults
3. **Flexibility**: Different pipelines can have different field lists
4. **Target-Aware**: Only fields that exist on the target project should be listed

**Rejected Alternative**: Update `FieldSeeder.DEFAULT_*_CASCADE_FIELDS`
- Risk: Affects all pipelines globally
- Problem: Fields may not exist on all target projects (causes skipped fields warnings)

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Where to configure fields | `PipelineStage` | Pipeline-specific, explicit, safe | N/A (design doc covers) |
| Field list source | Explicit strings matching target project | Must match exact field names on Onboarding project | N/A |
| Rep field handling | Include in `unit_cascade_fields` | Rep is a PeopleField; FieldSeeder handles correctly | N/A |
| MRR field inclusion | Include in `unit_cascade_fields` | NumberField; exists on Onboarding project | N/A |

---

## Implementation Plan

### Phase 1: Update Demo Script Configuration (Immediate Fix)

**File**: `/Users/tomtenuta/Code/autom8_asana/scripts/example_pipeline_automation.py`

**Location**: Lines 308-326 (initial PipelineStage creation) and Lines 379-383 (discovery update)

**Current Code** (Lines 314-324):
```python
"onboarding": PipelineStage(
    project_gid=onboarding_project_gid or "",
    target_section="Opportunity",
    due_date_offset_days=7,  # Due in 7 days from today
    # Optional: Configure custom field lists to match your Asana setup
    # business_cascade_fields=["Company Name", "Phone"],
    # unit_cascade_fields=["Location", "Type"],
    # process_carry_through_fields=["Priority", "Status"],
    # Optional: Fixed assignee (use if rep fields aren't populated)
    # assignee_gid="123456789",
),
```

**Required Change**:
```python
"onboarding": PipelineStage(
    project_gid=onboarding_project_gid or "",
    target_section="Opportunity",
    due_date_offset_days=7,
    # Field seeding configuration for Sales -> Onboarding conversion
    business_cascade_fields=[
        "Office Phone",
        # Note: Company ID excluded - not present on Onboarding project
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
    # Field name mapping: source -> target (if names differ)
    field_name_mapping={},
),
```

**Also Update** Lines 379-383 (discovery update block):
```python
automation_config.pipeline_stages["onboarding"] = PipelineStage(
    project_gid=discovered_onboarding_gid,
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
    field_name_mapping={},
)
```

### Phase 2: Validate Field Names Against Target Project (Verification)

Before deployment, verify that the field names in the configuration match exactly what exists on the Onboarding project. The PRD identified these fields exist on Onboarding:

| Field Name | Source Entity | Type | Verified in PRD |
|------------|---------------|------|-----------------|
| Office Phone | Business | TextField | Yes |
| Vertical | Unit | EnumField | Yes |
| Products | Unit | MultiEnumField | Yes |
| MRR | Unit | NumberField | Yes |
| Rep | Unit | PeopleField | Yes |
| Platforms | Unit | MultiEnumField | Needs verification |
| Booking Type | Unit | EnumField | Needs verification |
| Contact Phone | Process/Contact | TextField | Needs verification |
| Priority | Process | EnumField | Needs verification |

**Verification Command**:
```bash
# Run the demo in dry-run mode to see field resolution logs
python scripts/example_pipeline_automation.py --dry-run --gid <process_gid>
```

### Phase 3: Optional - Consider Default Updates (Future)

If multiple pipelines need the same field lists, consider updating `FieldSeeder` defaults. This is deferred because:
1. Only one pipeline (Onboarding) is currently configured
2. Other pipelines may have different target projects with different fields

---

## Field Availability Matrix

### Business Model Fields Available for Cascade

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py`:

| Field | Descriptor | Available | Notes |
|-------|------------|-----------|-------|
| `office_phone` | TextField(cascading=True) | Yes | CascadingFields.OFFICE_PHONE declared |
| `company_id` | TextField | Yes | But may not exist on Onboarding project |
| `rep` | PeopleField | Yes | Used for assignee resolution separately |

### Unit Model Fields Available for Cascade

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/unit.py`:

| Field | Descriptor | Available | Notes |
|-------|------------|-----------|-------|
| `vertical` | EnumField | Yes | CascadingFields.VERTICAL declared |
| `products` | MultiEnumField | Yes | NOT in CascadingFields (SDK), but in field list |
| `mrr` | NumberField(field_name="MRR") | Yes | Note: uppercase field_name |
| `rep` | PeopleField | Yes | Cascade for Rep field (distinct from assignee) |
| `platforms` | MultiEnumField | Yes | CascadingFields.PLATFORMS declared |
| `booking_type` | EnumField | Yes | CascadingFields.BOOKING_TYPE declared |

### Process Model Fields Available for Carry-Through

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py`:

| Field | Available | Notes |
|-------|-----------|-------|
| `contact_phone` | Likely via Contact | Needs verification of source |
| `priority` | Yes | EnumField on Process |

---

## Complexity Assessment

**Level**: Script (single configuration change)

**Justification**: This is a configuration-only change. The code infrastructure already exists and works correctly. The gap is simply that the configuration was not populated with the required field lists.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Field name mismatch | Fields silently skipped | Medium | Verify field names against Onboarding project before deployment |
| Enum value mismatch | Field skipped with warning | Medium | FieldSeeder logs enum resolution failures; monitor logs |
| Rep field empty | Assignee not set | Low | Separate assignee logic handles this; non-blocking |
| Platforms/Booking Type not on target | Fields skipped | Medium | Review logs after first conversion |

---

## Observability

### Logging (Already Implemented)

FieldSeeder already logs extensively at INFO level:

```
[SEEDING] seed_fields_async called - Business: {name}, Unit: {name}, Process: {name}
[SEEDING] Cascade fields collected: {dict}
[SEEDING] Carry-through fields collected: {dict}
[SEEDING] Computed fields: {dict}
[SEEDING] Final seeded fields: {dict}
[SEEDING] Target task custom fields available: [field names]
[SEEDING] Mapped fields (after name mapping): {dict}
[SEEDING] Field '{name}': matched={bool}, value={value}
[SEEDING] WriteResult: written=[fields], skipped=[fields]
```

### Success Criteria

After deployment, logs should show:
- `Cascade fields collected` includes Vertical, Products, MRR, Rep, etc.
- `WriteResult: written=[...]` includes the configured fields
- `skipped=[]` is empty or contains only fields intentionally omitted

---

## Testing Strategy

### Unit Testing

Existing tests in `tests/unit/models/business/` cover FieldSeeder functionality. No new unit tests required for configuration-only change.

### Integration Testing

Manual verification after deployment:

1. Create a Sales Process with a Unit that has:
   - Vertical = "Dental" (or any value)
   - Products = ["Product A", "Product B"]
   - Rep = assigned user
   - MRR = 1000

2. Move Sales Process to "Converted" section

3. Verify new Onboarding task has:
   - Vertical = "Dental"
   - Products = ["Product A", "Product B"]
   - Rep = same user
   - MRR = 1000
   - Launch Date = today

### Regression Testing

Verify Launch Date still works (computed field unaffected by this change).

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Does Platforms exist on Onboarding? | Engineering | Before deploy | Verify via API or Asana UI |
| Does Booking Type exist on Onboarding? | Engineering | Before deploy | Verify via API or Asana UI |
| Does Contact Phone exist on Onboarding? | Engineering | Before deploy | Verify via API or Asana UI |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Architect Agent | Initial draft |

---

## Appendix A: Code Snippets for Engineer

### Snippet 1: Primary Configuration Update (Lines 314-324)

Replace:
```python
"onboarding": PipelineStage(
    project_gid=onboarding_project_gid or "",
    target_section="Opportunity",
    due_date_offset_days=7,  # Due in 7 days from today
    # Optional: Configure custom field lists to match your Asana setup
    # business_cascade_fields=["Company Name", "Phone"],
    # unit_cascade_fields=["Location", "Type"],
    # process_carry_through_fields=["Priority", "Status"],
    # Optional: Fixed assignee (use if rep fields aren't populated)
    # assignee_gid="123456789",
),
```

With:
```python
"onboarding": PipelineStage(
    project_gid=onboarding_project_gid or "",
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
    field_name_mapping={},
),
```

### Snippet 2: Discovery Update Block (Lines 379-383)

Replace:
```python
automation_config.pipeline_stages["onboarding"] = PipelineStage(
    project_gid=discovered_onboarding_gid,
    target_section="Opportunity",
    due_date_offset_days=7,  # Due in 7 days from today
)
```

With:
```python
automation_config.pipeline_stages["onboarding"] = PipelineStage(
    project_gid=discovered_onboarding_gid,
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
    field_name_mapping={},
)
```

---

## Appendix B: Quality Gates Checklist

- [x] Traces to approved PRD (PRD-FIELD-SEEDING-GAP)
- [x] All significant decisions documented (PipelineStage vs FieldSeeder defaults)
- [x] Component responsibilities are clear
- [x] Interfaces are defined (PipelineStage configuration schema)
- [x] Complexity level is justified (Script level - config only)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable (specific line numbers and code snippets)
