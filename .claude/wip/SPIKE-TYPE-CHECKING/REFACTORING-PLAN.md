---
type: refactoring-plan
---

# TYPE_CHECKING Refactoring Plan

**Spike**: SPIKE-TYPE-CHECKING Phase 2 (Architect Enforcer)
**Date**: 2026-02-24
**Input**: SMELL-REPORT.md (234 files, 553 imports classified)
**Output**: Removal contracts, verdicts, cycle adjudication, final verdict

---

## Executive Summary

Of 234 files with `if TYPE_CHECKING:` blocks, 86 files (165+ imports) were flagged
as candidates for architect-enforcer review (Categories C and D). After verifying
runtime import paths, reverse dependencies, and transitive chains through
`autom8_asana/__init__.py`:

| Verdict | Files | Imports | Notes |
|---------|------:|--------:|-------|
| REMOVE (safe) | 37 | ~70 | No cycle risk, purely defensive |
| KEEP (cycle risk) | 46 | ~95 | Transitive cycle via `__init__.py` or structural |
| RECLASSIFY C->A | 2 | 4 | automation <-> lifecycle cycle not fully cut |
| REMOVE C (confirmed) | 1 | 1 | api -> cache direction confirmed safe |

**Final Verdict**: PARTIAL -- proceed with Phase 3 for safe removals only.

---

## 1. Category C: Removal Contract Adjudication

### C-001: api/dependencies.py -> cache (DataFrameCache)

**Cut Cycle**: cache -> api (Cycle 5, Phase 1)

**Verification**:
- `api/dependencies.py` imports `DataFrameCache` under TYPE_CHECKING (line 503)
- `DataFrameCache` is used only in the type alias `DataFrameCacheDep` on line 514 (string annotation)
- Reverse check: `cache/integration/dataframe_cache.py` has NO runtime import from `api`
- `api` is not imported by `__init__.py`, `client.py`, or `config.py` at runtime

**Verdict**: REMOVE -- but PARTIAL. The `DataFrameCache` import can be moved to top-level.
However, the other 5 imports in the same TYPE_CHECKING block serve different purposes:
- `EntityWriteRegistry` (D-Cross: resolution -> api -- no cycle) -> REMOVE
- `DataFrameService` (D-Cross: services -> api -- no cycle) -> REMOVE
- `EntityService` (D-Cross: services -> api -- no cycle) -> REMOVE
- `SectionService` (D-Cross: services -> api -- no cycle) -> REMOVE
- `TaskService` (D-Cross: services -> api -- no cycle) -> REMOVE

All 6 imports in this file can be moved to top-level. The entire TYPE_CHECKING
block can be eliminated.

**Before State**:
```python
# Line 500-508 of api/dependencies.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
    from autom8_asana.resolution.write_registry import EntityWriteRegistry
    from autom8_asana.services.dataframe_service import DataFrameService
    from autom8_asana.services.entity_service import EntityService
    from autom8_asana.services.section_service import SectionService
    from autom8_asana.services.task_service import TaskService
```

**After State**:
```python
# Top-level imports (no TYPE_CHECKING block needed)
from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
from autom8_asana.resolution.write_registry import EntityWriteRegistry
from autom8_asana.services.dataframe_service import DataFrameService
from autom8_asana.services.entity_service import EntityService
from autom8_asana.services.section_service import SectionService
from autom8_asana.services.task_service import TaskService
```

**Invariants**:
- String annotations in Annotated aliases become resolvable at runtime
- No behavior change (these are only used in type annotations)
- All existing tests pass without modification

**Verification**:
1. `python -c "from autom8_asana.api.dependencies import DataFrameCacheDep"`
2. `pytest tests/unit/ -x -k "dependencies or api"` (scoped)
3. Full suite: `pytest tests/ -x`

**Rollback**: Revert single commit.

---

### C-002: automation/workflows/pipeline_transition.py -> lifecycle (RECLASSIFIED TO A)

**Cut Cycle**: automation <-> lifecycle (P2-02)

