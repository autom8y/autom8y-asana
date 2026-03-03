# WS-SYSCTX: system_context.py Registration Pattern Refactor

**Objective**: Replace the god-context upward imports in `core/system_context.py` with
a registration pattern where singletons register their own reset functions, eliminating
Cycle 4 and the core -> {models, dataframes, services, metrics} layering violation.

**Rite**: hygiene
**Complexity**: MODULE
**Recommendations**: R-005
**Preconditions**: None (Phase 1 -- independent)
**Estimated Effort**: 1-2 days

---

## Problem

`core/system_context.py` (87 LOC) imports from 5 subsystems above it:
- `models.business.registry`
- `models.business._bootstrap`
- `dataframes.models.registry`
- `dataframes.watermark`
- `services.resolver`
- `metrics.registry`

This creates Cycle 4 and means all 12 units depending on `core/` transitively
depend on these subsystems. Adding a new singleton requires remembering to update
this file -- if forgotten, test isolation silently breaks.

**Evidence**: ARCHITECTURE-ASSESSMENT.md AP-1 (Risk 1); ARCHITECTURE-REPORT.md R-005

---

## Artifact References

- Anti-pattern detail: `ARCHITECTURE-ASSESSMENT.md` Section 2, AP-1
- Risk register: `ARCHITECTURE-ASSESSMENT.md` Section 8, Risk 1 and Risk 4
- Migration readiness: `ARCHITECTURE-REPORT.md` Section 6, R-005
- Cycle 4 detail: `DEPENDENCY-MAP.md` Section 6.1, Cycle 4

---

## Implementation Sketch

### Step 1: Add Registration API (keep existing code working)

In `src/autom8_asana/core/system_context.py`:
- Add `_reset_registry: list[Callable[[], None]] = []`
- Add `register_reset(fn: Callable[[], None]) -> None`
- Keep existing `reset_all()` body intact during transition

### Step 2: Migrate One Singleton (verify pattern works)

Start with `dataframes.models.registry.SchemaRegistry`:
- In `dataframes/models/registry.py`, add at module level:
  `from autom8_asana.core.system_context import register_reset`
  `register_reset(SchemaRegistry.reset)`
- Verify `pytest tests/ -k "reset" --tb=short` passes
- Verify `pytest tests/unit/dataframes/ -x` passes

### Step 3: Migrate Remaining Singletons (one at a time)

For each singleton, add registration call in the singleton's module:
1. SchemaRegistry (`dataframes/models/registry.py`) -- done in Step 2
2. ProjectTypeRegistry (`models/business/registry.py`)
3. WorkspaceProjectRegistry (`models/business/registry.py`)
4. EntityProjectRegistry (`services/resolver.py`)
5. WatermarkRepository (`dataframes/watermark.py`)
6. MetricRegistry (`metrics/registry.py`)
7. DataFrameCache singleton (`cache/dataframe/factory.py`)
8. Bootstrap state (`models/business/_bootstrap.py`)

Run `pytest tests/ -x` after each migration.

### Step 4: Remove Upward Imports

Once all 8 singletons are registered:
1. Replace explicit per-singleton calls in `reset_all()` with:
   `for fn in _reset_registry: fn()`
2. Remove all imports from `models`, `dataframes`, `services`, `metrics`
3. Cycle 4 is eliminated

### Step 5: Verify

- `pytest tests/ -x` (full suite)
- Run 3x to confirm no flaky tests introduced
- Verify no imports of upper layers remain: `grep -r "from autom8_asana.models" src/autom8_asana/core/system_context.py`

---

## Resolves Unknown

**U-006** (system_context.py design intent): This refactor treats it as an organic
accumulation of test infrastructure that should use a registration pattern. The
module docstring references "QW-5 (ARCH-REVIEW-1 Section 3.1)" as origin,
confirming it was a pragmatic response, not a designed architectural element.

---

## Do NOT

- Move `system_context.py` out of `core/` (keep it where consumers expect it)
- Change the `reset_all()` public API signature
- Remove singletons themselves (just change how they register for reset)
- Batch-migrate all singletons at once (one-at-a-time with tests after each)

---

## Green-to-Green Gates

- Full test suite passes after each singleton migration
- `pytest -k "reset" --tb=short` shows no failures
- No new flaky tests (run suite 3x)
- Zero imports from `models`, `dataframes`, `services`, `metrics` in system_context.py
- `core/` fan-out to upper layers reduced (verify via grep)

---

## Definition of Done

- [ ] Registration API added to system_context.py
- [ ] All 8 singletons migrated to self-registration
- [ ] Upward imports removed from system_context.py
- [ ] Cycle 4 eliminated (verify: no core -> upper-layer imports)
- [ ] Full test suite green (10,552+ tests)
- [ ] Run 3x stability check passed
- [ ] MEMORY.md updated: "WS-SYSCTX: system_context registration pattern DONE"
