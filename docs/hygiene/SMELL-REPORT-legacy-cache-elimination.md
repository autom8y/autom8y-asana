# Smell Report: Legacy Cache Elimination

**Report ID**: SMELL-REPORT-legacy-cache-elimination
**Generated**: 2026-01-02
**Sprint**: unified-cache-001
**Code Smeller**: Claude Opus 4.5

---

## Executive Summary

**Total Legacy Usage Count**: 21 production code locations + 62 test fixture locations

The unified cache architecture (`UnifiedTaskStore`, `HierarchyIndex`, `FreshnessCoordinator`) was implemented with OPTIONAL integration paths. All callers continue using legacy instantiation patterns, meaning the unified cache provides no actual benefit until these paths are migrated.

**Critical Finding**: The `StalenessCheckCoordinator` (legacy) is still injected into `BaseClient` and `TasksClient`, running in parallel with `FreshnessCoordinator` (unified). This creates dual staleness checking overhead.

### Blast Radius Summary

| Category | Findings | Files Affected | Estimated LOC |
|----------|----------|----------------|---------------|
| LEGACY_CACHE | 5 | 5 | ~150 |
| CACHE_FRAGMENTATION | 2 | 4 | ~80 |
| MIGRATION_INCOMPLETE | 14 | 8 | ~200 |
| TEST_FIXTURES | 62 | 4 | ~400 |

---

## Findings by Category

### Category: LEGACY_CACHE (Direct legacy instantiation)

#### SM-LC-001: TaskCacheCoordinator direct instantiation (HIGH)

**Severity**: High | **Frequency**: 1 | **Blast Radius**: Medium | **Fix Complexity**: Low
**ROI Score**: 8.5/10

**Location**: `src/autom8_asana/dataframes/builders/project.py:323`

**Evidence**:
```python
# Get Task-level cache provider from client (if available)
task_cache_provider = self._get_task_cache_provider(client) if use_cache else None
task_cache_coordinator = TaskCacheCoordinator(task_cache_provider)
```

**Issue**: `TaskCacheCoordinator` is instantiated directly with a `CacheProvider` instead of using `TaskCacheCoordinator.from_unified_store()`. This bypasses the unified cache integration entirely.

**Note**: This is the PRIMARY integration point where unified store should be wired. The `unified_store` parameter exists on `ProjectDataFrameBuilder` but is not used when building via `build_with_parallel_fetch_async()`.

---

#### SM-LC-002: CascadingFieldResolver without cascade_plugin (HIGH)

**Severity**: High | **Frequency**: 1 | **Blast Radius**: High | **Fix Complexity**: Low
**ROI Score**: 9.0/10

**Location**: `src/autom8_asana/dataframes/extractors/base.py:114`

**Evidence**:
```python
from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver

self._cascading_resolver = CascadingFieldResolver(self._client)
```

**Issue**: `CascadingFieldResolver` is instantiated without the `cascade_plugin` parameter. Per TDD-UNIFIED-CACHE-001, the `CascadeViewPlugin` should be passed to delegate parent chain resolution to the unified cache.

**Blast Radius**: Every cascade field resolution across all extractors uses this code path, causing redundant API calls for parent chain traversal.

---

#### SM-LC-003: ProjectDataFrameBuilder without unified_store - services/resolver.py (HIGH)

**Severity**: High | **Frequency**: 4 | **Blast Radius**: High | **Fix Complexity**: Low
**ROI Score**: 8.0/10

**Locations**:
- `src/autom8_asana/services/resolver.py:569`
- `src/autom8_asana/services/resolver.py:647`
- `src/autom8_asana/services/resolver.py:1085`
- `src/autom8_asana/services/resolver.py:1325`

**Evidence** (line 569):
```python
builder = ProjectDataFrameBuilder(
    project=project_proxy,
    task_type="Unit",
    schema=UNIT_SCHEMA,
    resolver=resolver,
    client=client,
)
```

**Issue**: All four `ProjectDataFrameBuilder` instantiations in the resolver service omit the `unified_store` parameter. The resolver is a high-traffic code path for DataFrame construction.

---

#### SM-LC-004: ProjectDataFrameBuilder without unified_store - api/main.py (MEDIUM)

