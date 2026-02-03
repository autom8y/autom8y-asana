# Smell Report: Cache Architecture Landscape

## Executive Summary

Assessment of 6 cache subsystems across 22 files (~5,800 lines). Found **32 findings** ranging from critical cross-subsystem coupling issues to low-priority naming inconsistencies. The most impactful patterns are:

1. **Hardcoded entity type lists** scattered across 6+ locations (config drift risk)
2. **Duplicated datetime parsing** logic in 3 files (identical Z-suffix handling)
3. **Duplicated degraded-mode/reconnection patterns** across Redis, S3, and AsyncS3 backends
4. **Inconsistent error handling** between DataFrameCache and UnifiedTaskStore subsystems
5. **Side-channel freshness propagation** expanding from DataFrameCache into QueryEngine via getattr

The codebase is generally well-structured with good documentation. Most smells are DRY violations and configuration sprawl rather than architectural defects.

---

## Findings

### SM-L001: Hardcoded entity type lists in 6+ locations (HIGH)

- **Severity**: HIGH
- **Category**: Config / DRY Violation
- **Subsystem**: Cross-cutting (1, 2, 3, 5, 6)
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:216` -- `["unit", "business", "offer", "contact", "asset_edit"]`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:554` -- same list repeated
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/schema_providers.py:122-128` -- `["unit", "contact", "offer", "business", "asset_edit", "asset_edit_holder"]`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:256` -- `{"unit", "business", "offer", "contact"}` (missing asset_edit)
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py:26` -- `{"unit", "business", "offer", "contact", "asset_edit"}`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py:83-99` -- hardcoded schema imports
- **Description**: Entity type lists are hardcoded independently in multiple modules. Adding a new entity type requires finding and updating all locations. The lists are already inconsistent -- `resolver.py` is missing "asset_edit", `schema_providers.py` includes "asset_edit_holder" that others lack.
- **Impact**: Adding a new entity type is error-prone. Existing inconsistencies prove the drift has already occurred.
- **Suggested Fix**: Define a single `ENTITY_TYPES` constant (or derive from SchemaRegistry) and import everywhere.
- **ROI**: 9/10 -- low fix complexity, high blast radius, prevents future bugs

### SM-L002: Duplicated datetime parsing with Z-suffix handling (MEDIUM)

- **Severity**: MEDIUM
- **Category**: DRY Violation
- **Subsystem**: 1, 3, 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py:845-871` -- `_parse_version()` method
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:900-930` -- `_parse_datetime()` method
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py:347-369` -- `_parse_datetime()` method
- **Description**: Three independent implementations of identical datetime parsing logic: strip "Z" suffix, replace with "+00:00", call `fromisoformat()`, handle missing tzinfo. The implementations are functionally identical, differing only in return type on failure (current time vs None).
- **Impact**: 3 locations to fix if parsing logic changes. Risk of subtle divergence.
- **Suggested Fix**: Extract to a shared utility (e.g., `autom8_asana.utils.datetime.parse_iso_datetime()`).
- **ROI**: 7/10 -- straightforward extraction, moderate blast radius

### SM-L003: Duplicated degraded-mode + reconnection pattern across backends (MEDIUM)

- **Severity**: MEDIUM
- **Category**: DRY Violation
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:127-141,168-205` -- `_degraded`, `_last_reconnect_attempt`, `_attempt_reconnect()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:136-154,201-217` -- identical pattern
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py:186-191,246-265` -- similar but slightly different degraded mode
- **Description**: Three backend classes independently implement the same degraded-mode state machine: `_degraded` bool, `_last_reconnect_attempt` float, reconnect interval check, `_attempt_reconnect()` method. Redis and S3 backends are nearly identical; AsyncS3Client uses a similar but slightly different approach (`_degraded_backoff` vs `_settings.reconnect_interval`).
- **Impact**: Three places to update if degraded-mode behavior changes. The AsyncS3Client already diverged (uses 60s hardcoded backoff instead of settings).
- **Suggested Fix**: Extract a `DegradedModeHandler` or mixin class.
- **ROI**: 6/10 -- moderate complexity extraction, good deduplication

### SM-L004: Duplicated error classification logic across backends (MEDIUM)

- **Severity**: MEDIUM
- **Category**: DRY Violation
- **Subsystem**: 2, 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:725-755` -- `_handle_redis_error()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:770-828` -- `_handle_s3_error()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py:586-680` -- `_is_not_found_error()`, `_is_retryable_error()`, `_handle_error()`
- **Description**: Each backend independently classifies errors into categories (connection, timeout, not-found, retryable). The base error types `(ConnectionError, TimeoutError, OSError)` appear identically in all three. S3 backends both check botocore error codes with duplicated `error.response.get("Error", {}).get("Code", "")` patterns.
- **Impact**: Error handling inconsistency already exists -- `async_s3.py` checks string patterns ("nosuchkey", "not found") while `s3.py` only checks error codes.
- **Suggested Fix**: Extract shared error classification into `cache/errors.py`.
- **ROI**: 6/10 -- moderate complexity, prevents inconsistent error handling

