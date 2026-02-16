# TDD: Runtime Remediation Sprint 1 -- Easy Wins

```yaml
id: TDD-RUNTIME-REM-S1
initiative: INIT-RUNTIME-REM-001
rite: 10x-dev
agent: architect
upstream: PROMPT-0-runtime-remediation.md, SMELL-runtime-efficiency-audit.md
downstream: principal-engineer
date: 2026-02-15
status: ready-for-principal-engineer
```

---

## 1. Executive Summary

Three deferred findings from the runtime efficiency audit are designed for Sprint 1. Two proceed to implementation; one is explicitly not recommended.

| ID | Finding | Score | Decision |
|----|---------|:-----:|----------|
| AT2-003 | Freshness delta sequential added GID fetch | 57 | **IMPLEMENT** -- simple `asyncio.gather` with `return_exceptions=True`; reuses existing `gather_with_limit` |
| DRY-001 | Section extraction 4x duplication | 55 | **IMPLEMENT** -- canonical `extract_section_name()` is already live (used by `offer.py`, `unit.py`); wire into 2 remaining callers, leave `Process.pipeline_state` as-is |
| AT2-005 | Lifecycle init sequential dep check | 42 | **NOT RECOMMENDED** -- early-return benefit outweighs parallelization; see ADR below |

### Key Discovery: DRY-001 Canonical Is No Longer Orphaned

The SMELL report and spike doc state `extract_section_name()` in `activity.py:138` is orphaned. This is stale. It is now actively imported and called by:
- `src/autom8_asana/models/business/offer.py:124,127` (Offer.account_activity property)
- `src/autom8_asana/models/business/unit.py:118,121` (Unit.account_activity property)
- Re-exported from `src/autom8_asana/models/business/__init__.py:117,235`

This makes the DRY consolidation safer: the canonical is already production-tested via entity model properties.

### Key Discovery: BaseExtractor._extract_section Is Dead Code

`BaseExtractor._extract_section()` at `extractors/base.py:488-521` is defined but **never called in production code**. No extractor subclass or any production module calls `self._extract_section()`. It is only exercised by 4 tests in `tests/unit/dataframes/test_extractors.py`. This simplifies the DRY-001 approach: we replace the dead method body with a delegation to the canonical, and the tests continue to pass without changes.

---

## 2. Finding Contracts

### RF-S1-001: Freshness Delta Parallel Added GID Fetch (AT2-003)

**Finding**: AT2-003
**Risk Level**: LOW
**Estimated Lines Changed**: ~30
**File**: `src/autom8_asana/dataframes/builders/freshness.py`

#### Before State

File: `src/autom8_asana/dataframes/builders/freshness.py`, method `_apply_section_delta`, lines 338-355:

```python
# Fetch added tasks individually (may not appear in modified_since)
fetched_gids = {t.gid for t in delta_tasks}
for gid in added_gids:
    if gid not in fetched_gids:
        try:
            task = await self._client.tasks.get_async(
                gid, opt_fields=BASE_OPT_FIELDS
            )
            delta_tasks.append(task)
        except Exception as e:  # BROAD-CATCH: api-boundary -- individual task fetch via Asana API
            logger.warning(
                "freshness_delta_fetch_added_failed",
                extra={
                    "section_gid": section_gid,
                    "task_gid": gid,
                    "error": str(e),
                },
            )
```

**Problem**: Added GIDs are fetched one-by-one sequentially. For N added GIDs not already in `fetched_gids`, this makes N sequential API calls.

#### After State

Replace the sequential loop with parallel fetching using `asyncio.gather` with `return_exceptions=True`, bounded by `Semaphore(8)` per the resolution/enumeration concurrency limit. Per-GID error handling is preserved by inspecting results for exceptions.

