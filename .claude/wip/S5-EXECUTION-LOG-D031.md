# Execution Log: D-031 Retry Callback Factory

**Date**: 2026-02-18
**Agent**: Janitor
**Task**: D-031 -- Extract retry callback factory to _retry.py
**Status**: Complete (no commit -- per instructions)

---

## Files Changed

| File | Change | LOC Before | LOC After | Delta |
|------|--------|-----------|-----------|-------|
| `src/autom8_asana/clients/data/_retry.py` | NEW | 0 | 193 | +193 |
| `src/autom8_asana/clients/data/client.py` | MODIFIED | 2,173 | 2,017 | -156 |

**Net LOC change**: +37 (193 new, 156 removed from client.py)
**Callback boilerplate removed from client.py**: 196 LOC (replaced by ~40 LOC of factory calls)

---

## Test Gates

| Gate | Command | Result | Count |
|------|---------|--------|-------|
| Unit gate | `pytest tests/unit/clients/data/ -x --timeout=120` | PASS | 386 passed, 1 skipped |
| Full suite | `pytest tests/ --tb=no -q --timeout=300` | PASS | 10,522 passed, 1 pre-existing failure |

Pre-existing failure: `tests/unit/core/test_concurrency.py::TestStructuredLogging::test_label_in_log` (out of scope, unchanged).

---

## Implementation Summary

### New File: `_retry.py`

Created `RetryCallbacks` frozen dataclass (with `slots=True`) and `build_retry_callbacks` factory function. Factory parameterizes all 7 variation axes:

1. **on_retry presence**: `log_event_retry=None` sets `on_retry=None`
2. **Error class**: `error_class` parameter (`InsightsServiceError` or `ExportError`)
3. **Error messages**: `timeout_message` and `http_error_template` (with `{e}` placeholder)
4. **Error kwargs**: `error_kwargs` dict (merged into error constructor, also into log extras for `request_id`)
5. **Metrics emission**: `emit_metric` callback + `metric_tags` dict
6. **Elapsed time**: `start_time` parameter (when present, computes `elapsed_ms` and logs/emits it)
7. **Extra log context**: `extra_log_context` dict (e.g., `batch_size`)

Key design: `_base_log_extras = {**error_kwargs, **extra_log_context}` so `request_id` from `error_kwargs` flows naturally into log extras without a separate parameter.

### client.py Changes

1. Added `from autom8_asana.clients.data import _retry as _retry_mod` to imports (following `_cache_mod`, `_metrics_mod`, `_response_mod` pattern)

2. Replaced 5 sets of inline callbacks with factory calls:
   - `_execute_batch_request` (L1169): logging + elapsed time + extra context (`batch_size`)
   - `_execute_insights_request` (L1534): logging + metrics + elapsed time (most complex)
   - `get_export_csv_async` (L1726): minimal (ExportError, no logging/metrics)
   - `get_appointments_async` (L1860): minimal (InsightsServiceError, no logging/metrics)
   - `get_leads_async` (L1964): minimal (InsightsServiceError, no logging/metrics)

---

## Deviations from Contract

**None.** All 5 call sites implemented per contract specification. Factory signature matches contract exactly.

**Minor implementation note**: The contract's call site examples showed `error_kwargs={"request_id": request_id, "reason": "timeout"}` but the Design Decisions section clarifies `reason` should NOT be in `error_kwargs` (factory injects it). The factory was implemented per the Design Decisions section (correct behavior).

---

## Invariants Verified

- Same error classes raised with same message text: CONFIRMED (tests pass)
- Same log event names and extra fields: CONFIRMED (observability tests pass)
- Same metrics emitted with same tags: CONFIRMED (metrics tests pass)
- Same circuit breaker `record_failure` calls: CONFIRMED (circuit breaker tests pass)
- `on_timeout_exhausted` always raises: CONFIRMED (factory raises `error_class(...)`)
- `on_http_error` always raises: CONFIRMED (factory raises `error_class(...)`)
- Public API unchanged: CONFIRMED (no public method signatures changed)

---

## Rollback Point

Pre-change state: commit `f6e08e5` (last committed state before this work).
To rollback: `git checkout f6e08e5 -- src/autom8_asana/clients/data/client.py` and delete `src/autom8_asana/clients/data/_retry.py`.
