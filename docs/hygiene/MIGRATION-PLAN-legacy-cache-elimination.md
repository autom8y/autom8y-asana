# Migration Plan: Legacy Cache Elimination

**Plan ID**: MIGRATION-PLAN-legacy-cache-elimination
**Generated**: 2026-01-02
**Sprint**: unified-cache-001
**Architect Enforcer**: Claude Opus 4.5

**Input Artifact**: `docs/hygiene/SMELL-REPORT-legacy-cache-elimination.md`
**Reference TDD**: `docs/architecture/TDD-UNIFIED-CACHE-001.md`

---

## Executive Summary

This migration plan eliminates 21 production code locations using legacy cache patterns by wiring the existing `UnifiedTaskStore` infrastructure into all callers. The unified cache architecture exists but remains OPTIONAL - all callers bypass it through direct instantiation of legacy components.

**Strategy**: Dependency injection via `CacheProviderFactory` and `AsanaClient` property exposure, followed by systematic caller migration and legacy removal.

**Risk Profile**: Medium - All changes preserve existing behavior while adding unified cache paths. Rollback points defined at each phase boundary.

---

## Architectural Assessment

### Root Cause Analysis

The unified cache components (`UnifiedTaskStore`, `HierarchyIndex`, `FreshnessCoordinator`) were implemented per TDD-UNIFIED-CACHE-001 but lack adoption because:

1. **No Factory Pattern**: Callers cannot easily construct `UnifiedTaskStore` with required dependencies (CacheProvider, BatchClient, FreshnessMode)
2. **No DI Mechanism**: `AsanaClient` lacks a `unified_store` property, so callers have no access point
3. **Optional Parameters**: All integration points use `unified_store=None` default, making bypass the path of least resistance
4. **Dual Staleness Infrastructure**: `StalenessCheckCoordinator` (legacy) runs in parallel with `FreshnessCoordinator` (unified), creating overhead

### Boundary Health Assessment

| Boundary | Current State | Target State | Risk |
|----------|---------------|--------------|------|
| `AsanaClient` -> Cache | Exposes `_cache_provider` only | Add `unified_store` property | Low |
| `CacheProviderFactory` -> Stores | Creates providers, not stores | Add `create_unified_store()` | Low |
| `BaseClient` -> Staleness | Injects `StalenessCheckCoordinator` | Remove legacy coordinator | Medium |
| `CascadingFieldResolver` -> Cache | Local `_parent_cache` dict | Delegate to `CascadeViewPlugin` | Medium |
| `ProjectDataFrameBuilder` -> Cache | Direct `TaskCacheCoordinator` | Use `unified_store` parameter | Low |

---

## Migration Phases

### Phase 1: Factory and DI Setup (Non-Breaking)

**Goal**: Establish infrastructure for callers to access unified store without manual construction.

**Addresses**: SM-MI-001, SM-MI-003, SM-MI-002

#### RF-001: Add `create_unified_store()` to CacheProviderFactory

**Before State**:
- `src/autom8_asana/cache/factory.py:22-211`: `CacheProviderFactory` has methods for `create_redis()`, `create_in_memory()`, `create_tiered()`, `create_null()` - NO unified store method

**After State**:
- `CacheProviderFactory.create_unified_store(config, batch_client)` method added
- Returns `UnifiedTaskStore` wired with appropriate `CacheProvider` and `FreshnessMode`
- Follows existing pattern of environment-aware selection

**Interface Contract**:
```python
@staticmethod
def create_unified_store(
    config: CacheConfig,
    batch_client: BatchClient | None = None,
    freshness_mode: FreshnessMode = FreshnessMode.EVENTUAL,
) -> UnifiedTaskStore:
    """Create unified task store with environment-aware provider selection.

    Per MIGRATION-PLAN-legacy-cache-elimination RF-001:
    Follows same detection chain as create() for provider selection.

    Args:
        config: CacheConfig with provider settings.
        batch_client: Optional BatchClient for freshness checks.
        freshness_mode: Default freshness mode.

    Returns:
        UnifiedTaskStore configured for the environment.
    """
```

