# Context Architecture: WS5-WS7 Hygiene Sprint

**Author**: Context Engineer (consultation 4)
**Date**: 2026-02-18
**Predecessor**: WS4 SMELL-REPORT-WS4.md (Code Smeller, complete)
**Pipeline**: Architect Enforcer -> Janitor -> Audit Lead (per hygiene rite)

---

## 1. Token Budget Analysis Per Agent Per WS

### Source Line Counts (Pre-Computed)

| File | Lines | WS5 | WS6 | WS7 |
|------|-------|-----|-----|-----|
| automation/pipeline.py | 1,085 | DRY-003,DRY-004 | DRY-001,DRY-007,BOUNDARY-002 | - |
| automation/seeding.py | 928 | DRY-004 | BOUNDARY-001 | - |
| automation/events/rule.py | 191 | DRY-003 | - | - |
| lifecycle/engine.py | 893 | DRY-003 | - | - |
| lifecycle/creation.py | 826 | - | DRY-001,DRY-007,BOUNDARY-002 | - |
| lifecycle/seeding.py | 305 | - | BOUNDARY-001 | - |
| models/business/business.py | 813 | DC-002 | - | - |
| models/business/__init__.py | 237 | DC-002 | - | AR-001,IM-001,BOUNDARY-003 |
| models/business/_bootstrap.py | ~140 | - | - | BOUNDARY-003 |
| models/business/hydration.py (L740-775) | ~35 | DC-002 | - | - |
| models/business/registry.py (L239) | ~1 | DC-002 | - | - |
| root __init__.py | 236 | - | - | IM-002 |
| persistence/__init__.py | 157 | - | - | AR-001 |
| automation/__init__.py | 118 | - | - | AR-001 |
| automation/polling/__init__.py | 131 | - | - | AR-001 |
| lifecycle/__init__.py | 113 | - | - | AR-001 |
| models/business/detection/__init__.py | 128 | - | - | AR-001 |
| api/preload/legacy.py | 613 | - | - | DC-001 |
| api/preload/progressive.py (L258-260) | ~3 | - | - | DC-001 |
| api/preload/__init__.py | 8 | - | - | DC-001 |
| core/exceptions.py | 321 | DRY-004 | - | - |
| automation/templates.py | 215 | - | shared primitive | - |
| automation/waiter.py | 143 | - | shared primitive | - |
| lifecycle/init_actions.py | 594 | - | creation caller | - |

### Test File Counts

| Test File | Lines | WS |
|-----------|-------|-----|
| tests/unit/automation/test_pipeline.py | 1,731 | WS5,WS6 |
| tests/unit/automation/test_pipeline_hierarchy.py | 373 | WS6 |
| tests/unit/automation/test_seeding.py | 1,001 | WS5,WS6 |
| tests/unit/automation/test_seeding_write.py | 636 | WS6 |
| tests/unit/automation/workflows/test_pipeline_transition.py | 736 | WS6 |
| tests/unit/lifecycle/test_creation.py | 1,353 | WS6 |
| tests/unit/lifecycle/test_engine.py | 1,066 | WS5,WS6 |
| tests/unit/lifecycle/test_seeding.py | 214 | WS6 |
| tests/unit/lifecycle/test_init_actions.py | 1,198 | WS6 |
| tests/unit/models/business/test_holder_factory.py | 474 | WS5 |
| tests/unit/models/business/test_registry.py | 371 | WS5 |
| tests/unit/models/business/test_hydration.py | 1,909 | WS5 |
| tests/unit/api/test_preload_parquet_fallback.py | 310 | WS7 |
| tests/unit/api/test_preload_lambda_delegation.py | 149 | WS7 |
| tests/api/test_startup_preload.py | 522 | WS7 |

### Architect Enforcer Token Budgets