```python
# Fetch added tasks in parallel (may not appear in modified_since)
fetched_gids = {t.gid for t in delta_tasks}
unfetched_added = [gid for gid in added_gids if gid not in fetched_gids]

if unfetched_added:
    sem = asyncio.Semaphore(8)

    async def _fetch_one(gid: str) -> tuple[str, Any]:
        """Fetch a single added GID with bounded concurrency."""
        async with sem:
            return gid, await self._client.tasks.get_async(
                gid, opt_fields=BASE_OPT_FIELDS
            )

    fetch_results = await asyncio.gather(
        *[_fetch_one(g) for g in unfetched_added],
        return_exceptions=True,
    )

    succeeded = 0
    failed = 0
    for i, result in enumerate(fetch_results):
        if isinstance(result, BaseException):
            failed += 1
            logger.warning(
                "freshness_delta_fetch_added_failed",
                extra={
                    "section_gid": section_gid,
                    "task_gid": unfetched_added[i],
                    "error": str(result),
                    "error_type": type(result).__name__,
                },
            )
        else:
            _gid, task = result
            delta_tasks.append(task)
            succeeded += 1

    if unfetched_added:
        logger.info(
            "freshness_delta_parallel_fetch_summary",
            extra={
                "section_gid": section_gid,
                "total_added": len(unfetched_added),
                "succeeded": succeeded,
                "failed": failed,
            },
        )
```

**Fallback**: The `return_exceptions=True` pattern ensures that individual GID fetch failures do not abort the entire batch. Failed GIDs are logged exactly as before (same log event name: `freshness_delta_fetch_added_failed`). The delta merge proceeds with whatever tasks were successfully fetched -- identical to the original sequential behavior where a failed GID was simply skipped.

**Import required**: Add `import asyncio` at the top of `freshness.py`. Check if it already exists -- the file already imports from `autom8_asana.dataframes.builders.base` which uses `asyncio`, but `freshness.py` itself does not directly import `asyncio`. Add it.

#### Invariants

1. **Same delta merge result**: Successfully fetched tasks are appended to `delta_tasks` exactly as before; failed tasks are skipped with a warning log
2. **Same error semantics**: Per-GID exceptions produce `freshness_delta_fetch_added_failed` warnings with `section_gid`, `task_gid`, `error` fields (identical to before); additionally `error_type` is added for observability
3. **Same downstream behavior**: The rest of `_apply_section_delta` is unchanged -- it processes `delta_tasks` regardless of how many added GIDs failed
4. **Concurrency bounded**: Semaphore(8) per the resolution/enumeration limit from PROMPT-0 constraints
5. **No public API change**: `_apply_section_delta` is a private method; `apply_deltas_async` signature unchanged
6. **BROAD-CATCH preserved**: The original `except Exception` catch is structurally preserved via `return_exceptions=True` + `isinstance(result, BaseException)` check

#### Verification Criteria

1. `grep -n 'import asyncio' src/autom8_asana/dataframes/builders/freshness.py` -- must show the import
2. `grep -n 'Semaphore' src/autom8_asana/dataframes/builders/freshness.py` -- must show `Semaphore(8)`
3. `grep -n 'freshness_delta_parallel_fetch_summary' src/autom8_asana/dataframes/builders/freshness.py` -- must show the observability log
4. `grep -n 'for gid in added_gids' src/autom8_asana/dataframes/builders/freshness.py` -- must return ZERO results (sequential loop eliminated)
5. `.venv/bin/pytest tests/unit/dataframes/test_freshness.py -x -q --timeout=60` -- all pass
6. `.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60` -- >= 8781 passed

#### Rollback Strategy

Revert single commit. `_apply_section_delta` is a private method with no external callers beyond `apply_deltas_async`.

---

### RF-S1-002: DRY Section Extraction Consolidation (DRY-001)

**Finding**: DRY-001
**Risk Level**: LOW
**Estimated Lines Changed**: ~35 (net reduction of ~30 lines across 2 files)
**Files Modified**: `src/autom8_asana/dataframes/extractors/base.py`, `src/autom8_asana/dataframes/views/dataframe_view.py`, `src/autom8_asana/models/business/activity.py`