**Invariants**:
- Must use same provider selection logic as existing `create()` method
- If caching disabled (`config.enabled=False`), returns store with `NullCacheProvider`
- No changes to existing `CacheProviderFactory` methods

**Verification**:
1. Run: `pytest tests/unit/cache/test_factory.py -v`
2. Verify new `test_create_unified_store_*` tests pass
3. Confirm existing factory tests unchanged

**Rollback**: Remove `create_unified_store()` method, no other changes required

---

#### RF-002: Add `unified_store` property to AsanaClient

**Before State**:
- `src/autom8_asana/client.py:84-983`: `AsanaClient` exposes `_cache_provider` and `cache_metrics` but no unified store
- Pattern exists: `_dataframe_cache_integration` is exposed for `Project.to_dataframe_parallel_async()`

**After State**:
- `AsanaClient.unified_store` property added (lazy-initialized like other clients)
- Uses `CacheProviderFactory.create_unified_store()` for construction
- Returns `UnifiedTaskStore | None` (None if caching disabled)

**Interface Contract**:
```python
@property
def unified_store(self) -> UnifiedTaskStore | None:
    """Access unified task store for cache operations.

    Per MIGRATION-PLAN-legacy-cache-elimination RF-002:
    Provides single source of truth for task caching.

    Thread-safe lazy initialization using double-checked locking.

    Returns:
        UnifiedTaskStore if caching enabled, None otherwise.

    Example:
        >>> if client.unified_store:
        ...     task = await client.unified_store.get_async("task-gid")
    """
```

**Invariants**:
- Thread-safe initialization (follow existing `_tasks_lock` pattern)
- Returns same instance on repeated calls
- Returns None if `_cache_provider` is `NullCacheProvider`
- Wires `self.batch` as `batch_client` parameter

**Verification**:
1. Run: `pytest tests/unit/test_client.py -v -k unified_store`
2. Verify `test_unified_store_lazy_init` passes
3. Verify `test_unified_store_none_when_cache_disabled` passes

**Rollback**: Remove `_unified_store` attribute, lock, and property

---

#### RF-003: Export `UnifiedTaskStore` from cache package

**Before State**:
- `src/autom8_asana/cache/__init__.py:137-207`: `__all__` does NOT include `UnifiedTaskStore`, `FreshnessMode`, `HierarchyIndex`

**After State**:
- `UnifiedTaskStore`, `FreshnessMode`, `HierarchyIndex` added to imports and `__all__`
- Public API for unified cache components established

**Interface Contract**:
```python
# Add to imports (after line 134)
from autom8_asana.cache.unified import UnifiedTaskStore
from autom8_asana.cache.freshness_coordinator import FreshnessMode
from autom8_asana.cache.hierarchy import HierarchyIndex

# Add to __all__ (unified cache section)
"UnifiedTaskStore",
"FreshnessMode",
"HierarchyIndex",
```

**Invariants**:
- No changes to existing exports
- All three classes importable from `autom8_asana.cache`

**Verification**:
1. Run: `python -c "from autom8_asana.cache import UnifiedTaskStore, FreshnessMode, HierarchyIndex"`
2. Verify no import errors

**Rollback**: Remove imports and `__all__` entries

---

### Phase 2: Client Wiring (Low Risk)

**Goal**: Wire unified store into primary callers without removing legacy paths.

**Addresses**: SM-LC-001, SM-LC-003, SM-LC-004, SM-LC-005, SM-MI-004

#### RF-004: Wire `unified_store` at `project.py:323` (TaskCacheCoordinator entry point)

**Before State**:
- `src/autom8_asana/dataframes/builders/project.py:320-325`:
```python
# Get Task-level cache provider from client (if available)
task_cache_provider = self._get_task_cache_provider(client) if use_cache else None
task_cache_coordinator = TaskCacheCoordinator(task_cache_provider)
```

