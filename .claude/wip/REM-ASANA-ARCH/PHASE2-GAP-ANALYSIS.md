# REM-ASANA-ARCH Phase 2: Gap Analysis (83 -> 92+)

**Spike**: Architecture health score gap analysis
**Date**: 2026-02-24
**Session**: session-20260224-014749-f2547c57

---

## Raw Findings Summary

| Dimension | Key Number | Surprise? |
|-----------|-----------|-----------|
| Deferred imports | 549 across 233 files (down from 915) | Reduced ~40%, but still substantial |
| Bidirectional 2-cycles | **13 remain** (not 3) | YES — Phase 1 claimed 3 of 6; actual count is 13 |
| Layer violations | 36 total (13 runtime, 23 TYPE_CHECKING) | 2 systematic patterns account for 13 of 13 runtime |
| Singletons | 9 registered + **1 unregistered** (EntityRegistry) | Test isolation bug |
| automation/ blast radius | 33 files, 10.8 kLOC, only 12 external imports | XR-001 leverage revised: 3/10 -> 7/10 |
| Test failures (203) | **0 caused by Phase 1**, 20 fixable in 4-6 hrs | No coupling-related fixes unlocked |

### Cycle Count Correction

Phase 1 TRACKER claimed "3 of 6 cycles eliminated." Investigation reveals the original "6 cycles" undercounted. The actual bidirectional import graph has **13 runtime 2-cycles**. Phase 1 fully eliminated 1 (Cycle 5: cache->api). Cycles 1 and 4 still have residual bidirectional imports despite protocol extraction.

Fully clean: `cache -> api` (Cycle 5 only)
Partially reduced: `models <-> dataframes` (Cycle 1), `core <-> services` (Cycle 4)
Untouched: 10 additional 2-cycles discovered by this analysis

---

## Scored Gap Matrix

| # | Gap | Points | Effort (hrs) | Leverage (pts/hr) | Surgical? | Dependencies |
|---|-----|--------|-------------|-------------------|-----------|--------------|
| G-01 | Extract `to_pascal_case()` to `core/` | 2 | 2 | 1.0 | YES | None |
| G-02 | Move `register_holder()` to `core/registry.py` | 2 | 3 | 0.67 | YES | None |
| G-03 | Register EntityRegistry with SystemContext | 1 | 0.5 | 2.0 | YES | None |
| G-04 | Cut 5 surgical cycles (automation↔lifecycle, cache↔models, core↔dataframes, core↔models, dataframes↔services) | 3 | 8 | 0.38 | YES | G-01 helps core↔dataframes |
| G-05 | Protocol purity (remove impl imports from protocols/) | 1 | 4 | 0.25 | MEDIUM | None |
| G-06 | automation/ pipeline rules -> lifecycle/ (Scenario C) | 2 | 16 | 0.13 | MEDIUM | None |
| G-07 | Fix 20 phantom HTTP mock targets | 1 | 5 | 0.20 | YES | None |
| G-08 | Remove unnecessary TYPE_CHECKING guards (post-cycle-cut) | 1 | 4 | 0.25 | YES | G-04 |
| **TOTAL** | | **13** | **42.5** | | | |

**Pareto frontier (83 -> 92)**: G-03 + G-01 + G-02 + G-04 = **8 points in 13.5 hours** (4 sessions)

---

## Phase 2 Manifest

### Target: 83 -> 91-92 in 3-4 sessions

Based on leverage ranking, the top items that close the gap with minimum sessions:

---

### Session P2-01: Utility Extraction + EntityRegistry Fix (2 hrs)
**Rite**: hygiene
**Scope**: G-01 + G-02 + G-03

**G-01: Extract `to_pascal_case()` to `core/string_utils.py`**
- FROM: `services/resolver.py` (utility trapped in service layer)
- TO: `core/string_utils.py` (new file, single function)
- Update 5 import sites:
  - `cache/dataframe/factory.py:55` (runtime)
  - `cache/integration/schema_providers.py:27` (runtime)
  - `core/registry_validation.py:62` (deferred -> runtime)
  - `core/schema.py:70` (deferred -> runtime)
  - `dataframes/builders/progressive.py:70` (deferred -> runtime)
