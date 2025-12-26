# PRD: Field Seeding Gap Analysis

> **Status**: Analysis Complete
> **Author**: Requirements Analyst
> **Date**: 2025-12-18
> **Initiative**: Pipeline Automation Field Seeding

---

## 1. Problem Statement

### 1.1 What Problem Are We Solving?

When pipeline automation creates an Onboarding process from a Sales process, custom field values are expected to cascade/map from the entity hierarchy (Business, Unit, source Process) to the new task. Currently, **only Launch Date is being written** - all other expected fields are not appearing on the target Onboarding task.

### 1.2 Who Is Affected?

Operations team members who expect Onboarding tasks to be pre-populated with data from the Business and Unit hierarchy, reducing manual data entry.

### 1.3 What Happens If We Don't Fix This?

- Manual data entry required for every converted process
- Inconsistent data between Sales and Onboarding processes
- Risk of data entry errors
- Reduced automation ROI

---

## 2. Current State Analysis

### 2.1 Default Field Configuration in FieldSeeder

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/seeding.py`:

| Category | Default Fields | Notes |
|----------|----------------|-------|
| **Business Cascade** | `[]` (EMPTY) | "Empty by default - common Business fields like Office Phone, Company ID don't exist on all target projects" |
| **Unit Cascade** | `["Vertical"]` | "Only Vertical exists on common target projects" |
| **Process Carry-Through** | `["Contact Phone", "Priority"]` | Source process fields |
| **Computed** | `["Launch Date"]` | Hardcoded: today's date |

### 2.2 Root Cause Identification

**ROOT CAUSE #1: Empty Business Cascade Defaults**

The `DEFAULT_BUSINESS_CASCADE_FIELDS` is an empty list `[]`. This means **no fields from Business are cascaded by default**.

From the code comments:
```python
# Default fields that cascade from Business
# Note: Empty by default - common Business fields like Office Phone, Company ID
# don't exist on all target projects. Configure per-pipeline via constructor.
DEFAULT_BUSINESS_CASCADE_FIELDS: list[str] = []
```

**ROOT CAUSE #2: Minimal Unit Cascade Defaults**

Only `Vertical` cascades from Unit by default. `Products`, `Platforms`, `Booking Type`, and `Rep` are NOT in the defaults.

**ROOT CAUSE #3: No Pipeline-Specific Configuration**

The `PipelineStage` configuration allows overriding these defaults via:
- `business_cascade_fields`
- `unit_cascade_fields`
- `process_carry_through_fields`
- `field_name_mapping`

However, if no explicit configuration is provided when setting up the pipeline stage, the defaults apply.

---

## 3. Entity Field Inventory

### 3.1 Business Model Fields

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py`:

| Field | Type | Cascading? | Notes |
|-------|------|-----------|-------|
| `company_id` | TextField | Yes (declared) | CascadingFields.COMPANY_ID targets all descendants |
| `facebook_page_id` | TextField | No | |
| `fallback_page_id` | TextField | No | |
| `google_cal_id` | TextField | No | |
| **`office_phone`** | TextField | **Yes (declared)** | CascadingFields.OFFICE_PHONE targets Unit, Offer, Process, Contact |
| `owner_name` | TextField | No | |
| `owner_nickname` | TextField | No | |
| `review_1` | TextField | No | |
| `review_2` | TextField | No | |
| `reviews_link` | TextField | No | |
| `stripe_id` | TextField | No | |
| `stripe_link` | TextField | No | |
| `twilio_phone_num` | TextField | No | |
| `num_reviews` | IntField | No | |
| `aggression_level` | EnumField | No | |
| `booking_type` | EnumField | No | |
| `vca_status` | EnumField | No | |
| `vertical` | EnumField | No | |
| **`rep`** | PeopleField | No | But used for assignee resolution |

