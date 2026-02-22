# Refactoring Plan: WS5 / WS6 / WS7

**Author**: Architect Enforcer
**Date**: 2026-02-18
**Upstream**: SMELL-REPORT-WS4.md (25 findings), CE-WS5-WS7-ARCHITECTURE.md (pre-computed intelligence)
**Downstream**: Janitor executes phases sequentially; Audit Lead validates each phase gate
**Branch Strategy**: Direct to main, green-to-green gates
**Test Baseline**: 10,585 passed; pre-existing failures: test_adversarial_pacing.py, test_paced_fetch.py

---

## 1. Architectural Assessment

### 1.1 Boundary Health

The codebase has three systemic boundary issues:

1. **Dual creation paths** (automation/pipeline.py vs lifecycle/creation.py): Both implement the same 7-step creation pipeline independently. This is the most expensive maintenance burden -- any creation logic change must be replicated in two places or behavior silently diverges. Seeding has already diverged (FieldSeeder vs AutoCascadeSeeder). This is an **architectural** smell, not a style issue.

2. **Cross-package private imports** (lifecycle/seeding.py importing `_get_field_attr` and `_normalize_custom_fields` from automation/seeding.py): These are private API symbols being consumed across package boundaries. The underscore prefix contract is being violated.

3. **Import-time side effects** (models/business/__init__.py calling `register_all_models()`): Any consumer of a single business model class triggers the full registration cascade. This creates hidden coupling between import order and runtime correctness.

### 1.2 Root Cause Clusters

| Cluster | Root Cause | Symptoms |
|---------|-----------|----------|
| **Creation Duplication** | Lifecycle module was built as next-gen replacement but shares no creation primitives with automation | DRY-001, AR-002, DRY-007, NM-001, BOUNDARY-002 |
| **Utility Scatter** | Small helpers defined locally in each module rather than extracted | DRY-003, DRY-004 |
| **Boundary Leakage** | Private symbols exposed because shared module layer is missing | BOUNDARY-001, BOUNDARY-002 |
| **Import Sprawl** | Barrel __init__.py files grew organically to include logic, side effects, and excessive re-exports | AR-001, IM-001, IM-002, BOUNDARY-003 |
| **Complexity Accumulation** | God objects and high-cyclomatic functions grew unchecked | CX-001 through CX-008 (deferred) |

### 1.3 Execution Order

**WS5 -> WS6 -> WS7** (strictly sequential).

Rationale:
- WS5 removes noise from files WS6 touches (pipeline.py lines 38-42, 499-508).
- WS6 may change automation/__init__.py exports; WS7 restructures barrels.
- WS7 is the cleanup pass after WS5+WS6 have stabilized file contents.

---

## 2. Phase 1: WS5 -- Utility Consolidation

**Scope**: DRY-003, DRY-004, DC-002
**Estimated effort**: 1 day
**Risk level**: LOW

### RF-001: Extract `_elapsed_ms()` to `core/timing.py`

**Smell**: DRY-003 (3 identical implementations, 13 call sites)

**Before State**:
- `src/autom8_asana/automation/pipeline.py:499-508` -- `PipelineConversionRule._elapsed_ms(self, start_time: float) -> float`
- `src/autom8_asana/lifecycle/engine.py:698-700` -- `LifecycleEngine._elapsed_ms(self, start_time: float) -> float`
- `src/autom8_asana/automation/events/rule.py:190-191` -- `BaseAutomationRule._elapsed_ms(self, start_time: float) -> float`
- All three: `return (time.perf_counter() - start_time) * 1000`

**After State**:
- New file `src/autom8_asana/core/timing.py`:
  ```python
  """Timing utilities for performance measurement."""
  import time

  def elapsed_ms(start_time: float) -> float:
      """Calculate elapsed time in milliseconds from a perf_counter start."""
      return (time.perf_counter() - start_time) * 1000
  ```
- All three classes: Remove `_elapsed_ms` method. Replace `self._elapsed_ms(start_time)` with `elapsed_ms(start_time)` at all 13 call sites.
- Each file adds `from autom8_asana.core.timing import elapsed_ms`.

**Call sites to update**:
- pipeline.py: lines 232, 255, 273, 300, 478, 495 (6 sites)
- engine.py: lines 370, 598, 624, 671, 722 (5 sites, verify exact lines)
- rule.py: lines 123, 147 (2 sites)

