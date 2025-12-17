# Test Plan: autom8_asana SDK Phase 1 Parity Validation

## Metadata
- **TP ID**: TP-0001
- **Status**: Draft
- **Author**: QA Adversary
- **Created**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md)
- **TDD Reference**: [TDD-0001](../design/TDD-0001-sdk-architecture.md)

## Test Scope

### In Scope

**Phase 1 SDK Components Under Test**:
- HTTP Client (`src/autom8_asana/transport/http.py`)
- TasksClient (`src/autom8_asana/clients/tasks.py`)
- Rate Limiter (`src/autom8_asana/transport/rate_limiter.py`)
- Retry Handler (`src/autom8_asana/transport/retry.py`)
- Sync Wrapper (`src/autom8_asana/transport/sync.py`)
- Exceptions (`src/autom8_asana/exceptions.py`)

**Operations Under Test**:
| Legacy Operation | Location | SDK Equivalent | Phase |
|-----------------|----------|----------------|-------|
| `Task.get_task()` | `objects/task/main/main.py:211` | `TasksClient.get()` | Phase 1 |
| `Task.put_data()` | `objects/task/main/main.py:249` | `TasksClient.update()` | Phase 1 |
| `Task.create_task()` | `objects/task/main/main.py:404` | `TasksClient.create()` | Phase 1 |
| `Task.delete_task()` | `objects/task/main/main.py:422` | `TasksClient.delete()` | Phase 1 |

### Out of Scope

- `Task.duplicate_task()` - Phase 2
- `Task.get_tasks()` - Phase 2
- `BatchAPI.get_tasks()` - Phase 2
- Other resource clients (Projects, Sections, etc.) - Phase 2+
- S3CacheProvider implementation - Phase 2
- Full autom8 integration testing - Phase 2+

---

## Requirements Traceability

### Transport Layer Requirements

| Requirement ID | Description | Test Cases | Coverage Status |
|----------------|-------------|------------|-----------------|
| FR-SDK-001 | Connection pooling for HTTP requests | TC-HTTP-001, TC-HTTP-002 | Planned |
| FR-SDK-002 | httpx async-first design | TC-HTTP-003, TC-HTTP-004 | Planned |
| FR-SDK-003 | Sync wrappers for all async operations | TC-SYNC-001 through TC-SYNC-005 | Partial (9 unit tests exist) |
| FR-SDK-005 | Configurable timeouts | TC-HTTP-005, TC-HTTP-006 | Planned |
| FR-SDK-006 | Token-bucket rate limiting at 1500 req/min | TC-RATE-001 through TC-RATE-005 | Partial (10 unit tests exist) |
| FR-SDK-007 | Automatic retry on HTTP 429 | TC-RETRY-001, TC-RETRY-002 | Partial (13 unit tests exist) |
| FR-SDK-008 | Automatic retry on HTTP 503 | TC-RETRY-003 | Partial |
| FR-SDK-009 | Automatic retry on HTTP 504 | TC-RETRY-004 | Partial |
| FR-SDK-010 | Exponential backoff with jitter | TC-RETRY-005, TC-RETRY-006 | Partial |
| FR-SDK-011 | Respect Retry-After headers | TC-RETRY-007 | Planned |
| FR-SDK-013 | Limit concurrent read operations to 50 | TC-CONC-001 | Planned |
| FR-SDK-014 | Limit concurrent write operations to 15 | TC-CONC-002 | Planned |

### Client Layer Requirements

| Requirement ID | Description | Test Cases | Coverage Status |
|----------------|-------------|------------|-----------------|
| FR-SDK-016 | TasksClient CRUD operations | TC-TASK-001 through TC-TASK-020 | Planned |
| FR-SDK-041 | AsanaError base exception | TC-ERR-001 | Covered (16 unit tests exist) |
| FR-SDK-042 | Specific exceptions (RateLimitError, etc.) | TC-ERR-002 through TC-ERR-006 | Covered |
| FR-SDK-043 | Preserve original Asana API error details | TC-ERR-007, TC-ERR-008 | Planned |

### Boundary Protocol Requirements

| Requirement ID | Description | Test Cases | Coverage Status |
|----------------|-------------|------------|-----------------|
| FR-BOUNDARY-001 | AuthProvider.get_secret() | TC-AUTH-001, TC-AUTH-002 | Planned |
| FR-BOUNDARY-006 | Default no-op AuthProvider | TC-AUTH-003 | Planned |
| FR-BOUNDARY-007 | Default no-op CacheProvider | TC-CACHE-001 | Planned |

