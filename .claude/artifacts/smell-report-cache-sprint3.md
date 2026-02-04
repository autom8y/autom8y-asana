# Smell Report: Cache Architecture Landscape -- Sprint 3 Scoping

**Agent**: code-smeller
**Date**: 2026-02-04
**Scope**: Boy Scout Canary Pass -- post-refactoring assessment after Sprint 1 (RF-L01 to RF-L11) and Sprint 2 (RF-L12 to RF-L15)
**Finding Prefix**: SM-S3-
**Files Scanned**: 28

---

## Executive Summary

After two sprint cycles of hygiene work (15 refactoring commits), the cache architecture landscape is substantially cleaner. Sprint 1 eliminated datetime parsing duplication (RF-L05), schema version duplication (RF-L08), query engine copy-paste (RF-L08/RF-L09), entity type drift (RF-L06), and several complexity hotspots. Sprint 2 tackled the `_ResumeResult` decomposition (RF-L12), FreshnessInfo typed attributes (RF-L13), DegradedModeMixin extraction (RF-L14), and structured logging migration (RF-L15).

No canary bugs (regression-level defects introduced by refactoring) were detected. However, the refactoring has exposed **3 newly visible smells**, **2 incomplete extraction gaps**, and **10 of the 15 deferred items remain actionable** (5 have been partially addressed or reduced in severity).

The highest-ROI items for Sprint 3 are:

1. **SM-S3-001**: Private attribute boundary violations in progressive.py (canary-adjacent, HIGH)
2. **SM-S3-003**: DegradedModeMixin not adopted by memory backend (incomplete extraction, MEDIUM)
3. **SM-L009 re-assessment**: SectionPersistence encapsulation (deferred, HIGH -- unchanged)
4. **SM-L008 re-assessment**: `_fetch_and_persist_section` still 230+ lines (deferred, MEDIUM -- unchanged)

---

## Section A: Canary Findings

No true canary bugs (regressions introduced by refactoring) were found. The refactored code is consistent and the extractions are correctly wired. This section reports **canary-adjacent findings** -- issues that became more visible or more important due to the refactoring.

### SM-S3-001: Private attribute boundary violations amplified by RF-L12 decomposition (HIGH)

**Category**: Encapsulation Violation
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:807-813` (`_write_checkpoint`)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:881-896` (`_update_checkpoint_metadata`)

**Evidence**: After RF-L12 decomposed `build_progressive_async` into `_ResumeResult`, the checkpoint methods became more prominent as standalone units. They access private internals of `SectionPersistence`:
- `self._persistence._make_section_key` (private method)
- `self._persistence._s3_client.put_object_async` (private attribute chain)
- `self._persistence._get_manifest_lock` (private method)
- `self._persistence._manifest_cache` (private attribute)
- `self._persistence._save_manifest_async` (private method)

This was already flagged as deferred SM-L009 but the RF-L12 decomposition makes the violation more visible: `_write_checkpoint` and `_update_checkpoint_metadata` are now clearly separable methods that should be delegating to public SectionPersistence APIs rather than reaching into internals.

**Blast Radius**: 2 methods in progressive.py, 1 class boundary (SectionPersistence)
**Fix Complexity**: Medium (add public methods to SectionPersistence for checkpoint write + manifest update)
**ROI Score**: 7.5/10
**Relationship**: Supersedes deferred SM-L009

---

### SM-S3-002: SUPPORTED_ENTITY_TYPES hardcoded fallback constant in resolver.py (LOW)

**Category**: Dead Code / Drift Risk
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:257`

**Evidence**: After RF-L06 consolidated entity types into `core/entity_types.py`, the resolver route still maintains its own hardcoded `SUPPORTED_ENTITY_TYPES = {"unit", "business", "offer", "contact"}` as a fallback for `_get_supported_entity_types()`. The comment says "DEPRECATED: Use get_resolvable_entities() instead (TASK-004)" but the constant remains and diverges from `core/entity_types.ENTITY_TYPES` which includes `"asset_edit"` (5 items vs 4).

The `_get_supported_entity_types()` function at line 260-305 falls back to this stale constant when dynamic discovery fails. This creates a subtle inconsistency where a discovery failure would hide `asset_edit` from the resolver.

**Blast Radius**: 1 file, 1 fallback path
**Fix Complexity**: Low (replace with `set(ENTITY_TYPES)` from core, or remove fallback entirely)
**ROI Score**: 4.0/10

---

## Section B: Newly Visible Smells

These smells existed before but became more apparent due to the cleaner organization post-refactoring.

### SM-S3-003: DegradedModeMixin not adopted by EnhancedInMemoryCacheProvider (MEDIUM)

**Category**: Incomplete Pattern Adoption
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py:1-433`

