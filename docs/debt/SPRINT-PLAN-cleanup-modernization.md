---
plan_id: "SPRINT-cleanup-modernization"
created_at: "2026-02-18"
input_risk_matrix: "RISK-MATRIX-cleanup-modernization.md"
input_ledger: "LEDGER-cleanup-modernization.md"
total_items: 35
planned_sprints: 5
deferred_items: 11
total_effort: "18-26 developer-days"
risk_appetite: "aggressive"
---

# Cleanup & Modernization Sprint Plan

## Executive Summary

**Total Effort**: 18-26 developer-days across 5 sprints
**Sprint Count**: 5 (2 pattern/cleanup, 1 test integrity, 1 pipeline convergence, 1 god object decomposition)
**Quick Wins**: 7 items packable into < 1 hour each, suitable for warm-up or interstitial work
**Deferred**: 11 items with documented rationale and trigger conditions
**LOC Impact**: ~3,800 net reduction (sprints 1-3) + ~2,500 refactored-in-place (sprints 4-5)

**Stakeholder Alignment**:
- Pain point #1 (pattern inconsistency): Sprint 1 unifies error handling, DI, and query routers across all API routes
- Pain point #2 (code bloat/LOC): Sprints 1-3 deliver ~3,800 LOC net reduction; sprints 4-5 restructure ~4,000 LOC
- Pain point #3 (test brittleness): Sprint 3 fixes pre-existing failures, retargets dead-code tests, and hardens CI signal

**Canonical Decisions Applied**:
- Error handling = dict-mapping (D-004, applied in Sprint 1)
- DI = Depends+Annotated with RequestId (D-005, applied in Sprint 1)
- Query routers merged into single query.py (D-012, applied in Sprint 1)

---

## Sprint Roadmap Overview

| Sprint | Name | Goal | Effort | LOC Impact | Dependencies |
|--------|------|------|--------|------------|--------------|
| **1** | Pattern Unification | Single canonical pattern for error handling and DI across all API routes | 4-6 days | -1,000 to -1,200 | None |
| **2** | Config & Cleanup Sweep | Consolidate config access, remove deprecated exports and shims | 2-3 days | -350 to -450 | None (parallel with Sprint 1 possible) |
| **3** | Test Integrity | Fix pre-existing failures, retarget dead-code tests, restore CI trust | 2-3 days | -500 (test LOC) | Sprint 1 (D-012 must complete before D-026) |
| **4** | Pipeline Convergence | Extract shared creation engine, consolidate dual-path architecture | 5-8 days | -900 to -1,500 (refactor) | Sprints 1-2 complete |
| **5** | God Object Decomposition | Decompose DataServiceClient and SaveSession into cohesive units | 5-8 days | ~4,000 (restructured) | Sprint 4 complete (patterns established) |

```
Sprint 1          Sprint 2         Sprint 3          Sprint 4              Sprint 5
[Pattern Unif.]   [Config/Cleanup]  [Test Integrity]  [Pipeline Converge]   [God Object Decomp]
 D-005,D-006       D-010,D-011      D-029             D-023                 D-031
 D-004,D-008       D-007,D-017      D-026             D-033                 D-030
 D-012,D-018       D-014            D-027(partial)    D-022                 D-032
 D-019,D-001                                                                D-028
                   Can overlap
                   with Sprint 1
                        |
                        v
              Sprint 3 blocked on D-012 from Sprint 1
```

---

## Sprint 1: Pattern Unification

**Goal**: Establish a single canonical pattern for error handling and dependency injection across all API routes. Directly addresses stakeholder pain point #1 (pattern inconsistency).

**Duration**: 4-6 developer-days
**Items**: D-005, D-006, D-004, D-008, D-012, D-001, D-018, D-019
**Combined Risk Score**: 105
**LOC Reduction**: ~1,000-1,200 net
**Confidence**: Medium (add 30% buffer for mock breakage from D-027)
**Dependencies**: None -- this is the starting sprint

### Execution Sequence

The dependency chain dictates strict ordering for some items. Others can be parallelized.

```
Phase A (parallel):                    Phase B:           Phase C:
  D-005 (DI: RequestId migration)       D-006 (narrow      D-004 (error handling
  D-012 (query router merge)             raise_api_error)    consolidation)
  D-008 (webhooks HTTPException)
  D-018 (entity_write DI)
  D-019 (resolver DI)

         |                                   |                    |
    [all Phase A complete]              [D-005 done]         [D-006 done]
```

### Task 1.1: DI Migration to RequestId (D-005)

**Size**: M (4-6 hours)
**Confidence**: High
**Dependencies**: None
**Parallelizable**: Yes -- proceed alongside D-012, D-008

**What to do**:
Migrate three route files from `Request` object to `RequestId` dependency for obtaining the request ID. This is a mechanical migration: replace `request: Request` parameters with `request_id: RequestId` and update all downstream calls.

**Files to change**:
- `src/autom8_asana/api/routes/query.py` -- Replace `request: Request` with `request_id: RequestId` in handler signatures. Replace `getattr(request.state, "request_id", "unknown")` with direct `request_id` usage. Update `raise_api_error(request, ...)` calls to `raise_api_error(request_id, ...)`.
- `src/autom8_asana/api/routes/entity_write.py` -- Same migration at line 131+. Also address inline `request.app.state` access (covered more fully in Task 1.5).
- `src/autom8_asana/api/routes/resolver.py` -- Same migration at line 149+. Remove inline `getattr(request.state, ...)` patterns.

**Step-by-step**:
1. Add `from autom8_asana.api.dependencies import RequestId` to each file's imports
2. Replace `request: Request` with `request_id: RequestId` in route handler signatures
3. Replace all `getattr(request.state, "request_id", "unknown")` with `request_id`
4. Replace all `raise_api_error(request, ...)` with `raise_api_error(request_id, ...)`
5. Run affected test files: `pytest tests/api/test_routes_query.py tests/api/test_routes_entity_write.py tests/api/test_routes_resolver.py -x`
6. Fix any mock breakage (tests that construct `Request` objects with `request.state.request_id` will need updating)

**Risk mitigation**: Tests that manually construct `Request` objects (D-027: 14 instances in test_dependencies.py, test_integration.py) will break. Budget 1-2 hours for test fixup. If a test is too entangled, add a `# TODO: D-027 mock migration` comment and use a minimal shim.

**Definition of Done**:
- [ ] Zero route files pass a `Request` object to `raise_api_error()` or `raise_service_error()`
- [ ] All three route files use `RequestId` type alias in handler signatures
- [ ] No `getattr(request.state, "request_id", ...)` patterns remain in route files
- [ ] All affected tests pass

### Task 1.2: Query Router Merge (D-012, absorbs D-001)

**Size**: M (4-6 hours)
**Confidence**: High
**Dependencies**: None
**Parallelizable**: Yes -- proceed alongside D-005, D-008