**Invariants**:
- Same calculation: `(time.perf_counter() - start_time) * 1000`
- Return type unchanged: `float`
- No test mocks target `_elapsed_ms` (verified)

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/test_pipeline.py::TestElapsedMs -x -q`
2. Run: `.venv/bin/pytest tests/unit/automation/ tests/unit/lifecycle/ -x -q --timeout=60`
3. Confirm no test references `_elapsed_ms` beyond the direct test class (which should be updated to test the free function).

**Rollback**: Revert single commit.

---

### RF-002: Centralize `_ASANA_API_ERRORS` to `core/exceptions.py`

**Smell**: DRY-004 (2 definitions; 1 is dead code)

**Before State**:
- `src/autom8_asana/automation/pipeline.py:38-42` -- Defines `_ASANA_API_ERRORS = (AsanaError, ConnectionError, TimeoutError)`. Used in 6 except clauses: lines 621, 662, 733, 780, 864, 917.
- `src/autom8_asana/automation/seeding.py:32-36` -- Defines identical `_ASANA_API_ERRORS`. **NEVER USED** in any except clause. This is dead code.

**After State**:
- `src/autom8_asana/core/exceptions.py` gains:
  ```python
  # Asana API errors (import-safe)
  # Used by automation/pipeline.py for catch-site convenience.
  # Includes AsanaError from the SDK + builtin network errors.
  ASANA_API_ERRORS: tuple[type[Exception], ...] = (
      ConnectionError,
      TimeoutError,
  )
  try:
      from autom8_asana.exceptions import AsanaError
      ASANA_API_ERRORS = (AsanaError, ConnectionError, TimeoutError)
  except ImportError:
      pass
  ```
  Note: Follow the existing import-safe pattern used by `S3_TRANSPORT_ERRORS`. Use public name (drop underscore prefix).
- `src/autom8_asana/automation/pipeline.py`: Remove lines 38-42. Add `from autom8_asana.core.exceptions import ASANA_API_ERRORS`. Update 6 except clauses to use `ASANA_API_ERRORS` (drop underscore). Also remove the `from autom8_asana.exceptions import AsanaError` import at line 33 (no longer needed directly).
- `src/autom8_asana/automation/seeding.py`: Remove lines 25-36 entirely (the `from autom8_asana.exceptions import AsanaError` import and the dead `_ASANA_API_ERRORS` definition). If `AsanaError` is imported elsewhere in seeding.py, verify; otherwise remove completely.

**Decision note on import-safe pattern**: The existing `AsanaError` import in pipeline.py (`from autom8_asana.exceptions import AsanaError`) is a top-level import that works fine. However, for consistency with the WS2 error tuple pattern in core/exceptions.py (which uses try/except ImportError), the centralized definition should follow the same pattern. The Janitor should check whether `AsanaError` is available at `core/exceptions.py` import time -- it should be, since `autom8_asana.exceptions` is a leaf module with no circular dependencies. If so, the try/except is unnecessary and a direct import suffices:
  ```python
  from autom8_asana.exceptions import AsanaError
  ASANA_API_ERRORS: tuple[type[Exception], ...] = (
      AsanaError,
      ConnectionError,
      TimeoutError,
  )
  ```
  The Janitor should test both approaches and use whichever works without circular import. The simpler direct import is preferred.

**Invariants**:
- Identical exception tuple: `(AsanaError, ConnectionError, TimeoutError)`
- All 6 except clauses in pipeline.py catch the same types
- seeding.py behavior unchanged (the definition was dead code)

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/test_pipeline.py -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/unit/automation/test_seeding.py -x -q --timeout=60`
3. Grep: Confirm no remaining references to `_ASANA_API_ERRORS` in `src/`

**Rollback**: Revert single commit.

---

### RF-003: Remove `ReconciliationsHolder` deprecated alias

**Smell**: DC-002 (deprecated alias with no downstream consumers)

**Before State**:
- `src/autom8_asana/models/business/business.py:80-95` -- `ReconciliationsHolder(ReconciliationHolder)` class with deprecation warning (15 lines).
- `src/autom8_asana/models/business/__init__.py:83` -- imports `ReconciliationsHolder`
- `src/autom8_asana/models/business/__init__.py:179` -- lists in `__all__`
- `src/autom8_asana/models/business/__init__.py:24` -- docstring mention
- `src/autom8_asana/models/business/hydration.py:749` -- imports `ReconciliationsHolder`
- `src/autom8_asana/models/business/hydration.py:769` -- `EntityType.RECONCILIATIONS_HOLDER: ReconciliationsHolder`
- `src/autom8_asana/models/business/registry.py:239` -- `"ReconciliationsHolder": "RECONCILIATIONS_HOLDER"` in SPECIAL_CASES

**Live test references**:
- `tests/unit/models/business/test_holder_factory.py:412-432` -- `TestDeprecationAlias` class (2 tests)
- `tests/unit/models/business/test_registry.py:219` -- `_class_name_to_entity_type("ReconciliationsHolder")` assertion

**After State**:
- `business.py`: Remove the `ReconciliationsHolder` class (lines 80-95). Keep `ReconciliationHolder` unchanged.
- `__init__.py`: Remove the import of `ReconciliationsHolder` from line 83. Remove from `__all__` at line 179. Update docstring at line 24 to remove the line mentioning `ReconciliationsHolder` and its deprecated status.
- `hydration.py:749`: Remove `ReconciliationsHolder` from the import. Line 769: Change `EntityType.RECONCILIATIONS_HOLDER: ReconciliationsHolder` to `EntityType.RECONCILIATIONS_HOLDER: ReconciliationHolder` (map the enum value directly to the non-deprecated class).
- `registry.py:239`: Remove the `"ReconciliationsHolder": "RECONCILIATIONS_HOLDER"` entry from SPECIAL_CASES. Keep `"ReconciliationHolder": "RECONCILIATIONS_HOLDER"`.
- `_bootstrap.py:81`: Already maps `EntityType.RECONCILIATIONS_HOLDER` to `ReconciliationHolder` (not the deprecated alias). No change needed.

**Keep**: `EntityType.RECONCILIATIONS_HOLDER` enum value stays. It maps to `ReconciliationHolder` for backward compatibility with any persisted EntityType values.

**Test changes**:
- `test_holder_factory.py`: Remove `TestDeprecationAlias` class entirely (lines 412-432, 2 tests). These tests validate deprecated behavior that is being removed.
- `test_registry.py:218-221`: Remove the "Legacy alias" assertion for `ReconciliationsHolder`. Keep the `ReconciliationHolder` assertion.

**Root __init__.py**: `ReconciliationsHolder` is NOT exported from root `src/autom8_asana/__init__.py`. No change needed.

