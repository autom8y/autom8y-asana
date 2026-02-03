# Refactoring Plan: Cache Architecture Landscape

**Produced by**: Architect Enforcer
**Input**: Smell Report `smell-report-cache-landscape.md` (32 findings)
**Date**: 2026-02-04

---

## Architectural Assessment

The cache landscape consists of two parallel subsystems (DataFrameCache and UnifiedTaskStore) with distinct design philosophies but shared operational concerns. The smell report confirms the codebase is generally well-structured -- most findings are DRY violations and configuration sprawl, not architectural defects.

**Root cause clusters**:
1. **Entity type proliferation without central registry** -- hardcoded lists in 6+ locations have already drifted (SM-L001)
2. **Datetime parsing solved independently 3 times** -- classic extract-utility opportunity (SM-L002)
3. **God methods in hot paths** -- `put_batch_async` and `build_progressive_async` grew organically as features were added (SM-L006, SM-L007)
4. **QueryEngine copy-paste** -- section resolution and freshness extraction duplicated between two public methods (SM-L027, SM-L028)

**Boundary health**: Module boundaries are generally sound. The side-channel freshness propagation (SM-L005) is the most concerning boundary violation but requires API changes to fix properly -- deferred.

---

## Phase 1: Quick Wins (Zero-Risk)

These are dead code removals and trivial cleanups. Each is a single atomic commit with near-zero blast radius.

### RF-L01: Remove empty TYPE_CHECKING block from tiered.py

- **Addresses**: SM-L019
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:27,36-37`
- **Before**:
  ```python
  from typing import TYPE_CHECKING, Any
  # ...
  if TYPE_CHECKING:
      pass
  ```
- **After**:
  ```python
  from typing import Any
  ```
  Remove the `TYPE_CHECKING` import and the empty `if TYPE_CHECKING: pass` block entirely.
- **Contract**: No runtime behavior change. `TYPE_CHECKING` was unused. The `Any` import on the same line must be preserved.
- **Invariants**:
  - All existing tests pass without modification
  - `ruff check` passes
  - `mypy --strict` passes (TYPE_CHECKING was not guarding any type imports)
- **Risk**: LOW
- **Commit Message**: `chore(cache): remove dead TYPE_CHECKING block from tiered.py`

---

### RF-L02: Remove dead `already_known` variable from hierarchy_warmer.py

- **Addresses**: SM-L017
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py:203-204,250-254`
- **Before**:
  ```python
  parents_to_fetch = gids_to_fetch
  already_known: list[str] = []
  # ... (46 lines later)
  # Add already-known parents that might have grandparents we need
  for parent_gid in already_known:
      grandparent = hierarchy_index.get_parent_gid(parent_gid)
      if grandparent and grandparent not in visited:
          next_level_gids.append(grandparent)
  ```
- **After**:
  ```python
  parents_to_fetch = gids_to_fetch
  ```
  Remove line 204 (`already_known: list[str] = []`) and lines 250-254 (the comment and `for parent_gid in already_known:` loop). The `parents_to_fetch = gids_to_fetch` assignment on line 203 remains.
- **Contract**: `already_known` is initialized empty and never populated. The loop on lines 251-253 iterates zero times. Removing it changes nothing.
- **Invariants**:
  - `warm_ancestors_async()` return value unchanged for any input
  - All hierarchy warmer tests pass (6 unit tests + 1 integration test)
  - No callers depend on `already_known` (it is a local variable)
- **Risk**: LOW
- **Commit Message**: `chore(cache): remove dead already_known variable from hierarchy_warmer`

---

### RF-L03: Replace double parquet serialization in ProgressiveTier.put_async