#### Scope Decisions

| Location | Action | Rationale |
|----------|--------|-----------|
| `activity.py:138-171` (canonical) | **MODIFY** -- add dict-path support | Canonical already takes `Any`; add membership-dict guard + make `.memberships` access duck-type safe via `getattr` |
| `base.py:488-521` (BaseExtractor) | **REPLACE body** with delegation to canonical | Dead code in production; tests exercise it directly but will pass with delegation |
| `dataframe_view.py:835-870` (DataFrameViewPlugin) | **REPLACE body** with delegation to canonical | Only production caller; operates on dict input; canonical will handle dicts after modification |
| `process.py:414-430` (Process.pipeline_state) | **LEAVE AS-IS** | Returns `ProcessSection` enum, not `str`; has no `project_gid` filter; simpler logic. Wiring through the canonical would add complexity for zero maintenance benefit. A 4-line property that returns an enum from a different domain should stay self-contained. |

#### Before State

**Canonical (`activity.py:138-171`)** -- takes `Any`, accesses `task.memberships` directly:
```python
def extract_section_name(
    task: Any,
    project_gid: str | None = None,
) -> str | None:
    if not task.memberships:
        return None

    for membership in task.memberships:
        if project_gid:
            project = membership.get("project", {})
            if isinstance(project, dict) and project.get("gid") != project_gid:
                continue

        section = membership.get("section")
        if section and isinstance(section, dict):
            name = section.get("name")
            if name is not None and isinstance(name, str):
                return str(name)

    return None
```

**Duplicate 1 (`base.py:488-521`)** -- identical logic, instance method, takes `Task`:
```python
def _extract_section(self, task: Task, project_gid: str | None = None) -> str | None:
    # ... identical logic ...
```

**Duplicate 2 (`dataframe_view.py:835-870`)** -- dict input, adds `isinstance(membership, dict)` guard, **missing** `isinstance(section_name, str)` check:
```python
def _extract_section(self, task_data: dict[str, Any], project_gid: str | None = None) -> str | None:
    memberships = task_data.get("memberships")
    if not memberships:
        return None
    for membership in memberships:
        if not isinstance(membership, dict):
            continue
        # ... same core logic, but missing isinstance(str) check ...
```

#### After State

**Step 1: Modify canonical (`activity.py:138-171`)** to handle both Task model and dict input via duck-typing:

```python
def extract_section_name(
    task: Any,
    project_gid: str | None = None,
) -> str | None:
    """Extract section name from task memberships.

    Canonical implementation of section name extraction. Handles both
    Task model objects (with .memberships attribute) and raw dicts
    (with "memberships" key).

    Args:
        task: Task instance or dict with memberships data.
        project_gid: Optional project GID to disambiguate multi-project tasks.
                     If provided, only memberships for that project are checked.

    Returns:
        Section name string or None if no section found.
    """
    # Duck-type: support both Task model (.memberships) and dict (.get("memberships"))
    memberships = (
        task.get("memberships") if isinstance(task, dict) else getattr(task, "memberships", None)
    )
    if not memberships:
        return None

    for membership in memberships:
        if not isinstance(membership, dict):
            continue

        if project_gid:
            project = membership.get("project", {})
            if isinstance(project, dict) and project.get("gid") != project_gid:
                continue

        section = membership.get("section")
        if section and isinstance(section, dict):
            name = section.get("name")
            if name is not None and isinstance(name, str):
                return str(name)

    return None
```

**Changes from current canonical**:
1. Memberships access is now duck-typed: `task.get("memberships")` for dicts, `getattr(task, "memberships", None)` for models. This replaces the bare `task.memberships` which would `AttributeError` on a dict.
2. Added `isinstance(membership, dict)` guard from `dataframe_view.py` Location 3 -- defensive, handles edge cases where memberships contain non-dict items.
3. The `isinstance(name, str)` check is **retained** (Location 3 was missing it -- this is a bug fix for the dict path).

