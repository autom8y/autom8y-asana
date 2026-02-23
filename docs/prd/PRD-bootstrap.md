---
prd_id: "PRD-BOOTSTRAP"
title: "Explicit Application Bootstrap"
status: "proposed"
created_at: "2026-02-23"
impact: low
impact_categories: []
complexity: "MODULE"
estimated_effort: "8-11 developer-days (reference from integration fit analysis)"
source_documents:
  - "docs/rnd/SCOUT-import-side-effect-elimination.md"
  - ".claude/wip/q1_arch/INTEGRATION-FIT-ANALYSIS.md (Gap 5A)"
related_debt: ["D-029", "RF-009"]
---

# PRD: Explicit Application Bootstrap

## Executive Summary

Replace the import-time `register_all_models()` call at `models/business/__init__.py:66` with an explicit `bootstrap()` function called at each application entry point, and add a `_ensure_bootstrapped()` deferred resolution guard to `ProjectTypeRegistry`. This eliminates fragile import ordering, improves test isolation, reduces Lambda cold start penalty, and follows the Django `django.setup()` pattern -- the most production-proven solution to this class of problem in the Python ecosystem.

## Impact Assessment

**impact**: low
**impact_categories**: []

**Rationale**: Internal initialization pattern change only. No API contract modifications, no database schema changes, no security-sensitive code paths, no cross-service dependencies. All changes are isolated to how and when an internal registry is populated. The public interface of every module remains identical.

## Background

### Problem

The current architecture registers 16 entity types into `ProjectTypeRegistry` as a side effect of importing `autom8_asana.models.business`. The call at `models/business/__init__.py:66` (`register_all_models()`) fires whenever any code does `from autom8_asana.models.business import X`. This causes four categories of harm:

1. **Fragile import ordering**: Any import of business models triggers registration, which must complete before any detection call succeeds. This creates invisible coupling documented in the debt ledger (D-029, RF-009). The comment at `models/business/__init__.py:55-58` explicitly acknowledges this as deferred work.

2. **Test pollution via mutable singletons**: `ProjectTypeRegistry._instance`, `SchemaRegistry._instance`, `MetricRegistry._instance`, and `WorkspaceProjectRegistry._instance` persist across tests. Currently mitigated by explicit `.reset()` calls in ~25 test files (100 occurrences), but the implicit bootstrap makes this error-prone.

3. **Lambda cold start penalty**: Lambda handlers pay full registration cost even when only needing a subset of functionality. Every handler that imports any business model triggers the entire 16-entity registration cascade.

4. **Circular dependency management burden**: 6+ `__getattr__` lazy-load sites, 20+ deferred function-body imports, and 4 active circular dependency chains are symptoms of import-time coupling. While this PRD does not address circular dependencies directly, removing the import-time side effect reduces pressure on the import graph.

### Why Now

- The codebase already has the building blocks: `register_all_models()` is idempotent, `reset_bootstrap()` exists, `is_bootstrap_complete()` exists, and `lifespan()` is the natural FastAPI hook.
- `SchemaRegistry._ensure_initialized()` and `MetricRegistry._ensure_initialized()` already implement the deferred resolution pattern -- `ProjectTypeRegistry` is the only registry without this guard.
- The defensive call in `detection/tier1.py:93-105` already implements a bootstrap guard, confirming the need is recognized in the codebase.
- Every new entity type added increases the registration cascade cost. Every new developer encounters the "why does import order matter" learning curve.

### Existing Patterns to Follow

| Pattern | Location | Description |
|---------|----------|-------------|
| `SchemaRegistry._ensure_initialized()` | `src/autom8_asana/dataframes/models/registry.py:104` | Lazy init with thread-safe locking on first `get_schema()` call |
| `MetricRegistry._ensure_initialized()` | `src/autom8_asana/metrics/registry.py:111` | Lazy import of definition modules on first `get_metric()` call |
| `register_all_models()` idempotency | `src/autom8_asana/models/business/_bootstrap.py:38` | `_BOOTSTRAP_COMPLETE` flag prevents re-registration |
| `reset_bootstrap()` for tests | `src/autom8_asana/models/business/_bootstrap.py:143` | Resets `_BOOTSTRAP_COMPLETE` flag |
| Tier-1 defensive bootstrap | `src/autom8_asana/models/business/detection/tier1.py:93-105` | Calls `register_all_models()` if detection finds empty registry |

## User Stories

