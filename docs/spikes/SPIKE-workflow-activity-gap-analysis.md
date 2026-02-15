# SPIKE: Workflow Activity Classification Gap Analysis

**Date**: 2026-02-15
**Status**: Complete
**Question**: What is the full surface area of the `list_for_project_async` / activity classifier gap?
**Decision**: Informs implementation plan for activity filtering across workflows

---

## Executive Summary

Three interconnected gaps span the automation workflow layer, the entity model layer, and the section classification module. Together they represent a **runtime-breaking bug** (phantom method), an **orphaned module** (committed but never integrated), and **4x code duplication** (section extraction logic).

---

## Gap 1: `tasks.list_for_project_async` Does Not Exist

### The Bug

Three workflow files call `self._client.tasks.list_for_project_async(...)` which **does not exist** on `TasksClient`.

| File | Line | Has type:ignore |
|------|------|-----------------|
| `conversation_audit.py` | 216 | No |
| `insights_export.py` | 261 | No |
| `pipeline_transition.py` | 246 | Yes (`# type: ignore[attr-defined]`) |

### Root Cause

`SectionsClient` has `list_for_project_async` (valid, used by 7 callers). `TasksClient` only has `list_async(*, project=...)` with keyword-only args. The workflow code was written against the wrong API surface.

### Why Tests Pass

All workflow tests use `MagicMock()`:

```python
# conftest.py line 25-27
client = MagicMock()
client.tasks = MagicMock()
```

`MagicMock` auto-creates any attribute accessed, so `mock.tasks.list_for_project_async` silently succeeds. **The tests do not validate that the method exists on the real client.**

### Production Impact

When invoked via Lambda (EventBridge schedule), the workflows receive a real `AsanaClient` instance. The call would raise:

```
AttributeError: 'TasksClient' object has no attribute 'list_for_project_async'
```

This crashes the entire workflow invocation (no tasks enumerated, WorkflowResult never returned).

### Correct Method

```python
# Before (broken)
client.tasks.list_for_project_async(PROJECT_GID, opt_fields=[...], completed_since="now")

# After (correct) — keyword-only args
client.tasks.list_async(project=PROJECT_GID, opt_fields=[...], completed_since="now")
```

### Call Site Census

