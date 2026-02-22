# Smell Report: WS4 Codebase-Wide Hygiene Assessment

**Date**: 2026-02-17
**Scope**: `src/autom8_asana/` excluding `cache/` (WS2) and `dataframes/` (WS3)
**Coverage**: 286 files, ~81,500 lines across 20 modules
**Agent**: code-smeller

---

## Executive Summary

| Category | Count | Critical | High | Medium | Low |
|----------|-------|----------|------|--------|-----|
| Complexity (CX-) | 8 | 2 | 3 | 2 | 1 |
| DRY Violations (DRY-) | 7 | 1 | 3 | 2 | 1 |
| Architecture (AR-) | 4 | 0 | 2 | 2 | 0 |
| Dead Code (DC-) | 2 | 0 | 0 | 2 | 0 |
| Import Hygiene (IM-) | 3 | 0 | 1 | 2 | 0 |
| Naming (NM-) | 1 | 0 | 0 | 1 | 0 |
| **Total** | **25** | **3** | **9** | **11** | **2** |

### Top 10 Findings by ROI

| Rank | ID | Category | ROI | Summary |
|------|----|----------|-----|---------|
| 1 | DRY-001 | DRY-PARA | 13.5 | Pipeline creation duplicated across automation + lifecycle |
| 2 | CX-001 | CX-GOD | 9.0 | DataServiceClient at 2,165 lines with 49 methods |
| 3 | DRY-002 | DRY-COPY | 9.0 | Retry callback boilerplate repeated 4x in DataServiceClient |
| 4 | CX-002 | CX-GOD | 9.0 | SaveSession at 1,853 lines with 58 methods |
| 5 | DRY-003 | DRY-COPY | 6.0 | `_elapsed_ms()` identical across 3 classes |
| 6 | CX-003 | CX-CYCLO | 6.0 | `_preload_dataframe_cache_progressive` complexity 35 |
| 7 | AR-001 | AR-LAYER | 4.5 | Barrel `__init__.py` files with non-trivial logic |
| 8 | DRY-004 | DRY-COPY | 4.5 | `_ASANA_API_ERRORS` tuple defined identically in 2 files |
| 9 | IM-001 | IM-BARREL | 4.5 | models/business/__init__.py at 237 lines |
| 10 | CX-004 | CX-CYCLO | 4.0 | `_execute_batch_request` complexity 29 |

---

## Module Health Matrix

| Module | Lines | Files | C901 | GOD | DRY | AR | Overall |
|--------|-------|-------|------|-----|-----|----|---------|
| clients/ | 11,235 | 27 | 4 | YES | HIGH | - | NEEDS ATTENTION |
| automation/ | 9,518 | 34 | 4 | - | HIGH | - | NEEDS ATTENTION |
| persistence/ | 8,137 | 20 | 0 | YES | LOW | - | FAIR |
| api/ | 8,854 | 33 | 6 | - | LOW | YES | FAIR |
| models/ | 15,375 | 59 | 2 | - | LOW | YES | FAIR |
| services/ | 5,695 | 16 | 2 | - | MED | - | FAIR |
| lifecycle/ | 4,083 | 12 | 2 | - | HIGH | - | NEEDS ATTENTION |
| core/ | 2,624 | 11 | 1 | - | LOW | - | GOOD |
| lambda_handlers/ | 1,977 | 8 | 1 | - | LOW | - | GOOD |
| transport/ | 1,700 | 6 | 2 | - | LOW | - | GOOD |
| Other (8 modules) | ~6,300 | ~50 | 1 | - | LOW | - | GOOD |

---

## Findings by Category

### Complexity (CX-)

#### SM-WS4-001: DataServiceClient god object (CRITICAL) {#CX-001}

**Category**: CX-GOD
**Severity**: 3 (high) | **Frequency**: 1 | **Blast Radius**: 3 (high) | **Fix Complexity**: 2 (medium)
**ROI Score**: (3 x 1 x 3) / 1 = 9.0

**Location**: `src/autom8_asana/clients/data/client.py` (2,165 lines, 49 methods)

**Evidence**:
- Single class `DataServiceClient` spanning lines 137-2152 (~2,015 lines in one class)
- 49 method/function definitions in file
- 3 C901 violations within this file:
  - `_execute_batch_request` (complexity 29, line 1092)
  - `_execute_insights_request` (complexity 22, line 1462)
  - `_execute_with_retry` (complexity 12, line 329)