- **US-1**: As a **developer**, I want business model imports to not trigger side effects, so that I can import entity classes without worrying about import ordering or registry state.
- **US-2**: As a **test author**, I want explicit control over when bootstrap runs, so that I can write isolated tests without implicit state leaking between test modules.
- **US-3**: As an **ops engineer**, I want Lambda handlers to only pay initialization costs when needed, so that cold starts are as fast as possible.
- **US-4**: As a **developer**, I want a safety net if I forget to call `bootstrap()`, so that detection still works (with a logged warning) rather than silently returning `None`.

## Functional Requirements

### Must Have (M)

- **FR-M1**: Create a `bootstrap()` function that wraps `register_all_models()` and serves as the single public API for application initialization. Location: `src/autom8_asana/models/business/_bootstrap.py` (co-located with existing bootstrap machinery) or `src/autom8_asana/core/bootstrap.py` (architect decides).

- **FR-M2**: Add `_ensure_bootstrapped()` guard to `ProjectTypeRegistry.lookup()`, `get_primary_gid()`, `is_registered()`, `get_all_mappings()`, and `get_all_schemas()` methods. The guard MUST call `register_all_models()` on first access if `_BOOTSTRAP_COMPLETE` is False. This follows the existing `SchemaRegistry._ensure_initialized()` pattern at `dataframes/models/registry.py:104`.

- **FR-M3**: Wire explicit `bootstrap()` call into all 8 cataloged entry points:

  | Entry Point | File | Insertion Point |
  |-------------|------|-----------------|
  | API lifespan | `src/autom8_asana/api/lifespan.py` | Before `_discover_entity_projects()` in startup sequence |
  | Cache warmer Lambda | `src/autom8_asana/lambda_handlers/cache_warmer.py` | Top of handler function, before business logic |
  | Cache invalidate Lambda | `src/autom8_asana/lambda_handlers/cache_invalidate.py` | Top of handler function |
  | Workflow handler Lambda | `src/autom8_asana/lambda_handlers/workflow_handler.py` | Top of handler function |
  | Conversation audit Lambda | `src/autom8_asana/lambda_handlers/conversation_audit.py` | Top of handler function |
  | Insights export Lambda | `src/autom8_asana/lambda_handlers/insights_export.py` | Top of handler function |
  | CLI entrypoint | `src/autom8_asana/entrypoint.py` | Before app import/startup |
  | Test conftest | `tests/conftest.py` | Session-scoped autouse fixture |

- **FR-M4**: Remove the `register_all_models()` call from `src/autom8_asana/models/business/__init__.py:66`. The import statement at line 64 (`from autom8_asana.models.business._bootstrap import register_all_models`) MAY remain for backward compatibility or be removed if no external consumers exist.

- **FR-M5**: Add a session-scoped bootstrap fixture to `tests/conftest.py` that calls `bootstrap()` once per test session, ensuring all tests run with a populated registry by default.

- **FR-M6**: Ensure the defensive `register_all_models()` call in `detection/tier1.py:93-105` remains compatible with the new pattern. Two valid options (architect decides):
  - **Option A**: Keep the existing guard as-is (calls `register_all_models()` directly).
  - **Option B**: Replace with a call to `_ensure_bootstrapped()` on the registry, removing duplication.

- **FR-M7**: Update ~25 test files that use `.reset()` patterns to work with the new session-scoped bootstrap fixture. Tests that call `ProjectTypeRegistry.reset()` and then expect registry population MUST either:
  - Re-call `bootstrap()` after reset, OR
  - Rely on `_ensure_bootstrapped()` to re-populate on next lookup.

### Should Have (S)

- **FR-S1**: The `bootstrap()` function SHOULD log a structured event at INFO level when called, including whether it was a fresh bootstrap or a no-op (idempotent).

- **FR-S2**: The `_ensure_bootstrapped()` guard SHOULD log a WARNING when it triggers (indicating a code path reached the registry without explicit bootstrap). This makes "forgot to call bootstrap" visible in logs without failing.

- **FR-S3**: The `bootstrap()` function SHOULD be importable from a short, memorable path: `from autom8_asana import bootstrap` or `from autom8_asana.models.business import bootstrap`.

### Could Have (C)

- **FR-C1**: Add a `bootstrap(*, registries: list[str] | None = None)` parameter allowing selective bootstrap of specific registries (e.g., only `ProjectTypeRegistry` for Lambda handlers that do not need Schema or Metric registries). Deferred unless Lambda cold start measurements indicate need.

- **FR-C2**: Add a `--no-bootstrap` CLI flag to `entrypoint.py` for diagnostic purposes (start the app without automatic registration to test behavior).

