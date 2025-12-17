# Test Plan: Custom Field Unification (Initiative B)

## Metadata
- **TP ID**: TP-HARDENING-B
- **Status**: APPROVED
- **Author**: QA/Adversary
- **Created**: 2025-12-16
- **Last Validated**: 2025-12-16 (Post DEF-001 fix)
- **PRD Reference**: PRD-HARDENING-B
- **TDD Reference**: TDD-HARDENING-B

## Test Scope

### In Scope
- CustomFieldAccessor reset behavior after SaveSession commit
- Task `_original_custom_fields` snapshot updates
- `custom_fields_editor()` method functionality
- `get_custom_fields()` deprecation warning
- No duplicate API calls on multiple commits (FR-007)
- Partial failure handling (FR-009)
- Business layer compatibility (FR-010)
- Edge cases: accessor None, empty modifications, None custom_fields

### Out of Scope
- ChangeTracker core architecture changes
- Direct list mutation deprecation warnings (FR-005)
- No-op detection in `set()` (FR-006)
- Performance benchmarking

## Requirements Traceability

| Requirement ID | Test Cases | Coverage Status |
|----------------|------------|-----------------|
| FR-001 | TC-001, TC-002 | Covered (PASS) |
| FR-002 | TC-003, TC-004 | Covered (PASS) |
| FR-003 | TC-005, TC-006 | Covered (PASS) |
| FR-004 | TC-007, TC-008 | Covered (PASS) |
| FR-007 | TC-009, TC-010 | Covered (PASS) - Fixed in DEF-001 |
| FR-009 | TC-011, TC-012 | Covered (PASS) |
| FR-010 | TC-013, TC-014 | Covered (PASS) |

## Test Cases

### Functional Tests

| TC ID | Description | Steps | Expected Result | Priority | Status |
|-------|-------------|-------|-----------------|----------|--------|
| TC-001 | Accessor modifications cleared after commit | 1. Track task with custom fields 2. Set field via accessor 3. Commit 4. Check has_changes() | has_changes() returns False | High | PASS |
| TC-002 | Clear_changes method works | 1. Create accessor 2. Set field 3. Call clear_changes() 4. Check has_changes() | has_changes() returns False | High | PASS |
| TC-003 | Snapshot updated after commit | 1. Track task 2. Modify custom_fields 3. Commit 4. Check _has_direct_custom_field_changes() | Returns False | High | PASS |
| TC-004 | _update_custom_fields_snapshot method | 1. Modify task.custom_fields directly 2. Call _update_snapshot() 3. Check detection | No changes detected after update | Medium | PASS |
| TC-005 | custom_fields_editor() returns accessor | 1. Create task 2. Call custom_fields_editor() | Returns CustomFieldAccessor instance | High | PASS |
| TC-006 | custom_fields_editor() caches instance | 1. Call custom_fields_editor() twice | Same instance returned | Medium | PASS |
| TC-007 | get_custom_fields() emits deprecation | 1. Call get_custom_fields() with warnings captured | DeprecationWarning emitted | High | PASS |
| TC-008 | Deprecation warning message correct | 1. Capture warning text | Contains "custom_fields_editor()" | Medium | PASS |
| TC-009 | No duplicate API on second commit | 1. Track task 2. Set via accessor 3. Commit 4. Commit again | Second commit has 0 CRUD operations | High | PASS |
| TC-010 | Preview shows no ops after reset | 1. After commit 2. Call preview() | Returns empty CRUD ops | High | PASS |
| TC-011 | Failed commit preserves accessor changes | 1. Set field 2. Commit (fails) 3. Check has_changes() | has_changes() returns True | High | PASS |
| TC-012 | Partial failure only resets succeeded | 1. Modify 2 tasks 2. One succeeds, one fails 3. Check both | Only succeeded task is clean | High | PASS |
| TC-013 | Business layer setters work | 1. Use business entity (Contact) 2. Set property 3. Commit | Changes committed correctly | High | PASS |
| TC-014 | Business layer deprecation warnings expected | 1. Use business entity property setter | Deprecation warning emitted | Medium | PASS |

### Edge Cases

