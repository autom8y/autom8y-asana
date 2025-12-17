# Test Plan: Batch API Adversarial Testing

## Metadata
- **TP ID**: TP-batch-api-adversarial
- **Status**: Completed
- **Author**: QA Adversary
- **Created**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-030 through FR-SDK-034)
- **TDD Reference**: [TDD-0005](../design/TDD-0005-batch-api.md)

## Test Scope

### In Scope

**Phase 3 Batch API Components Under Test**:
- `BatchRequest` model (`src/autom8_asana/batch/models.py`)
- `BatchResult` model (`src/autom8_asana/batch/models.py`)
- `BatchSummary` model (`src/autom8_asana/batch/models.py`)
- `BatchClient` (`src/autom8_asana/batch/client.py`)
- Auto-chunking logic (`_chunk_requests`, `_count_chunks`)
- Convenience methods (`create_tasks`, `update_tasks`, `delete_tasks`)

### Out of Scope

- Integration tests with real Asana API
- Performance/load testing
- Concurrent batch execution (deferred per ADR-0010)

---

## Test Summary

| Category | Tests | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Auto-Chunking Edge Cases | 12 | 12 | 0 | 100% |
| Partial Failure Scenarios | 7 | 7 | 0 | 100% |
| BatchRequest Validation | 12 | 12 | 0 | 100% |
| BatchResult Properties | 26 | 26 | 0 | 100% |
| BatchSummary Statistics | 10 | 10 | 0 | 100% |
| Convenience Methods | 10 | 10 | 0 | 100% |
| Request Index Correlation | 3 | 3 | 0 | 100% |
| Response Parsing | 5 | 5 | 0 | 100% |
| Other Edge Cases | 9 | 9 | 0 | 100% |
| **TOTAL** | **94** | **94** | **0** | **100%** |

---

## Bugs Found

### BUG-001: Non-list errors field causes AttributeError

**Severity**: Low

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/batch/models.py`

**Line**: 140

**Description**: When `body["errors"]` is a string instead of a list (e.g., `{"errors": "Something went wrong"}`), the `error` property iterates over the string characters and calls `.get()` on each character, causing `AttributeError: 'str' object has no attribute 'get'`.

**Root Cause**: The code assumes `errors` is always a list:
```python
errors = self.body.get("errors", [])
messages = [e.get("message", "Unknown error") for e in errors]
```

**Impact**: Low - Asana API always returns errors as a list, so this only affects malformed/unexpected responses.

**Recommended Fix**:
```python
errors_data = self.body.get("errors", [])
if isinstance(errors_data, list):
    errors = errors_data
    messages = [e.get("message", "Unknown error") for e in errors if isinstance(e, dict)]
else:
    errors = []
    messages = []
```

**Test Reference**: `test_error_with_non_list_errors` in `tests/unit/test_batch_adversarial.py`

---

### OBSERVATION-001: Empty body returns None for data property

**Severity**: Not a bug (design decision)

**Description**: When `body` is an empty dict `{}`, the `data` property returns `None` instead of `{}`. This is because `not {}` evaluates to `True` in Python, causing early return.

**Line**: 159 in `models.py`:
```python
if not self.success or not self.body:
    return None