**Invariants**:
- `ReconciliationHolder` behavior unchanged
- `EntityType.RECONCILIATIONS_HOLDER` enum value preserved
- `hydrate_from_gid_async` still resolves `RECONCILIATIONS_HOLDER` to a valid class (`ReconciliationHolder`)
- `_class_name_to_entity_type("ReconciliationHolder")` still returns `EntityType.RECONCILIATIONS_HOLDER`

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/models/business/test_holder_factory.py -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/unit/models/business/test_registry.py -x -q --timeout=60`
3. Run: `.venv/bin/pytest tests/unit/models/business/test_hydration.py -x -q --timeout=60`
4. Grep: Confirm no remaining references to `ReconciliationsHolder` in `src/`

**Rollback**: Revert single commit.

---

### WS5 Commit Sequence

| Commit | RF | Files Changed | Gate |
|--------|-----|---------------|------|
| WS5-C1 | RF-001 | core/timing.py (new), pipeline.py, engine.py, rule.py, test_pipeline.py | Green |
| WS5-C2 | RF-002 | core/exceptions.py, pipeline.py, seeding.py | Green |
| WS5-C3 | RF-003 | business.py, __init__.py, hydration.py, registry.py, test_holder_factory.py, test_registry.py | Green |

Each commit is independently revertible. Order within WS5 does not matter, but sequential commits are simpler.

---

## 3. Phase 2: WS6 -- Pipeline Creation Convergence

**Scope**: DRY-001, AR-002, DRY-007, NM-001, BOUNDARY-001, BOUNDARY-002
**Estimated effort**: 3-5 days
**Risk level**: MEDIUM-HIGH

### 3.1 Design Decision: Shared Creation Primitives

**Context**: Both `automation/pipeline.py:execute_async` (lines 191-497) and `lifecycle/creation.py:create_process_async` (lines 103-237) + `_configure_async` (lines 357-493) implement the same 7-step creation pipeline. Steps 1-6 are copy-paste identical. Step 7 (seeding) intentionally diverges: automation uses `FieldSeeder` (explicit field lists), lifecycle uses `AutoCascadeSeeder` (zero-config matching).

**Stakeholder constraint**: Lifecycle is canonical for CRM/Process pipelines. Automation stays for other workflows. Both coexist; both must share creation primitives.

**Architecture decision**: Extract shared primitives as free functions in a new module `src/autom8_asana/core/creation.py`. Both `automation/pipeline.py` and `lifecycle/creation.py` call these shared functions. The seeding step remains divergent (each caller provides its own seeding strategy). This is NOT a new class or service -- it is a utility module with shared helper functions.

**Why not a class?** The creation steps are stateless operations that take a client and configuration. A class would add ceremony without value. Free functions match the existing `core/timing.py` pattern from WS5.

### 3.2 Shared Module Design: `core/creation.py`

```python
"""Shared creation primitives for pipeline and lifecycle entity creation.

Both automation/pipeline.py and lifecycle/creation.py use these functions
for the common steps: template discovery, task duplication, name generation,
section placement, due date, subtask waiting, hierarchy placement, and
assignee resolution.

Seeding is intentionally NOT shared -- automation uses FieldSeeder (explicit
field lists), lifecycle uses AutoCascadeSeeder (zero-config matching).
"""

async def discover_template_async(
    client: AsanaClient,
    project_gid: str,
    template_section: str | None = None,
    template_section_gid: str | None = None,
) -> Task | None:
    """Discover template task in project. Wraps TemplateDiscovery."""

async def duplicate_from_template_async(
    client: AsanaClient,
    template: Task,
    name: str,
) -> Task:
    """Duplicate template task with subtasks and notes."""

def generate_entity_name(
    template_name: str | None,
    business: Any,
    unit: Any,
    fallback_name: str = "New Process",
) -> str:
    """Generate task name by replacing [Business Name] and [Unit Name] placeholders."""

async def place_in_section_async(
    client: AsanaClient,
    task_gid: str,
    project_gid: str,
    section_name: str,
) -> bool:
    """Move task to named section in project."""

def compute_due_date(offset_days: int) -> str:
    """Compute due date as ISO string from today + offset."""

async def wait_for_subtasks_async(
    client: AsanaClient,
    task_gid: str,
    expected_count: int,
    timeout: float = 2.0,
) -> bool:
    """Wait for Asana to finish creating subtasks after duplication."""
```

**What is NOT extracted**: Hierarchy placement and assignee resolution remain in each caller. These steps have meaningful behavioral differences between automation (uses `_place_in_hierarchy_async` with direct `set_parent` call) and lifecycle (uses `SaveSession` for `set_parent`). Extracting them would require abstracting over the session/non-session distinction, which is a behavior change.

### RF-004: Extract `generate_entity_name()` to `core/creation.py`

**Smell**: DRY-007, NM-001

**Before State**:
- `src/autom8_asana/automation/pipeline.py:510-579` -- `PipelineConversionRule._generate_task_name(self, template_name, business, unit)` (70 lines, instance method)
- `src/autom8_asana/lifecycle/creation.py:644-684` -- `EntityCreationService._generate_name(template_name, business, unit)` (40 lines, staticmethod)
- Both contain identical regex: `re.sub(r"\[business\s*name\]", ...)` and `re.sub(r"\[(business\s*)?unit\s*name\]", ...)`
- pipeline.py version has a different fallback: `f"New {self._target_type.value.title()}"` vs creation.py's `"New Process"`

**After State**:
- New file `src/autom8_asana/core/creation.py` (created in this RF, extended by subsequent RFs):
  ```python
  def generate_entity_name(
      template_name: str | None,
      business: Any,
      unit: Any,
      fallback_name: str = "New Process",
  ) -> str:
  ```
  The `fallback_name` parameter accommodates pipeline.py's `f"New {target_type.value.title()}"` without behavior change.
- `pipeline.py`: Remove `_generate_task_name` method (lines 510-579). Replace call at line 312 with:
  ```python
  from autom8_asana.core.creation import generate_entity_name
  new_task_name = generate_entity_name(
      template_name=template_task.name,
      business=business,
      unit=unit,
      fallback_name=f"New {self._target_type.value.title()}",
  )
  ```
- `creation.py`: Remove `_generate_name` staticmethod (lines 644-684). Replace calls at lines 159, 279 with `generate_entity_name(...)` using default `fallback_name`.

**Invariants**:
- Same regex patterns: `r"\[business\s*name\]"` and `r"\[(business\s*)?unit\s*name\]"`
- Same `re.IGNORECASE` flag
- Same `getattr(business, "name", None)` / `getattr(unit, "name", None)` pattern
- pipeline.py fallback preserved via `fallback_name` parameter
- creation.py fallback `"New Process"` preserved as default

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/test_pipeline.py -k "name" -x -q --timeout=60` (17 test cases)
2. Run: `.venv/bin/pytest tests/unit/lifecycle/test_creation.py -k "name" -x -q --timeout=60` (7 test cases)
3. All 24 name generation tests pass without modification.