### SM-L005: Side-channel freshness propagation expanding via getattr (MEDIUM)

- **Severity**: MEDIUM
- **Category**: Coupling
- **Subsystem**: 1, 4
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:197-200` -- `_last_freshness` dict
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:259` -- `getattr(self.query_service, "_last_freshness_info", None)`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:409` -- same pattern in `execute_aggregate`
- **Description**: This is the cross-cutting expansion of the SM-004 pattern from the prior cycle. The `_last_freshness` side-channel in DataFrameCache is now consumed by QueryEngine via `getattr` on the query_service -- breaking encapsulation through two layers. QueryEngine reads a private attribute (`_last_freshness_info`) from `EntityQueryService` via `getattr`, which itself reads from DataFrameCache's `_last_freshness` dict via `get_freshness_info()`.
- **Impact**: Fragile coupling across 3 components. Any rename of the private attribute silently breaks freshness metadata in query responses (getattr returns None, freshness disappears from API response without error).
- **Suggested Fix**: Make freshness info an explicit return value (e.g., return `(df, freshness_info)` tuple from query_service) or use a typed context/result object.
- **ROI**: 7/10 -- moderate fix, high fragility risk

### SM-L006: put_batch_async method is 200+ lines with deep nesting (HIGH)

- **Severity**: HIGH
- **Category**: Complexity
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py:452-687` -- `put_batch_async()` (235 lines)
- **Description**: `UnifiedTaskStore.put_batch_async()` is a 235-line method with 5 levels of nesting, inline function definition (`_fetch_immediate_parent`), pacing logic, and three distinct responsibilities: (1) batch cache storage, (2) immediate parent fetching with pacing, (3) ancestor warming. The inline function captures the outer scope's `tasks_client` and `self`, making it hard to test independently.
- **Impact**: Hard to test individual concerns. Difficult to reason about error handling. The method is the second-largest in the codebase.
- **Suggested Fix**: Extract parent-fetching and ancestor-warming into separate methods or a dedicated `HierarchyWarmingCoordinator`.
- **ROI**: 8/10 -- clear decomposition path, high readability improvement

### SM-L007: build_progressive_async method is 240+ lines (HIGH)

- **Severity**: HIGH
- **Category**: Complexity
- **Subsystem**: 3
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:138-389` -- `build_progressive_async()` (251 lines)
- **Description**: `ProgressiveProjectBuilder.build_progressive_async()` is 251 lines with 6 numbered steps, resume logic, freshness probing, manifest management, and metrics tracking all in a single method. The method's complexity is compounded by nested conditionals for resume detection (lines 184-269 alone are 85 lines of resume/freshness logic).
- **Impact**: Any change to one step risks breaking others. Freshness probing is deeply entangled with resume logic.
- **Suggested Fix**: Extract each numbered step into its own private method: `_check_resume()`, `_probe_freshness()`, `_fetch_sections()`, `_merge_and_finalize()`.
- **ROI**: 8/10 -- clear step boundaries already exist in comments

### SM-L008: _fetch_and_persist_section is 230+ lines (MEDIUM)

- **Severity**: MEDIUM
- **Category**: Complexity
- **Subsystem**: 3
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:411-658` -- `_fetch_and_persist_section()` (247 lines)
- **Description**: Another oversized method handling resume detection, page iteration, pacing, checkpoint writing, task extraction, DataFrame construction, and section persistence all in sequence. The method has two distinct code paths (small section vs large section) with shared post-processing.
- **Impact**: Complex to test edge cases. Large/small section paths share only the tail of the method.
- **Suggested Fix**: Extract small-section and large-section paths into separate methods sharing a common finalization step.
- **ROI**: 6/10 -- some complexity in disentangling, good readability gain

### SM-L009: Private attribute access across class boundaries (MEDIUM)

