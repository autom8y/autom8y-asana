# Refactoring Plan -- Phase 2 (WS-4, WS-5)

**Session**: session-20260210-230114-3c7097ab
**Initiative**: Deep Code Hygiene -- autom8_asana
**Phase**: 2 -- God Module Decomposition and Magic Values
**Date**: 2026-02-11
**Agent**: architect-enforcer
**Input**: `.claude/artifacts/smell-report-phase2.md`
**Downstream**: Janitor executes this plan

---

## 1. Architectural Assessment

### 1.1 Smell Classification

| ID | Classification | Disposition | Rationale |
|---|---|---|---|
| SM-101 | **Boundary violation** | FIX (Phase A) | 5 responsibilities in one class; export API has completely different response semantics from insights. Extract cache operations and response parsing to private modules, keeping DataServiceClient as facade. |
| SM-102 | **Module-level** | FIX (Phase B) | 232-line commit_async is the core orchestration hotspot. Extract 5 commit phases into named private methods. Do NOT decompose the class -- SaveSession's transactional guarantee requires cohesive state management. |
| SM-103 | **Local** | DEFER | See Decision 1. Borderline god module with high internal cohesion. 1 public method, longest function 110 lines (below 150-line threshold). Decomposition adds indirection without net benefit. |
| SM-104 | **Local** | FIX (Phase A) | 146-line method with duplicated enum resolution logic. Extract shared name-to-GID resolution helper. Clear algorithmic decomposition seam. |
| SM-105 | **Local** | FIX (Phase A) | 138-line match/case with 5 identical-structure cases and 5 sharing a positioning pattern. Data-driven dispatch table replaces branching with lookup. |
| SM-106 | **Module-level** | FIX (Phase A, Pattern B only) | 5 hardcoded `100` sentinel comparisons in progressive builder create hidden coupling to Asana page size. Extract to named constant. Pattern A (API defaults) is ACCEPTABLE. |
| SM-107 | **Local** | FIX (Phase A) | 7-level nesting in `_evaluate_rules`, localized to schedule-driven workflow dispatch. Extract to private method. Low risk, low effort. |
| SM-108 | **Intentional boundary** | DISMISS | See Decision 4. The `/v1/` vs `/api/v1/` split encodes a real security boundary: all `/v1/` routes use `require_service_claims` (S2S JWT only). Changing it would break the convention. |
| SM-109 | **Acceptable** | DISMISS | `f"Bearer {token}"` in 3 different auth contexts (workspace detect, platform SDK, data service). RFC 6750 standard. No shared abstraction warranted. |
| SM-110 | **Marginal** | DISMISS | Single occurrence of `timeout=5.0` in health check. Extracting a constant for 1 occurrence adds indirection without deduplication benefit. |
| SM-111 | **Acceptable** | DISMISS | Error code strings `CACHE_BUILD_IN_PROGRESS` and `DATAFRAME_BUILD_UNAVAILABLE` appear once each. Named constants for 1-occurrence strings add indirection without value. |

### 1.2 Architectural Decisions

**Decision 1 (SM-103 -- progressive.py): DEFER. Do not decompose.**

The code-smeller rated this BORDERLINE and the evidence supports deferral:
- **1 public method** (`build_progressive_async`) -- the class has a single-responsibility public API
- **Longest function is 110 lines** -- below the 150-line threshold
- **Max nesting is 4 levels** -- well within acceptable bounds
- **No method shares logic with another module** -- the internal helpers are used exclusively within this class
- **High internal cohesion** -- all 17 private methods serve the one public method's orchestration

Decomposing into `ProgressiveResumeManager`, checkpoint helper, and conversion helper would create 3 new classes with no callers outside the progressive builder. Each would need a reference to `self._persistence`, `self._schema`, and `self._client`, creating a web of cross-references that adds complexity without improving testability (the existing private methods are already individually testable via the public API).

**Net assessment**: The 1,221-line count is concerning at first glance, but the internal structure is well-organized. The only actionable item within this module is SM-106 Pattern B (extract page-size constant), which is addressed separately.

**Decision 2 (SM-101 -- client.py decomposition strategy): Option (a) -- Extract internal helpers, keep facade.**

Options evaluated:
- **(a) Extract internal helpers**: Move cache ops, response parsing to private submodules. `DataServiceClient` remains the only public class. Lowest risk.
- **(b) Split into InsightsClient + ExportClient**: Would change the public API surface. Consumers import `DataServiceClient` -- splitting forces migration.
- **(c) Extract only export API**: Lowest scope but leaves the insights API monolith at ~1,300 lines.