**WS5 (Utility Consolidation)**: ~3,900 source lines + ~5,500 test lines = ~9,400 lines
- Comfortably single-turn. The Architect reads targeted line ranges, not full files.
- Minimum read set: pipeline.py:38-42,499-500 + seeding.py:25-36 + rule.py:190-191 + engine.py:698-700 + business.py:81-95 + exceptions.py (full, 321 lines) + hydration.py:740-775 + registry.py:239
- Estimated actual read: ~800 lines of source, ~200 lines of test references.

**WS6 (Pipeline Creation Convergence)**: ~5,500 source lines + ~7,300 test lines = ~12,800 lines
- BORDERLINE single-turn for Architect. The Architect must understand BOTH creation paths end-to-end (pipeline.py:191-497, creation.py:103-493) plus seeding.py boundary crossings.
- Strategy: Pre-computed intelligence below eliminates exploratory reads. The Architect reads targeted sections, not full files.
- Minimum read set: pipeline.py:191-500 (310 lines) + creation.py:103-493 (390 lines) + lifecycle/seeding.py (full, 305 lines) + automation/seeding.py:164-230 (66 lines) + templates.py:20-60 (40 lines) + waiter.py:24-65 (41 lines) + init_actions.py:393-492 (100 lines)
- Estimated actual read: ~1,250 lines source, ~300 lines test references.
- VERDICT: Fits single turn if pre-computed intelligence is loaded.

**WS7 (Import Architecture + Dead Code)**: ~2,500 source lines + ~1,000 test lines = ~3,500 lines
- Comfortably single-turn. Import hygiene is pattern-based, not logic-deep.
- HOWEVER: The Architect must understand the `register_all_models()` side-effect chain and verify legacy.py dead code status.
- Minimum read set: models/business/__init__.py (full, 237 lines) + _bootstrap.py (~140 lines) + detection/tier1.py:93-105 + legacy.py:26-40 + progressive.py:258-260 + api/preload/__init__.py (8 lines) + api/lifespan.py:22,151 + root __init__.py:32-69 (37 lines)
- Estimated actual read: ~500 lines source, ~100 lines test references.

### Summary

| WS | Architect Source Read | Architect Test Read | Single Turn? |
|----|----------------------|--------------------|----|
| WS5 | ~800 lines | ~200 lines | YES |
| WS6 | ~1,250 lines | ~300 lines | YES (with pre-computed intel) |
| WS7 | ~500 lines | ~100 lines | YES |

No workstream exceeds single-turn Architect budget. WS6 is the densest, but the pre-computed intelligence below eliminates the need for exploratory reads.

---

## 2. Pre-Computed Intelligence for Architect Enforcer

### WS5: Utility Consolidation

#### DRY-003: `_elapsed_ms()` (3 identical implementations)

**Definitions** (all identical one-liner `(time.perf_counter() - start_time) * 1000`):
- `automation/pipeline.py:499` -- `PipelineConversionRule._elapsed_ms(self, start_time)`
- `lifecycle/engine.py:698` -- `LifecycleEngine._elapsed_ms(self, start_time)`
- `automation/events/rule.py:190` -- `BaseAutomationRule._elapsed_ms(self, start_time)`

**Call sites** (all use `self._elapsed_ms(start_time)` in structured log kwargs):
- pipeline.py: 6 call sites (lines 232, 255, 273, 300, 478, 495)
- engine.py: 5 call sites (lines 370, 598, 624, 671, 722)
- rule.py: 2 call sites (lines 123, 147)

**Test coverage**:
- `tests/unit/automation/test_pipeline.py:592-604` -- Tests `_elapsed_ms` via `rule._elapsed_ms(start)` on PipelineConversionRule
- No direct tests for engine.py or rule.py `_elapsed_ms` (tested indirectly via timing assertions)

**Candidate target**: Free function in `core/timing.py` (new file, 3 lines) or inline in each call site since it is a one-liner. Architect decides.

**Mock target change risk**: NONE. `_elapsed_ms` is not mocked in any test file.

#### DRY-004: `_ASANA_API_ERRORS` tuple (2 definitions)