**After State**:
```python
# Get Task-level cache coordinator
if self._unified_store is not None:
    task_cache_coordinator = TaskCacheCoordinator.from_unified_store(self._unified_store)
else:
    task_cache_provider = self._get_task_cache_provider(client) if use_cache else None
    task_cache_coordinator = TaskCacheCoordinator(task_cache_provider)
```

**Invariants**:
- If `unified_store` provided, uses unified path
- If `unified_store` is None, falls back to legacy path (preserves backward compatibility)
- `TaskCacheCoordinator.from_unified_store()` already exists per TDD-UNIFIED-CACHE-001

**Verification**:
1. Run: `pytest tests/unit/dataframes/test_project_builder.py -v`
2. Run: `pytest tests/integration/test_unified_cache_integration.py -v`
3. Verify both legacy and unified paths tested

**Rollback**: Remove conditional, restore direct `TaskCacheCoordinator(task_cache_provider)` call

---

#### RF-005: Wire `unified_store` at resolver service locations

**Before State**:
- `src/autom8_asana/services/resolver.py:569,647,1085,1325`: Four `ProjectDataFrameBuilder` instantiations without `unified_store`

**After State**:
- All four locations pass `unified_store=client.unified_store` if available
- Pattern:
```python
builder = ProjectDataFrameBuilder(
    project=project_proxy,
    task_type="Unit",
    schema=UNIT_SCHEMA,
    resolver=resolver,
    client=client,
    unified_store=client.unified_store,  # Added
)
```

**Invariants**:
- No change when `client.unified_store` is None
- Existing tests pass without modification
- `unified_store` parameter already exists on `ProjectDataFrameBuilder`

**Verification**:
1. Run: `pytest tests/unit/test_resolver_service.py -v`
2. Run: `pytest tests/integration/test_resolver_service.py -v` (if exists)
3. Grep for `ProjectDataFrameBuilder(` in resolver.py - all four should have `unified_store=`

**Rollback**: Remove `unified_store=client.unified_store` from all four locations

---

#### RF-006: Wire `unified_store` at API endpoint locations

**Before State**:
- `src/autom8_asana/api/main.py:645,744`: Two `ProjectDataFrameBuilder` instantiations without `unified_store`

**After State**:
- Both locations pass `unified_store` from request context or client
- Pattern mirrors resolver service changes

**Invariants**:
- API behavior unchanged when unified store unavailable
- Response format unchanged

**Verification**:
1. Run: `pytest tests/api/test_main.py -v`
2. Verify incremental catchup and full rebuild endpoints work

**Rollback**: Remove `unified_store=` parameter from both locations

---

#### RF-007: Wire `unified_store` at model locations

**Before State**:
- `src/autom8_asana/models/project.py:194,273`: Two `ProjectDataFrameBuilder` instantiations without `unified_store`

**After State**:
- Both locations pass `unified_store` from client if available
- Pattern:
```python
unified_store = client.unified_store if client else None
builder = ProjectDataFrameBuilder(
    project=self,
    task_type=task_type,
    schema=schema,
    sections=sections,
    resolver=resolver,
    cache_integration=cache_integration,
    client=client,
    unified_store=unified_store,  # Added
)
```

**Invariants**:
- No change when client not provided
- `Project.to_dataframe_parallel_async()` behavior unchanged

**Verification**:
1. Run: `pytest tests/unit/models/test_project.py -v`
2. Verify model DataFrame methods work with and without unified store

**Rollback**: Remove `unified_store=` parameter from both locations

---

### Phase 3: Cascade Integration (Medium Risk)

**Goal**: Wire `CascadeViewPlugin` into `CascadingFieldResolver` for unified parent chain resolution.

**Addresses**: SM-LC-002

#### RF-008: Wire `CascadeViewPlugin` at extractor base.py:114