**Evidence**: RF-L14 extracted `DegradedModeMixin` into `cache/errors.py` and wired it into `RedisCacheProvider`, `S3CacheProvider`, and `AsyncS3Client`. However, `EnhancedInMemoryCacheProvider` does not use the mixin. While a memory backend is unlikely to have connection failures, it does have its own degraded states:
- Line 145-159: `_evict_if_needed` silently drops entries when memory is full
- Line 287-304: `get_batch` is sequential with no error aggregation

The inconsistency means that if memory backend is swapped in (e.g., testing, local dev), monitoring code checking for `DegradedModeMixin` attributes would fail with `AttributeError`.

**Blast Radius**: 1 file, protocol inconsistency across 4 backends
**Fix Complexity**: Low (add mixin with no-op degraded behavior, or document as intentional)
**ROI Score**: 5.5/10

---

### SM-S3-004: DEFAULT_ENTITY_TTLS in config.py includes entity types not in ENTITY_TYPES (LOW)

**Category**: Naming / Drift
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py`

**Evidence**: After RF-L06 established `core/entity_types.py` as the canonical source, `config.py` still defines `DEFAULT_ENTITY_TTLS` with entries like `"process"`, `"address"`, and `"hours"` that do not appear in `ENTITY_TYPES` or `ENTITY_TYPES_WITH_DERIVATIVES`. These may be valid extended entity types, but the discrepancy raises questions about whether the TTL config and the entity type registry are in sync.

**Blast Radius**: Configuration drift, no runtime failure
**Fix Complexity**: Low (audit and reconcile, or document the relationship)
**ROI Score**: 3.0/10

---

### SM-S3-005: Inline import in resolver.py resolve_entities endpoint (LOW)

**Category**: Import Hygiene
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:498-499` (AsanaClient, BotPATError)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:649` (SchemaRegistry)

**Evidence**: Two endpoint functions use inline imports with comments about avoiding circular imports. This is a common pattern but post-refactoring these circular dependencies may have been resolved. The `SchemaRegistry` import in `get_entity_schema` and the `AsanaClient`/`get_bot_pat` imports in `resolve_entities` are both deferred unnecessarily if the circular dependency no longer exists.

**Blast Radius**: 2 endpoints, minor startup performance
**Fix Complexity**: Low (test moving imports to top-level)
**ROI Score**: 2.5/10

---

## Section C: Incomplete Extraction Findings

### SM-S3-006: clear_all_tasks uses getattr duck-typing instead of protocol method (MEDIUM)

**Category**: Incomplete Abstraction
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:478-493`

**Evidence**: `TieredCacheProvider.clear_all_tasks()` uses `getattr(self._hot, "clear_all_tasks", None)` to check if the underlying provider supports the method. This was already deferred as SM-L015. After RF-L14 established `DegradedModeMixin` as a pattern for shared behavior across backends, `clear_all_tasks` is now the most prominent method that bypasses the `CacheProvider` protocol.

The `CacheProvider` protocol (in `protocols/cache.py`) does not include `clear_all_tasks`, forcing the `getattr` pattern. All three concrete backends (Redis, S3, Memory) implement `clear_all_tasks`, so the protocol gap is purely definitional.

**Blast Radius**: 1 method in tiered.py, protocol definition gap
**Fix Complexity**: Low (add `clear_all_tasks` to `CacheProvider` protocol)
**ROI Score**: 6.0/10
**Relationship**: Supersedes deferred SM-L015

---

### SM-S3-007: warm() returns placeholder across all three backends (MEDIUM)