**Definitions** (identical `(AsanaError, ConnectionError, TimeoutError)`):
- `automation/pipeline.py:38-42` -- defined + used in 6 except clauses (lines 621, 662, 733, 780, 864, 917)
- `automation/seeding.py:32-36` -- defined but NEVER USED in any except clause

**Candidate target**: `core/exceptions.py` already has `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`. Add `ASANA_API_ERRORS` (public name, drop underscore) following the same pattern.

**Test coverage**: No tests reference `_ASANA_API_ERRORS` directly.

**Critical detail**: `seeding.py` defines the tuple but never catches it. The definition at seeding.py:32-36 is effectively dead code. Architect should note: remove from seeding.py, consolidate to core/exceptions.py, update pipeline.py imports.

#### DC-002: `ReconciliationsHolder` deprecated alias

**Definition**: `models/business/business.py:81-95` (15 lines, deprecation warning class)

**Live references in source** (ALL must be updated or removed):
1. `models/business/__init__.py:83` -- import + re-export
2. `models/business/__init__.py:179` -- in `__all__` list
3. `models/business/__init__.py:24` -- docstring mention
4. `models/business/hydration.py:749` -- import in `_entity_type_to_class()`
5. `models/business/hydration.py:769` -- dict entry `EntityType.RECONCILIATIONS_HOLDER: ReconciliationsHolder`
6. `models/business/registry.py:239` -- string mapping `"ReconciliationsHolder": "RECONCILIATIONS_HOLDER"`

**Live references in tests** (must update):
1. `tests/unit/models/business/test_registry.py:219` -- `_class_name_to_entity_type("ReconciliationsHolder")`
2. `tests/unit/models/business/test_holder_factory.py:413-432` -- 6 lines testing deprecation warning + inheritance

**Root __init__.py**: ReconciliationsHolder is NOT exported from root `__init__.py`.

**EntityType enum**: `RECONCILIATIONS_HOLDER` exists in the EntityType enum. The Architect must decide: remove the enum value (breaking) or keep it mapping to `ReconciliationHolder` (non-breaking).

**hydration.py:769**: Currently maps `EntityType.RECONCILIATIONS_HOLDER: ReconciliationsHolder`. After removal, this should map to `ReconciliationHolder` directly (keeps backward compatibility for any persisted EntityType values).

### WS6: Pipeline Creation Convergence

#### Import/Dependency Map

```
automation/pipeline.py
  imports: FieldSeeder (from automation/seeding.py)
           TemplateDiscovery (from automation/templates.py)
           SubtaskWaiter (from automation/waiter.py)
           Process, ProcessSection, ProcessType (from models/business)
  callers: automation/__init__.py:115 (lazy __getattr__ import)

lifecycle/creation.py
  imports: AutoCascadeSeeder (from lifecycle/seeding.py)
           TemplateDiscovery (from automation/templates.py)  <-- cross-package
           SubtaskWaiter (from automation/waiter.py)         <-- cross-package
  callers: lifecycle/__init__.py:31, lifecycle/init_actions.py:393+492,
           lifecycle/engine.py:804

lifecycle/seeding.py
  imports: FieldSeeder, _get_field_attr, _normalize_custom_fields
           (from automation/seeding.py)  <-- BOUNDARY-001: private imports
  callers: lifecycle/creation.py:38, lifecycle/__init__.py:54
```

#### Shared Creation Primitives (already shared)

| Primitive | Location | Used By Both? |
|-----------|----------|--------------|
| `TemplateDiscovery` | automation/templates.py (215 lines) | YES: pipeline.py:282, creation.py:150+272, init_actions.py:246 |
| `SubtaskWaiter` | automation/waiter.py (143 lines) | YES: pipeline.py:369, creation.py:403 |
| `FieldSeeder` | automation/seeding.py (928 lines) | pipeline.py:386 directly, creation.py via AutoCascadeSeeder |

#### The 7-Step Pipeline (side-by-side comparison)