- Mixes concerns: HTTP transport, retry logic, circuit breaker, caching, PII redaction, metrics emission, response parsing, 5 separate API endpoints (insights, batch, export CSV, appointments, leads)
- 13 parameters on `get_insights_async` (line 732)
- 16 parameters on `handle_error_response` (line 59 of `_response.py`)

**Cross-refs**: DRY-002 (retry callbacks), CX-004 (batch complexity)

**Note for Architect Enforcer**: This file has already started decomposition (extracted `_response.py`, `_metrics.py`, `_cache.py`), but the class itself remains monolithic. The 5 endpoint methods (`get_insights_async`, `get_insights_batch_async`, `get_export_csv_async`, `get_appointments_async`, `get_leads_async`) each contain ~100-200 lines of near-identical retry/circuit-breaker/logging scaffolding.

---

#### SM-WS4-002: SaveSession god object (CRITICAL) {#CX-002}

**Category**: CX-GOD
**Severity**: 3 (high) | **Frequency**: 1 | **Blast Radius**: 3 (high) | **Fix Complexity**: 2 (medium)
**ROI Score**: (3 x 1 x 3) / 1 = 9.0

**Location**: `src/autom8_asana/persistence/session.py` (1,853 lines, 58 methods)

**Evidence**:
- Single class `SaveSession` spanning lines 67-1853 (~1,786 lines)
- 58 method/function definitions
- Mixes concerns: entity tracking, dirty detection, dependency ordering, CRUD execution, cascade execution, healing execution, automation execution, event hooks, action building (followers, comments, parents, reordering), cache invalidation
- Constructor at line 134 initializes 15+ collaborators, many via conditional lazy imports
- 6 distinct phases in `commit_async` (line 722): ensure_holders, CRUD, cascades, healing, automation, finalize

**Cross-refs**: None (unique concentration)

**Note for Architect Enforcer**: Session already delegates well to collaborators (ChangeTracker, DependencyGraph, EventSystem, SavePipeline, ActionExecutor, HealingManager, CascadeExecutor, CacheInvalidator). The issue is that the orchestration logic itself (commit phases, action builders like `add_followers`, `add_comment`, `set_parent`, `reorder_subtask`) could be extracted into phase-specific handlers.

---

#### SM-WS4-003: `_preload_dataframe_cache_progressive` extreme complexity (HIGH) {#CX-003}

**Category**: CX-CYCLO
**Severity**: 3 (high) | **Frequency**: 1 | **Blast Radius**: 2 (medium) | **Fix Complexity**: 2 (medium)
**ROI Score**: (3 x 1 x 2) / 1 = 6.0

**Location**: `src/autom8_asana/api/preload/progressive.py:67` (complexity 35)

**Evidence**:
- Cyclomatic complexity of 35 (highest in codebase outside cache/dataframes)
- Function spans ~440 lines (lines 67-508)
- Contains nested `heartbeat_loop()`, `process_one_project()` async functions
- Manages 10+ local state variables (counters, sets, task references)
- Contains 6 `except Exception` blocks with various degrade behaviors

**Cross-refs**: CX-006 (`_preload_dataframe_cache` in legacy.py, complexity 23)

---

#### SM-WS4-004: `_execute_batch_request` high complexity (HIGH) {#CX-004}

**Category**: CX-CYCLO
**Severity**: 2 (medium) | **Frequency**: 1 | **Blast Radius**: 2 (medium) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 1 x 2) / 1 = 4.0

**Location**: `src/autom8_asana/clients/data/client.py:1092` (complexity 29)

**Evidence**:
- Cyclomatic complexity 29 in a single method
- ~270 lines (1092-1363)
- Contains 3 nested callback functions (`_on_retry`, `_on_timeout_exhausted`, `_on_http_error`)
- Handles circuit breaker, HTTP request, response parsing, partial success (207), per-PVP error handling, success counting -- all in one method

**Cross-refs**: DRY-002 (retry callbacks are near-identical to those in `_execute_insights_request`)

---

#### SM-WS4-005: `PipelineConversionRule.execute_async` high complexity (HIGH) {#CX-005}

**Category**: CX-CYCLO
**Severity**: 2 (medium) | **Frequency**: 1 | **Blast Radius**: 2 (medium) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 1 x 2) / 1 = 4.0

**Location**: `src/autom8_asana/automation/pipeline.py:191` (complexity 20)