**Step 2: Replace `BaseExtractor._extract_section` body (`base.py:488-521`)**:

```python
def _extract_section(
    self,
    task: Task,
    project_gid: str | None = None,
) -> str | None:
    """Extract section name from task memberships (FR-MODEL-009).

    Per PRD-0003: Section extracted from task's memberships for target project.
    Delegates to canonical extract_section_name() per DRY-001.

    Args:
        task: Task to extract from
        project_gid: Project GID to filter memberships by

    Returns:
        Section name or None
    """
    from autom8_asana.models.business.activity import extract_section_name

    return extract_section_name(task, project_gid)
```

**Note**: Use a local import to avoid circular dependency. The `dataframes.extractors` package does not currently import from `models.business.activity`. A module-level import would create: `dataframes.extractors.base` -> `models.business.activity` -> (no dependency back). Verify there is no circular path. If there is, the local import handles it safely.

**Step 3: Replace `DataFrameViewPlugin._extract_section` body (`dataframe_view.py:835-870`)**:

```python
def _extract_section(
    self,
    task_data: dict[str, Any],
    project_gid: str | None = None,
) -> str | None:
    """Extract section name from task memberships.

    Delegates to canonical extract_section_name() per DRY-001.

    Args:
        task_data: Task data dict.
        project_gid: Optional project GID filter.

    Returns:
        Section name or None.
    """
    from autom8_asana.models.business.activity import extract_section_name

    return extract_section_name(task_data, project_gid)
```

#### Invariants

1. **Same return values**: For Task model input, behavior is identical (canonical already handles `.memberships` attribute). For dict input, behavior is identical except the missing `isinstance(section_name, str)` check is now present -- this is a bug fix (a non-string `section_name` would previously pass through, now it is correctly rejected)
2. **Same method signatures**: `BaseExtractor._extract_section(self, task, project_gid)` and `DataFrameViewPlugin._extract_section(self, task_data, project_gid)` signatures are unchanged
3. **Same return types**: `str | None` in all cases
4. **Process.pipeline_state unchanged**: Not modified; returns `ProcessSection` enum
5. **No new modules**: Canonical stays in `activity.py`; no new files created
6. **Existing callers unaffected**: `Offer.account_activity`, `Unit.account_activity` call `extract_section_name()` with Task model objects -- the added dict-path support does not change model-path behavior

#### Verification Criteria

1. `grep -rn 'from autom8_asana.models.business.activity import extract_section_name' src/autom8_asana/dataframes/` -- must show 2 results (base.py and dataframe_view.py)
2. `grep -c 'membership.get' src/autom8_asana/dataframes/extractors/base.py` -- must be 0 or 1 (only the import delegation, no inline membership iteration)
3. `grep -c 'membership.get' src/autom8_asana/dataframes/views/dataframe_view.py` -- must NOT contain inline section extraction logic (only in other methods like `_extract_tags`)
4. `.venv/bin/pytest tests/unit/dataframes/test_extractors.py -x -q --timeout=60` -- all pass (existing `test_extract_section*` tests)
5. `.venv/bin/pytest tests/unit/dataframes/views/test_dataframe_view.py -x -q --timeout=60` -- all pass
6. `.venv/bin/pytest tests/unit/models/business/test_activity.py -x -q --timeout=60` -- all pass
7. `.venv/bin/pytest tests/unit/models/business/test_process.py -x -q --timeout=60` -- all pass (pipeline_state unchanged)
8. `.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60` -- >= 8781 passed

#### Rollback Strategy

Revert single commit. All three methods retain their original signatures; only the internal bodies change. Callers are unaffected.

---

### RF-S1-003: Lifecycle Init Sequential Dep Check (AT2-005) -- NOT RECOMMENDED

