---
artifact_id: PRD-unit-cascade-resolution-fix
title: "Unit DataFrame Cascade Field Resolution Fix"
created_at: "2026-01-06T12:00:00Z"
author: requirements-analyst
status: draft
complexity: MODULE
impact: high
impact_categories: [data_model, api_contract]
success_criteria:
  - id: SC-001
    description: "Unit resolution returns 2/3 matches for known phone/vertical pairs in demo"
    testable: true
    priority: must-have
    verification: "curl POST /v1/resolve/unit with test pairs returns resolved_count >= 2"
  - id: SC-002
    description: "Unit DataFrame contains populated office_phone column from Business parent"
    testable: true
    priority: must-have
    verification: "DataFrame extraction includes non-null office_phone values"
  - id: SC-003
    description: "Unit DataFrame contains populated vertical column from Business parent"
    testable: true
    priority: must-have
    verification: "DataFrame extraction includes non-null vertical values"
  - id: SC-004
    description: "Integration test validates cascade resolution with real parent hierarchy"
    testable: true
    priority: must-have
    verification: "Test extracts cascade fields without mocking DataFrame contents"
stakeholders:
  - principal-engineer
  - qa-adversary
related_adrs:
  - ADR-hierarchy-registration-architecture
schema_version: "1.0"
---

# PRD: Unit DataFrame Cascade Field Resolution Fix

## Overview

The Entity Resolver `POST /v1/resolve/unit` endpoint returns `NOT_FOUND` for all Unit lookups despite data existing in Asana. Root cause analysis reveals that cascade field resolution (`source="cascade:Office Phone"` and `source="cascade:Vertical"`) is failing silently during DataFrame extraction, resulting in null values for the lookup index keys.

## Background

### Current State (Broken)

The production Entity Resolver returns:
```json
{
  "results": [{"gid": null, "error": "NOT_FOUND"}, ...],
  "meta": {"resolved_count": 0, "unresolved_count": 3}
}
```

For known phone/vertical pairs that exist in Asana:
- `+12604442080` / `chiropractic` -> "True Wellness Chiropractic Business Units"
- `+19127481506` / `chiropractic` -> "Ranicki Chiropractic Wellness Center Business Unit"

### What Works

| Component | Status | Evidence |
|-----------|--------|----------|
| Health endpoint | OK | Returns healthy |
| S2S authentication | OK | JWT validated |
| Case sensitivity fix | Deployed | Vertical normalized to lowercase |
| Data in Asana | Verified | API confirms tasks exist |
| Project GID | Correct | `1204433992667196` |

### What's Broken

The `GidLookupIndex.from_dataframe()` method requires populated `office_phone` and `vertical` columns to build the lookup dictionary:

```python
# gid_lookup.py line 271-274
required_columns = {"office_phone", "vertical", "gid"}
missing = required_columns - set(df.columns)
if missing:
    raise KeyError(f"Missing required columns: {missing}")
```

The UNIT_SCHEMA defines these as cascade fields:
```python
# schemas/unit.py
ColumnDef(name="office_phone", source="cascade:Office Phone")  # From Business
ColumnDef(name="vertical", source="cascade:Vertical")          # From Business/Unit
```

But in production, these columns contain `null` values because the cascade resolution through the parent hierarchy is failing.

### Technical Flow

```
Unit Task (project 1204433992667196)
    |
    +-- parent.gid -> Business Task (root of hierarchy)
    |                    |
    |                    +-- custom_fields["Office Phone"] = "+12604442080"
    |                    +-- custom_fields["Vertical"] = "Chiropractic"
    |
    +-- cascade:Office Phone -> SHOULD resolve to "+12604442080"
    +-- cascade:Vertical -> SHOULD resolve to "Chiropractic"
```

The cascade resolution path:
1. `DataFrameViewPlugin.materialize_async()` extracts rows
2. `_resolve_cascade_from_dict()` called for `cascade:*` sources
3. `store.get_parent_chain_async()` retrieves parent hierarchy
4. `_get_custom_field_value_from_dict()` extracts field value

**Suspected Failure Points:**
- Parent chain not warmed in UnifiedTaskStore
- HierarchyIndex not populated with parent GIDs
- `warm_hierarchy=True` not being called or not effective
- Custom fields not included in parent task fetch opt_fields

### Test Gap

Existing unit tests mock the DataFrame with pre-populated values:
```python
# Tests create DataFrame directly with office_phone/vertical already set
df = pl.DataFrame({
    "gid": ["123"],
    "office_phone": ["+15551234567"],  # Pre-populated - bypasses cascade
    "vertical": ["dental"],             # Pre-populated - bypasses cascade
})
```