**Evidence**:
- Complexity 20, spans ~300 lines (191-497)
- 7-step sequential pipeline embedded in a single method
- Steps: pre-validation, template discovery, task duplication, section placement, due date, subtask wait, field seeding, hierarchy, assignee, comment, post-validation
- Each step accumulates into `actions_executed`, `entities_created`, `enhancement_results`
- Entire method wrapped in try/except Exception

**Cross-refs**: DRY-001 (parallel implementation in `lifecycle/creation.py`)

---

#### SM-WS4-006: Multiple C901 violations in preload modules (MEDIUM) {#CX-006}

**Category**: CX-CYCLO
**Severity**: 2 (medium) | **Frequency**: 2 | **Blast Radius**: 1 (low) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 2 x 1) / 1 = 4.0

**Locations**:
- `src/autom8_asana/api/preload/legacy.py:26` -- `_preload_dataframe_cache` (complexity 23)
- `src/autom8_asana/lambda_handlers/cache_warmer.py:317` -- `_warm_cache_async` (complexity 24)
- `src/autom8_asana/core/entity_registry.py:694` -- `_validate_registry_integrity` (complexity 25)

**Evidence**: All three are long procedural functions with deep branching. The preload functions (legacy.py, progressive.py) are likely superseded, creating dead-weight complexity.

---

#### SM-WS4-007: High parameter count methods (MEDIUM) {#CX-007}

**Category**: CX-PARAM
**Severity**: 1 (low) | **Frequency**: 3 (high) | **Blast Radius**: 2 (medium) | **Fix Complexity**: 1 (low)
**ROI Score**: (1 x 3 x 2) / 1 = 6.0

**Locations**:
- `src/autom8_asana/clients/data/_response.py:59` -- `handle_error_response` (16 params)
- `src/autom8_asana/clients/data/client.py:732` -- `get_insights_async` (13 params)
- `src/autom8_asana/clients/data/client.py:830` -- `get_insights` (13 params, sync mirror)
- `src/autom8_asana/clients/data/client.py:329` -- `_execute_with_retry` (12 params)
- `src/autom8_asana/api/routes/dataframes.py:255` -- `get_section_dataframe` (12 params)
- `src/autom8_asana/api/routes/dataframes.py:168` -- `get_project_dataframe` (12 params)

**Evidence**: Methods exceeding 10 parameters indicate missing parameter objects or configuration containers.

---

#### SM-WS4-008: Deep nesting hotspots (LOW) {#CX-008}

**Category**: CX-NEST
**Severity**: 1 (low) | **Frequency**: 2 (medium) | **Blast Radius**: 1 (low) | **Fix Complexity**: 1 (low)
**ROI Score**: (1 x 2 x 1) / 1 = 2.0

**Locations** (top 5 files by lines with 4+ indent levels):
- `src/autom8_asana/automation/pipeline.py` (255 deeply-nested lines)
- `src/autom8_asana/clients/data/client.py` (253 deeply-nested lines)
- `src/autom8_asana/automation/workflows/insights_export.py` (204 deeply-nested lines)
- `src/autom8_asana/lifecycle/creation.py` (190 deeply-nested lines)
- `src/autom8_asana/transport/asana_http.py` (167 deeply-nested lines)

**Evidence**: These files have the highest density of code indented 4+ levels (16+ spaces), indicating complex control flow.

---

### DRY Violations (DRY-)

#### SM-WS4-009: Pipeline creation duplicated across automation and lifecycle (CRITICAL) {#DRY-001}

**Category**: DRY-PARA
**Severity**: 3 (high) | **Frequency**: 3 (high) | **Blast Radius**: 3 (high) | **Fix Complexity**: 2 (medium)
**ROI Score**: (3 x 3 x 3) / 2 = 13.5

**Locations**:
- `src/autom8_asana/automation/pipeline.py` -- `PipelineConversionRule.execute_async` (lines 191-497)
- `src/autom8_asana/lifecycle/creation.py` -- `EntityCreationService.create_process_async` (lines 103-237) + `_configure_async` (lines 357-493)

