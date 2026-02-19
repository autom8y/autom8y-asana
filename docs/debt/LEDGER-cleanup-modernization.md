# Debt Ledger: Cleanup & Modernization Sprint

**Audit date**: 2026-02-18
**Scope**: `src/autom8_asana/` (entire tree -- 386 files, ~111K LOC)
**Auditor**: debt-collector agent
**Baseline**: SMELL-REPORT-WS4.md (25 findings, 2026-02-17)
**Carry-forward**: Sprint 3 deferred items (3 confirmed)

---

## Table of Contents

1. [Sprint 3 Carry-Forward Items](#sprint-3-carry-forward)
2. [Pattern Inconsistencies](#pattern-inconsistencies)
3. [Code Debt](#code-debt)
4. [Architecture Debt](#architecture-debt)
5. [Test Debt](#test-debt)
6. [Infrastructure / Design Debt](#infrastructure--design-debt)
7. [WS4 Baseline Status](#ws4-baseline-status)
8. [Summary Statistics](#summary-statistics)
9. [Audit Limitations](#audit-limitations)

---

## Sprint 3 Carry-Forward

### D-001: Dead v1 `query_rows` handler [Sprint-3]

- **Location**: `src/autom8_asana/api/routes/query.py:239-369`
- **Category**: Code > Dead Code
- **Description**: The v1 `query_rows` handler is shadowed by v2 after the QW-6 router registration fix (`api/main.py:184` registers v2 first). This handler is unreachable -- FastAPI matches the first registered route for `POST /v1/query/{entity_type}/rows`. 130 LOC of dead code.
- **Estimated LOC impact**: 130 (removal)
- **Related**: D-002, D-003, D-005

### D-002: v1 query endpoint sunset -- full v1 router removal [Sprint-3]

- **Location**: `src/autom8_asana/api/routes/query.py` (entire file, 369 LOC)
- **Category**: Code > Dead Code
- **Description**: Per V1-SUNSET-INVENTORY.md, the v1 query router contains two endpoints: (a) `POST /v1/query/{entity_type}` (deprecated, sunset 2026-06-01) and (b) the dead `query_rows` handler (D-001). After sunset, the entire v1 router can be removed. The deprecated endpoint is the only one with no v2 equivalent -- callers must migrate from flat `where` equality filtering to `/rows` predicate trees. Also includes 3 request/response models (`QueryRequest`, `QueryMeta`, `QueryResponse`) that exist only for v1.
- **Estimated LOC impact**: 369 (full file removal at sunset)
- **Related**: D-001, D-003, D-004

### D-003: Legacy preload module (active fallback) [Sprint-3]

- **Location**: `src/autom8_asana/api/preload/legacy.py` (613 LOC, complexity 23)
- **Category**: Design > Active Legacy
- **Description**: Confirmed as active degraded-mode fallback per stakeholder. Cannot be deleted, but represents significant design debt: 613 LOC of high-complexity code (cyclomatic 23) with 12 preserved bare-except sites tagged for I6 exception narrowing. No modernization path planned. Progressive preload (`progressive.py`, 508 LOC, complexity 35) is the primary path but falls back to legacy on failure.
- **Estimated LOC impact**: 613 (cannot remove, modernization target)
- **Related**: D-021 (WS4 CX-003/CX-006)

---

## Pattern Inconsistencies

### D-004: Error handling -- v1 per-exception-type vs v2 dict-mapping style [PRIORITY]

- **Location**: Multiple route files (see below)
- **Category**: Pattern > Error Handling
- **Description**: Two distinct error handling patterns coexist in the API routes:

  **v2 pattern (canonical)**: `query_v2.py:43-58` uses `_ERROR_STATUS` dict mapping + single `_raise_query_error()` function. Catches `QueryEngineError` base class once, maps to status via dict lookup. ~15 LOC for all error handling.

  **v1 pattern (legacy)**: `query.py:306-352` catches 6 individual exception types (`QueryTooComplexError`, `UnknownFieldError`, `InvalidOperatorError`, `CoercionError`, `UnknownSectionError`, `CacheNotWarmError`) with separate `except` blocks each calling `raise_api_error()` with hand-assembled error dicts. ~50 LOC for equivalent error handling.

  Files using v1 pattern:
  - `query.py` (6 separate except blocks)
  - `entity_write.py:211-294` (8 separate except blocks, uses `Request` object)
  - `resolver.py:220-370` (8+ separate except blocks, uses `Request` object)
  - `webhooks.py:139-165` (raw `HTTPException` raises, no `raise_api_error`)

  Files using v2 pattern:
  - `query_v2.py` (dict-mapping)
  - `tasks.py` (uses `raise_service_error` consistently)
  - `sections.py` (uses `raise_service_error` consistently)
  - `dataframes.py` (uses `raise_service_error` consistently)

- **Estimated LOC impact**: ~200 (consolidation across 4 files)
- **Related**: D-005, D-006

### D-005: DI wiring -- `Request` object vs `RequestId` dependency [PRIORITY]

- **Location**: Multiple route files
- **Category**: Pattern > Dependency Injection
- **Description**: Two DI patterns coexist for obtaining the request ID:

  **Modern pattern** (`Depends + Annotated`): Routes use `RequestId` type alias (`Annotated[str, Depends(get_request_id)]`) and pass the string directly to `raise_api_error(request_id, ...)` and `raise_service_error(request_id, ...)`. Used in: `query_v2.py`, `tasks.py`, `sections.py`, `dataframes.py`, `projects.py`, `users.py`, `workspaces.py`, `resolver_schema.py`.

  **Legacy pattern** (`request.state`): Routes accept `Request` and call `getattr(request.state, "request_id", "unknown")` inline. Pass the `Request` object to `raise_api_error(request, ...)`. Used in: `query.py`, `entity_write.py:131`, `resolver.py:152`.

  `raise_api_error()` and `raise_service_error()` both accept `Request | str` via a union overload (`request_or_id`), which enables this inconsistency to persist silently.

  Additionally, `entity_write.py` accesses `request.app.state` to get `entity_write_registry` and `mutation_invalidator` instead of using FastAPI `Depends` -- bypassing the DI system entirely.

- **Estimated LOC impact**: ~60 (signature changes across 3 route files)
- **Related**: D-004, D-006

### D-006: `raise_api_error()` overloaded `Request | str` first parameter

- **Location**: `src/autom8_asana/api/errors.py:86-131`
- **Category**: Pattern > Error Handling
- **Description**: `raise_api_error()` accepts either a `Request` object or a `str` request ID as its first parameter. This union type enables the DI inconsistency in D-005 to exist without type errors. Once all routes are migrated to `RequestId` (D-005), this should accept only `str`.
- **Estimated LOC impact**: ~10
- **Related**: D-004, D-005

### D-007: Deprecated DI dependencies still exported [PRIORITY]

- **Location**: `src/autom8_asana/api/dependencies.py:290-377`
- **Category**: Pattern > Dependency Injection
- **Description**: Two deprecated dependency functions are still exported and potentially in use:
  - `get_asana_pat()` (line 290) -- marked "DEPRECATED: Use get_auth_context()"
  - `get_asana_client()` (line 352) -- marked "DEPRECATED: Use get_asana_client_from_context()"

  Both are exported in `__all__` (line 587-588) along with their type aliases (`AsanaPAT`, `AsanaClientDep`). The modern equivalents (`get_auth_context`, `get_asana_client_from_context`) handle dual-mode auth (JWT + PAT). These legacy deps only handle PAT mode.

  `get_asana_pat()` duplicates the Bearer token extraction logic already in `_extract_bearer_token()` (~30 lines of identical validation code).
- **Estimated LOC impact**: ~90 (two deprecated functions + duplicate validation)
- **Related**: D-005

### D-008: webhooks route uses raw `HTTPException` instead of `raise_api_error` [PRIORITY]

- **Location**: `src/autom8_asana/api/routes/webhooks.py:139-165`
- **Category**: Pattern > Error Handling
- **Description**: The webhooks route raises `HTTPException` directly in `verify_webhook_token()` instead of using the centralized `raise_api_error()` helper. This means webhook error responses lack the consistent error format (no `request_id` in the response body). Three separate `HTTPException` raises for: token not configured (503), token missing (401), token invalid (401).
- **Estimated LOC impact**: ~30 (refactor to use raise_api_error)
- **Related**: D-004

### D-009: Logging import source inconsistency

- **Location**: Multiple files (see below)
- **Category**: Pattern > Logging
- **Description**: Two logging import sources coexist:
  - **Primary** (~145 files): `from autom8y_log import get_logger`
  - **Legacy** (~5 files): `from autom8_asana.core.logging import get_logger`

  Files using legacy import: `api/middleware.py:26`, `core/__init__.py:7`, `api/lifespan.py:18`, and polling subsystem files (`polling/polling_scheduler.py`, `polling/structured_logger.py`, `polling/cli.py`).

  `autom8_asana.core.logging` itself delegates to `autom8y_log`, so this is a cosmetic inconsistency. However, it adds indirection and creates confusion about the canonical import path.
- **Estimated LOC impact**: ~10 (import changes)
- **Related**: None

### D-010: Config access pattern -- module-level `get_settings()` calls

- **Location**: `src/autom8_asana/clients/sections.py:27`, `clients/users.py:22`, `clients/custom_fields.py:26`, `clients/projects.py:22`
- **Category**: Pattern > Configuration
- **Description**: Four client files call `get_settings()` at **module level** (import time) to extract cache TTL values:
  ```python
  SECTION_CACHE_TTL = get_settings().cache.ttl_section  # sections.py:27
  ```
  This means Settings are evaluated at import time, before any test can override them. If environment variables are set after import, these stale values persist. The rest of the codebase accesses settings lazily (inside functions/methods).
- **Estimated LOC impact**: ~8
- **Related**: D-011

### D-011: Direct `os.environ` / `os.getenv` access bypassing Settings

- **Location**: Multiple files (20+ call sites)
- **Category**: Pattern > Configuration
- **Description**: At least 20 call sites read environment variables directly via `os.environ.get()` or `os.getenv()` instead of going through the `Settings` pydantic model (`settings.py`). Key offenders:
  - `clients/data/config.py:242-306` (4 calls for `AUTOM8_DATA_URL`, `AUTOM8_DATA_CACHE_TTL`)
  - `clients/data/client.py:548` (feature flag env var)
  - `lambda_handlers/cloudwatch.py:19-20` (namespace, environment)
  - `lambda_handlers/cache_warmer.py:378` (S3 bucket)
  - `lambda_handlers/checkpoint.py:155` (S3 bucket)
  - `cache/dataframe/decorator.py:84` (bypass flag)
  - `cache/dataframe/tiers/memory.py:34` (container memory)
  - `cache/integration/batch.py:95-100` (ECS metadata)
  - `dataframes/builders/progressive.py:270` (feature flag)
  - `models/business/registry.py:282` (registry config)
  - `entrypoint.py:40-41` (host, port)

  This undermines the single-source-of-truth design of `settings.py` and makes configuration hard to test (must set env vars rather than override Settings).
- **Estimated LOC impact**: ~30 (route through Settings)
- **Related**: D-010

---

## Code Debt

### D-012: v1/v2 query routers -- consolidation target [PRIORITY]

- **Location**: `src/autom8_asana/api/routes/query.py` (369 LOC), `query_v2.py` (191 LOC)
- **Category**: Code > Duplication
- **Description**: Per stakeholder decision, the v1 and v2 query routers should be merged into a single `query.py`. Currently:
  - v2 is the active router for `/rows` and `/aggregate` (registered first in `main.py:184`)
  - v1 contributes only the deprecated `POST /{entity_type}` endpoint (sunset 2026-06-01)
  - v1's `query_rows` handler (D-001) is dead code
  - The naming convention (`query_v2.py`) should become just `query.py` per stakeholder decision to strip "v2" naming

  After merge: single file, v2 error handling pattern (dict-mapping), v2 DI pattern (RequestId), with the legacy endpoint preserved behind deprecation headers until sunset.
- **Estimated LOC impact**: ~370 (remove v1 file, merge deprecated endpoint into v2)
- **Related**: D-001, D-002, D-004, D-005

### D-013: `type: ignore` suppression density in client files

- **Location**: `src/autom8_asana/clients/*.py` (132 `type: ignore` comments)
- **Category**: Code > Type Safety
- **Description**: 132 `type: ignore` comments across the `clients/` directory, concentrated in files using the `@overload` + `@async_method` decorator pattern. The primary suppressions are:
  - `# type: ignore[no-overload-impl]` -- mypy cannot see the impl behind `@async_method`
  - `# type: ignore[arg-type, operator, misc]` -- type mismatch in decorator signatures
  - `# type: ignore[attr-defined, no-any-return]` -- delegation methods on `tasks.py`

  This is a known trade-off for the sync/async overload pattern (WS4 DRY-006). The `@async_method` decorator generates sync wrappers at runtime, which mypy cannot verify statically. Reducing these requires either a mypy plugin for the decorator or a different code generation approach.

  **Note**: This may be intentional design, not debt. Catalog for awareness.
- **Estimated LOC impact**: N/A (architecture-level change needed)
- **Related**: D-022 (WS4 DRY-006)

### D-014: Deprecated `PipelineAutoCompletionService` wrapper [CLOSED]

- **Status**: CLOSED (2026-02-19). Class already removed from `lifecycle/completion.py`. Confirmed zero references in `src/`.
- **Location**: `src/autom8_asana/lifecycle/completion.py` (no longer exists)
- **Category**: Code > Dead Code
- **Description**: `PipelineAutoCompletionService` wrapper was removed during the cleanup-modernization initiative. Debt item resolved.
- **Related**: None

### D-015: Stub implementations in `UnitExtractor` with TODO markers

- **Location**: `src/autom8_asana/dataframes/extractors/unit.py:66-118`
- **Category**: Code > Incomplete Implementation
- **Description**: Two stub methods that always return `None`:
  - `_extract_vertical_id()` (line 71) -- TODO: derive from Vertical model
  - `_extract_max_pipeline_stage()` (line 97) -- TODO: derive from UnitHolder model

  Both are marked "deferred pending autom8 team input." If these columns are populated downstream (e.g., in the schema), they always contain `None`, which may cause silent data quality issues.
- **Estimated LOC impact**: ~50 (implement or remove columns)
- **Related**: None

### D-016: Commented-out metric definition imports

- **Location**: `src/autom8_asana/metrics/definitions/__init__.py:14-15`
- **Category**: Code > Dead Code
- **Description**: Two commented-out imports for unimplemented metric definitions:
  ```python
  # from autom8_asana.metrics.definitions import unit  # noqa: F401
  # from autom8_asana.metrics.definitions import business  # noqa: F401
  ```
  Only `offer` metrics are implemented. These commented lines indicate planned but unstarted work.
- **Estimated LOC impact**: 2 (remove or implement)
- **Related**: None

### D-017: Deprecated aliases and backward-compatibility shims (accumulated)

- **Location**: Multiple files
- **Category**: Code > Dead Code
- **Description**: Accumulated deprecated aliases across the codebase:
  - `models/business/hours.py:80-85` -- 6 `_deprecated_alias` decorators for `monday_hours` -> `monday` etc. (per ADR-0114)
  - `models/business/business.py:395-407` -- `reconciliations_holder` property with deprecation warning
  - `models/business/reconciliation.py:60-70` -- `reconciliations_holder` property
  - `models/business/detection/facade.py:234-258` -- `detect_by_name()` deprecated for `detect_entity_type()`
  - `models/business/detection/config.py:223` -- deprecated `NAME_PATTERNS` dict kept for backward compat
  - `persistence/exceptions.py:256-303` -- `ValidationError` deprecated alias with custom metaclass
  - `persistence/__init__.py:104` -- `ValidationError` re-exported for backward compat
  - `models/task.py:78-121` -- `num_hearts`, `hearted`, `hearts` deprecated Asana fields
  - `models/custom_field_accessor.py:52` -- deprecated `normalize=False` parameter
  - `cache/integration/dataframe_cache.py:168` -- deprecated alias comment
  - `dataframes/resolver/protocol.py:81-92`, `default.py:162-170` -- deprecated `expected_type` parameter

  Each shim adds LOC, import surface, and cognitive load.
- **Estimated LOC impact**: ~150 (collective removal, requires consumer audit)
- **Related**: D-023 (WS4 DC-002 resolved)

### D-018: `entity_write.py` -- inline `request.app.state` access for registry and invalidator

- **Location**: `src/autom8_asana/api/routes/entity_write.py:146-198`
- **Category**: Code > Shortcuts
- **Description**: `entity_write.py` accesses `request.app.state.entity_write_registry` and `request.app.state.mutation_invalidator` directly instead of using FastAPI Depends. It also does inline imports of `AsanaClient` and `get_bot_pat` inside the handler body. This route should use the established DI pattern:
  - `MutationInvalidatorDep` (already exists in `dependencies.py`)
  - A new `EntityWriteRegistryDep` dependency
  - `AsanaClientDualMode` or equivalent for client creation

  The inline `get_bot_pat()` call duplicates logic already in `get_auth_context()`.
- **Estimated LOC impact**: ~40 (refactor to Depends)
- **Related**: D-005, D-007

### D-019: `resolver.py` -- no DI for entity resolution, uses `Request` directly

- **Location**: `src/autom8_asana/api/routes/resolver.py:149-154`
- **Category**: Code > Shortcuts
- **Description**: The resolver route accepts `Request` directly and uses neither `RequestId` nor the standard `EntityServiceDep`. It does its own entity type validation (lines 97-141) with a `get_supported_entity_types()` function that has multiple fallback layers and broad exception catches. Modern routes use `EntityServiceDep` for this. Also accesses `AsanaClient` by constructing it inline with `get_bot_pat()` instead of via `AsanaClientDualMode`.
- **Estimated LOC impact**: ~50 (migrate to EntityServiceDep + RequestId)
- **Related**: D-005, D-018

---

## Architecture Debt

### D-020: Side-effect import for business model bootstrap [WS4: AR-001 / IM-001] [open]

- **Location**: `src/autom8_asana/api/main.py:35`, `src/autom8_asana/models/business/__init__.py:62`
- **Category**: Architecture > Import Side Effects
- **Description**: `api/main.py` contains a critical side-effect import:
  ```python
  import autom8_asana.models.business  # noqa: F401 - side effect import for bootstrap
  ```
  This triggers `register_all_models()` which populates `ProjectTypeRegistry` for Tier 1 detection. The barrel `__init__.py` (239 LOC, 87 `__all__` entries) calls this at import time. Any `from autom8_asana.models.business import X` triggers the full registration cascade, creating fragile import ordering. Tests depend on this side effect.
- **Estimated LOC impact**: ~60 (extract to explicit init)
- **Related**: D-021

### D-021: Barrel `__init__.py` files with non-trivial logic [WS4: AR-001] [open]

- **Location**: Multiple barrel files
- **Category**: Architecture > Module Structure
- **Description**: Four barrel files exceed 100 LOC with non-trivial logic:
  - `models/business/__init__.py` -- 239 LOC, calls `register_all_models()`, uses `# ruff: noqa: E402`
  - `persistence/__init__.py` -- 157 LOC, re-exports deprecated `ValidationError`
  - `automation/__init__.py` -- 118 LOC, uses `__getattr__` for lazy `PipelineConversionRule` import (circular break)
  - `lifecycle/__init__.py` -- 113 LOC

  These go beyond simple re-exports and contain load-bearing logic.
- **Estimated LOC impact**: 627 (total across 4 files; refactor target)
- **Related**: D-020

### D-022: Dual-path automation architecture [WS4: AR-002] [open]

- **Location**: `src/autom8_asana/automation/pipeline.py` (896 LOC), `src/autom8_asana/lifecycle/engine.py` (890 LOC) + `lifecycle/creation.py` (778 LOC)
- **Category**: Architecture > Dual Path
- **Description**: Two separate systems orchestrate pipeline transitions:
  - **Legacy** (`automation/`): `PipelineConversionRule` -- explicit field lists, single transition type
  - **New** (`lifecycle/`): `LifecycleEngine` -- YAML-driven, multi-stage, zero-config seeding

  Both exist simultaneously. `lifecycle/seeding.py:AutoCascadeSeeder` imports from `automation/seeding.py:FieldSeeder` (private cross-package import). This was the highest-ROI WS4 finding (DRY-001, ROI 13.5). WS6 (Pipeline Creation Convergence) was planned but not yet executed.
- **Estimated LOC impact**: ~900 (consolidation of pipeline.py into lifecycle engine)
- **Related**: D-024 (DRY-001), D-025

### D-023: Cross-module coupling -- lifecycle imports from automation internals [WS4: BOUNDARY-001] [open]

- **Location**: `src/autom8_asana/lifecycle/seeding.py` imports from `src/autom8_asana/automation/seeding.py`
- **Category**: Architecture > Coupling
- **Description**: `lifecycle/seeding.py` imports private functions (`_get_field_attr`, `_normalize_custom_fields`) from `automation/seeding.py`. This creates tight coupling between the new and legacy automation paths. These should be extracted to a shared module (e.g., `core/fields.py`) or the lifecycle module should have its own implementation.
- **Estimated LOC impact**: ~30 (extract shared functions)
- **Related**: D-022

### D-024: Bidirectional dependency -- services/resolver <-> services/universal_strategy [WS4: AR-004] [open]

- **Location**: `src/autom8_asana/services/universal_strategy.py:156,326` and `src/autom8_asana/services/resolver.py:690`
- **Category**: Architecture > Circular Dependency
- **Description**: `universal_strategy.py` has inline imports from `resolver.py` (lines 156, 326), while `resolver.py:690` (`get_strategy`) imports from `universal_strategy.py`. This bidirectional dependency is broken at runtime via inline imports but indicates a structural coupling issue in the services layer.
- **Estimated LOC impact**: ~20 (extract shared interface)
- **Related**: None

### D-025: Inline deferred imports for circular avoidance (12+ instances) [WS4: IM-003] [open]

- **Location**: Multiple files in `services/`, `persistence/`, `automation/`
- **Category**: Architecture > Import Structure
- **Description**: 12+ instances of function-body imports used to avoid circular dependencies:
  - `services/universal_strategy.py:156,183`
  - `services/resolver.py:344,569`
  - `persistence/session.py:191`
  - `api/errors.py:157` (TYPE_CHECKING workaround)
  - Various other locations

  While valid Python, this density indicates the module dependency graph has structural issues.
- **Estimated LOC impact**: N/A (architecture-level)
- **Related**: D-024

---

## Test Debt

### D-026: Tests targeting dead/deprecated v1 query code

- **Location**: `tests/api/test_routes_query.py`, `tests/api/test_routes_query_rows.py`
- **Category**: Test > Targeting Dead Code
- **Description**: Per V1-SUNSET-INVENTORY.md:
  - `test_routes_query.py` -- 14 test cases targeting the deprecated `POST /v1/query/{entity_type}` endpoint
  - `test_routes_query_rows.py` -- 20 test cases targeting the v1 `query_rows` handler (D-001, dead code after QW-6)

  The `test_routes_query_rows.py` tests pass only because they instantiate the v1 router directly, bypassing the v2-first registration. They test unreachable code paths. Should be migrated to test v2 handler (`query_v2.py`) directly, or deleted after v1 sunset.
- **Estimated LOC impact**: ~500+ (across two test files, migrate or remove)
- **Related**: D-001, D-002, D-012

### D-027: Heavy mock usage in API tests (540 mock call sites)

- **Location**: `tests/api/` (all files), `tests/unit/api/`
- **Category**: Test > Brittleness
- **Description**: 540 mock-related call sites (`@patch`, `MagicMock`, `AsyncMock`, `monkeypatch`) across API test files. Key concerns:
  - Tests mock internal implementation details (e.g., patching `autom8_asana.api.routes.query.AsanaClient` directly)
  - Tests construct `Request` objects with manually set `request.state.request_id` (14 instances in `test_dependencies.py`, `test_integration.py`) -- tightly coupled to middleware internals
  - Tests that mock the entire service layer obscure integration issues

  This level of mocking makes tests brittle to refactoring (e.g., renaming an internal module breaks mock paths).
- **Estimated LOC impact**: N/A (test architecture issue)
- **Related**: D-005

### D-028: Largest test file -- `test_client.py` at 4,848 LOC

- **Location**: `tests/unit/clients/data/test_client.py` (4,848 LOC)
- **Category**: Test > Maintainability
- **Description**: The DataServiceClient test file is the largest in the codebase at 4,848 LOC. Given that the source file (`clients/data/client.py`) is itself a god object (WS4 CX-001, 2,175 LOC), the test file mirrors its complexity. When the client is decomposed, these tests must also be restructured.
- **Estimated LOC impact**: N/A (follows source refactoring)
- **Related**: D-030 (WS4 CX-001)

### D-029: Pre-existing test failures

- **Location**: `test_adversarial_pacing.py`, `test_paced_fetch.py`
- **Category**: Test > Broken
- **Description**: Two test files have pre-existing checkpoint assertion failures noted in both WS4 and WS5 checkpoints. These have been carried forward through multiple sprints without resolution.
- **Estimated LOC impact**: Unknown
- **Related**: None

---

## Infrastructure / Design Debt

### D-030: God object -- DataServiceClient (2,175 LOC, 49 methods) [WS4: CX-001] [open]

- **Location**: `src/autom8_asana/clients/data/client.py` (2,175 LOC)
- **Category**: Design > God Object
- **Description**: Single class spanning ~2,015 lines with 49 methods. Mixes HTTP transport, retry logic, circuit breaker, caching, PII redaction, metrics, response parsing, and 5 separate API endpoints. Three C901 violations: `_execute_batch_request` (complexity 29), `_execute_insights_request` (complexity 22), `_execute_with_retry` (complexity 12). High parameter counts: `get_insights_async` (13 params), `handle_error_response` (16 params). WS5-A (DataServiceClient Decomposition) was planned but not yet executed.
- **Estimated LOC impact**: 2,175 (decomposition target)
- **Related**: D-031, D-032, D-028

### D-031: Retry callback boilerplate repeated 5x in DataServiceClient [WS4: DRY-002] [open]

- **Location**: `src/autom8_asana/clients/data/client.py` (5 locations, lines 1171-2120)
- **Category**: Code > Duplication
- **Description**: Each of the 5 endpoint methods defines 2-3 nested callback functions (`_on_retry`, `_on_timeout_exhausted`, `_on_http_error`) with near-identical structure. Only variation is log event name and error message prefix. A callback factory could replace all 5 instances.
- **Estimated LOC impact**: ~250 (extracted to factory)
- **Related**: D-030

### D-032: God object -- SaveSession (1,853 LOC, 58 methods) [WS4: CX-002] [open]

- **Location**: `src/autom8_asana/persistence/session.py` (1,853 LOC)
- **Category**: Design > God Object
- **Description**: Single class with 58 methods spanning ~1,786 lines. Mixes entity tracking, dirty detection, dependency ordering, CRUD execution, cascade execution, healing execution, automation execution, event hooks, action building, and cache invalidation. Already delegates to collaborators but the orchestration logic itself could be extracted into phase-specific handlers.
- **Estimated LOC impact**: 1,853 (decomposition target)
- **Related**: None

### D-033: Pipeline creation logic duplicated [WS4: DRY-001] [open]

- **Location**: `src/autom8_asana/automation/pipeline.py:191-497` and `src/autom8_asana/lifecycle/creation.py:103-493`
- **Category**: Code > Duplication
- **Description**: Both modules independently implement the same 7-step creation pipeline: template discovery, task duplication, name generation, section placement, due date, subtask waiting, hierarchy placement, assignee resolution. Identical regex patterns for name generation. Changes must be replicated in both places. Field seeding already diverged (`FieldSeeder` vs `AutoCascadeSeeder`). This was the highest-ROI WS4 finding (ROI 13.5).
- **Estimated LOC impact**: ~600 (extract shared creation engine)
- **Related**: D-022, D-023

### D-034: Broad exception catches (136 instances)

- **Location**: Codebase-wide
- **Category**: Code > Error Handling
- **Description**: 136 `except Exception` catches across the source tree. While many are annotated with `# BROAD-CATCH: boundary` or `# BROAD-CATCH: degrade` (indicating intentional catch-and-degrade), others are unqualified. The `api/preload/legacy.py` file alone has 12 preserved bare-except sites from its extraction from `main.py`, tagged for I6 (Exception Narrowing) but not yet addressed.
- **Estimated LOC impact**: N/A (needs per-site audit)
- **Related**: D-003

### D-035: Direct `os.environ` access in Lambda handlers

- **Location**: `src/autom8_asana/lambda_handlers/cloudwatch.py:19-20`, `cache_warmer.py:378`, `checkpoint.py:155`
- **Category**: Infrastructure > Configuration
- **Description**: Lambda handler files read environment variables directly at module level:
  ```python
  CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "autom8/lambda")
  ENVIRONMENT = os.environ.get("ENVIRONMENT", "staging")
  ```
  These bypass the centralized `Settings` model, making them hard to test and inconsistent with the main application's config access pattern.
- **Estimated LOC impact**: ~10 (route through Settings)
- **Related**: D-011

---

## WS4 Baseline Status

Status of all 25 WS4 findings as of this audit:

| WS4 ID | Ledger ID | Status | Notes |
|---------|-----------|--------|-------|
| CX-001 (DataServiceClient god) | D-030 | **open** | WS5-A planned, not executed |
| CX-002 (SaveSession god) | D-032 | **open** | No remediation plan yet |
| CX-003 (preload progressive complexity) | D-003/D-021 | **open** | Active fallback, cannot remove |
| CX-004 (batch complexity) | D-030 | **open** | Subsumed by DataServiceClient decomp |
| CX-005 (PipelineConversionRule) | D-033 | **open** | Subsumed by pipeline convergence |
| CX-006 (preload/entity_registry/cache_warmer) | D-003 | **open** | Preload = active legacy |
| CX-007 (high params) | D-030 | **open** | Subsumed by DataServiceClient decomp |
| CX-008 (deep nesting) | -- | **open** | Low priority, follows other decomps |
| DRY-001 (pipeline duplication) | D-033 | **open** | WS6 planned, not executed |
| DRY-002 (retry callbacks) | D-031 | **open** | WS5-A planned, not executed |
| DRY-003 (_elapsed_ms) | -- | **resolved** | WS5-S1 RF-001 (commit 27c0491) -> `core/timing.py` |
| DRY-004 (_ASANA_API_ERRORS) | -- | **resolved** | WS5-S1 RF-002 (commit 5772928) -> `core/exceptions.py` |
| DRY-005 (sync mirror docstrings) | -- | **open** | Low priority, follows DataServiceClient decomp |
| DRY-006 (client CRUD overloads) | D-013 | **open** | Known trade-off for type safety |
| DRY-007 (name generation regex) | D-033 | **open** | Subsumed by pipeline convergence |
| AR-001 (barrel __init__.py) | D-020/D-021 | **open** | No progress |
| AR-002 (dual-path automation) | D-022 | **open** | WS6 planned, not executed |
| AR-003 (AsanaClient coupling) | -- | **open** | Low priority |
| AR-004 (E402 circular) | -- | **open** | Single instance, low priority |
| DC-001 (legacy preload) | D-003 | **open** | Confirmed active fallback |
| DC-002 (ReconciliationsHolder alias) | -- | **resolved** | WS5-S1 RF-003 (commit fce83a0) |
| IM-001 (models/business barrel) | D-020 | **open** | Subsumed by barrel cleanup |
| IM-002 (root __init__.py dataframes) | -- | **resolved** | RF-010 (commit 152a951) lazy-load dataframes |
| IM-003 (inline deferred imports) | D-025 | **open** | Architecture-level |
| NM-001 (inconsistent naming) | D-022 | **open** | Subsumed by pipeline convergence |

**Summary**: 3 resolved, 22 open (many subsumed into higher-level items in this ledger).

---

## Summary Statistics

### Items by Category

| Category | Count | Items |
|----------|-------|-------|
| **Pattern** (error handling, DI, logging, config) | 8 | D-004 through D-011 |
| **Code** (dead code, duplication, shortcuts, stubs) | 8 | D-012 through D-019 |
| **Architecture** (imports, coupling, dual-path) | 6 | D-020 through D-025 |
| **Test** (dead targets, brittleness, failures) | 4 | D-026 through D-029 |
| **Design / Infra** (god objects, duplication, config) | 6 | D-030 through D-035 |
| **Sprint-3 carry-forward** | 3 | D-001 through D-003 |
| **Total** | **35** | |

### Items by Priority Attention Flag

| Priority Flag | Items |
|---------------|-------|
| [PRIORITY] | D-004, D-005, D-007, D-008, D-012 |
| [Sprint-3] | D-001, D-002, D-003 |
| [WS4] open | 22 items (see WS4 Baseline Status table) |
| [WS4] resolved | 3 items (DRY-003, DRY-004, DC-002) |

### Estimated LOC Impact

| Scope | LOC |
|-------|-----|
| Dead code removable now | ~500 (D-001 + D-016 + D-014) |
| Dead code removable at sunset (2026-06-01) | ~370 (D-002) |
| Pattern consolidation | ~440 (D-004 + D-005 + D-006 + D-007 + D-008 + D-009 + D-010 + D-011) |
| Query router merge | ~370 (D-012) |
| Deprecated alias cleanup | ~150 (D-017) |
| God object decomposition targets | ~4,028 (D-030 + D-032) |
| Pipeline convergence | ~1,500 (D-022 + D-033) |
| **Total addressable** | **~7,358** |

### Most Affected Modules

| Module | Debt Items | LOC at Risk |
|--------|-----------|-------------|
| `clients/data/` | D-013, D-030, D-031, D-028 | 2,175 |
| `api/routes/` | D-001, D-002, D-004, D-005, D-008, D-012, D-018, D-019 | ~1,200 |
| `automation/` | D-022, D-023, D-033 | ~900 |
| `lifecycle/` | D-022, D-023, D-033, D-014 | ~778 |
| `persistence/` | D-032 | 1,853 |
| `models/business/` | D-017, D-020, D-021 | ~400 |
| `api/preload/` | D-003 | 1,121 |
| `api/dependencies.py` | D-007 | ~90 |

---

## Audit Limitations

1. **Cache and dataframes modules**: Partially audited. WS4 excluded these; this audit included them at the file/pattern level but did not deep-read every file. The `cache/` (51 files) and `dataframes/` (30 files) subsystems may harbor additional debt not captured here.

2. **Test coverage gaps**: This audit identified test files targeting dead code and mock density, but did not measure actual coverage percentages. A `pytest --cov` run would be needed to identify coverage gaps on critical paths.

3. **External consumer audit**: The v1 query endpoint deprecation (D-002) affects external callers. This audit found "None in this repository" per the sunset inventory, but calling services have not been audited.

4. **Git blame for age**: Debt item ages were not individually computed via `git blame`. The WS4 report timestamp (2026-02-17) and WS5 completion (2026-02-18) provide temporal bounds.

5. **Runtime behavior**: Dead code determination for the v1 `query_rows` handler (D-001) is based on FastAPI router registration order. This was confirmed by the QW-6 fix documentation but was not verified via runtime traffic analysis.

6. **Intentional design vs debt**: Items D-013 (type:ignore in clients) and D-034 (broad exception catches) may be partially intentional. They are cataloged for awareness; the Risk Assessor should determine which instances warrant action.