**Finding**: AT2-005
**Risk Level**: N/A (not implementing)
**Decision**: Do not parallelize

#### Analysis

The sequential dependency check in `PlayCreationHandler.execute_async` at `init_actions.py:199-204`:

```python
for dep in dependencies:
    dep_gid = dep.gid if hasattr(dep, "gid") else dep.get("gid")
    if dep_gid:
        dep_task = await self._client.tasks.get_async(
            dep_gid, opt_fields=["memberships"]
        )
        memberships = getattr(dep_task, "memberships", []) or []
        for membership in memberships:
            proj = membership.get("project", {})
            if proj.get("gid") == action_config.project_gid:
                return CreationResult(success=True, entity_gid=dep_gid)
```

#### Why Parallelization Is Not Recommended

**1. Early return eliminates most work.** The loop checks each dependency's project memberships sequentially. On the **first match**, it returns immediately. In the common case where the play is already linked (the most frequent path per the `not_already_linked` condition), only 1 API call is made. Parallelizing with `asyncio.gather` would fetch ALL dependencies upfront, then check results -- this means MORE API calls in the common case (N calls instead of 1), not fewer.

**2. Typical dependency count is 0-2.** Tasks in this lifecycle path rarely have more than 1-2 dependencies. The maximum theoretical gain from parallelizing 2 calls is ~300ms (one sequential hop). This is negligible for a path that executes 5-15 times per day.

**3. Execution frequency is very low.** At 5-15 lifecycle init actions per day, even a 300ms saving yields 1.5-4.5 seconds saved per day. The implementation complexity (gather + result scanning + maintaining early-return semantics) is not justified.

**4. Parallelization changes semantic ordering.** The current sequential approach returns the **first** matching dependency. Parallelizing returns **any** matching dependency (whichever resolves first). While functionally equivalent for correctness, this changes determinism of `entity_gid` in the return value, which could affect logging consistency and debugging.

**5. Budget is not a concern.** Unlike resolution strategies (AT2-001) where budget exhaustion is tracked, this handler has no budget mechanism. The N+1 pattern here is bounded by dependency count (1-3), not by a traversal depth.

#### Quantitative Assessment

| Metric | Sequential (current) | Parallel (proposed) |
|--------|---------------------|---------------------|
| API calls when already linked (common) | 1-2 (early return) | N (all deps fetched) |
| API calls when not linked | N | N |
| Executions per day | 5-15 | 5-15 |
| Max time saved per execution | ~300ms (for N=2) | 0 (worse when linked) |
| Implementation complexity | None | ~20 lines + semantic change |

**Verdict**: Parallelization would make the common case (already linked) **slower** by fetching all dependencies instead of stopping at the first match. The fix direction in PROMPT-0 acknowledged this: "OR keep sequential if early-return value is high." The early-return value IS high.

---

## 3. ADR: AT2-005 Not Recommended

### ADR-S1-001: Do Not Parallelize PlayCreationHandler Dependency Check

**Status**: Accepted

**Context**: AT2-005 identified sequential `get_async` calls in `PlayCreationHandler.execute_async` for checking dependency project membership. The fix direction suggested `asyncio.gather` but noted early-return semantics must be preserved.

**Decision**: Leave the sequential loop as-is.

**Alternatives Considered**:

- **Option A: asyncio.gather all deps, then scan results** -- Fetches all N dependencies in parallel. Eliminates sequential latency. But: in the common "already linked" case, makes N API calls instead of 1. Changes which dependency GID is returned (non-deterministic ordering).

- **Option B: asyncio.gather with cancellation** -- Launch all fetches, cancel remaining on first match via `asyncio.wait(FIRST_COMPLETED)`. Preserves early-exit benefit. But: adds significant complexity (task cancellation, cleanup, partial result handling) for a 5-15/day code path with 1-2 dependencies.

