# ADR-0011: Batch API Request Format Fix

**Status:** Accepted
**Date:** 2025-12-09
**Context:** Bug fix for 400 Bad Request error in batch API operations
**References:** TDD-0005 (Batch API for Bulk Operations)

## Problem

The batch API endpoint was returning HTTP 400 Bad Request errors when attempting to create tasks via `BatchClient.create_tasks_async()`. The error occurred in the `_execute_chunk()` method when making POST requests to the `/batch` endpoint.

### Error Manifestation

```python
# In examples/04_batch_create.py
results = await client.batch.create_tasks_async(tasks_data)
# => AsanaError: Bad Request (HTTP 400)
```

## Root Cause Analysis

The batch request body was missing the required outer `"data"` wrapper that Asana's Batch API expects.

**Incorrect format (before fix):**
```json
{
  "actions": [
    {
      "method": "POST",
      "relative_path": "/tasks",
      "data": {...}
    }
  ]
}
```

**Correct format (after fix):**
```json
{
  "data": {
    "actions": [
      {
        "method": "POST",
        "relative_path": "/tasks",
        "data": {...}
      }
    ]
  }
}
```

### Why This Happened

The HTTP client in `transport/http.py` automatically **unwraps** the `"data"` field from response bodies (line 212-213), but it does **not** automatically wrap request bodies. This asymmetry led to the assumption that request bodies also didn't need wrapping.

Asana's API convention:
- **Responses:** Always wrapped in `{"data": ...}`
- **Requests:** Also wrapped in `{"data": ...}` for batch operations

## Solution

Modified `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/batch/client.py` line 380:

```python
# Before:
response = await self._http.request(
    "POST",
    "/batch",
    json={"actions": actions},
)

# After:
response = await self._http.request(
    "POST",
    "/batch",
    json={"data": {"actions": actions}},
)
```

## Impact

### Files Modified

1. **`src/autom8_asana/batch/client.py`**
   - Line 380: Added `"data"` wrapper to batch request body
   - Updated comment to document the expected format

2. **`tests/unit/test_batch.py`**
   - Updated 5 test assertions to expect `json["data"]["actions"]` instead of `json["actions"]`
   - Tests affected:
     - `test_execute_async_builds_correct_request_body`
     - `test_create_tasks_async`
     - `test_create_tasks_async_with_opt_fields`
     - `test_update_tasks_async`
     - `test_delete_tasks_async`

3. **`tests/unit/test_batch_adversarial.py`**
   - Updated 2 test assertions to match new format:
     - `test_update_tasks_verifies_request_structure`
     - `test_delete_tasks_verifies_request_structure`

4. **`tests/integration/test_batch_api.py`** (new file)
   - Added integration tests to verify batch operations work with real API
   - Tests batch create, update, delete, and mixed operations

### Test Results

All 155 batch-related unit tests pass after the fix:

```bash
pytest tests/ -k batch -v
# Result: 155 passed, 772 deselected
```

## Verification

To verify the fix works:

```bash
# Set environment variables
export ASANA_PAT="your_token"
export ASANA_PROJECT_GID="your_project_gid"

# Run the example script
python examples/04_batch_create.py --project $ASANA_PROJECT_GID

# Run integration tests (requires live API access)
pytest tests/integration/test_batch_api.py -v
```

## Lessons Learned

1. **API conventions aren't always symmetric:** Response unwrapping doesn't imply request wrapping is unnecessary
2. **Test against real API early:** Integration tests would have caught this immediately
3. **Document API formats explicitly:** The batch endpoint's expected format should be documented in code comments

## Follow-up Actions

- [x] Fix batch request format
- [x] Update unit tests to match new format
- [x] Add integration tests for batch operations
- [ ] Consider adding request/response format validation in development mode
- [ ] Document Asana API format conventions in SDK documentation

## References

- [Asana Batch API Documentation](https://developers.asana.com/reference/batch-api)
- TDD-0005: Batch API for Bulk Operations
- ADR-0010: Sequential chunk execution for batch operations
