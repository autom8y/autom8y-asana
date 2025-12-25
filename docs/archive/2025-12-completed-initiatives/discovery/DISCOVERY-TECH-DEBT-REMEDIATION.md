# Discovery: Technical Debt Remediation Initiative

> **Status**: Session 0 Discovery Complete
> **Date**: 2025-12-19
> **Author**: Requirements Analyst
> **Purpose**: Validate DEBT items, resolve blocking questions, map dependencies

---

## Executive Summary

This discovery document validates 26 identified DEBT items across 4 phases against the current codebase state. The analysis reveals that significant remediation work has already been completed for Hours, Location, and several Unit field type corrections. However, critical gaps remain in Process entity fields, detection system configuration, and custom field type alignment.

**Key Findings:**
1. **Hours model ALREADY FIXED**: Field names corrected from "Monday Hours" to "Monday", type changed to multi-enum
2. **Location model ALREADY FIXED**: Fields updated to match Asana reality (street_number, country as enum, etc.)
3. **Unit type corrections PARTIALLY FIXED**: 5 of 8 type mismatches have been corrected
4. **AssetEdit PRIMARY_PROJECT_GID ADDED**: Now set to "1202204184560785"
5. **Process model remains generic**: Still has only 8 fields vs 67+ in Sales project
6. **ProcessProjectRegistry to be deleted**: Per IMPACT-PROCESS-CLEANUP analysis

---

## 1. DEBT Item Inventory

### Phase 1: Foundation - Detection System (8 items)

| ID | DEBT Item | Status | Evidence | Priority |
|----|-----------|--------|----------|----------|
| DEBT-001 | Process.PRIMARY_PROJECT_GID is None | CONFIRMED | `process.py:165` - `PRIMARY_PROJECT_GID: ClassVar[str | None] = None` | P0 |
| DEBT-002 | ProcessHolder.PRIMARY_PROJECT_GID is None | CONFIRMED | `process.py:297` - Same pattern | P0 |
| DEBT-003 | LocationHolder.PRIMARY_PROJECT_GID is None | CONFIRMED | `location.py:298` - `PRIMARY_PROJECT_GID: ClassVar[str | None] = None` | P1 |
| DEBT-004 | UnitHolder.PRIMARY_PROJECT_GID is None | CONFIRMED | `unit.py:509` - Same pattern | P1 |
| DEBT-005 | Detection Tier 2 name patterns unreliable | CONFIRMED | `detection.py:400-440` - Uses exact name matching which fails for decorated names | P1 |
| DEBT-006 | No self-healing implementation | CONFIRMED | `session.py` has `add_to_project()` but no automatic healing | P2 |
| DEBT-007 | WorkspaceProjectRegistry discovery timing | PARTIAL | `registry.py:573-601` - Lazy discovery implemented but not tested in production | P1 |
| DEBT-008 | Missing env var validation at startup | CONFIRMED | No startup check for `ASANA_PROJECT_*` vars | P2 |

### Phase 2: Custom Field Remediation (10 items)

| ID | DEBT Item | Status | Evidence | Priority |
|----|-----------|--------|----------|----------|
| DEBT-009 | Unit.specialty wrong type | **FIXED** | `unit.py:106` - Now `MultiEnumField` | N/A |
| DEBT-010 | Unit.gender wrong type | **FIXED** | `unit.py:114` - Now `MultiEnumField` | N/A |
| DEBT-011 | Unit.discount wrong type | **FIXED** | `unit.py:90` - Now `EnumField` | N/A |
| DEBT-012 | Unit.zip_codes_radius wrong type | **FIXED** | `unit.py:116` - Now `IntField` | N/A |
| DEBT-013 | Unit.filter_out_x wrong type | **FIXED** | `unit.py:128` - Now `EnumField` | N/A |
| DEBT-014 | Unit.form_questions wrong type | CONFIRMED | `unit.py:121` - Now `MultiEnumField` - correct! | N/A |
| DEBT-015 | Unit.disabled_questions wrong type | CONFIRMED | `unit.py:122` - Now `MultiEnumField` - correct! | N/A |
| DEBT-016 | Unit.disclaimers wrong type | CONFIRMED | `unit.py:123` - Now `MultiEnumField` - correct! | N/A |
| DEBT-017 | Hours field name mismatches | **FIXED** | `hours.py:74-79` - Fields now "Monday", "Tuesday", etc. | N/A |
| DEBT-018 | Hours field type mismatches | **FIXED** | `hours.py:84-102` - `_get_multi_enum_field()` handles multi-enum | N/A |