This masks the cascade resolution failure in production where the DataFrame must be built from raw task data.

---

## User Stories

### US-001: Fix Unit Resolution

**As a** autom8_data service developer
**I want** Unit resolution to return matching GIDs for known phone/vertical pairs
**So that** I can resolve business identifiers to Asana task GIDs

**Acceptance Criteria:**
- [ ] `POST /v1/resolve/unit` returns `resolved_count >= 2` for demo pairs
- [ ] Response includes valid GIDs for matched Units
- [ ] Logs show `cascade_field_found` entries (not `cascade_field_not_found`)

### US-002: Cascade Field Population

**As a** DataFrame consumer
**I want** the Unit DataFrame to have populated `office_phone` and `vertical` columns
**So that** the GidLookupIndex can build its O(1) lookup dictionary

**Acceptance Criteria:**
- [ ] `office_phone` column contains non-null values from Business parent
- [ ] `vertical` column contains non-null values from Business/Unit parent
- [ ] Null rate for these columns is < 10% (accounts for incomplete data)

### US-003: Integration Test Coverage

**As a** test engineer
**I want** an integration test that validates real cascade resolution
**So that** regressions in the cascade flow are caught before production

**Acceptance Criteria:**
- [ ] Test uses actual parent/child task hierarchy
- [ ] Test does NOT mock DataFrame contents for cascade fields
- [ ] Test verifies fields resolved from parent, not local task

---

## Functional Requirements

### Must Have

#### FR-001: Diagnose Parent Chain Population

Investigate why `UnifiedTaskStore.get_parent_chain_async()` returns empty or incomplete chains:

1. **Hypothesis A**: HierarchyIndex not populated
   - `put_batch_async()` with `warm_hierarchy=True` may not be registering parent relationships
   - Verify `hierarchy.register_parent()` is called for each task

2. **Hypothesis B**: Parent tasks not fetched with custom_fields
   - Parent fetch may use minimal opt_fields missing `custom_fields.*`
   - Verify `_BASE_OPT_FIELDS` includes all required custom field paths

3. **Hypothesis C**: Completeness level insufficient
   - `get_with_upgrade_async()` may not upgrade to STANDARD completeness
   - Verify `tasks_client` parameter is passed for upgrade capability

#### FR-002: Fix CascadeViewPlugin Resolution

Ensure `CascadeViewPlugin._traverse_parent_chain()` successfully:

1. Gets ancestor GIDs from `HierarchyIndex.get_ancestor_chain()`
2. Fetches each ancestor with STANDARD completeness
3. Extracts custom field value from ancestor with matching entity type

#### FR-003: Fix DataFrameViewPlugin Integration

Ensure `DataFrameViewPlugin._resolve_cascade_from_dict()`:

1. Correctly identifies `cascade:` prefix sources
2. Calls `CascadeViewPlugin` with properly initialized store
3. Falls back gracefully when cascade resolution returns None

#### FR-004: Integration Test for Cascade Resolution

Create test that validates end-to-end cascade field resolution:

```python
async def test_unit_cascade_resolution_integration():
    """Test that cascade fields resolve from parent Business task."""
    # Setup: Create/use actual hierarchy in Asana
    # - Business task with Office Phone and Vertical custom fields
    # - Unit task as child of Business

    # Act: Build Unit DataFrame
    df = await builder.build_with_parallel_fetch_async(client)

    # Assert: Cascade fields populated from parent
    assert df["office_phone"].null_count() < len(df) * 0.1  # < 10% null
    assert df["vertical"].null_count() < len(df) * 0.1
```

### Should Have

#### FR-005: Logging Enhancement

Add DEBUG logging at each cascade resolution step:
- `cascade_parent_chain_requested` with task_gid and max_depth
- `cascade_parent_chain_result` with chain length and ancestor GIDs
- `cascade_field_extraction_attempt` with parent_gid and field_name
- `cascade_field_extraction_result` with value or null reason

#### FR-006: Metrics for Cascade Resolution

Track cascade resolution success/failure rates:
- `cascade_resolution_success_total` counter
- `cascade_resolution_failure_total` counter with reason label
- `cascade_parent_chain_depth_histogram` for debugging

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| Unit DataFrame build time | < 30 seconds for full project |
| Cascade resolution per task | < 50ms (with warm cache) |
| Memory overhead | No increase from current |

### NFR-002: Observability

- Structured logging with correlation IDs
- Clear error messages for cascade failures
- Stats available via `cascade_plugin.get_stats()`