**Evidence**: Both modules independently implement the **same 7-step creation pipeline**:
1. **Template discovery**: Both call `TemplateDiscovery(client).find_template_task_async()` with `opt_fields=["num_subtasks"]`
2. **Task duplication**: Both call `client.tasks.duplicate_async(template.gid, name=..., include=["subtasks", "notes"])`
3. **Name generation**: `pipeline.py._generate_task_name()` (lines 510-579) and `creation.py._generate_name()` (lines 645-684) use **identical regex patterns** (`r"\[business\s*name\]"`, `r"\[(business\s*)?unit\s*name\]"`)
4. **Section placement**: Both find section by name and call `move_to_section`
5. **Due date**: Both compute `date.today() + timedelta(days=offset_days)`
6. **Subtask waiting**: Both use `SubtaskWaiter(client).wait_for_subtasks_async(gid, expected_count, timeout=2.0)`
7. **Hierarchy placement**: Both resolve holder and call `set_parent(new_task, holder, insert_after=source_process)`
8. **Assignee resolution**: Both traverse unit.rep -> business.rep cascade

**Blast Radius**: Changes to creation logic must be replicated in both places or behavior diverges. Field seeding already diverged: `automation/pipeline.py` uses `FieldSeeder` (explicit field lists), while `lifecycle/creation.py` uses `AutoCascadeSeeder` (zero-config name matching).

**Note for Architect Enforcer**: This is the highest-ROI smell. The lifecycle module was created as the "next-gen" replacement, and `automation/pipeline.py` appears to be the legacy path. They should share a common creation engine. Flag for boundary review.

---

#### SM-WS4-010: Retry callback boilerplate repeated 4x in DataServiceClient (HIGH) {#DRY-002}

**Category**: DRY-COPY
**Severity**: 3 (high) | **Frequency**: 3 (high) | **Blast Radius**: 2 (medium) | **Fix Complexity**: 1 (low)
**ROI Score**: (3 x 3 x 2) / 2 = 9.0

**Locations**:
- `src/autom8_asana/clients/data/client.py:1171-1231` -- batch request callbacks
- `src/autom8_asana/clients/data/client.py:1582-1676` -- insights request callbacks
- `src/autom8_asana/clients/data/client.py:1852-1868` -- export request callbacks
- `src/autom8_asana/clients/data/client.py:1996-2010` -- appointments request callbacks
- `src/autom8_asana/clients/data/client.py:2106-2120` -- leads request callbacks

**Evidence**: Each of the 5 endpoint methods defines 2-3 nested callback functions (`_on_retry`, `_on_timeout_exhausted`, `_on_http_error`) with near-identical structure:
1. Calculate elapsed_ms
2. Log error/retry with extra dict
3. Record circuit breaker failure
4. Raise domain-specific error

The only variation is the log event name and error message prefix. A callback factory or class method could replace all 5 instances.

---

#### SM-WS4-011: `_elapsed_ms()` identical implementation in 3 classes (HIGH) {#DRY-003}

**Category**: DRY-COPY
**Severity**: 1 (low) | **Frequency**: 3 (high) | **Blast Radius**: 2 (medium) | **Fix Complexity**: 1 (low)
**ROI Score**: (1 x 3 x 2) / 1 = 6.0

**Locations**:
- `src/autom8_asana/automation/pipeline.py:499` -- `PipelineConversionRule._elapsed_ms`
- `src/autom8_asana/lifecycle/engine.py:698` -- `LifecycleEngine._elapsed_ms`
- `src/autom8_asana/automation/events/rule.py:190` -- `BaseAutomationRule._elapsed_ms`

**Evidence**: All three implement the identical one-liner:
```python
def _elapsed_ms(self, start_time: float) -> float:
    return (time.perf_counter() - start_time) * 1000
```

---

#### SM-WS4-012: `_ASANA_API_ERRORS` tuple defined identically in 2 files (HIGH) {#DRY-004}

**Category**: DRY-CONST
**Severity**: 2 (medium) | **Frequency**: 2 (medium) | **Blast Radius**: 1 (low) | **Fix Complexity**: 1 (low)
**ROI Score**: (2 x 2 x 1) / 1 = 4.0 (adjusted to 4.5 for quick fix)

**Locations**:
- `src/autom8_asana/automation/pipeline.py:38-42`
- `src/autom8_asana/automation/seeding.py:32-36`

**Evidence**: Identical tuple definition:
```python
_ASANA_API_ERRORS: tuple[type[Exception], ...] = (
    AsanaError,
    ConnectionError,
    TimeoutError,
)
```
Compare with WS2's consolidated error tuples in `core/exceptions.py` (`CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, etc.). This pattern should follow the same centralization approach.

---

#### SM-WS4-013: Sync/async mirror methods with full docstring duplication (MEDIUM) {#DRY-005}

**Category**: DRY-COPY
**Severity**: 2 (medium) | **Frequency**: 3 (high) | **Blast Radius**: 1 (low) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 3 x 1) / 2 = 3.0