**What to do**:
Merge `query.py` (369 LOC) and `query_v2.py` (191 LOC) into a single `query.py` using the v2 patterns. The v1 `query_rows` handler (D-001, 130 LOC dead code) is deleted. The deprecated `POST /v1/query/{entity_type}` endpoint is preserved with deprecation headers until sunset (2026-06-01). The "v2" naming is stripped per stakeholder decision.

**Files to change**:
- `src/autom8_asana/api/routes/query_v2.py` -- Rename to `query.py` (or merge content into existing `query.py`)
- `src/autom8_asana/api/routes/query.py` -- Receives merged content; dead v1 handler deleted
- `src/autom8_asana/api/main.py` -- Update router import/registration (line 184) to reference single router
- `tests/api/test_routes_query_rows.py` -- Tests for dead handler: delete or quarantine (Sprint 3 handles full retargeting)

**Step-by-step**:
1. Read both query files fully to understand endpoint registration
2. Create new `query.py` with v2 content as the base
3. Port the deprecated `POST /v1/query/{entity_type}` endpoint from old `query.py`, applying v2 patterns (dict-mapping error handling, RequestId DI)
4. Delete the dead `query_rows` handler (D-001: lines 239-369 of old query.py)
5. Delete old `query_v2.py` file
6. Update `api/main.py` router imports to point to single `query_router`
7. Update any imports elsewhere that reference `query_v2`
8. Run: `pytest tests/api/test_routes_query*.py -x`
9. Quarantine `test_routes_query_rows.py` tests with `@pytest.mark.skip(reason="D-026: retarget to merged router in Sprint 3")`

**Risk mitigation**: The `api/main.py` router registration is the critical point. If the merged router registers incorrectly, v2 endpoints break. Verify by running the full API test suite, not just query tests. Rollback: revert the file rename and restore both files.

**Definition of Done**:
- [ ] Single `query.py` file contains all active query endpoints
- [ ] `query_v2.py` file deleted
- [ ] Dead v1 `query_rows` handler removed (130 LOC)
- [ ] Deprecated v1 endpoint preserved with deprecation headers
- [ ] `api/main.py` registers a single query router
- [ ] All v2 query tests pass against merged router
- [ ] Net LOC reduction: ~370

### Task 1.3: Webhooks HTTPException Fix (D-008)

**Size**: S (1-2 hours)
**Confidence**: High
**Dependencies**: None
**Parallelizable**: Yes -- fully independent

**What to do**:
Replace three raw `HTTPException` raises in `webhooks.py:verify_webhook_token()` with `raise_api_error()` calls to ensure consistent error format with `request_id` in response body.

**Files to change**:
- `src/autom8_asana/api/routes/webhooks.py` -- Lines 139-165: three `HTTPException` raises

**Step-by-step**:
1. Add `RequestId` dependency to the webhook handler signature
2. Import `raise_api_error` from `api.errors`
3. Replace `raise HTTPException(status_code=503, detail="...")` with `raise_api_error(request_id, status_code=503, error_type="webhook_config_error", message="...")`
4. Repeat for 401 raises (missing token, invalid token)
5. Run: `pytest tests/api/test_routes_webhooks.py -x`

**Definition of Done**:
- [ ] Zero `HTTPException` raises in webhooks.py (use `raise_api_error` exclusively)
- [ ] Webhook error responses include `request_id` field
- [ ] All webhook tests pass

### Task 1.4: entity_write.py DI Migration (D-018)

**Size**: M (3-4 hours)
**Confidence**: Medium (inline `request.app.state` access adds complexity beyond simple DI swap)
**Dependencies**: None (can proceed in parallel, but benefits from D-005 patterns being established)
**Parallelizable**: Yes

**What to do**:
Migrate `entity_write.py` from `request.app.state` access to proper FastAPI Depends for `entity_write_registry`, `mutation_invalidator`, and auth context. Replace inline `get_bot_pat()` with `get_auth_context()`.

**Files to change**:
- `src/autom8_asana/api/routes/entity_write.py` -- Lines 146-198: replace `request.app.state` access
- `src/autom8_asana/api/dependencies.py` -- Add `EntityWriteRegistryDep` if not already present

**Step-by-step**:
1. Add `RequestId` to handler signature (aligns with D-005)
2. Add `MutationInvalidatorDep` to handler signature (already exists in dependencies.py)
3. Create `EntityWriteRegistryDep` in dependencies.py if needed, or use existing lifespan-registered dependency
4. Replace `request.app.state.entity_write_registry` with injected dependency
5. Replace `request.app.state.mutation_invalidator` with `MutationInvalidatorDep`
6. Replace inline `get_bot_pat()` call with `get_auth_context()` dependency
7. Remove `Request` import if no longer needed
8. Run: `pytest tests/api/test_routes_entity_write.py -x`

**Risk mitigation**: The `entity_write_registry` may be registered on app state during lifespan startup. Verify it is available as a FastAPI dependency. If not, create a simple `Depends` wrapper that reads from app state -- this is still better than inline access.

**Definition of Done**:
- [ ] No `request.app.state` access in entity_write.py
- [ ] Uses `RequestId`, `MutationInvalidatorDep`, and proper DI for all dependencies
- [ ] No inline `get_bot_pat()` calls
- [ ] All entity_write tests pass

### Task 1.5: resolver.py DI Migration (D-019)

**Size**: M (3-4 hours)
**Confidence**: Medium (custom `get_supported_entity_types()` fallback logic adds scope)
**Dependencies**: None (can proceed in parallel)
**Parallelizable**: Yes

**What to do**:
Migrate `resolver.py` from `Request` to `RequestId` and from inline `AsanaClient` construction to `AsanaClientDualMode` dependency. Replace custom entity type validation with `EntityServiceDep`.

**Files to change**:
- `src/autom8_asana/api/routes/resolver.py` -- Lines 97-154: replace DI and validation approach

**Step-by-step**:
1. Add `RequestId` to handler signature
2. Replace `Request` parameter with proper DI dependencies
3. Replace `get_supported_entity_types()` (lines 97-141) with `EntityServiceDep` if it provides equivalent validation
4. Replace inline `AsanaClient` construction with `AsanaClientDualMode` dependency
5. Replace broad exception catches in entity validation with typed catches
6. Run: `pytest tests/api/test_routes_resolver.py -x`

**Risk mitigation**: The `get_supported_entity_types()` function has multiple fallback layers. Verify that `EntityServiceDep` provides the same entity types. If there is a gap, keep the function but have it consume the injected service rather than constructing its own.

**Definition of Done**:
- [ ] No `Request` parameter in resolver.py handler signatures
- [ ] Uses `RequestId` and `EntityServiceDep` (or equivalent typed DI)
- [ ] No inline `AsanaClient` construction via `get_bot_pat()`
- [ ] Broad exception catches replaced with typed catches where possible
- [ ] All resolver tests pass

### Task 1.6: Narrow raise_api_error Signature (D-006)