- **Severity**: MEDIUM
- **Category**: Coupling
- **Subsystem**: 3, 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:695` -- `self._persistence._make_section_key()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:701` -- `self._persistence._s3_client.put_object_async()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:769` -- `self._persistence._get_manifest_lock()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:783` -- `self._persistence._manifest_cache[...]`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:784` -- `self._persistence._save_manifest_async()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py:140-141` -- `self.persistence._config.prefix`, `self.persistence._s3_client`
- **Description**: `ProgressiveProjectBuilder._write_checkpoint()` and `ProgressiveTier` directly access private attributes of `SectionPersistence` (`_make_section_key`, `_s3_client`, `_get_manifest_lock`, `_manifest_cache`, `_save_manifest_async`, `_config`). This creates tight coupling between classes.
- **Impact**: Any internal refactoring of `SectionPersistence` breaks callers. The checkpoint path bypasses the public API intentionally (to avoid marking sections COMPLETE), but could be formalized.
- **Suggested Fix**: Add public methods to `SectionPersistence`: `write_checkpoint_async()`, `get_s3_key_for_section()`, and make `_config.prefix` accessible via property.
- **ROI**: 7/10 -- moderate fix, eliminates fragile coupling

### SM-L010: Inconsistent statistics tracking patterns (MEDIUM)

- **Severity**: MEDIUM
- **Category**: DRY Violation / Naming
- **Subsystem**: 1, 2, 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:209-235` -- Dict-based stats per entity type with `_ensure_stats()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py:80-99` -- Dict-based stats (flat)
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py:92-103` -- Dict-based stats
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/coalescer.py:83-94` -- Dict-based stats
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/circuit_breaker.py:86-97` -- Dict-based stats
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:124` -- Uses `CacheMetrics` class
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:134` -- Uses `CacheMetrics` class
- **Description**: Two different statistics patterns coexist: UnifiedTaskStore subsystem uses `CacheMetrics` class (structured), while DataFrameCache subsystem uses raw `dict[str, int]` with manual `_ensure_stats()`. The dict-based approach requires `_ensure_stats()` calls before every stats update (called 8 times in `dataframe_cache.py`).
- **Impact**: Inconsistent observability. Stats are collected differently, making cross-subsystem dashboards harder. `_ensure_stats()` guard is easy to forget when adding new code paths.
- **Suggested Fix**: Standardize on `CacheMetrics` or a similar class for all components.
- **ROI**: 5/10 -- moderate effort, improves consistency

### SM-L011: _get_schema_version_for_entity called redundantly (LOW)

- **Severity**: LOW
- **Category**: Complexity / Performance
- **Subsystem**: 1
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:52-79` -- module-level function
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:761` -- called in `_check_freshness()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:732` -- called in `_schema_is_valid()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:499` -- called in `put_async()`
- **Description**: `_get_schema_version_for_entity()` is called up to 3 times per cache operation (once in `_check_freshness`, once in `_schema_is_valid` for circuit breaker path, once in `put_async`). Each call does a try/except with `SchemaRegistry.get_instance()`, `to_pascal_case()`, and `registry.get_schema()`. While the registry is a singleton, the repeated lookups and try/except overhead is unnecessary.
- **Impact**: Minor performance overhead per cache operation (3x registry lookups instead of 1x).
- **Suggested Fix**: Cache the schema version per entity_type in DataFrameCache, invalidated by `invalidate_on_schema_change()`.
- **ROI**: 4/10 -- low impact, minor optimization

### SM-L012: _resolve_schema_version duplicates _get_schema_version_for_entity (LOW)

- **Severity**: LOW
- **Category**: DRY Violation
- **Subsystem**: 3, 1
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py:194-216` -- `_resolve_schema_version()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:52-79` -- `_get_schema_version_for_entity()`
- **Description**: Two module-level functions with identical logic: import `SchemaRegistry` and `to_pascal_case`, get instance, look up schema by pascal-cased entity type, return version. The `section_persistence.py` version was created to "avoid circular imports" per its docstring, but both perform the same operation.
- **Impact**: Two functions to maintain for the same lookup. Minor but adds to cognitive load.
- **Suggested Fix**: Extract to a shared utility or have `section_persistence.py` import the one from `dataframe_cache.py` (if circular import concern can be resolved via lazy import).
- **ROI**: 4/10 -- easy fix, low impact

### SM-L013: ProgressiveTier double-serializes DataFrame on put (LOW)

- **Severity**: LOW
- **Category**: Performance
- **Subsystem**: 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py:234-248` -- `put_async()`
- **Description**: `ProgressiveTier.put_async()` delegates to `SectionPersistence.write_final_artifacts_async()` which serializes the DataFrame to parquet internally. Then on line 246-247, the method re-serializes the DataFrame to parquet again just to calculate `bytes_written` stats.
- **Impact**: Double parquet serialization on every cache write. For large DataFrames this is measurable overhead.
- **Suggested Fix**: Get the byte count from the SectionPersistence write result, or estimate from `df.estimated_size()`.
- **ROI**: 5/10 -- easy fix, measurable performance gain for large DataFrames

### SM-L014: Inconsistent f-string vs structured logging (MEDIUM)