**Verdict: Option (a).** Three private modules are extracted:

1. `clients/data/_cache.py` -- `_build_cache_key`, `_cache_response`, `_get_stale_response` (159 lines)
2. `clients/data/_response.py` -- `_parse_success_response`, `_handle_error_response`, `_validate_factory` (220 lines)
3. `clients/data/_metrics.py` -- `_emit_metric` (33 lines)

`DataServiceClient` imports and delegates to these helpers. The public API surface is unchanged. Phase 1's `_run_sync()` and `_execute_with_retry()` remain on the class (they use `self` state directly).

Key constraint: Phase 1 added `_run_sync()` (lines 291-328) and `_execute_with_retry()` (lines 332-428). These must remain on the class because they access `self._config`, `self._retry_handler`, and `self._circuit_breaker`.

**Decision 3 (SM-105 -- to_api_call): Option (a) -- Data-driven dispatch table.**

Options evaluated:
- **(a) Dict-based dispatch table**: Replace 138 lines of match/case with a ~40-line ACTION_DISPATCH dict + 3 payload builder functions. Most cases are `("POST", template, {"data": {key: target_gid}})`.
- **(b) Decompose into smaller methods**: 15 methods for 15 action types adds class surface area without reducing complexity.
- **(c) Accept as-is**: 138 lines is just below threshold, but 5 cases share identical structure and 3 share positioning logic -- this IS a data table disguised as code.

**Verdict: Option (a).** The match/case has clear data-table structure:
- 5 simple cases (ADD_TAG, REMOVE_TAG, REMOVE_FROM_PROJECT, ADD_FOLLOWER, REMOVE_FOLLOWER) share identical `("POST", f"/tasks/{gid}/{endpoint}", {"data": {key: target_gid}})` pattern
- 3 positioning cases (ADD_TO_PROJECT, MOVE_TO_SECTION, SET_PARENT) share the `insert_before`/`insert_after` augmentation pattern
- 4 list-target cases (ADD_DEPENDENCY, REMOVE_DEPENDENCY, ADD_DEPENDENT, REMOVE_DEPENDENT) share `{"data": {key: [target_gid]}}` pattern
- 2 no-target cases (ADD_LIKE, REMOVE_LIKE) share `{"data": {}}` pattern
- 1 special case (ADD_COMMENT) has unique text/html logic

A dispatch table with 4 payload builder categories replaces repetitive branching with declarative data. The `to_api_call` method becomes a ~20-line lookup + dispatch.

Test coverage is excellent (25+ tests covering all 15 action types), providing a strong safety net.

**Decision 4 (SM-108 -- route prefixes): DISMISS. The split is intentional and encodes a security boundary.**

Evidence:
- **All 4 `/v1/` routes** (`resolver.py`, `query.py`, `query_v2.py`, `admin.py`) use `require_service_claims` -- S2S JWT authentication only
- **All 8 `/api/v1/` routes** (`workspaces.py`, `dataframes.py`, `projects.py`, `webhooks.py`, `users.py`, `tasks.py`, `sections.py`, `internal.py`) support PAT authentication or mixed auth
- The naming convention `/v1/` = S2S-only internal, `/api/v1/` = external-facing, is consistent across all route files
- Changing this would break the implicit security contract and confuse API consumers who depend on the prefix to understand auth requirements

The code-smeller correctly flagged the inconsistency, but investigation reveals it is an intentional architectural boundary, not drift. No action taken beyond documenting the convention.

**Decision 5 (WS-5 scoping): Collapse to SM-106 Pattern B only.**

Of the 5 WS-5 findings:
- **SM-106 Pattern B**: FIX. 5 hardcoded `100` comparisons in `progressive.py` create hidden coupling to Asana API page size. Extract `ASANA_PAGE_SIZE = 100` constant.
- **SM-106 Pattern A**: DISMISS. 20+ `limit: int = 100` parameter defaults are API contract documentation. A shared constant would not change behavior and callers can already override.
- **SM-108**: DISMISS (Decision 4).
- **SM-109**: DISMISS. RFC 6750 standard, 3 different auth contexts.
- **SM-110**: DISMISS. Single occurrence, marginal value.
- **SM-111**: DISMISS. Single-occurrence error codes.

WS-5 collapses to a single RF task: extract `ASANA_PAGE_SIZE` in progressive builder.

---

## 2. Refactoring Tasks

### Phase A: Low-Risk Extractions (SM-104, SM-105, SM-106, SM-107)

These are localized changes within single files with clear test coverage.

---

#### RF-101: Extract shared enum resolution helper in `seeding.py`