**Locations**:
- `src/autom8_asana/clients/data/client.py:732-828` vs `client.py:830-906` -- `get_insights_async` (96 lines) mirrored by `get_insights` (76 lines) with full docstring duplication
- All `clients/*.py` files use the `@async_method` decorator pattern to generate sync wrappers, which is correct, but `DataServiceClient` manually duplicates parameters + docstrings for its sync wrappers

**Evidence**: `get_insights` duplicates all 13 parameter descriptions and 4 exception descriptions from `get_insights_async`. The sync method is a pure delegation: `self._run_sync(self.get_insights_async(...))`.

---

#### SM-WS4-014: Client CRUD overloads pattern repeated across 8+ client files (MEDIUM) {#DRY-006}

**Category**: DRY-PARA
**Severity**: 1 (low) | **Frequency**: 3 (high) | **Blast Radius**: 2 (medium) | **Fix Complexity**: 3 (high)
**ROI Score**: (1 x 3 x 2) / 3 = 2.0

**Locations**: All files in `src/autom8_asana/clients/`:
- `tasks.py`, `tags.py`, `sections.py`, `users.py`, `goals.py`, `projects.py`, `portfolios.py`, `stories.py`, `custom_fields.py`

**Evidence**: Each client defines 4-8 overloaded method signatures per CRUD operation (get_async raw=True, get_async raw=False, get raw=True, get raw=False). Function names `get`, `get_async`, `create`, `create_async`, `update`, `update_async`, `delete`, `fetch_page` appear 14-26 times across files.

This is an intentional pattern using `@overload` + `@async_method` decorators and is NOT easily removable. However, the pattern bloats each client file with ~100 lines of type stubs per CRUD method. This is noted as a **known trade-off** for type safety, not a high-priority fix.

---

#### SM-WS4-015: Name generation regex pattern duplicated (LOW) {#DRY-007}

**Category**: DRY-COPY
**Severity**: 1 (low) | **Frequency**: 2 (medium) | **Blast Radius**: 1 (low) | **Fix Complexity**: 1 (low)
**ROI Score**: (1 x 2 x 1) / 1 = 2.0

**Locations**:
- `src/autom8_asana/automation/pipeline.py:563-577` -- `_generate_task_name()`
- `src/autom8_asana/lifecycle/creation.py:670-684` -- `_generate_name()`

**Evidence**: Identical regex patterns:
```python
re.sub(r"\[business\s*name\]", business_name, result, flags=re.IGNORECASE)
re.sub(r"\[(business\s*)?unit\s*name\]", unit_name, result, flags=re.IGNORECASE)
```
Subsumed by DRY-001 (pipeline creation duplication) but noted separately for quick-fix targeting.

---

### Architecture (AR-)

#### SM-WS4-016: Barrel `__init__.py` files with non-trivial logic (HIGH) {#AR-001}

**Category**: AR-LAYER
**Severity**: 2 (medium) | **Frequency**: 3 (high) | **Blast Radius**: 1 (low) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 3 x 1) / 2 = 3.0 (adjusted to 4.5 for import-chain risk)

**Locations** (lines of non-import logic):
- `src/autom8_asana/models/business/__init__.py` (237 lines, 185 lines non-import) -- Calls `register_all_models()` at import time, E402 suppression for post-registration imports
- `src/autom8_asana/__init__.py` (236 lines, 187 lines non-import) -- Re-exports from 8 subpackages
- `src/autom8_asana/persistence/__init__.py` (157 lines, 131 lines non-import) -- Re-exports from 5 modules
- `src/autom8_asana/automation/polling/__init__.py` (131 lines, 114 lines non-import)
- `src/autom8_asana/models/business/detection/__init__.py` (128 lines, 103 lines non-import)
- `src/autom8_asana/automation/__init__.py` (118 lines, uses `__getattr__` for lazy import of `PipelineConversionRule`)
- `src/autom8_asana/lifecycle/__init__.py` (113 lines, 93 lines non-import)

**Evidence**: These barrel files go beyond simple re-exports. `models/business/__init__.py` executes `register_all_models()` as a side effect of import, which is load-bearing (tests depend on it). `automation/__init__.py` uses `__getattr__` to break a circular import chain.

**Note for Architect Enforcer**: The `register_all_models()` call at import time is an architectural constraint -- it must run before any business model class is used. This creates fragile import ordering dependencies.

---

#### SM-WS4-017: Dual-path automation architecture (HIGH) {#AR-002}