**Rollback**: Revert single commit.

---

### RF-005: Extract shared creation helpers to `core/creation.py`

**Smell**: DRY-001, BOUNDARY-002

This RF extends the `core/creation.py` module created in RF-004 with additional shared helpers.

**Before State**:
- Template discovery: `pipeline.py:282-301` and `creation.py:150-156,272-277` both instantiate `TemplateDiscovery(client)` and call `find_template_task_async()` with `opt_fields=["num_subtasks"]`.
- Task duplication: `pipeline.py:324-328` and `creation.py:170-174,286-290` both call `client.tasks.duplicate_async(gid, name=..., include=["subtasks", "notes"])`.
- Section placement: `pipeline.py:343-352` calls `self._move_to_target_section_async()`. `creation.py:381-391` calls `self._move_to_section_async()`. Both find section by name and call add_to_project or move.
- Due date: `pipeline.py:356-364` calls `self._set_due_date_async()`. `creation.py:394-399` computes `date.today() + timedelta(days=offset)`.
- Subtask wait: `pipeline.py:368-382` and `creation.py:402-410` both instantiate `SubtaskWaiter(client)` and call `wait_for_subtasks_async(gid, expected_count, timeout=2.0)`.

**After State**:
- `core/creation.py` gains the helper functions defined in Section 3.2.
- Both `pipeline.py` and `creation.py` import and call these shared helpers instead of implementing them inline.
- `TemplateDiscovery` and `SubtaskWaiter` remain in their current locations (`automation/templates.py`, `automation/waiter.py`). The shared helpers in `core/creation.py` import from them. This eliminates the direct cross-package import from `lifecycle/creation.py -> automation/templates.py` and `lifecycle/creation.py -> automation/waiter.py` -- those imports now go through `core/creation.py`.

**Note on section placement**: pipeline.py's `_move_to_target_section_async` and creation.py's `_move_to_section_async` have slightly different signatures and logging. The shared `place_in_section_async` should use the simpler interface: `(client, task_gid, project_gid, section_name) -> bool`. Both callers can adapt to this. The Janitor must read both implementations fully to confirm behavioral equivalence before extracting.

**Invariants**:
- Same `opt_fields=["num_subtasks"]` in template discovery
- Same `include=["subtasks", "notes"]` in task duplication
- Same `timeout=2.0` in subtask wait
- Pipeline.py still calls `TemplateDiscovery` and `SubtaskWaiter` (via core/creation.py)
- Lifecycle/creation.py no longer directly imports from `automation/templates.py` or `automation/waiter.py`

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/test_pipeline.py -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/unit/lifecycle/test_creation.py -x -q --timeout=60`
3. Run: `.venv/bin/pytest tests/unit/lifecycle/test_init_actions.py -x -q --timeout=60`
4. Run: `.venv/bin/pytest tests/unit/automation/test_pipeline_hierarchy.py -x -q --timeout=60`

**Mock target changes**: Tests that mock `autom8_asana.automation.templates.TemplateDiscovery` should still work because the import path for the class itself does not change -- only who imports it changes. The Janitor must verify by running all affected tests. If any test mocks at the import site (e.g., `@patch("autom8_asana.lifecycle.creation.TemplateDiscovery")`), the patch target must be updated to `autom8_asana.core.creation.TemplateDiscovery`.

**Rollback**: Revert single commit.

---

### RF-006: Promote `_get_field_attr` and `_normalize_custom_fields` to public API

**Smell**: BOUNDARY-001

**Before State**:
- `src/autom8_asana/automation/seeding.py:41-64` -- `_get_field_attr()` (private, 24 lines)
- `src/autom8_asana/automation/seeding.py:123-134` -- `_normalize_custom_fields()` (private, 12 lines)
- `src/autom8_asana/lifecycle/seeding.py:29-33` -- imports both private symbols cross-package:
  ```python
  from autom8_asana.automation.seeding import (
      FieldSeeder,
      _get_field_attr,
      _normalize_custom_fields,
  )
  ```
- lifecycle/seeding.py uses `_get_field_attr` in 18 call sites and `_normalize_custom_fields` in 2 call sites.

**Resolution decision**: Option A -- Promote to public API in `automation/seeding.py`. Renaming is the lowest-risk option. These functions are stable (unchanged since initial implementation), well-documented, and have clear public utility. Moving to a separate module (Option B) would change import paths for all consumers. Inlining (Option C) would duplicate 36 lines of code.

**After State**:
- `automation/seeding.py`: Rename `_get_field_attr` to `get_field_attr`. Rename `_normalize_custom_fields` to `normalize_custom_fields`. Rename `_to_dict` to `to_dict` (called by `normalize_custom_fields`).
- `automation/seeding.py`: Update all internal call sites (9 for `_get_field_attr`, 2 for `_normalize_custom_fields`, references to `_to_dict` within `_normalize_custom_fields`).
- `lifecycle/seeding.py:29-33`: Update import to use public names:
  ```python
  from autom8_asana.automation.seeding import (
      FieldSeeder,
      get_field_attr,
      normalize_custom_fields,
  )
  ```
- `lifecycle/seeding.py`: Update all 18 `_get_field_attr` call sites to `get_field_attr` and 2 `_normalize_custom_fields` call sites to `normalize_custom_fields`. Use `replace_all` in Edit tool.

**Invariants**:
- Function bodies unchanged
- Return types unchanged
- All existing behavior preserved
- No test mocks target these functions directly (they are called indirectly)

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/automation/test_seeding.py -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/unit/lifecycle/test_seeding.py -x -q --timeout=60`
3. Run: `.venv/bin/pytest tests/unit/lifecycle/test_creation.py -x -q --timeout=60`
4. Grep: Confirm no remaining references to `_get_field_attr` or `_normalize_custom_fields` in `src/`