**Size**: S (30-60 minutes)
**Confidence**: High
**Dependencies**: D-005 must be complete (all callers pass `str`, not `Request`)
**Parallelizable**: No -- blocked on Phase A completion

**What to do**:
Once all routes pass `request_id: str` (not `Request`), narrow the `raise_api_error()` signature to accept only `str`. Remove the `Request` branch from the union type.

**Files to change**:
- `src/autom8_asana/api/errors.py` -- Lines 86-131: change `request_or_id: Request | str` to `request_id: str`

**Step-by-step**:
1. Verify grep confirms zero callers pass `Request`: `grep -r "raise_api_error(request," src/` should return nothing
2. Change parameter type from `Request | str` to `str`
3. Remove the `isinstance(request_or_id, Request)` branch
4. Rename parameter from `request_or_id` to `request_id`
5. Run full test suite: `pytest tests/ -x --timeout=120`

**Definition of Done**:
- [ ] `raise_api_error()` accepts only `str` as first parameter
- [ ] `isinstance` check for `Request` type removed
- [ ] Parameter renamed to `request_id`
- [ ] All tests pass

### Task 1.7: Error Handling Consolidation (D-004)

**Size**: M (4-6 hours)
**Confidence**: Medium (4 files with different error shapes)
**Dependencies**: D-005 and D-006 must be complete
**Parallelizable**: No -- blocked on D-006

**What to do**:
Migrate the remaining v1-style error handling (individual except blocks) to v2 dict-mapping pattern across all route files. After this task, every route file uses the same canonical error handling pattern.

**Files to change**:
- `src/autom8_asana/api/routes/entity_write.py` -- Lines 211-294: 8 except blocks to dict-mapping
- `src/autom8_asana/api/routes/resolver.py` -- Lines 220-370: 8+ except blocks to dict-mapping
- `src/autom8_asana/api/routes/query.py` -- Deprecated endpoint: simplify remaining error handling to dict-mapping (post-merge from Task 1.2)

**Step-by-step (per file)**:
1. Identify all exception types caught in the handler
2. Create `_ERROR_STATUS: dict[type[Exception], int]` mapping at module level
3. Create a single `_raise_<route>_error(request_id, exc)` helper that does dict lookup
4. Replace N separate except blocks with single `except tuple(_ERROR_STATUS) as exc:` + helper call
5. Run file-specific tests
6. Repeat for each file

**Risk mitigation**: Some except blocks may have handler-specific logic beyond status code mapping (e.g., custom error message construction). Audit each block before converting. If a block has unique logic, keep it as a separate except but document why.

**Definition of Done**:
- [ ] All route files use dict-mapping error handling pattern
- [ ] Zero files use individual per-exception-type except blocks for status code mapping
- [ ] Each route file has at most one error-mapping dict and one error-raising helper
- [ ] All tests pass
- [ ] Net LOC reduction: ~200 across files

### Sprint 1 Summary

| Task | Item(s) | Size | Parallel | LOC Impact |
|------|---------|------|----------|------------|
| 1.1 | D-005 | M | Phase A | -60 |
| 1.2 | D-012, D-001 | M | Phase A | -370 |
| 1.3 | D-008 | S | Phase A | -30 (net ~0, refactor) |
| 1.4 | D-018 | M | Phase A | -40 |
| 1.5 | D-019 | M | Phase A | -50 |
| 1.6 | D-006 | S | Phase B | -10 |
| 1.7 | D-004 | M | Phase C | -200 |
| **Total** | **8 items** | **4-6 days** | | **-730 to -760** |

**Mock Breakage Buffer** (D-027): Add 1 day for test fixup across all tasks. Pattern changes will break mock paths in tests that patch `autom8_asana.api.routes.query.AsanaClient` or construct `Request` objects. Each task should fix its own test breakage, but budget a buffer day for cascading failures discovered during integration.

**Sprint 1 Acceptance Criteria**:
- [ ] All API route files use `RequestId` dependency (zero `Request` object DI)
- [ ] All API route files use dict-mapping error handling (zero per-exception-type blocks)
- [ ] Single `query.py` file (no `query_v2.py`)
- [ ] `raise_api_error()` accepts only `str` (no `Request` union)
- [ ] Webhooks use `raise_api_error()` (no raw `HTTPException`)
- [ ] `entity_write.py` and `resolver.py` use proper FastAPI DI (no `request.app.state`)
- [ ] Full test suite passes (or failures are pre-existing D-029, quarantined)
- [ ] Net LOC reduction: >= 700

---

## Sprint 2: Configuration & Cleanup Sweep

**Goal**: Consolidate config access through Settings, remove deprecated exports and shims. Addresses pain point #2 (code bloat) and establishes config-access consistency.

**Duration**: 2-3 developer-days
**Items**: D-010, D-011, D-035, D-007, D-017, D-014
**Combined Risk Score**: 48
**LOC Reduction**: ~350-450
**Confidence**: Medium (D-011 has 20+ sites; D-017 requires consumer audit)
**Dependencies**: None -- can run in parallel with Sprint 1 if staffing allows

**Note**: Sprint 2 is independent of Sprint 1. If multiple developers are available, Sprints 1 and 2 can be executed concurrently.

### Task 2.1: Fix Module-Level get_settings() Calls (D-010)

**Size**: S (30-60 minutes)
**Confidence**: High
**Dependencies**: None

**What to do**:
Move 4 module-level `get_settings()` calls inside the functions/methods that use them. This fixes test override breakage and stale config values.

**Files to change**:
- `src/autom8_asana/clients/sections.py:27` -- Move `SECTION_CACHE_TTL = get_settings().cache.ttl_section` inside function
- `src/autom8_asana/clients/users.py:22` -- Same pattern
- `src/autom8_asana/clients/custom_fields.py:26` -- Same pattern
- `src/autom8_asana/clients/projects.py:22` -- Same pattern

**Definition of Done**:
- [ ] Zero module-level `get_settings()` calls in client files
- [ ] Cache TTL values resolved lazily inside functions
- [ ] Test overrides of Settings work correctly for these values

### Task 2.2: Consolidate os.environ Access (D-011, absorbs D-035)

**Size**: L (8-12 hours)
**Confidence**: Medium (20+ sites, some may need new Settings fields)
**Dependencies**: D-010 should be done first (establishes pattern)

**What to do**:
Route 20+ `os.environ.get()` / `os.getenv()` calls through the `Settings` pydantic model. For any env vars not yet in Settings, add them. D-035 (Lambda handler subset) is absorbed by this task.

**Key files** (11+ files, 20+ call sites):
- `clients/data/config.py` -- 4 calls
- `clients/data/client.py` -- 1 call
- `lambda_handlers/cloudwatch.py` -- 2 calls
- `lambda_handlers/cache_warmer.py` -- 1 call
- `lambda_handlers/checkpoint.py` -- 1 call
- `cache/dataframe/decorator.py` -- 1 call
- `cache/dataframe/tiers/memory.py` -- 1 call
- `cache/integration/batch.py` -- 2 calls
- `dataframes/builders/progressive.py` -- 1 call
- `models/business/registry.py` -- 1 call
- `entrypoint.py` -- 2 calls

