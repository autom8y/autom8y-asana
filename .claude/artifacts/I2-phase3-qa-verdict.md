# QA Verdict: I2 Phase 3 -- QueryService DI Wiring + query_v2.py Alignment

**Date**: 2026-02-15
**Scope**: Commits b1cb469, 8909dbe, 5ba3386
**Verdict**: **GO**

---

## Test Summary

| Category | Count | Result |
|----------|-------|--------|
| Pre-existing unit tests (test_query_service.py) | 20 | PASS |
| Adversarial unit tests (added) | 22 | PASS |
| API integration tests (test_routes_query*.py) | 334 | PASS |
| Full test suite | 10,214 | PASS (46 skip, 2 xfail) |

---

## Changes Validated

1. **resolve_section_index()** -- Module-level function in `services/query_service.py`. Manifest-first, enum-fallback strategy for building SectionIndex. Replaces inline pattern from query_v2.py.

2. **strip_section_conflicts()** -- Module-level function in `services/query_service.py`. EC-006 section param vs predicate conflict resolution. Replaces inline `_has_section_pred()` + `strip_section_predicates()` pattern.

3. **_has_section_pred()** -- Moved from `api/routes/query.py` to `services/query_service.py`. Predicate tree walker for detecting section comparisons.

4. **EntityService.project_registry** -- New `@property` exposing `_project_registry` for query_v2.py to pass to `QueryEngine.execute_rows()`.

5. **query_v2.py EntityServiceDep wiring** -- Replaced ~100 lines of inline entity validation (registry lookup, project GID check, bot PAT acquisition) with `EntityServiceDep` injection.

6. **query.py cleanup** -- Removed `_get_query_service()` and `_has_section_pred()`, replaced with imports from `query_service`.

---

## Adversarial Test Coverage

### Risk Area 1: Section Index Behavior (5 tests)

| Test | Target | Result |
|------|--------|--------|
| Empty string section_name not treated as None | resolve_section_index("", ...) | PASS -- correctly enters manifest path |
| S3 transport error propagates unhandled | ConnectionError in from_manifest_async | PASS -- propagates (by design, matches old code) |
| create_section_persistence failure | RuntimeError in factory | PASS -- propagates |
| Empty manifest falls back to enum | resolve returns None | PASS -- enum fallback activated |
| Unknown entity type returns empty enum index | from_enum_fallback for unknown type | PASS -- returns empty SectionIndex |

### Risk Area 2: Error Response Parity (7 tests)

| Test | Target | Result |
|------|--------|--------|
| UnknownEntityError has code UNKNOWN_ENTITY_TYPE | Wire format | PASS |
| UnknownEntityError maps to HTTP 404 | get_status_for_error() | PASS |
| ServiceNotConfiguredError has code SERVICE_NOT_CONFIGURED | Wire format | PASS |
| ServiceNotConfiguredError maps to HTTP 503 | get_status_for_error() | PASS |
| project_gid=None raises ServiceNotConfiguredError | EntityService.validate_entity_type() | PASS |
| Missing bot PAT raises ServiceNotConfiguredError | EntityService._acquire_bot_pat() | PASS |
| to_dict() wire format for both error types | JSON structure | PASS |

### Risk Area 3: Predicate Tree Walker (_has_section_pred) (5 tests)

| Test | Target | Result |
|------|--------|--------|
| Deeply nested AND->OR->NOT->AND section detected | 4-level nesting | PASS |
| No section in deep tree returns False | 4-level non-section | PASS |
| NOT(section) detected | NotGroup wrapper | PASS |
| OR with mixed section/non-section returns True | OrGroup | PASS |
| Arbitrary objects return False | str, int, None | PASS |

### Risk Area 4: strip_section_conflicts Field Preservation (3 tests)

| Test | Target | Result |
|------|--------|--------|
| model_copy preserves all fields | select, limit, offset, order_by, order_dir | PASS |
| Section in OR group stripped correctly | OrGroup with section | PASS |
| No mutation of original request | Immutability check | PASS |

### Contract Parity: resolve_section vs resolve_section_index (2 tests)

| Test | Target | Result |
|------|--------|--------|
| Both succeed when manifest resolves | Happy path consistency | PASS |
| Both fall back to enum on empty manifest | Fallback consistency | PASS |

---

## Defects Found

**None.** Zero defects discovered during adversarial testing.

---

## Known Behavioral Differences (Intentional, Not Defects)

These are documented behavioral changes between the old inline code and the new EntityServiceDep wiring. They were already addressed in the existing test suite (see `test_routes_query.py::TestQueryProjectNotConfigured`).

### D1: Error Code Change for Uninitialized Registry

- **Old behavior**: When `EntityProjectRegistry` is not initialized (`is_ready() == False`), the old inline code returned `503 / PROJECT_NOT_CONFIGURED`.
- **New behavior**: `EntityService.validate_entity_type()` calls `get_resolvable_entities()` which returns empty set, so entity validation fails first with `404 / UNKNOWN_ENTITY_TYPE`.
- **Impact**: Low. This is a startup-only edge case. Callers should retry on both 404 and 503. The existing test `test_empty_registry_returns_404` documents this change.

### D2: Error Code Change for Missing Project GID

- **Old behavior**: `503 / PROJECT_NOT_CONFIGURED`
- **New behavior**: `503 / SERVICE_NOT_CONFIGURED`
- **Impact**: Low. HTTP status (503) is preserved. Error code changed but callers should handle by status code, not error code string. The existing test `test_registry_none_returns_503` documents this change.

---

## Risk Assessment

### resolve_section_index() Lacks S3 Error Handling

`resolve_section_index()` does NOT catch `S3_TRANSPORT_ERRORS` around `SectionIndex.from_manifest_async()`. If S3 is unreachable, the exception propagates and the request fails with HTTP 500.

- **Severity**: Low (pre-existing risk, faithfully extracted from old inline code)
- **Impact**: Section-filtered query_v2 requests fail with 500 instead of gracefully falling back to enum when S3 is down
- **Mitigation**: The sibling function `resolve_section()` in query.py's `/rows` endpoint does catch S3 errors. The query_v2 endpoints use `resolve_section_index()` which does not.
- **Recommendation**: Future improvement (not a blocker). Consider adding `try/except S3_TRANSPORT_ERRORS` wrapper around the manifest call in `resolve_section_index()`, matching the pattern in `resolve_section()`.

---

## Files Tested

- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/entity_service.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query_v2.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/dependencies.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py`

## Test Files Modified

- `/Users/tomtenuta/Code/autom8_asana/tests/unit/services/test_query_service.py` (22 adversarial tests added)

---

## Release Recommendation

**GO** -- All acceptance criteria verified. No defects found. 22 adversarial tests added covering section index edge cases, error response parity, predicate tree walking, and model copy field preservation. Known behavioral differences (D1, D2) are intentional and documented in existing tests. One low-severity pre-existing risk documented (resolve_section_index S3 error handling) but not a blocker.