- **Severity**: MEDIUM
- **Category**: Naming / Consistency
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:172` -- `f"S3 delete failed for {key}, continuing: {e}"`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:215` -- `f"S3 get_versioned failed for {key}/{entry_type.value}: {e}"`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:231` -- `f"Promotion to Redis failed for {key}: {e}"`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:261-262` -- f-string logging
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:300-321` -- more f-string patterns
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:165,205,294,361,382,452,500,593,616,752,755,810` -- f-string logging throughout
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:178,217,333,639,818-828` -- f-string logging
- **Description**: The UnifiedTaskStore subsystem (tiered.py, redis.py, s3.py) uses f-string interpolation in log messages (`logger.warning(f"S3 delete failed for {key}: {e}")`), while the DataFrameCache subsystem and newer code uses structured logging with `extra={}` dicts. The project's logging library (`autom8y_log`) supports structured logging.
- **Impact**: f-string logging prevents structured log parsing, makes log aggregation harder, and risks PII leakage in log messages. ~40+ instances in the task cache backends.
- **Suggested Fix**: Migrate f-string log calls to structured `extra={}` pattern.
- **ROI**: 6/10 -- tedious but mechanical, improves observability

### SM-L015: TieredCacheProvider uses getattr for clear_all_tasks (LOW)

- **Severity**: LOW
- **Category**: Type Safety
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:459-461` -- `getattr(self._hot, "clear_all_tasks", None)`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:469-471` -- `getattr(self._cold, "clear_all_tasks", None)`
- **Description**: `TieredCacheProvider.clear_all_tasks()` uses `getattr` to check if the underlying provider has `clear_all_tasks`, even though both `RedisCacheProvider` and `S3CacheProvider` implement it. This is a type safety escape hatch that masks missing protocol methods.
- **Impact**: If `clear_all_tasks` is removed from a backend, the code silently skips instead of failing. The `CacheProvider` protocol should either include `clear_all_tasks` or not.
- **Suggested Fix**: Add `clear_all_tasks` to the `CacheProvider` protocol, or use `isinstance` checks.
- **ROI**: 3/10 -- low impact, minor type safety improvement

### SM-L016: S3 batch operations are sequential (not parallelized) (MEDIUM)

- **Severity**: MEDIUM
- **Category**: Performance
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:565-594` -- `get_batch()` -- sequential loop
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:596-617` -- `set_batch()` -- sequential loop
- **Description**: `S3CacheProvider.get_batch()` and `set_batch()` make individual S3 requests in a synchronous loop. The class correctly documents this ("S3 does not support true batch GET"), but the calls could be parallelized using `concurrent.futures` since the class already uses threading.
- **Impact**: Batch cold-tier lookups scale linearly with key count. For 100 keys, this could be 100 sequential S3 requests.
- **Suggested Fix**: Use `concurrent.futures.ThreadPoolExecutor` for parallel S3 batch operations.
- **ROI**: 5/10 -- moderate complexity, measurable latency improvement for batch ops

### SM-L017: Unused `already_known` list in warm_ancestors_async (LOW)

- **Severity**: LOW
- **Category**: Dead Code
- **Subsystem**: 3
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py:204` -- `already_known: list[str] = []`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py:251-253` -- iteration over `already_known` (always empty)
- **Description**: `already_known` is initialized as an empty list on line 204 and never populated. The loop on lines 251-253 iterates over it (always zero iterations). This appears to be a remnant of a refactoring where the distinction between "already known" and "to fetch" was simplified.
- **Impact**: Dead code that adds cognitive load. Zero runtime impact.
- **Suggested Fix**: Remove the `already_known` variable and its iteration loop.
- **ROI**: 9/10 -- trivial fix, removes confusion

### SM-L018: SectionPersistence passes kwargs to logger without extra= (LOW)

- **Severity**: LOW
- **Category**: Naming / Consistency
- **Subsystem**: 3
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py:432-434` -- `logger.warning("manifest_get_failed", project_gid=project_gid, error=result.error)`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py:444` -- same pattern
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py:499,657,670,737,757` -- same pattern
- **Description**: Multiple logger calls in `SectionPersistence` pass structured data as keyword arguments (`project_gid=...`) rather than in `extra={}` dict. This relies on `autom8y_log` accepting kwargs, but is inconsistent with the dominant pattern used elsewhere.
- **Impact**: Minor inconsistency. May or may not work depending on logger configuration. If `autom8y_log` changes its kwargs handling, these calls break.
- **Suggested Fix**: Standardize to `extra={"project_gid": ..., "error": ...}` pattern.
- **ROI**: 3/10 -- mechanical, low impact

### SM-L019: Missing TYPE_CHECKING guard yields empty import block (LOW)