**Step-by-step**:
1. Audit each call site to identify env var name and default value
2. For each env var not already in Settings, add a field with matching default
3. Replace `os.environ.get("VAR", default)` with `get_settings().section.var`
4. For Lambda handlers: evaluate whether a Lambda-specific Settings subclass is warranted, or if the main Settings model suffices
5. Run tests for each changed file

**Risk mitigation**: Some env vars (e.g., ECS metadata URLs in `batch.py`) are container-specific and may not make sense in Settings. For these, add a `# ENV-DIRECT: container-specific, intentional bypass` annotation and leave in place.

**Definition of Done**:
- [ ] All non-annotated `os.environ` / `os.getenv` calls route through Settings
- [ ] Remaining direct env access has explicit annotation documenting why
- [ ] New Settings fields have defaults matching current behavior
- [ ] Tests can override all config via Settings fixture

### Task 2.3: Remove Deprecated DI Dependencies (D-007)

**Size**: M (2-4 hours)
**Confidence**: Medium (requires consumer audit)
**Dependencies**: Sprint 1 D-005 should be complete (ensures no route uses deprecated path)

**What to do**:
Remove `get_asana_pat()` and `get_asana_client()` from `dependencies.py` and from `__all__`. Remove duplicated Bearer token validation logic.

**Files to change**:
- `src/autom8_asana/api/dependencies.py` -- Lines 290-377: remove two deprecated functions + aliases
- Remove from `__all__` (lines 587-588)

**Step-by-step**:
1. Grep for all usages: `get_asana_pat`, `get_asana_client`, `AsanaPAT`, `AsanaClientDep`
2. For each consumer: verify they can use `get_auth_context` / `get_asana_client_from_context` instead
3. Migrate any remaining consumers
4. Delete deprecated functions and type aliases
5. Remove from `__all__`
6. Run full test suite

**Definition of Done**:
- [ ] `get_asana_pat()` and `get_asana_client()` removed
- [ ] `AsanaPAT` and `AsanaClientDep` type aliases removed
- [ ] `__all__` updated
- [ ] Zero consumers reference deprecated functions
- [ ] ~90 LOC removed

### Task 2.4: Remove Deprecated Aliases (D-017)

**Size**: L (6-10 hours)
**Confidence**: Low (11+ locations, requires consumer audit across codebase and potentially external consumers)
**Dependencies**: None

**What to do**:
Audit and remove accumulated deprecated aliases across the codebase. Each alias requires a consumer check before removal.

**Locations**:
- `models/business/hours.py:80-85` -- 6 `_deprecated_alias` decorators
- `models/business/business.py:395-407` -- `reconciliations_holder` property
- `models/business/reconciliation.py:60-70` -- `reconciliations_holder` property
- `models/business/detection/facade.py:234-258` -- `detect_by_name()`
- `models/business/detection/config.py:223` -- `NAME_PATTERNS` dict
- `persistence/exceptions.py:256-303` -- `ValidationError` alias + metaclass
- `persistence/__init__.py:104` -- `ValidationError` re-export
- `models/task.py:78-121` -- deprecated Asana fields
- `models/custom_field_accessor.py:52` -- deprecated parameter
- `cache/integration/dataframe_cache.py:168` -- deprecated alias
- `dataframes/resolver/protocol.py:81-92`, `default.py:162-170` -- deprecated parameter

**Step-by-step**:
1. For each alias, grep the full codebase (src/ and tests/) for usages
2. If zero consumers remain: delete the alias
3. If consumers exist: migrate them to the modern equivalent, then delete
4. For external-facing aliases (models that may be used by other services): mark with `# EXTERNAL: audit before removal` and skip
5. Run full test suite after each batch of removals

**Risk mitigation**: Proceed in small batches. Remove aliases one category at a time (business models, persistence, dataframes). Commit between categories so rollback is granular.

**Definition of Done**:
- [ ] All aliases with zero internal consumers removed
- [ ] Remaining aliases (if any) annotated with reason for retention
- [ ] ~150 LOC removed
- [ ] All tests pass

### Task 2.5: Remove PipelineAutoCompletionService Wrapper (D-014)

**Size**: S (20-30 minutes)
**Confidence**: High
**Dependencies**: None

**What to do**:
Delete the `PipelineAutoCompletionService` wrapper class and update `engine.py` to import `CompletionService` directly.

**Files to change**:
- `src/autom8_asana/lifecycle/completion.py` -- Lines 102-135: delete class
- `src/autom8_asana/lifecycle/engine.py` -- Update import to use `CompletionService`

**Definition of Done**:
- [ ] `PipelineAutoCompletionService` class deleted
- [ ] `engine.py` imports `CompletionService` directly
- [ ] ~35 LOC removed
- [ ] All lifecycle tests pass

### Sprint 2 Summary

| Task | Item(s) | Size | LOC Impact |
|------|---------|------|------------|
| 2.1 | D-010 | S | ~0 (refactor) |
| 2.2 | D-011, D-035 | L | -30 |
| 2.3 | D-007 | M | -90 |
| 2.4 | D-017 | L | -150 |
| 2.5 | D-014 | S | -35 |
| **Total** | **6 items** | **2-3 days** | **-305 to -350** |

**Sprint 2 Acceptance Criteria**:
- [ ] Zero module-level `get_settings()` calls
- [ ] All `os.environ` access either routes through Settings or has explicit annotation
- [ ] Deprecated DI functions (`get_asana_pat`, `get_asana_client`) removed
- [ ] Deprecated aliases removed or annotated for retention
- [ ] `PipelineAutoCompletionService` removed
- [ ] Full test suite passes

---

## Sprint 3: Test Integrity

**Goal**: Restore CI signal integrity by fixing pre-existing failures and retargeting tests at dead code. Directly addresses stakeholder pain point #3 (test brittleness).

**Duration**: 2-3 developer-days
**Items**: D-029, D-026, D-027 (partial -- scope limited to Sprint 1 breakage)
**Combined Risk Score**: 33
**LOC Reduction**: ~500 (test LOC)
**Confidence**: Medium (D-029 requires investigation; D-026 depends on merged router being stable)
**Dependencies**: Sprint 1 must be complete (D-012 query router merge required for D-026)

### Task 3.1: Fix Pre-Existing Test Failures (D-029)

**Size**: M (4-8 hours)
**Confidence**: Low (unknown root cause -- investigation required)
**Dependencies**: None

**What to do**:
Investigate and fix the pre-existing assertion failures in `test_adversarial_pacing.py` and `test_paced_fetch.py`. These have been carried forward through multiple sprints. Either fix the underlying issue or quarantine with `@pytest.mark.skip` and a documented reason.