## Non-Functional Requirements

- **NFR-1**: Performance -- `_ensure_bootstrapped()` guard MUST add less than 1 microsecond to lookup calls when bootstrap is already complete (single boolean check). The guard MUST NOT add locking overhead on the hot path (check `_BOOTSTRAP_COMPLETE` flag first, only acquire lock if False).

- **NFR-2**: Performance -- Lambda cold start latency MUST NOT regress. Target: measurable improvement by avoiding registration when not needed, or at worst, identical latency (registration moved from import to explicit call within the same handler invocation).

- **NFR-3**: Idempotency -- `bootstrap()` MUST remain idempotent. Multiple calls MUST be no-ops after the first successful call. This preserves the existing `_BOOTSTRAP_COMPLETE` guard behavior.

- **NFR-4**: Test isolation -- The session-scoped fixture MUST NOT prevent individual tests from calling `reset()` + `bootstrap()` for test-specific registry states. The fixture provides a default; tests can override.

- **NFR-5**: Backward compatibility -- Any code that currently works via `from autom8_asana.models.business import X` followed by detection MUST continue to work due to the `_ensure_bootstrapped()` fallback. Behavior is preserved; only the mechanism changes.

## Edge Cases

| # | Case | Expected Behavior |
|---|------|-------------------|
| EC-1 | Script/notebook imports business models without calling `bootstrap()` | `_ensure_bootstrapped()` fires on first registry lookup. Registration happens transparently. WARNING logged to indicate missing explicit bootstrap. |
| EC-2 | Test calls `ProjectTypeRegistry.reset()` then immediately does a registry lookup | `_ensure_bootstrapped()` re-triggers `register_all_models()`, repopulating the registry. Test proceeds normally. |
| EC-3 | Detection code at `tier1.py:93-105` fires before explicit `bootstrap()` | Either the existing guard calls `register_all_models()` directly (Option A) or `_ensure_bootstrapped()` handles it (Option B). Either way, detection succeeds. |
| EC-4 | Third-party code does `from autom8_asana.models.business import Offer` and calls `detect_entity_type()` | Works via `_ensure_bootstrapped()`. No behavioral change from current implicit bootstrap. |
| EC-5 | Test file imports business models at module level (before conftest fixture runs) | Python's import machinery runs before fixtures. However, the import no longer triggers registration. The session-scoped fixture runs before any test function executes, so by test execution time, the registry is populated. Module-level code that calls detection functions (not just imports) would hit `_ensure_bootstrapped()`. |
| EC-6 | Lambda handler invoked in an environment where `register_all_models()` fails (e.g., missing entity module) | Same behavior as today -- `register_all_models()` logs the error. The failure now happens at explicit `bootstrap()` call rather than at import time, making the error more visible and debuggable. |
| EC-7 | `bootstrap()` called concurrently from multiple threads | Idempotent: `_BOOTSTRAP_COMPLETE` flag is checked first. If a race condition occurs, `register_all_models()` handles duplicate registrations gracefully (existing idempotency guard). For additional safety, architect may add a threading lock matching the `SchemaRegistry._ensure_initialized()` pattern. |
| EC-8 | `WorkspaceProjectRegistry` accessed before bootstrap | `WorkspaceProjectRegistry` composes with `ProjectTypeRegistry` (line 368 of registry.py). If `ProjectTypeRegistry` is not yet populated, `WorkspaceProjectRegistry.lookup()` delegates to `_type_registry.lookup()`, which triggers `_ensure_bootstrapped()`. No special handling needed. |

## Success Criteria