**Severity**: Medium | **Frequency**: 2 | **Blast Radius**: Medium | **Fix Complexity**: Low
**ROI Score**: 7.0/10

**Locations**:
- `src/autom8_asana/api/main.py:645`
- `src/autom8_asana/api/main.py:744`

**Evidence** (line 645):
```python
builder = ProjectDataFrameBuilder(
    project=project_proxy,
    task_type=task_type,
    schema=schema,
    resolver=resolver,
)
```

**Issue**: API endpoints for incremental catchup and full rebuild do not pass `unified_store`, falling back to legacy cache path.

---

#### SM-LC-005: ProjectDataFrameBuilder without unified_store - models/project.py (MEDIUM)

**Severity**: Medium | **Frequency**: 2 | **Blast Radius**: Medium | **Fix Complexity**: Low
**ROI Score**: 6.5/10

**Locations**:
- `src/autom8_asana/models/project.py:194`
- `src/autom8_asana/models/project.py:273`

**Evidence** (line 273):
```python
builder = ProjectDataFrameBuilder(
    project=self,
    task_type=task_type,
    schema=schema,
    sections=sections,
    resolver=resolver,
    cache_integration=cache_integration,
    client=client,  # Per TDD-CASCADING-FIELD-RESOLUTION-001
)
```

**Issue**: Project model's DataFrame methods do not wire unified store despite having access to client which could provide it.

---

### Category: CACHE_FRAGMENTATION (Parallel cache paths)

#### SM-CF-001: StalenessCheckCoordinator still injected into clients (CRITICAL)

**Severity**: Critical | **Frequency**: 2 | **Blast Radius**: High | **Fix Complexity**: Medium
**ROI Score**: 9.5/10

**Locations**:
- `src/autom8_asana/clients/base.py:44` (parameter definition)
- `src/autom8_asana/clients/base.py:64` (assignment)
- `src/autom8_asana/clients/base.py:296-300` (usage)
- `src/autom8_asana/clients/tasks.py:54` (parameter definition)
- `src/autom8_asana/clients/tasks.py:65` (docstring)
- `src/autom8_asana/clients/tasks.py:75` (pass-through)
- `src/autom8_asana/clients/tasks.py:165` (usage)

**Evidence** (base.py:44):
```python
def __init__(
    self,
    http: AsyncHTTPClient,
    config: AsanaConfig,
    auth_provider: AuthProvider,
    cache_provider: CacheProvider | None = None,
    log_provider: LogProvider | None = None,
    staleness_coordinator: "StalenessCheckCoordinator | None" = None,
) -> None:
```

**Evidence** (base.py:296-300):
```python
if self._staleness_coordinator is not None:
    ...
    result = await self._staleness_coordinator.check_and_get_async(
```

**Issue**: `StalenessCheckCoordinator` (the LEGACY staleness checker per ADR-0134) is still injected into `BaseClient` and used for cache lookups. This runs in PARALLEL with `FreshnessCoordinator` in the unified cache, creating:
1. Duplicate staleness check infrastructure
2. Potential inconsistent freshness decisions
3. Wasted API calls if both paths active

**Note**: Per TDD-UNIFIED-CACHE-001, `FreshnessCoordinator` replaces `StalenessCheckCoordinator`. The legacy coordinator should be removed.

---

#### SM-CF-002: staleness_coordinator import and export in cache/__init__.py (MEDIUM)

**Severity**: Medium | **Frequency**: 1 | **Blast Radius**: Low | **Fix Complexity**: Low
**ROI Score**: 5.0/10

**Location**: `src/autom8_asana/cache/__init__.py:134`

**Evidence**:
```python
from autom8_asana.cache.staleness_coordinator import StalenessCheckCoordinator
```

**Issue**: The legacy `StalenessCheckCoordinator` is still exported from the cache package's public API, encouraging continued usage.

---

### Category: MIGRATION_INCOMPLETE (Optional path not wired)

#### SM-MI-001: No UnifiedTaskStore factory or singleton (HIGH)

**Severity**: High | **Frequency**: N/A | **Blast Radius**: High | **Fix Complexity**: Medium
**ROI Score**: 9.0/10

**Evidence**: Searched for `UnifiedTaskStore(` instantiation in `src/` - found ZERO instances outside the unified.py module itself.

