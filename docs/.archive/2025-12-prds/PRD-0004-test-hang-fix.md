# PRD-0004: Test Suite Hang Prevention

| Field | Value |
|-------|-------|
| **ID** | PRD-0004 |
| **Title** | Test Suite Hang Prevention |
| **Status** | Implemented |
| **Created** | 2025-12-09 |
| **Author** | Requirements Analyst |

---

## 1. Problem Statement

Five tests in the autom8_asana suite can hang indefinitely due to missing thread join timeouts and untracked fire-and-forget threads. When any thread blocks unexpectedly, the test suite waits forever instead of failing fast, requiring manual intervention and blocking CI pipelines.

---

## 2. Root Causes

| ID | File | Line | Issue Type | Description |
|----|------|------|------------|-------------|
| RC-1 | `tests/unit/test_tier1_adversarial.py` | 1335 | Missing timeout | 10 threads joined without timeout in `test_concurrent_projects_access` |
| RC-2 | `tests/unit/dataframes/test_resolver.py` | 392 | Missing timeout | 10 threads joined without timeout in `test_concurrent_index_building` |
| RC-3 | `tests/unit/dataframes/test_registry.py` | 348 | Missing timeout | 20 threads joined without timeout in `test_singleton_thread_safety` |
| RC-4 | `tests/unit/cache/test_concurrency.py` | 688-736 | Untracked threads | Up to 50 callback threads spawned but never joined in `test_no_deadlock_on_nested_locks` |
| RC-5 | `tests/unit/test_client.py` | 197 | asyncio anti-pattern | `asyncio.run()` inside sync test instead of `async def` pattern |

---

## 3. Scope

### 3.1 In Scope

- Adding timeouts to existing `thread.join()` calls
- Tracking and joining fire-and-forget threads
- Converting one asyncio anti-pattern to proper async test
- Verifying fixes via test runs

### 3.2 Out of Scope

- Refactoring test architecture or abstractions
- Adding new testing infrastructure
- Modifying production code
- Performance optimization of tests
- Adding new tests beyond what's needed for validation

---

## 4. Requirements

### 4.1 Thread Join Timeout Requirements

**FR-THREAD-001**: Add timeout to thread joins in `test_concurrent_projects_access`

| Attribute | Value |
|-----------|-------|
| File | `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_tier1_adversarial.py` |
| Line | 1335 |
| Root Cause | RC-1 |
| Priority | Must |

**Current pattern:**
```python
for t in threads:
    t.join()
```

**Required pattern:**
```python
for t in threads:
    t.join(timeout=10)
    if t.is_alive():
        raise AssertionError(f"Thread {t.name} did not complete within timeout")
```

---

**FR-THREAD-002**: Add timeout to thread joins in `test_concurrent_index_building`

| Attribute | Value |
|-----------|-------|
| File | `/Users/tomtenuta/Code/autom8_asana/tests/unit/dataframes/test_resolver.py` |
| Line | 392 |
| Root Cause | RC-2 |
| Priority | Must |

**Current pattern:**
```python
for t in threads:
    t.join()
```

**Required pattern:**
```python
for t in threads:
    t.join(timeout=10)
    if t.is_alive():
        raise AssertionError(f"Thread {t.name} did not complete within timeout")
```

---

**FR-THREAD-003**: Add timeout to thread joins in `test_singleton_thread_safety`

| Attribute | Value |
|-----------|-------|
| File | `/Users/tomtenuta/Code/autom8_asana/tests/unit/dataframes/test_registry.py` |
| Line | 348 |
| Root Cause | RC-3 |
| Priority | Must |

**Current pattern:**
```python
for t in threads:
    t.join()
```

**Required pattern:**
```python
for t in threads:
    t.join(timeout=10)
    if t.is_alive():
        raise AssertionError(f"Thread {t.name} did not complete within timeout")
```

---

### 4.2 Fire-and-Forget Thread Tracking

**FR-THREAD-004**: Track and join callback threads in `test_no_deadlock_on_nested_locks`

| Attribute | Value |
|-----------|-------|
| File | `/Users/tomtenuta/Code/autom8_asana/tests/unit/cache/test_concurrency.py` |
| Lines | 688-736 |
| Root Cause | RC-4 |
| Priority | Must |

**Current pattern (lines 703-713):**
```python
def triggering_callback(event: Any) -> None:
    def nested_op() -> None:
        try:
            cache.get_versioned("other_key", EntryType.TASK)
        except Exception as e:
            callback_errors.append(e)

    # Run in separate thread to avoid deadlock from re-entrant lock
    t = threading.Thread(target=nested_op)
    t.start()
    # Don't join - fire and forget to avoid blocking the callback
```