**Smell**: SM-104 (MEDIUM, ROI 7.0)
**Risk**: LOW
**Blast radius**: `automation/seeding.py` only

**Before State**:
- `src/autom8_asana/automation/seeding.py` lines 740-885: Single 146-line `_resolve_enum_value` method
- Multi-enum branch (lines 772-829): builds `name_to_gid` dict, iterates values, resolves each, warns on missing
- Single-enum branch (lines 832-882): builds linear scan of options, resolves by name, warns on missing
- Duplication: case-insensitive name matching, GID passthrough validation, missing-option warning with available options list

**After State**:
- New private method `_build_enum_lookup(enum_options) -> dict[str, str]`: Builds case-insensitive name-to-GID dict from enum_options. Shared by both branches. ~15 lines.
- New private method `_resolve_single_option(value, name_to_gid, enum_options, field_name, task_gid) -> str | None`: Resolves a single string value to GID using lookup dict, with GID passthrough and missing-option warning. ~25 lines.
- `_resolve_enum_value` refactored to:
  - Call `_build_enum_lookup` once per invocation
  - Multi-enum branch: iterate values, call `_resolve_single_option` for each
  - Single-enum branch: call `_resolve_single_option` directly
  - Non-enum: passthrough unchanged
- `_resolve_enum_value` target: ~55 lines (down from 146)

**Invariants**:
- Same enum_options parsing (case-insensitive name matching)
- Same GID passthrough for numeric strings
- Same warning messages (seeding_enum_value_not_found, seeding_multi_enum_value_not_found, etc.)
- Same return types: `str | None` for single enum, `list[str] | None` for multi-enum
- Same None handling (return None for None input)
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/test_seeding.py -x -q --timeout=60`
2. Confirm all enum resolution tests pass (class `TestResolveEnumValue` at line 523+)
3. Verify `_resolve_enum_value` is now under 60 lines
4. Run: `.venv/bin/pytest tests/unit/automation/ -x -q --timeout=60` (full automation suite)

**Rollback**: Revert single commit

---

#### RF-102: Convert `to_api_call` match/case to dispatch table in `models.py`

**Smell**: SM-105 (MEDIUM, ROI 6.5)
**Risk**: LOW
**Blast radius**: `persistence/models.py`, consumed by `persistence/action_executor.py`

**Before State**:
- `src/autom8_asana/persistence/models.py` lines 526-663: 138-line `to_api_call` method with 15 match/case branches
- 5 simple cases: identical `("POST", path, {"data": {key: target_gid}})` pattern (ADD_TAG, REMOVE_TAG, REMOVE_FROM_PROJECT, ADD_FOLLOWER, REMOVE_FOLLOWER)
- 4 list-target cases: `{"data": {key: [target_gid]}}` (ADD_DEPENDENCY, REMOVE_DEPENDENCY, ADD_DEPENDENT, REMOVE_DEPENDENT)
- 3 positioning cases: augment data dict with `insert_before`/`insert_after` from `extra_params` (ADD_TO_PROJECT, MOVE_TO_SECTION, SET_PARENT)
- 2 no-target cases: `{"data": {}}` (ADD_LIKE, REMOVE_LIKE)
- 1 special case: ADD_COMMENT (text/html from extra_params)

**After State**:
- Module-level `_ACTION_SPECS` dict mapping `ActionType` to `ActionSpec` dataclass/namedtuple containing: `endpoint_template`, `payload_key`, `payload_style` (one of: "single", "list", "positioning", "no_target", "comment")
- Private function `_build_positioning_data(base_data, extra_params)` for the 3 positioning cases (~10 lines)
- Private function `_build_comment_data(extra_params)` for the ADD_COMMENT case (~8 lines)
- `to_api_call` method reduced to: lookup spec in `_ACTION_SPECS`, build payload by style, return tuple. ~25 lines.
- The `case _: raise ValueError(...)` default is preserved (spec lookup returns None -> ValueError)

**Invariants**:
- Return type unchanged: `tuple[str, str, dict[str, Any]]`
- All 15 action types produce identical (method, endpoint, payload) tuples
- Positioning parameters (insert_before, insert_after) propagated identically
- ADD_COMMENT text/html_text handling unchanged
- SET_PARENT parent=None case (promote to top-level) unchanged
- MOVE_TO_SECTION uses `target_gid` in path, `task_gid` in data (reversed from other cases) -- preserved
- ValueError raised for unknown ActionType -- preserved
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/persistence/test_models.py -x -q --timeout=60`
2. Confirm all 25+ `test_to_api_call_*` tests pass
3. Verify `to_api_call` method is under 30 lines
4. Run: `.venv/bin/pytest tests/unit/persistence/ -x -q --timeout=60` (full persistence suite)