### Phase 3: Process Entity Enhancement (5 items)

| ID | DEBT Item | Status | Evidence | Priority |
|----|-----------|--------|----------|----------|
| DEBT-019 | Process missing Sales-specific fields | CONFIRMED | `process.py:223-236` - Only 8 generic fields vs 67+ in Sales | P0 |
| DEBT-020 | Process missing Onboarding fields | CONFIRMED | Same pattern - generic model | P1 |
| DEBT-021 | Process missing Implementation fields | CONFIRMED | Same pattern - generic model | P1 |
| DEBT-022 | ProcessProjectRegistry incorrect design | MARKED FOR DELETE | Per IMPACT-PROCESS-CLEANUP - canonical project IS pipeline | P0 |
| DEBT-023 | ProcessType enum incomplete | PARTIAL | `process.py:39-65` - Has 7 types but missing granular types | P1 |

### Phase 4: Test Coverage & Documentation (3 items)

| ID | DEBT Item | Status | Evidence | Priority |
|----|-----------|--------|----------|----------|
| DEBT-024 | Test pyramid imbalance | CONFIRMED | See Section 5 - 95+ unit files vs 15 integration | P1 |
| DEBT-025 | Missing integration tests for detection | CONFIRMED | No `tests/integration/` detection tests | P1 |
| DEBT-026 | Stale documentation references | CONFIRMED | Multiple TDDs reference deleted ProcessProjectRegistry | P2 |

---

## 2. Dependency Graph

### Visual Representation

```
Phase 1: Foundation
    |
    +-- DEBT-001 (Process.PRIMARY_PROJECT_GID)
    |       |
    |       +-- DEBT-022 (ProcessProjectRegistry DELETE) [BLOCKER]
    |       |
    |       +-- DEBT-019 (Process Sales fields) [DEPENDENCY]
    |
    +-- DEBT-002 (ProcessHolder.PRIMARY_PROJECT_GID)
    |       |
    |       +-- Same dependencies as DEBT-001
    |
    +-- DEBT-003 (LocationHolder.PRIMARY_PROJECT_GID)
    |       |
    |       +-- Standalone (no dependencies)
    |
    +-- DEBT-004 (UnitHolder.PRIMARY_PROJECT_GID)
    |       |
    |       +-- Standalone (no dependencies)
    |
    +-- DEBT-005 (Detection Tier 2)
    |       |
    |       +-- DEBT-007 (WorkspaceProjectRegistry) [SOFT DEPENDENCY]
    |
    +-- DEBT-006 (Self-healing)
    |       |
    |       +-- DEBT-001..004 (PRIMARY_PROJECT_GID values) [REQUIRED]
    |       |
    |       +-- DEBT-005 (Detection tiers) [REQUIRED]
    |
    +-- DEBT-007 (WorkspaceProjectRegistry)
    |       |
    |       +-- DEBT-022 (ProcessProjectRegistry DELETE) [BLOCKER]
    |
    +-- DEBT-008 (Startup validation)
            |
            +-- DEBT-001..004 (PRIMARY_PROJECT_GID values) [REQUIRED]

Phase 2: Custom Fields
    |
    +-- DEBT-009..018 (Unit/Hours fields)
            |
            +-- **ALL FIXED** - No remaining work

Phase 3: Process Enhancement
    |
    +-- DEBT-019..021 (Process type-specific fields)
    |       |
    |       +-- DEBT-022 (ProcessProjectRegistry DELETE) [BLOCKER]
    |       |
    |       +-- DEBT-001 (Process.PRIMARY_PROJECT_GID) [REQUIRED]
    |
    +-- DEBT-022 (ProcessProjectRegistry DELETE)
    |       |
    |       +-- Must complete FIRST before DEBT-001, DEBT-019
    |
    +-- DEBT-023 (ProcessType enum)
            |
            +-- DEBT-019..021 (Process fields) [SOFT DEPENDENCY]

Phase 4: Test & Docs
    |
    +-- DEBT-024..026
            |
            +-- All Phase 1-3 items [WAIT FOR COMPLETION]
```

### Dependency Matrix

| Item | Blocks | Blocked By |
|------|--------|------------|
| DEBT-001 | DEBT-006, DEBT-019 | DEBT-022 |
| DEBT-002 | DEBT-006 | DEBT-022 |
| DEBT-003 | - | - |
| DEBT-004 | - | - |
| DEBT-005 | - | - |
| DEBT-006 | - | DEBT-001, DEBT-002, DEBT-003, DEBT-004, DEBT-005 |
| DEBT-007 | - | DEBT-022 |
| DEBT-008 | - | DEBT-001, DEBT-002, DEBT-003, DEBT-004 |
| DEBT-022 | DEBT-001, DEBT-002, DEBT-007, DEBT-019 | - |