**Step-by-step**:
1. Run both test files in isolation with verbose output to capture exact failure messages
2. Determine if failures are: (a) stale assertions from code changes, (b) timing/race conditions, (c) environment-specific
3. For stale assertions: update expected values to match current behavior
4. For timing issues: add appropriate waits or make assertions time-insensitive
5. For environment issues: add skip conditions with `@pytest.mark.skipif`
6. If root cause is unclear after 4 hours: quarantine with `@pytest.mark.skip(reason="D-029: pre-existing failure, needs dedicated investigation")` and file a follow-up item

**Definition of Done**:
- [ ] Both test files either pass or are quarantined with documented reason
- [ ] CI no longer shows known failures masking regressions
- [ ] If quarantined: follow-up item created with diagnostic output

### Task 3.2: Retarget Dead-Code Tests to Merged Router (D-026)

**Size**: M (4-8 hours)
**Confidence**: Medium
**Dependencies**: Sprint 1 Task 1.2 (D-012 query router merge) must be complete

**What to do**:
The 34 test cases across `test_routes_query.py` and `test_routes_query_rows.py` that target dead/deprecated v1 code must be either migrated to test the merged router or deleted.

**Step-by-step**:
1. Categorize each test: (a) tests a behavior that still exists in merged router, (b) tests dead code
2. For category (a): rewrite to use merged router's handler, updating mock paths and assertions
3. For category (b): delete -- the code no longer exists
4. For the 14 tests of the deprecated `POST /v1/query/{entity_type}` endpoint: keep but retarget to the preserved deprecated endpoint in merged router
5. For the 20 tests of dead `query_rows` handler: delete
6. Run: `pytest tests/api/test_routes_query*.py -v`

**Risk mitigation**: Some test behaviors may be subtly different between v1 and v2 handlers. For each migrated test, verify it exercises the intended code path by temporarily adding a marker in the source and confirming the test hits it.

**Definition of Done**:
- [ ] Zero tests target the deleted `query_rows` handler
- [ ] Tests for deprecated v1 endpoint target the preserved endpoint in merged router
- [ ] Coverage on merged `query.py` handler has no regression
- [ ] ~500 LOC of test code removed or restructured
- [ ] All remaining tests pass

### Task 3.3: Mock Fixup Sweep (D-027, partial)

**Size**: S-M (2-4 hours)
**Confidence**: Medium
**Dependencies**: Sprints 1 and 2 complete

**What to do**:
This is NOT a full D-027 remediation (that is XL and deferred). This is a targeted sweep to fix any mock breakage caused by Sprint 1 pattern changes that was not caught during individual task execution. Focus on:
- Mock paths that reference `query_v2` (file renamed)
- Mock paths that reference old function signatures (Request vs RequestId)
- Tests that construct `Request` objects solely to pass to `raise_api_error`

**Definition of Done**:
- [ ] Full test suite passes with zero mock-path-related failures
- [ ] No test file references `query_v2` module
- [ ] Tests that needed `Request` objects solely for request_id now use string directly

### Sprint 3 Summary

| Task | Item(s) | Size | LOC Impact |
|------|---------|------|------------|
| 3.1 | D-029 | M | TBD |
| 3.2 | D-026 | M | -500 (test LOC) |
| 3.3 | D-027 (partial) | S-M | ~0 (test fixes) |
| **Total** | **3 items** | **2-3 days** | **~-500 test LOC** |

**Sprint 3 Acceptance Criteria**:
- [ ] CI runs clean -- zero pre-existing failures, zero known-dead-code tests
- [ ] All query tests target the merged `query.py` router
- [ ] No mock paths reference renamed/deleted modules
- [ ] Test count may decrease (dead-code tests removed) but coverage on active code is maintained or improved

---

## Sprint 4: Pipeline Convergence

**Goal**: Extract shared creation primitives and consolidate the dual-path automation architecture. Highest-ROI WS4 finding (DRY-001, ROI 13.5). Addresses pain point #2 (code bloat) and establishes transferable patterns for greenfield.

**Duration**: 5-8 developer-days
**Items**: D-023, D-033, D-022
**Combined Risk Score**: 41
**LOC Reduction**: ~900-1,500
**Confidence**: Low (significant architectural work -- add 50-100% buffer)
**Dependencies**: Sprints 1-2 complete (pattern conventions established)

**Note**: This is the first XL-effort sprint. WS6 plan (RF-004 through RF-007) provides the blueprint. This sprint executes that plan.

### Task 4.1: Extract Shared Functions from automation/seeding.py (D-023)

**Size**: S (1-2 hours)
**Confidence**: High (may already be partially done by WS6 RF-006)
**Dependencies**: None

**What to do**:
Promote private functions (`_get_field_attr`, `_normalize_custom_fields`) from `automation/seeding.py` to a public shared module (e.g., `core/fields.py`). Update imports in `lifecycle/seeding.py`.

**Definition of Done**:
- [ ] Shared functions in a public module (not prefixed with `_`)
- [ ] No private cross-package imports between lifecycle and automation
- [ ] All seeding tests pass

### Task 4.2: Extract Shared Creation Engine (D-033)

**Size**: XL (3-5 days)
**Confidence**: Low (add 75% buffer)
**Dependencies**: D-023 complete

**What to do**:
Extract the shared 7-step creation pipeline from `automation/pipeline.py` and `lifecycle/creation.py` into a shared creation engine. Both modules should delegate to this engine rather than implementing the steps independently.

**High-level approach** (per WS6 RF-004/RF-005 blueprint):
1. Identify the 7 shared creation steps (template discovery through assignee resolution)
2. Create `core/creation.py` (or similar) with a `CreationEngine` class
3. Express each step as a method with clear interfaces
4. Migrate `automation/pipeline.py` to delegate to `CreationEngine`
5. Migrate `lifecycle/creation.py` to delegate to `CreationEngine`
6. Reconcile seeding divergence (`FieldSeeder` vs `AutoCascadeSeeder`) -- both should be pluggable strategies
7. Comprehensive testing at each migration step

**Definition of Done**:
- [ ] Shared `CreationEngine` (or equivalent) exists with the 7 creation steps
- [ ] `automation/pipeline.py` delegates to shared engine
- [ ] `lifecycle/creation.py` delegates to shared engine
- [ ] Seeding is pluggable (both strategies work)
- [ ] Name generation regex exists in one place only
- [ ] ~600 LOC of duplication eliminated
- [ ] All pipeline and lifecycle tests pass

### Task 4.3: Consolidate Dual-Path Architecture (D-022)

**Size**: XL (2-3 days)
**Confidence**: Low (architectural change with wide blast radius)
**Dependencies**: D-033 complete

**What to do**:
With the shared creation engine in place, evaluate whether `automation/pipeline.py` can be fully absorbed into the lifecycle engine, or whether it should remain as a thin adapter. The goal is a single orchestration path with lifecycle as canonical.