**Rollback**: Revert single commit

---

#### RF-103: Extract `ASANA_PAGE_SIZE` constant in progressive builder

**Smell**: SM-106 Pattern B (MEDIUM, ROI 6.0)
**Risk**: VERY LOW
**Blast radius**: `dataframes/builders/progressive.py` only

**Before State**:
- `src/autom8_asana/dataframes/builders/progressive.py` -- 5 hardcoded `100` occurrences used as page-boundary sentinel:
  - Line 624: `if len(first_page_tasks) < 100:`
  - Line 828: `if skip_task_count >= 100:`
  - Line 847: `if len(first_page_tasks) >= 100:`
  - Line 855: `"pacing_enabled": len(first_page_tasks) == 100,`
  - Line 888: `if current_page_task_count >= 100:`

**After State**:
- New module-level constant: `ASANA_PAGE_SIZE: int = 100` defined near the top of the file (after imports, near existing constants like `logger`)
- All 5 occurrences replaced with `ASANA_PAGE_SIZE`
- Comment on constant: `# Asana API maximum items per page. Used as page-boundary sentinel for pacing and checkpoint logic.`

**Invariants**:
- All comparisons produce identical boolean results (100 == 100)
- No behavioral change whatsoever
- Pacing, checkpoint, and resume logic unchanged
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/dataframes/ -x -q --timeout=60`
2. Grep `progressive.py` for bare `100` -- confirm only the constant definition remains
3. Run: `.venv/bin/pytest tests/integration/ -k progressive -x -q --timeout=60` (if integration tests exist)

**Rollback**: Revert single commit

---

#### RF-104: Extract scheduled workflow dispatch in `polling_scheduler.py`

**Smell**: SM-107 (LOW, ROI 5.5)
**Risk**: VERY LOW
**Blast radius**: `automation/polling/polling_scheduler.py` only

**Before State**:
- `src/autom8_asana/automation/polling/polling_scheduler.py` lines 346-380: 7-level nested block within `_evaluate_rules` handling schedule-driven workflow dispatch
- Nesting: `for rule` > `if schedule+workflow` > `if should_run` > `if workflow_id+registry` > `if workflow` > `asyncio.run(...)` + else branches

**After State**:
- New private method `_dispatch_scheduled_workflow(self, rule, structured_log) -> None`: Encapsulates the schedule check, workflow lookup, execution, and error logging. ~30 lines.
- `_evaluate_rules` calls `_dispatch_scheduled_workflow(rule, structured_log)` followed by `continue` -- replacing lines 350-380 with a 2-line call + continue
- Max nesting in `_evaluate_rules` drops from 7 to 4 (for loop > if schedule > method call)

**Invariants**:
- Same schedule evaluation (`_should_run_schedule` check)
- Same workflow registry lookup
- Same asyncio.run() execution path
- Same error logging (workflow_not_found, workflow_registry_not_configured, schedule_not_due)
- Same `continue` after schedule-driven rules

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/polling/ -x -q --timeout=60`
2. Verify `_evaluate_rules` max nesting is <= 4 levels
3. Run: `.venv/bin/pytest tests/ -k "scheduler" -x -q --timeout=60`

**Rollback**: Revert single commit

---

### Phase B: Module Decomposition (SM-101, SM-102)

These are higher-risk changes affecting widely-imported modules. Phase A must be complete and verified before starting Phase B.

---

#### RF-105: Extract cache operations from DataServiceClient to `_cache.py`

**Smell**: SM-101 (HIGH, ROI 8.5) -- Part 1 of 3
**Risk**: MEDIUM
**Blast radius**: `clients/data/client.py` -- internal restructuring, no public API change

**Before State**:
- `src/autom8_asana/clients/data/client.py` lines 663-821: Three cache-related methods on DataServiceClient:
  - `_build_cache_key(self, factory, pvp)` -- line 665 (13 lines)
  - `_cache_response(self, cache_key, response)` -- line 679 (49 lines)
  - `_get_stale_response(self, cache_key, request_id)` -- line 729 (93 lines)
- These methods access `self._cache`, `self._config.cache_ttl`, `self._log`, and `self._staleness_settings`

**After State**:
- New file: `src/autom8_asana/clients/data/_cache.py` containing three module-level functions:
  - `build_cache_key(factory: str, pvp: PhoneVerticalPair) -> str`
  - `cache_response(cache: CacheProvider, cache_key: str, response: InsightsResponse, ttl: int, log: LogProvider | None) -> None`
  - `get_stale_response(cache: CacheProvider | None, cache_key: str, request_id: str, log: LogProvider | None) -> InsightsResponse | None`