**Rollback**: Revert single commit.

---

### RF-007: Wire `lifecycle/creation.py` to shared creation helpers

**Smell**: AR-002 (dual-path architecture wiring)

This RF applies the shared helpers from RF-005 specifically to `lifecycle/creation.py`.

**Before State**:
- `lifecycle/creation.py:35-36` imports directly from automation:
  ```python
  from autom8_asana.automation.templates import TemplateDiscovery
  from autom8_asana.automation.waiter import SubtaskWaiter
  ```
- `lifecycle/creation.py` has inline template discovery, duplication, section placement, due date, and subtask wait logic in `create_process_async` (lines 147-196) and `_configure_async` (lines 380-410).

**After State**:
- `lifecycle/creation.py`: Replace direct imports of `TemplateDiscovery` and `SubtaskWaiter` with imports from `core/creation.py`:
  ```python
  from autom8_asana.core.creation import (
      discover_template_async,
      duplicate_from_template_async,
      generate_entity_name,
      place_in_section_async,
      compute_due_date,
      wait_for_subtasks_async,
  )
  ```
- Inline template discovery / duplication / section / due date / subtask-wait code replaced with calls to shared helpers.
- `create_entity_async` (lines 239-351) also refactored to use shared helpers (it duplicates the same pattern as `create_process_async`).

**Invariants**:
- All creation behavior identical
- Blank fallback path preserved (creation.py has `create_async` fallback when no template found -- this path is NOT extracted, only the template path is shared)
- `AutoCascadeSeeder` usage unchanged
- `SaveSession` usage in hierarchy placement unchanged

**Verification**:
1. Run: `.venv/bin/pytest tests/unit/lifecycle/ -x -q --timeout=60`
2. Run: `.venv/bin/pytest tests/unit/automation/workflows/test_pipeline_transition.py -x -q --timeout=60`

**Rollback**: Revert single commit.

---

### WS6 Commit Sequence

| Commit | RF | Files Changed | Gate |
|--------|-----|---------------|------|
| WS6-C1 | RF-004 | core/creation.py (new), pipeline.py, creation.py | Green |
| WS6-C2 | RF-005 | core/creation.py (extend), pipeline.py | Green |
| WS6-C3 | RF-006 | automation/seeding.py, lifecycle/seeding.py | Green |
| WS6-C4 | RF-007 | lifecycle/creation.py | Green |

**Critical ordering**: RF-004 before RF-005 (RF-005 extends the module created by RF-004). RF-006 is independent and can be in any position. RF-007 depends on RF-005.

---

## 4. Phase 3: WS7 -- Import Architecture + Dead Code

**Scope**: AR-001, IM-001, IM-002, IM-003, DC-001, BOUNDARY-003
**Estimated effort**: 2-3 days
**Risk level**: MEDIUM

### 4.1 DC-001 Investigation: Legacy Preload

**Question**: Is `api/preload/legacy.py` dead code?

**Evidence gathered**:
- `api/preload/__init__.py` exports ONLY `_preload_dataframe_cache_progressive` (progressive).
- `api/lifespan.py:22,151` imports and calls ONLY `_preload_dataframe_cache_progressive`.
- `progressive.py:250-260` contains a fallback:
  ```python
  if not persistence.is_available:
      # Fall back to existing preload
      from .legacy import _preload_dataframe_cache
      await _preload_dataframe_cache(app)
      return
  ```
- This fallback triggers when `persistence.is_available` is False, which occurs when `SectionPersistence(storage=df_storage)` reports S3 unavailable.

**Conclusion**: Legacy preload is NOT dead code. It serves as a fallback when S3 storage is unavailable. This is a **degraded-mode path** -- removing it would mean that when S3 is down, preload silently does nothing instead of falling back to the legacy in-memory approach.

**Decision**: DEFER removal. Legacy preload removal requires a product decision about degraded-mode behavior. Document this finding for future workstream. The fallback path is a valid architectural safety net.

**Action for WS7**: No code change for DC-001. Add a code comment at `progressive.py:257` clarifying the fallback purpose:
```python
# ARCHITECTURE NOTE: legacy preload is the degraded-mode fallback when S3
# is unavailable. Do not remove without replacing degraded-mode strategy.
```

---

### RF-008: Reduce barrel `__init__.py` files to pure re-exports

**Smell**: AR-001 (7 barrel files with non-trivial logic)

**Scope**: The LOW-risk barrel files only. The HIGH-risk `models/business/__init__.py` is handled separately in RF-009.

**Before State** (5 LOW-risk barrels):
- `src/autom8_asana/persistence/__init__.py` (157 lines) -- Pure re-exports, no logic. Already clean.
- `src/autom8_asana/automation/polling/__init__.py` (131 lines) -- Pure re-exports. Already clean.
- `src/autom8_asana/models/business/detection/__init__.py` (128 lines) -- Pure re-exports. Already clean.
- `src/autom8_asana/automation/__init__.py` (118 lines) -- Has `__getattr__` for lazy PipelineConversionRule import. This is intentional circular-import avoidance, not a smell.
- `src/autom8_asana/lifecycle/__init__.py` (113 lines) -- Pure re-exports. Already clean.