**Business CascadingFields Definitions:**
- `OFFICE_PHONE` - targets: Unit, Offer, Process, Contact
- `COMPANY_ID` - targets: all descendants
- `BUSINESS_NAME` - targets: Unit, Offer (from task.name)
- `PRIMARY_CONTACT_PHONE` - targets: Unit, Offer, Process

### 3.2 Unit Model Fields

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/unit.py`:

| Field | Type | Cascading? | Notes |
|-------|------|-----------|-------|
| `mrr` | NumberField | No | |
| `weekly_ad_spend` | NumberField | No | |
| `discount` | EnumField | No | |
| `meta_spend` | NumberField | No | |
| `meta_spend_sub_id` | TextField | No | |
| `tiktok_spend` | NumberField | No | |
| `tiktok_spend_sub_id` | TextField | No | |
| `solution_fee_sub_id` | TextField | No | |
| `ad_account_id` | TextField | No | |
| **`platforms`** | MultiEnumField | **Yes (declared)** | CascadingFields.PLATFORMS targets Offer (allow_override=True) |
| `tiktok_profile` | TextField | No | |
| **`products`** | MultiEnumField | **No** | Not in CascadingFields |
| `languages` | MultiEnumField | No | |
| **`vertical`** | EnumField | **Yes (declared)** | CascadingFields.VERTICAL targets Offer, Process |
| `specialty` | MultiEnumField | No | |
| **`rep`** | PeopleField | **No** | But used for assignee resolution |
| `currency` | EnumField | No | |
| `radius` | IntField | No | |
| `min_age` | IntField | No | |
| `max_age` | IntField | No | |
| `gender` | MultiEnumField | No | |
| `zip_code_list` | TextField | No | |
| `zip_codes_radius` | IntField | No | |
| `excluded_zips` | TextField | No | |
| **`booking_type`** | EnumField | **Yes (declared)** | CascadingFields.BOOKING_TYPE targets Offer |

**Unit CascadingFields Definitions:**
- `PLATFORMS` - targets: Offer (allow_override=True)
- `VERTICAL` - targets: Offer, Process
- `BOOKING_TYPE` - targets: Offer

### 3.3 Process Model Fields

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py`:

| Field | Type | Carry-Through? | Notes |
|-------|------|----------------|-------|
| `started_at` | TextField | No | |
| `process_completed_at` | TextField | No | |
| `process_notes` | TextField | No | |
| `status` | EnumField | No | |
| `priority` | EnumField | **In defaults** | |
| `vertical` | EnumField | No | |
| `process_due_date` | TextField | No | |
| `assigned_to` | PeopleField | No | |

**Note:** Process model has minimal fields. Most data comes from Business/Unit.

### 3.4 Contact Model Fields (Reference)

| Field | Type | Notes |
|-------|------|-------|
| `contact_phone` | TextField | In carry-through defaults |
| `contact_email` | TextField | |
| `source` | TextField | |
| `medium` | TextField | |
| `content` | TextField | |

---

## 4. Target Onboarding Project Fields

From QA testing, these custom fields exist on the Onboarding project:

| Field Name | Exists on Onboarding | Source Entity | Currently Seeded? |
|------------|---------------------|---------------|-------------------|
| Asset Edit Comments | Yes | - | No (manual) |
| Client Current MRR | Yes | - | No (manual) |
| Client Goal MRR | Yes | - | No (manual) |
| Current Revenue Growth | Yes | - | No (manual) |
| Goal Revenue Growth | Yes | - | No (manual) |
| **Source Type** | Yes | Contact? | No |
| **Rep** | Yes | Unit/Business | No (not in cascade list) |
| **Products** | Yes | Unit | No (not in cascade list) |
| **Calendly Link** | Yes | ? | No |
| **Office Phone** | Yes | Business | No (empty defaults) |
| **Vertical** | Yes | Unit | Yes (in defaults) |
| **Source** | Yes | Contact | No |
| **Medium** | Yes | Contact | No |
| **Content** | Yes | Contact | No |
| Payout Amount | Yes | - | No (manual) |
| **MRR** | Yes | Unit | No (not in cascade list) |
| Intercom User ID | Yes | - | No (manual) |
| Time to Close | Yes | - | No (computed?) |
| Content stage | Yes | - | No (manual) |
| Videography Date | Yes | - | No (manual) |
| **Launch Date** | Yes | Computed | **YES** |
| Time to launch call | Yes | - | No (computed?) |
| Internal Notes | Yes | - | No (manual) |
| Data Entry Completed | Yes | - | No (manual) |
| Emails /Dock | Yes | - | No (manual) |
| FB Access | Yes | - | No (manual) |
| Cal/Sch: DNA Submitted | Yes | - | No (manual) |
| Offer Completed | Yes | - | No (manual) |
| Time to Video Session | Yes | - | No (computed?) |
| Status | Yes | - | No |