**Verification**:
- `pipeline_transition.py` guards `LifecycleConfig` and `LifecycleEngine` under TYPE_CHECKING (lines 50-51)
- `pipeline_transition.py` also has a DEFERRED runtime import of `LifecycleEngine` inside `execute_async` (line 194)
- Reverse check: `lifecycle/seeding.py` has a TOP-LEVEL runtime import `from autom8_asana.automation.seeding import FieldSeeder` (line 29)
- `lifecycle/init_actions.py` has a deferred import `from autom8_asana.automation.templates import TemplateDiscovery` (line 246)
- The automation <-> lifecycle cycle is NOT fully cut at runtime.

**Root Cause**: The REM-ASANA-ARCH P2-02 work broke some paths of this cycle but
`lifecycle/seeding.py` still has a top-level runtime import from automation. The
TYPE_CHECKING guard in pipeline_transition.py is actively preventing a circular
import because:
1. `from autom8_asana.lifecycle.config import LifecycleConfig` would trigger `lifecycle/__init__.py`
2. `lifecycle/__init__.py` imports `lifecycle/seeding.py` (line 53)
3. `lifecycle/seeding.py` imports `from autom8_asana.automation.seeding import FieldSeeder` (line 29)
4. Loading `automation.seeding` triggers `automation/__init__.py`
5. If `pipeline_transition.py` is already being loaded (part of automation), circular import.

**Verdict**: RECLASSIFY to Category A. The automation <-> lifecycle cycle is partially
cut but still exists via the `lifecycle/seeding.py -> automation/seeding.py` runtime path.
Add to structural cycle registry note: "Partially cut; residual via lifecycle/seeding.py."

---

### C-003: services/dataframe_service.py -> dataframes (3 imports)

**Cut Cycle**: dataframes <-> services (P2-02)

**Verification**:
- `dataframe_service.py` guards 3 imports under TYPE_CHECKING: `DataFrameCacheIntegration`, `DataFrameSchema`, `CustomFieldResolver` (lines 33-35)
- `dataframe_service.py` also has 3 TOP-LEVEL runtime imports from dataframes (lines 23, 27, 28)
- Reverse check: `dataframes/` has NO runtime imports from `services/`
- `services/` is not imported by `__init__.py` or `client.py` at runtime

**Verdict**: REMOVE -- these 3 imports can safely be top-level. The file already has
top-level imports from `dataframes` (lines 23-28), so adding 3 more from the same
package is consistent and introduces no new dependency.

However, the TYPE_CHECKING block also contains D-category imports:
- `from autom8_asana.client import AsanaClient` (D-Root) -> see D-Root verdict
- `from autom8_asana.models.project import Project` (D-Cross) -> see D-Cross verdict
- `from autom8_asana.models.section import Section` (D-Cross) -> see D-Cross verdict

The C imports can be moved to top-level. The D imports require separate verdicts (see below).

**Before State**:
```python
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.models.project import Project
    from autom8_asana.models.section import Section
```

**After State** (C imports only; D imports addressed separately):
```python
from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration
from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.project import Project
    from autom8_asana.models.section import Section
```

**Invariants**:
- `DataFrameCacheIntegration`, `DataFrameSchema`, `CustomFieldResolver` become runtime-resolvable
- String annotations in function signatures can optionally be changed to bare names
- No behavior change

**Verification**:
1. `python -c "from autom8_asana.services.dataframe_service import DataFrameService"`
2. `pytest tests/unit/services/ -x`
3. Full suite: `pytest tests/ -x`

**Rollback**: Revert single commit.

---

## 2. Category D Verdicts

### 2.1 D-Root: AsanaClient/AsanaConfig Guards (22 files)

**Critical Finding**: The `autom8_asana/__init__.py` package init imports `client.py`
and `config.py` at top-level. `client.py` transitively imports from: `_defaults`,
`batch`, `cache`, `clients`, `config`, `exceptions`, `persistence`, `protocols`,
`transport`. `config.py` transitively imports from: `automation.config`, `exceptions`,
`settings`, `core`.