**Category**: Incomplete Implementation
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:608-631`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:636-659`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py:305-330`

**Evidence**: All three backends have `warm()` methods that return `WarmResult(warmed=0, failed=0, skipped=len(gids))`. These are placeholders that silently skip all warming. `TieredCacheProvider.warm()` delegates to `self._hot.warm()` which returns the placeholder result. Any caller expecting actual warming gets no-op behavior with no indication it is a stub.

This was deferred as SM-L032. After RF-L14 cleaned up the backends, these stubs are now the most prominent incomplete implementations remaining.

**Blast Radius**: 3 files, any warm() caller gets silent no-op
**Fix Complexity**: Medium (requires understanding what warming should do per backend)
**ROI Score**: 5.0/10
**Relationship**: Supersedes deferred SM-L032

---

## Section D: Deferred Item Re-assessment

### SM-L008: `_fetch_and_persist_section` complexity (MEDIUM -- UNCHANGED)

**Original**: Method too long (~230 lines, cyclomatic complexity ~15)
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:523-770`
**Status**: Still present at ~247 lines. RF-L12 decomposed `build_progressive_async` but did not touch this method. The method handles API fetching, DataFrame construction, S3 persistence, checkpoint writing, and error handling in a single flow.
**Sprint 3 Recommendation**: Candidate for decomposition. Could extract: (a) API fetch + pagination, (b) DataFrame construction, (c) persistence + checkpoint. Medium fix complexity.
**Updated ROI**: 6.0/10

---

### SM-L009: SectionPersistence private attribute access (HIGH -- SUBSUMED by SM-S3-001)

**Original**: progressive.py reaches into SectionPersistence internals
**Status**: Subsumed by SM-S3-001 above. The RF-L12 decomposition made this more visible. No additional action needed beyond SM-S3-001.

---

### SM-L010: DataFrameCache `_check_freshness_and_serve` parameter count (MEDIUM -- REDUCED)

**Original**: Method has 7+ parameters
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:357-365`
**Status**: RF-L13 introduced `FreshnessInfo` dataclass which reduced the side-channel complexity. The method still has 7 parameters but the overall readability has improved because callers no longer need `getattr` to access freshness state. The parameter count alone is less concerning now.
**Updated ROI**: 3.5/10 (reduced from original)

---

### SM-L011: `_swr_build_callback` coupling (LOW -- ADDRESSED)

**Original**: Tightly coupled callback pattern
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py`
**Status**: RF-L09 extracted `_swr_build_callback` as a module-level function, reducing the coupling. The pattern is now cleaner though still present. Consider this substantially addressed.
**Updated ROI**: 2.0/10

---

### SM-L015: getattr duck-typing for clear_all_tasks (MEDIUM -- SUBSUMED by SM-S3-006)

**Status**: Subsumed by SM-S3-006 above with updated context from RF-L14.

---

### SM-L016: S3 sequential batch operations (MEDIUM -- UNCHANGED)

**Original**: `get_batch` and `set_batch` in S3 backend are sequential
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:582-611` (get_batch)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:613-634` (set_batch)
**Status**: Still sequential loop-based. RF-L14 cleaned up the error handling but did not parallelize the batch operations.
**Updated ROI**: 4.5/10

---

### SM-L018: Mixed structured/unstructured logging (LOW -- ADDRESSED)

**Original**: Mix of f-string and structured `extra={}` logging
**Status**: RF-L15 migrated structured logging across tiered.py and other cache files. Spot-checking confirms `logger.info/warning/error` calls now consistently use `extra={}` dict pattern in the refactored files. Consider this addressed.
**Updated ROI**: 1.0/10

---

### SM-L020: DataFrameCache method complexity (MEDIUM -- REDUCED)

**Original**: Several methods in dataframe_cache.py have high complexity
**Status**: RF-L13 reduced complexity by introducing `FreshnessInfo` and `FreshnessStatus` as typed return values, eliminating `getattr`-based side channels. The overall file is still 884 lines but the individual method complexity has been reduced.
**Updated ROI**: 3.5/10

---

### SM-L021: UnifiedTaskStore file size (LOW -- UNCHANGED)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` (902 lines)
**Status**: Unchanged. The file was not in scope for Sprint 1 or 2 refactoring. It remains a large module but is well-organized with clear method boundaries.
**Updated ROI**: 2.5/10

---

### SM-L025: Memory backend get_batch non-atomic (LOW -- UNCHANGED)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py:287-304`
**Status**: Still sequential. This is a test/dev backend so the practical impact is low.
**Updated ROI**: 1.5/10

---

### SM-L026: Duplicate wrap_flat_array validators in query models (MEDIUM -- UNCHANGED)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py`
**Status**: `RowsRequest.where`, `AggregateRequest.where`, and `AggregateRequest.having` each have their own `wrap_flat_array` field_validator with identical logic. This was not addressed in Sprint 1 or 2.
**Updated ROI**: 5.0/10

---

### SM-L029: Hierarchy warmer field list maintenance (LOW -- UNCHANGED)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py`
**Status**: `_HIERARCHY_OPT_FIELDS` is a hardcoded list. Not addressed. Low priority.
**Updated ROI**: 2.0/10

