# QA Verdict: I2 Phase 4 -- DataFrameService Extraction

**Date**: 2026-02-15
**Scope**: Commits a3daa95, 746a835, 1c95922
**Verdict**: **CONDITIONAL GO**

---

## Test Summary

| Category | Count | Result |
|----------|-------|--------|
| Pre-existing unit tests (test_dataframe_service.py) | 33 | PASS |
| Adversarial unit tests (added) | 48 | PASS |
| API integration tests (test_routes_dataframes.py) | 48 | PASS |
| Full test suite | 10,262 | PASS (46 skip, 2 xfail) |

---

## Changes Validated

1. **DataFrameService** -- New service class (351 LOC) extracting schema resolution, opt_fields management, and DataFrame construction from route handlers. Two build paths: project (async via DataFrameViewPlugin) and section (sync via SectionDataFrameBuilder).

2. **dataframes.py refactoring** -- Route file reduced from 556 to 309 LOC. Routes now handle only HTTP concerns (content negotiation, response formatting). Business logic delegated to DataFrameService.

3. **DataFrameServiceDep** -- New FastAPI dependency in `dependencies.py`. Stateless, per-request lifecycle. No constructor dependencies.

4. **InvalidSchemaError** -- New exception subclassing InvalidParameterError. NOT registered in SERVICE_ERROR_MAP; relies on MRO walk to resolve to HTTP 400.

5. **reset_schema_cache()** -- Module-level cache reset function for test isolation.

6. **_SectionProxy** -- Lightweight adapter replacing inline class definition from old dataframes.py. Uses `__slots__` for memory efficiency.

---

## Adversarial Test Coverage

### Risk Area 1: InvalidSchemaError MRO Status Resolution (3 tests)

| Test | Target | Result |
|------|--------|--------|
| MRO walk finds 400 not 500 | get_status_for_error(InvalidSchemaError) | PASS |
| MRO chain is correct | InvalidParameterError before ServiceError | PASS |
| status_hint fallback is also 400 | Backup resolution path | PASS |

**Conclusion**: TDD deviation validated. InvalidSchemaError correctly resolves to HTTP 400 via MRO walk through InvalidParameterError, despite not being directly in SERVICE_ERROR_MAP.

### Risk Area 2: Content Negotiation Preservation (6 tests)

| Test | Target | Result |
|------|--------|--------|
| MIME_POLARS in accept returns true | _should_use_polars_format | PASS |
| application/json returns false | JSON default | PASS |
| None accept returns false | Missing header | PASS |
| Mixed accept with polars returns true | Multi-type header | PASS |
| Empty accept returns false | Edge case | PASS |
| Polars substring attack | "application/polars" vs full MIME | PASS |

### Risk Area 3: Section Endpoint 404 Handling (4 tests)

| Test | Target | Result |
|------|--------|--------|
| project=None crashes with AttributeError | **DEFECT D1** | DOCUMENTED |
| project.gid="" (empty string) raises EntityNotFoundError | Falsy GID | PASS |
| project.gid=None raises EntityNotFoundError | Null GID | PASS |
| Empty response raises EntityNotFoundError | No project key | PASS |

### Risk Area 4: Pagination Offset Passthrough Fidelity (5 tests)

| Test | Target | Result |
|------|--------|--------|
| Project offset=None not in params | No spurious offset | PASS |
| Project offset="" not in params | Empty string is falsy | PASS |
| Section offset=None not in params | Section endpoint parity | PASS |
| Section offset passthrough exact | Base64-like cursor preserved | PASS |
| Project limit passthrough exact | Limit value forwarded | PASS |

### Schema Cache Isolation (4 tests)

| Test | Target | Result |
|------|--------|--------|
| Cache shared between service instances | Module-level singleton | PASS |
| Reset produces new cache objects | id() differs after reset | PASS |
| Cache content matches registry | All registered schemas present | PASS |
| Valid schemas list is sorted | Alphabetical ordering | PASS |

### _SectionProxy Correctness (5 tests)

| Test | Target | Result |
|------|--------|--------|
| Empty tasks list | Valid construction | PASS |
| Project dict format matches builder expectations | {"gid": "..."} | PASS |
| No extra attributes via __slots__ | Memory efficiency enforced | PASS |
| Tasks list is not copied | Same object reference | PASS |
| None tasks value accepted | Builder handles downstream | PASS |

### get_schema() Boundary Inputs (9 tests)