- **Severity**: LOW
- **Category**: Dead Code / Import Hygiene
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:36-37` -- `if TYPE_CHECKING: pass`
- **Description**: Empty `TYPE_CHECKING` block. The `TYPE_CHECKING` import and the empty `if` block are dead code.
- **Impact**: Zero runtime impact. Minor code noise.
- **Suggested Fix**: Remove the `TYPE_CHECKING` import and empty block.
- **ROI**: 10/10 -- trivial one-line fix

### SM-L020: _check_freshness_and_serve has 7 parameters (LOW)

- **Severity**: LOW
- **Category**: Complexity
- **Subsystem**: 1
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:371-379` -- 7 parameters
- **Description**: `_check_freshness_and_serve()` takes 7 parameters: `self, entry, current_watermark, project_gid, entity_type, cache_key, tier`. This was noted in the prior cycle but not addressed as it was part of the LKG/SWR extraction. The method also contains inline imports from `autom8_asana.config`.
- **Impact**: Method signature is unwieldy. Parameters are all pass-through context.
- **Suggested Fix**: Group `project_gid`, `entity_type`, `cache_key`, `tier` into a `CacheLookupContext` dataclass.
- **ROI**: 3/10 -- cosmetic, low urgency

### SM-L021: Inline imports from config in hot paths (LOW)

- **Severity**: LOW
- **Category**: Performance / Style
- **Subsystem**: 1
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:385-389` -- `from autom8_asana.config import ...`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:700` -- `from autom8_asana.config import ...`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:789-793` -- `from autom8_asana.config import ...`
- **Description**: Config values (`DEFAULT_ENTITY_TTLS`, `DEFAULT_TTL`, `SWR_GRACE_MULTIPLIER`, `LKG_MAX_STALENESS_MULTIPLIER`) are imported inside methods that are called on every cache lookup. Python caches module imports, so the performance impact is minimal, but these imports appear 3 times in the same file, each importing overlapping sets of names.
- **Impact**: Minor. Python's import system caches modules, so this is primarily a readability concern.
- **Suggested Fix**: Move these to module-level imports since the circular import concern (noted in docstring) could be resolved with TYPE_CHECKING or lazy imports at class init time.
- **ROI**: 2/10 -- very low impact

### SM-L022: _swr_build callback defined inside factory function (MEDIUM)

- **Severity**: MEDIUM
- **Category**: Complexity / Testability
- **Subsystem**: 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py:138-186` -- `_swr_build` closure
- **Description**: The SWR build callback is defined as a 48-line closure inside `initialize_dataframe_cache()`. It captures `cache` from the outer scope and performs substantial logic: PAT retrieval, workspace GID lookup, client construction, schema lookup, section persistence setup, and progressive build execution. This closure is untestable in isolation.
- **Impact**: Cannot unit test the SWR build path without calling the entire factory function. Difficult to mock dependencies.
- **Suggested Fix**: Extract to a module-level async function or class method that accepts the cache as a parameter.
- **ROI**: 6/10 -- moderate complexity, significant testability improvement

### SM-L023: MemoryTier._get_max_bytes() recalculates on every eviction check (LOW)

- **Severity**: LOW
- **Category**: Performance
- **Subsystem**: 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py:240-254` -- `_get_max_bytes()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py:217-223` -- called in `_should_evict()`
- **Description**: `_get_max_bytes()` calls `_get_container_memory_bytes()` which reads cgroup files or env vars on every invocation. This is called inside `_should_evict()`, which is called inside the `while` loop of `put()`. For a put that triggers multiple evictions, this reads the filesystem multiple times.
- **Impact**: Filesystem reads in a hot path under lock. Likely negligible in practice (OS caches the reads), but wasteful.
- **Suggested Fix**: Cache the container memory value at init time (it doesn't change during process lifetime).
- **ROI**: 5/10 -- trivial fix, prevents unnecessary syscalls

### SM-L024: MemoryTier._get_max_bytes() logs on every call (LOW)

- **Severity**: LOW
- **Category**: Performance / Noise
- **Subsystem**: 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py:245-252` -- `logger.debug()` inside `_get_max_bytes()`
- **Description**: `_get_max_bytes()` emits a debug log on every call. Since this is called on every `put()` and potentially multiple times during eviction loops, this generates high-volume debug logs.
- **Impact**: Log noise in debug mode. No production impact if debug is disabled.
- **Suggested Fix**: Move the log to `__post_init__` or remove it.
- **ROI**: 3/10 -- trivial fix, minor improvement

### SM-L025: EnhancedInMemoryCacheProvider.get_batch not thread-safe for batch atomicity (LOW)

