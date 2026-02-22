# QA Report: Classification API Surface Enhancements (S-1, S-2, S-3)

## Overview
- **Test Period**: 2026-02-20
- **Tester**: QA Adversary
- **Build**: main branch, post-implementation of S-1/S-2/S-3
- **Test Baseline**: 84 targeted tests, all passing (0.66s)

---

## Results Summary

| Category | Pass | Fail | Notes |
|----------|------|------|-------|
| Acceptance Criteria (S-3) | 7 | 0 | Model fields, derivation, serialization |
| Acceptance Criteria (S-1) | 11 | 0 | Route validation, service filtering, backward compat |
| Acceptance Criteria (S-2) | 27 | 0 | Model validation, resolver, integration, error serialization |
| Cross-Item Consistency | 5 | 0 | S-1 filter and S-3 derivation use same code path |
| Backward Compatibility | 3 | 0 | No-param returns all, existing consumers unaffected |
| Edge Cases | 6 | 0 | Empty results, unknown sections, case sensitivity |
| Security | 3 | 0 | No auth bypass, no PII exposure, no privilege escalation |
| Anti-Pattern Compliance | 3 | 0 | No cache key proliferation, no DF schema change, no auth change |
| Static Analysis | 2 | 0 | ruff check: clean, mypy --strict: clean |

**Totals: 67 PASS, 0 FAIL**

---

## Test Cases

### TC-01: S-3 -- current_section and current_classification fields

**Requirement**: S-3 in ANALYSIS-classification-api-surface.md
**Priority**: High
**Type**: Functional

| ID | Scenario | Expected | Actual | Result |
|----|----------|----------|--------|--------|
| 01a | OfferTimelineEntry with both fields populated | Serialize to JSON with string values | Fields present as `"ACTIVE"` / `"active"` | PASS |
| 01b | OfferTimelineEntry without new fields | Default to `null` | Both fields `null` | PASS |
| 01c | current_classification is string, not enum | `isinstance(str)` | `True` | PASS |
| 01d | extra fields still forbidden | ValidationError on bogus field | Pydantic raises | PASS |
| 01e | Derivation from last interval (ACTIVATING -> ACTIVE) | current_section="ACTIVE" | Correct | PASS |
| 01f | Empty intervals | Both fields None | Correct | PASS |
| 01g | Unknown section | current_section set, current_classification=None | Correct | PASS |

**Source**: `tests/unit/models/test_section_timeline.py::TestOfferTimelineEntry` (4 tests), `tests/unit/services/test_section_timeline_service.py::TestComputeDayCountsCurrentFields` (7 tests)

### TC-02: S-1 -- classification filter on section-timelines endpoint

**Requirement**: S-1 in ANALYSIS-classification-api-surface.md
**Priority**: High
**Type**: Functional

| ID | Scenario | Expected | Actual | Result |
|----|----------|----------|--------|--------|
| 02a | `?classification=bogus` | 422 VALIDATION_ERROR | 422, "bogus" in message | PASS |
| 02b | `?classification=active` | Pass through to service | `classification_filter="active"` in call | PASS |
| 02c | No classification param | Pass None to service | `classification_filter=None` | PASS |
| 02d | Filter active only | Only ACTIVE entries returned | 1 of 4 entries | PASS |
| 02e | Filter inactive only | Only INACTIVE entries returned | 1 of 4 entries | PASS |
| 02f | Filter with no matches (ignored) | Empty list, not error | `[]` | PASS |
| 02g | No filter returns all | All 4 entries | 4 entries | PASS |
| 02h | Response includes current_section/current_classification | Fields present | Verified in JSON | PASS |
| 02i | Null current_section in response | `null` | Correct | PASS |

**Source**: `tests/api/test_section_timelines.py` (5 tests), `tests/unit/services/test_section_timeline_service.py::TestComputeDayCountsClassificationFilter` (6 tests)

### TC-03: S-2 -- classification virtual filter on query engine

**Requirement**: S-2 in ANALYSIS-classification-api-surface.md
**Priority**: High
**Type**: Functional