**Before State**:
- `src/autom8_asana/dataframes/extractors/base.py:112-115`:
```python
from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver

self._cascading_resolver = CascadingFieldResolver(self._client)
```

**After State**:
```python
from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver

# Create cascade plugin if unified store available
cascade_plugin = None
if hasattr(self._client, 'unified_store') and self._client.unified_store:
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
    cascade_plugin = CascadeViewPlugin(store=self._client.unified_store)

self._cascading_resolver = CascadingFieldResolver(
    self._client,
    cascade_plugin=cascade_plugin,
)
```

**Invariants**:
- If `cascade_plugin` provided, `CascadingFieldResolver.resolve_async()` delegates to it
- If `cascade_plugin` is None, uses legacy `_parent_cache` path
- Parent chain values resolved identically in both paths
- `CascadeViewPlugin` already exists per TDD-UNIFIED-CACHE-001

**Verification**:
1. Run: `pytest tests/unit/dataframes/test_cascading_resolver.py -v`
2. Run: `pytest tests/integration/test_cascading_field_resolution.py -v`
3. Verify "Office Phone" resolved identically with/without unified cache

**Rollback**: Remove cascade_plugin construction, revert to `CascadingFieldResolver(self._client)`

---

### Phase 4: Legacy Removal (Breaking Changes)

**Goal**: Remove dual staleness infrastructure and legacy public exports.

**Addresses**: SM-CF-001, SM-CF-002

**PREREQUISITE**: Phases 1-3 complete and validated. All callers using unified paths.

#### RF-009: Remove `staleness_coordinator` parameter from BaseClient

**Before State**:
- `src/autom8_asana/clients/base.py:37-65`: `BaseClient.__init__` accepts `staleness_coordinator` parameter
- `src/autom8_asana/clients/base.py:296-326`: `_cache_get_with_staleness_async` uses `self._staleness_coordinator`

**After State**:
- `staleness_coordinator` parameter removed from `BaseClient.__init__`
- `self._staleness_coordinator` attribute removed
- `_cache_get_with_staleness_async` method removed (unified store handles staleness)

**Invariants**:
- All callers use unified store for staleness checks
- No `StalenessCheckCoordinator` instantiation in client code
- Cache lookup behavior unchanged (delegated to unified store)

**Migration Path for Callers**:
```python
# Before (legacy)
client = BaseClient(http, config, auth, cache, log, staleness_coordinator=coordinator)

# After (unified)
client = BaseClient(http, config, auth, cache, log)
# Staleness handled by AsanaClient.unified_store internally
```

**Verification**:
1. Run: `pytest tests/unit/clients/ -v`
2. Grep for `staleness_coordinator` - should return zero hits in src/
3. Verify `mypy src/autom8_asana/clients/` passes

**Rollback**: Restore parameter, attribute, and method (revert commit)

---

#### RF-010: Remove `staleness_coordinator` from TasksClient

**Before State**:
- `src/autom8_asana/clients/tasks.py:54`: `staleness_coordinator` parameter
- `src/autom8_asana/clients/tasks.py:65`: Docstring reference
- `src/autom8_asana/clients/tasks.py:75`: Pass-through to BaseClient
- `src/autom8_asana/clients/tasks.py:165`: Usage in cache lookup

**After State**:
- All `staleness_coordinator` references removed
- Cache lookup uses unified store (if available) or simple TTL check

**Invariants**:
- `TasksClient` signature simplified
- Staleness checks delegated to unified infrastructure

**Verification**:
1. Run: `pytest tests/unit/clients/test_tasks.py -v`
2. Grep for `staleness_coordinator` in tasks.py - zero hits

**Rollback**: Restore removed code (revert commit)

---

#### RF-011: Remove `StalenessCheckCoordinator` from cache public API

**Before State**:
- `src/autom8_asana/cache/__init__.py:134`: `from autom8_asana.cache.staleness_coordinator import StalenessCheckCoordinator`
- `src/autom8_asana/cache/__init__.py:200+`: `StalenessCheckCoordinator` in `__all__`

