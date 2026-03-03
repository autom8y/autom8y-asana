# Re-Export Elimination Spike: PROMPT-0

**Scope**: Remove backward-compatibility re-exports from two files
**Rite**: hygiene (code-smeller -> architect-enforcer -> janitor -> audit-lead)
**Complexity**: PATCH
**Estimated Effort**: 1-2 hours
**Date**: 2026-02-24

---

## Background

REM-ASANA-ARCH Phase 2 (Session P2-01, commit d87b9a9) extracted two utilities
to `core/` and updated lower-layer callers to import from canonical locations.
Re-exports were intentionally preserved in the origin files as a conservative
measure. All lower-layer callers were migrated at that time.

The re-exports remain:
1. `services/resolver.py:48` re-exports `to_pascal_case` from `core/string_utils`
2. `persistence/holder_construction.py:40` re-exports `HOLDER_REGISTRY` and `register_holder` from `core/registry`

**This spike eliminates both re-exports by migrating remaining callers to canonical paths.**

---

## Pre-Computed Caller Map

**Do NOT re-discover this. The analysis is complete.**

### Re-Export 1: `to_pascal_case` in `services/resolver.py:48`

**Re-export line**: `from autom8_asana.core.string_utils import to_pascal_case as to_pascal_case  # noqa: E501`

**Callers still using the re-export path** (`from autom8_asana.services.resolver import to_pascal_case`):

| File | Line | Import Style | Layer |
|------|------|-------------|-------|
| `services/query_service.py` | 73 | deferred | services (same layer) |
| `services/universal_strategy.py` | 22 | runtime | services (same layer) |
| `api/preload/legacy.py` | 456 | deferred | api (above services) |
| `api/preload/legacy.py` | 560 | deferred | api (above services) |
| `api/routes/admin.py` | 226 | deferred | api (above services) |
| `api/preload/progressive.py` | 95 | deferred | api (above services) |

**Callers already on canonical path** (`from autom8_asana.core.string_utils import to_pascal_case`):
- `cache/dataframe/factory.py:55` (migrated in P2-01)
- `cache/integration/schema_providers.py:27` (migrated in P2-01)
- `dataframes/models/registry.py:314` (migrated in P2-01)

**Test files**: Zero test files import `to_pascal_case` from either path.

**`__all__` impact**: `resolver.py:39` lists `"to_pascal_case"` in `__all__`. Must be removed.

### Re-Export 2: `HOLDER_REGISTRY` + `register_holder` in `persistence/holder_construction.py:40`

**Re-export line**: `from autom8_asana.core.registry import HOLDER_REGISTRY, register_holder  # noqa: F401`

**Source callers using re-export path** (`from autom8_asana.persistence.holder_construction import ...`):

| File | What | Line | Notes |
|------|------|------|-------|
| `persistence/holder_ensurer.py` | `construct_holder`, `detect_existing_holders` | 27-30 | NOT re-exports, legitimate same-module imports |
| `persistence/holder_ensurer.py` | `get_holder_class_map` | 434 | NOT a re-export, lives in holder_construction |

**Source callers already on canonical path** (`from autom8_asana.core.registry import ...`):
- All 6 `models/business/*.py` files (migrated in P2-01)

**Test callers using re-export path**:

| File | What | Line |
|------|------|------|
| `tests/unit/persistence/test_holder_construction.py` | `HOLDER_REGISTRY` | 16 |

**Key insight**: `holder_ensurer.py` imports `construct_holder` and `detect_existing_holders` -- these are NOT re-exports, they live in `holder_construction.py`. Only `HOLDER_REGISTRY` is a re-export. One test file imports `HOLDER_REGISTRY` via the re-export path.

---

## Canonical Locations (Already on Main)

| Symbol | Canonical Path | Created By |
|--------|---------------|------------|
| `to_pascal_case` | `autom8_asana.core.string_utils` | P2-01 (d87b9a9) |
| `HOLDER_REGISTRY` | `autom8_asana.core.registry` | P2-01 (d87b9a9) |
| `register_holder` | `autom8_asana.core.registry` | P2-01 (d87b9a9) |

---

## Scope Boundaries

### In Scope
- Migrate 6 remaining `to_pascal_case` callers to `core.string_utils`
- Migrate 1 test file `HOLDER_REGISTRY` import to `core.registry`
- Remove re-export line from `services/resolver.py:48`
- Remove `"to_pascal_case"` from `services/resolver.py:39` (`__all__`)
- Remove re-export line from `persistence/holder_construction.py:40`