- [ ] SC-1: `register_all_models()` is NOT called at import time from `models/business/__init__.py` (line 66 removed or commented with rationale).
- [ ] SC-2: `bootstrap()` function exists and is called explicitly at all 8 cataloged entry points (API lifespan, 6 Lambda handlers, CLI entrypoint).
- [ ] SC-3: `_ensure_bootstrapped()` guard is present on all `ProjectTypeRegistry` public lookup methods (`lookup`, `get_primary_gid`, `is_registered`, `get_all_mappings`).
- [ ] SC-4: Session-scoped bootstrap fixture exists in `tests/conftest.py`.
- [ ] SC-5: All 10,552+ existing tests pass (zero regressions).
- [ ] SC-6: Lambda cold start latency measured before and after -- no regression, with target improvement documented.
- [ ] SC-7: Detection code in `tier1.py:93-105` continues to function correctly (either kept as-is or replaced by `_ensure_bootstrapped()` mechanism).
- [ ] SC-8: A test exists that verifies: import business models, do NOT call `bootstrap()`, call `detect_entity_type()` -- verify it succeeds via `_ensure_bootstrapped()` fallback.

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R-1 | Test breakage during migration (50-100 tests affected based on 100 `.reset()` occurrences across 25 files) | Medium | Medium | Session-scoped `conftest.py` fixture provides baseline. Incremental fix: run test suite after each batch of file updates. |
| R-2 | Lambda handler missing `bootstrap()` call | Low | High | `_ensure_bootstrapped()` fallback ensures correctness even if a handler omits the call. WARNING log makes omission visible. Add integration test per handler. |
| R-3 | Performance: first registry lookup post-bootstrap pays initialization cost | Low | Low | `register_all_models()` completes in <5ms (16 entity types, dictionary inserts). All real code paths are dominated by network I/O (50-500ms per Asana API call). |
| R-4 | Developer confusion about when to call `bootstrap()` | Medium | Low | Document in codebase (update `__init__.py` module docstring and `CLAUDE.md`). The pattern is identical to Django's `django.setup()`, which every Python web developer knows. |
| R-5 | Rollback needed mid-migration | Low | Low | Rollback is a single-line change: re-add `register_all_models()` to `models/business/__init__.py:66`. All other changes (entry point calls, `_ensure_bootstrapped()` guard) are additive and harmless if the import-time call is restored. |

## Out of Scope

These items are explicitly excluded from this work. They may be addressed in future work items.

- **Import graph restructuring**: Eliminating the 4 active circular dependency chains and 20+ deferred imports. This is a separate initiative (SCOUT Phase 2/3 -- ASSESS verdict).
- **DI container introduction**: Replacing singleton registries with dependency injection. Assessed and placed on HOLD per SCOUT analysis (Pydantic v2 compatibility issues, 8-12 week effort).
- **PEP 562 lazy loading formalization**: Extending `__getattr__` lazy imports to all `__init__.py` files. On HOLD per SCOUT analysis (treats symptoms, not root cause).
- **Consolidation of other registries**: `SchemaRegistry`, `MetricRegistry`, and `WorkspaceProjectRegistry` already have their own initialization patterns. This PRD addresses `ProjectTypeRegistry` only.
- **Changes to `__init_subclass__` or `__set_name__` descriptor hooks**: These fire at class definition time (import) regardless of bootstrap. They are orthogonal to this work and must not be modified.
- **`register_all_models()` function removal**: The function itself remains. Only its call site at import time is removed. It continues to be called by `bootstrap()` and by the tier-1 defensive guard (if retained).

## Effort Reference

**8-11 developer-days** (1.5-2.5 developer-weeks) per integration fit analysis. Confidence: Medium-High. The uncertainty range is driven by test fix effort (3-5 days estimated based on 100 `.reset()` occurrences across 25 test files).

Breakdown from integration fit analysis:

| Phase | Effort |
|-------|--------|
| Create `bootstrap()` function | 1 day |
| Add `_ensure_bootstrapped()` to ProjectTypeRegistry | 1 day |
| Add explicit `bootstrap()` to 6 Lambda handlers | 1 day |
| Add explicit `bootstrap()` to API lifespan | 0.5 days |
| Remove import-time `register_all_models()` from `__init__.py` | 0.5 days |
| Fix broken tests (~50-100 affected) | 3-5 days |
| Add `bootstrap()` to test conftest.py | 0.5 days |
| Verify all entry points + CI green | 1-2 days |

## Open Questions

None. All questions resolved during SCOUT and integration fit analysis phases.

## Traceability

| Requirement | Source |
|-------------|--------|
| FR-M1, FR-M2 | SCOUT Approach 1 (Explicit Bootstrap) + Approach 6 (Deferred Resolution) |
| FR-M3 | Integration Fit Analysis Gap 5A, entry point inventory |
| FR-M4 | SCOUT recommendation, `models/business/__init__.py:55-58` comment (RF-009) |
| FR-M5 | SCOUT impact on test isolation analysis |
| FR-M6 | Integration Fit Analysis hidden dependency #7 |
| FR-M7 | Integration Fit Analysis, 100 `.reset()` occurrences across 25 test files |
| NFR-1 | SCOUT risk analysis: "<5ms, dominated by network I/O" |
| NFR-5 | SCOUT Approach 6 rationale: "graceful degradation" |
| Edge cases | SCOUT "What breaks during migration" sections |