- **Severity**: LOW
- **Category**: Concurrency
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py:287-304` -- `get_batch()` calls `get_versioned()` per key
- **Description**: `get_batch()` iterates over keys calling `get_versioned()` for each. Each `get_versioned()` acquires and releases the lock independently. This means the batch is not atomic -- entries could be modified between individual gets. For a cache, this is generally acceptable, but it differs from Redis backend's pipelined batch behavior.
- **Impact**: Low -- cache reads are inherently racy. The inconsistency is more conceptual than practical.
- **Suggested Fix**: Document the non-atomic behavior, or acquire lock once for the batch.
- **ROI**: 2/10 -- low impact, architectural consistency concern only

### SM-L026: Duplicate wrap_flat_array validators in query models (LOW)

- **Severity**: LOW
- **Category**: DRY Violation
- **Subsystem**: 4
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:145-153` -- `wrap_flat_array` on AggregateRequest.where
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:155-163` -- `wrap_having_flat_array` on AggregateRequest.having
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:206-217` -- `wrap_flat_array` on RowsRequest.where
- **Description**: Three nearly identical Pydantic `field_validator` methods that wrap bare lists in `{"and": v}`. The logic is identical across all three.
- **Impact**: Low -- Pydantic validators are class-bound, so extracting is somewhat constrained. But the duplication adds maintenance surface.
- **Suggested Fix**: Extract the wrapping logic to a shared function and call from each validator.
- **ROI**: 3/10 -- low impact, minor DRY improvement

### SM-L027: Duplicated section resolution pattern in QueryEngine (LOW)

- **Severity**: LOW
- **Category**: DRY Violation
- **Subsystem**: 4
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:106-117` -- section resolution in `execute_rows`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:332-341` -- identical section resolution in `execute_aggregate`
- **Description**: Both `execute_rows` and `execute_aggregate` have identical 10-line blocks for resolving the `section` parameter: lazy-import `SectionIndex`, call `from_enum_fallback()`, resolve GID, raise `UnknownSectionError`. Copy-pasted between the two methods.
- **Impact**: Low -- two locations to update if section resolution changes.
- **Suggested Fix**: Extract to `_resolve_section()` private method.
- **ROI**: 5/10 -- trivial extraction, clear deduplication

### SM-L028: Duplicated freshness info extraction in QueryEngine (LOW)

- **Severity**: LOW
- **Category**: DRY Violation
- **Subsystem**: 4
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:258-266` -- freshness meta extraction in `execute_rows`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:408-416` -- identical extraction in `execute_aggregate`
- **Description**: Both methods have identical 8-line blocks reading freshness info via `getattr` and building `freshness_meta` dict. This is the consumer side of SM-L005.
- **Impact**: Two locations to update if freshness metadata structure changes. Compounds the getattr fragility.
- **Suggested Fix**: Extract to `_get_freshness_meta()` private method.
- **ROI**: 5/10 -- trivial extraction

### SM-L029: SchemaRegistry silently falls back to base schema for unknown types (LOW)

- **Severity**: LOW
- **Category**: Error Handling
- **Subsystem**: 5
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py:117-123` -- fallback to "*" schema
- **Description**: `SchemaRegistry.get_schema()` falls back to the base ("*") schema for any unknown task type rather than raising. This means a typo like `get_schema("Uint")` silently returns the base schema instead of failing. The `SchemaNotFoundError` exception exists but is only raised if there's no "*" schema registered (which never happens after initialization).
- **Impact**: Typos in entity type lookups are silently accepted. Could cause subtle data issues where the wrong schema is used for extraction.
- **Suggested Fix**: Log a warning when falling back to base schema, or make fallback opt-in via parameter.
- **ROI**: 4/10 -- easy fix, prevents silent errors

### SM-L030: dataframe_cache decorator assumes resolve() signature (LOW)

- **Severity**: LOW
- **Category**: Coupling / Type Safety
- **Subsystem**: 6
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py:72` -- `original_resolve = cls.resolve`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py:75-80` -- hardcoded `(self, criteria, project_gid, client)` signature
- **Description**: The `@dataframe_cache` decorator hardcodes the expected method signature as `(self, criteria, project_gid, client)` and accesses `cls.resolve` without type checking. If any strategy changes its `resolve()` signature, the decorator breaks at runtime with an opaque error.
- **Impact**: Fragile coupling to strategy interface. No compile-time safety.
- **Suggested Fix**: Define a `ResolutionStrategy` Protocol with the expected `resolve()` signature and type-check in the decorator.
- **ROI**: 3/10 -- moderate complexity, low likelihood of breakage

### SM-L031: os.environ.get for SECTION_FRESHNESS_PROBE config (LOW)

- **Severity**: LOW
- **Category**: Config
- **Subsystem**: 3
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:219` -- `os.environ.get("SECTION_FRESHNESS_PROBE", "1") != "0"`
- **Description**: A feature flag read directly from `os.environ` inside business logic, bypassing the Pydantic Settings pattern used elsewhere (`get_settings()`). The other config values in the same file (`CHECKPOINT_EVERY_N_PAGES`, `PACE_DELAY_SECONDS`, etc.) are imported from `config.py`.
- **Impact**: Inconsistent config sourcing. This flag won't appear in settings validation or documentation.
- **Suggested Fix**: Move to the Settings class or config module.
- **ROI**: 3/10 -- trivial, consistency improvement