- **Option C: Keep sequential (chosen)** -- Zero changes. Sequential loop with early return. 1 API call in the common case.

**Rationale**: The early-return path dominates (play is already linked in the common case). Parallelization makes the common case slower. The code path executes 5-15 times per day with 1-2 dependencies. Implementation complexity for Options A/B is not justified by the marginal gain on the uncommon path.

**Consequences**: AT2-005 is closed as "not-recommended." The finding score of 42 was accurate -- below the action threshold for this code path's frequency and early-return characteristics.

---

## 4. Sequencing

### Phase 1: DRY Consolidation (RF-S1-002)

| Order | Task | Risk | Dependency | Rollback Point |
|:-----:|------|------|------------|----------------|
| 1 | RF-S1-002: DRY section extraction | LOW | None | Commit boundary |

**Rationale**: The DRY consolidation is a structural improvement that touches more files but has no behavioral change for existing callers. Doing it first establishes a clean canonical that other future changes can build on. The canonical is already production-tested via `offer.py` and `unit.py` -- extending it to handle dicts is a safe, testable change.

**Rollback checkpoint**: Run `tests/unit/dataframes/test_extractors.py`, `tests/unit/dataframes/views/test_dataframe_view.py`, `tests/unit/models/business/test_activity.py`, and `tests/unit/models/business/test_process.py`. If any fail, revert before proceeding.

### Phase 2: Freshness Parallel Fetch (RF-S1-001)

| Order | Task | Risk | Dependency | Rollback Point |
|:-----:|------|------|------------|----------------|
| 2 | RF-S1-001: Parallel added GID fetch | LOW | None | Commit boundary |

**Rationale**: Independent of Phase 1 (different files entirely). Scheduled second because it changes runtime behavior (sequential to parallel) and benefits from the principal-engineer being warmed up after the structural DRY change.

**Rollback checkpoint**: Run `tests/unit/dataframes/test_freshness.py`. Then full suite.

### Dependency Graph

```
RF-S1-002 (DRY section extraction)
  |
  v
RF-S1-001 (freshness parallel fetch)    [independent, risk-ordered]
```

Both tasks are technically independent (no code dependencies). The sequencing is risk-preference: structural refactor first, behavioral change second.

---

## 5. Risk Assessment

| Task | Blast Radius | Failure Detection | Recovery Path | Recovery Cost |
|------|-------------|-------------------|---------------|:-------------:|
| RF-S1-001 | `freshness.py` `_apply_section_delta` only; delta merge path | Freshness unit tests; observability log verification | Revert 1 commit | Trivial |
| RF-S1-002 | `activity.py` canonical + 2 delegation sites (`base.py`, `dataframe_view.py`) | Extractor tests, view tests, activity tests, process tests | Revert 1 commit | Trivial |

### RF-S1-001 Specific Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Semaphore(8) too aggressive for environments with limited connection pool | Low | Low | Semaphore value matches existing convention (resolution calls use Semaphore(8)); `gather_with_limit` in the same file uses configurable `max_concurrent` |
| `return_exceptions=True` masks errors that the sequential try/except would surface | Low | Low | Each exception is individually logged with the same event name; the summary log adds visibility into batch success/failure rates |
| Parallel fetch order differs from sequential (tasks appended in completion order) | Low | None | Delta tasks are upserted by GID (`filter(~col("gid").is_in(...))` + `concat`); order does not affect merge correctness |

### RF-S1-002 Specific Risks

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Circular import between `dataframes/extractors/base.py` and `models/business/activity.py` | Low | Medium | Local import within method body avoids module-level circular dependency; verify with import trace |
| Behavioral change from added `isinstance(membership, dict)` guard in canonical | Very Low | Low | This guard was already present in Location 3 (`dataframe_view.py`); adding it to the canonical is defensive and handles edge cases; existing tests confirm memberships are always dicts |
| Behavioral change from added `isinstance(section_name, str)` check for dict path | Very Low | Positive | This was a **missing check** in Location 3 (dataframe_view.py); adding it fixes a subtle bug where non-string section names could pass through |