| Step | automation/pipeline.py | lifecycle/creation.py | Identical? |
|------|----------------------|---------------------|-----------|
| 1. Template discovery | L282-290: `TemplateDiscovery.find_template_task_async()` | L150-160,L272-280: same | YES |
| 2. Task duplication | L295-310: `tasks.duplicate_async(gid, name, include)` | L155-170,L276-290: same | YES |
| 3. Name generation | L312+L510-579: `_generate_task_name()` (70 lines) | L159+L645-684: `_generate_name()` (40 lines, staticmethod) | YES (identical regex) |
| 4. Section placement | L320-340: find section + `add_to_project_async` | L175-195: same | YES |
| 5. Due date | L350-365: `today() + timedelta(offset)` | L200-215: same | YES |
| 6. Subtask wait | L369-380: `SubtaskWaiter.wait_for_subtasks_async()` | L400-410: same | YES |
| 7. Field seeding | L386-395: `FieldSeeder(client).seed_async()` | L413-420: `AutoCascadeSeeder(client).seed_async()` | DIVERGED |
| 8. Hierarchy/assignee | L400-475: resolve holder + set_parent + assignee cascade | L430-490: same pattern | SIMILAR |

**Key divergence**: Step 7 (seeding). `pipeline.py` uses explicit field lists via `FieldSeeder`. `creation.py` uses zero-config name matching via `AutoCascadeSeeder`. Both ultimately call `FieldSeeder.write_fields_async()` for the actual API write.

#### DRY-007: Name Generation (duplicated regex)

**automation/pipeline.py:510-579** (`_generate_task_name`, instance method, 70 lines):
- Handles more edge cases (unit_name=None fallback, business_name=None fallback)
- Extra logic for composite names

**lifecycle/creation.py:645-684** (`_generate_name`, staticmethod, 40 lines):
- Cleaner implementation, same core regex
- Tests at test_creation.py:260-340 (80 lines, 7 test cases)
- Tests at test_pipeline.py:611-822 (211 lines, 17 test cases)

**Identical regex patterns in both**:
```python
re.sub(r"\[business\s*name\]", business_name, result, flags=re.IGNORECASE)
re.sub(r"\[(business\s*)?unit\s*name\]", unit_name, result, flags=re.IGNORECASE)
```

#### BOUNDARY-001: lifecycle/seeding.py private imports

`lifecycle/seeding.py:29-33` imports 3 private symbols from `automation/seeding.py`:
- `FieldSeeder` (public -- fine)
- `_get_field_attr` (private -- 18 call sites in lifecycle/seeding.py)
- `_normalize_custom_fields` (private -- 2 call sites in lifecycle/seeding.py)

**Resolution options** (for Architect to decide):
A. Promote `_get_field_attr` and `_normalize_custom_fields` to public API in automation/seeding.py (rename, drop underscore)
B. Extract to shared utility module (e.g., `core/custom_field_utils.py`)
C. Inline into lifecycle/seeding.py (duplicates code but eliminates cross-package coupling)

#### DSC + SaveSession (stakeholder decision: Architect decides placement)

CX-001 (DataServiceClient, 2,165 lines) and CX-002 (SaveSession, 1,853 lines) are the two god objects. Per stakeholder decision, the Architect determines whether to fold decomposition into WS6 or defer.

**Recommendation**: DEFER. These are CX (complexity) findings, not DRY or boundary violations. Each requires its own focused workstream. WS6 should stay focused on pipeline creation convergence.

### WS7: Import Architecture + Dead Code

#### AR-001: Barrel __init__.py files (7 files)

| File | Lines | Non-Import Logic | Risk |
|------|-------|-----------------|------|
| models/business/__init__.py | 237 | `register_all_models()` at import time | HIGH (side-effect) |
| root __init__.py | 236 | Re-exports from 8 subpackages | MEDIUM |
| persistence/__init__.py | 157 | Re-exports from 5 modules | LOW |
| automation/polling/__init__.py | 131 | Re-exports | LOW |
| models/business/detection/__init__.py | 128 | Re-exports | LOW |
| automation/__init__.py | 118 | `__getattr__` lazy import of PipelineConversionRule | LOW |
| lifecycle/__init__.py | 113 | Re-exports | LOW |