### SM-L032: warm method stub in all three backends (LOW)

- **Severity**: LOW
- **Category**: Dead Code
- **Subsystem**: 2
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:597-617` -- `warm()` returns placeholder
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:619-641` -- `warm()` returns placeholder
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py:318-336` -- `warm()` returns placeholder
- **Description**: All three cache backends implement `warm()` as a stub that logs "not yet implemented" and returns `WarmResult(warmed=0, failed=0, skipped=len(gids))`. The method is required by the `CacheProvider` protocol but never performs actual warming. Redis says "Phase 1" in its comment.
- **Impact**: Protocol surface area that does nothing. Callers may incorrectly assume warming is functional.
- **Suggested Fix**: If warming is not planned, remove from protocol. If planned, track as a TODO with a concrete timeline.
- **ROI**: 2/10 -- low urgency, protocol cleanliness

---

## Cross-Cutting Observations

### OBS-1: Two parallel cache architectures with different design philosophies

The codebase has two independent cache systems:
- **DataFrameCache** (subsystem 1): Polars DataFrames, Memory+S3 tiered, entity-aware TTL, SWR, circuit breaker, coalescer. Uses `dataclass` composition. Stats are raw dicts.
- **UnifiedTaskStore** (subsystem 2): JSON task dicts, Redis+S3 tiered, version-based freshness, hierarchy-aware. Uses `CacheProvider` protocol. Stats use `CacheMetrics`.

These share no common infrastructure for: error handling, degraded mode, statistics, configuration, or S3 access. The DataFrameCache uses `AsyncS3Client` (asyncio.to_thread), while the task cache uses synchronous `boto3` directly. This is an architectural choice (different access patterns), but the operational tooling gap means observability is fragmented.

### OBS-2: FreshnessInfo side-channel is expanding (related to prior SM-004)

The `_last_freshness` side-channel from DataFrameCache has propagated to QueryEngine via `EntityQueryService._last_freshness_info`. This is the pattern the prior cycle flagged as SM-004 (DEFERRED). It is now consumed in two places in QueryEngine via `getattr`. The pattern should be formalized before it spreads further.

### OBS-3: Schema version lookup is a shared concern poorly shared

Three different functions do the same SchemaRegistry lookup: `_get_schema_version_for_entity()` in dataframe_cache.py, `_resolve_schema_version()` in section_persistence.py, and `AsanaSchemaProvider.schema_version` in schema_providers.py. Each cites circular import concerns as the reason for duplication.

### OBS-4: Configuration is sourced from 3 different mechanisms

1. `autom8_asana.config` module (constants like `DEFAULT_ENTITY_TTLS`)
2. `autom8_asana.settings.get_settings()` (Pydantic Settings for S3 config)
3. Direct `os.environ.get()` (e.g., `SECTION_FRESHNESS_PROBE`, `CONTAINER_MEMORY_MB`)

This means there's no single source of truth for configuration, and some values are validated (Pydantic) while others are not.

---

## Verification Attestation

| File | Lines Read | Subsystem |
|------|-----------|-----------|
| `src/autom8_asana/cache/dataframe_cache.py` | 1-900 (full) | 1: DataFrameCache |
| `src/autom8_asana/cache/unified.py` | 1-897 (full) | 2: UnifiedTaskStore |
| `src/autom8_asana/cache/tiered.py` | 1-522 (full) | 2: UnifiedTaskStore |
| `src/autom8_asana/cache/backends/redis.py` | 1-813 (full) | 2: UnifiedTaskStore |
| `src/autom8_asana/cache/backends/s3.py` | 1-900 (full) | 2: UnifiedTaskStore |
| `src/autom8_asana/cache/backends/memory.py` | 1-433 (full) | 2: UnifiedTaskStore |
| `src/autom8_asana/dataframes/builders/progressive.py` | 1-969 (full) | 3: ProgressiveProjectBuilder |
| `src/autom8_asana/dataframes/section_persistence.py` | 1-910 (full) | 3: ProgressiveProjectBuilder |
| `src/autom8_asana/cache/hierarchy_warmer.py` | 1-281 (full) | 3: ProgressiveProjectBuilder |
| `src/autom8_asana/query/engine.py` | 1-430 (full) | 4: QueryEngine |
| `src/autom8_asana/query/compiler.py` | 1-298 (full) | 4: QueryEngine |
| `src/autom8_asana/query/models.py` | 1-249 (full) | 4: QueryEngine |
| `src/autom8_asana/query/join.py` | 1-154 (full) | 4: QueryEngine |
| `src/autom8_asana/query/aggregator.py` | 1-285 (full) | 4: QueryEngine |
| `src/autom8_asana/dataframes/models/registry.py` | 1-194 (full) | 5: Schema Registry |
| `src/autom8_asana/dataframes/models/schema.py` | 1-189 (full) | 5: Schema Registry |
| `src/autom8_asana/cache/schema_providers.py` | 1-152 (full) | 5: Schema Registry |
| `src/autom8_asana/cache/dataframe/tiers/memory.py` | 1-268 (full) | 6: Memory management |
| `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 1-370 (full) | 6: Memory management |
| `src/autom8_asana/dataframes/async_s3.py` | 1-681 (full) | 6: S3 persistence |
| `src/autom8_asana/cache/dataframe/coalescer.py` | 1-256 (full) | 6: Memory management |
| `src/autom8_asana/cache/dataframe/circuit_breaker.py` | 1-256 (full) | 6: Memory management |
| `src/autom8_asana/cache/dataframe/factory.py` | 1-254 (full) | 6: Memory management |
| `src/autom8_asana/cache/dataframe/decorator.py` | 1-252 (full) | 6: Memory management |