---

### SM-L030: @dataframe_cache decorator assumes resolve() signature (LOW -- UNCHANGED)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py`
**Status**: The decorator still assumes the wrapped function has a `resolve()` method signature. Not addressed. Low practical impact since only used by resolution strategies.
**Updated ROI**: 2.0/10

---

### SM-L031: Inline os.environ.get for SECTION_FRESHNESS_PROBE (LOW -- UNCHANGED)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:257`
**Status**: Still uses `os.environ.get("SECTION_FRESHNESS_PROBE", "1")` inline rather than going through config.py. Minor but inconsistent with how other feature flags are managed.
**Updated ROI**: 2.0/10

---

### SM-L032: warm() placeholder implementations (MEDIUM -- SUBSUMED by SM-S3-007)

**Status**: Subsumed by SM-S3-007 above with updated locations across all 3 backends.

---

## Priority Matrix: Sprint 3 Candidates

| Rank | ID | Category | Severity | ROI | Fix Complexity | Recommendation |
|------|----|----------|----------|-----|----------------|----------------|
| 1 | SM-S3-001 | Encapsulation | HIGH | 7.5 | Medium | Add public SectionPersistence APIs for checkpoint ops |
| 2 | SM-S3-006 | Protocol Gap | MEDIUM | 6.0 | Low | Add clear_all_tasks to CacheProvider protocol |
| 3 | SM-L008 | Complexity | MEDIUM | 6.0 | Medium | Decompose _fetch_and_persist_section into 3 phases |
| 4 | SM-S3-003 | Pattern Adoption | MEDIUM | 5.5 | Low | Add DegradedModeMixin to memory backend or document exclusion |
| 5 | SM-L026 | DRY Violation | MEDIUM | 5.0 | Low | Extract shared wrap_flat_array validator |
| 6 | SM-S3-007 | Incomplete Impl | MEDIUM | 5.0 | Medium | Implement or explicitly stub warm() with logging |
| 7 | SM-L016 | Performance | MEDIUM | 4.5 | Medium | Parallelize S3 batch operations |
| 8 | SM-S3-002 | Drift Risk | LOW | 4.0 | Low | Replace SUPPORTED_ENTITY_TYPES with core import |
| 9 | SM-L010 | Complexity | MEDIUM | 3.5 | Medium | Consider parameter object (lower priority post-RF-L13) |
| 10 | SM-S3-004 | Drift | LOW | 3.0 | Low | Reconcile config TTLs with entity_types |

Items below ROI 3.0 (SM-L021, SM-L025, SM-L029, SM-L030, SM-L031, SM-S3-005) are not recommended for Sprint 3.

**Addressed/Closed Items** (no action needed):
- SM-L011: Substantially addressed by RF-L09
- SM-L018: Addressed by RF-L15
- SM-L009: Subsumed by SM-S3-001
- SM-L015: Subsumed by SM-S3-006
- SM-L032: Subsumed by SM-S3-007

---

## Verification Attestation

| # | File | Read | Verified |
|---|------|------|----------|
| 1 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Yes | Yes |
| 2 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Yes | Yes |
| 3 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Yes | Yes |
| 4 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Yes | Yes |
| 5 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py` | Yes | Yes |
| 6 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Yes | Yes |
| 7 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Yes | Yes |
| 8 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py` | Yes | Yes |
| 9 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` | Yes | Yes |
| 10 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/errors.py` | Yes | Yes |
| 11 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/datetime_utils.py` | Yes | Yes |
| 12 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/schema.py` | Yes | Yes |
| 13 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_types.py` | Yes | Yes |
| 14 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py` | Yes | Yes |
| 15 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` | Yes | Yes |
| 16 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/coalescer.py` | Yes | Yes |
| 17 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/circuit_breaker.py` | Yes | Yes |
| 18 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py` | Yes | Yes |
| 19 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py` | Yes | Yes |
| 20 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes | Yes |
| 21 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/schema_providers.py` | Yes | Yes |
| 22 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py` | Yes | Yes |
| 23 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py` | Yes | Yes |
| 24 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py` | Yes | Yes |
| 25 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py` | Yes | Yes |
| 26 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Yes | Yes |
| 27 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py` | Yes | Yes |
| 28 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | Yes | Yes |

All 28 files in scope were read via the Read tool. No findings are based on assumptions or prior knowledge alone. Each finding includes file path and line number references verified against actual file contents.