---

## Test Strategy

### Unit Tests

Unit tests validate individual components in isolation using mocks and fakes.

**Test Files to Create**:
- `tests/unit/test_http_client.py` - HTTP client unit tests
- `tests/unit/test_tasks_client.py` - TasksClient unit tests

**Existing Coverage** (48 tests passing):
| Component | Test File | Tests | Status |
|-----------|-----------|-------|--------|
| Exceptions | `tests/unit/test_exceptions.py` | 16 | Complete |
| Rate Limiter | `tests/unit/test_rate_limiter.py` | 10 | Unit only |
| Retry Handler | `tests/unit/test_retry.py` | 13 | Unit only |
| Sync Wrapper | `tests/unit/test_sync.py` | 9 | Unit only |
| HTTP Client | - | **0** | **CRITICAL GAP** |
| TasksClient | - | **0** | **GAP** |

### Integration Tests

Integration tests validate component interactions and end-to-end flows using httpx mock server.

**Test Files to Create**:
- `tests/integration/test_crud_lifecycle.py` - End-to-end CRUD tests
- `tests/integration/test_rate_limit_load.py` - Rate limiting under load

### Parity Tests

Parity tests compare SDK behavior against legacy implementation using record-replay pattern.

**Test Files to Create**:
- `tests/parity/test_legacy_comparison.py` - Record-replay parity tests

**Comparison Strategy**:
```python
# Record-Replay Pattern
def record_legacy_response(operation, inputs):
    """Record: request details, response, timing, cache ops, retries"""

def replay_against_sdk(recorded_request, recorded_response):
    """Compare: response data, error types, retry behavior"""
```

**Diff Criteria**:
- Response data structure must match
- Error types must map correctly
- Timing within acceptable bounds (SDK may be faster)

---

## Test Scenarios

### HTTP Client Tests

**File**: `tests/unit/test_http_client.py`

#### Request Lifecycle

| TC ID | Scenario | Input | Expected Result | Priority |
|-------|----------|-------|-----------------|----------|
| TC-HTTP-001 | Successful GET request | Valid task GID | Returns parsed JSON with `data` unwrapped | High |
| TC-HTTP-002 | Successful POST request | Task creation payload | Returns created task JSON | High |
| TC-HTTP-003 | Request uses async by default | Async context | Uses `httpx.AsyncClient` | High |
| TC-HTTP-004 | Connection pool reuse | Multiple sequential requests | Same connection reused | Medium |
| TC-HTTP-005 | Connect timeout triggers error | Timeout=0.001s | `TimeoutError` raised | High |
| TC-HTTP-006 | Read timeout triggers retry | Timeout during response | Retry attempted | High |

#### Error Handling

| TC ID | Scenario | HTTP Status | Expected Behavior | Priority |
|-------|----------|-------------|-------------------|----------|
| TC-HTTP-007 | 400 Bad Request | 400 | `ValidationError` raised | High |
| TC-HTTP-008 | 401 Unauthorized | 401 | `AuthenticationError` raised | High |
| TC-HTTP-009 | 403 Forbidden | 403 | `ForbiddenError` raised | High |
| TC-HTTP-010 | 404 Not Found | 404 | `NotFoundError` raised | High |
| TC-HTTP-011 | 410 Gone | 410 | `GoneError` raised | High |
| TC-HTTP-012 | 429 Too Many Requests | 429 | `RateLimitError` raised after max retries | High |
| TC-HTTP-013 | 500 Internal Server Error | 500 | `ServerError` raised | High |
| TC-HTTP-014 | 502 Bad Gateway | 502 | `ServerError` raised | Medium |
| TC-HTTP-015 | 503 Service Unavailable | 503 | Retry then `ServerError` | High |
| TC-HTTP-016 | 504 Gateway Timeout | 504 | Retry then `ServerError` | High |

#### Retry Behavior

| TC ID | Scenario | Condition | Expected Behavior | Priority |
|-------|----------|-----------|-------------------|----------|
| TC-HTTP-017 | Retry on 429 | First attempt returns 429 | Waits and retries | High |
| TC-HTTP-018 | Retry on 503 | First attempt returns 503 | Waits and retries | High |
| TC-HTTP-019 | Retry on 504 | First attempt returns 504 | Waits and retries | High |
| TC-HTTP-020 | Max retries exceeded | 3 consecutive 429s | Raises after 3rd retry | High |
| TC-HTTP-021 | Successful after retry | 429 then 200 | Returns success response | High |

#### Rate Limiting