- **Addresses**: SM-L013
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py:244-248`
- **Before**:
  ```python
  if success:
      # Estimate bytes written from DataFrame size
      buffer = io.BytesIO()
      entry.dataframe.write_parquet(buffer)
      self._stats["bytes_written"] += len(buffer.getvalue())
  ```
- **After**:
  ```python
  if success:
      # Estimate bytes written from DataFrame memory footprint
      self._stats["bytes_written"] += entry.dataframe.estimated_size()
  ```
  Remove the `import io` at the top of the file if it becomes unused after this change. Use Polars' `estimated_size()` which returns approximate memory usage without re-serializing.
- **Contract**: The `bytes_written` stat will now reflect estimated in-memory size rather than exact parquet-encoded size. This is a stats-only change -- no external API, cache behavior, or data flow is affected. The stat was already labeled "estimate" in the variable name.
- **Invariants**:
  - `put_async()` return value unchanged
  - Data written to S3 unchanged (that happens in `write_final_artifacts_async`)
  - All other stats keys unchanged
- **Verification**: Check whether `io` is imported at module level or only used here. If only here, remove the import.
- **Risk**: LOW
- **Commit Message**: `perf(cache): replace double parquet serialization with estimated_size in ProgressiveTier`

---

### RF-L04: Cache container memory at MemoryTier init

- **Addresses**: SM-L023, SM-L024
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/memory.py:22-55,240-254`
- **Before**:
  ```python
  # _get_container_memory_bytes() is a module-level function called on every _get_max_bytes()
  # _get_max_bytes() is called inside _should_evict(), which runs in the put() while loop
  def _get_max_bytes(self) -> int:
      total_memory = _get_container_memory_bytes()
      max_bytes = int(total_memory * self.max_heap_percent)
      logger.debug("memory_tier_max_bytes", extra={...})
      return max_bytes
  ```
- **After**:
  ```python
  # In MemoryTier.__post_init__ (or __init__), compute and store:
  def __post_init__(self) -> None:
      # ... existing init code ...
      self._container_memory_bytes = _get_container_memory_bytes()
      self._max_bytes = int(self._container_memory_bytes * self.max_heap_percent)
      logger.debug(
          "memory_tier_max_bytes",
          extra={
              "total_memory_mb": self._container_memory_bytes // (1024 * 1024),
              "heap_percent": self.max_heap_percent,
              "max_bytes_mb": self._max_bytes // (1024 * 1024),
          },
      )

  def _get_max_bytes(self) -> int:
      return self._max_bytes
  ```
  Container memory does not change during process lifetime (cgroups are set at container start). Caching it once eliminates repeated filesystem reads and the per-call debug log.
- **Contract**: The computed `_max_bytes` value is identical. The debug log fires once at init instead of on every eviction check. No change to eviction behavior.
- **Invariants**:
  - `_should_evict()` returns same boolean for same inputs
  - `put()` behavior unchanged
  - `get_stats()` unchanged
  - Note: `_container_memory_bytes` and `_max_bytes` are new private attributes on the dataclass. Since `MemoryTier` is a `@dataclass`, these must be added as `field(init=False)` or set in `__post_init__`.
- **Risk**: LOW
- **Commit Message**: `perf(cache): cache container memory at MemoryTier init instead of per-eviction`

---

## Phase 2: DRY Extractions (Low-Risk)

These extract duplicated logic into shared locations. Each touches 2-4 files but the extraction pattern is mechanical.

### RF-L05: Extract shared datetime parsing utility

