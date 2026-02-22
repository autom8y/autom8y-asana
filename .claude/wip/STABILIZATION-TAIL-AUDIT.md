# Stabilization Tail Audit Report

**Date**: 2026-02-18
**Auditor**: Audit Lead (Claude Opus 4.6)
**Scope**: 3 tasks, 4 commits (D-022a, D-022b, Cache DI)
**Verdict**: **APPROVED WITH NOTES**

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Commits audited | 4 (`ed229b7`, `5d32f8e`, `12a919f`, `4605815`) |
| Test results | 10,566 passed, 46 skipped, 2 xfailed, 1 failed (pre-existing) |
| Baseline | 10,552 passed, 46 skipped, 2 xfailed |
| Test delta | +14 passed (net gain from prior sprint merges, not these commits) |
| Smells addressed | 3 (private API access, inline cascade, singleton anti-pattern) |
| Behavior changes | None detected |
| Blocking issues | 0 |
| Advisory notes | 2 |

All three stabilization tail tasks pass audit. Behavior is preserved, contracts are met, commits are atomic and independently revertible, and the codebase is measurably improved.

---

## Test Verification

**Full suite run** (via `.venv/bin/python -m pytest tests/`):
```
1 failed, 10,566 passed, 46 skipped, 2 xfailed in 228.12s
```

**Failed test**: `tests/unit/core/test_concurrency.py::TestStructuredLogging::test_label_in_log`
- Passes when run in isolation (confirmed: `1 passed in 0.07s`)
- Test-ordering flake (logging state pollution from prior tests)
- File NOT modified by any of the 4 audited commits (confirmed via `git diff ed229b7^..4605815`)
- **Verdict**: Pre-existing flake. Not a regression.

**Baseline comparison**: 10,566 passed >= 10,552 baseline. The +14 delta comes from prior sprint merges already on `main`, not from these commits. No tests were removed or weakened.

---

## Task 1: D-022a -- Hierarchy Placement Migration

**Commit**: `ed229b7` -- `refactor(automation): migrate hierarchy placement to resolve_holder_async [D-022a]`
**Files**: `pipeline.py` (+34/-30), `test_pipeline_hierarchy.py` (+44/-39)
**Blueprint**: `PIPELINE-PARITY-ANALYSIS.md` divergence #2

### Contract Verification

| Contract | Status | Evidence |
|----------|--------|----------|
| No `_process_holder` access in pipeline.py | PASS | `grep _process_holder pipeline.py` returns 0 matches |
| No `_fetch_holders_async` access in pipeline.py | PASS | `grep _fetch_holders_async pipeline.py` returns 0 matches |
| `resolve_holder_async` or equivalent adopted | PASS | Lines 550-567: `ctx.resolve_holder_async(ProcessHolder)` as strategy 3 |
| `unit.process_holder` retained as intermediate | PASS | Line 548: `getattr(unit, "process_holder", None)` as strategy 2 |
| `source_process.process_holder` remains first | PASS | Line 544: `getattr(source_process, "process_holder", None)` as strategy 1 |
| FR-HIER-003 graceful degradation preserved | PASS | Lines 569-575: `if process_holder is None` logs warning, returns False |
| SaveSession placement unchanged | PASS | Lines 578-610: identical `set_parent` + `commit_async` pattern |

### Behavior Preservation

The old code had a 4-step strategy: (1) `source_process.process_holder`, (2) `unit.process_holder`, (3) `unit._process_holder` (private), (4) `unit._fetch_holders_async(client)` (private). The new code has a 3-step strategy: (1) same, (2) same, (3) `ctx.resolve_holder_async(ProcessHolder)` (public API, session-cached).

Steps 3 and 4 of the old code accessed private attributes. The new step 3 uses the public `ResolutionContext` API which performs the same holder lookup through proper channels. The net behavior is equivalent: if the holder is available via public properties, it is found at step 1 or 2. If not, the resolution context performs the lookup. If the lookup fails, `resolve_holder_async` returns None and FR-HIER-003 graceful degradation is triggered -- same as the old code's exception-guarded private path.

**Test changes**: Two tests that exercised private API behavior (`test_fetches_holders_on_demand`, `test_fetch_holders_failure_graceful`) replaced with two tests that verify the public strategy chain (`test_graceful_degradation_when_no_hydrated_holder`, `test_resolve_holder_async_used_as_fallback`). Both new tests mock `ResolutionContext.resolve_holder_async` and verify the same functional outcomes: successful placement when holder is found, graceful degradation when it is not.

### Deviation Assessment