| TC ID | Scenario | Condition | Expected Behavior | Priority |
|-------|----------|-----------|-------------------|----------|
| TC-HTTP-022 | Rate limiter acquired before request | Any request | `acquire()` called before HTTP | High |
| TC-HTTP-023 | Read semaphore used for GET | GET request | Read semaphore (50 limit) | High |
| TC-HTTP-024 | Write semaphore used for POST | POST request | Write semaphore (15 limit) | High |
| TC-HTTP-025 | Write semaphore used for PUT | PUT request | Write semaphore (15 limit) | High |
| TC-HTTP-026 | Write semaphore used for DELETE | DELETE request | Write semaphore (15 limit) | High |

---

### TasksClient Tests

**File**: `tests/unit/test_tasks_client.py`

#### get() / get_async()

| TC ID | Scenario | Input | Expected Behavior | Priority |
|-------|----------|-------|-------------------|----------|
| TC-TASK-001 | Standard fetch | Valid GID "12345" | Returns Task with `data` unwrapped | High |
| TC-TASK-002 | With opt_fields | `opt_fields=["name", "notes"]` | Returns only specified fields | High |
| TC-TASK-003 | Empty GID | `task_gid=""` | `ValidationError` raised | High |
| TC-TASK-004 | Non-numeric GID | `task_gid="abc"` | `ValidationError` or 404 | Medium |
| TC-TASK-005 | Task not found | Non-existent GID | `NotFoundError` raised | High |
| TC-TASK-006 | Task deleted (410) | Deleted task GID | `GoneError` raised | High |
| TC-TASK-007 | Rate limited | During 429 | Retry with backoff | High |
| TC-TASK-008 | Server error retry | During 5xx | Retry up to 3 times | High |

#### create() / create_async()

| TC ID | Scenario | Input | Expected Behavior | Priority |
|-------|----------|-------|-------------------|----------|
| TC-TASK-009 | Minimal task creation | `name="Test Task"` | Returns created Task | High |
| TC-TASK-010 | Full task creation | All fields populated | Returns Task with all fields | High |
| TC-TASK-011 | Task with custom fields | `custom_fields={"cf_123": "value"}` | Custom fields set correctly | Medium |
| TC-TASK-012 | Task with parent | `parent="parent_gid"` | Creates as subtask | Medium |
| TC-TASK-013 | Missing required field | No name | `ValidationError` raised | High |
| TC-TASK-014 | Invalid project GID | Non-existent project | 400 error from API | High |

#### update() / update_async()

| TC ID | Scenario | Input | Expected Behavior | Priority |
|-------|----------|-------|-------------------|----------|
| TC-TASK-015 | Update single field | `name="New Name"` | Returns updated Task | High |
| TC-TASK-016 | Update multiple fields | name, notes, due_on | All fields updated | High |
| TC-TASK-017 | Mark complete | `completed=True` | Task marked complete | High |
| TC-TASK-018 | Update non-existent task | Invalid GID | `NotFoundError` raised | High |
| TC-TASK-019 | Concurrent update conflict | Simultaneous updates | Last write wins (Asana behavior) | Medium |

#### delete() / delete_async()

| TC ID | Scenario | Input | Expected Behavior | Priority |
|-------|----------|-------|-------------------|----------|
| TC-TASK-020 | Successful delete | Valid GID | No error, task deleted | High |
| TC-TASK-021 | Delete non-existent | Invalid GID | `NotFoundError` raised | High |
| TC-TASK-022 | Delete already deleted | Previously deleted GID | `NotFoundError` or `GoneError` | Medium |

---

### Integration Tests

**File**: `tests/integration/test_crud_lifecycle.py`

| TC ID | Scenario | Steps | Expected Result | Priority |
|-------|----------|-------|-----------------|----------|
| INT-001 | Full CRUD lifecycle | Create -> Read -> Update -> Delete | All operations succeed in sequence | High |
| INT-002 | Create with project | Create task in specific project | Task appears in project | High |
| INT-003 | Update preserves fields | Update one field, read back | Other fields unchanged | High |
| INT-004 | Retry chain success | Simulate 429 -> 429 -> 200 | Returns success after retries | High |
| INT-005 | Sync/async mixed usage | Alternate sync and async calls | No deadlocks or errors | High |

**File**: `tests/integration/test_rate_limit_load.py`

| TC ID | Scenario | Load | Expected Behavior | Priority |
|-------|----------|------|-------------------|----------|
| INT-006 | Rate limit under load | 100 concurrent requests | Semaphores limit concurrency | High |
| INT-007 | Backpressure handling | Burst of 200 requests | Rate limiter throttles appropriately | Medium |
| INT-008 | Recovery after 429 | Hit rate limit, wait, retry | Successful recovery | High |