#### IM-001 + BOUNDARY-003: `register_all_models()` side effect

**Call chain**:
1. `models/business/__init__.py:62` calls `register_all_models()`
2. Defined in `models/business/_bootstrap.py:22`
3. Also called from `models/business/detection/tier1.py:105` (guard: ensures registration before detection)
4. Has idempotency guard (`_bootstrap.py:39`: "already complete, skipping")

**Import sites for models/business** (11 distinct files import from the barrel):
- clients/tasks.py, clients/task_ttl.py, dataframes/builders/task_cache.py
- dataframes/views/cascade_view.py, dataframes/views/dataframe_view.py
- dataframes/resolver/cascading.py, persistence/session.py
- automation/seeding.py, automation/pipeline.py, services/discovery.py
- models/business/__init__.py (self-reference in docstring example)

**Risk assessment**: Moving `register_all_models()` out of import-time requires ensuring every entry point calls it explicitly before first use. The `_bootstrap.py` idempotency guard makes this safe but requires auditing all entry points (API startup, Lambda handlers, CLI, tests).

#### DC-001: Legacy preload (dead code investigation)

**Evidence for "likely dead"**:
- `api/preload/__init__.py` only exports `_preload_dataframe_cache_progressive` (progressive)
- `api/lifespan.py:22,151` only imports/calls `_preload_dataframe_cache_progressive`
- `progressive.py:258-260` contains a fallback that calls legacy: `from .legacy import _preload_dataframe_cache; await _preload_dataframe_cache(app)`
- NO other import site for legacy.py found in any source file
- legacy.py has 2 internal `from autom8_asana import AsanaClient` imports (TYPE_CHECKING style)

**Conclusion**: legacy.py is NOT dead code -- it is called as a fallback from progressive.py:258-260. The Architect must determine:
1. Under what conditions does the progressive -> legacy fallback trigger?
2. Is that fallback path still needed?
3. Can the fallback be removed (converting legacy.py to truly dead code)?

#### IM-002: Root __init__.py imports dataframes

`root __init__.py:32-69` re-exports 37 symbols from `autom8_asana.dataframes`. This means `import autom8_asana` eagerly loads polars + DataFrame subsystem.

**Impact**: Every Lambda handler, CLI tool, or script that does `from autom8_asana import AsanaClient` pays the dataframes import cost. 15 files import `AsanaClient` from root.

#### IM-003: Inline deferred imports (12+ instances)

**BOUNDARY-004 (bidirectional dependency)**:
- `services/universal_strategy.py:23` imports `to_pascal_case` from resolver (top-level)
- `services/universal_strategy.py:156,326` imports `validate_criterion_for_entity` from resolver (deferred)
- `services/resolver.py:26` imports `UniversalResolutionStrategy` (TYPE_CHECKING)
- `services/resolver.py:712` imports `get_universal_strategy` (deferred)

This is a genuine circular dependency resolved via deferred imports. The Architect should note this as an observation, not necessarily a fix target for WS7 (fixing would require interface extraction or dependency inversion).

---

## 3. Cross-WS Dependencies

### Critical Ordering Analysis

```
WS5 (Utility Consolidation)
  Touches: pipeline.py, seeding.py, engine.py, rule.py, business.py, exceptions.py

WS6 (Pipeline Creation Convergence)
  Touches: pipeline.py, creation.py, seeding.py (both), templates.py, waiter.py

WS7 (Import Architecture + Dead Code)
  Touches: models/business/__init__.py, root __init__.py, other __init__ files, legacy.py
```

### Dependency Matrix