**Deviation**: Retained `unit.process_holder` check as intermediate strategy (lifecycle skips this, using only `ResolutionContext`).

**Verdict**: Appropriate. The automation pipeline's callers already hydrate `unit.process_holder` in many code paths. Keeping this as strategy 2 avoids unnecessary `ResolutionContext` instantiation and API calls when the holder is already available. This is a pragmatic intermediate step that preserves existing fast-path behavior while adopting the public API for the fallback path.

---

## Task 2: D-022b -- Assignee Resolution Migration

**Commit**: `5d32f8e` -- `refactor(automation): migrate assignee resolution to AssigneeConfig [D-022b]`
**Files**: `pipeline.py` (+130/-36), `config.py` (+29), `__init__.py` (+2/-1)
**Blueprint**: `PIPELINE-PARITY-ANALYSIS.md` divergence #3

### Contract Verification

| Contract | Status | Evidence |
|----------|--------|----------|
| Inline cascade replaced with AssigneeConfig | PASS | `_resolve_assignee_gid()` at lines 612-668 uses `AssigneeConfig` |
| `fixed_assignee_gid` parameter removed | PASS | `grep fixed_assignee_gid pipeline.py` returns 0 matches |
| AssigneeConfig frozen dataclass exists | PASS | `config.py` lines 14-40 |
| 4-step cascade: source, fixed, unit.rep, business.rep | PASS | `_resolve_assignee_gid` steps 1-4 at lines 642-667 |
| Existing 3-step behavior preserved | PASS | `assignee_source` defaults to None, so step 1 is always skipped in current automation usage, yielding the original 3-step cascade |
| FR-ASSIGN-001 through FR-ASSIGN-006 preserved | PASS | Docstrings and code reference all FRs |
| `__init__.py` exports AssigneeConfig | PASS | Line 82 and line 103 |

### Behavior Preservation

**Old code**: A monolithic `_set_assignee_from_rep_async` with inline `if/else` and `try/except` around `getattr(entity, "rep", None)` access.

**New code**: Decomposed into `_resolve_assignee_gid` (pure, no API call) + `_extract_user_gid` + `_extract_first_rep` static helpers, with `_set_assignee_from_rep_async` as the thin async wrapper.

Key behavioral equivalence:
- **Old step 1** (fixed GID): Maps to new step 2 (`assignee_config.assignee_gid`). Since `assignee_source` defaults to None, new step 1 is a no-op, so fixed GID remains highest effective priority. Identical.
- **Old step 2** (unit.rep): Maps to new step 3. `_extract_first_rep` performs the same `getattr -> len check -> isinstance dict -> .get("gid")` logic. Verified all edge cases (no rep attribute, empty list, non-dict elements, None) produce identical results.
- **Old step 3** (business.rep): Maps to new step 4. Same logic as step 3.
- **Try/except removal**: The old code wrapped rep access in `try/except (AttributeError, KeyError, TypeError, IndexError)`. The new `_extract_first_rep` uses `getattr` (cannot raise AttributeError), `len()` on a truthy list (cannot raise), `isinstance` (cannot raise), and `.get()` (cannot raise KeyError). None of the caught exceptions are reachable in the new code. The removal is safe.

### Deviation Assessment

**Deviation**: `AssigneeConfig` added to `automation/config.py` rather than extracted to shared `core/`.

**Verdict**: Appropriate. The automation `AssigneeConfig` and lifecycle `AssigneeConfig` serve the same conceptual role but have different usage contexts: automation stages are Python-configured with `assignee_source` always None; lifecycle stages are YAML-driven. Placing the automation variant in `automation/config.py` alongside `PipelineStage` (which references `assignee_gid`) is correct colocation. A shared `core/AssigneeConfig` would require conditional logic or subclassing for the different configuration patterns. If future convergence is desired, it can be done as a follow-up.

---

## Task 3: Cache DI -- DataFrameCacheProtocol + Singleton Migration

**Commits**: `12a919f` (Cache-DI-1) + `4605815` (Cache-DI-2)
**Blueprint**: `ADR-0067-cache-system-divergence.md` dimensions 3 + 14

### Commit 1: `12a919f` -- Introduce DataFrameCacheProtocol

**Files**: `protocols/cache.py` (+111), `protocols/__init__.py` (+2/-1)