**Note**: This task may be reduced in scope depending on Task 4.2 findings. If the shared engine sufficiently decouples the two paths, full consolidation may be deferred to a future sprint.

**Definition of Done**:
- [ ] Single canonical orchestration path (lifecycle engine)
- [ ] `automation/pipeline.py` either absorbed or reduced to thin adapter
- [ ] No duplicated orchestration logic
- [ ] All automation and lifecycle tests pass
- [ ] Architecture documented for greenfield transfer

### Sprint 4 Summary

| Task | Item(s) | Size | LOC Impact |
|------|---------|------|------------|
| 4.1 | D-023 | S | -30 |
| 4.2 | D-033 | XL | -600 |
| 4.3 | D-022 | XL | -300 to -900 |
| **Total** | **3 items** | **5-8 days** | **-900 to -1,500** |

**Sprint 4 Acceptance Criteria**:
- [ ] Shared creation engine exists and is used by both automation and lifecycle paths
- [ ] No private cross-package imports between lifecycle and automation
- [ ] Pipeline creation logic exists in exactly one place
- [ ] Seeding strategies are pluggable
- [ ] All tests pass
- [ ] Architecture patterns documented for greenfield reference

---

## Sprint 5: God Object Decomposition

**Goal**: Decompose the two largest classes in the codebase (DataServiceClient and SaveSession) into cohesive, maintainable units. Addresses pain point #2 (code bloat) and establishes structural patterns for greenfield.

**Duration**: 5-8 developer-days
**Items**: D-031, D-030, D-032, D-028
**Combined Risk Score**: 30
**LOC Impact**: ~4,000 LOC restructured (not reduced -- decomposition, not deletion)
**Confidence**: Low (add 75-100% buffer)
**Dependencies**: Sprints 1-4 complete (patterns and conventions established)

**Note**: This sprint restructures code without significant LOC reduction. The value is in maintainability, testability, and establishing decomposition patterns transferable to greenfield.

### Task 5.1: Extract Retry Callback Factory (D-031)

**Size**: L (8-12 hours)
**Confidence**: Medium
**Dependencies**: None (independent of full decomposition)

**What to do**:
Extract the repeated retry callback boilerplate from 5 endpoint methods in `DataServiceClient` into a callback factory. This is standalone prep work for the full decomposition.

**Files to change**:
- `src/autom8_asana/clients/data/client.py` -- Lines 1171-2120: 5 locations with near-identical callbacks

**Definition of Done**:
- [ ] Single callback factory replaces 5 instances of boilerplate
- [ ] Factory parameterized by log event name and error message prefix
- [ ] ~250 LOC reduced
- [ ] All DataServiceClient tests pass

### Task 5.2: DataServiceClient Decomposition (D-030)

**Size**: XL (3-5 days)
**Confidence**: Low
**Dependencies**: D-031 complete

**What to do**:
Decompose the 2,175 LOC DataServiceClient into cohesive modules. WS5-A plan provides the blueprint. Target structure:
- HTTP transport + retry logic (core client)
- Endpoint-specific request builders (per API endpoint)
- Response parsing and error handling
- Caching layer
- Metrics and PII redaction (cross-cutting)

**Definition of Done**:
- [ ] DataServiceClient decomposed into 3+ focused modules
- [ ] No single class exceeds 500 LOC
- [ ] C901 violations resolved (complexity < 15 per function)
- [ ] All existing tests pass (may need restructuring)
- [ ] Public API (method signatures) unchanged or adapter provided

### Task 5.3: SaveSession Decomposition (D-032)

**Size**: XL (2-3 days)
**Confidence**: Low
**Dependencies**: None (independent of D-030)

**What to do**:
Decompose SaveSession (1,853 LOC, 58 methods) into phase-specific handlers. The class already delegates to collaborators; extract the orchestration logic itself.

**Definition of Done**:
- [ ] SaveSession reduced to orchestration core
- [ ] Phase-specific logic extracted to handlers
- [ ] No single class exceeds 500 LOC
- [ ] All persistence tests pass

### Task 5.4: Test File Restructuring (D-028)

**Size**: L (dependent on D-030)
**Confidence**: Low
**Dependencies**: D-030 complete

**What to do**:
Restructure `test_client.py` (4,848 LOC) to mirror the decomposed source structure. This follows naturally from D-030.

**Definition of Done**:
- [ ] Test files mirror decomposed module structure
- [ ] No single test file exceeds 1,000 LOC
- [ ] Coverage maintained or improved

### Sprint 5 Summary

| Task | Item(s) | Size | LOC Impact |
|------|---------|------|------------|
| 5.1 | D-031 | L | -250 |
| 5.2 | D-030 | XL | restructure |
| 5.3 | D-032 | XL | restructure |
| 5.4 | D-028 | L | restructure |
| **Total** | **4 items** | **5-8 days** | **~4,000 restructured** |

**Sprint 5 Acceptance Criteria**:
- [ ] No class in the codebase exceeds 500 LOC
- [ ] DataServiceClient decomposed into focused modules
- [ ] SaveSession decomposed into phase handlers
- [ ] Test files restructured to mirror source
- [ ] All tests pass
- [ ] Decomposition patterns documented for greenfield

---

## Quick Wins Batch

Items that can be done in < 1 hour each. Suitable for warm-up at the start of a sprint, cool-down at the end, or between-sprint interstitial work. Not assigned to a numbered sprint -- pick them up opportunistically.

| ID | Title | Effort | LOC | Notes |
|----|-------|--------|-----|-------|
| D-016 | Commented-out metric imports | 5 min | -2 | Delete 2 commented lines. Trivial. |
| D-009 | Logging import inconsistency | 15 min | -10 | Change 5 imports from `autom8_asana.core.logging` to `autom8y_log`. |
| D-014 | Deprecated PipelineAutoCompletionService | 20 min | -35 | Remove wrapper, update 1 import. (Also in Sprint 2 Task 2.5 -- do it wherever it fits.) |
| D-010 | Module-level get_settings() calls | 30 min | ~0 | Move 4 module-level calls inside functions. (Also in Sprint 2 Task 2.1.) |
| D-006 | Narrow raise_api_error signature | 30 min | -10 | After D-005 is done. (Also in Sprint 1 Task 1.6.) |
| D-008 | Webhooks HTTPException fix | 45 min | ~0 | 3 raises to refactor. (Also in Sprint 1 Task 1.3.) |
| D-023 | Cross-module coupling fix | 45 min | -30 | Promote 2 private functions. May already be done by WS6. (Also in Sprint 4 Task 4.1.) |

**Note**: Items D-006, D-008, D-010, D-014, and D-023 appear in both the Quick Wins list and their respective sprints. If picked up as a quick win, mark the sprint task as complete. The Quick Wins list provides the standalone context needed to execute without reading the full sprint plan.

---

## Deferred Track

Items intentionally excluded from the 5-sprint plan with rationale and trigger conditions for revisiting.