| Dependency | Impact | Ordering Requirement |
|-----------|--------|---------------------|
| WS5 moves `_elapsed_ms` from pipeline.py; WS6 modifies pipeline.py:191-497 | MERGE CONFLICT risk if parallel | WS5 BEFORE WS6 |
| WS5 moves `_ASANA_API_ERRORS` from pipeline.py; WS6 modifies pipeline.py | Same file, different regions (L38 vs L191+) | WS5 BEFORE WS6 (avoids rebase) |
| WS5 removes `ReconciliationsHolder`; WS7 modifies models/business/__init__.py | WS5 deletes from __init__.py; WS7 restructures __init__.py | WS5 BEFORE WS7 |
| WS6 extracts creation primitives; WS7 restructures barrel __init__.py | WS6 may change what automation/__init__.py exports | WS6 BEFORE WS7 |
| WS5 `_ASANA_API_ERRORS` -> core/exceptions.py; WS6 pipeline refactor uses it | WS6 Janitor needs the new import path | WS5 BEFORE WS6 |

### Recommended Execution Order

**WS5 -> WS6 -> WS7** (strictly sequential)

Rationale:
1. WS5 is quick wins (1 day). Removes noise from files WS6 and WS7 touch.
2. WS6 is the highest-ROI workstream. Must complete before WS7 because it may change export surfaces that WS7 restructures.
3. WS7 is the cleanup pass. After WS5+WS6, the barrel files will have fewer exports to manage.

---

## 4. Anti-Patterns and Context Traps

### For Architect Enforcer

1. **Mock target path trap (WS5, WS6)**: When extracting `_elapsed_ms` to a shared module, the Architect must specify the new import path precisely. If any test patches `automation.pipeline.PipelineConversionRule._elapsed_ms`, the patch target changes. VERIFIED: no test mocks `_elapsed_ms`, so this trap is CLEAR for WS5.

2. **FieldSeeder mock targets (WS6)**: Tests mock `automation.seeding.FieldSeeder` at the import site. If WS6 moves FieldSeeder or changes import paths, all mock targets must be updated. 11 distinct import sites reference FieldSeeder.

3. **`_ASANA_API_ERRORS` dead definition (WS5)**: `seeding.py:32-36` defines the tuple but NEVER catches it. The Architect should flag this as dead code removal, not consolidation.

4. **ReconciliationsHolder -> EntityType.RECONCILIATIONS_HOLDER (WS5)**: The EntityType enum value must remain (backward compat) but should map to `ReconciliationHolder` directly. DO NOT delete the enum value.

5. **`register_all_models()` test dependency (WS7)**: Root conftest.py resets 4 registries including registration state. Moving `register_all_models()` to explicit init requires the conftest to call it explicitly. The Architect must audit `conftest.py` reset logic.

6. **Progressive -> legacy fallback (WS7)**: `progressive.py:258-260` calls legacy as fallback. The Architect must read progressive.py:250-265 to understand the trigger condition before declaring legacy.py dead.

### For Janitor

1. **Import-time side effects (WS7)**: Moving `register_all_models()` out of `__init__.py` means any code that previously imported from `models.business` no longer triggers registration. The Janitor must add explicit `register_all_models()` calls at EVERY entry point (API lifespan, Lambda handlers, CLI commands, test conftest). Missing one = silent failures.

2. **Seeding boundary violation fix order (WS6)**: `_get_field_attr` and `_normalize_custom_fields` are called 20 times in lifecycle/seeding.py. If the Janitor renames/moves these functions, ALL 20 call sites must update atomically. Use `replace_all` in Edit tool.

3. **Test mock path updates (WS6)**: When extracting shared creation primitives, the mock target path changes. The Janitor must grep for the OLD path in all test files and update. Common pattern: `@patch("autom8_asana.automation.pipeline.TemplateDiscovery")`.

4. **Pipeline.py is 1,085 lines (WS6)**: After WS5 removes `_elapsed_ms` (1 line) and `_ASANA_API_ERRORS` (5 lines), the WS6 Janitor works with a slightly cleaner file. Confirms WS5-before-WS6 ordering.

5. **Green-to-green gates**: Run `.venv/bin/pytest tests/ -x -q --timeout=60` after EVERY commit. Pre-existing failures: test_adversarial_pacing.py, test_paced_fetch.py (checkpoint assertions -- ignore).