| Test | Target | Result |
|------|--------|--------|
| Numeric string raises | "42" is not a schema | PASS |
| Special characters raise | SQL injection attempt | PASS |
| Very long name raises | 1000-char input | PASS |
| Tab whitespace returns base | \t triggers fallback | PASS |
| Newline whitespace returns base | \n triggers fallback | PASS |
| Wildcard with spaces rejected | " * " normalized | PASS |
| Case preserved in error message | "UnItZ" in error | PASS |
| base resolves to wildcard schema | task_type == "*" | PASS |
| All 7 schemas resolve | Exhaustive enumeration | PASS |

### DataFrameResult Edge Cases (5 tests)

| Test | Target | Result |
|------|--------|--------|
| Empty DataFrame | Zero rows, correct shape | PASS |
| None offset | Terminal pagination | PASS |
| Empty string offset | Falsy but not None | PASS |
| has_more=False with offset present | Inconsistent but allowed | PASS |
| Equality | Frozen dataclass equality | PASS |

### TASK_OPT_FIELDS Deduplication (5 tests)

| Test | Target | Result |
|------|--------|--------|
| No whitespace in fields | Field quality | PASS |
| No empty strings | Field quality | PASS |
| All fields use dot notation or plain | Format consistency | PASS |
| Joined CSV is valid | No double commas | PASS |
| Field count is stable (26) | Regression guard | PASS |

### Empty DataFrame Schema Conformance (2 tests)

| Test | Target | Result |
|------|--------|--------|
| Empty DF has correct columns | Schema column names match | PASS |
| Empty DF has correct dtypes | Schema dtypes match | PASS |

---

## Defects Found

### D1: AttributeError on section with null project (MEDIUM)

**Severity**: Medium
**Priority**: P2
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/dataframe_service.py` line 245

**Reproduction Steps**:
1. Call `build_section_dataframe()` where the section API returns `{"project": null}`
2. Line 245: `section_data.get("project", {}).get("gid")` executes
3. `.get("project", {})` returns `None` (key exists, value is null; default `{}` only used when key is absent)
4. `None.get("gid")` raises `AttributeError: 'NoneType' object has no attribute 'get'`

**Expected**: `EntityNotFoundError` ("Section not found or has no parent project")
**Actual**: Unhandled `AttributeError` propagates as HTTP 500

**Impact**: Orphaned sections in Asana (where a section's parent project has been deleted) will cause HTTP 500 instead of the expected HTTP 404. This is a pre-existing pattern that was carried forward from the old inline code in `dataframes.py`.

**Fix**: Replace line 245 with:
```python
project_data = section_data.get("project") or {}
project_gid = project_data.get("gid") if isinstance(project_data, dict) else None
```

**Test documenting defect**: `TestAdversarialBuildSectionProjectKeyVariants::test_project_none_crashes_with_attribute_error`

---

## Risk Assessment

### D1 is a Carried-Forward Defect

The `section_data.get("project", {}).get("gid")` pattern was present in the original `dataframes.py` route code before extraction. The DataFrameService faithfully preserved this behavior. The defect is pre-existing, not introduced by the extraction.

The Asana API returns `"project": null` for orphaned sections (sections whose parent project was deleted). This is uncommon but possible in production.

**Recommendation**: Fix in a follow-up commit. The fix is a one-line change with no downstream risk.

---

## Files Tested

- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/dataframe_service.py` (351 LOC)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/dataframes.py` (309 LOC)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py` (594 LOC)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` (344 LOC)
- `/Users/tomtenuta/Code/autom8_asana/tests/api/test_routes_dataframes.py` (1021 LOC)

## Test Files Modified

- `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_dataframe_service.py` (48 adversarial tests added, total 81)

---

## Documentation Impact Assessment

No user-facing behavior changes. The API endpoints, request/response formats, error codes, and status codes are all preserved. The extraction is purely internal refactoring.

---

## Release Recommendation

**CONDITIONAL GO** -- All acceptance criteria verified. 48 adversarial tests added covering MRO status resolution, content negotiation, section 404 handling, schema cache isolation, pagination fidelity, schema boundary inputs, DataFrame result edge cases, and opt_fields deduplication. One medium-severity defect found (D1: AttributeError on null project) but it is a pre-existing pattern carried forward from the old inline code, not introduced by this extraction. Recommend fixing D1 in a follow-up commit before the next release.

**Condition**: D1 should be fixed before this code path handles orphaned sections in production. If orphaned sections are not expected in the target Asana workspace, this can ship as-is.