| TC ID | Description | Input | Expected Result | Status |
|-------|-------------|-------|-----------------|--------|
| EDGE-001 | Accessor is None | Task with no accessor created | reset_custom_field_tracking() succeeds | PASS |
| EDGE-002 | Empty modifications | Accessor created, no set() calls | Reset succeeds, has_changes() = False | PASS |
| EDGE-003 | None custom_fields | Task(custom_fields=None) | Accessor can be created, reset succeeds | PASS |
| EDGE-004 | Re-track after reset | Reset then set new value | has_changes() returns True | PASS |
| EDGE-005 | Reset is idempotent | Call reset multiple times | No error, consistent state | PASS |
| EDGE-006 | Non-Task entity | Project tracked in session | No error on commit (duck typing) | PASS |

### Error Cases

| TC ID | Description | Failure Condition | Expected Handling | Status |
|-------|-------------|-------------------|-------------------|--------|
| ERR-001 | Commit fails entirely | API returns 400 | Accessor retains changes | PASS |
| ERR-002 | Partial batch failure | One task fails | Only successful task reset | PASS |
| ERR-003 | Entity without reset method | Entity lacks reset_custom_field_tracking | Graceful skip via hasattr | PASS |

### Integration Tests

| TC ID | Description | Status |
|-------|-------------|--------|
| INT-001 | SaveSession commit flow (end-to-end) | PASS |
| INT-002 | Cross-session entity reuse | PASS |
| INT-003 | Business layer integration | PASS (deprecation warnings expected) |

## Defect Report

### DEF-001: Incorrect Order of mark_clean and _reset_custom_field_tracking

**Severity**: High
**Status**: RESOLVED
**Discovered**: During TC-009/TC-010 validation
**Fixed**: 2025-12-16

**Description**:
In `SaveSession.commit_async()`, the order of operations was incorrect:
1. `mark_clean(entity)` was called first - captured `model_dump()` which included accessor changes
2. `_reset_custom_field_tracking(entity)` was called second - cleared accessor changes

This caused the ChangeTracker snapshot to contain the API format `{'456': 'High'}` while the actual `model_dump()` after reset returned the list format `[{'gid': '456', ...}]`.

**Fix Applied**: Lines 585-587 in session.py now correctly order operations:
```python
# Per ADR-0074: Reset custom field tracking (Systems 2 & 3) FIRST
# This clears stale modifications before snapshot capture
self._reset_custom_field_tracking(entity)
# Then capture clean snapshot (mark_clean calls model_dump())
self._tracker.mark_clean(entity)
```

**Verification**: TC-009 and TC-010 now PASS.

## Regression Test Results

| Test Suite | Tests | Passed | Failed | Warnings |
|------------|-------|--------|--------|----------|
| test_custom_field_accessor.py | 83 | 83 | 0 | 0 |
| test_task_custom_fields.py | 49 | 49 | 0 | 0 |
| test_session.py | 115 | 115 | 0 | 4 (expected) |
| test_business.py | 40 | 40 | 0 | 14 (expected) |
| **TOTAL** | **286** | **286** | **0** | 18 (expected) |

**Note**: Deprecation warnings in tests using `get_custom_fields()` are expected per FR-004.

## Test Environment
- Python 3.11.7
- pytest 9.0.2
- macOS Darwin 25.1.0
- Dependencies: pydantic, httpx (mocked for unit tests)

## Risks & Gaps

### Coverage Gaps
1. **FR-005** (Direct mutation warning) - Not tested in this plan, deferred to future initiative
2. **FR-006** (No-op detection) - Not tested in this plan, deferred to future initiative
3. **Real API integration** - Unit tests use mocks; real API behavior not validated

### Known Risks
1. Business layer deprecation warnings may cause noise in logs (acceptable)

## Exit Criteria

| Criteria | Status |
|----------|--------|
| All acceptance criteria have passing tests | PASS |
| Edge cases covered | PASS |
| Error paths tested and correct | PASS |
| No Critical or High defects open | PASS (DEF-001 resolved) |
| Coverage gaps documented and accepted | PASS |
| Comfortable on-call when this deploys | YES |

## Approval Status

**APPROVED** - All functional requirements validated, all tests pass, DEF-001 resolved.

### Non-Blocking Issues
- Business layer deprecation warnings are expected and acceptable
- FR-005/FR-006 deferred to future work

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | QA/Adversary | Initial test plan with defect report |
| 1.1 | 2025-12-16 | QA/Adversary | Re-validated after DEF-001 fix, updated to APPROVED |