---

## 5. Checkpoint Templates

### WS5-CHECKPOINT.md Template

```markdown
# WS5 Checkpoint: Utility Consolidation

**Updated**: [DATE]
**Sprint**: [PHASE]
**Status**: [STATUS]

## Sprint Scope
Quick-win utility consolidation: DRY-003, DRY-004, DC-002.

## Completed
- WS5-Arch: Refactoring plan at [LOCATION] (Architect Enforcer [THREAD_ID])
- WS5-S1: [DESCRIPTION] (Janitor [THREAD_ID]) -- [TEST_COUNT] passed
  - DRY-003: _elapsed_ms [RESOLUTION]
  - DRY-004: _ASANA_API_ERRORS [RESOLUTION]
  - DC-002: ReconciliationsHolder [RESOLUTION]
- WS5-QA: [DESCRIPTION] (Audit Lead [THREAD_ID])

## Decisions
- [DECISION_LOG]

## Key File Pointers
| Domain | Files |
|--------|-------|
| Shared timing | [TARGET_FILE] |
| Error tuples | core/exceptions.py (ASANA_API_ERRORS) |
| Deprecated alias removal | models/business/business.py |

## Pre-existing Failures
- test_adversarial_pacing.py, test_paced_fetch.py (checkpoint assertions)

## Next
WS6 (Pipeline Creation Convergence)
```

### WS6-CHECKPOINT.md Template

```markdown
# WS6 Checkpoint: Pipeline Creation Convergence

**Updated**: [DATE]
**Sprint**: [PHASE]
**Status**: [STATUS]

## Sprint Scope
Pipeline creation convergence: DRY-001, AR-002, DRY-007, NM-001, BOUNDARY-001, BOUNDARY-002.

## Completed
- WS6-Arch: Refactoring plan at [LOCATION] (Architect Enforcer [THREAD_ID])
- WS6-S1: [DESCRIPTION] (Janitor [THREAD_ID]) -- [TEST_COUNT] passed
  - DRY-001: Shared creation engine [RESOLUTION]
  - DRY-007: Name generation [RESOLUTION]
  - BOUNDARY-001: Private import resolution [RESOLUTION]
  - BOUNDARY-002: Shared service layer [RESOLUTION]
- WS6-QA: [DESCRIPTION] (Audit Lead [THREAD_ID])

## Decisions
- Pipeline direction: Lifecycle canonical for CRM/Process, automation for other workflows
- DSC + SaveSession: [ARCHITECT_DECISION]
- [DECISION_LOG]

## Key File Pointers
| Domain | Files |
|--------|-------|
| Creation engine | [TARGET_FILE] |
| Pipeline (automation) | automation/pipeline.py |
| Creation (lifecycle) | lifecycle/creation.py |
| Seeding boundary | [RESOLUTION_FILES] |

## Pre-existing Failures
- test_adversarial_pacing.py, test_paced_fetch.py (checkpoint assertions)

## Next
WS7 (Import Architecture + Dead Code)
```

### WS7-CHECKPOINT.md Template

```markdown
# WS7 Checkpoint: Import Architecture + Dead Code

**Updated**: [DATE]
**Sprint**: [PHASE]
**Status**: [STATUS]

## Sprint Scope
Import cleanup and dead code removal: AR-001, IM-001, IM-002, IM-003, DC-001, BOUNDARY-003.

## Completed
- WS7-Arch: Refactoring plan at [LOCATION] (Architect Enforcer [THREAD_ID])
- WS7-S1: [DESCRIPTION] (Janitor [THREAD_ID]) -- [TEST_COUNT] passed
  - AR-001: Barrel __init__ cleanup [RESOLUTION]
  - IM-001: register_all_models [RESOLUTION]
  - IM-002: Root __init__ lazy loading [RESOLUTION]
  - DC-001: Legacy preload [RESOLUTION]
  - BOUNDARY-003: Import side-effect [RESOLUTION]
- WS7-QA: [DESCRIPTION] (Audit Lead [THREAD_ID])

## Decisions
- register_all_models placement: [DECISION]
- Legacy preload: [INVESTIGATION_RESULT]
- IM-003 deferred imports: [DECISION]
- [DECISION_LOG]

## Key File Pointers
| Domain | Files |
|--------|-------|
| Business model barrel | models/business/__init__.py |
| Bootstrap | models/business/_bootstrap.py |
| Root barrel | __init__.py |
| Legacy preload | api/preload/legacy.py |
| Progressive preload | api/preload/progressive.py |

## Pre-existing Failures
- test_adversarial_pacing.py, test_paced_fetch.py (checkpoint assertions)

## Next
[Initiative review or next initiative]
```