---

## Priority Matrix

| ID | Severity | ROI | Subsystem | Recommended Action |
|----|----------|-----|-----------|-------------------|
| SM-L001 | HIGH | 9/10 | Cross-cutting | Extract ENTITY_TYPES constant; fix existing inconsistencies |
| SM-L006 | HIGH | 8/10 | UnifiedTaskStore | Decompose put_batch_async into 3 methods |
| SM-L007 | HIGH | 8/10 | ProgressiveBuilder | Extract numbered steps into private methods |
| SM-L005 | MEDIUM | 7/10 | DataFrameCache + QueryEngine | Formalize freshness info as explicit return value |
| SM-L002 | MEDIUM | 7/10 | Cross-cutting | Extract shared datetime parser |
| SM-L009 | MEDIUM | 7/10 | ProgressiveBuilder + SectionPersistence | Add public API for checkpoint operations |
| SM-L003 | MEDIUM | 6/10 | Task cache backends | Extract DegradedModeHandler |
| SM-L004 | MEDIUM | 6/10 | Task cache backends | Extract shared error classification |
| SM-L008 | MEDIUM | 6/10 | ProgressiveBuilder | Split small/large section paths |
| SM-L014 | MEDIUM | 6/10 | Task cache backends | Migrate f-string logging to structured |
| SM-L022 | MEDIUM | 6/10 | Factory | Extract _swr_build to module-level function |
| SM-L010 | MEDIUM | 5/10 | Cross-cutting | Standardize statistics pattern |
| SM-L013 | LOW | 5/10 | ProgressiveTier | Remove double parquet serialization |
| SM-L016 | MEDIUM | 5/10 | S3 backend | Parallelize batch operations |
| SM-L023 | LOW | 5/10 | MemoryTier | Cache container memory at init |
| SM-L027 | LOW | 5/10 | QueryEngine | Extract _resolve_section method |
| SM-L028 | LOW | 5/10 | QueryEngine | Extract _get_freshness_meta method |
| SM-L017 | LOW | 9/10 | HierarchyWarmer | Remove dead `already_known` variable |
| SM-L019 | LOW | 10/10 | TieredCache | Remove empty TYPE_CHECKING block |
| SM-L011 | LOW | 4/10 | DataFrameCache | Cache schema version lookups |
| SM-L012 | LOW | 4/10 | SectionPersistence | Deduplicate schema version lookup |
| SM-L029 | LOW | 4/10 | SchemaRegistry | Add fallback warning log |
| SM-L015 | LOW | 3/10 | TieredCache | Add clear_all_tasks to protocol |
| SM-L018 | LOW | 3/10 | SectionPersistence | Standardize logger kwargs to extra= |
| SM-L020 | LOW | 3/10 | DataFrameCache | Group parameters into context object |
| SM-L024 | LOW | 3/10 | MemoryTier | Move debug log to init |
| SM-L026 | LOW | 3/10 | Query models | Extract wrap_flat_array helper |
| SM-L030 | LOW | 3/10 | Decorator | Define ResolutionStrategy Protocol |
| SM-L031 | LOW | 3/10 | ProgressiveBuilder | Move env var to Settings |
| SM-L021 | LOW | 2/10 | DataFrameCache | Move config imports to module level |
| SM-L025 | LOW | 2/10 | Memory backend | Document non-atomic batch behavior |
| SM-L032 | LOW | 2/10 | All backends | Decide on warm() method future |
