---
type: scan
target: autom8y-asana
focus: test-coverage-and-performance
scan_date: "2026-04-12"
scanner: signal-sifter
signal_count: 18
categories:
  test-gap: 9
  mock-quality: 3
  performance-risk: 5
  test-infrastructure: 2
  coverage-architecture: 1
status: draft
---

# SCAN: autom8y-asana — Test Coverage & Performance

## Scope

- **Target**: Full repository, `src/autom8_asana/` and `tests/`
- **Complexity**: FULL
- **Focus lens**: test-coverage-and-performance
- **Scan date**: 2026-04-12

## Overview

| Metric | Value |
|--------|-------|
| Source files scanned | 425 |
| Test files | 502 |
| Test-to-source ratio | 1.14 |
| Test functions | 12,393 |
| Total assertions | 23,860 |
| Assertions per test | 1.93 |
| Source files with zero direct tests | ~83 |
| Unspec'd MagicMock() | 2,360 |
| Unspec'd AsyncMock() | 630 |
| Spec'd MagicMock(spec=) | 66 (2.7%) |
| Benchmark tests in CI | 0 (excluded) |
| Benchmark baselines stored | 0 |

---

## Raw Signals

### SCAN-TC-001: Four packages have zero dedicated test directories

- **Category**: test-gap
- **Location**: `observability/` (3 files), `protocols/` (8 files, 926 lines), `_defaults/` (4 files), `batch/` (2 files: client.py 434 lines, models.py 234 lines)
- **Evidence**: Zero test files for all four packages. `batch/client.py` is a write-path multiplexer with 9 async public methods.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-TC-002: models/business — four stub models have no test file

- **Category**: test-gap
- **Location**: `dna.py` (71 lines), `mixins.py` (315 lines), `videography.py` (56 lines), `reconciliation.py` (56 lines)
- **Evidence**: `mixins.py` at 315 lines covers 5 mixin classes with traversal logic affecting business entity graphs. Zero direct tests.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-TC-003: services/ — intake service modules have no dedicated test files

- **Category**: test-gap
- **Location**: `intake_create_service.py` (732 lines), `intake_custom_field_service.py` (229 lines), `intake_resolve_service.py` (365 lines), `entity_context.py`
- **Evidence**: `intake_create_service.py` at 732 lines is the primary write-path entry point. Tested only through route-level tests.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-TC-004: api/routes/workspaces.py has no test file

- **Category**: test-gap
- **Location**: `src/autom8_asana/api/routes/workspaces.py` (131 lines, 2 route handlers)
- **Evidence**: Zero test results for `*workspaces*` in tests directory.
- **Confidence**: HIGH
- **Severity hint**: MEDIUM

### SCAN-TC-005: api/rate_limit.py has no dedicated test file

- **Category**: test-gap
- **Location**: `src/autom8_asana/api/rate_limit.py` (83 lines)
- **Evidence**: Rate limit key derivation, header injection, 429 behavior all untested at API layer.
- **Confidence**: HIGH
- **Severity hint**: MEDIUM

### SCAN-TC-006: Integration test gap — auth, transport, search, reconciliation

- **Category**: test-gap
- **Location**: `tests/integration/` (31 files, covers entity/cache/hydration only)
- **Evidence**: No integration tests for JWT/PAT flows against full middleware stack. No integration tests for transport, search (758 lines), or reconciliation E2E.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-TC-007: tests/integration/test_workspace_switching.py — 8 tests permanently skipped

- **Category**: test-gap
- **Location**: Lines 39, 52, 64, 76, 98, 110, 131, 144
- **Evidence**: All 8 tests carry `@pytest.mark.skip`. Reasons reference unimplemented workspace affinity and shared singleton registry.
- **Confidence**: HIGH
- **Severity hint**: HIGH (shared singleton across workspace clients is a correctness risk)

### SCAN-TC-008: Benchmarks are standalone scripts, not regression-enforcing tests

- **Category**: test-gap
- **Location**: `tests/benchmarks/bench_cache_operations.py`, `bench_batch_operations.py`
- **Evidence**: Both are `__main__` scripts with no `test_` functions. CI excludes all benchmark-marked tests. No `.benchmarks/` baseline storage. `test_insights_benchmark.py` is pytest-structured but also excluded from CI.
- **Confidence**: HIGH
- **Severity hint**: HIGH (no CI gate for performance regressions; SCAR-015 recurrence invisible)

### SCAN-TC-009: SCAR-004, SCAR-008, SCAR-013 have no regression test markers

- **Category**: test-gap
- **Location**: `tests/` (entire directory)
- **Evidence**: `grep -r "SCAR-004\|SCAR-008\|SCAR-013" tests/` returns zero. Future refactoring cannot detect scar reintroduction.
- **Confidence**: HIGH
- **Severity hint**: MEDIUM

---

### SCAN-MQ-001: 2,360 unspec'd MagicMock() vs 66 spec'd (2.7% spec rate)