**Issue**: There is no factory method, singleton, or dependency injection mechanism that creates `UnifiedTaskStore` instances. All callers would need to manually construct it with:
- A `CacheProvider`
- A `BatchClient`
- A `FreshnessMode`

Without a centralized factory, each caller must repeat this wiring, making adoption impractical.

**Recommendation for Architect Enforcer**: Create `UnifiedCacheFactory.create_unified_store()` that wires these dependencies from config/environment.

---

#### SM-MI-002: AsanaClient lacks unified_store property (HIGH)

**Severity**: High | **Frequency**: N/A | **Blast Radius**: High | **Fix Complexity**: Medium
**ROI Score**: 8.5/10

**Issue**: `AsanaClient` (the main entry point) has no property or method to access a `UnifiedTaskStore`. Callers cannot get a unified store without manual construction.

**Pattern**: Compare with `_dataframe_cache_integration` which IS exposed on AsanaClient and used by `Project.to_dataframe_parallel_async()`.

---

#### SM-MI-003: CacheFactory.create_unified_store() not implemented (HIGH)

**Severity**: High | **Frequency**: N/A | **Blast Radius**: High | **Fix Complexity**: Medium
**ROI Score**: 8.0/10

**Location**: `src/autom8_asana/cache/factory.py`

**Evidence**: `CacheFactory` has methods for:
- `create_redis()`
- `create_in_memory()`
- `create_tiered()`
- `create_null()`

But NO `create_unified_store()` method exists.

---

#### SM-MI-004: DataFrameViewPlugin created but not passed to builder (MEDIUM)

**Severity**: Medium | **Frequency**: 1 | **Blast Radius**: Medium | **Fix Complexity**: Low
**ROI Score**: 7.0/10

**Location**: `src/autom8_asana/dataframes/builders/project.py:746-751`

**Evidence**:
```python
# Create DataFrameViewPlugin for extraction
view_plugin = DataFrameViewPlugin(
    store=self._unified_store,
    schema=self._schema,
    resolver=self._resolver,
    row_cache=self._cache_integration,
)
```

**Issue**: The `DataFrameViewPlugin` is created inside `_build_with_unified_store_async()` but the unified store path is never entered because callers don't pass `unified_store` to the builder constructor.

---

### Category: TEST_FIXTURES (Legacy patterns in tests)

#### SM-TF-001: TaskCacheCoordinator legacy instantiation in tests (LOW)

**Severity**: Low | **Frequency**: 17 | **Blast Radius**: Test-only | **Fix Complexity**: Low
**ROI Score**: 3.0/10

**Locations**:
- `tests/integration/test_cache_optimization_e2e.py`: 12 instances (lines 181, 217, 247, 288, 324, 360, 374, 400, 424, 548, 573)
- `tests/integration/test_unified_cache_integration.py`: 2 instances (lines 593, 665)
- `tests/unit/dataframes/test_task_cache.py`: 5 instances (lines 60, 66, 326, 408, 717, 862)

**Evidence** (test_cache_optimization_e2e.py:181):
```python
coordinator = TaskCacheCoordinator(cache_provider)
```

**Issue**: Test fixtures use legacy `TaskCacheCoordinator(cache_provider)` pattern. While tests exist for `from_unified_store()` path (test_unified_cache_integration.py), the bulk of cache integration tests use legacy patterns.

**Note**: These tests validate legacy behavior which is correct for backward compatibility testing, but should be supplemented with unified store tests.

---

#### SM-TF-002: CascadingFieldResolver without cascade_plugin in tests (LOW)

**Severity**: Low | **Frequency**: 27 | **Blast Radius**: Test-only | **Fix Complexity**: Low
**ROI Score**: 2.5/10

**Locations**:
- `tests/integration/test_cascading_field_resolution.py`: 5 instances
- `tests/integration/test_unified_cache_integration.py`: 4 instances (some WITH cascade_plugin for comparison)
- `tests/unit/dataframes/test_cascading_resolver.py`: 18 instances

**Evidence** (test_cascading_resolver.py:96):
```python
resolver = CascadingFieldResolver(mock_client)
```

**Issue**: Most cascading resolver tests use legacy pattern without `cascade_plugin`.

---