- Gate: `grep "from autom8_asana.services.resolver import to_pascal_case" src/` -> 0 matches
- Tests: `pytest tests/unit/cache/ tests/unit/core/ tests/unit/dataframes/ -x`

**G-02: Move `register_holder()` to `core/registry.py`**
- FROM: `persistence/holder_construction.py`
- TO: `core/registry.py` (new file or extend `core/entity_registry.py`)
- Update 9 import sites (all in `models/business/*.py`)
- Gate: `grep "from autom8_asana.persistence.holder_construction import register_holder" src/autom8_asana/models/` -> 0 matches
- Tests: `pytest tests/unit/persistence/ tests/unit/models/ -x`

**G-03: Register EntityRegistry with SystemContext**
- File: `core/entity_registry.py` (add `register_reset()` at module bottom)
- Add `reset()` classmethod if missing
- Gate: `grep "register_reset" src/autom8_asana/core/entity_registry.py` -> 1 match
- Tests: `pytest tests/unit/core/ -x`

**File-scope contract**:
```
TOUCH: core/string_utils.py (NEW), core/registry.py (NEW or extend entity_registry.py),
       core/entity_registry.py, services/resolver.py, persistence/holder_construction.py
UPDATE IMPORTS: cache/dataframe/factory.py, cache/integration/schema_providers.py,
                core/registry_validation.py, core/schema.py, dataframes/builders/progressive.py,
                models/business/{contact,unit,offer,location,process,business,custom_field_accessor}.py
DO NOT TOUCH: api/, query/, clients/, protocols/, automation/
```

**Points**: +5 (G-01: 2, G-02: 2, G-03: 1)
**Running total**: 83 + 5 = **88**

---

### Session P2-02: Surgical Cycle Cuts (4-5 hrs)
**Rite**: 10x-dev (protocol extraction patterns)
**Scope**: G-04 (5 surgical cycles)

**Cycle: `automation ↔ lifecycle`** (3 imports, 2 files)
- `automation/workflows/pipeline_transition.py:194` imports from lifecycle
- `lifecycle/seeding.py:29` imports from automation
- Fix: Extract shared type/interface to `core/` or `protocols/`

**Cycle: `cache ↔ models`** (3 imports, 2 files)
- `cache/integration/derived.py:19` imports from models
- `models/business/detection/facade.py:24` imports from cache
- Fix: Extract cache type reference to protocol or move detection concern

**Cycle: `core ↔ dataframes`** (17 imports, asymmetric)
- `core/schema.py:26` imports from dataframes (SINGLE direction from core)
- Fix: Move schema utility that depends on dataframes out of core, OR extract interface

**Cycle: `core ↔ models`** (6 imports, 2 files)
- `core/registry_validation.py:139`, `core/schema.py:26` import from models
- Fix: Extract model types used by core into `core/types.py` or use protocols

**Cycle: `dataframes ↔ services`** (23 imports, asymmetric)
- `dataframes/builders/progressive.py:1234-1235` imports from services (ONLY 2 imports)
- Fix: Extract the 2 service references to protocol/callback parameter

**File-scope contract**:
```
TOUCH: core/schema.py, core/registry_validation.py, cache/integration/derived.py,
       models/business/detection/facade.py, dataframes/builders/progressive.py,
       automation/workflows/pipeline_transition.py, lifecycle/seeding.py
MAY CREATE: core/types.py (shared type definitions)
DO NOT TOUCH: api/, clients/, persistence/, query/, protocols/ (except new protocol if needed)
```

**Gate**: For each cycle, verify bidirectional imports are broken:
```bash
# automation ↔ lifecycle
grep "from autom8_asana.lifecycle" src/autom8_asana/automation/ -> 0
grep "from autom8_asana.automation" src/autom8_asana/lifecycle/ -> 0

# cache ↔ models (should be unidirectional cache -> models OR models -> cache, not both)
# core ↔ dataframes (core should not import dataframes)
grep "from autom8_asana.dataframes" src/autom8_asana/core/ -> 0

# core ↔ models (core should not import models)
grep "from autom8_asana.models" src/autom8_asana/core/ -> 0 (may need TYPE_CHECKING exception)

# dataframes ↔ services
grep "from autom8_asana.services" src/autom8_asana/dataframes/ -> 0
```