Any D-Root file in a package that is in the transitive import chain of `__init__.py`
must KEEP its TYPE_CHECKING guard. Files in packages outside this chain can REMOVE.

**Import chain packages** (KEEP if source is one of these):
- `_defaults`, `batch`, `cache`, `clients`, `config`, `exceptions`, `persistence`,
  `protocols`, `transport`, `automation` (via config.py -> automation.config),
  `core` (via config.py -> core.entity_registry), `settings`, `observability` (via __init__.py)

**Safe packages** (REMOVE -- not in transitive chain):
- `dataframes`, `lifecycle`, `models` (business submodules only -- core models are in chain
  but business/ is not imported by models/__init__.py), `services`, `search`, `query`,
  `resolution`, `metrics`, `lambda_handlers`

| File | Source Pkg | Guard | Verdict | Rationale |
|------|-----------|-------|---------|-----------|
| `automation/waiter.py` | automation | AsanaClient | **KEEP** | config.py -> automation.config -> automation/__init__.py -> waiter.py |
| `cache/dataframe/warmer.py` | cache | AsanaClient | **KEEP** | client.py -> cache at runtime |
| `clients/name_resolver.py` | clients | AsanaClient | **KEEP** | client.py -> clients at runtime |
| `clients/task_operations.py` | clients | AsanaClient | **KEEP** | client.py -> clients at runtime |
| `clients/task_ttl.py` | clients | AsanaConfig | **KEEP** | client.py -> clients at runtime |
| `clients/tasks.py` | clients | AsanaClient | **KEEP** | client.py -> clients at runtime |
| `dataframes/builders/freshness.py` | dataframes | AsanaClient | **REMOVE** | dataframes not in __init__.py chain |
| `dataframes/storage.py` | dataframes | S3LocationConfig | **REMOVE** | dataframes not in __init__.py chain |
| `lifecycle/dispatch.py` | lifecycle | AsanaClient | **REMOVE** | lifecycle not in __init__.py chain |
| `models/business/asset_edit.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/base.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/detection/facade.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/detection/tier1.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/detection/tier4.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/hydration.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/mixins.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/registry.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/resolution.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `models/business/unit.py` | models | AsanaClient | **REMOVE** | business/ not in models/__init__.py |
| `services/section_timeline_service.py` | services | AsanaClient | **REMOVE** | services not in __init__.py chain |
| `transport/asana_http.py` | transport | AsanaConfig | **KEEP** | client.py -> transport at runtime |
| `transport/config_translator.py` | transport | AsanaConfig | **KEEP** | client.py -> transport at runtime |

**D-Root Summary**: 12 REMOVE, 10 KEEP.

---

### 2.2 D-Cross Verdicts (61 files)

For each D-Cross file, the question is: does the target package have a runtime
import path back to the source file's package (directly or transitively through
`__init__.py`)? If yes, KEEP. If no, REMOVE.

**Methodology**: For each entry, I checked:
1. Does the target package import from the source package at runtime?
2. Is the source package in the transitive import chain of `__init__.py`?
3. Would a top-level import trigger `__init__.py` of the target, and does that
   `__init__.py` transitively reach back to the source?

| File | Source | Target(s) | Verdict | Rationale |
|------|--------|-----------|---------|-----------|
| `_defaults/cache.py` | _defaults | cache | **KEEP** | _defaults in __init__.py chain; cache imports _defaults (deferred but bidirectional risk) |
| `api/errors.py` | api | services | **REMOVE** | api not in __init__.py chain; services has no runtime import from api |
| `api/preload/legacy.py` | api | dataframes, services | **REMOVE** | api not in chain; neither target imports api |
| `api/routes/workflows.py` | api | lambda_handlers | **REMOVE** | api not in chain; lambda_handlers does not import api |
| `automation/base.py` | automation | models, persistence | **KEEP** | automation in chain via config.py; automation/__init__.py imports base.py |
| `automation/context.py` | automation | (root), persistence | **KEEP** | automation in chain; context.py imported by automation/__init__.py (via engine) |
| `automation/engine.py` | automation | (root), models, persistence | **KEEP** | automation in chain; engine.py imported by automation/__init__.py |
| `automation/events/rule.py` | automation | models | **KEEP** | automation in chain; rule.py may be loaded transitively |
| `automation/pipeline.py` | automation | models | **KEEP** | automation in chain; pipeline.py lazy-loaded via __getattr__ (safe but conservative) |
| `automation/polling/structured_logger.py` | automation | persistence | **KEEP** | automation in chain |
| `automation/seeding.py` | automation | (root), models | **KEEP** | automation in chain; seeding.py imported by automation/__init__.py |
| `automation/templates.py` | automation | (root), models | **KEEP** | automation in chain; templates.py imported by automation/__init__.py |
| `automation/workflows/base.py` | automation | core | **KEEP** | automation in chain |
| `automation/workflows/conversation_audit.py` | automation | clients, core, models | **KEEP** | automation in chain |
| `automation/workflows/insights_export.py` | automation | clients, core | **KEEP** | automation in chain |
| `automation/workflows/section_resolution.py` | automation | clients | **KEEP** | automation in chain |
| `cache/integration/factory.py` | cache | (root), batch | **KEEP** | cache in chain |
| `cache/integration/freshness_coordinator.py` | cache | batch | **KEEP** | cache in chain |
| `cache/integration/hierarchy_warmer.py` | cache | clients | **KEEP** | cache in chain; clients imports cache (deferred) |
| `cache/integration/staleness_coordinator.py` | cache | batch | **KEEP** | cache in chain |
| `cache/integration/upgrader.py` | cache | clients | **KEEP** | cache in chain |
| `cache/policies/lightweight_checker.py` | cache | batch | **KEEP** | cache in chain |
| `cache/providers/unified.py` | cache | batch, clients | **KEEP** | cache in chain |
| `client.py` | (root) | automation, cache, search | **KEEP** | root file; automation/cache guards are intentional cycle prevention |
| `clients/base.py` | clients | (root), cache, transport | **KEEP** | clients in chain |
| `clients/data/_cache.py` | clients | models | **KEEP** | clients in chain; but models imports are from leaf modules... conservative KEEP |
| `clients/data/_endpoints/batch.py` | clients | models | **KEEP** | clients in chain |
| `clients/data/client.py` | clients | cache | **KEEP** | clients in chain; cache <-> clients bidirectional |
| `config.py` | (root) | cache | **KEEP** | root file; cache in chain |
| `lambda_handlers/workflow_handler.py` | lambda_handlers | automation | **REMOVE** | lambda_handlers not in chain; automation does not import lambda_handlers |
| `lifecycle/completion.py` | lifecycle | (root), models | **REMOVE** | lifecycle not in chain |
| `lifecycle/creation.py` | lifecycle | (root), models, resolution | **REMOVE** | lifecycle not in chain |
| `lifecycle/engine.py` | lifecycle | (root), models | **REMOVE** | lifecycle not in chain |
| `lifecycle/init_actions.py` | lifecycle | (root), models, resolution | **REMOVE** | lifecycle not in chain |
| `lifecycle/reopen.py` | lifecycle | (root), models, resolution | **REMOVE** | lifecycle not in chain |
| `lifecycle/sections.py` | lifecycle | (root), resolution | **REMOVE** | lifecycle not in chain |
| `lifecycle/seeding.py` | lifecycle | (root), models | **REMOVE** | lifecycle not in chain |
| `lifecycle/wiring.py` | lifecycle | (root), resolution | **REMOVE** | lifecycle not in chain |
| `metrics/resolve.py` | metrics | dataframes | **REMOVE** | metrics not in chain; dataframes does not import metrics |
| `models/business/business.py` | models | (root), clients | **REMOVE** | business/ not in models/__init__.py; clients does not import business/ |
| `models/business/seeder.py` | models | (root), search | **REMOVE** | business/ not in chain |
| `persistence/action_executor.py` | persistence | batch, transport | **KEEP** | persistence in chain |
| `protocols/cache.py` | protocols | cache | **KEEP** | protocols in chain (client.py -> protocols.cache) |
| `protocols/dataframe_provider.py` | protocols | (root), cache | **KEEP** | protocols in chain |
| `protocols/insights.py` | protocols | clients | **KEEP** | protocols in chain |
| `protocols/item_loader.py` | protocols | models | **KEEP** | protocols in chain; but models is also in chain |
| `query/aggregator.py` | query | dataframes | **REMOVE** | query not in chain; dataframes does not import query |
| `query/compiler.py` | query | dataframes | **REMOVE** | query not in chain |
| `query/engine.py` | query | (root), metrics | **REMOVE** | query not in chain |
| `query/guards.py` | query | dataframes | **REMOVE** | query not in chain |
| `resolution/context.py` | resolution | (root), models | **REMOVE** | resolution not in chain |
| `resolution/selection.py` | resolution | models | **REMOVE** | resolution not in chain |
| `resolution/strategies.py` | resolution | models | **REMOVE** | resolution not in chain |
| `resolution/write_registry.py` | resolution | core | **REMOVE** | resolution not in chain; core does not import resolution |
| `search/service.py` | search | dataframes | **REMOVE** | search not in chain |
| `services/field_write_service.py` | services | (root), cache | **REMOVE** | services not in chain |
| `services/gid_lookup.py` | services | models | **REMOVE** | services not in chain |
| `services/query_service.py` | services | (root), cache, metrics, query | **REMOVE** | services not in chain |
| `services/section_service.py` | services | (root), cache | **REMOVE** | services not in chain |
| `services/task_service.py` | services | (root), cache | **REMOVE** | services not in chain |
| `services/universal_strategy.py` | services | (root), cache | **REMOVE** | services not in chain |

**D-Cross Summary**: 25 REMOVE, 36 KEEP.

---

### 2.3 Combined D Verdict Summary

| Category | REMOVE | KEEP |
|----------|-------:|-----:|
| D-Root (22 files) | 12 | 10 |
| D-Cross (61 files) | 25 | 36 |
| **D Total (83 files)** | **37** | **46** |

---

## 3. Undocumented Cycle Adjudication

### 3.1 cache <-> clients (3+2 guarded files)

**Analysis**:
- cache -> clients: 3 files, all TYPE_CHECKING only (upgrader.py, hierarchy_warmer.py, unified.py)
- clients -> cache: 2 D files (base.py, data/client.py), TYPE_CHECKING + deferred runtime imports

**Runtime imports**:
- clients -> cache: Deferred only (function-local `from autom8_asana.cache.models.entry import ...`)
- cache -> clients: TYPE_CHECKING only (no runtime)

**Verdict**: NOT a runtime cycle. The deferred imports in clients break any potential
cycle. All guards are in-chain packages (both cache and clients are in __init__.py chain),
so KEEP all guards for safety. No addition to structural cycle registry needed.

### 3.2 clients <-> models (2+1 guarded files)

**Analysis**:
- clients -> models: 2 D files, but clients has MANY top-level runtime imports from models (PageIterator, Task, etc.)
- models -> clients: 1 D file (business/business.py), TYPE_CHECKING only

**Runtime imports**:
- clients -> models: Top-level runtime (many files)
- models -> clients: TYPE_CHECKING only (no runtime)

**Verdict**: NOT a runtime cycle. Unidirectional at runtime (clients -> models).
The guard in `models/business/business.py` is defensive only. Since business/ is
not in the models/__init__.py chain, it can be REMOVED (already counted in D-Root/D-Cross verdicts above).

### 3.3 protocols <-> cache (1+13 guarded files)

**Analysis**:
- protocols -> cache: 1 D file (`protocols/cache.py`, 4 imports), TYPE_CHECKING only
- cache -> protocols: 13 files, a mix of TYPE_CHECKING (10 files) and top-level runtime (3 files: s3.py, redis.py, memory.py import `WarmResult`)

**Runtime imports**:
- cache -> protocols: Top-level runtime (3 backend files import `WarmResult`)
- protocols -> cache: TYPE_CHECKING only (no runtime)

**Verdict**: NOT a runtime cycle. Unidirectional at runtime (cache -> protocols).
However, both packages are in the `__init__.py` import chain (client.py imports from
both), so all guards are KEEP for safety. No addition to structural cycle registry needed.

### 3.4 Updated Structural Cycle Registry Note

The smell report identified 3 bidirectional TYPE_CHECKING pairs. None are actual
runtime cycles. However, one correction to the existing registry:

**automation <-> lifecycle** (listed as "Cut" in PROMPT_0):
- Partially cut only. `lifecycle/seeding.py` still has a top-level runtime import
  from `automation/seeding.py`. The TYPE_CHECKING guards in
  `automation/workflows/pipeline_transition.py` are actively preventing circular imports.
- **Recommendation**: Reclassify from "Cut" to "Residual" in the cycle registry.
  The cycle is reduced but not eliminated.

---

## 4. Removal Phases

### Phase 3A: Low-Risk Removals (25 files, ~60 imports)

Files outside the `__init__.py` transitive import chain. Zero cycle risk.

**Scope**:
- Lifecycle D-Root + D-Cross (8+1 files): lifecycle/dispatch, completion, creation,
  engine, init_actions, reopen, sections, seeding, wiring
- Models D-Root (9 files): models/business/asset_edit, base, detection/facade,
  detection/tier1, detection/tier4, hydration, mixins, registry, resolution, unit
- Models D-Cross (2 files): models/business/business, seeder
- Services D-Root + D-Cross (7 files): services/section_timeline_service,
  field_write_service, gid_lookup, query_service, section_service, task_service,
  universal_strategy
- Resolution D-Cross (4 files): resolution/context, selection, strategies, write_registry
- Query D-Cross (4 files): query/aggregator, compiler, engine, guards
- Dataframes D-Root (2 files): dataframes/builders/freshness, storage
- Other D-Cross (4 files): api/errors, api/preload/legacy, api/routes/workflows,
  lambda_handlers/workflow_handler, metrics/resolve, search/service

**Commit granularity**: 3 commits by package family
1. lifecycle/ + models/business/ (19 files)
2. services/ + resolution/ + query/ (15 files)
3. api/ + dataframes/ + lambda_handlers/ + metrics/ + search/ (7 files)

**Rollback**: Each commit is independently revertable.

### Phase 3B: Category C Removals (2 files, 4 imports)

Confirmed-safe removals from cut-cycle analysis.

**Scope**:
1. `api/dependencies.py`: Move all 6 TYPE_CHECKING imports to top-level. Eliminate TYPE_CHECKING block entirely.
2. `services/dataframe_service.py`: Move 3 C-category imports to top-level. Retain TYPE_CHECKING block for remaining D imports (AsanaClient, Project, Section).

**Commit granularity**: 1 commit (both files).

**Rollback**: Revert single commit.

---

## 5. Risk Assessment

| Phase | Files | Blast Radius | Failure Detection | Rollback Cost |
|-------|------:|-------------|-------------------|---------------|
| 3A-1 | 19 | lifecycle, models/business | `python -c "import autom8_asana.lifecycle"` + `pytest tests/unit/models/business/ -x` | 1 revert |
| 3A-2 | 15 | services, resolution, query | `pytest tests/unit/services/ tests/unit/query/ -x` | 1 revert |
| 3A-3 | 7 | api, dataframes, lambda, metrics, search | `pytest tests/unit/ -x` (broader net) | 1 revert |
| 3B | 2 | api/dependencies, services/dataframe_service | `python -c "from autom8_asana.api.dependencies import *"` + `pytest tests/ -x` | 1 revert |

**Overall risk**: LOW. All Phase 3A removals are in packages completely outside the
`__init__.py` transitive import chain. Phase 3B removals are verified against
specific cycle cuts.

---

## 6. What Stays

### Category A (36 files, 48 imports) -- Structural cycle guards
All KEEP. These guard the 7 known structural cycles.

### Category B (112 files, 334 imports) -- Standard type-only usage
All KEEP. These are idiomatic Python (no cycle, just type-hint optimization).

### Category D KEEP (46 files, ~95 imports) -- In-chain defensive guards
All KEEP. These are in packages that participate in the `__init__.py` transitive
import chain. While individually some might be safe, the interconnected nature of
the chain makes removal risky without refactoring the package init structure.

### Reclassified C->A (2 imports in 1 file)
KEEP. The automation <-> lifecycle cycle is not fully cut.

---

## 7. Final Verdict

**PARTIAL -- proceed with Phase 3 for safe removals.**

| Metric | Value |
|--------|-------|
| Total TYPE_CHECKING blocks | 234 |
| Removable (Phase 3A+3B) | 39 files (~17%) |
| Remaining after cleanup | 195 files (83%) |
| Estimated effort (Phase 3) | 2-3 hours |
| Risk profile | LOW |
| Expected import reduction | ~70 guarded imports -> top-level |

**Rationale for PARTIAL**:
- 39 files is meaningful cleanup (~17% reduction) with verified-zero cycle risk
- Remaining 195 files are either structurally necessary (A: 36, B: 112) or in the
  high-risk transitive import chain (D-KEEP: 46 + reclassified: 1)
- Reducing further would require refactoring `__init__.py` to use lazy loading
  for all re-exports, which is a separate architectural initiative
- The 46 D-KEEP files are individually defensible but collectively risky to touch
  without first untangling the `__init__.py` import graph

**Recommendation**: Execute Phase 3 (Phases 3A + 3B). Defer D-KEEP reductions to a
future initiative that addresses `__init__.py` lazy-loading (this would unlock
another ~46 files for cleanup).

---

## 8. Janitor Notes

### Commit Conventions
- Prefix: `refactor(hygiene):` for all commits
- Each commit message references this spike: `(SPIKE-TYPE-CHECKING Phase 3)`
- Include count of files and imports changed

### Implementation Pattern
For each file being modified:
1. Read the file
2. Identify the TYPE_CHECKING block
3. For REMOVE-all files: move all guarded imports to top-level, remove `TYPE_CHECKING` import and `if TYPE_CHECKING:` block
4. For partial files (e.g., dataframe_service.py): move only specified imports, keep remaining in block
5. Update string annotations to bare names where the import is now top-level
6. Run `python -c "import autom8_asana.{module}"` to verify no circular import
7. Run scoped tests

### String Annotation Conversion
When a TYPE_CHECKING import is removed, any string annotations using that type
(e.g., `"AsanaClient"` or `"DataFrameCache | None"`) can optionally be converted
to bare names. This is cosmetic only -- `from __future__ import annotations`
defers all annotation evaluation, so string vs bare makes no runtime difference.

**Decision**: Do NOT convert string annotations in this phase. It is unnecessary
churn and increases diff size. The `from __future__ import annotations` at the
top of each file already defers annotation evaluation.

### Critical Ordering
- Phase 3A before Phase 3B (lower risk first)
- Within Phase 3A, the 3 commits are independent (no ordering dependency)
- Run full test suite between Phase 3A and Phase 3B

### Test Requirements
- Per-commit: `python -c "import autom8_asana.{module}"` for each touched module
- Per-phase: `pytest tests/ -x` (full suite)
- Gate: Zero new test failures beyond pre-existing baseline (10,492 passed, 178+35 pre-existing failures)

---

## Attestation

| Check | Status |
|-------|--------|
| All Category C files verified for reverse runtime imports | PASS |
| All D-Root files checked against __init__.py transitive chain | PASS |
| All D-Cross files checked for bidirectional runtime imports | PASS |
| Bidirectional pairs adjudicated (3 pairs) | PASS |
| automation <-> lifecycle cycle reclassified | PASS |
| Phase sequencing follows low-to-high risk | PASS |
| Rollback points defined between phases | PASS |
| No architectural changes proposed beyond import guard removal | PASS |
| No new abstractions or protocols designed | PASS |
| Read tool used to verify all referenced files | PASS |