### Critical Path

```
DEBT-022 (Delete ProcessProjectRegistry)
    -> DEBT-001/002 (Process PRIMARY_PROJECT_GID)
    -> DEBT-019 (Process Sales fields)
    -> DEBT-006 (Self-healing)
    -> Phase 4 items
```

---

## 3. Resolved Questions

### Question 1: PRIMARY_PROJECT_GID Values for All Entity Types

**RESOLVED** - Values confirmed from source code and analysis documents:

| Entity Type | Project Name | PRIMARY_PROJECT_GID | Source |
|-------------|--------------|---------------------|--------|
| **Business** | Businesses | `1200653012566782` | `business.py:154` |
| **Contact** | Contacts | `1200775689604552` | Audit document |
| **ContactHolder** | Contact Holder | `1201500116978260` | Audit document |
| **Unit** | Business Units | `1201081073731555` | `unit.py:57` |
| **UnitHolder** | Units | `None` (has no project) | `unit.py:509` |
| **Offer** | Business Offers | `1143843662099250` | Audit document |
| **OfferHolder** | Offer Holders | `1210679066066870` | Audit document |
| **Location** | Locations | `1200836133305610` | `location.py:42` |
| **LocationHolder** | N/A | `None` (has no project) | `location.py:298` |
| **Hours** | Hours | `1201614578074026` | `hours.py:46` |
| **Process** | (Multiple pipelines) | `None` (dynamic) | `process.py:165` |
| **ProcessHolder** | N/A | `None` (has no project) | `process.py:297` |
| **DNAHolder** | Backend DNA | `1167650840134033` | `business.py:51` |
| **ReconciliationHolder** | Reconciliations | `1203404998225231` | `business.py:70` |
| **AssetEditHolder** | Asset Edit Holder | `1203992664400125` | `business.py:106` |
| **AssetEdit** | Paid Content | `1202204184560785` | `asset_edit.py:65` |
| **VideographyHolder** | Videography Services | `1207984018149338` | `business.py:124` |

**Process Project GIDs** (all map to EntityType.PROCESS):

| Process Type | Project Name | GID |
|--------------|--------------|-----|
| SALES | Sales | `1200944186565610` |
| ONBOARDING | Onboarding | `1201319387632570` |
| IMPLEMENTATION | Implementation | `1201476141989746` |
| RETENTION | Retention | `1201346565918814` |
| REACTIVATION | Reactivation | `1201265144487549` |
| OUTREACH | Outreach | `1201753128450029` |

### Question 2: AssetEdit Project Location

**RESOLVED**: AssetEdit uses project "Paid Content" with GID `1202204184560785`.

- Source: `asset_edit.py:65` - `PRIMARY_PROJECT_GID: ClassVar[str | None] = "1202204184560785"`
- Verified in CUSTOM-FIELD-REALITY-AUDIT.md

### Question 3: Complete ProcessType Enum Values

**RESOLVED**: Current implementation in `process.py:39-65`:

```python
class ProcessType(str, Enum):
    # Pipeline types (stakeholder-aligned)
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"

    # Fallback (backward compatibility)
    GENERIC = "generic"
```

**Note**: Original TDD placeholders (AUDIT, BUILD, CREATIVE, etc.) were removed per stakeholder feedback. Current 7 values align with actual pipeline workflows.

### Question 4: Hours Model Field Names and Time Formats

**RESOLVED** - Already fixed in current codebase:

**Field Names** (`hours.py:74-79`):
```python
class Fields:
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    # Note: Sunday not found in Asana project per audit
```

**Time Format**: Multi-enum with time strings like `"08:00:00"`, `"17:00:00"`

**Implementation** (`hours.py:84-102`):
```python
def _get_multi_enum_field(self, field_name: str) -> list[str]:
    """Get multi-enum custom field value as list of strings."""
    # Returns e.g., ["08:00:00", "17:00:00"]
```

### Question 5: Unit Field Type Corrections (8 Mismatches)

**RESOLVED** - All 8 have been corrected:

| Field | Original Type | Correct Type | Current Status |
|-------|---------------|--------------|----------------|
| specialty | EnumField | MultiEnumField | **FIXED** `unit.py:106` |
| gender | EnumField | MultiEnumField | **FIXED** `unit.py:114` |
| discount | NumberField | EnumField | **FIXED** `unit.py:90` |
| zip_codes_radius | TextField | IntField | **FIXED** `unit.py:116` |
| filter_out_x | TextField | EnumField | **FIXED** `unit.py:128` |
| form_questions | TextField | MultiEnumField | **FIXED** `unit.py:121` |
| disabled_questions | TextField | MultiEnumField | **FIXED** `unit.py:122` |
| disclaimers | TextField | MultiEnumField | **FIXED** `unit.py:123` |

---

## 4. Test Pyramid Analysis

### File Count Methodology

```bash
# Unit tests
find tests/unit -name "*.py" -type f | wc -l
# Result: 95+ files

# Integration tests
find tests/integration -name "*.py" -type f | wc -l
# Result: 15 files
```

### Current Test Pyramid Ratio

| Test Type | File Count | Percentage |
|-----------|------------|------------|
| Unit Tests | 95 | 86% |
| Integration Tests | 15 | 14% |

### Analysis by Subdirectory

**Unit Tests** (`tests/unit/`):
- `cache/` - 17 files
- `dataframes/` - 16 files
- `models/business/` - 16 files
- `persistence/` - 12 files
- `automation/` - 6 files
- `clients/` - 4 files
- `patterns/` - 3 files
- `transport/` - 1 file
- Root level - 20 files

**Integration Tests** (`tests/integration/`):
- `persistence/` - 3 files
- Root level - 12 files

### Gap Assessment

**Missing Integration Coverage:**
1. Detection system end-to-end
2. WorkspaceProjectRegistry with live API
3. Business hierarchy hydration
4. Custom field type coercion
5. Process pipeline state transitions

**Recommended Ratio**: 70% unit / 20% integration / 10% e2e
**Current Ratio**: 86% unit / 14% integration / 0% e2e

---

## 5. Phase Ordering Confirmation

### Original Order (Proposed)

1. Phase 1: Detection System Foundation
2. Phase 2: Custom Field Remediation
3. Phase 3: Process Entity Enhancement
4. Phase 4: Test Coverage & Documentation

### Validated Order (Adjusted)

**CRITICAL CHANGE**: ProcessProjectRegistry deletion must happen FIRST, before any Process-related work.

**New Phase Order:**

```
Phase 0: Cleanup (NEW)
    - Delete ProcessProjectRegistry (process_registry.py)
    - Delete test_process_registry.py
    - Update imports in process.py, seeder.py, detection.py, __init__.py
    - ~1,085 lines removed per IMPACT-PROCESS-CLEANUP

Phase 1: Detection System Foundation (Original)
    - PRIMARY_PROJECT_GID for Process, ProcessHolder
    - WorkspaceProjectRegistry timing
    - Detection Tier 2 improvements
    - Self-healing implementation

Phase 2: Custom Field Remediation
    - **SKIPPED** - All items already fixed

Phase 3: Process Entity Enhancement
    - Process type-specific fields (Sales: 67 fields, Onboarding: 41 fields, etc.)
    - ProcessType enum refinements

Phase 4: Test Coverage & Documentation
    - Integration test additions
    - Documentation cleanup
```

---

## 6. Risk Assessment

### Phase 0: Cleanup

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing workflows | Medium | High | Test coverage before deletion |
| Import errors | High | Low | Single PR with all changes |
| Tests fail without registry | High | Medium | Delete tests in same PR |

### Phase 1: Detection System

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Wrong PRIMARY_PROJECT_GID values | Low | High | Values confirmed from audit |
| WorkspaceProjectRegistry race condition | Medium | Medium | Add mutex/lock |
| Self-healing causes data corruption | Low | High | Add dry-run mode |

### Phase 3: Process Enhancement

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Process subclass explosion | Medium | Medium | Use composition over inheritance |
| API rate limits during field reads | Medium | Low | Batch field access |
| Backward compatibility breaks | Medium | High | Deprecation warnings |

### Phase 4: Test & Docs

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Integration tests flaky | High | Low | Use mocks for external deps |
| Documentation drift | Medium | Low | Link docs to code |

---

## 7. New Discoveries

### Discovery 1: AssetEditHolder Has Custom Fields (Pattern Break)

**Finding**: AssetEditHolder has 4 custom fields unlike all other holders:
- Generic Assets (enum)
- Template Assets (enum)
- Review All Ads (enum)
- Asset Edit Comments (text)

**Impact**: Holder pattern assumption (0 custom fields) is violated. May need:
1. Add field accessors to AssetEditHolder (break pattern consistency)
2. Treat as configuration fields cascading to children
3. Document as exception

**Recommendation**: Add as DEBT-027 - Architectural decision needed.