- **Addresses**: SM-L002
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py:845-871` -- `_parse_version()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:900-930` -- `_parse_datetime()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/progressive.py:347-369` -- `_parse_datetime()`
- **Before**: Three independent implementations of the same logic:
  1. `UnifiedTaskStore._parse_version()` -- returns `datetime.now(UTC)` on failure
  2. `ProgressiveProjectBuilder._parse_datetime()` -- also handles `datetime` input, returns `None` on failure
  3. `ProgressiveTier._parse_datetime()` -- returns `datetime.now(UTC)` on failure
- **After**: Create `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/datetime_utils.py`:
  ```python
  """Shared datetime parsing utilities for cache subsystems."""
  from __future__ import annotations
  from datetime import UTC, datetime

  def parse_iso_datetime(value: str | None, *, default_now: bool = True) -> datetime | None:
      """Parse ISO datetime string with Z-suffix handling.

      Args:
          value: ISO format datetime string, or None.
          default_now: If True, return datetime.now(UTC) when value is
              None/unparseable. If False, return None.

      Returns:
          Timezone-aware UTC datetime, or None/now per default_now flag.
      """
      if not value:
          return datetime.now(UTC) if default_now else None

      if value.endswith("Z"):
          value = value[:-1] + "+00:00"

      try:
          dt = datetime.fromisoformat(value)
          if dt.tzinfo is None:
              dt = dt.replace(tzinfo=UTC)
          return dt
      except ValueError:
          return datetime.now(UTC) if default_now else None
  ```

  Then replace each call site:
  - `UnifiedTaskStore._parse_version(self, modified_at)` becomes a one-liner calling `parse_iso_datetime(modified_at, default_now=True)`
  - `ProgressiveTier._parse_datetime(self, value)` becomes a one-liner calling `parse_iso_datetime(value, default_now=True)`
  - `ProgressiveProjectBuilder._parse_datetime(self, value)` -- this one also handles `datetime` input; keep the `isinstance(value, datetime)` guard in the method, delegate string parsing to `parse_iso_datetime(value, default_now=False)`

  The three original methods can be kept as thin wrappers (preserving the method signature contract) or inlined at call sites. Prefer keeping as wrappers for this cycle to minimize call-site changes.
- **Contract**:
  - `UnifiedTaskStore._parse_version()` return values unchanged for any input
  - `ProgressiveTier._parse_datetime()` return values unchanged for any input
  - `ProgressiveProjectBuilder._parse_datetime()` return values unchanged for any input (including `datetime` and non-string inputs)
- **Invariants**:
  - The shared function is pure (no side effects beyond the `datetime.now()` fallback)
  - All callers get identical behavior via `default_now` flag
  - Warning log in `UnifiedTaskStore._parse_version()` is preserved in the wrapper
- **Risk**: LOW
- **Commit Message**: `refactor(core): extract shared datetime parsing utility from 3 duplicate implementations`

---

### RF-L06: Extract section resolution helper in QueryEngine

- **Addresses**: SM-L027
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:104-117,331-341`
- **Before**: Identical 10-line blocks in `execute_rows` and `execute_aggregate`:
  ```python
  section_name_filter: str | None = None
  if request.section is not None:
      if section_index is None:
          from autom8_asana.metrics.resolve import SectionIndex as _SectionIndex
          section_index = _SectionIndex.from_enum_fallback(entity_type)
      resolved_gid = section_index.resolve(request.section)
      if resolved_gid is None:
          raise UnknownSectionError(section=request.section)
      section_name_filter = request.section
  ```
- **After**: Extract to private method:
  ```python
  def _resolve_section(
      self,
      section: str | None,
      entity_type: str,
      section_index: SectionIndex | None,
  ) -> str | None:
      """Resolve section parameter to section name filter.

      Returns:
          Section name string if section was provided, None otherwise.

      Raises:
          UnknownSectionError: If section cannot be resolved.
      """
      if section is None:
          return None
      if section_index is None:
          from autom8_asana.metrics.resolve import SectionIndex as _SectionIndex
          section_index = _SectionIndex.from_enum_fallback(entity_type)
      resolved_gid = section_index.resolve(section)
      if resolved_gid is None:
          raise UnknownSectionError(section=section)
      return section
  ```
  Replace both call sites with:
  ```python
  section_name_filter = self._resolve_section(
      request.section, entity_type, section_index
  )
  ```
- **Contract**: Identical behavior. Same exception raised on unknown section. Same return value.
- **Invariants**:
  - `execute_rows()` and `execute_aggregate()` responses unchanged
  - `UnknownSectionError` raised for same inputs as before
  - Lazy import of `SectionIndex` preserved (only imported when section is not None)
- **Risk**: LOW
- **Commit Message**: `refactor(query): extract _resolve_section helper to deduplicate engine methods`

---

### RF-L07: Extract freshness metadata helper in QueryEngine