**Aggregate risk**: LOW. Both tasks modify private methods/internal function bodies. No public API changes. Each is independently revertible.

---

## 6. Principal-Engineer Notes

### Commit Conventions

Each task gets ONE atomic commit:

```
refactor(dataframes): DRY section extraction via canonical extract_section_name

DRY-001: Adapts the canonical extract_section_name() in activity.py to handle
both Task model and dict inputs via duck-typing. Replaces duplicate inline
implementations in BaseExtractor._extract_section (dead code) and
DataFrameViewPlugin._extract_section (production caller) with delegations.
Adds isinstance(membership, dict) guard and fixes missing isinstance(str)
check for dict-path callers. Process.pipeline_state left as-is (returns
enum, different domain).

Refs: INIT-RUNTIME-REM-001, DRY-001

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

```
perf(dataframes): parallelize freshness delta added GID fetches

AT2-003: Sequential get_async calls for newly-added GIDs in the delta merge
path are now batched via asyncio.gather with return_exceptions=True, bounded
by Semaphore(8). Per-GID error handling preserved (failed GIDs logged and
skipped). Adds freshness_delta_parallel_fetch_summary observability log with
total_added/succeeded/failed counts.

Refs: INIT-RUNTIME-REM-001, AT2-003

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

### Test Commands

```bash
# After RF-S1-002 (DRY):
.venv/bin/pytest tests/unit/dataframes/test_extractors.py tests/unit/dataframes/views/test_dataframe_view.py tests/unit/models/business/test_activity.py tests/unit/models/business/test_process.py -x -q --timeout=60

# After RF-S1-001 (freshness):
.venv/bin/pytest tests/unit/dataframes/test_freshness.py -x -q --timeout=60

# After ALL tasks (full regression):
.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60
# Expected: >= 8781 passed

# Pre-existing failures to IGNORE:
# - test_adversarial_pacing.py (checkpoint assertions)
# - test_paced_fetch.py (checkpoint assertions)
# - test_parallel_fetch.py::test_cache_errors_logged_as_warnings (caplog vs structured logging)
```

### Critical Constraints

1. **RF-S1-002: Do NOT modify `Process.pipeline_state`** -- it returns `ProcessSection` (different type), has no `project_gid` filter, and is a 4-line property in a different semantic domain. Leave it.

2. **RF-S1-002: Use local imports** for `extract_section_name` in both `base.py` and `dataframe_view.py` to avoid potential circular imports. Module-level imports are NOT safe until circular dependency analysis is complete.

3. **RF-S1-002: The canonical modification must be backward-compatible** -- `offer.py` and `unit.py` already call `extract_section_name(self, self.PRIMARY_PROJECT_GID)` where `self` is a Task model with `.memberships` attribute. The duck-typing change must not break this path. Verify: `getattr(task_model, "memberships", None)` returns the same value as `task_model.memberships`.

4. **RF-S1-001: Semaphore must be 8** -- per PROMPT-0 constraint: "Semaphore(8) for resolution/enumeration calls."

5. **RF-S1-001: Do NOT change the BROAD-CATCH behavior** -- the original `except Exception` per-GID catch is structurally preserved via `return_exceptions=True` + `isinstance(result, BaseException)`. Do not narrow the exception types.

6. **RF-S1-001: `import asyncio` is required** -- `freshness.py` does not currently import `asyncio` directly. Add it at the top with the other stdlib imports.

7. **Both tasks: No new modules** -- per PROMPT-0 constraint 5.

8. **Both tasks: Test baseline >= 8781 passed** -- per PROMPT-0 constraint 6.

### Implementation Rules Reminder (from PROMPT-0)