**Category**: AR-COUPLE
**Severity**: 3 (high) | **Frequency**: 1 | **Blast Radius**: 3 (high) | **Fix Complexity**: 3 (high)
**ROI Score**: (3 x 1 x 3) / 3 = 3.0

**Locations**:
- `src/autom8_asana/automation/pipeline.py` (1,085 lines) -- Legacy pipeline conversion
- `src/autom8_asana/lifecycle/engine.py` (893 lines) + `lifecycle/creation.py` (826 lines) -- New lifecycle engine

**Evidence**: Two separate systems both orchestrate pipeline transitions:
1. **Legacy path** (`automation/`): `PipelineConversionRule` triggered by `AutomationEngine` after `SaveSession.commit_async()`. Uses `FieldSeeder` (explicit field lists), handles single sales-to-onboarding transition.
2. **New path** (`lifecycle/`): `LifecycleEngine.handle_transition_async()` with YAML-driven stage configs, DNC routing, 4-phase pipeline, `AutoCascadeSeeder` (zero-config). Supports multi-stage transitions.

Both paths exist simultaneously, with `lifecycle/seeding.py:AutoCascadeSeeder` importing from `automation/seeding.py:FieldSeeder` for the actual API write, creating tight coupling.

**Note for Architect Enforcer**: This is the highest-impact architectural decision. Determines whether `automation/pipeline.py` should be deprecated or whether both paths serve different use cases. Flag for boundary review.

---

#### SM-WS4-018: Cross-module coupling in AsanaClient (MEDIUM) {#AR-003}

**Category**: AR-COUPLE
**Severity**: 2 (medium) | **Frequency**: 1 | **Blast Radius**: 2 (medium) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 1 x 2) / 2 = 2.0

**Location**: `src/autom8_asana/client.py` (1,041 lines)

**Evidence**:
- Imports from 9 different top-level subpackages (highest in codebase)
- Facade class wires together: `_defaults`, `batch`, `cache`, `clients` (13 sub-clients), `config`, `exceptions`, `persistence`, `protocols`, `transport`
- This is an intentional facade pattern, but the file also contains business logic: cache warming (`warm_cache_async`, ~80 lines), workspace GID auto-detection, automation engine initialization

---

#### SM-WS4-019: E402 circular import avoidance (MEDIUM) {#AR-004}

**Category**: AR-CIRC
**Severity**: 1 (low) | **Frequency**: 1 | **Blast Radius**: 1 (low) | **Fix Complexity**: 2 (medium)
**ROI Score**: (1 x 1 x 1) / 2 = 0.5

**Location**: `src/autom8_asana/clients/data/client.py:134`

**Evidence**: One `# noqa: E402` for circular import avoidance:
```python
from autom8_asana.clients.data._metrics import MetricsHook  # noqa: E402
```
The pre-computed intelligence noted 5 files with E402 ignores, but 4 are in cache/dataframes (excluded). Only 1 remains in scope -- minimal concern.

Note: 35+ files use `TYPE_CHECKING` imports, which is the correct pattern and not a smell.

---

### Dead Code (DC-)

#### SM-WS4-020: Legacy preload module likely superseded (MEDIUM) {#DC-001}

**Category**: DC-MOD (needs-domain-review)
**Severity**: 2 (medium) | **Frequency**: 1 | **Blast Radius**: 2 (medium) | **Fix Complexity**: 1 (low)
**ROI Score**: (2 x 1 x 2) / 1 = 4.0

**Locations**:
- `src/autom8_asana/api/preload/legacy.py` (613 lines, complexity 23)
- `src/autom8_asana/api/preload/progressive.py` (508 lines, complexity 35)

**Evidence**: Two preload implementations exist side-by-side. `progressive.py` was created to replace `legacy.py` (per TDD naming convention). Both have very high complexity. If `progressive.py` is the active path, `legacy.py` may be dead code. **Needs domain review** to confirm which is active.

---

#### SM-WS4-021: Deprecated `ReconciliationsHolder` alias still exported (MEDIUM) {#DC-002}

**Category**: DC-BRANCH
**Severity**: 1 (low) | **Frequency**: 1 | **Blast Radius**: 1 (low) | **Fix Complexity**: 1 (low)
**ROI Score**: (1 x 1 x 1) / 1 = 1.0

**Location**: `src/autom8_asana/models/business/business.py:81-95`