| ID | Title | Rationale | Trigger to Revisit |
|----|-------|-----------|--------------------|
| D-002 | v1 query endpoint sunset | Calendar-gated: cannot remove until 2026-06-01. External consumer audit incomplete. | Sunset date reached AND external consumer migration confirmed. |
| D-003 | Legacy preload module | Active degraded-mode fallback. Cannot delete. XL effort to modernize with uncertain return. 613 LOC, complexity 23. | Production incident in fallback path, OR greenfield replaces preload entirely. |
| D-013 | type:ignore density in clients | Intentional design trade-off for @async_method decorator. Requires mypy plugin or different codegen -- architecture-level change. | Decision to change sync/async generation pattern, OR mypy plugin becomes available. |
| D-015 | UnitExtractor stub implementations | Awaiting team input on whether vertical_id and max_pipeline_stage columns are needed. | Team provides requirements for these columns, OR schema audit removes them. |
| D-020 | Side-effect import for bootstrap | Deferred per WS7 RF-009. Idempotency guard is sufficient safety net. Risk-to-reward ratio unfavorable. | Import ordering causes a production bug, OR explicit init is needed for greenfield. |
| D-021 | Barrel __init__.py files | WS7 RF-008 found most barrels are clean re-exports. Remaining concern (models/business) is subsumed by D-020. | D-020 is addressed, OR a barrel causes an import-time failure. |
| D-024 | Bidirectional resolver/strategy dependency | Valid Python pattern. Functional at runtime. Disproportionate effort for structural improvement. | Services layer refactoring (e.g., during god object decomposition in Sprint 5) makes extraction natural. |
| D-025 | Inline deferred imports (12+ instances) | Valid Python pattern. Architecture-level fix (interface extraction) is disproportionate. WS7 RF-011 reached same conclusion. | Major architectural restructuring makes dependency graph cleanup natural. |
| D-027 | Heavy mock usage (540 sites, full scope) | Test architecture issue. Cannot be addressed in a single sprint. Sprint 3 handles immediate breakage only. | Dedicated test architecture initiative, OR greenfield test strategy established. |
| D-034 | Broad exception catches (136 instances) | Many are intentionally annotated. Needs per-site audit. The highest-risk subset (12 bare-excepts in D-003) is deferred with D-003. | Per-site audit scoped as a dedicated task, OR D-003 modernization begins. |
| D-035 | Direct os.environ in Lambda handlers | Absorbed by D-011 (Sprint 2 Task 2.2). Listed here as deferred only if D-011 is descoped. | D-011 is descoped from Sprint 2, in which case handle Lambda handlers independently. |

---

## Success Metrics

### LOC Reduction Targets

| Sprint | Target LOC Reduction | Cumulative | Measurement |
|--------|---------------------|------------|-------------|
| Sprint 1 | >= 700 | 700 | `git diff --stat` against pre-sprint baseline |
| Sprint 2 | >= 300 | 1,000 | `git diff --stat` against Sprint 1 end |
| Sprint 3 | >= 400 (test LOC) | 1,400 | `git diff --stat` against Sprint 2 end |
| Sprint 4 | >= 600 | 2,000 | `git diff --stat` against Sprint 3 end |
| Sprint 5 | ~0 net (restructure) | 2,000 | LOC per class metric, not total LOC |
| **Total** | **~2,000 net reduction** | | Plus ~4,000 LOC restructured in place |

**Note on total vs addressable**: The ledger estimates 7,358 total addressable LOC. This plan targets ~2,000 net reduction (sprints 1-4) plus ~4,000 restructured (sprint 5). The remaining ~1,300 is in deferred items (D-002 sunset, D-003 modernization, D-034 audit).

### Pattern Consistency Metrics

| Metric | After Sprint 1 | After Sprint 2 | After All |
|--------|---------------|----------------|-----------|
| Routes using `Request.state` for request_id | 0 | 0 | 0 |
| Routes using per-exception-type error handling | 0 | 0 | 0 |
| Routes using raw `HTTPException` | 0 | 0 | 0 |
| Files with `request.app.state` access | 0 | 0 | 0 |
| Module-level `get_settings()` calls | unchanged | 0 | 0 |
| Unannotated `os.environ` direct access | unchanged | 0 | 0 |
| Deprecated DI functions exported | unchanged | 0 | 0 |
| Query router files (target: 1) | 1 | 1 | 1 |

**How to measure**: Run the following grep checks after each sprint (all should return 0 matches for their target sprint):
```bash
# After Sprint 1:
grep -rn "request\.state\." src/autom8_asana/api/routes/ | grep -v "test" | grep "request_id"
grep -rn "raise HTTPException" src/autom8_asana/api/routes/
grep -rn "request\.app\.state" src/autom8_asana/api/routes/
ls src/autom8_asana/api/routes/query_v2.py 2>/dev/null  # should not exist

# After Sprint 2:
grep -rn "get_settings()" src/autom8_asana/clients/ | grep -v "def " | grep -v "test"
grep -rn "os\.environ\|os\.getenv" src/autom8_asana/ | grep -v "BROAD-CATCH\|ENV-DIRECT\|test"
grep -n "get_asana_pat\|get_asana_client[^_]" src/autom8_asana/api/dependencies.py
```

### Test Health Indicators

| Metric | Before | After Sprint 3 | How to Measure |
|--------|--------|----------------|----------------|
| Pre-existing test failures | 2 files | 0 | `pytest --tb=no -q 2>&1 | grep FAILED` |
| Tests targeting dead code | 34 cases | 0 | Manual audit of test_routes_query*.py |
| CI noise ratio | >0 (known failures) | 0 | CI run with no known-failure noise |
| Mock paths referencing deleted modules | unknown | 0 | `grep -r "query_v2" tests/` |

---

## Risks and Mitigations

### Sprint 1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Mock breakage cascade (D-027) | High | Medium | Budget 1 day buffer. Fix mocks per-task. If cascade exceeds buffer, quarantine broken tests for Sprint 3. |
| Query router merge breaks endpoint registration | Medium | High | Test with full API suite before committing. Verify router order in `api/main.py`. Rollback: restore both files. |
| entity_write registry not available as Depends | Low | Medium | Create thin Depends wrapper over app.state access. Still better than inline access. |
| Error handling migration misses edge cases | Medium | Low | Each route file has different error shapes. Audit every except block individually. Keep handler-specific logic outside dict mapping. |

### Sprint 2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Deprecated alias removal breaks external consumer | Low | High | Grep entire codebase first. For any alias with uncertain consumers, keep with annotation. |
| Settings model changes break test fixtures | Medium | Low | Add new fields with defaults matching current env var defaults. Existing tests unchanged. |
| D-011 scope creep (20+ sites) | High | Medium | Time-box to 12 hours. If not complete, defer remaining sites with annotations. |