---

## 5. Gap Analysis Matrix

| Field | Source Entity | Source Field | Exists on Target? | In Cascade Defaults? | Currently Seeding? | Gap |
|-------|---------------|--------------|-------------------|---------------------|-------------------|-----|
| **Launch Date** | Computed | - | Yes | - | **YES** | None |
| **Vertical** | Unit | `vertical` | Yes | Yes (Unit cascade) | Should be, if Unit hydrated | Check hydration |
| **Products** | Unit | `products` | Yes | **NO** | No | **Missing from Unit cascade defaults** |
| **Rep** | Unit/Business | `rep` | Yes | **NO** | No | **Missing from cascade defaults** |
| **Office Phone** | Business | `office_phone` | Yes | **NO** (empty Business defaults) | No | **Missing from Business cascade defaults** |
| **MRR** | Unit | `mrr` | Yes | **NO** | No | **Missing from Unit cascade defaults** |
| **Source** | Contact | `source` | Yes | **NO** | No | Contact fields not in carry-through |
| **Medium** | Contact | `medium` | Yes | **NO** | No | Contact fields not in carry-through |
| **Content** | Contact | `content` | Yes | **NO** | No | Contact fields not in carry-through |
| Contact Phone | Contact/Process | `contact_phone` | ? | Yes (Process carry-through) | Should be | Check field existence |
| Priority | Process | `priority` | ? | Yes (Process carry-through) | Should be | Check field existence |

---

## 6. Root Causes Summary

### 6.1 Configuration Issue: Empty/Minimal Defaults

**Primary Cause**: The `DEFAULT_BUSINESS_CASCADE_FIELDS` and `DEFAULT_UNIT_CASCADE_FIELDS` are too conservative:

```python
DEFAULT_BUSINESS_CASCADE_FIELDS: list[str] = []  # EMPTY!
DEFAULT_UNIT_CASCADE_FIELDS: list[str] = ["Vertical"]  # Only Vertical
```

### 6.2 Missing Pipeline-Specific Configuration

The `PipelineStage` in `AutomationConfig` is not being configured with the fields that should cascade for Sales -> Onboarding conversion.

### 6.3 Potential Hydration Issue

Even if Vertical is in defaults, it requires the Unit to be hydrated and have a value. If `unit` is None or `unit.vertical` is None, nothing cascades.

### 6.4 Field Name Mapping Not Configured

Source field names may differ from target field names. The `field_name_mapping` in `PipelineStage` is not configured.

---

## 7. Recommended Fixes

### 7.1 Option A: Configure PipelineStage (Recommended)

Update the `AutomationConfig` to include explicit field lists for the onboarding pipeline:

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
            field_name_mapping={
                # Add any source->target name mappings if needed
                # "Unit MRR": "MRR",
            },
        ),
    },
)
```

### 7.2 Option B: Update FieldSeeder Defaults

If these fields should cascade for ALL pipelines (not just onboarding), update the class-level defaults:

```python
class FieldSeeder:
    DEFAULT_BUSINESS_CASCADE_FIELDS: list[str] = [
        "Office Phone",
    ]

    DEFAULT_UNIT_CASCADE_FIELDS: list[str] = [
        "Vertical",
        "Products",
        "Rep",
        "MRR",
    ]
