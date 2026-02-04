# TDD: Cache Module Reorganization

**TDD ID**: TDD-CACHE-REORG-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**Sprint**: S3 (Architectural Opportunities -- Wave 3)
**Task**: B2
**PRD Reference**: Architectural Opportunities Initiative
**Depends On**: B4 (Config Consolidation -- Sprint 1), B1 (Entity Registry -- Sprint 2), A2 (Cross-Tier Freshness -- Sprint 2), C3 (Retry Orchestrator -- Sprint 3, placed at `core/retry.py`)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Current Structure Analysis](#2-current-structure-analysis)
3. [Target Structure](#3-target-structure)
4. [File Move Manifest](#4-file-move-manifest)
5. [Import Rewrite Strategy](#5-import-rewrite-strategy)
6. [Migration Plan](#6-migration-plan)
7. [Circular Dependency Prevention](#7-circular-dependency-prevention)
8. [Test Strategy](#8-test-strategy)
9. [ADRs](#9-adrs)
10. [Risk Assessment](#10-risk-assessment)
11. [Success Criteria](#11-success-criteria)

---

## 1. Overview

### 1.1 Problem Statement

The `src/autom8_asana/cache/` directory is a flat namespace containing ~30 files that mix four distinct concerns:

1. **Data models**: `entry.py`, `mutation_event.py`, `freshness_stamp.py`, `freshness.py`, `completeness.py`, `errors.py`
2. **Backend implementations**: `backends/redis.py`, `backends/s3.py`, `backends/memory.py`
3. **Policies and coordination**: `freshness_policy.py`, `staleness_coordinator.py`, `staleness.py`, `staleness_settings.py`, `coalescer.py`, `lightweight_checker.py`
4. **Integration and orchestration**: `tiered.py`, `dataframe_cache.py`, `unified.py`, `mutation_invalidator.py`, `factory.py`, `autom8_adapter.py`, `loader.py`, `dataframes.py`

Additionally, the `dataframe/` subdirectory already exists as a partial reorganization (circuit breaker, coalescer, tiers, warmer), but `dataframe_cache.py` (the primary DataFrameCache class) still lives at the flat level.

This flat structure creates several problems:

- **No dependency direction**: Files at the same level import each other freely, making it unclear which components are foundational vs. derived.
- **Discovery friction**: A developer looking for "how does freshness work" must scan 30 files to find `freshness.py`, `freshness_stamp.py`, `freshness_policy.py`, `freshness_coordinator.py`, and `staleness_coordinator.py`.
- **Placement ambiguity**: When adding new cache functionality, there is no structural guidance for where it should go. The flat layout invites further flattening.
- **Coupling opacity**: `tiered.py` is a provider implementation that coordinates backends, but it lives alongside models and policies. Its architectural role is invisible.

### 1.2 Goals

1. Reorganize cache/ into subdirectories that reflect a layered dependency structure: models at the bottom, policies in the middle, providers and integration at the top.
2. Zero import breakage. Every existing `from autom8_asana.cache.X import Y` continues to work via re-exports.
3. Make the dependency direction explicit and enforceable: models have zero intra-cache imports; policies import only models; providers import models and policies.
4. Provide clear placement guidance for future cache features.

### 1.3 Non-Goals

- Changing any public API or class names.
- Merging the two `CacheEntry` classes (that is B3, a separate opportunity).
- Modifying the `dataframe/` subdirectory internal structure (it already has its own organization).
- Changing the `backends/` subdirectory internal structure.
- Altering the `_defaults/cache.py` module (it sits outside the cache package).

---

## 2. Current Structure Analysis

### 2.1 File Inventory

```
src/autom8_asana/cache/
    __init__.py              # Re-export hub (~250 lines, exports ~55 symbols)
    autom8_adapter.py        # External SDK integration adapter
    batch.py                 # Batch modification checking
    coalescer.py             # Request coalescing for staleness checks
    completeness.py          # Completeness level tracking
    dataframe_cache.py       # DataFrameCache class (33KB, largest file)
    dataframes.py            # Dataframe key helpers (make_key, invalidate)
    entry.py                 # CacheEntry + EntryType models
    errors.py                # Error classification + DegradedModeMixin
    events.py                # Cache event integration (metrics callbacks)
    factory.py               # CacheProviderFactory
    freshness.py             # Freshness enum (re-exports from SDK)
    freshness_coordinator.py # FreshnessMode coordinator
    freshness_policy.py      # FreshnessPolicy evaluator (A2)
    freshness_stamp.py       # FreshnessStamp + VerificationSource (A2)
    hierarchy.py             # HierarchyIndex
    hierarchy_warmer.py      # HierarchyWarmer
    lightweight_checker.py   # LightweightChecker for staleness
    loader.py                # Multi-entry loading (load_task_entry, etc.)
    metrics.py               # CacheMetrics + CacheEvent
    mutation_event.py        # MutationEvent + EntityKind + MutationType (A1)
    mutation_invalidator.py  # MutationInvalidator service (A1)
    schema_providers.py      # Schema registration
    settings.py              # CacheSettings + TTLSettings
    staleness.py             # Staleness check utilities
    staleness_coordinator.py # StalenessCheckCoordinator
    staleness_settings.py    # StalenessCheckSettings
    stories.py               # Incremental story loading
    tiered.py                # TieredCacheProvider (two-tier coordinator)
    unified.py               # UnifiedTaskStore
    upgrader.py              # AsanaTaskUpgrader (completeness)
    versioning.py            # Version comparison utilities
    backends/
        __init__.py
        memory.py            # InMemoryCacheProvider
        redis.py             # RedisCacheProvider
        s3.py                # S3CacheProvider
    dataframe/
        __init__.py
        circuit_breaker.py
        coalescer.py
        decorator.py
        factory.py
        warmer.py
        tiers/
            __init__.py
            memory.py
            progressive.py
```

### 2.2 Dependency Analysis

Analysis of intra-cache imports reveals three natural tiers:

**Tier 0 -- Models (imported by everything, import nothing in cache/):**
- `entry.py`: `CacheEntry`, `EntryType` -- imported by 15+ files
- `freshness.py`: `Freshness` enum -- imported by 8+ files
- `freshness_stamp.py`: `FreshnessStamp`, `VerificationSource`, `FreshnessClassification` -- imported by 5+ files
- `mutation_event.py`: `MutationEvent`, `EntityKind`, `MutationType` -- imported by 3 files
- `metrics.py`: `CacheMetrics`, `CacheEvent` -- imported by 5+ files
- `errors.py`: Error classification utilities + `DegradedModeMixin` -- imported by 3+ files
- `completeness.py`: `CompletenessLevel` and helpers -- imported by 3+ files
- `versioning.py`: Version comparison utilities -- imported by 3+ files
- `settings.py`: `CacheSettings`, `TTLSettings` -- imported by 2+ files
- `staleness_settings.py`: `StalenessCheckSettings` -- imported by 2 files
- `events.py`: Metrics callback creation -- imported by 2 files

**Tier 1 -- Policies (import models, imported by providers):**
- `freshness_policy.py`: Imports `entry`, `freshness_stamp` -- stateless evaluator
- `staleness.py`: Imports `entry`, `freshness`, `versioning` -- check utilities
- `lightweight_checker.py`: Imports `entry` -- batch modified_at checker
- `coalescer.py`: Imports `entry`, `lightweight_checker` -- request coalescing
- `hierarchy.py`: `HierarchyIndex` -- pure data structure

**Tier 2 -- Providers (import models + policies):**
- `backends/`: Redis, S3, Memory providers
- `tiered.py`: Imports `entry`, `freshness`, `metrics`, `freshness_stamp` -- coordinates backends
- `unified.py`: `UnifiedTaskStore` -- high-level task cache facade

**Tier 3 -- Integration (import everything, imported by application code):**
- `dataframe_cache.py`: `DataFrameCache` class -- highest-level DF cache
- `mutation_invalidator.py`: Imports `entry`, `mutation_event`, `dataframe_cache`
- `factory.py`: `CacheProviderFactory` -- wires providers together
- `loader.py`: Multi-entry loading helpers
- `autom8_adapter.py`: External SDK adapter
- `staleness_coordinator.py`: Orchestrates coalescer + checker + provider
- `hierarchy_warmer.py`: Warming orchestration
- `schema_providers.py`: Schema registration
- `stories.py`: Story loading helpers
- `batch.py`: Batch modification checking
- `dataframes.py`: DataFrame key utilities
- `upgrader.py`: Completeness upgrader

### 2.3 External Import Patterns

80+ import sites across the codebase reference `autom8_asana.cache.*`. Key patterns:

| Import Pattern | Count | Consumers |
|---------------|-------|-----------|
| `from autom8_asana.cache.entry import CacheEntry, EntryType` | 15+ | backends, tiered, loader, staleness, dataframes, client, _defaults |
| `from autom8_asana.cache.freshness import Freshness` | 8+ | tiered, loader, staleness, _defaults, dataframes |
| `from autom8_asana.cache.mutation_event import ...` | 3 | routes/tasks, routes/sections, mutation_invalidator |
| `from autom8_asana.cache.mutation_invalidator import ...` | 3 | api/dependencies, api/main |
| `from autom8_asana.cache.dataframe_cache import ...` | 2 | services/query_service, services/universal_strategy |
| `from autom8_asana.cache.tiered import ...` | 2 | lambda_handlers/cache_invalidate, (docstrings) |
| `from autom8_asana.cache.unified import ...` | 3 | routes/dataframes, views/dataframe_view, client |
| `from autom8_asana.cache.metrics import ...` | 4 | tiered, _defaults, client |
| `from autom8_asana.cache.freshness_stamp import ...` | 3 | tiered, entry (TYPE_CHECKING), freshness_policy |
| `from autom8_asana.cache.errors import ...` | 1 | dataframes/async_s3 |
| `from autom8_asana.cache.factory import ...` | 3 | client, api/main |
| `from autom8_asana.cache.dataframe.factory import ...` | 5 | api/main, admin routes, lambda handlers, universal_strategy |
| `from autom8_asana.cache.freshness_coordinator import ...` | 2 | factory, views/dataframe_view |

---

## 3. Target Structure

### 3.1 Subdirectory Taxonomy

```
src/autom8_asana/cache/
    __init__.py                  # Public API re-exports (unchanged surface area)

    models/                      # Tier 0: Data models, enums, value objects
        __init__.py              # Re-exports all model types
        entry.py                 # CacheEntry, EntryType
        freshness.py             # Freshness enum
        freshness_stamp.py       # FreshnessStamp, VerificationSource, FreshnessClassification
        mutation_event.py        # MutationEvent, EntityKind, MutationType
        metrics.py               # CacheMetrics, CacheEvent
        errors.py                # Error classification, DegradedModeMixin
        completeness.py          # CompletenessLevel, field sets, helpers
        versioning.py            # Version comparison utilities
        settings.py              # CacheSettings, TTLSettings, OverflowSettings
        staleness_settings.py    # StalenessCheckSettings
        events.py                # Cache event integration (metrics callbacks)

    policies/                    # Tier 1: Stateless evaluation and checking logic
        __init__.py              # Re-exports policy types
        freshness_policy.py      # FreshnessPolicy
        staleness.py             # check_entry_staleness, check_batch_staleness, partition_by_staleness
        lightweight_checker.py   # LightweightChecker
        coalescer.py             # RequestCoalescer
        hierarchy.py             # HierarchyIndex

    backends/                    # Tier 2: Provider implementations (unchanged)
        __init__.py
        memory.py                # InMemoryCacheProvider
        redis.py                 # RedisCacheProvider
        s3.py                    # S3CacheProvider

    providers/                   # Tier 2: Composite provider orchestration
        __init__.py              # Re-exports provider types
        tiered.py                # TieredCacheProvider, TieredConfig
        unified.py               # UnifiedTaskStore

    integration/                 # Tier 3: Application wiring, adapters, helpers
        __init__.py              # Re-exports integration types
        dataframe_cache.py       # DataFrameCache, FreshnessStatus, FreshnessInfo
        mutation_invalidator.py  # MutationInvalidator, SoftInvalidationConfig
        factory.py               # CacheProviderFactory, create_cache_provider
        loader.py                # load_task_entry, load_task_entries, load_batch_entries
        staleness_coordinator.py # StalenessCheckCoordinator
        autom8_adapter.py        # create_autom8_cache_provider, warm_project_tasks, etc.
        hierarchy_warmer.py      # HierarchyWarmer
        schema_providers.py      # register_asana_schemas
        stories.py               # load_stories_incremental, filter_relevant_stories, etc.
        batch.py                 # ModificationCheckCache, fetch_task_modifications, etc.
        dataframes.py            # make_dataframe_key, invalidate_dataframe, etc.
        upgrader.py              # AsanaTaskUpgrader
        freshness_coordinator.py # FreshnessMode

    dataframe/                   # Existing subdirectory (unchanged)
        __init__.py
        circuit_breaker.py
        coalescer.py
        decorator.py
        factory.py
        warmer.py
        tiers/
            __init__.py
            memory.py
            progressive.py
```

### 3.2 Layer Rules

Each layer has strict import constraints:

| Layer | May Import From | May NOT Import From |
|-------|----------------|---------------------|
| `models/` | External packages only (`autom8y_cache`, `autom8y_log`, stdlib) | `policies/`, `backends/`, `providers/`, `integration/`, `dataframe/` |
| `policies/` | `models/`, external packages | `backends/`, `providers/`, `integration/`, `dataframe/` |
| `backends/` | `models/`, external packages, `autom8_asana.core.exceptions`, `autom8_asana.protocols.cache` | `policies/`, `providers/`, `integration/`, `dataframe/` |
| `providers/` | `models/`, `policies/`, `backends/` (via protocol), external packages | `integration/`, `dataframe/` |
| `integration/` | All cache sublayers, `dataframe/`, external packages, other `autom8_asana` modules | (no restrictions -- this is the application wiring layer) |
| `dataframe/` | `models/` (for types), external packages | `policies/`, `providers/`, `integration/` |

### 3.3 Rationale for Taxonomy

**Why `models/` instead of `types/`?** These files contain not just type definitions but value objects with behavior (e.g., `CacheEntry.is_expired()`, `FreshnessStamp.age_seconds()`). "Models" better conveys that these are domain objects.

**Why `policies/` separate from `models/`?** Policies have evaluation logic that depends on configuration lookups (EntityRegistry TTLs, config defaults). Keeping them out of `models/` ensures the model layer remains free of runtime dependencies on the config system.

**Why `providers/` separate from `backends/`?** `backends/` contains concrete storage implementations (Redis, S3, memory). `providers/` contains composite orchestrators (`TieredCacheProvider` coordinates backends; `UnifiedTaskStore` coordinates task-level access). This distinction mirrors the GoF composite pattern: backends are leaves, providers are composites.

**Why `integration/` as a catch-all?** Many files in cache/ exist to wire cache primitives into the application (factory, loader, adapter, invalidator). These files have the broadest dependency surface and are the entry points for application code. Grouping them makes it clear that they are "glue code" with no reuse expectation beyond the autom8_asana application.

**Why keep `backends/` at the same level (not nested under `providers/`)?** Backends are already an established subdirectory with its own `__init__.py`. Moving it would break `from autom8_asana.cache.backends.redis import RedisCacheProvider` with no benefit. The flat relationship between `backends/` and `providers/` correctly reflects that providers depend on backends but do not own them.

---

## 4. File Move Manifest

### 4.1 Complete Source-to-Destination Mapping

| # | Current Path | Target Path | Notes |
|---|-------------|-------------|-------|
| 1 | `cache/entry.py` | `cache/models/entry.py` | Core model, zero intra-cache deps |
| 2 | `cache/freshness.py` | `cache/models/freshness.py` | Enum/re-export, zero deps |
| 3 | `cache/freshness_stamp.py` | `cache/models/freshness_stamp.py` | Frozen dataclass, zero deps |
| 4 | `cache/mutation_event.py` | `cache/models/mutation_event.py` | Frozen dataclass, zero deps |
| 5 | `cache/metrics.py` | `cache/models/metrics.py` | CacheMetrics, zero cache deps |
| 6 | `cache/errors.py` | `cache/models/errors.py` | Error utils + mixin, zero cache deps |
| 7 | `cache/completeness.py` | `cache/models/completeness.py` | CompletenessLevel + helpers |
| 8 | `cache/versioning.py` | `cache/models/versioning.py` | Pure version comparison utils |
| 9 | `cache/settings.py` | `cache/models/settings.py` | CacheSettings config model |
| 10 | `cache/staleness_settings.py` | `cache/models/staleness_settings.py` | StalenessCheckSettings config |
| 11 | `cache/events.py` | `cache/models/events.py` | Metrics callback helpers |
| 12 | `cache/freshness_policy.py` | `cache/policies/freshness_policy.py` | Imports: entry, freshness_stamp |
| 13 | `cache/staleness.py` | `cache/policies/staleness.py` | Imports: entry, freshness, versioning |
| 14 | `cache/lightweight_checker.py` | `cache/policies/lightweight_checker.py` | Imports: entry |
| 15 | `cache/coalescer.py` | `cache/policies/coalescer.py` | Imports: entry, lightweight_checker |
| 16 | `cache/hierarchy.py` | `cache/policies/hierarchy.py` | HierarchyIndex pure data |
| 17 | `cache/tiered.py` | `cache/providers/tiered.py` | Imports: entry, freshness, metrics |
| 18 | `cache/unified.py` | `cache/providers/unified.py` | UnifiedTaskStore |
| 19 | `cache/dataframe_cache.py` | `cache/integration/dataframe_cache.py` | DataFrameCache (33KB) |
| 20 | `cache/mutation_invalidator.py` | `cache/integration/mutation_invalidator.py` | MutationInvalidator |
| 21 | `cache/factory.py` | `cache/integration/factory.py` | CacheProviderFactory |
| 22 | `cache/loader.py` | `cache/integration/loader.py` | Multi-entry loading |
| 23 | `cache/staleness_coordinator.py` | `cache/integration/staleness_coordinator.py` | StalenessCheckCoordinator |
| 24 | `cache/autom8_adapter.py` | `cache/integration/autom8_adapter.py` | SDK adapter |
| 25 | `cache/hierarchy_warmer.py` | `cache/integration/hierarchy_warmer.py` | Warming orchestration |
| 26 | `cache/schema_providers.py` | `cache/integration/schema_providers.py` | Schema registration |
| 27 | `cache/stories.py` | `cache/integration/stories.py` | Story loading helpers |
| 28 | `cache/batch.py` | `cache/integration/batch.py` | Batch modification checking |
| 29 | `cache/dataframes.py` | `cache/integration/dataframes.py` | DataFrame key utils |
| 30 | `cache/upgrader.py` | `cache/integration/upgrader.py` | AsanaTaskUpgrader |
| 31 | `cache/freshness_coordinator.py` | `cache/integration/freshness_coordinator.py` | FreshnessMode coordinator |

**Files NOT moved:**

| Path | Reason |
|------|--------|
| `cache/__init__.py` | Remains as public API surface; will be rewritten for re-exports |
| `cache/backends/*` | Already organized; stays in place |
| `cache/dataframe/*` | Already organized; stays in place |

### 4.2 New `__init__.py` Files

Each subdirectory gets a minimal `__init__.py` that re-exports its public symbols. This enables both direct imports (`from autom8_asana.cache.models.entry import CacheEntry`) and package-level imports (`from autom8_asana.cache.models import CacheEntry`).

---

## 5. Import Rewrite Strategy

### 5.1 Approach: Shim Files at Old Paths

After moving files to subdirectories, place a **shim module** at each old path that re-exports everything from the new location. Example:

```python
# src/autom8_asana/cache/entry.py (SHIM -- backward compatibility)
"""Backward compatibility shim. See cache/models/entry.py."""
from autom8_asana.cache.models.entry import *  # noqa: F401,F403
from autom8_asana.cache.models.entry import __all__  # noqa: F401
```

This approach means:
- `from autom8_asana.cache.entry import CacheEntry` continues to work.
- `from autom8_asana.cache.models.entry import CacheEntry` also works (canonical path).
- Grep/IDE "find references" can identify shim consumers for eventual migration.

### 5.2 Internal Import Migration

All **intra-cache** imports are updated to use canonical (new) paths immediately. Only **external consumers** (outside cache/) use shims during transition.

Example -- before:
```python
# cache/tiered.py
from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.metrics import CacheMetrics
```

After:
```python
# cache/providers/tiered.py
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.metrics import CacheMetrics
```

### 5.3 The Root `__init__.py`

The root `cache/__init__.py` remains the public API surface. Its imports are updated to point to new canonical locations:

```python
# cache/__init__.py (updated)
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.freshness import Freshness
from autom8_asana.cache.models.settings import CacheSettings, TTLSettings, OverflowSettings
# ... etc
```

Consumers using `from autom8_asana.cache import CacheEntry` continue to work with zero changes.

### 5.4 Shim Deprecation Plan

Shim files carry a `# DEPRECATED` comment and emit no runtime warning (to avoid noise). They are removed in a future sprint after all external consumers have been migrated.

**Deprecation timeline:**

| Phase | Action | Sprint |
|-------|--------|--------|
| Phase 1 | Shims created, all code works | S3 (this sprint) |
| Phase 2 | External consumers migrated to canonical paths | S4 |
| Phase 3 | Shims removed, old paths become errors | S5 |

### 5.5 What Changes for Consumers

For this sprint: **nothing**. Every existing import path continues to work. The migration is transparent.

In future sprints, consumers update from:
```python
from autom8_asana.cache.mutation_event import MutationEvent
```
to:
```python
from autom8_asana.cache.models.mutation_event import MutationEvent
```

---

## 6. Migration Plan

### 6.1 Approach: Single-Commit Big-Bang Move

The reorganization is executed as a single atomic commit. See ADR-B2-002 for the rationale.

**Why not incremental?** Moving files one-by-one creates intermediate states where some files are in subdirectories and some are flat. This is confusing, hard to review, and requires multiple rounds of `__init__.py` updates. A single commit is easier to review ("before" vs "after"), easier to revert, and avoids the intermediate confusion.

**Risk mitigation for big-bang:** The move is purely structural (file paths change, code does not). Shim files ensure zero import breakage. The entire change can be verified by running the full test suite.

### 6.2 Execution Steps

**Step 1: Create subdirectories and `__init__.py` files**

```bash
mkdir -p src/autom8_asana/cache/{models,policies,providers,integration}
```

Create `__init__.py` for each with appropriate re-exports.

**Step 2: Move files to target locations**

Execute moves per the File Move Manifest (Section 4.1). Use `git mv` to preserve history.

**Step 3: Update intra-cache imports**

Rewrite all imports within `cache/` to use canonical paths. For example, `cache/providers/tiered.py` changes from `from autom8_asana.cache.entry import ...` to `from autom8_asana.cache.models.entry import ...`.

**Step 4: Create shim files at old paths**

For each moved file, create a shim at the original path that re-exports from the new location.

**Step 5: Update root `__init__.py`**

Rewrite `cache/__init__.py` imports to point to new canonical paths.

**Step 6: Run full test suite**

```bash
python -m pytest tests/ -x --tb=short
```

All tests must pass with zero modifications to test files (tests import via shims or root `__init__.py`).

**Step 7: Verify import resolution**

```bash
python -c "from autom8_asana.cache import CacheEntry, TieredCacheProvider, MutationInvalidator; print('OK')"
python -c "from autom8_asana.cache.entry import CacheEntry; print('OK')"
python -c "from autom8_asana.cache.models.entry import CacheEntry; print('OK')"
```

### 6.3 Rollback Plan

If the test suite fails and the issue is not immediately fixable:

```bash
git revert HEAD  # Single commit, single revert
```

The big-bang approach makes rollback trivial.

---

## 7. Circular Dependency Prevention

### 7.1 Current Circular Dependencies

The codebase already uses `TYPE_CHECKING` guards to break cycles:

- `entry.py` uses `TYPE_CHECKING` for `FreshnessStamp` (avoids `entry -> freshness_stamp -> entry` cycle)
- `freshness_policy.py` uses `TYPE_CHECKING` for `CacheEntry` and `FreshnessStamp`
- `mutation_invalidator.py` uses `TYPE_CHECKING` for `DataFrameCache` and `CacheProvider`
- `staleness_coordinator.py` uses `TYPE_CHECKING` for `BatchClient` and `CacheProvider`
- `dataframe_cache.py` uses `TYPE_CHECKING` for internal `dataframe/` types

### 7.2 How the New Structure Prevents Cycles

The layered structure enforces a DAG:

```
models/  <--  policies/  <--  providers/  <--  integration/
   |              |               |                |
   v              v               v                v
 (stdlib,      (models/)       (models/,        (everything)
  external)                    policies/,
                               protocols/)
```

**Enforcement mechanism:** No automated linter is proposed in this TDD (that would be a separate tooling initiative). Instead, the layer rules are documented in each `__init__.py` as a comment:

```python
# cache/models/__init__.py
# LAYER RULE: models/ must NOT import from policies/, providers/, or integration/.
# It may import from stdlib, autom8y_cache, autom8y_log, and autom8_asana.core.
```

### 7.3 Known Cross-Layer References to Preserve

These existing patterns use deferred imports or `TYPE_CHECKING` and must be maintained:

| From | To | Mechanism | Purpose |
|------|-----|-----------|---------|
| `models/entry.py` | `models/freshness_stamp.py` | `TYPE_CHECKING` | Type annotation only |
| `policies/freshness_policy.py` | `models/entry.py`, `models/freshness_stamp.py` | `TYPE_CHECKING` | Type annotations |
| `providers/tiered.py` | `models/freshness_stamp.py` | Deferred import in `_promote_entry()` | Runtime lazy load |
| `integration/dataframe_cache.py` | `dataframe/` types | `TYPE_CHECKING` | Type annotations |
| `integration/mutation_invalidator.py` | `integration/dataframe_cache.py` | `TYPE_CHECKING` | Type annotation only |
| `integration/factory.py` | `integration/freshness_coordinator.py`, `providers/unified.py` | `TYPE_CHECKING` | Type annotations |

All of these patterns are preserved as-is. The file moves do not change the import guard structure, only the module paths within the guards.

---

## 8. Test Strategy

### 8.1 Verification Approach

The reorganization is a structural refactor with no logic changes. Testing focuses on import integrity, not behavioral correctness.

**Tier 1: Full Test Suite (blocking)**
```bash
python -m pytest tests/ -x --tb=short
```
All existing tests must pass without modification. If any test fails, the reorganization has broken an import path.

**Tier 2: Import Smoke Tests (blocking)**
A new test file `tests/unit/cache/test_reorg_imports.py` verifies that all public import paths work:

```python
"""Verify all cache import paths work after reorganization."""

def test_root_imports():
    """Root __init__.py exports are accessible."""
    from autom8_asana.cache import CacheEntry, EntryType, Freshness
    from autom8_asana.cache import TieredCacheProvider, TieredConfig
    from autom8_asana.cache import CacheMetrics, CacheEvent
    from autom8_asana.cache import CacheSettings
    # ... all __all__ members

def test_canonical_imports():
    """New canonical paths work."""
    from autom8_asana.cache.models.entry import CacheEntry, EntryType
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp
    from autom8_asana.cache.policies.freshness_policy import FreshnessPolicy
    from autom8_asana.cache.providers.tiered import TieredCacheProvider
    from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator

def test_shim_imports():
    """Old paths still work via shims."""
    from autom8_asana.cache.entry import CacheEntry
    from autom8_asana.cache.freshness_stamp import FreshnessStamp
    from autom8_asana.cache.tiered import TieredCacheProvider
    from autom8_asana.cache.mutation_invalidator import MutationInvalidator
    from autom8_asana.cache.dataframe_cache import DataFrameCache

def test_subpackage_imports():
    """Subpackage __init__.py re-exports work."""
    from autom8_asana.cache.models import CacheEntry, FreshnessStamp
    from autom8_asana.cache.policies import FreshnessPolicy
    from autom8_asana.cache.providers import TieredCacheProvider
    from autom8_asana.cache.integration import MutationInvalidator
```

**Tier 3: Layer Violation Test (non-blocking initially)**
A test that scans imports in each layer to detect violations. This can be implemented as a lint check in a future sprint:

```python
def test_models_layer_no_upward_imports():
    """Models layer must not import from policies, providers, or integration."""
    # Scan cache/models/*.py for prohibited import patterns
    # (implementation left for Principal Engineer)
```

### 8.2 Test File Changes

No existing test files should require changes. Tests import via:
1. Root `cache/__init__.py` (e.g., `from autom8_asana.cache import CacheEntry`) -- still works
2. Direct module paths (e.g., `from autom8_asana.cache.entry import CacheEntry`) -- still works via shim
3. Test patching paths (e.g., `@patch("autom8_asana.cache.dataframe.factory.get_dataframe_cache")`) -- still works, `dataframe/` is not moved

---

## 9. ADRs

### ADR-B2-001: Subdirectory Taxonomy

**Status**: Proposed
**Context**: The cache module has ~30 files in a flat directory with no structural guidance for dependency direction. We need to choose a subdirectory organization scheme.

**Options Considered**:

| Option | Structure | Pros | Cons |
|--------|-----------|------|------|
| **A: By concern (models/policies/providers/integration)** | 4 layers reflecting dependency direction | Clear DAG, enforceable rules, mirrors architecture | More directories, learning curve |
| **B: By feature (freshness/, staleness/, invalidation/, storage/)** | Feature-based grouping | Intuitive navigation by feature | Cross-feature dependencies create cycles; no clear layering |
| **C: By lifecycle (read/, write/, check/)** | Operation-based grouping | Matches runtime flow | Artificial -- many components participate in multiple operations |

**Decision**: Option A -- concern-based layering (models/policies/providers/integration).

**Rationale**: The primary problem is unclear dependency direction, not unclear feature grouping. Option A makes the dependency DAG explicit: models at the bottom, integration at the top. Feature-based (Option B) would group `freshness_stamp.py` (model) with `freshness_policy.py` (policy) and `freshness_coordinator.py` (integration), recreating the flat-structure problem within each feature directory. Option A keeps the "which way do dependencies flow?" question answerable at a glance.

**Consequences**:
- Developers must learn the four-layer model.
- New files have clear placement guidance: "Is this a data model? A stateless evaluator? A backend? Application wiring?"
- Layer violations are detectable (even if not yet automated).

---

### ADR-B2-002: Migration Approach (Big-Bang vs. Incremental)

**Status**: Proposed
**Context**: We must choose between moving all files at once (big-bang) or incrementally (one subdirectory at a time across multiple commits/PRs).

**Options Considered**:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: Big-bang** | Single commit moves all 31 files, creates all shims | Atomic, easy to review as "before/after", trivial rollback via revert | Large diff, merge conflicts if other PRs touch cache/ |
| **B: Incremental** | 4 PRs (one per subdirectory), each moving a subset | Smaller diffs, easier merge | Intermediate states are confusing, requires multiple __init__.py rewrites, harder to reason about partial reorganization |

**Decision**: Option A -- single-commit big-bang.

**Rationale**: The reorganization is purely structural (no logic changes). A big-bang commit is:
1. **Easier to verify**: Run test suite once, not four times with intermediate states.
2. **Easier to revert**: One `git revert`, not four.
3. **Avoids intermediate confusion**: No period where some files are in subdirectories and others are flat.
4. **Merge conflict mitigation**: Schedule the move when no other cache-related PRs are in flight.

The large diff is mitigated by the fact that most of the diff is file moves (`git mv` preserves history) and mechanical shim creation.

**Consequences**:
- Requires coordination: no other cache-related PRs should be in flight during the move.
- The single commit will be large (~31 file moves + ~31 shims + 4 `__init__.py` files + import rewrites). Reviewers should focus on the manifest (Section 4) rather than reading every line.
- Rollback is trivial: `git revert HEAD`.

---

### ADR-B2-003: Re-Export Strategy

**Status**: Proposed
**Context**: After moving files, existing import paths (`from autom8_asana.cache.entry import CacheEntry`) must continue to work. We need to choose how to maintain backward compatibility.

**Options Considered**:

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| **A: Shim files at old paths** | Each old path becomes a module that re-exports from new location | Zero consumer changes, explicit backward compat, grep-findable | Creates ~31 shim files, slight import overhead |
| **B: `__init__.py` re-exports only** | No shim files; rely on `cache/__init__.py` re-exports | Fewer files | Breaks `from autom8_asana.cache.entry import CacheEntry` (only `from autom8_asana.cache import CacheEntry` works) |
| **C: sys.path manipulation** | Add module aliases programmatically | No shim files | Fragile, confusing for IDEs, breaks `mypy` |

**Decision**: Option A -- shim files at old paths.

**Rationale**: Option A is the only approach that preserves **all** existing import patterns with zero consumer changes. Option B would break direct module imports, which are used extensively (80+ sites). Option C is fragile and hostile to static analysis tools.

The overhead of ~31 shim files is minimal (each is 2-3 lines) and they serve as explicit documentation of the backward compatibility contract. Their presence in the file tree also makes it clear which old paths are still supported.

**Deprecation plan**: Shims are removed after all consumers have migrated to canonical paths (estimated S5). Each shim carries a `# DEPRECATED: Use autom8_asana.cache.models.entry instead` comment.

**Consequences**:
- ~31 small shim files are created.
- `mypy` and IDEs continue to work without changes.
- Shims must be maintained until removed (minimal burden since they are pure re-exports).
- The `cache/` directory will temporarily have both shim files (flat) and subdirectories (organized). This is acceptable during the transition period.

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Test failures from missed import paths** | Low | Medium | Comprehensive import smoke test; full test suite run before merge |
| **Merge conflicts with concurrent cache PRs** | Medium | Low | Schedule move when no other cache PRs are in flight; communicate timing |
| **IDE/mypy confusion with shim files** | Low | Low | Shims are standard Python re-exports; tools handle them natively |
| **Circular imports introduced by move** | Low | High | Layer rules documented; all existing deferred imports preserved; import smoke test |
| **`__pycache__` stale bytecode** | Medium | Low | Clean bytecode before running tests: `find . -name __pycache__ -exec rm -rf {} +` |
| **Lambda deployment path changes** | Low | Medium | Lambda imports via `cache/__init__.py` or `cache.dataframe.factory` -- both preserved |
| **Patch/mock paths in tests break** | Medium | Medium | Tests that patch `autom8_asana.cache.X.Y` will work via shims; grep for all patch targets before merge |

### 10.1 Highest-Risk Item

**Patch/mock paths in tests** is the most likely source of breakage. If a test patches `autom8_asana.cache.mutation_invalidator.MutationInvalidator`, the shim at the old path ensures the import works, but the patch target must resolve to the same object. Since shim files re-export via `from ... import *`, the patched name in the shim module is the **same object** as in the canonical module. Patches work correctly because:

```python
# test patches: autom8_asana.cache.mutation_invalidator.MutationInvalidator
# shim module: from autom8_asana.cache.integration.mutation_invalidator import *
# This means autom8_asana.cache.mutation_invalidator.MutationInvalidator IS
# autom8_asana.cache.integration.mutation_invalidator.MutationInvalidator
```

However, if code does `import autom8_asana.cache.integration.mutation_invalidator` and a test patches `autom8_asana.cache.mutation_invalidator.MutationInvalidator`, the patch only affects the shim namespace, not the canonical namespace. This is why **intra-cache imports must be updated to canonical paths** (Section 5.2) -- so production code and test patches resolve through the same module.

---

## 11. Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | All files in cache/ are in a subdirectory (models/, policies/, providers/, integration/) or are shims | `ls -1 src/autom8_asana/cache/*.py` shows only `__init__.py` + shim files |
| 2 | Full test suite passes with zero test file modifications | `pytest tests/ -x` exit code 0 |
| 3 | All 80+ external import sites work without changes | Import smoke test passes |
| 4 | Canonical imports work | `from autom8_asana.cache.models.entry import CacheEntry` succeeds |
| 5 | Shim imports work | `from autom8_asana.cache.entry import CacheEntry` succeeds |
| 6 | Root package imports work | `from autom8_asana.cache import CacheEntry` succeeds |
| 7 | No circular imports | `python -c "import autom8_asana.cache"` succeeds without ImportError |
| 8 | Layer rules documented | Each subdirectory `__init__.py` contains layer rule comment |
| 9 | Git history preserved | `git log --follow cache/models/entry.py` shows history from before the move |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-module-reorganization.md` | Yes (this file) |