---

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| Unit has no parent | Return null for cascade fields, log warning |
| Parent missing custom_fields | Upgrade parent to STANDARD completeness via API |
| Parent chain exceeds max_depth | Stop at max_depth (5), log info |
| Field not in CASCADING_FIELD_REGISTRY | Return null, log debug |
| Circular parent reference | Detect cycle, break traversal, log error |
| Empty project (no tasks) | Return empty DataFrame with correct schema |

---

## Success Criteria

- [ ] **SC-001**: Unit resolution returns 2/3 matches for known phone/vertical pairs
- [ ] **SC-002**: Unit DataFrame contains populated office_phone column
- [ ] **SC-003**: Unit DataFrame contains populated vertical column
- [ ] **SC-004**: Integration test validates cascade resolution with real hierarchy

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Other entity types (Contact, Offer, Business) | Unit resolution is the blocking issue |
| Lambda warm-up improvements | Already implemented in Phase 3 |
| Case sensitivity handling | Already fixed in prior sprint |
| Performance optimization | Focus on correctness first |
| New cascade fields | Existing Office Phone and Vertical only |

---

## Technical Context

### Key Files

| File | Responsibility |
|------|---------------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | UnitResolutionStrategy |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py` | UNIT_SCHEMA with cascade fields |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py` | ProjectDataFrameBuilder |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/resolver/cascading.py` | CascadingFieldResolver |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/cascade_view.py` | CascadeViewPlugin |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/dataframe_view.py` | DataFrameViewPlugin |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/gid_lookup.py` | GidLookupIndex |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` | UnifiedTaskStore |

### CASCADING_FIELD_REGISTRY

The registry maps field names to their owner classes:

```python
# Business.CascadingFields
OFFICE_PHONE = CascadingFieldDef(
    name="Office Phone",
    target_types={"Unit", "Offer", "Process", "Contact"},
)

# Unit.CascadingFields
VERTICAL = CascadingFieldDef(
    name="Vertical",
    target_types={"Offer", "Process"},
)
```

Note: The `VERTICAL` field on Business might also exist and cascade to Unit. Need to verify which entity owns the Vertical field for Unit tasks.

---

## Acceptance Test

### Manual Verification

```bash
# 1. Invoke resolver endpoint
curl -X POST http://localhost:8000/v1/resolve/unit \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+12604442080", "vertical": "chiropractic"},
      {"phone": "+19127481506", "vertical": "chiropractic"},
      {"phone": "+15555555555", "vertical": "dental"}
    ]
  }'

# Expected (after fix):
# {
#   "results": [
#     {"gid": "12345..."},
#     {"gid": "67890..."},
#     {"gid": null, "error": "NOT_FOUND"}
#   ],
#   "meta": {"resolved_count": 2, "unresolved_count": 1, ...}
# }
```

### Programmatic Verification

```python
import asyncio
from autom8_asana.client import AsanaClient
from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

async def verify_cascade_fix():
    """Verify cascade field resolution is working."""
    client = await AsanaClient.create()

    class ProjectProxy:
        gid = "1204433992667196"  # Unit project
        tasks = []

    builder = ProjectDataFrameBuilder(
        project=ProjectProxy(),
        task_type="Unit",
        schema=UNIT_SCHEMA,
        unified_store=client.unified_store,
    )

    df = await builder.build_with_parallel_fetch_async(client)

    # Check cascade fields populated
    office_phone_nulls = df["office_phone"].null_count()
    vertical_nulls = df["vertical"].null_count()
    total_rows = len(df)

    print(f"Total rows: {total_rows}")
    print(f"office_phone nulls: {office_phone_nulls} ({office_phone_nulls/total_rows*100:.1f}%)")
    print(f"vertical nulls: {vertical_nulls} ({vertical_nulls/total_rows*100:.1f}%)")

    # Should have < 10% null (accounts for incomplete Business data)
    assert office_phone_nulls / total_rows < 0.1, "Too many null office_phone values"
    assert vertical_nulls / total_rows < 0.1, "Too many null vertical values"

    print("SUCCESS: Cascade fields populated correctly")

if __name__ == "__main__":
    asyncio.run(verify_cascade_fix())
```

---

## Open Questions

*All resolved - ready for Architecture handoff.*

1. ~~Which entity owns the Vertical field for Unit cascade?~~ **Resolved**: Check both Business.CascadingFields and Unit.CascadingFields registry

2. ~~Is warm_hierarchy=True actually being invoked?~~ **Investigation Required**: Add logging to confirm

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| UnifiedTaskStore | Implemented | May have hierarchy warming bug |
| CascadeViewPlugin | Implemented | May not receive populated store |
| HierarchyIndex | Implemented | May not be populated with parents |
| CASCADING_FIELD_REGISTRY | Implemented | Office Phone owned by Business |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-unit-cascade-resolution-fix.md` | Pending |