```

**Warning**: This affects all pipelines. Option A is safer for targeted changes.

### 7.3 Verify Hierarchy Hydration

Ensure that when seeding fields:
1. `business` parameter is not None
2. `unit` parameter is not None
3. These entities have their custom fields loaded (hydrated)

Check logs for:
```
[SEEDING] seed_fields_async called - Business: None, Unit: None
```

If Business/Unit are None, the issue is upstream in hierarchy resolution.

### 7.4 Rep Field Special Handling

`Rep` is a PeopleField that returns `list[dict[str, Any]]`. The seeding code should handle this correctly, but verify:
1. Source entity has rep populated (not empty list)
2. Target field can accept people values

---

## 8. Acceptance Criteria

### 8.1 Must Have

- [ ] `Vertical` cascades from Unit to Onboarding task
- [ ] `Products` cascades from Unit to Onboarding task
- [ ] `Office Phone` cascades from Business to Onboarding task
- [ ] `Rep` cascades from Unit (fallback: Business) to Onboarding task
- [ ] `Launch Date` continues to be set (regression test)

### 8.2 Should Have

- [ ] `MRR` cascades from Unit to Onboarding task
- [ ] `Platforms` cascades from Unit to Onboarding task
- [ ] `Contact Phone` carries through from source Process

### 8.3 Nice to Have

- [ ] `Source`, `Medium`, `Content` carry through if available on source Process
- [ ] Logging shows which fields were written vs skipped

---

## 9. Test Plan

### 9.1 Configuration Verification

```python
# Verify PipelineStage is configured with field lists
stage = config.get_pipeline_stage("onboarding")
assert stage.business_cascade_fields is not None
assert "Office Phone" in stage.business_cascade_fields
assert stage.unit_cascade_fields is not None
assert "Products" in stage.unit_cascade_fields
```

### 9.2 Integration Test

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

### 9.3 Logging Verification

Check logs for:
```
[SEEDING] Cascade fields collected: {"Vertical": "Dental", "Products": [...], ...}
[SEEDING] WriteResult: written=["Vertical", "Products", ...], skipped=[]
```

---

## 10. Dependencies

- FieldSeeder implementation (exists)
- PipelineStage configuration structure (exists)
- Entity hierarchy hydration (exists but verify)

---

## 11. Open Questions

| Question | Owner | Due Date |
|----------|-------|----------|
| What is the PipelineStage configuration currently being used? | Engineering | Immediate |
| Are Business and Unit being hydrated before seeding? | Engineering | Immediate |
| Should defaults be updated globally or per-pipeline? | Product | Before implementation |
| Are there field name differences between projects? | Product | Before implementation |

---

## Appendix A: Code References

- **FieldSeeder**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/seeding.py`
- **PipelineConversionRule**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/pipeline.py`
- **PipelineStage Config**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/config.py`
- **Business Model**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py`
- **Unit Model**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/unit.py`
- **Process Model**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py`

---

## Appendix B: Key Findings Summary

1. **Launch Date works** because it's a computed field (hardcoded `arrow.now().format("YYYY-MM-DD")`)

2. **Other fields don't work** because:
   - Business cascade defaults are EMPTY `[]`
   - Unit cascade defaults only include `["Vertical"]`
   - No pipeline-specific configuration overrides the defaults

3. **Fix is configuration**, not code change:
   - Add field lists to `PipelineStage` configuration
   - OR update class-level defaults in `FieldSeeder`

4. **Architecture supports** the required functionality:
   - `PipelineStage.business_cascade_fields` exists
   - `PipelineStage.unit_cascade_fields` exists
   - `field_name_mapping` exists for name translation
   - Code handles enum resolution, people fields, etc.