---

### Parity Tests

**File**: `tests/parity/test_legacy_comparison.py`

| TC ID | Scenario | Comparison | Acceptance Criteria | Priority |
|-------|----------|------------|---------------------|----------|
| PAR-001 | get_task response structure | Legacy vs SDK | Response data identical | High |
| PAR-002 | Error mapping | Legacy AsanaError vs SDK exceptions | Correct exception type | High |
| PAR-003 | Retry behavior | Legacy vs SDK retry count | Same number of retries | Medium |
| PAR-004 | Response timing | Legacy vs SDK latency | SDK within 2x of legacy | Medium |

---

## Edge Cases

| TC ID | Description | Input | Expected Result |
|-------|-------------|-------|-----------------|
| EDGE-001 | Empty task name | `name=""` | `ValidationError` or API error |
| EDGE-002 | Unicode in task name | `name="Task \u2603"` | Created successfully |
| EDGE-003 | Very long notes | 65536 character notes | Truncated or error |
| EDGE-004 | Null assignee | `assignee=None` | Unassigned task |
| EDGE-005 | Past due date | `due_on="2020-01-01"` | Created with past date |
| EDGE-006 | Invalid date format | `due_on="not-a-date"` | `ValidationError` |
| EDGE-007 | Zero timeout | `timeout=0` | Immediate timeout |
| EDGE-008 | Negative retry count | `max_retries=-1` | No retries attempted |

---

## Error Cases

| TC ID | Failure Condition | Expected Handling | Recovery Action |
|-------|-------------------|-------------------|-----------------|
| ERR-001 | Network disconnect | `httpx.ConnectError` wrapped | Retry with backoff |
| ERR-002 | DNS resolution failure | `httpx.ConnectError` wrapped | Raise after retries |
| ERR-003 | SSL certificate invalid | `httpx.ConnectError` wrapped | Fail fast, no retry |
| ERR-004 | Connection reset | `httpx.ReadError` wrapped | Retry |
| ERR-005 | Response body truncated | JSON parse error | Retry |
| ERR-006 | API returns HTML (error page) | JSON parse error | `ServerError` raised |
| ERR-007 | Auth token expired | 401 Unauthorized | `AuthenticationError` raised |
| ERR-008 | Insufficient permissions | 403 Forbidden | `ForbiddenError` raised |

---

## Performance Tests

| PERF ID | Scenario | Target | Measurement Method |
|---------|----------|--------|-------------------|
| PERF-001 | Cold import time | < 500ms | `time python -c "import autom8_asana"` |
| PERF-002 | Single request latency | < 200ms p95 (excluding API) | pytest-benchmark |
| PERF-003 | Connection pool warmup | < 100ms | Time first vs subsequent requests |
| PERF-004 | Rate limiter throughput | 1500 req/min sustained | Load test with mock server |
| PERF-005 | Memory under pagination | < 100MB for 10k tasks | Memory profiler |

---

## Security Tests

| SEC ID | Attack Vector | Test Method | Expected Defense |
|--------|---------------|-------------|------------------|
| SEC-001 | Token in logs | Grep logs for token pattern | Token masked or absent |
| SEC-002 | Token in error messages | Trigger error, check message | Token not exposed |
| SEC-003 | SSL downgrade | Force HTTP | Rejected or upgraded |
| SEC-004 | Invalid SSL cert | Use self-signed cert | Connection rejected |
| SEC-005 | Request injection | Special chars in task name | Properly escaped |

---

## Test Environment

### Requirements
- Python 3.10 or 3.11
- pytest >= 7.0
- pytest-asyncio >= 0.21
- pytest-cov >= 4.0
- httpx >= 0.24
- respx >= 0.20 (for HTTP mocking)

### Configuration
```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_http_client.py -v

# Run with coverage
pytest --cov=src/autom8_asana --cov-report=html

# Run only Phase 1 tests
pytest -m "phase1" -v
```

### Mock Server Setup
Integration tests use `respx` for HTTP mocking:
```python
import respx
from httpx import Response

@respx.mock
async def test_get_task():
    respx.get("https://app.asana.com/api/1.0/tasks/123").mock(
        return_value=Response(200, json={"data": {"gid": "123", "name": "Test"}})
    )
    # Test code...
```

---

## Risks & Gaps

### Critical Risks