- `DataServiceClient` delegates to these functions, passing `self._cache`, `self._config.cache_ttl`, `self._log` as arguments
- Methods on `DataServiceClient` become thin wrappers: `def _build_cache_key(self, factory, pvp): return build_cache_key(factory, pvp)` (or inline the call at the call site)
- `_cache.py` is a private module (underscore prefix) -- not exported from `clients/data/__init__.py`

**Invariants**:
- All cache key formats unchanged
- Stale response reconstruction unchanged (same InsightsMetadata fields, same warning message)
- Cache error handling unchanged (same exception types caught, same graceful degradation)
- `DataServiceClient` public API unchanged -- no new public methods, no signature changes
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/clients/data/ -x -q --timeout=60`
2. Verify `clients/data/_cache.py` exists and is NOT in `__init__.py` exports
3. Verify `DataServiceClient` still passes all integration tests
4. Run: `.venv/bin/pytest tests/ -k "data_service or insights" -x -q --timeout=60`

**Rollback**: Revert single commit, restore inline methods

---

#### RF-106: Extract response parsing from DataServiceClient to `_response.py`

**Smell**: SM-101 (HIGH, ROI 8.5) -- Part 2 of 3
**Risk**: MEDIUM
**Blast radius**: `clients/data/client.py` -- internal restructuring, no public API change
**Depends on**: RF-105 (to avoid merge conflicts in same region)

**Before State**:
- `src/autom8_asana/clients/data/client.py`:
  - `_validate_factory(self, factory, request_id)` -- lines 1530-1547 (17 lines)
  - `_handle_error_response(self, response, request_id, cache_key, factory, elapsed_ms)` -- lines 1548-1675 (128 lines)
  - `_parse_success_response(self, response, request_id)` -- lines 1677-1749 (73 lines)
- These methods access `self._log`, `self._cache`, `self._metrics_hook` (via `_emit_metric`), `self._circuit_breaker`, and `self.VALID_FACTORIES`

**After State**:
- New file: `src/autom8_asana/clients/data/_response.py` containing:
  - `validate_factory(factory: str, request_id: str, valid_factories: frozenset[str]) -> None`
  - `parse_success_response(response: httpx.Response, request_id: str, log: LogProvider | None) -> InsightsResponse`
  - `handle_error_response(response, request_id, cache_key, factory, elapsed_ms, *, log, emit_metric, circuit_breaker, get_stale_response) -> InsightsResponse` -- accepts callbacks for side effects
- `DataServiceClient` delegates to these functions, binding its instance state as arguments
- `_response.py` is a private module -- not exported from `__init__.py`

**Invariants**:
- Same HTTP status code to exception type mapping (400 -> InsightsValidationError, 404 -> InsightsNotFoundError, 500+ -> InsightsServiceError)
- Same error message extraction from response body (`error` or `detail` fields)
- Same circuit breaker failure recording for 5xx responses
- Same stale cache fallback behavior for 5xx responses
- Same response parsing (metadata, columns, data, warnings)
- Same validation error messages for invalid factory names
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/clients/data/ -x -q --timeout=60`
2. Verify `_response.py` is NOT in `__init__.py` exports
3. Run: `.venv/bin/pytest tests/ -k "data_service or insights or export" -x -q --timeout=60`

**Rollback**: Revert single commit, restore inline methods

---

#### RF-107: Extract metrics emission from DataServiceClient to `_metrics.py`

**Smell**: SM-101 (HIGH, ROI 8.5) -- Part 3 of 3
**Risk**: LOW
**Blast radius**: `clients/data/client.py` -- internal restructuring, no public API change
**Depends on**: RF-106 (RF-106 references `_emit_metric` which moves here)

**After completing RF-105, RF-106, RF-107**:
- `DataServiceClient` class is reduced from ~1,916 lines to ~1,250 lines
- Responsibilities cleanly separated: client lifecycle + retry + public API (on class), cache (in `_cache.py`), response parsing (in `_response.py`), metrics (in `_metrics.py`)
- No new public exports from `clients/data/` package

**Before State**:
- `src/autom8_asana/clients/data/client.py` lines 628-661: `_emit_metric` method (33 lines)
- Also: `MetricsHook` type alias (line 137) and `mask_phone_number` + `_mask_canonical_key` PII helpers (lines 80-131)