### Out of Scope
- Do NOT touch callers importing other symbols from `resolver.py` (EntityProjectRegistry, get_strategy, etc.) -- those are NOT re-exports
- Do NOT move `construct_holder`, `detect_existing_holders`, `get_holder_class_map` -- they live in `holder_construction.py`
- Do NOT modify `core/string_utils.py` or `core/registry.py`
- Do NOT change any business logic

---

## File-Scope Contract

```
MODIFY (re-export removal):
  src/autom8_asana/services/resolver.py          (remove line 48, update __all__ line 39)
  src/autom8_asana/persistence/holder_construction.py  (remove line 40)

MODIFY (import path update):
  src/autom8_asana/services/query_service.py     (line 73: resolver -> core.string_utils)
  src/autom8_asana/services/universal_strategy.py (line 22: resolver -> core.string_utils)
  src/autom8_asana/api/preload/legacy.py         (lines 456, 560: resolver -> core.string_utils)
  src/autom8_asana/api/routes/admin.py           (line 226: resolver -> core.string_utils)
  src/autom8_asana/api/preload/progressive.py    (line 95: resolver -> core.string_utils)
  tests/unit/persistence/test_holder_construction.py (line 16: holder_construction -> core.registry)

DO NOT TOUCH:
  src/autom8_asana/core/string_utils.py
  src/autom8_asana/core/registry.py
  src/autom8_asana/core/entity_registry.py
  src/autom8_asana/persistence/holder_ensurer.py
  src/autom8_asana/models/business/*.py
  Any file not listed above
```

---

## Execution Strategy (for Janitor)

### Commit 1: Migrate `to_pascal_case` callers and remove re-export
1. Update imports in 6 files (query_service, universal_strategy, legacy x2, admin, progressive)
2. Remove re-export line from `resolver.py:48`
3. Remove `"to_pascal_case"` from `resolver.py __all__`
4. Gate: `grep "from autom8_asana.services.resolver import.*to_pascal_case" src/` -> 0 matches
5. Test: `pytest tests/unit/services/ tests/unit/api/ -x`

### Commit 2: Migrate `HOLDER_REGISTRY` caller and remove re-export
1. Update import in `test_holder_construction.py:16` (HOLDER_REGISTRY from core.registry)
2. Remove re-export line from `holder_construction.py:40`
3. Gate: `grep "from autom8_asana.persistence.holder_construction import.*HOLDER_REGISTRY" .` -> 0 matches
4. Gate: `grep "from autom8_asana.persistence.holder_construction import.*register_holder" .` -> 0 matches
5. Test: `pytest tests/unit/persistence/ -x`

### Final Gate
- Full suite: `AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x`
- Test baseline: 11,121+ passed

---

## Guardrails

1. Run tests after every commit. Green-to-green mandatory.
2. Verify file paths before editing (lesson from WS6 reference drift).
3. Do NOT remove symbols that are defined (not re-exported) in the origin files.
4. Do NOT modify `holder_ensurer.py` -- its imports of `construct_holder` and `detect_existing_holders` are legitimate same-module imports.
5. Do NOT modify any `models/business/*.py` -- already migrated.
6. The `to_pascal_case` callers in `api/` layer are deferred imports -- keep them deferred (just change the source path). Do not convert deferred to runtime.

---

## Existing Artifacts (Read Only If Needed)

These are for reference if agents need deeper context. Do NOT load them upfront.

| Artifact | What It Contains | Load When |
|----------|-----------------|-----------|
| `.claude/wip/REM-ASANA-ARCH/WS-P2-01.md` | Original extraction plan | Only if questioning why re-exports exist |
| `.claude/wip/REM-ASANA-ARCH/PHASE2-GAP-ANALYSIS.md` | Full gap analysis with cycle details | Only if questioning layer boundaries |
| `src/autom8_asana/core/string_utils.py` | Canonical `to_pascal_case` (33 lines) | Only if verifying function signature |
| `src/autom8_asana/core/registry.py` | Canonical `HOLDER_REGISTRY` + `register_holder` | Only if verifying function signature |

---

## Definition of Done

- [ ] Zero imports of `to_pascal_case` from `services.resolver` anywhere in codebase
- [ ] Zero imports of `HOLDER_REGISTRY` or `register_holder` from `persistence.holder_construction`
- [ ] Re-export lines removed from both origin files
- [ ] `to_pascal_case` removed from `resolver.py __all__`
- [ ] All callers updated to canonical import paths
- [ ] Full test suite green (11,121+ tests)