### Sprint 3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pre-existing test failures have deep root cause | Medium | Medium | Time-box investigation to 4 hours. If unresolved, quarantine with skip markers. |
| Test retargeting reveals coverage gaps on v2 handler | Medium | Low | Coverage gaps are better discovered than hidden. Add new tests for gaps found. |

### Sprint 4 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shared creation engine cannot reconcile seeding divergence | Medium | High | Spike first (2-4 hours) to validate that both seeding strategies can plug into shared engine. If not, descope to shared steps only (exclude seeding). |
| Dual-path consolidation has hidden consumers | Medium | Medium | Grep for all imports from `automation/pipeline.py`. Map every consumer before starting. |
| Effort estimate too low (XL + XL) | High | Medium | Plan for 8 days, accept 5 as optimistic. If at day 6 with D-022 not started, defer D-022 to follow-up sprint. |

### Sprint 5 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Decomposition changes public API surface | Medium | High | Maintain backward-compatible facade during transition. Deprecate old imports after migration. |
| Test restructuring takes longer than source decomposition | High | Medium | Accept 1:1 ratio of source:test effort. Budget accordingly. |
| God object decomposition reveals hidden coupling | Medium | Medium | Extract incrementally. Start with D-031 (callback factory) to validate approach before full decomposition. |

### Cross-Sprint Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sprint 1 pattern changes destabilize Sprints 2-3 | Low | High | Sprint 1 must achieve green CI before Sprint 2 begins. Sprint 2 can overlap only if on separate modules. |
| Total effort exceeds 26 days | Medium | Medium | Sprints 4-5 are the most likely to overrun. Plan checkpoints at day 3 of each. If behind, reduce scope rather than rush. |
| New debt discovered during remediation | High | Low | Route back to Debt Collector for cataloging. Do not scope-creep current sprints. |

---

## Capacity Model: What-If Scenarios

### Scenario A: Single Developer, Full-Time

| Sprint | Duration | Running Total |
|--------|----------|---------------|
| Sprint 1 | 6 days (4 base + 2 buffer) | 6 days |
| Sprint 2 | 3 days | 9 days |
| Sprint 3 | 3 days | 12 days |
| Sprint 4 | 8 days | 20 days |
| Sprint 5 | 8 days | 28 days |
| **Total** | **28 working days** | ~6 weeks |

### Scenario B: Two Developers, Full-Time

| Sprint | Duration | Notes |
|--------|----------|-------|
| Sprint 1 + Sprint 2 | 6 days (parallel) | Dev A: Sprint 1, Dev B: Sprint 2 |
| Sprint 3 | 3 days (one dev, other on Sprint 4 spike) | Sprint 3 needs Sprint 1 done |
| Sprint 4 | 6 days (both devs) | Pair on architectural work |
| Sprint 5 | 6 days (parallel: D-030 and D-032 are independent) | Dev A: DataServiceClient, Dev B: SaveSession |
| **Total** | **~21 working days** | ~4 weeks |

### Scenario C: Sprints 1-3 Only (Aggressive Timebox)

If only 2 weeks are available, execute Sprints 1-3 for maximum ROI:
- ~1,500 LOC reduction
- Pattern consistency achieved
- CI signal restored
- Sprints 4-5 become backlog items with documented plans

---

## Appendix: Item-to-Sprint Mapping

Complete mapping of all 35 ledger items to their sprint (or deferred status).

| ID | Title | Sprint | Task |
|----|-------|--------|------|
| D-001 | Dead v1 query_rows handler | Sprint 1 | 1.2 (absorbed by D-012) |
| D-002 | v1 query endpoint sunset | Deferred | Calendar-gated (2026-06-01) |
| D-003 | Legacy preload module | Deferred | Active fallback, XL effort |
| D-004 | Error handling pattern divergence | Sprint 1 | 1.7 |
| D-005 | DI wiring inconsistency | Sprint 1 | 1.1 |
| D-006 | raise_api_error overloaded parameter | Sprint 1 | 1.6 |
| D-007 | Deprecated DI dependencies exported | Sprint 2 | 2.3 |
| D-008 | Webhooks raw HTTPException | Sprint 1 | 1.3 |
| D-009 | Logging import inconsistency | Quick Win | -- |
| D-010 | Module-level get_settings() calls | Sprint 2 | 2.1 |
| D-011 | Direct os.environ bypassing Settings | Sprint 2 | 2.2 |
| D-012 | v1/v2 query router consolidation | Sprint 1 | 1.2 |
| D-013 | type:ignore density in clients | Deferred | Intentional design |
| D-014 | Deprecated PipelineAutoCompletionService | Sprint 2 | 2.5 |
| D-015 | UnitExtractor stub implementations | Deferred | Awaiting team input |
| D-016 | Commented-out metric imports | Quick Win | -- |
| D-017 | Deprecated aliases and shims | Sprint 2 | 2.4 |
| D-018 | entity_write.py inline app.state access | Sprint 1 | 1.4 |
| D-019 | resolver.py no DI | Sprint 1 | 1.5 |
| D-020 | Side-effect import for bootstrap | Deferred | Per WS7 RF-009 |
| D-021 | Barrel __init__.py files | Deferred | Per WS7 RF-008 |
| D-022 | Dual-path automation architecture | Sprint 4 | 4.3 |
| D-023 | Cross-module coupling | Sprint 4 | 4.1 |
| D-024 | Bidirectional resolver/strategy dep | Deferred | Valid pattern |
| D-025 | Inline deferred imports | Deferred | Architecture-level |
| D-026 | Tests targeting dead v1 code | Sprint 3 | 3.2 |
| D-027 | Heavy mock usage (full scope) | Deferred | Sprint 3 handles partial |
| D-028 | Largest test file | Sprint 5 | 5.4 |
| D-029 | Pre-existing test failures | Sprint 3 | 3.1 |
| D-030 | God object: DataServiceClient | Sprint 5 | 5.2 |
| D-031 | Retry callback boilerplate | Sprint 5 | 5.1 |
| D-032 | God object: SaveSession | Sprint 5 | 5.3 |
| D-033 | Pipeline creation logic duplicated | Sprint 4 | 4.2 |
| D-034 | Broad exception catches | Deferred | Needs per-site audit |
| D-035 | Direct os.environ in Lambda handlers | Sprint 2 | 2.2 (absorbed by D-011) |

---

## Handoff Notes

**For Debt Collector**: During Sprint 1 execution, expect discovery of new debt related to mock patterns (D-027 derivatives). During Sprint 4, expect discovery of undocumented coupling between automation and lifecycle modules. Route findings back through the ledger process.

**For Risk Assessor**: After Sprint 1 completion, reassess D-027 (mock usage) risk score -- it may decrease if pattern unification reduces mock surface area. After Sprint 4, reassess D-022 if full consolidation was deferred.

**For Executing Engineers**: Sprint 1 is designed for confident execution with well-understood scope. Sprints 4-5 have low confidence estimates -- plan spike time before committing to full scope. The Quick Wins batch is available for onboarding or between-sprint breathing room.