**Points**: +3
**Running total**: 88 + 3 = **91**

---

### Session P2-03: Protocol Purity + Guard Cleanup (2-3 hrs)
**Rite**: hygiene
**Scope**: G-05 + G-08

**G-05: Protocol purity**
- `protocols/cache.py:10,14` — imports from `cache.integration` (violation)
- `protocols/dataframe_provider.py:12` — imports from `cache` (violation)
- `protocols/insights.py:15` — imports from `clients` (violation)
- Fix: Define pure abstract types in protocols, move concrete type references to TYPE_CHECKING or eliminate

**G-08: Remove unnecessary TYPE_CHECKING guards**
- Post-cycle-cut, scan for TYPE_CHECKING guards that protected now-eliminated cycles
- Verify each guard is still needed by temporarily removing and running imports
- Focus on top-15 files from the deferred import analysis

**File-scope contract**:
```
TOUCH: protocols/cache.py, protocols/dataframe_provider.py, protocols/insights.py
SCAN: top-15 files by deferred import count (see gap analysis)
DO NOT TOUCH: api/, core/, persistence/, clients/
```

**Points**: +2 (G-05: 1, G-08: 1)
**Running total**: 91 + 2 = **93**

---

### Session P2-04 (OPTIONAL): Test Fixes + automation/ Reorg
**Rite**: hygiene
**Scope**: G-07 (+ G-06 if time permits)

**G-07: Fix 20 phantom HTTP mock targets**
- `tests/unit/clients/data/test_client.py` — 11 tests mocking `httpx.AsyncClient` instead of `Autom8yHttpClient`
- `tests/unit/services/test_gid_push.py` — 8 tests with same issue
- 3 closing tests asserting `aclose()` instead of `close()`
- Fix patterns documented in `.wip/REMEDY-tests-unit-p1.md`

**G-06: automation/ pipeline rules -> lifecycle/ (if time)**
- Move pipeline.py, seeding.py, templates.py, waiter.py, validation.py
- Update ~25 import sites
- Full effort: 2-3 days standalone, but could be started in this session

**Points**: +1-3 (G-07: 1, G-06: 2 if completed)
**Running total**: 93-95

---

## Score Projection

| After Session | Score | Delta | Cumulative Effort |
|---------------|-------|-------|-------------------|
| Phase 1 (done) | 83 | +15 from 68 | ~10 hrs |
| P2-01 | 88 | +5 | +2 hrs |
| P2-02 | 91 | +3 | +5 hrs |
| P2-03 | 93 | +2 | +3 hrs |
| P2-04 (optional) | 94-95 | +1-2 | +5 hrs |

**Minimum sessions to hit 92**: 3 (P2-01 through P2-03, ~10 hrs)
**Sessions to hit 95**: 4 (include P2-04, ~15 hrs total)

---

## What NOT to Do (Effort Sinks)

| Item | Why Skip |
|------|----------|
| Fix all 549 deferred imports | Most are legitimate type-hint guards, not cycle artifacts |
| Eliminate all 13 2-cycles | 8 are structural (cache↔dataframes, clients↔persistence, etc.) — would require major redesign |
| Decompose automation/ fully | Scenario B (full decomp) is 3-5 days for +2 points — Scenario C is better if pursued |
| Fix 160+ NameGid test failures | Already improved by Phase 1 NameGid fix; remaining are external API contract issues |
| Convert all singletons to DI | Lambda handlers have no DI framework; factory pattern is correct for hybrid codebase |

---

## Key Risk: Cycle Count Discrepancy

The original architecture review identified "6 cycles." This spike found **13 bidirectional 2-cycles** at the package level. The discrepancy likely comes from:
1. Original review counted major architectural cycles (coarse-grained)
2. This analysis counts all bidirectional import pairs (fine-grained)

Phase 1 fully cleaned 1 cycle (Cycle 5), partially addressed 2 (Cycles 1, 4), and left 10 untouched. Phase 2 targets the 5 most surgical of the remaining 12. The other 7 are structural coupling that would require deeper redesign.
