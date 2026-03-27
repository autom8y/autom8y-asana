---
name: sprint5_instrumentation_patterns
description: Key implementation patterns discovered during Sprint 5 diagnostic span instrumentation (G-01 through G-07)
type: project
---

Sprint 5 diagnostic spans were implemented across 3 source files and 3 test files.

**Why:** Resolution error paths were log-observable but trace-invisible; null-slot INTERNAL_ERROR and INDEX_UNAVAILABLE had no trace ancestry.

**Key implementation discoveries:**

1. `start_as_current_span` auto-records exceptions by default (`record_exception=True`). When instrumenting a re-raise path (Tier 2 AsanaError) where we don't want an exception event, use `record_exception=False, set_status_on_exception=False` and handle all error tiers manually.

2. `ServiceError` base class `error_code` property returns `"SERVICE_ERROR"`. Subclasses override with specific codes (`EntityNotFoundError` → `"NOT_FOUND"`, etc.). Test assertions against the base class must use `"SERVICE_ERROR"` not `"DATA_UNAVAILABLE"`.

3. `audit_cascade_key_nulls` early-return guard (`if not cascade_key_nulls: return`) fires only when no cascade column appears in both the schema AND the key_columns tuple. Zero-null columns still populate the dict -- the guard is for "no matching columns" not "no nulls". Test the early-return path by passing an empty `key_columns=()` tuple.

4. The module-level `_tracer` patch pattern for non-computation spans: patch `autom8_asana.services.universal_strategy._tracer` and `autom8_asana.api.routes.resolver._tracer` (same pattern as `autom8y_telemetry.computation._tracer` in test_computation_spans.py).

5. ExitStack resolver test pattern (from test_resolver_status.py): `_resolve_patches()` returns ctx_patches + mock_resolve as last element. Enter `*ctx_patches` only; `entered[4]` is the AsanaClient mock class.

**How to apply:** When implementing future diagnostic spans in resolver or strategy layers, use these patterns verbatim.