- **Addresses**: SM-L028
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:258-266,408-416`
- **Before**: Identical 8-line blocks in `execute_rows` and `execute_aggregate`:
  ```python
  freshness_info = getattr(self.query_service, "_last_freshness_info", None)
  freshness_meta: dict[str, object] = {}
  if freshness_info is not None:
      freshness_meta = {
          "freshness": freshness_info.freshness,
          "data_age_seconds": freshness_info.data_age_seconds,
          "staleness_ratio": freshness_info.staleness_ratio,
      }
  ```
- **After**: Extract to private method:
  ```python
  def _get_freshness_meta(self) -> dict[str, object]:
      """Read freshness info from query_service side-channel.

      Note: Uses getattr side-channel pattern (see SM-L005 for future
      formalization). This helper consolidates the read to a single location.
      """
      freshness_info = getattr(self.query_service, "_last_freshness_info", None)
      if freshness_info is None:
          return {}
      return {
          "freshness": freshness_info.freshness,
          "data_age_seconds": freshness_info.data_age_seconds,
          "staleness_ratio": freshness_info.staleness_ratio,
      }
  ```
  Replace both call sites with:
  ```python
  freshness_meta = self._get_freshness_meta()
  ```
- **Contract**: Identical dict returned. Same `getattr` side-channel behavior. The docstring notes the SM-L005 technical debt for future cleanup.
- **Invariants**:
  - API response `meta` fields unchanged for any query
  - The `getattr` pattern is unchanged (still reads `_last_freshness_info`)
- **Risk**: LOW
- **Commit Message**: `refactor(query): extract _get_freshness_meta helper to deduplicate engine methods`

---

### RF-L08: Deduplicate schema version lookup

- **Addresses**: SM-L012
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:52-79` -- `_get_schema_version_for_entity()`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py:194-216` -- `_resolve_schema_version()`
- **Before**: Two module-level functions with identical logic (lazy import `SchemaRegistry`, `to_pascal_case`, look up schema, return version). `section_persistence.py` cites circular import avoidance.
- **After**: Move the canonical implementation to `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/datetime_utils.py` (rename to `core/schema_utils.py` or add to a new `core/` module alongside the datetime utility). Actually, to minimize new files, place it in the same `core/datetime_utils.py` module renamed to `core/parsing.py` -- NO, keep it focused. Better: create `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/schema.py`:
  ```python
  """Schema version lookup utilities."""
  from __future__ import annotations
  from autom8y_log import get_logger

  logger = get_logger(__name__)

  def get_schema_version(entity_type: str | None) -> str | None:
      """Look up schema version from SchemaRegistry for an entity type.

      Performs lazy imports to avoid circular dependencies.

      Args:
          entity_type: Entity type in lowercase (e.g., "unit", "contact").
              Returns None if entity_type is None or empty.

      Returns:
          Schema version string if found, None if lookup fails.
      """
      if not entity_type:
          return None
      try:
          from autom8_asana.dataframes.models.registry import SchemaRegistry
          from autom8_asana.services.resolver import to_pascal_case

          registry = SchemaRegistry.get_instance()
          registry_key = to_pascal_case(entity_type)
          schema = registry.get_schema(registry_key)
          return schema.version if schema else None
      except Exception as e:
          logger.warning(
              "schema_version_lookup_failed",
              extra={"entity_type": entity_type, "error": str(e)},
          )
          return None
  ```
  Then:
  - In `dataframe_cache.py`: Replace `_get_schema_version_for_entity` body with `from autom8_asana.core.schema import get_schema_version` and delegate. Or keep the function as a thin wrapper for backwards compatibility with internal callers.
  - In `section_persistence.py`: Replace `_resolve_schema_version` body with import and delegate.
- **Contract**:
  - `_get_schema_version_for_entity("unit")` returns identical value
  - `_resolve_schema_version("unit")` returns identical value
  - The warning log from `dataframe_cache.py` is preserved in the shared function
  - The `section_persistence.py` version silently returned `None` on exception -- the shared version now logs a warning. This is a MINOR behavioral addition (logging only), acceptable per the MAY-change rules.
- **Invariants**:
  - All callers get same return value for same entity_type
  - No changes to public APIs
- **Risk**: LOW
- **Commit Message**: `refactor(core): extract shared schema version lookup from dataframe_cache and section_persistence`

---

## Phase 3: Method Decomposition (Medium-Risk)

These break large methods into smaller ones. They touch single files but modify critical code paths. Test coverage is the safety net.

### RF-L09: Decompose UnifiedTaskStore.put_batch_async

- **Addresses**: SM-L006
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py:452-687`
- **Before**: 235-line method with 3 responsibilities:
  1. **Batch cache storage** (lines 476-516): Build entries, register hierarchy, batch store
  2. **Immediate parent fetching** (lines 533-660): Identify missing parents, fetch with pacing, cache
  3. **Ancestor warming** (lines 662-672): Delegate to `warm_ancestors_async`
  Plus an inline function `_fetch_immediate_parent` (lines 565-588) that captures outer scope.