**After State**:
- New file: `src/autom8_asana/clients/data/_metrics.py` containing:
  - `MetricsHook` type alias (moved from client.py)
  - `emit_metric(hook: MetricsHook | None, name: str, value: float, tags: dict[str, str], log: LogProvider | None) -> None`
- `mask_phone_number` and `_mask_canonical_key` stay in `client.py` because `mask_phone_number` is a public export (`__all__`)
- `DataServiceClient.__init__` still accepts `metrics_hook: MetricsHook | None` -- the type is re-exported or imported from `_metrics.py`
- `MetricsHook` is also re-exported from `clients/data/__init__.py` if it was previously accessible (check current `__init__.py`)

**Invariants**:
- Same metrics emission behavior (graceful degradation on hook failure)
- Same PII masking behavior (unchanged in client.py)
- `MetricsHook` type available at same import paths
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/clients/data/ -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/ -k "metrics" -x -q --timeout=60`
3. Verify total line count of `client.py` is < 1,300 lines

**Rollback**: Revert single commit

---

#### RF-108: Extract commit phases from SaveSession.commit_async

**Smell**: SM-102 (HIGH, ROI 8.0)
**Risk**: MEDIUM-HIGH
**Blast radius**: `persistence/session.py` -- 10+ test files for SaveSession

**Before State**:
- `src/autom8_asana/persistence/session.py` lines 722-954: 232-line `commit_async` method with 5 phases:
  - Phase 0: ENSURE_HOLDERS (lines 808-821) -- 14 lines
  - Phase 1: Execute CRUD + actions (lines 823-828) -- 6 lines
  - Phase 1.5: Cache invalidation (lines 831-837) -- 7 lines
  - Phase 2: Cascade operations (lines 845-857) -- 13 lines
  - Phase 3: Healing operations (lines 859-881) -- 23 lines
  - Post-phase: State updates (lines 883-894) -- 12 lines
  - Phase 5: Automation (lines 907-926) -- 20 lines
  - Post-commit hooks + logging (lines 928-954) -- 27 lines
- Interleaved with state capture (lines 769-778), empty-commit guard (lines 780-793), and logging (lines 795-803)

**After State**:
- `commit_async` refactored to ~80 lines as a high-level orchestrator calling:
  - `_capture_commit_state() -> tuple[list, list, list, bool]` -- lock acquisition, state snapshot (~15 lines)
  - `_execute_ensure_holders(dirty_entities) -> list` -- Phase 0 (~15 lines)
  - `_execute_crud_and_actions(dirty_entities, pending_actions) -> tuple[SaveResult, list[ActionResult]]` -- Phase 1 + 1.5 (~20 lines)
  - `_execute_cascades(pending_cascades) -> list[CascadeResult]` -- Phase 2 (~15 lines)
  - `_execute_healing() -> HealingReport | None` -- Phase 3 (~25 lines)
  - `_execute_automation(crud_result) -> list[AutomationResult]` -- Phase 5 (~20 lines)
  - `_finalize_commit(crud_result, action_results, cascade_results, healing_report, automation_results) -> SaveResult` -- state updates, logging (~30 lines)
- All new methods are private (prefixed with `_`)
- No changes to class API, constructor, or any other method

**Invariants**:
- Lock acquisition and release patterns identical (state_lock for capture, release during I/O, re-acquire for updates)
- Phase execution order unchanged: 0 -> 1 -> 1.5 -> 2 -> 3 -> state update -> 5 -> post-commit hooks -> logging
- Empty-commit guard unchanged (returns SaveResult() immediately)
- `SessionClosedError` raised at same point (state capture)
- BROAD-CATCH on automation preserved with same error handling
- `_clear_successful_actions` called at same point
- `_reset_custom_field_tracking` + `mark_clean` in same order
- State transition to COMMITTED at same point
- Post-commit hook emission at same point
- Logging metrics (succeeded, failed, action counts, etc.) identical
- All existing tests pass without modification

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/persistence/test_session.py -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/unit/persistence/ -x -q --timeout=60` (all session test files)
3. Run: `.venv/bin/pytest tests/integration/test_savesession_edge_cases.py tests/integration/test_savesession_partial_failures.py -x -q --timeout=60`
4. Verify `commit_async` is under 90 lines
5. Verify each extracted method is under 30 lines
6. Run: `.venv/bin/pytest tests/ -x -q --timeout=60` (full suite -- critical for this high-blast-radius change)

**Rollback**: Revert single commit

---

## 3. Execution Sequence

### Phase A: Low-Risk Extractions