1. Every optimization MUST have a fallback -- RF-S1-001: failed GIDs are skipped (same as before). RF-S1-002: not a runtime optimization, but delegation preserves identical behavior.
2. Every optimization MUST log savings -- RF-S1-001: `freshness_delta_parallel_fetch_summary` with `total_added`, `succeeded`, `failed`.
3. Every optimization MUST preserve test compatibility -- no public API changes in either task.
4. Concurrency limits: Semaphore(8) for enumeration -- applied in RF-S1-001.
5. No new modules -- both tasks modify existing files only.

---

## 7. Attestation

| Source Artifact | Verified Via | Line References Confirmed |
|-----------------|-------------|--------------------------|
| `src/autom8_asana/dataframes/builders/freshness.py` | Read tool | Lines 338-355: sequential `get_async` for added GIDs in `_apply_section_delta` confirmed |
| `src/autom8_asana/dataframes/builders/base.py` | Read tool | Lines 48-70: `gather_with_limit` with semaphore pattern confirmed as existing infrastructure |
| `src/autom8_asana/lifecycle/init_actions.py` | Read tool | Lines 199-214: sequential dep check in `PlayCreationHandler` with early return confirmed |
| `src/autom8_asana/models/business/activity.py` | Read tool | Lines 138-171: canonical `extract_section_name()` confirmed; `task.memberships` direct access |
| `src/autom8_asana/dataframes/extractors/base.py` | Read tool | Lines 488-521: duplicate `_extract_section` confirmed; zero production callers (dead code) |
| `src/autom8_asana/dataframes/views/dataframe_view.py` | Read tool | Lines 835-870: duplicate `_extract_section` confirmed; dict input; missing `isinstance(str)` check |
| `src/autom8_asana/models/business/process.py` | Read tool | Lines 414-430: `pipeline_state` confirmed; returns `ProcessSection` enum, no `project_gid` filter |
| `src/autom8_asana/models/business/offer.py` | Grep tool | Lines 124,127: `extract_section_name` is imported and called (NOT orphaned) |
| `src/autom8_asana/models/business/unit.py` | Grep tool | Lines 118,121: `extract_section_name` is imported and called (NOT orphaned) |
| `src/autom8_asana/models/business/__init__.py` | Grep tool | Lines 117,235: `extract_section_name` re-exported (NOT orphaned) |
| `tests/unit/dataframes/test_extractors.py` | Grep tool | 4 tests exercise `_extract_section` |
| `tests/unit/lifecycle/test_init_actions.py` | Grep tool | `TestPlayCreationHandler` tests sequential dep check with mocks |
| SMELL report | Read tool | All 3 findings reviewed in full context |
| Prior TDD (`docs/hygiene/TDD-runtime-efficiency-audit.md`) | Read tool | Format and conventions used as template |
| PROMPT-0 (`PROMPT-0-runtime-remediation.md`) | Read tool | Constraints, anti-patterns, and key file index verified |
| Spike doc (`docs/spikes/SPIKE-workflow-activity-gap-analysis.md`) | Read tool | DRY-001 context reviewed; orphaned status is stale (corrected in this TDD) |

---

## Handoff Checklist

- [x] AT2-003: Before/after contract documented with implementation specification (RF-S1-001)
- [x] DRY-001: Before/after contract documented for canonical + 2 delegation sites (RF-S1-002)
- [x] AT2-005: Explicitly marked NOT RECOMMENDED with quantitative rationale (RF-S1-003)
- [x] ADR for AT2-005 non-recommendation documented (ADR-S1-001)
- [x] Invariants specified for each implementing task
- [x] Verification criteria with concrete commands for each task
- [x] Sequencing with explicit dependencies (none; risk-ordered)
- [x] Rollback points identified (commit boundary after each task)
- [x] Risk assessment complete (all LOW)
- [x] Principal-engineer can implement mechanically without judgment calls
- [x] All artifacts verified via Read/Grep tools with attestation table