**Required pattern:**
```python
# At test function scope (after line 699):
spawned_threads: list[threading.Thread] = []
spawned_threads_lock = threading.Lock()

def triggering_callback(event: Any) -> None:
    def nested_op() -> None:
        try:
            cache.get_versioned("other_key", EntryType.TASK)
        except Exception as e:
            callback_errors.append(e)

    t = threading.Thread(target=nested_op)
    with spawned_threads_lock:
        spawned_threads.append(t)
    t.start()
    # Don't join here - still fire and forget within callback

# Replace time.sleep(0.1) at line 735 with:
for t in spawned_threads:
    t.join(timeout=5)
    if t.is_alive():
        raise AssertionError(f"Callback thread {t.name} did not complete within timeout")
```

---

### 4.3 Async Pattern Requirements

**FR-ASYNC-001**: Convert `asyncio.run()` to async test pattern

| Attribute | Value |
|-----------|-------|
| File | `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_client.py` |
| Lines | 186-197 |
| Root Cause | RC-5 |
| Priority | Should |

**Current pattern:**
```python
def test_sync_context_manager_raises_configuration_error(self) -> None:
    """Sync context manager raises ConfigurationError."""

    async def run_test() -> None:
        client = AsanaClient(token="test-token")
        with pytest.raises(ConfigurationError) as exc_info:
            with client:
                pass

        assert "async context" in str(exc_info.value).lower()
        assert "async with" in str(exc_info.value).lower()

    asyncio.run(run_test())
```

**Required pattern:**
```python
async def test_sync_context_manager_raises_configuration_error(self) -> None:
    """Sync context manager raises ConfigurationError."""
    client = AsanaClient(token="test-token")
    with pytest.raises(ConfigurationError) as exc_info:
        with client:
            pass

    assert "async context" in str(exc_info.value).lower()
    assert "async with" in str(exc_info.value).lower()
```

---

## 5. Acceptance Criteria

### 5.1 Per-Requirement Verification

| Requirement | Verification Method |
|-------------|---------------------|
| FR-THREAD-001 | Run `pytest tests/unit/test_tier1_adversarial.py::TestCacheBehavior::test_concurrent_projects_access -v` passes without hang |
| FR-THREAD-002 | Run `pytest tests/unit/dataframes/test_resolver.py::TestDefaultCustomFieldResolver::test_concurrent_index_building -v` passes without hang |
| FR-THREAD-003 | Run `pytest tests/unit/dataframes/test_registry.py::TestSchemaRegistry::test_singleton_thread_safety -v` passes without hang |
| FR-THREAD-004 | Run `pytest tests/unit/cache/test_concurrency.py::TestDeadlockPrevention::test_no_deadlock_on_nested_locks -v` passes without hang |
| FR-ASYNC-001 | Run `pytest tests/unit/test_client.py::TestContextManagers::test_sync_context_manager_raises_configuration_error -v` passes |

### 5.2 Overall Success Criteria

1. **Full suite passes**: `make test` completes without hangs
2. **Stability validation**: 10 consecutive full test runs complete successfully
3. **No regressions**: All ~1850 tests continue to pass
4. **Timeout behavior**: If a thread blocks, test fails with clear error within 10 seconds (not hang)

---

## 6. Fix Order

Execute fixes in this sequence to minimize risk:

| Order | Requirement | Rationale |
|-------|-------------|-----------|
| 1 | FR-THREAD-001 | Simple pattern, establishes the timeout fix approach |
| 2 | FR-THREAD-002 | Same pattern as #1 |
| 3 | FR-THREAD-003 | Same pattern as #1 |
| 4 | FR-THREAD-004 | More complex (thread tracking), builds on #1-3 confidence |
| 5 | FR-ASYNC-001 | Different pattern, lower priority (Should vs Must) |

---

## 7. Assumptions

| ID | Assumption | Basis |
|----|------------|-------|
| A-1 | 10-second timeout is sufficient for all thread operations | Existing tests with timeouts use 10s; operations are fast in-memory cache ops |
| A-2 | pytest-asyncio `asyncio_mode = "auto"` handles async test conversion | Verified in pyproject.toml |
| A-3 | Thread tracking list access needs synchronization | Callbacks fire from ThreadPoolExecutor threads concurrently |
| A-4 | CacheMetrics recursion guard is intact and not a hang risk | Verified thread-local `_emitting` flag exists in metrics.py |

---

## 8. Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| pytest-asyncio configured | Project | Verified (`asyncio_mode = "auto"`) |
| pytest-timeout configured | Project | Verified (60s global timeout) |
| No external services needed | N/A | Tests use in-memory mocks |

---

## 9. Open Questions

None. All clarifications gathered during requirements analysis.

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-12-09 | Requirements Analyst | Initial draft |