```
RF-103 (page size constant)     -- VERY LOW risk, no logic change
  |
RF-104 (scheduler nesting)     -- VERY LOW risk, extract method
  |
RF-101 (enum resolution)       -- LOW risk, extract + refactor within file
  |
RF-102 (dispatch table)        -- LOW risk, data-driven replacement
```

**Rollback point A**: After Phase A, run full test suite. All 4 commits are independently revertible.

### Phase B: Module Decomposition

```
RF-105 (cache extraction)      -- MEDIUM risk, new file
  |
RF-106 (response extraction)   -- MEDIUM risk, new file, depends on RF-105
  |
RF-107 (metrics extraction)    -- LOW risk, small extraction
  |
RF-108 (commit_async decomp)   -- MEDIUM-HIGH risk, widely tested
```

**Rollback point B1**: After RF-107, run full test suite. DataServiceClient is decomposed but SaveSession is untouched.

**Rollback point B2**: After RF-108, run full test suite. Both modules are decomposed.

---

## 4. Risk Matrix

| RF | Blast Radius | Failure Detection | Recovery Cost | Net Risk |
|---|---|---|---|---|
| RF-101 | 1 file, 1 class | Unit tests for enum resolution | Revert 1 commit | LOW |
| RF-102 | 1 file, 1 method | 25+ targeted unit tests | Revert 1 commit | LOW |
| RF-103 | 1 file, 5 replacements | Dataframe builder tests | Revert 1 commit | VERY LOW |
| RF-104 | 1 file, 1 method | Scheduler tests | Revert 1 commit | VERY LOW |
| RF-105 | 2 files (client.py + new _cache.py) | Data service client tests | Revert 1 commit, delete _cache.py | MEDIUM |
| RF-106 | 2 files (client.py + new _response.py) | Data service client tests | Revert 1 commit, delete _response.py | MEDIUM |
| RF-107 | 2 files (client.py + new _metrics.py) | Metrics tests | Revert 1 commit, delete _metrics.py | LOW |
| RF-108 | 1 file, 232-line method | 10+ session test files, 2 integration test files | Revert 1 commit | MEDIUM-HIGH |

---

## 5. Smell Disposition Summary

| ID | Disposition | RF Task | Rationale |
|---|---|---|---|
| SM-101 | FIX | RF-105, RF-106, RF-107 | Extract cache, response, metrics to private submodules |
| SM-102 | FIX | RF-108 | Extract commit phases to named private methods |
| SM-103 | **DEFER** | -- | High internal cohesion, 1 public method, longest function 110 lines. Net negative to decompose. |
| SM-104 | FIX | RF-101 | Extract shared enum resolution helper |
| SM-105 | FIX | RF-102 | Convert match/case to dispatch table |
| SM-106 | FIX (Pattern B only) | RF-103 | Extract ASANA_PAGE_SIZE constant for 5 sentinel uses |
| SM-107 | FIX | RF-104 | Extract scheduled workflow dispatch to private method |
| SM-108 | **DISMISS** | -- | Intentional security boundary: `/v1/` = S2S JWT only, `/api/v1/` = PAT supported |
| SM-109 | **DISMISS** | -- | RFC 6750 standard, 3 different auth contexts, no shared abstraction warranted |
| SM-110 | **DISMISS** | -- | Single occurrence, marginal value |
| SM-111 | **DISMISS** | -- | Single-occurrence error codes, no deduplication benefit |

All 11 smells classified: 7 fixed, 1 deferred, 3 dismissed.

---

## 6. Janitor Notes

### Commit Conventions

Each RF task is one atomic commit. Use this format:

```
refactor(<scope>): <description>

<body explaining what was extracted/changed>

Refs: SM-1XX
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Scope mapping:
- RF-101: `refactor(seeding): extract shared enum resolution helper`
- RF-102: `refactor(models): convert to_api_call to dispatch table`
- RF-103: `refactor(progressive): extract ASANA_PAGE_SIZE constant`
- RF-104: `refactor(scheduler): extract scheduled workflow dispatch method`
- RF-105: `refactor(data-client): extract cache operations to _cache module`
- RF-106: `refactor(data-client): extract response parsing to _response module`
- RF-107: `refactor(data-client): extract metrics emission to _metrics module`
- RF-108: `refactor(session): decompose commit_async into phase methods`

### Test Requirements

- Run targeted tests after each RF task (see Verification section per task)
- Run FULL test suite (`.venv/bin/pytest tests/ -x -q --timeout=60`) at rollback points A, B1, B2
- Pre-existing failures: `test_adversarial_pacing.py`, `test_paced_fetch.py`, `test_parallel_fetch.py::test_cache_errors_logged_as_warnings` -- these MUST remain unchanged (do not fix, do not break further)
- New files (`_cache.py`, `_response.py`, `_metrics.py`) do NOT need new test files -- they are tested via existing `DataServiceClient` tests

### Critical Ordering

1. **RF-103 before RF-105**: RF-103 touches `progressive.py` only. RF-105 creates a new file in `clients/data/`. No conflict, but RF-103's simplicity validates the workflow.
2. **RF-105 before RF-106**: RF-106 references `_emit_metric` which moves in RF-107. But RF-106's `handle_error_response` calls both `_emit_metric` and cache functions. Do RF-105 (cache) first to avoid editing the same code region twice.
3. **RF-106 before RF-107**: RF-107 moves `MetricsHook` type alias. RF-106's `handle_error_response` takes an `emit_metric` callback. Complete RF-106 first so RF-107 only needs to move the type and simple function.
4. **All of RF-105/106/107 before RF-108**: RF-108 is the highest-risk change. Complete the client decomposition first, verify, then proceed to session decomposition.
5. **Phase A fully complete before Phase B**: Phase A validates the workflow and provides a clean rollback point.

### New File Conventions

- Private submodules in `clients/data/` use underscore prefix: `_cache.py`, `_response.py`, `_metrics.py`
- These are NOT added to `clients/data/__init__.py` exports
- Functions in private submodules are module-level (not class methods) to enable independent testing in the future
- Type imports use `TYPE_CHECKING` guard where possible to avoid circular imports

### Constraints Reminder

- No function > 150 lines after cleanup
- No nesting > 8 levels after cleanup
- Zero test regressions (9,212 tests)
- No new dependencies
- No changes to public API signatures, return types, or error semantics
- Phase 1 changes (`_run_sync`, `_execute_with_retry`, `CacheBackendBase`) are done -- do not re-plan or conflict

---

## 7. Attestation Table

| Artifact | Verified Via | Attestation |
|---|---|---|
| Smell report read in full | Read tool: `.claude/artifacts/smell-report-phase2.md` (523 lines) | All 11 findings reviewed |
| `clients/data/client.py` (1,916 lines) | Read tool: full file | Confirmed: 5 responsibilities, decomposition seams at lines 663-821, 1530-1749, 628-661 |
| `persistence/session.py` (1,712 lines) | Read tool: full file | Confirmed: commit_async 232 lines (722-954), 5 phases, 10 subsystems in __init__ |
| `dataframes/builders/progressive.py` (1,221 lines) | Read tool: full file | Confirmed: 1 public method, longest function 110 lines, 5 hardcoded `100` at lines 624, 828, 847, 855, 888 |
| `automation/seeding.py` _resolve_enum_value | Read tool: lines 740-886 | Confirmed: 146 lines, duplicated name-to-GID resolution in multi_enum (772-829) and single enum (832-882) |
| `persistence/models.py` to_api_call | Read tool: lines 526-663 | Confirmed: 138 lines, 15 match cases, 5 identical structure, 3 positioning pattern |
| `polling_scheduler.py` _evaluate_rules | Read tool: lines 301-435 | Confirmed: 7-level nesting at lines 346-380 |
| Route prefix security boundary | Grep: `APIRouter(prefix=` + `require_service_claims` | Confirmed: all 4 `/v1/` routes use S2S JWT only; all 8 `/api/v1/` routes support PAT |
| Phase 1 plan (no conflicts) | Read tool: `.claude/artifacts/refactoring-plan-phase1.md` | Confirmed: RF-105/106/107 build on Phase 1 changes (RF-006/RF-007), no conflicts |
| `to_api_call` test coverage | Grep: `test_to_api_call` in test_models.py | Confirmed: 25+ tests covering all 15 action types |
| `_resolve_enum_value` test coverage | Grep: `_resolve_enum_value` in test_seeding.py | Confirmed: 15+ test calls in TestResolveEnumValue class |
| DataServiceClient consumers | Grep: `from autom8_asana.clients.data` in src/ | Confirmed: 3 consumers (conversation_audit, __init__, business.py) -- all import `DataServiceClient`, not internals |
| SaveSession consumers | Grep: `from autom8_asana.persistence.session import` | Confirmed: 5 consumer files -- all import `SaveSession` class, not `commit_async` |
| All 11 smells addressed | Manual review | 7 fixed (RF-101 through RF-108, excluding RF-103 numbering gap), 1 deferred (SM-103), 3 dismissed (SM-108, SM-109, SM-110, SM-111) |
| Refactoring plan written | Write tool: `.claude/artifacts/refactoring-plan-phase2.md` | This document |