### Discovery 2: Specialty Field Has Two Different GIDs

**Finding**: Two distinct Specialty fields exist:
- GID `1202981898844151` (multi_enum) - Used by Unit, AssetEdit
- GID `1200943943116217` (enum) - Used by Offer, Business, Process types

**Impact**: Field resolution must handle both GIDs or standardize to one.

**Recommendation**: Add as DEBT-028 - Field disambiguation required.

### Discovery 3: Process Has Dual Project Membership Pattern

**Finding**: Process entities belong to BOTH:
1. ProcessHolder (as subtask hierarchy)
2. Pipeline Project (as project member for state tracking)

**Impact**: Current understanding that "canonical project IS the pipeline" may be incomplete.

**Recommendation**: Clarify in TDD whether dual membership is intentional.

### Discovery 4: Business Model Missing 16 Fields

**Finding**: Per CUSTOM-FIELD-REALITY-AUDIT, Business model is missing:
- Specialty, Time Zone, Ad Account ID
- Meta Spend Sub ID, TikTok Spend Sub ID, Solution Fee Sub ID
- TikTok Profile, Logo URL, Header URL, Website
- Landing Page URL, Scheduling Link
- MRR, Weekly Ad Spend, Discount, Status

**Impact**: Business field coverage is approximately 54% (19/35 fields).

**Recommendation**: Add as DEBT-029 if field coverage is a priority.

### Discovery 5: Contact Model Missing 2 Fields

**Finding**: Contact missing:
- Office Location (text)
- State (text)

**Impact**: Minor gap - 91% coverage (19/21 fields).

**Recommendation**: Low priority - address if Contact fields become priority.

---

## 8. Summary and Recommendations

### Immediate Actions

1. **Create Phase 0 PRD** for ProcessProjectRegistry cleanup
2. **Update DEBT inventory** to mark completed items (DEBT-009 through DEBT-018)
3. **Revise phase timeline** - Phase 2 is complete, can skip

### Blocking Questions Resolved

All 5 blocking questions have been answered with source citations:
- PRIMARY_PROJECT_GID values documented
- AssetEdit project confirmed
- ProcessType enum validated
- Hours model corrected
- Unit field types all fixed

### Quality Gate Status

| Criterion | Status |
|-----------|--------|
| All 26 DEBT items validated | PASS - 10 already fixed |
| PRIMARY_PROJECT_GID values specific | PASS - All values documented |
| ProcessType enum complete | PASS - 7 stakeholder-aligned types |
| Hours field names exact | PASS - Already corrected |
| Unit field types correct | PASS - All 8 fixed |
| Dependency graph complete | PASS - No circular dependencies |
| Test pyramid ratio calculated | PASS - 86/14 unit/integration |

### Next Steps

1. Create PROMPT-0-TECH-DEBT-REMEDIATION.md with validated scope
2. Create PRD for Phase 0 (ProcessProjectRegistry cleanup)
3. Update initiative timeline to reflect Phase 2 completion
4. Schedule Phase 0 execution

---

## Appendix A: File Reference Summary

| File | Purpose | Lines |
|------|---------|-------|
| `detection.py` | Entity type detection | 924 |
| `process.py` | Process/ProcessHolder models | 360 |
| `registry.py` | ProjectTypeRegistry, WorkspaceProjectRegistry | 679 |
| `hours.py` | Hours model | 341 |
| `unit.py` | Unit/UnitHolder models | 536 |
| `location.py` | Location/LocationHolder models | 393 |
| `asset_edit.py` | AssetEdit model | 743 |
| `business.py` | Business model + stub holders | 788 |

## Appendix B: Analysis Documents Referenced

1. `/docs/analysis/CUSTOM-FIELD-REALITY-AUDIT.md` - Field type audit (1085 lines)
2. `/docs/analysis/DETECTION-SYSTEM-ANALYSIS.md` - Detection gaps (254 lines)
3. `/docs/analysis/ANALYSIS-PROCESS-ENTITIES.md` - Process architecture (549 lines)
4. `/docs/analysis/GAP-ANALYSIS-WORKSPACE-PROJECT-REGISTRY.md` - Registry gaps (434 lines)
5. `/docs/analysis/IMPACT-PROCESS-CLEANUP.md` - ProcessProjectRegistry deletion (479 lines)
6. `/docs/analysis/DISCOVERY-DETECTION-SYSTEM.md` - Detection discovery (570 lines)
7. `/docs/analysis/SECTION-HANDLING-ANALYSIS.md` - Section name retention (387 lines)

---

*End of Discovery Document*