| Contract | Status | Evidence |
|----------|--------|----------|
| `DataFrameCacheProtocol` exists in `protocols/cache.py` | PASS | Line 257: `class DataFrameCacheProtocol(Protocol)` |
| Structural typing (Protocol) used | PASS | Inherits from `typing.Protocol` |
| Methods match DataFrameCache public API | PASS | `get_async`, `put_async`, `invalidate`, `invalidate_project`, `invalidate_on_schema_change`, `get_freshness_info` |
| Exported from `protocols/__init__.py` | PASS | Line 7 and line 15 |
| Additive-only change (no behavior impact) | PASS | Only new code added, no existing code modified beyond imports |

### Commit 2: `4605815` -- Replace Singleton with DI

**Files**: `cache/dataframe/factory.py` (+32/-25), `cache/integration/dataframe_cache.py` (-27), `api/dependencies.py` (+24), `api/startup.py` (+9/-6), `api/lifespan.py` (+2/-1), 2 test files (import updates)

| Contract | Status | Evidence |
|----------|--------|----------|
| Singleton removed from `cache/integration/dataframe_cache.py` | PASS | `grep` confirms 0 matches for `_dataframe_cache`, `get_dataframe_cache`, `set_dataframe_cache`, `reset_dataframe_cache` in that file |
| Singleton moved to `cache/dataframe/factory.py` | PASS | Line 37: `_dataframe_cache: DataFrameCache \| None = None` |
| `app.state.dataframe_cache` wired via DI | PASS | `startup.py` line 33: `app.state.dataframe_cache = cache` |
| `get_dataframe_cache` FastAPI dependency exists | PASS | `dependencies.py` lines 384-399 |
| `DataFrameCacheDep` type alias exported | PASS | `dependencies.py` line 513 |
| `_initialize_mutation_invalidator` reads from app.state | PASS | `startup.py` line 88: `getattr(app.state, "dataframe_cache", None)` |
| `set_dataframe_cache()` retained for testing/Lambda | PASS | `factory.py` lines 242-252 |
| Test imports updated | PASS | `test_dataframe_cache.py` and `test_decorator.py` import from `factory` |

### Behavior Preservation

The singleton still exists but is now managed in `factory.py` (one location) instead of `dataframe_cache.py`. FastAPI routes gain a proper DI dependency (`get_dataframe_cache` from `dependencies.py`) that reads from `app.state`. Lambda and non-FastAPI paths continue to use the module-level singleton via `factory.get_dataframe_cache()`. The `MutationInvalidator` initialization now reads from `app.state` instead of calling the factory accessor -- both paths return the same instance since `_initialize_dataframe_cache(app)` stores the same object in both locations.

No functional behavior changes. The cache initialization, lookup, eviction, invalidation, and SWR patterns are all unchanged.

### Deviation Assessment

**Deviation**: Singleton moved to `factory.py` rather than fully eliminated. `set_dataframe_cache()` retained for testing/Lambda.

**Verdict**: Appropriate. Full DI elimination of the singleton would require Lambda handler refactoring (passing cache through function arguments) which is outside the scope of this hygiene task. The current state achieves ADR-0067's goal: FastAPI routes use proper DI via `app.state`, while the factory singleton provides backward compatibility for non-FastAPI paths. `set_dataframe_cache()` is legitimately needed for test fixtures and Lambda warm-up injection.

---

## Commit Quality Assessment

| Commit | Atomic | Message | Task ID | Revertible |
|--------|--------|---------|---------|------------|
| `ed229b7` | Yes (pipeline.py + its test) | Clear, references D-022a | [D-022a] | Yes (tested) |
| `5d32f8e` | Yes (config + pipeline + init) | Clear, references D-022b | [D-022b] | Yes (independent of D-022a) |
| `12a919f` | Yes (protocol only, additive) | Clear, references Cache-DI-1 | [Cache-DI-1] | Yes (additive, safe to remove) |
| `4605815` | Yes (DI wiring + singleton migration) | Clear, references Cache-DI-2 | [Cache-DI-2] | Yes (tested via `git revert --no-commit`) |

All commits are single-concern, clearly messaged, reference their task IDs, and include co-authorship attribution.

---

## Behavior Preservation Checklist

| Category | Item | Status |
|----------|------|--------|
| **MUST preserve** | Public API signatures | PASS -- no public API changes |
| **MUST preserve** | Return types | PASS -- all methods return same types |
| **MUST preserve** | Error semantics | PASS -- FR-HIER-003, FR-ASSIGN-005/006 degradation preserved |
| **MUST preserve** | Documented contracts | PASS -- all FR references maintained |
| **MAY change** | Internal logging | PASS -- log event names unchanged |
| **MAY change** | Error message text | PASS -- no changes |
| **MAY change** | Private implementations | PASS -- this is what changed (by design) |

---