| Client | Method | Exists | Count | Files |
|--------|--------|--------|-------|-------|
| `tasks` | `list_for_project_async` | NO | 3 | 3 workflow files |
| `sections` | `list_for_project_async` | YES | 7 | name_resolver, pipeline, templates, lifecycle/*, dataframes/* |

---

## Gap 2: `activity.py` — Orphaned Module

### Status

`src/autom8_asana/models/business/activity.py` (271 lines) is committed but **has zero production consumers**.

| Dimension | Status |
|-----------|--------|
| Production imports | **NONE** |
| `__init__.py` exports | **NONE** |
| Test imports | 2 files (created this session, both fail) |
| References in .claude/artifacts/ | **NONE** (TDD/plan files from previous session were lost) |

### What It Contains

- `AccountActivity` enum: ACTIVE, ACTIVATING, INACTIVE, IGNORED
- `SectionClassifier` frozen dataclass: O(1) case-insensitive section-to-activity mapping
- `OFFER_CLASSIFIER`: 33 sections mapped (21 active, 5 activating, 3 inactive, 4 ignored)
- `UNIT_CLASSIFIER`: 14 sections mapped (3 active, 4 activating, 6 inactive, 1 ignored)
- `extract_section_name(task, project_gid)`: Canonical section extraction
- `ACTIVITY_PRIORITY` tuple: ACTIVE > ACTIVATING > INACTIVE > IGNORED
- `CLASSIFIERS` registry + `get_classifier(entity_type)`

### What It Was Supposed To Enable (Never Implemented)

| Feature | Target File | Status |
|---------|-------------|--------|
| `Offer.account_activity` property | `offer.py` | NOT IMPLEMENTED |
| `Unit.account_activity` property | `unit.py` | NOT IMPLEMENTED |
| `Business.max_unit_activity` property | `business.py` | NOT IMPLEMENTED |
| `__init__.py` re-exports | `__init__.py` | NOT ADDED |
| InsightsExport ACTIVE-only filtering | `insights_export.py` | NOT INTEGRATED |
| ConversationAudit activity scoping | `conversation_audit.py` | NOT INTEGRATED |

---

## Gap 3: Section Extraction — 4x Duplication

### Duplicate Implementations

The `extract_section_name()` function in `activity.py` was designed to DRY a pattern that exists **4 separate times**:

#### 1. `activity.extract_section_name(task, project_gid)` — lines 138-171
Canonical implementation. **Never called by production code.**

#### 2. `BaseExtractor._extract_section(task, project_gid)` — `extractors/base.py:488-521`
Instance method on Task objects. Identical logic. Used by DataFrame extractors.

#### 3. `DataFrameViewPlugin._extract_section(task_data, project_gid)` — `dataframe_view.py:835-870`
Instance method on dict objects (not Task). Identical logic except operates on raw dicts.

#### 4. `Process.pipeline_state` — `process.py:414-430`
Property. Simpler variant (no project_gid filter). Returns `ProcessSection` enum, not string.

#### 5. `pipeline_transition._enumerate_processes_async` — inline at line 265-268
Inline extraction. Manual membership iteration duplicating the same pattern.

### Duplication Cost

~40 lines x 4 = ~160 lines of near-identical membership iteration logic. Any bug fix or behavioral change must be applied 4+ times independently.

---

## Gap 4: Missing Test Coverage (Dangling Tests)

Two test files exist that **will fail** because the properties they test don't exist:

| File | Tests | Status |
|------|-------|--------|
| `tests/unit/models/business/test_activity.py` | 65 | PASSES (tests activity.py which exists) |
| `tests/unit/models/business/test_activity_properties.py` | 41 | **FAILS** (`AttributeError: 'Offer' object has no attribute 'account_activity'`) |

These were created in this session based on the previous session's design. `test_activity_properties.py` is effectively a specification for the not-yet-implemented entity properties.

---

## Impact Analysis

### Without Activity Filtering

| Workflow | Impact |
|----------|--------|
| **InsightsExport** | Processes ALL offers including INACTIVE, IGNORED, and ACTIVATING. Each offer triggers 9 concurrent API calls to autom8_data. Inactive offers have no meaningful data → wasted API calls + empty/error reports attached to tasks. |
| **ConversationAudit** | Processes ALL ContactHolders regardless of parent Business activity. Each holder triggers: Asana GET (parent resolution) + Business hydration + autom8_data CSV export. Inactive businesses waste ~3 API calls per holder. |
| **PipelineTransition** | Already filters by section (CONVERTED/DID NOT CONVERT) — not affected. |

### Estimated Waste

If ~40% of offers are non-ACTIVE (based on the section distribution: 12 non-active sections vs 21 active):
- InsightsExport: ~40% unnecessary API calls (9 calls per inactive offer)
- ConversationAudit: ~40% unnecessary API calls (3 calls per inactive holder's parent)

---

## Dependency Graph

```
activity.py (EXISTS, orphaned)
    ├── AccountActivity enum
    ├── SectionClassifier
    ├── OFFER_CLASSIFIER / UNIT_CLASSIFIER
    └── extract_section_name()

Entity Properties (DO NOT EXIST)
    ├── Offer.account_activity → uses OFFER_CLASSIFIER
    ├── Unit.account_activity → uses UNIT_CLASSIFIER
    └── Business.max_unit_activity → aggregates Unit activities

Workflow Integration (DO NOT EXIST)
    ├── InsightsExport._enumerate_offers() → filter by ACTIVE
    └── ConversationAudit._process_holder() → check parent activity

API Bug (BLOCKS ALL ABOVE)
    └── tasks.list_for_project_async → must be list_async(project=...)
```

---

## Recommendation

### Priority Order

1. **P0 — Fix the API bug** (3 files, ~10 lines each)
   - `list_for_project_async` → `list_async(project=...)` in all 3 workflows
   - Update all test mocks to match
   - This is a runtime-breaking bug; everything else depends on it

2. **P1 — Wire the orphaned module** (4 files, ~60 lines total)
   - Add `__init__.py` exports
   - Add `account_activity` property to Offer and Unit
   - Add `max_unit_activity` property to Business
   - Unblocks workflow activity filtering

3. **P2 — Integrate activity filtering** (2 files + tests)
   - InsightsExport: filter `_enumerate_offers()` to ACTIVE-only
   - ConversationAudit: add `_resolve_business_activity()` with dedup cache

4. **P3 — DRY section extraction** (3 files, optional)
   - Replace `BaseExtractor._extract_section` with `extract_section_name()`
   - Replace `DataFrameView._extract_section` with `extract_section_name()`
   - Replace inline extraction in `pipeline_transition.py`
   - Lower priority — duplication is stable and low-risk

### Non-Goals

- `Process.pipeline_state` returns `ProcessSection` (different type) — leave as-is
- `OfferSection` deprecation (Phase 4 from previous plan) — defer

---

## Follow-Up Actions

- [ ] Implement P0 (API bug fix) — prerequisite for all workflows
- [ ] Implement P1 (entity properties) — prerequisite for P2
- [ ] Implement P2 (workflow activity filtering) — the main value delivery
- [ ] Delete `test_activity_properties.py` OR implement the properties it tests
- [ ] Consider P3 (DRY section extraction) as tech debt cleanup