- **After**: Extract two private methods:
  ```python
  async def _fetch_immediate_parents(
      self,
      tasks: list[dict[str, Any]],
      tasks_client: TasksClient,
  ) -> int:
      """Fetch and cache immediate parents not yet in cache.

      Returns count of parents successfully fetched.
      """
      # Move lines 546-660 here
      # The _fetch_immediate_parent inner function becomes a nested function
      # in this method (same scope capture pattern, just in a smaller method)
      ...

  async def _warm_ancestors(
      self,
      tasks: list[dict[str, Any]],
      tasks_client: TasksClient,
  ) -> int:
      """Warm deeper ancestor chains via hierarchy warmer.

      Returns count of ancestors warmed.
      """
      # Move lines 662-672 here
      ...
  ```
  The main method becomes:
  ```python
  async def put_batch_async(self, tasks, ttl, opt_fields, tasks_client, warm_hierarchy) -> int:
      if not tasks:
          return 0
      # Step 1: Build entries and batch store (lines 479-516, unchanged)
      ...
      # Step 2: Warm hierarchy if requested
      immediate_parents_fetched = 0
      ancestors_warmed = 0
      if warm_hierarchy and tasks_client is not None:
          immediate_parents_fetched = await self._fetch_immediate_parents(tasks, tasks_client)
          ancestors_warmed = await self._warm_ancestors(tasks, tasks_client)
      # Step 3: Log and return (lines 674-687, unchanged)
      ...
  ```
- **Contract**:
  - `put_batch_async()` signature, return type, and return value unchanged
  - Same tasks cached, same parents fetched, same ancestors warmed
  - Same logging output (log messages and extra dicts identical)
  - The `_fetch_immediate_parent` inner function remains an inner function of `_fetch_immediate_parents` (it needs `tasks_client` and `self` from the enclosing scope, same as before)
- **Invariants**:
  - `put_batch_async()` returns same `cached_count` for same inputs
  - Hierarchy index state identical after call
  - Cache state identical after call
  - Pacing behavior (batch delay) unchanged
- **Risk**: MEDIUM -- this is the second-largest method in the codebase and sits on a hot path. However, the extraction is purely structural (moving lines, no logic changes). Test coverage includes 5+ unit tests and 2 integration tests.
- **Commit Message**: `refactor(cache): decompose put_batch_async into focused private methods`

---

### RF-L10: Extract _swr_build closure to module-level function

- **Addresses**: SM-L022
- **Files**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py:138-186`
- **Before**: 48-line closure inside `initialize_dataframe_cache()` capturing `cache` from outer scope.
- **After**: Extract to module-level async function:
  ```python
  async def _swr_build_callback(
      cache: DataFrameCache,
      project_gid: str,
      entity_type: str,
  ) -> None:
      """SWR background rebuild callback.

      Extracted from initialize_dataframe_cache closure for testability.
      """
      # Same body as current closure, but `cache` is now a parameter
      ...
  ```
  In `initialize_dataframe_cache()`, replace:
  ```python
  # Before:
  async def _swr_build(project_gid: str, entity_type: str) -> None:
      # 48 lines capturing `cache`
  cache.set_build_callback(_swr_build)

  # After:
  from functools import partial
  cache.set_build_callback(partial(_swr_build_callback, cache))
  ```
- **Contract**:
  - `set_build_callback` receives a callable with signature `(project_gid: str, entity_type: str) -> Coroutine`. The `partial` preserves this.
  - Same SWR rebuild behavior, same error handling, same imports.
- **Invariants**:
  - Cache initialization unchanged
  - SWR rebuild behavior unchanged
  - `_swr_build_callback` is now independently testable
- **Risk**: MEDIUM -- the `partial` changes how the callback is represented (no longer a closure). Verify `set_build_callback` does not inspect the callable beyond calling it.
- **Commit Message**: `refactor(cache): extract _swr_build closure to module-level function for testability`

---

## Phase 4: Entity Type Consolidation (Medium-Risk, Cross-Cutting)

This is the highest-value refactoring but touches the most files. Sequenced last because Phases 1-3 are prerequisites (they clean up noise, making this change easier to review).

### RF-L11: Centralize entity type constants

- **Addresses**: SM-L001
- **Files**:
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:216,554`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/schema_providers.py:122-128`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py:26`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:256`
  - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py:83-99`