**After State**: Upon source verification, these 5 barrels are already pure re-exports (except `automation/__init__.py`'s intentional `__getattr__`). No changes needed.

**Decision**: AR-001 is partially DISMISSED for these 5 barrels. The smell report classified them as having "non-trivial logic" based on line count, but the lines are import/export statements and docstrings, not logic. The `__getattr__` in `automation/__init__.py` is an intentional pattern for circular import avoidance and should remain.

The two remaining AR-001 targets (`models/business/__init__.py` and root `__init__.py`) are addressed in RF-009 and RF-010 respectively.

---

### RF-009: Extract `register_all_models()` from import-time to explicit initialization

**Smell**: BOUNDARY-003, IM-001

**Before State**:
- `src/autom8_asana/models/business/__init__.py:60-62`:
  ```python
  from autom8_asana.models.business._bootstrap import register_all_models
  register_all_models()
  ```
  This runs at import time. Any `from autom8_asana.models.business import X` triggers registration.
- `_bootstrap.py:38-39`: Idempotency guard (`_BOOTSTRAP_COMPLETE` flag). Multiple calls are safe.
- `models/business/detection/tier1.py:105`: Also calls `register_all_models()` as a guard before detection.
- 11 distinct source files import from `models/business` (CE pre-computed list).
- `tests/unit/models/business/test_registry_consolidation.py`: Tests `register_all_models()`, `reset_bootstrap()`, idempotency.

**Risk assessment**: Moving `register_all_models()` out of import-time requires ensuring every entry point calls it before first use. The idempotency guard makes this safe, but missing an entry point would cause silent detection failures. This is a HIGH-RISK refactor.

**Decision**: DEFER. The risk-to-reward ratio is unfavorable for WS7. The idempotency guard works correctly. Import-time registration is a documented architectural decision (TDD-registry-consolidation). The side effect is deterministic and fast. The only downside is that importing a simple dataclass from `models.business` triggers registration, but this is a performance cost, not a correctness issue.

**Action for WS7**: Add a code comment at `__init__.py:56-62` clarifying the architectural decision:
```python
# ARCHITECTURE: Import-time registration is intentional per TDD-registry-consolidation.
# The idempotency guard in _bootstrap.py makes repeated calls safe.
# Moving to explicit initialization would require auditing all entry points
# (API lifespan, Lambda handlers, CLI, tests). Deferred until entry point
# inventory is complete. See REFACTORING-PLAN-WS567.md RF-009.
```

---

### RF-010: Lazy-load dataframes from root `__init__.py`

**Smell**: IM-002

**Before State**:
- `src/autom8_asana/__init__.py:31-69` -- Eagerly imports 37 symbols from `autom8_asana.dataframes`. This means `import autom8_asana` or `from autom8_asana import AsanaClient` loads polars + DataFrame subsystem.
- 15 files import `AsanaClient` from root and pay this cost.

**After State**:
- Root `__init__.py`: Replace eager dataframe imports (lines 31-69) with lazy loading via `__getattr__`:
  ```python
  # Dataframe Layer (TDD-0009) -- lazy-loaded to avoid pulling in polars
  # for consumers that only need the core API client.
  _DATAFRAME_EXPORTS = {
      "BASE_SCHEMA", "CONTACT_SCHEMA", "LAZY_THRESHOLD", "UNIT_SCHEMA",
      "BaseExtractor", "CachedRow", "ColumnDef", "ContactExtractor",
      "ContactRow", "CustomFieldResolver", "DataFrameBuilder",
      "DataFrameCacheIntegration", "DataFrameError", "DataFrameSchema",
      "DefaultCustomFieldResolver", "ExtractionError", "FailingResolver",
      "MockCustomFieldResolver", "NameNormalizer", "ProgressiveProjectBuilder",
      "SchemaNotFoundError", "SchemaRegistry", "SchemaVersionError",
      "SectionDataFrameBuilder", "TaskRow", "TypeCoercionError",
      "UnitExtractor", "UnitRow",
  }

  def __getattr__(name: str) -> object:
      if name in _DATAFRAME_EXPORTS:
          import autom8_asana.dataframes as _df
          return getattr(_df, name)
      raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
  ```
- Keep all 37 symbols in `__all__` so `from autom8_asana import *` still works (it triggers `__getattr__` for each).
- Consumers using `from autom8_asana import DataFrameBuilder` still work -- `__getattr__` resolves the import.

**Invariants**:
- All 37 dataframe symbols remain importable from root
- `__all__` unchanged
- `from autom8_asana import AsanaClient` no longer loads polars
- `from autom8_asana import DataFrameBuilder` still works (triggers lazy load)

**Verification**:
1. Run: `.venv/bin/pytest tests/ -x -q --timeout=60` (full suite)
2. Verify: `python -c "from autom8_asana import AsanaClient; print('OK')"` does NOT import polars
3. Verify: `python -c "from autom8_asana import DataFrameBuilder; print('OK')"` works

**Rollback**: Revert single commit.

---

### RF-011: Document inline deferred imports

**Smell**: IM-003

**Before State**: 12+ inline imports across `services/`, `persistence/` for circular dependency avoidance.

**Decision**: OBSERVE, do not fix. The inline imports are a valid Python pattern for circular dependency resolution. The most notable case (`services/universal_strategy.py` <-> `services/resolver.py`) is a genuine bidirectional dependency that would require interface extraction or dependency inversion to resolve properly. That is architectural work beyond WS7's scope.

**Action for WS7**: No code change. The smell is documented here as acknowledged. Future workstream (WS8+) could introduce a protocol/interface layer in `services/` to break the circular dependency.

---

### RF-012: Annotate legacy preload fallback

**Smell**: DC-001 (companion to investigation in Section 4.1)

**Before State**: `progressive.py:250-260` has an uncommented fallback to legacy preload.

**After State**: Add clarifying comment:
```python
# ARCHITECTURE NOTE: Legacy preload is the degraded-mode fallback when S3
# is unavailable (persistence.is_available == False). This path exercises
# the full in-memory preload from Asana API. Do not remove without
# replacing degraded-mode strategy. See REFACTORING-PLAN-WS567.md DC-001.
```

**Verification**: Comment-only change. Run full test suite to confirm no accidental edits.

**Rollback**: Revert single commit.

---

### WS7 Commit Sequence

| Commit | RF | Files Changed | Gate |
|--------|-----|---------------|------|
| WS7-C1 | RF-010 | root __init__.py | Green |
| WS7-C2 | RF-012 | progressive.py, models/business/__init__.py | Green |

RF-008 (barrel cleanup) requires no code changes. RF-009 (register_all_models) is deferred. RF-011 (inline imports) is observe-only.

---

## 5. CX-001 / CX-002 Placement Decision

**CX-001 (DataServiceClient)**: 2,165 lines, 49 methods, mixes HTTP transport / retry / circuit breaker / caching / PII redaction / metrics / response parsing / 5 API endpoints.

**CX-002 (SaveSession)**: 1,853 lines, 58 methods, mixes entity tracking / dirty detection / dependency ordering / CRUD / cascade / healing / automation / event hooks / action builders / cache invalidation.

**Decision**: DEFER both to a future WS8.

**Rationale**:
1. These are CX (complexity) findings, not DRY or boundary violations. They require decomposition, not consolidation.
2. Each god object requires its own focused workstream. DataServiceClient needs callback factory extraction + endpoint method extraction. SaveSession needs phase-specific handler extraction.
3. Blast radius is extreme: DataServiceClient has 13 parameters on its main method and is the sole HTTP gateway to the data service. SaveSession is the transactional core of the persistence layer.
4. The stakeholder's "aggressive" risk appetite means "do it if risk is manageable," not "do it regardless of blast radius." These decompositions have unmanageable blast radius within a shared workstream.
5. WS5/WS6/WS7 already deliver high ROI by addressing the #1 ranked smell (DRY-001) and 14 other findings. Adding god object decomposition would overload the sprint.

---

## 6. Risk Matrix

| Phase | RF | Blast Radius | Failure Detection | Recovery | Risk |
|-------|-----|-------------|-------------------|----------|------|
| WS5 | RF-001 | 3 files, 13 call sites | Unit tests, timing assertions | Single commit revert | LOW |
| WS5 | RF-002 | 2 files, 6 except clauses | Exception handling tests | Single commit revert | LOW |
| WS5 | RF-003 | 4 source + 2 test files | Hydration + registry tests | Single commit revert | LOW |
| WS6 | RF-004 | 3 files, 24 test cases | Name generation tests | Single commit revert | LOW |
| WS6 | RF-005 | 3 files, mock path risk | Full automation + lifecycle tests | Single commit revert | MEDIUM |
| WS6 | RF-006 | 2 files, 20+ call sites | Seeding tests | Single commit revert | LOW |
| WS6 | RF-007 | 1 file, mock path risk | Full lifecycle tests | Single commit revert | MEDIUM |
| WS7 | RF-010 | 1 file, import behavior | Full test suite + manual import check | Single commit revert | MEDIUM |
| WS7 | RF-012 | 1 file, comment only | Full test suite | Single commit revert | TRIVIAL |

**Highest risk**: RF-005 and RF-007 (mock path changes). The Janitor must grep for all mock/patch targets referencing `TemplateDiscovery`, `SubtaskWaiter` at the lifecycle import site and update them.

---

## 7. Complete Smell Disposition Table

| ID | Category | Severity | Disposition | RF/Reason |
|----|----------|----------|-------------|-----------|
| CX-001 | CX-GOD | CRITICAL | DEFERRED | WS8 -- god object decomposition, extreme blast radius |
| CX-002 | CX-GOD | CRITICAL | DEFERRED | WS8 -- god object decomposition, extreme blast radius |
| CX-003 | CX-CYCLO | HIGH | DEFERRED | WS8 -- coupled to DC-001 investigation; progressive.py complexity |
| CX-004 | CX-CYCLO | HIGH | DEFERRED | WS8 -- subsumed by CX-001 DataServiceClient decomposition |
| CX-005 | CX-CYCLO | HIGH | SUBSUMED | By RF-005/RF-007 -- extracting shared helpers reduces pipeline.py complexity |
| CX-006 | CX-CYCLO | MEDIUM | DEFERRED | Legacy preload complexity; DC-001 deferred |
| CX-007 | CX-PARAM | MEDIUM | DEFERRED | WS8 -- parameter objects for DataServiceClient |
| CX-008 | CX-NEST | LOW | DISMISSED | Nesting is symptomatic of the patterns addressed by DRY-001 |
| DRY-001 | DRY-PARA | CRITICAL | ADDRESSED | RF-004, RF-005, RF-007 |
| DRY-002 | DRY-COPY | HIGH | DEFERRED | WS8 -- subsumed by CX-001 callback factory extraction |
| DRY-003 | DRY-COPY | HIGH | ADDRESSED | RF-001 |
| DRY-004 | DRY-CONST | HIGH | ADDRESSED | RF-002 |
| DRY-005 | DRY-COPY | MEDIUM | DEFERRED | WS8 -- sync/async docstring DRY in DataServiceClient |
| DRY-006 | DRY-PARA | MEDIUM | DISMISSED | Intentional `@overload` pattern for type safety |
| DRY-007 | DRY-COPY | LOW | ADDRESSED | RF-004 (subsumed by name generation extraction) |
| AR-001 | AR-LAYER | HIGH | PARTIALLY ADDRESSED | RF-008 (5 barrels verified clean), RF-009 (deferred), RF-010 (root lazy load) |
| AR-002 | AR-COUPLE | HIGH | ADDRESSED | RF-005, RF-007 (shared creation layer) |
| AR-003 | AR-COUPLE | MEDIUM | DISMISSED | Intentional facade pattern; business logic is minimal |
| AR-004 | AR-CIRC | MEDIUM | DISMISSED | Single E402 in scope; TYPE_CHECKING pattern is correct |
| DC-001 | DC-MOD | MEDIUM | INVESTIGATED, DEFERRED | RF-012 (comment); legacy is degraded-mode fallback, not dead |
| DC-002 | DC-BRANCH | MEDIUM | ADDRESSED | RF-003 |
| IM-001 | IM-BARREL | HIGH | PARTIALLY ADDRESSED | RF-009 deferred; import-time side effect documented |
| IM-002 | IM-BARREL | MEDIUM | ADDRESSED | RF-010 |
| IM-003 | IM-CIRC | MEDIUM | OBSERVED | RF-011 -- inline imports are valid pattern; root cause is bidirectional dependency |
| NM-001 | NM-CONV | MEDIUM | ADDRESSED | RF-004 (unified naming in shared module) |
| BOUNDARY-001 | -- | HIGH | ADDRESSED | RF-006 |
| BOUNDARY-002 | -- | HIGH | ADDRESSED | RF-005 |
| BOUNDARY-003 | -- | HIGH | DEFERRED | RF-009 deferred |
| BOUNDARY-004 | -- | MEDIUM | OBSERVED | Subsumed by IM-003; bidirectional services/ dependency |

**Summary**: 25 smell findings + 4 boundary flags = 29 items total.
- ADDRESSED: 12 (RF-001 through RF-007, RF-010)
- DEFERRED: 10 (with specific WS8 targets or investigation outcomes)
- DISMISSED: 4 (intentional patterns, not actual smells)
- OBSERVED: 3 (acknowledged, no action needed this sprint)

---

## 8. Janitor Notes

### 8.1 Commit Conventions
- Commit message format: `refactor(<scope>): <description> [<RF-IDs>]`
- Example: `refactor(core): extract elapsed_ms to shared timing utility [RF-001]`
- Include `[WS5]`, `[WS6]`, or `[WS7]` tag in commit body for traceability.

### 8.2 Test Requirements
- Run `.venv/bin/pytest tests/ -x -q --timeout=60` after EVERY commit (green-to-green gate).
- Pre-existing failures to ignore: `test_adversarial_pacing.py`, `test_paced_fetch.py` (checkpoint assertions).
- Expected test count: 10,585 (minus 2 removed deprecation tests in RF-003 = 10,583).

### 8.3 Critical Ordering
1. **WS5 before WS6**: WS5 cleans pipeline.py lines 38-42 and 499-508. WS6 modifies pipeline.py lines 191-497 and 510-579.
2. **RF-004 before RF-005**: RF-005 extends the module created by RF-004.
3. **RF-005 before RF-007**: RF-007 wires lifecycle to helpers created in RF-005.
4. **WS6 before WS7**: WS6 may change automation/__init__.py exports.

### 8.4 Mock Path Audit (WS6)
Before committing RF-005 and RF-007, the Janitor MUST:
1. Grep for `@patch.*TemplateDiscovery` and `@patch.*SubtaskWaiter` in all test files.
2. Identify patches targeting the lifecycle import site (e.g., `@patch("autom8_asana.lifecycle.creation.TemplateDiscovery")`).
3. Update those patch targets to the new import path.
4. Do NOT update patches targeting the automation import site -- those remain unchanged.

### 8.5 `replace_all` Usage (RF-006)
When renaming `_get_field_attr` -> `get_field_attr` in lifecycle/seeding.py, use `replace_all=true` in the Edit tool to update all 18 call sites atomically. Same for `_normalize_custom_fields` -> `normalize_custom_fields` (2 sites). Similarly in automation/seeding.py for internal call sites.

### 8.6 New File Conventions
- `src/autom8_asana/core/timing.py` (RF-001): Module docstring, single function, type hints.
- `src/autom8_asana/core/creation.py` (RF-004, RF-005): Module docstring explaining shared creation primitives, free functions (not a class), type hints.

---

## 9. Attestation Table

All file:line references verified via Read tool during plan creation.

| File | Lines Verified | Purpose | Confirmed |
|------|---------------|---------|-----------|
| `src/autom8_asana/core/exceptions.py` | 1-322 (full) | DRY-004 target pattern | YES |
| `src/autom8_asana/automation/pipeline.py` | 35-46, 191-500, 510-579, 615-627 | DRY-003, DRY-004, DRY-001, DRY-007 | YES |
| `src/autom8_asana/automation/seeding.py` | 25-44, 67-119, 123-134 | DRY-004 dead code, BOUNDARY-001 functions | YES |
| `src/autom8_asana/automation/events/rule.py` | 185-191 | DRY-003 definition | YES |
| `src/autom8_asana/lifecycle/engine.py` | 694-700 | DRY-003 definition | YES |
| `src/autom8_asana/lifecycle/creation.py` | 1-50, 100-493, 640-684 | DRY-001, DRY-007 | YES |
| `src/autom8_asana/lifecycle/seeding.py` | 1-306 (full) | BOUNDARY-001 | YES |
| `src/autom8_asana/models/business/business.py` | 70-96 | DC-002 | YES |
| `src/autom8_asana/models/business/__init__.py` | 1-237 (full) | DC-002, AR-001, IM-001, BOUNDARY-003 | YES |
| `src/autom8_asana/models/business/_bootstrap.py` | 1-151 (full) | BOUNDARY-003 | YES |
| `src/autom8_asana/models/business/hydration.py` | 740-779 | DC-002 mapping | YES |
| `src/autom8_asana/models/business/registry.py` | 235-244 | DC-002 special cases | YES |
| `src/autom8_asana/__init__.py` | 1-237 (full) | IM-002 | YES |
| `src/autom8_asana/api/preload/__init__.py` | 1-8 (full) | DC-001 | YES |
| `src/autom8_asana/api/preload/progressive.py` | 230-264 | DC-001 fallback | YES |
| `src/autom8_asana/automation/__init__.py` | 1-119 (full) | AR-001 | YES |
| `tests/unit/models/business/test_holder_factory.py` | 410-433 | DC-002 tests | YES |
| `tests/unit/models/business/test_registry.py` | 215-221 | DC-002 tests | YES |
| `tests/unit/automation/test_pipeline.py` | 590-608 | DRY-003 test | YES |

---

## 10. Handoff Checklist

- [x] Every smell classified (addressed, deferred with reason, or dismissed)
- [x] Each refactoring has before/after contract documented
- [x] Invariants and verification criteria specified
- [x] Refactorings sequenced with explicit dependencies
- [x] Rollback points identified between phases
- [x] Risk assessment complete for each phase
- [x] CX-001/CX-002 placement decided (DEFER to WS8)
- [x] DC-001 investigated (legacy preload is degraded-mode fallback, not dead)
- [x] Artifacts verified via Read tool with attestation table