```

**Impact**: None - This is arguably correct behavior since an empty response body has no meaningful data.

**Test Reference**: `test_empty_body` in `tests/unit/test_batch_adversarial.py`

---

## Requirements Traceability

### Batch API Requirements

| Requirement ID | Description | Test Cases | Status |
|----------------|-------------|------------|--------|
| FR-SDK-030 | Support Asana Batch API for bulk operations | TestBatchClientExecuteAsync, TestAutoChunkingEdgeCases | Verified |
| FR-SDK-031 | Automatically chunk batch requests to Asana limits | test_chunk_* tests, test_execute_hundred_* tests | Verified |
| FR-SDK-032 | Support batch create operations | test_create_tasks_* tests | Verified |
| FR-SDK-033 | Support batch update operations | test_update_tasks_* tests | Verified |
| FR-SDK-034 | Handle partial batch failures gracefully | TestPartialFailureScenarios | Verified |

---

## Test Coverage by Edge Case Category

### 1. Auto-Chunking Edge Cases

| Test | Boundary | Expected Behavior | Result |
|------|----------|-------------------|--------|
| test_chunk_zero_requests | 0 requests | Empty list of chunks | PASS |
| test_chunk_one_request | 1 request | Single chunk with 1 item | PASS |
| test_chunk_nine_requests | 9 requests (just under limit) | Single chunk | PASS |
| test_chunk_ten_requests | 10 requests (at limit) | Single chunk | PASS |
| test_chunk_eleven_requests | 11 requests (just over) | 2 chunks (10 + 1) | PASS |
| test_chunk_hundred_requests | 100 requests (10x limit) | 10 chunks | PASS |
| test_chunk_hundred_one_requests | 101 requests | 11 chunks (10x10 + 1) | PASS |

### 2. Partial Failure Scenarios

| Test | Pattern | Expected Behavior | Result |
|------|---------|-------------------|--------|
| test_all_succeed | All 200s | All results successful | PASS |
| test_all_fail | All 4xx/5xx | All results failed with errors | PASS |
| test_first_fails_rest_succeed | [400, 200, 200, 200, 200] | First fails, rest succeed | PASS |
| test_last_fails_rest_succeed | [200, 200, 200, 200, 500] | Last fails, rest succeed | PASS |
| test_alternating_success_failure | [200, 404, 200, 404, ...] | Alternating pattern preserved | PASS |
| test_middle_chunk_has_failures | Failures in chunk 2 only | Other chunks unaffected | PASS |
| test_chunk_endpoint_failure_raises_exception | Batch endpoint 503 | Raises AsanaError (not BatchResult) | PASS |

### 3. BatchRequest Validation

| Test | Input | Expected Behavior | Result |
|------|-------|-------------------|--------|
| test_empty_path_rejected | "" | ValueError | PASS |
| test_path_with_only_slash | "/" | Accepted | PASS |
| test_very_long_path | 1000+ chars | Accepted | PASS |
| test_path_with_special_characters | Various special chars | Accepted | PASS |
| test_method_variations_invalid | PATCH, OPTIONS, HEAD, etc. | ValueError | PASS |
| test_all_valid_methods_* | GET, POST, PUT, DELETE | Accepted (case-insensitive) | PASS |
| test_large_data_payload | 50KB+ data | Accepted | PASS |
| test_empty_data_dict | {} | Included in action | PASS |
| test_nested_data_structure | 4+ levels deep | Preserved | PASS |

### 4. BatchResult Properties

| Test | Status Code | Expected | Result |
|------|-------------|----------|--------|
| test_status_199_is_failure | 199 | Failure | PASS |
| test_status_200_is_success | 200 | Success | PASS |
| test_status_299_is_success | 299 | Success | PASS |
| test_status_300_is_failure | 300 | Failure | PASS |
| test_status_4xx_is_failure | 400, 401, 403, 404, 429 | Failure | PASS |
| test_status_5xx_is_failure | 500, 502, 503 | Failure | PASS |
| test_missing_body_* | None body | Handled gracefully | PASS |
| test_error_* | Various error formats | Extracted correctly | PASS |
| test_data_* | Various body formats | Unwrapped correctly | PASS |

### 5. BatchSummary Statistics

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| test_empty_results | [] | total=0, all_succeeded=True | PASS |
| test_large_all_success | 100 successes | succeeded=100, failed=0 | PASS |
| test_large_all_failure | 100 failures | succeeded=0, failed=100 | PASS |
| test_large_mixed_results | 75% success | succeeded + failed = total | PASS |
| test_*_preserves_order | Various | Original order preserved | PASS |

### 6. Convenience Methods

| Test | Method | Input | Result |
|------|--------|-------|--------|
| test_create_tasks_empty_list | create_tasks_async | [] | Empty, no HTTP call | PASS |
| test_update_tasks_empty_list | update_tasks_async | [] | Empty, no HTTP call | PASS |
| test_delete_tasks_empty_list | delete_tasks_async | [] | Empty, no HTTP call | PASS |
| test_*_large_batch | All methods | 100+ items | Chunked correctly | PASS |
| test_*_verifies_request_structure | update/delete | Various | Correct action format | PASS |

---

## Test File Location

All adversarial tests are located at:
```
/Users/tomtenuta/Code/autom8_asana/tests/unit/test_batch_adversarial.py
```

**Test Count**: 94 tests
**Run Command**: `python -m pytest tests/unit/test_batch_adversarial.py -v`

---

## Approval Status

### Approval Criteria Check

- [x] All acceptance criteria from PRD have passing tests
- [x] Edge cases are covered (0, 1, 9, 10, 11, 100, 101 boundary conditions)
- [x] Error paths are tested and behave correctly (partial failures, endpoint failures)
- [x] No high-severity defects remain open (BUG-001 is low severity)
- [x] Coverage gaps are documented (non-list errors handling)
- [x] Would be comfortable being on-call when this deploys

### Recommendation

**APPROVED FOR SHIP** with the following note:

BUG-001 (non-list errors handling) is low severity since Asana API always returns errors as a list. A future enhancement could add defensive type checking, but it is not blocking for release.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | QA Adversary | Initial adversarial test plan |