- **Before**: Six independent hardcoded lists, already inconsistent:
  - `dataframe_cache.py:216`: `["unit", "business", "offer", "contact", "asset_edit"]`
  - `dataframe_cache.py:554`: same list
  - `schema_providers.py:122-128`: `["unit", "contact", "offer", "business", "asset_edit", "asset_edit_holder"]`
  - `admin.py:26`: `{"unit", "business", "offer", "contact", "asset_edit"}`
  - `resolver.py:256`: `{"unit", "business", "offer", "contact"}` (missing asset_edit -- ALREADY DEPRECATED with `get_resolvable_entities()`)
- **After**: Define constants in `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_types.py`:
  ```python
  """Canonical entity type constants.

  Single source of truth for entity type lists across all subsystems.
  Add new entity types HERE; all consumers import from this module.
  """

  # Core entity types used by DataFrameCache, admin, and query subsystems
  ENTITY_TYPES: list[str] = [
      "unit",
      "business",
      "offer",
      "contact",
      "asset_edit",
  ]

  # Extended set including derivative types (used by schema providers)
  ENTITY_TYPES_WITH_DERIVATIVES: list[str] = [
      *ENTITY_TYPES,
      "asset_edit_holder",
  ]
  ```
  Then update each consumer:
  - `dataframe_cache.py:216` and `:554` -- import `ENTITY_TYPES`
  - `schema_providers.py:122` -- import `ENTITY_TYPES_WITH_DERIVATIVES`
  - `admin.py:26` -- `VALID_ENTITY_TYPES = set(ENTITY_TYPES)` (import and convert to set)
  - `resolver.py:256` -- Leave `SUPPORTED_ENTITY_TYPES` as-is since it is already deprecated with a dynamic replacement (`get_resolvable_entities()`). Add a comment pointing to `core.entity_types` for reference.
  - `registry.py:83-99` -- The schema imports are keyed by PascalCase names, not this list. Leave as-is; the registry is the dynamic source. Add a comment noting the `ENTITY_TYPES` constant.
- **Contract**:
  - The actual values in each list are UNCHANGED. This is a code organization change, not a data change.
  - `resolver.py:256` `SUPPORTED_ENTITY_TYPES` is not modified (it is deprecated and dynamically overridden by `_get_supported_entity_types()`).
- **Invariants**:
  - `DataFrameCache.__post_init__` initializes same entity types
  - `invalidate()` iterates same entity types
  - `register_all_schema_providers()` registers same entity types
  - `VALID_ENTITY_TYPES` in admin.py contains same set members
  - No API behavior changes
- **Risk**: MEDIUM -- touches 4 files across 3 subsystems, but each change is a simple import replacement. All changes are compile-time verifiable (wrong import = immediate failure, not silent bug).
- **Commit Message**: `refactor(core): centralize entity type constants to eliminate drift across 6 locations`

---

## Deferred Items