---

## 6. Architect Enforcer Loading Strategy

Each Architect Enforcer invocation should load this document as the primary context brief. The Architect does NOT need to re-read the full SMELL-REPORT-WS4.md -- the relevant findings are pre-extracted above.

### Per-WS Loading Sequence

**WS5 Architect Enforcer invocation**:
1. Load: This document (Section 2, WS5 subsection only)
2. Read: `core/exceptions.py` (full, 321 lines -- to understand existing pattern)
3. Read: `models/business/business.py:70-96` (ReconciliationsHolder definition)
4. Read: `models/business/hydration.py:740-775` (type_to_class mapping)
5. Produce: Refactoring plan with 3 contracts (DRY-003, DRY-004, DC-002)

**WS6 Architect Enforcer invocation**:
1. Load: This document (Section 2, WS6 subsection only)
2. Read: `automation/pipeline.py:191-500` (execute_async + _generate_task_name)
3. Read: `lifecycle/creation.py:100-500` (create_process_async + _configure_async)
4. Read: `lifecycle/seeding.py` (full, 305 lines -- boundary violation)
5. Optionally: `automation/seeding.py:164-230` (FieldSeeder class header)
6. Produce: Refactoring plan with shared creation engine design

**WS7 Architect Enforcer invocation**:
1. Load: This document (Section 2, WS7 subsection only)
2. Read: `models/business/__init__.py` (full, 237 lines)
3. Read: `models/business/_bootstrap.py` (full, ~140 lines)
4. Read: `api/preload/progressive.py:250-265` (legacy fallback trigger)
5. Read: `api/lifespan.py:20-25,148-155` (startup preload call)
6. Produce: Refactoring plan for import architecture + dead code assessment

---

## 7. INITIATIVE-INDEX Update Template

After all WS5-WS7 are complete, update `.claude/wip/INITIATIVE-INDEX.md`:

```markdown
| WS | Status | Checkpoint | Domain |
|----|--------|-----------|--------|
| WS5 | COMPLETE | .claude/wip/WS5-CHECKPOINT.md (commit [HASH]) | Utility consolidation |
| WS6 | COMPLETE | .claude/wip/WS6-CHECKPOINT.md (commit [HASH]) | Pipeline convergence |
| WS7 | COMPLETE | .claude/wip/WS7-CHECKPOINT.md (commit [HASH]) | Import architecture |
```

Add to Execution History:
```markdown
| WS5-Arch | Utility consolidation plan | Architect Enforcer [ID] | (design only) |
| WS5-S1 | DRY-003+DRY-004+DC-002 | Janitor [ID] | [HASH] |
| WS5-QA | Validation | Audit Lead [ID] | (validation only) |
| WS6-Arch | Pipeline convergence plan | Architect Enforcer [ID] | (design only) |
| WS6-S1 | Creation engine extraction | Janitor [ID] | [HASH] |
| WS6-QA | Validation | Audit Lead [ID] | (validation only) |
| WS7-Arch | Import architecture plan | Architect Enforcer [ID] | (design only) |
| WS7-S1 | Barrel cleanup + dead code | Janitor [ID] | [HASH] |
| WS7-QA | Validation | Audit Lead [ID] | (validation only) |
```