- **Category**: mock-quality
- **Location**: Codebase-wide; highest in `tests/unit/cache/`, `tests/unit/clients/`, `tests/unit/transport/`
- **Evidence**: Combined 2,990 unspec'd mock sites (2,360 MagicMock + 630 AsyncMock). Per SCAR-026: unspec'd mocks silently accept non-existent method calls.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-MQ-002: MockClientBuilder root fixture uses unspec'd MagicMock

- **Category**: mock-quality
- **Location**: `tests/conftest.py:137`
- **Evidence**: `self._client = MagicMock()` — all 485 test files inherit an unspec'd root mock. Single highest-leverage fix for SCAR-026 class of issues.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-MQ-003: xfail in test_cascading_resolver.py marks stale API surface

- **Category**: mock-quality
- **Location**: `tests/unit/dataframes/test_cascading_resolver.py:503`
- **Evidence**: `@pytest.mark.xfail(reason="clear_cache method removed")` — test for removed method still counted in suite.
- **Confidence**: HIGH
- **Severity hint**: MEDIUM

---

### SCAN-PERF-001: section_timeline_service.py calls model_dump() twice per task in hot loop

- **Category**: performance-risk
- **Location**: `src/autom8_asana/services/section_timeline_service.py:560-561`
- **Evidence**: Two `task.model_dump()` calls per iteration over 3,800+ offers = 7,600 calls instead of 3,800. Pydantic v2 model_dump() is O(n fields), Task has 20+ fields. Contributes to SCAR-015 504 timeout.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-PERF-002: No scale-boundary test for SCAR-015 timeline 504 cliff

- **Category**: performance-risk
- **Location**: `tests/unit/services/test_section_timeline_service.py` (730 lines, 38 tests)
- **Evidence**: No test references 3,800 offer threshold. Cold path claims "< 5 seconds" with no CI enforcement.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-PERF-003: InMemoryCacheProvider eviction is FIFO, not LRU as documented

- **Category**: performance-risk
- **Location**: `src/autom8_asana/cache/backends/memory.py:105-124`
- **Evidence**: `list(self._simple_cache.keys())[:n]` is insertion-order FIFO. Docstring claims "LRU eviction." O(n) list construction per write at capacity (default 10,000).
- **Confidence**: HIGH
- **Severity hint**: MEDIUM

### SCAN-PERF-004: sync time.sleep() in RetryOrchestrator (sync path)

- **Category**: performance-risk
- **Location**: `src/autom8_asana/core/retry.py:724`
- **Evidence**: `time.sleep(delay)` blocks event loop if called from async context. Async counterpart uses `asyncio.sleep` correctly. Lambda handlers use sync path via `asyncio.run()`.
- **Confidence**: MEDIUM
- **Severity hint**: MEDIUM

### SCAN-PERF-005: DataServiceClient max_connections=10 undersized for batch workloads

- **Category**: performance-risk
- **Location**: `src/autom8_asana/clients/data/config.py:88`
- **Evidence**: 10 connections for 50+ PVP batch operations. Pool exhaustion adds queue time invisible to mock-based benchmarks.
- **Confidence**: MEDIUM
- **Severity hint**: MEDIUM

---

### SCAN-TI-001: --dist=loadfile workaround masks shared-state isolation failure

- **Category**: test-infrastructure
- **Location**: `pyproject.toml` lines 100-110
- **Evidence**: Comment documents worker crashes at 31.23% coverage with `--dist=load`. Root cause: `SystemContext` singletons and hypothesis DB state shared across workers. The band-aid prevents parallel isolation but doesn't fix the root cause.
- **Confidence**: HIGH
- **Severity hint**: HIGH

### SCAN-TI-002: test_computation_spans.py T9 batch span test permanently skipped

- **Category**: test-infrastructure
- **Location**: `tests/test_computation_spans.py:706`
- **Evidence**: `@pytest.mark.skip(reason="not yet instrumented")` — observability gap tracked as dead test.
- **Confidence**: HIGH
- **Severity hint**: LOW

---

### SCAN-CA-001: 80% threshold is codebase-wide average, not per-package minimum

- **Category**: coverage-architecture
- **Location**: `pyproject.toml` coverage config
- **Evidence**: Four zero-tested packages (~83 files with no direct tests) hidden beneath high-coverage packages. No per-module floor.
- **Confidence**: HIGH
- **Severity hint**: MEDIUM

---

## Corrections to Known-Issues

1. **lifecycle/loop_detector.py**: IS tested via `test_webhook_dispatcher.py` (class TestLoopDetector, lines 250-283) and `test_lifecycle_observation_contracts.py` (classes TestLO15, TestLO16, lines 548-592).
2. **lifecycle/observation_store.py**: IS tested via `test_lifecycle_observation_contracts.py` (StageTransitionStore across LO-05 through LO-19, lines 240-782).