| ID | Finding | Reason for Deferral |
|----|---------|-------------------|
| SM-L005 | FreshnessInfo side-channel formalization | Requires changing return types across DataFrameCache -> EntityQueryService -> QueryEngine (4 layers). This is a **feature change** (new return type), not a refactoring. Needs design discussion for `(df, FreshnessInfo)` tuple or result object pattern. |
| SM-L003 | Degraded-mode handler extraction | Touches 3 backends (Redis, S3, AsyncS3) with subtly different implementations. AsyncS3 uses `_degraded_backoff` vs settings-based interval. Requires careful protocol design. High test surface (each backend has 10+ tests). |
| SM-L004 | Error classification extraction | Same blast radius as SM-L003. The three backends have diverged error handling (string matching vs error code checking). Needs unified error taxonomy design first. |
| SM-L007 | build_progressive_async decomposition | 251-line method but the step boundaries are clean and well-commented. The entanglement with resume/freshness logic makes extraction non-trivial -- the freshness probe (step 2b, 50 lines) shares state with resume detection. Defer to next cycle when SM-L005 freshness formalization is done. |
| SM-L008 | _fetch_and_persist_section split | Entangled with checkpoint logic and manifest state. Small/large section paths share post-processing. Needs SM-L009 (SectionPersistence public API) done first. |
| SM-L009 | SectionPersistence public API | Requires design discussion about which private methods to promote. The checkpoint write path intentionally bypasses the public API to avoid marking sections COMPLETE. Needs architecture review. |
| SM-L014 | Logging migration (f-string to structured) | 40+ instances across redis.py, s3.py, tiered.py. Mechanical but large blast radius. Best done as a dedicated cycle with grep-based verification. |
| SM-L010 | Statistics pattern standardization | Requires migrating DataFrameCache from raw dicts to CacheMetrics. Cross-subsystem change affecting observability dashboards. Needs coordination with monitoring setup. |
| SM-L016 | S3 batch parallelization | Performance optimization, not refactoring. Requires adding ThreadPoolExecutor, affects concurrency behavior. Needs load testing. |
| SM-L001 (registry.py) | SchemaRegistry hardcoded imports | The registry's `_ensure_initialized()` uses hardcoded schema imports. This is the canonical registration point -- deriving from `ENTITY_TYPES` would require a schema naming convention. Leave as authoritative source. |

### Low-Priority Items (Not Addressed This Cycle)

The following LOW findings (ROI <= 4) are acknowledged but not included. They are style/cosmetic improvements that do not justify the review overhead in this cycle:

SM-L011, SM-L015, SM-L018, SM-L020, SM-L021, SM-L024 (addressed as part of RF-L04), SM-L025, SM-L026, SM-L029, SM-L030, SM-L031, SM-L032.

---

## Execution Order

```
Phase 1 (independent, any order):
  RF-L01 --> RF-L02 --> RF-L03 --> RF-L04

Phase 2 (independent of each other, depends on Phase 1 being committed):
  RF-L05 --> RF-L06 --> RF-L07 --> RF-L08

Phase 3 (depends on Phase 2 for clean diffs):
  RF-L09 --> RF-L10

Phase 4 (depends on Phase 1-2 for clean diffs):
  RF-L11
```

**Dependencies**:
- RF-L05 creates `core/datetime_utils.py`; RF-L08 creates `core/schema.py`. Both create files in `core/`. RF-L05 should go first to establish `core/__init__.py`.
- RF-L11 creates `core/entity_types.py`. Must come after RF-L05/RF-L08 so the `core/` package exists.
- RF-L09 and RF-L10 are independent of each other but both are in Phase 3 for risk sequencing.

**Rollback Points**:
- After Phase 1: All 4 commits are independently revertible
- After Phase 2: Each extraction commit is independently revertible. Reverting RF-L05 requires also reverting RF-L08 if they share `core/__init__.py`
- After Phase 3: Each decomposition is independently revertible
- After Phase 4: RF-L11 is a single commit, revertible independently

---

## Verification Commands

After each commit:
```bash
# Type checking
python -m mypy src/autom8_asana --strict

# Lint
python -m ruff check src/autom8_asana

# Unit tests (targeted by phase)
# Phase 1:
python -m pytest tests/unit/cache/test_hierarchy_warmer.py tests/unit/cache/test_unified.py -x -q
# Phase 2:
python -m pytest tests/unit/cache/ tests/unit/query/ -x -q
# Phase 3:
python -m pytest tests/unit/cache/test_unified.py tests/integration/test_unit_cascade_resolution.py -x -q
# Phase 4:
python -m pytest tests/ -x -q  # Full suite -- cross-cutting change

# Full verification (run after all phases):
python -m pytest tests/ -x
python -m mypy src/autom8_asana --strict
python -m ruff check src/autom8_asana
```

---

## Janitor Notes