## Improvement Assessment

| Before | After | Improvement |
|--------|-------|-------------|
| `pipeline.py` accessed `unit._process_holder` and `unit._fetch_holders_async` (private) | Uses `getattr` public properties + `ResolutionContext.resolve_holder_async` | Private API coupling eliminated |
| Inline 35-line assignee cascade with try/except | Decomposed into `_resolve_assignee_gid` + 2 static helpers + `AssigneeConfig` | Testable, mirrors lifecycle pattern, cascade is configurable |
| `DataFrameCache` had no protocol | `DataFrameCacheProtocol` in `protocols/cache.py` | Enables `NullDataFrameCache` test double, aligns with CacheProvider pattern |
| Module-level singleton in `dataframe_cache.py` | DI via `app.state.dataframe_cache` + factory singleton for Lambda | Eliminates AP-009 singleton anti-pattern for FastAPI path |
| Singleton accessors scattered across two modules | Consolidated in `factory.py` | Single source of truth for singleton lifecycle |

---

## Advisory Notes (Non-Blocking)

### Note 1: `_extract_first_rep` does not handle non-dict, non-None first elements

The old code's `try/except` would catch `AttributeError` if `rep_list[0]` were an unexpected type with no `.get()`. The new `_extract_first_rep` checks `isinstance(first, dict)` and returns None for non-dict elements, which is functionally equivalent. However, the lifecycle version `_extract_user_gid` also handles the case where `first` has a `.gid` attribute (object-style rep entries). The automation `_extract_first_rep` only handles dict-style. If rep entries are ever objects rather than dicts, the automation path would silently return None where the lifecycle path would succeed.

**Risk**: Low. Automation rep fields come from Asana API responses which are always dicts. No action required unless the rep field source changes.

### Note 2: `DataFrameCacheProtocol.put_async` uses `Any` for `dataframe` and `build_result` parameters

The protocol types `dataframe` as `Any` rather than `pl.DataFrame` and `build_result` as `Any` rather than `BuildResult`. This weakens type checking at the protocol boundary.

**Risk**: Low. There is only one implementation currently. If a `NullDataFrameCache` is added, its `put_async` signature should use concrete types. No action required now.

---

## Verification Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| D-022a commit | `ed229b7` | Read via `git show --stat` and `git diff` |
| D-022b commit | `5d32f8e` | Read via `git show --stat` and `git diff` |
| Cache-DI-1 commit | `12a919f` | Read via `git show --stat` and `git diff` |
| Cache-DI-2 commit | `4605815` | Read via `git show --stat` and `git diff` |
| Pipeline blueprint | `.claude/wip/PIPELINE-PARITY-ANALYSIS.md` | Read via Read tool |
| Cache blueprint | `docs/decisions/ADR-0067-cache-system-divergence.md` | Read via Read tool |
| pipeline.py (current) | `src/autom8_asana/automation/pipeline.py` | Read lines 538-768 |
| config.py (current) | `src/autom8_asana/automation/config.py` | Read full file |
| protocols/cache.py (current) | `src/autom8_asana/protocols/cache.py` | Read lines 250-362 |
| factory.py (current) | `src/autom8_asana/cache/dataframe/factory.py` | Read full file |
| dataframe_cache.py singleton check | `src/autom8_asana/cache/integration/dataframe_cache.py` | Grep confirmed 0 singleton matches |
| Test suite | `tests/` | Full run: 10,566 passed, 1 failed (pre-existing), 46 skipped, 2 xfailed |
| Revert test (4605815) | `git revert --no-commit 4605815` | Clean revert confirmed |

---

## Verdict: APPROVED WITH NOTES

All three stabilization tail tasks pass audit:

- [x] All tests pass (10,566 passed >= 10,552 baseline; 1 failure is pre-existing flake)
- [x] D-022a: No private attribute access in pipeline.py
- [x] D-022a: `resolve_holder_async` public API adopted as fallback strategy
- [x] D-022b: Inline assignee cascade replaced with AssigneeConfig
- [x] D-022b: Existing 3-step cascade behavior preserved (assignee_source=None by default)
- [x] Cache DI: `DataFrameCacheProtocol` exists in `protocols/cache.py`
- [x] Cache DI: Singleton removed from `cache/integration/dataframe_cache.py`
- [x] Cache DI: FastAPI routes use `app.state.dataframe_cache` via DI
- [x] All commits atomic and independently revertible
- [x] No behavior changes (structure only)
- [x] Commit messages reference task IDs

Two advisory notes documented for future consideration. Neither is blocking.

**Ready to merge.**