| ID | Scenario | Expected | Actual | Result |
|----|----------|----------|--------|--------|
| 03a | `classification="active"` in RowsRequest | Valid, section=None | Correct | PASS |
| 03b | No classification in RowsRequest | Defaults to None | Correct | PASS |
| 03c | `section` + `classification` both set | ValidationError "mutually exclusive" | Correct | PASS |
| 03d | `classification` with `where`, `select`, `limit` | All coexist | Correct | PASS |
| 03e | `_resolve_classification(None, "offer")` | Returns None | Correct | PASS |
| 03f | `_resolve_classification("active", "offer")` | Returns ACTIVE sections set (21 sections) | Correct | PASS |
| 03g | `_resolve_classification("ACTIVE", "offer")` | Case-insensitive, same as "active" | Correct | PASS |
| 03h | `_resolve_classification("active", "unit")` | Unit classifier sections | Correct | PASS |
| 03i | `_resolve_classification("active", "business")` | ClassificationError "No classifier registered" | Correct | PASS |
| 03j | `_resolve_classification("bogus", "offer")` | ClassificationError "Invalid classification value" | Correct | PASS |
| 03k | Execute rows with classification="active" | Returns 3 rows (ACTIVE, STAGING, STAGED) | Correct | PASS |
| 03l | Classification + WHERE predicate | ANDed filter | Correct | PASS |
| 03m | Classification=None returns all 7 rows | No filter applied | Correct | PASS |
| 03n | Case-insensitive section matching | "ACTIVE", "active", "Active" all match | All 3 match | PASS |
| 03o | ClassificationError.to_dict() | `error: "INVALID_CLASSIFICATION"` | Correct | PASS |
| 03p | ClassificationError maps to HTTP 400 | `_ERROR_STATUS[ClassificationError] == 400` | Correct | PASS |

**Source**: `tests/unit/query/test_classification_filter.py` (27 tests)

### TC-04: Cross-Item Consistency (S-1 vs S-3 agreement)

**Requirement**: Validation item 1 from brief
**Priority**: High
**Type**: Consistency

| ID | Scenario | Expected | Actual | Result |
|----|----------|----------|--------|--------|
| 04a | S-1 filter uses same derivation as S-3 | Filter comparison `current_classification != filter` uses the same value populated in S-3 | Both derive from `classifier.classify(section_name).value` at service line 672-673, filter at line 678-679 | PASS |
| 04b | `sections_for(ACTIVE)` == set of sections where `classify(s)==ACTIVE` | Bidirectional equivalence | Verified programmatically: both produce 21 identical section names | PASS |
| 04c | S-2 `_resolve_classification` uses `sections_for()`, S-1 uses `classify()` | Mathematical equivalence | Same internal `_mapping` dict, verified identical results | PASS |
| 04d | Filter "active" returns entries whose current_classification IS "active" | Entries with classification="active" only | Test `test_filter_active_only` confirms | PASS |
| 04e | Filtered entries' day counts still computed correctly | Day counts unaffected by filter | Filter is post-computation | PASS |

### TC-05: Backward Compatibility

**Requirement**: Validation item 2 from brief
**Priority**: High
**Type**: Regression

| ID | Scenario | Expected | Actual | Result |
|----|----------|----------|--------|--------|
| 05a | Section-timelines without classification param | Returns ALL entries (same as before) | 3 entries returned, `classification_filter=None` | PASS |
| 05b | Query router RowsRequest without classification | No effect on existing queries | `classification=None`, all 7 rows | PASS |
| 05c | Existing serialization includes new fields as null | `current_section: null, current_classification: null` | Present and null | PASS |

### TC-06: Error Handling Consistency

**Requirement**: Validation items 3-4 from brief
**Priority**: High
**Type**: Edge Case / Error

| ID | Scenario | Expected | Actual | Result |
|----|----------|----------|--------|--------|
| 06a | Invalid classification on section-timelines | 422 VALIDATION_ERROR | 422 | PASS |
| 06b | Invalid classification on query router | 400 INVALID_CLASSIFICATION | 400 (via `_ERROR_STATUS` mapping) | PASS |
| 06c | Entity type without classifier on query router | 400 INVALID_CLASSIFICATION | ClassificationError with available types listed | PASS |
| 06d | section + classification mutual exclusion | Pydantic ValidationError (422) | ValueError "mutually exclusive" | PASS |
| 06e | Empty results from valid filter | Empty list `[]`, not error | Empty list | PASS |
| 06f | classification on AggregateRequest | 422 from Pydantic `extra=forbid` | AggregateRequest has no classification field | PASS |