1. **Commit convention**: Each RF-L task = one atomic commit. Use the suggested commit message. Include `Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>`.
2. **New files**: RF-L05 creates `core/datetime_utils.py`, RF-L08 creates `core/schema.py`, RF-L11 creates `core/entity_types.py`. All three need a `core/__init__.py` (can be empty). The `core/` directory does not exist yet -- create it with RF-L05.
3. **Import style**: This codebase uses `from __future__ import annotations` consistently. Include it in new files.
4. **Critical ordering**: RF-L05 MUST precede RF-L08 and RF-L11 (establishes `core/` package). Within each phase, order is flexible.
5. **Test before committing**: Run the phase-specific test commands. If any test fails, do NOT proceed to the next RF-L task. Investigate and fix within the same task scope, or flag for architect review.
6. **Preserve method signatures**: For RF-L09, keep `put_batch_async()` signature identical. The new private methods are internal -- no external callers.
7. **Do not touch SM-L005**: The `getattr` side-channel in QueryEngine is deliberately left alone in this cycle. RF-L07 consolidates the read to one location but does NOT change the pattern.

---

## Risk Matrix

| RF-L | Risk | Blast Radius | Failure Detection | Recovery |
|------|------|-------------|-------------------|----------|
| RF-L01 | LOW | 1 file | mypy, ruff | Revert 1 commit |
| RF-L02 | LOW | 1 file | Unit tests (6) | Revert 1 commit |
| RF-L03 | LOW | 1 file | Stats value change (acceptable) | Revert 1 commit |
| RF-L04 | LOW | 1 file | Unit tests, init log | Revert 1 commit |
| RF-L05 | LOW | 3 files + 1 new | Unit tests across subsystems | Revert 1 commit |
| RF-L06 | LOW | 1 file | Query engine tests | Revert 1 commit |
| RF-L07 | LOW | 1 file | Query engine tests | Revert 1 commit |
| RF-L08 | LOW | 2 files + 1 new | mypy (import resolution) | Revert 1 commit |
| RF-L09 | MEDIUM | 1 file (critical path) | Integration tests (2), unit tests (5+) | Revert 1 commit |
| RF-L10 | MEDIUM | 1 file | SWR rebuild integration test | Revert 1 commit |
| RF-L11 | MEDIUM | 4 files + 1 new | Full test suite, mypy | Revert 1 commit |

---

## Verification Attestation

| Source File | Lines Read | Purpose |
|-------------|-----------|---------|
| `.claude/artifacts/smell-report-cache-landscape.md` | 1-549 (full) | Input smell report |
| `src/autom8_asana/cache/tiered.py` | 1-40 | RF-L01 contract verification |
| `src/autom8_asana/cache/hierarchy_warmer.py` | 195-260 | RF-L02 contract verification |
| `src/autom8_asana/cache/dataframe/tiers/progressive.py` | 225-255, 340-370 | RF-L03, RF-L05 contract |
| `src/autom8_asana/cache/dataframe/tiers/memory.py` | 1-55, 235-255 | RF-L04 contract verification |
| `src/autom8_asana/cache/unified.py` | 440-700, 840-872 | RF-L05, RF-L09 contract |
| `src/autom8_asana/dataframes/builders/progressive.py` | 130-389, 895-931 | RF-L05 contract |
| `src/autom8_asana/query/engine.py` | 95-155, 245-295, 320-420 | RF-L06, RF-L07 contract |
| `src/autom8_asana/cache/dataframe_cache.py` | 1-80, 210-230, 545-565 | RF-L08, RF-L11 contract |
| `src/autom8_asana/dataframes/section_persistence.py` | 194-217 | RF-L08 contract |
| `src/autom8_asana/cache/dataframe/factory.py` | 125-195 | RF-L10 contract |
| `src/autom8_asana/cache/schema_providers.py` | 115-134 | RF-L11 contract |
| `src/autom8_asana/api/routes/admin.py` | 20-35 | RF-L11 contract |
| `src/autom8_asana/api/routes/resolver.py` | 250-265 | RF-L11 contract |
| `src/autom8_asana/dataframes/models/registry.py` | 75-100 | RF-L11 contract |