| Risk ID | Description | Impact | Mitigation |
|---------|-------------|--------|------------|
| RISK-001 | HTTP Client has zero tests | Core request/response cycle unvalidated; every SDK operation fails if broken | Write comprehensive HTTP client tests BEFORE migration |
| RISK-002 | Batch operations not implemented | Legacy heavily uses `BatchAPI.get_tasks()`; bulk loading 10-100x slower | DO NOT migrate batch-dependent handlers until Phase 2 |
| RISK-003 | Cache provider not implemented | Every request hits Asana API; 429 rate limits under normal load | Implement S3CacheProvider before production |

### High Risks

| Risk ID | Description | Impact | Mitigation |
|---------|-------------|--------|------------|
| RISK-004 | Sync wrapper nesting | Complex call chains deadlock or fail | Lint rule + explicit testing |
| RISK-005 | HTML error field stripping | Updates with malformed HTML fail | Document or implement similar logic |
| RISK-006 | Retry-After handling differs | Legacy doubles Retry-After; SDK uses raw value | Validate behavior, document difference |

### Known Parity Gaps

| Gap | Legacy Behavior | SDK Behavior | Status |
|-----|-----------------|--------------|--------|
| Caching | S3 with TTL | NullCacheProvider | **GAP** - Phase 2 |
| Cache eviction on 404/410 | Implemented | Not implemented | **GAP** - Phase 2 |
| Retry-After multiplier | `retry_after * 2` | Raw value | **DIFFERENCE** - Intentional |
| HTML field stripping | Implemented | Not implemented | **GAP** - Decision needed |

### Coverage Gaps

| Component | Current Tests | Required Tests | Gap |
|-----------|---------------|----------------|-----|
| HTTP Client | 0 | 26 | **CRITICAL** |
| TasksClient | 0 | 22 | **HIGH** |
| Integration | 0 | 8 | **CRITICAL** |
| Parity | 0 | 4 | **HIGH** |

---

## Acceptance Criteria (Approval Gate)

Before approving Phase 1 migration:

- [ ] HTTP client > 80% test coverage
- [ ] All TasksClient methods have unit tests
- [ ] At least 5 integration tests pass
- [ ] Parity tests show < 1% response difference
- [ ] Monitoring and alerting in place
- [ ] Rollback procedure tested

---

## Rollback Procedures

### Feature Flags

```python
# Per-handler feature flag
if FEATURE_FLAGS.get("use_sdk_for_task_get"):
    from autom8_asana import AsanaClient
else:
    from apis.asana_api.objects.task.main import Task

# Global kill switch
USE_AUTOM8_ASANA_SDK = os.getenv("USE_AUTOM8_ASANA_SDK", "false") == "true"
```

### Kill Switch Activation

1. Set environment variable: `USE_AUTOM8_ASANA_SDK=false`
2. Restart affected services
3. Verify traffic routing to legacy implementation
4. Investigate root cause before re-enabling

### Rollback Triggers

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Error rate | > 1% for 5 minutes | Automatic rollback |
| p99 latency | > 2x baseline | Alert, manual review |
| Rate limit errors | Any spike | Alert, manual review |
| Data corruption | Any detected | Immediate rollback |

### Monitoring Requirements

| Metric | Alert Threshold | Severity |
|--------|-----------------|----------|
| Error rate | > 1% for 5 min | HIGH |
| Error rate | > 5% for 2 min | CRITICAL |
| p99 latency | > 3x baseline for 5 min | HIGH |
| Rate limit (429) | Any spike | WARNING |
| Cache hit rate | > 20% drop | WARNING |

---

## Exit Criteria

Testing is complete when:

1. **All acceptance criteria met** - Per approval gate checklist above
2. **No high/critical defects open** - All P0/P1 defects resolved or explicitly accepted
3. **Coverage targets achieved** - HTTP client >80%, overall >80%
4. **Parity validated** - <1% response difference from legacy
5. **Rollback tested** - Feature flag and kill switch verified working
6. **On-call ready** - Would be comfortable being paged at 2am with this deployment

---

## Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `tests/unit/test_http_client.py` | HTTP client unit tests | HIGH |
| `tests/unit/test_tasks_client.py` | TasksClient unit tests | HIGH |
| `tests/integration/test_crud_lifecycle.py` | End-to-end CRUD tests | HIGH |
| `tests/integration/test_rate_limit_load.py` | Rate limiting under load | MEDIUM |
| `tests/parity/test_legacy_comparison.py` | Record-replay parity tests | HIGH |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | QA Adversary | Initial test plan from parity validation session |