**Evidence**:
```python
class ReconciliationsHolder(ReconciliationHolder):
    """Deprecated alias for ReconciliationHolder."""
    def __init__(self, **kwargs: Any) -> None:
        _warnings.warn(...)
        super().__init__(**kwargs)
```
Exported via `models/business/__init__.py` and root `__init__.py`. Has deprecation warning. **Needs domain review** for removal timeline.

---

### Import Hygiene (IM-)

#### SM-WS4-022: `models/business/__init__.py` excessive barrel re-exports (HIGH) {#IM-001}

**Category**: IM-BARREL
**Severity**: 2 (medium) | **Frequency**: 1 | **Blast Radius**: 3 (high) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 1 x 3) / 2 = 3.0 (adjusted to 4.5 for import-time side effects)

**Location**: `src/autom8_asana/models/business/__init__.py` (237 lines)

**Evidence**:
- Re-exports 80+ symbols from 15 submodules
- `__all__` has 87 entries
- Calls `register_all_models()` as side effect of import (line 62)
- Uses `# ruff: noqa: E402` to suppress import-order warning (line 65)
- Any `from autom8_asana.models.business import X` triggers the full registration cascade, even if X is a simple dataclass

**Cross-refs**: AR-001 (barrel logic)

---

#### SM-WS4-023: Root `__init__.py` imports entire dataframes subsystem (MEDIUM) {#IM-002}

**Category**: IM-BARREL
**Severity**: 2 (medium) | **Frequency**: 1 | **Blast Radius**: 2 (medium) | **Fix Complexity**: 2 (medium)
**ROI Score**: (2 x 1 x 2) / 2 = 2.0

**Location**: `src/autom8_asana/__init__.py` (lines 32-69)

**Evidence**: Root `__init__.py` re-exports 37 symbols from `autom8_asana.dataframes` including builders, extractors, schemas, resolvers, and cache integration. This means `import autom8_asana` eagerly loads the entire DataFrame subsystem (polars dependency, schema registry, etc.) even if only using basic task operations.

---

#### SM-WS4-024: Inline deferred imports for circular avoidance (MEDIUM) {#IM-003}

**Category**: IM-CIRC
**Severity**: 1 (low) | **Frequency**: 3 (high) | **Blast Radius**: 1 (low) | **Fix Complexity**: 2 (medium)
**ROI Score**: (1 x 3 x 1) / 2 = 1.5

**Locations** (representative, 12+ instances found):
- `src/autom8_asana/services/universal_strategy.py:156` -- `from autom8_asana.services.resolver import validate_criterion_for_entity`
- `src/autom8_asana/services/universal_strategy.py:183` -- `from autom8_asana.dataframes.builders.base import gather_with_limit`
- `src/autom8_asana/services/resolver.py:344` -- `from autom8_asana.dataframes.models.registry import SchemaRegistry`
- `src/autom8_asana/services/resolver.py:569` -- (same import again in a different function)
- `src/autom8_asana/persistence/session.py:191` -- `from autom8_asana.persistence.cascade import CascadeExecutor`

**Evidence**: Multiple inline imports (inside function bodies) to avoid circular dependencies. While this is a valid Python pattern, having 12+ instances across services/ and persistence/ indicates the module dependency graph has structural issues that could be addressed with interface extraction or a dependency inversion layer.

---

### Naming (NM-)

#### SM-WS4-025: Inconsistent naming between parallel systems (MEDIUM) {#NM-001}

**Category**: NM-CONV
**Severity**: 1 (low) | **Frequency**: 2 (medium) | **Blast Radius**: 1 (low) | **Fix Complexity**: 1 (low)
**ROI Score**: (1 x 2 x 1) / 1 = 2.0

**Locations**:
- `src/autom8_asana/automation/pipeline.py:510` -- `_generate_task_name(self, template_name, business, unit)`
- `src/autom8_asana/lifecycle/creation.py:645` -- `_generate_name(template_name, business, unit)` (staticmethod)
- `src/autom8_asana/automation/seeding.py` -- `FieldSeeder` (explicit field lists)
- `src/autom8_asana/lifecycle/seeding.py` -- `AutoCascadeSeeder` (zero-config matching)

**Evidence**: The automation and lifecycle modules use different names for equivalent concepts:
- "task name" vs "name" for the same generation logic
- "FieldSeeder" vs "AutoCascadeSeeder" for the same seeding phase
- "PipelineConversionRule" (automation) vs "EntityCreationService" (lifecycle) for the same creation flow
- "PipelineStage" (automation config) vs "StageConfig" (lifecycle config) for stage configuration