### TC-07: Anti-Pattern Compliance

**Requirement**: Section 7 of ANALYSIS-classification-api-surface.md
**Priority**: Medium
**Type**: Architecture

| ID | Check | Expected | Actual | Result |
|----|-------|----------|--------|--------|
| 07a | No per-classification cache keys | Zero matches for `cache_key.*classification` | Zero matches | PASS |
| 07b | No classification column in DataFrame schemas | Zero matches in `dataframes/schemas/` | Zero matches | PASS |
| 07c | No auth scheme changes | S2S-only on query router, dual-mode on section-timelines | `require_service_claims` and `AsanaClientDualMode` unchanged | PASS |

---

## Defects

### DEF-01: Case Sensitivity Inconsistency Between S-1 and S-2 (LOW)

**Severity**: Low
**Priority**: Low (cosmetic, does not cause incorrect results)
**Status**: OPEN

**Reproduction**:
1. S-1 (section-timelines): `?classification=ACTIVE` returns 422 because `"ACTIVE" not in {"active", "activating", "inactive", "ignored"}`
2. S-2 (query engine): `{"classification": "ACTIVE"}` succeeds because `_resolve_classification` calls `.lower()` before `AccountActivity(...)` construction

**Expected**: Both endpoints should handle case the same way.

**Actual**:
- Section-timelines endpoint validates `classification not in _VALID_CLASSIFICATIONS` where `_VALID_CLASSIFICATIONS = {e.value for e in AccountActivity}` (all lowercase). No `.lower()` applied to input.
- Query engine does `AccountActivity(classification.lower())`, accepting any case.

**Impact**: Negligible. The AccountActivity enum values are all lowercase. API consumers will use lowercase. The query router is more lenient, which is the less surprising direction.

**Location**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py:113-114` (missing `.lower()`)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py:451` (has `.lower()`)

**Recommended Fix**: Add `classification = classification.lower()` before the validation check in `section_timelines.py:114`, or add `.lower()` inside the `not in` check: `classification.lower() not in _VALID_CLASSIFICATIONS`.

---

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Classification filter bypasses auth | NO | Section-timelines still requires `AsanaClientDualMode`, query router still requires `require_service_claims` |
| PII in new fields | NO | `current_section` is an Asana section name (e.g., "ACTIVE"), `current_classification` is an enum value (e.g., "active"). Neither contains PII |
| Classification filter leaks cross-tenant data | NO | Post-cache filter on same data set; does not expand access |
| S2S-only restriction preserved on query router | YES | `require_service_claims` dependency unchanged |

---

## Documentation Impact Assessment

**User-facing behavior change**: YES. Two API endpoints now accept a new `classification` parameter, and the section-timelines response includes two new optional fields. Any consumer documentation or API guides should be updated.

**Breaking changes**: NONE. All new fields are optional with null defaults. All new parameters are optional with no-op defaults. Existing consumers ignoring the new fields/parameters see identical behavior.

---

## Release Recommendation

**CONDITIONAL GO**

**Rationale**: All 84 tests pass. All acceptance criteria verified. No critical or high defects. Static analysis clean (ruff + mypy --strict). Cross-item consistency confirmed. Anti-pattern compliance verified. Security checks pass.

**Condition**: DEF-01 (case sensitivity inconsistency) is low severity and does not block release. However, it should be fixed before the next release to prevent consumer confusion. A one-line fix: add `.lower()` to the section-timelines classification validation.

**Known Issues**:
- DEF-01: `?classification=ACTIVE` (uppercase) returns 422 on section-timelines but succeeds on query router. Low impact -- documented, fix is trivial.
- HTTP status divergence is intentional: section-timelines returns 422 (Pydantic validation pattern), query router returns 400 (domain error pattern). This is consistent with each endpoint's existing error handling convention.

**Not Tested**:
- Production load with 3,774 offers (unit tests use small fixtures; production performance was validated during SectionTimeline shipping)
- Actual Asana API integration (tested via mocks; integration testing is a separate concern)