**After State**:
- Import removed
- Export removed from `__all__`
- Deprecation warning added to `staleness_coordinator.py` module docstring

**Invariants**:
- `from autom8_asana.cache import StalenessCheckCoordinator` raises `ImportError`
- Direct import `from autom8_asana.cache.staleness_coordinator import StalenessCheckCoordinator` still works (for migration period)
- Deprecation warning logged on direct import

**Verification**:
1. Run: `python -c "from autom8_asana.cache import StalenessCheckCoordinator"` - should fail
2. Run: `python -c "from autom8_asana.cache.staleness_coordinator import StalenessCheckCoordinator"` - should warn

**Rollback**: Restore import and export

---

## Before/After Contract Summary

| Component | Before | After |
|-----------|--------|-------|
| `CacheProviderFactory` | Creates providers only | Creates providers + unified store |
| `AsanaClient` | No unified store access | `unified_store` property |
| `cache/__init__.py` | Exports legacy coordinator | Exports unified components |
| `BaseClient` | Accepts `staleness_coordinator` | No staleness parameter |
| `TasksClient` | Passes staleness coordinator | Simplified signature |
| `ProjectDataFrameBuilder` | `unified_store` ignored | `unified_store` wired through |
| `CascadingFieldResolver` | Local `_parent_cache` | Delegates to `CascadeViewPlugin` |
| `BaseExtractor` | No plugin wiring | Creates `CascadeViewPlugin` from client |

---

## Risk Matrix

| Phase | Blast Radius | Failure Detection | Recovery Path | Rollback Cost |
|-------|--------------|-------------------|---------------|---------------|
| Phase 1 | Low (additive) | Unit tests | Remove new code | 5 min |
| Phase 2 | Low (additive) | Integration tests | Remove parameter passing | 10 min |
| Phase 3 | Medium (behavior) | Cascade field tests | Revert conditional | 10 min |
| Phase 4 | High (breaking) | All cache tests | Revert commits | 30 min |

### Phase-Level Rollback Points

1. **After Phase 1**: Git tag `unified-cache-phase-1-complete`
2. **After Phase 2**: Git tag `unified-cache-phase-2-complete`
3. **After Phase 3**: Git tag `unified-cache-phase-3-complete`
4. **After Phase 4**: No rollback tag (breaking change committed)

---

## Test Requirements for Janitor Execution

### Phase 1 Tests

```bash
# RF-001: Factory method
pytest tests/unit/cache/test_factory.py -v -k "unified"

# RF-002: Client property
pytest tests/unit/test_client.py -v -k "unified"

# RF-003: Exports
python -c "from autom8_asana.cache import UnifiedTaskStore, FreshnessMode, HierarchyIndex"
```

### Phase 2 Tests

```bash
# RF-004: Primary entry point
pytest tests/unit/dataframes/test_task_cache.py -v
pytest tests/integration/test_unified_cache_integration.py -v

# RF-005/006/007: Wiring locations
pytest tests/unit/dataframes/test_project_builder.py -v
pytest tests/api/test_routes_resolver.py -v
```

### Phase 3 Tests

```bash
# RF-008: Cascade integration
pytest tests/unit/dataframes/test_cascading_resolver.py -v
pytest tests/integration/test_cascading_field_resolution.py -v
```

### Phase 4 Tests

```bash
# RF-009/010: Legacy removal
pytest tests/unit/clients/ -v
mypy src/autom8_asana/clients/

# RF-011: Export removal
python -c "from autom8_asana.cache import StalenessCheckCoordinator" && exit 1 || echo "Pass: ImportError as expected"
```

### Full Regression

```bash
# After each phase
pytest tests/unit/ -v --tb=short
pytest tests/integration/ -v --tb=short
ruff check src/autom8_asana/
mypy src/autom8_asana/
```

---

## Janitor Notes

### Commit Conventions