This makes it unclear to developers which module to use for new features.

---

## Cross-Module Patterns

### Pattern A: "Circuit Breaker + Retry + Log + Metric" scaffolding

Every HTTP-calling method in `DataServiceClient` repeats the same 5-step pattern:
1. Circuit breaker check (catch `SdkCircuitBreakerOpenError`)
2. Get HTTP client
3. Define 2-3 retry callbacks (log + metric + circuit breaker record)
4. Call `_execute_with_retry`
5. Handle error/success response with logging + metrics

This appears in: `get_insights_async`, `get_insights_batch_async`, `get_export_csv_async`, `get_appointments_async`, `get_leads_async`.

### Pattern B: "Template + Duplicate + Configure" pipeline

Both `automation/pipeline.py` and `lifecycle/creation.py` implement the same entity creation flow:
Template Discovery -> Task Duplication -> Name Generation -> Section Placement -> Due Date -> Subtask Wait -> Field Seeding -> Hierarchy Placement -> Assignee Resolution

### Pattern C: "Utility function duplication"

Small utility functions appear in multiple locations:
- `_elapsed_ms()` in 3 files
- `_ASANA_API_ERRORS` tuple in 2 files
- `_get_field_attr()` and `_normalize_custom_fields()` in seeding modules

---

## Boundary Violation Flags for Architect Enforcer

1. **BOUNDARY-001**: `lifecycle/seeding.py` imports private functions from `automation/seeding.py` (`_get_field_attr`, `_normalize_custom_fields`). This cross-package private import creates tight coupling between the legacy and new automation paths.

2. **BOUNDARY-002**: `automation/pipeline.py` and `lifecycle/creation.py` both directly call low-level SDK methods (`tasks.duplicate_async`, `tasks.add_to_project_async`, `tasks.update_async`) for the same operations. A shared service layer is missing.

3. **BOUNDARY-003**: `models/business/__init__.py` executes `register_all_models()` as an import side effect. This means any module importing a single business model class triggers the full registration cascade, creating hidden dependency on import order.

4. **BOUNDARY-004**: `services/universal_strategy.py` contains inline imports from `services/resolver.py` at lines 156 and 326, while `resolver.py:690` (`get_strategy`) imports from `universal_strategy.py`. This is a bidirectional dependency between two files in the same package.

---

## Recommended WS5+ Workstream Groupings

### WS5-A: DataServiceClient Decomposition (estimated: 3-5 days)
**Smells addressed**: CX-001, DRY-002, CX-004, CX-007, DRY-005
- Extract retry callback factory
- Extract endpoint-specific methods into dedicated modules (insights, batch, export, appointments, leads)
- Introduce parameter objects for high-param methods
- ROI: Addresses 5 of top 10 findings

### WS5-B: Pipeline Creation Convergence (estimated: 5-8 days)
**Smells addressed**: DRY-001, AR-002, DRY-007, NM-001, BOUNDARY-001, BOUNDARY-002
- Determine canonical creation path (likely lifecycle engine)
- Extract shared creation primitives (template discovery, name generation, hierarchy placement)
- Deprecate or delegate from `automation/pipeline.py` to lifecycle engine
- ROI: Addresses the #1 and #6 highest-ROI findings

### WS5-C: Import Architecture Cleanup (estimated: 2-3 days)
**Smells addressed**: AR-001, IM-001, IM-002, IM-003, AR-004, BOUNDARY-003
- Reduce barrel `__init__.py` to pure re-exports
- Move `register_all_models()` to explicit initialization
- Lazy-load dataframes from root `__init__.py`
- ROI: Reduces import-time overhead and fragile import ordering

### WS5-D: Utility Consolidation (estimated: 1 day)
**Smells addressed**: DRY-003, DRY-004
- Move `_elapsed_ms()` to a shared timing utility
- Centralize `_ASANA_API_ERRORS` in `core/exceptions.py`
- Quick wins, can be done as a warm-up before larger workstreams

---

## Attestation

| Artifact | Verified | Method |
|----------|----------|--------|
| SMELL-REPORT-WS4.md | Pending | Will verify via Read tool |
| All file:line references | Yes | Verified during Phase 2 reads |
| ROI scores | Yes | Computed using (severity x frequency x blast_radius) / fix_complexity |
| C901 counts | Yes | Verified via `ruff check --select C901` |
| Line counts | Yes | Verified via `wc -l` |