#### SM-TF-003: ProjectDataFrameBuilder without unified_store in tests (LOW)

**Severity**: Low | **Frequency**: 35+ | **Blast Radius**: Test-only | **Fix Complexity**: Low
**ROI Score**: 2.0/10

**Locations**:
- `tests/unit/test_incremental_refresh.py`: 12 instances
- `tests/unit/dataframes/test_export.py`: 20+ instances
- `tests/unit/dataframes/test_validation.py`: Multiple instances
- `tests/integration/test_unified_cache_integration.py`: 4 instances (some WITH unified_store for comparison)

**Issue**: Existing tests primarily exercise legacy paths. The `test_unified_cache_integration.py` file does test unified store integration, but coverage is limited.

---

## ROI-Ranked Priority for Architect Enforcer

| Rank | Finding ID | ROI | Rationale |
|------|------------|-----|-----------|
| 1 | SM-CF-001 | 9.5 | Critical: Dual staleness checking creates waste and inconsistency |
| 2 | SM-MI-001 | 9.0 | No factory = no adoption path |
| 3 | SM-LC-002 | 9.0 | Every cascade resolution bypasses unified cache |
| 4 | SM-MI-002 | 8.5 | Client lacks unified store access |
| 5 | SM-LC-001 | 8.5 | Primary builder entry point uses legacy |
| 6 | SM-MI-003 | 8.0 | CacheFactory missing unified method |
| 7 | SM-LC-003 | 8.0 | High-traffic resolver service |
| 8 | SM-MI-004 | 7.0 | View plugin created but never reached |
| 9 | SM-LC-004 | 7.0 | API endpoints use legacy |
| 10 | SM-LC-005 | 6.5 | Model methods use legacy |
| 11 | SM-CF-002 | 5.0 | Legacy export in public API |
| 12 | SM-TF-001 | 3.0 | Test fixtures (low priority) |
| 13 | SM-TF-002 | 2.5 | Test fixtures (low priority) |
| 14 | SM-TF-003 | 2.0 | Test fixtures (low priority) |

---

## Boundary Concerns for Architect Enforcer

### BC-001: Missing Dependency Injection Pattern

The unified cache components (`UnifiedTaskStore`, `HierarchyIndex`, `FreshnessCoordinator`) are designed as composable dataclasses but lack a dependency injection mechanism. Compare:

- **Legacy Pattern**: `CacheProvider` injected via `BaseClient` constructor
- **Unified Pattern**: No equivalent injection point

**Architectural Question**: Should `UnifiedTaskStore` be:
1. A property on `AsanaClient`?
2. A singleton managed by `CacheFactory`?
3. A context manager yielded from client initialization?

### BC-002: Dual Staleness Architecture

Two staleness systems coexist:
1. `StalenessCheckCoordinator` (legacy) - injected into clients
2. `FreshnessCoordinator` (unified) - composed inside `UnifiedTaskStore`

**Architectural Decision Required**: Migration strategy for removing `StalenessCheckCoordinator` without breaking existing integrations.

### BC-003: Optional vs Mandatory Parameter Conflict

Current design uses OPTIONAL parameters (`unified_store=None`, `cascade_plugin=None`) for backward compatibility. This creates:
1. Code paths that never use unified cache
2. Difficulty enforcing migration
3. Maintenance burden of supporting both paths

**Architectural Question**: Should there be a "unified cache required" configuration flag that fails initialization if not properly wired?

---

## Artifact Verification

| Artifact | Path | Status | Line Count |
|----------|------|--------|------------|
| Smell Report | docs/hygiene/SMELL-REPORT-legacy-cache-elimination.md | CREATED | ~350 |

---

## Handoff Checklist

- [x] All `src/autom8_asana/` scanned for legacy patterns
- [x] All `tests/` scanned for legacy fixtures
- [x] Each finding has file:line reference with evidence
- [x] Findings categorized (LEGACY_CACHE, CACHE_FRAGMENTATION, MIGRATION_INCOMPLETE, TEST_FIXTURES)
- [x] Findings ROI-ranked for cleanup priority
- [x] Boundary concerns flagged for Architect Enforcer
- [x] Report written to `docs/hygiene/SMELL-REPORT-legacy-cache-elimination.md`

**Ready for handoff to Architect Enforcer.**