- **Phase 1**: `feat(cache): add UnifiedTaskStore factory and client property`
- **Phase 2**: `feat(dataframes): wire unified_store to ProjectDataFrameBuilder callers`
- **Phase 3**: `feat(dataframes): integrate CascadeViewPlugin for parent chain resolution`
- **Phase 4**: `refactor(clients)!: remove legacy StalenessCheckCoordinator` (BREAKING)

### Critical Ordering

1. RF-001 MUST complete before RF-002 (client needs factory)
2. RF-002 MUST complete before RF-004/005/006/007 (callers need client property)
3. All Phase 2 MUST complete before Phase 3 (cascade needs unified store propagated)
4. Phase 3 MUST complete before Phase 4 (removal requires all paths migrated)

### Test Fixtures to Update (Deferred)

Per SM-TF-001/002/003: Test fixtures using legacy patterns (62 locations) are LOW priority.
Keep legacy tests for backward compatibility validation during migration.
New tests should use unified patterns.

---

## Boundary Concern Resolutions

### BC-001: Missing DI Pattern

**Resolution**: `UnifiedTaskStore` exposed as `AsanaClient.unified_store` property, following existing pattern for `_dataframe_cache_integration`. Factory method in `CacheProviderFactory` handles construction.

### BC-002: Dual Staleness Architecture

**Resolution**: Phase 4 removes `StalenessCheckCoordinator` from client layer. `FreshnessCoordinator` in unified store handles all staleness checks. Migration sequence ensures all callers use unified path before removal.

### BC-003: Optional Parameters

**Resolution**: NOT addressed in this migration. "Unified required" mode deferred to future initiative. This migration focuses on wiring, not enforcement.

---

## Artifact Verification

| Artifact | Path | Status |
|----------|------|--------|
| Migration Plan | `docs/hygiene/MIGRATION-PLAN-legacy-cache-elimination.md` | CREATED |
| Smell Report | `docs/hygiene/SMELL-REPORT-legacy-cache-elimination.md` | VERIFIED |
| TDD Reference | `docs/architecture/TDD-UNIFIED-CACHE-001.md` | VERIFIED |
| UnifiedTaskStore | `src/autom8_asana/cache/unified.py` | VERIFIED |
| HierarchyIndex | `src/autom8_asana/cache/hierarchy.py` | VERIFIED |
| FreshnessCoordinator | `src/autom8_asana/cache/freshness_coordinator.py` | VERIFIED |
| CascadeViewPlugin | `src/autom8_asana/dataframes/views/cascade_view.py` | VERIFIED |
| DataFrameViewPlugin | `src/autom8_asana/dataframes/views/dataframe_view.py` | VERIFIED |
| CacheProviderFactory | `src/autom8_asana/cache/factory.py` | VERIFIED |
| AsanaClient | `src/autom8_asana/client.py` | VERIFIED |
| BaseClient | `src/autom8_asana/clients/base.py` | VERIFIED |
| TasksClient | `src/autom8_asana/clients/tasks.py` | VERIFIED |
| ProjectDataFrameBuilder | `src/autom8_asana/dataframes/builders/project.py` | VERIFIED |
| CascadingFieldResolver | `src/autom8_asana/dataframes/resolver/cascading.py` | VERIFIED |
| BaseExtractor | `src/autom8_asana/dataframes/extractors/base.py` | VERIFIED |

---

## Handoff Checklist

- [x] Every smell addressed with specific refactoring task (RF-001 through RF-011)
- [x] Each refactoring has before/after contract documented
- [x] Invariants specified for each task
- [x] Verification criteria defined (test commands)
- [x] Refactorings sequenced with explicit dependencies
- [x] Rollback points identified between phases
- [x] Risk assessment complete for each phase
- [x] Boundary concerns from smell report addressed
- [x] Test fixtures deferred (documented rationale)
- [x] Commit conventions specified
- [x] Critical ordering documented

**Ready for handoff to Janitor.**

---

**End of Migration Plan**
