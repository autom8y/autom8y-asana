# Refactoring Plan: Cache Hygiene Sprint 3

**Agent**: architect-enforcer
**Date**: 2026-02-04
**Upstream Artifact**: `.claude/artifacts/smell-report-cache-sprint3.md`
**Downstream Consumer**: janitor
**Sprint**: 3 of cache hygiene initiative

---

## Architectural Assessment

Sprint 1 and 2 resolved 15 smells across the cache subsystem. Sprint 3 addresses 6 remaining items prioritized by ROI and structural impact. The findings cluster into three root causes:

1. **Protocol incompleteness** (RF-L17, RF-L19): The `CacheProvider` protocol and `DegradedModeMixin` pattern were established in earlier sprints but not fully adopted across all backends.
2. **Encapsulation violations** (RF-L16, RF-L18): `progressive.py` reaches into `SectionPersistence` private internals for checkpoint operations, a boundary violation amplified by Sprint 2's RF-L12 decomposition.
3. **DRY violations and drift** (RF-L20, RF-L21): Duplicated validators in query models and a stale entity type constant that diverges from the canonical source.

No findings require public API changes. All refactoring preserves existing behavior.

---

## Smell Disposition

| Smell ID | Disposition | RF Task |
|----------|-------------|---------|
| SM-S3-001 | **Addressed** | RF-L16 |
| SM-S3-002 | **Addressed** | RF-L21 |
| SM-S3-003 | **Addressed** | RF-L19 |
| SM-S3-006 | **Addressed** | RF-L17 |
| SM-L008 | **Addressed** | RF-L18 |
| SM-L009 | **Subsumed** by SM-S3-001 | RF-L16 |
| SM-L015 | **Subsumed** by SM-S3-006 | RF-L17 |
| SM-L026 | **Addressed** | RF-L20 |
| SM-S3-004 | **Deferred** -- config TTL drift is documentation concern, not structural | -- |
| SM-S3-005 | **Deferred** -- inline imports may still be needed for circular dep avoidance | -- |
| SM-S3-007 | **Deferred** -- warm() stubs require feature design, not refactoring | -- |
| SM-L010 | **Deferred** -- parameter count reduced by RF-L13; ROI insufficient | -- |
| SM-L016 | **Deferred** -- S3 batch parallelization is performance work, not structural | -- |

---

## Execution Phases

```
Phase 1 (Low Risk, No Dependencies)
  RF-L17  Add clear_all_tasks to CacheProvider protocol + memory backend
  RF-L19  Add DegradedModeMixin to memory backend
  RF-L20  Extract shared wrap_flat_array validator
  RF-L21  Replace stale SUPPORTED_ENTITY_TYPES

  >>> ROLLBACK POINT A: revert Phase 1 commits independently <<<

Phase 2 (Medium Risk, Internal Boundary Change)
  RF-L16  Formalize SectionPersistence checkpoint API

  >>> ROLLBACK POINT B: revert RF-L16 commit <<<

Phase 3 (Medium Risk, Depends on RF-L16)
  RF-L18  Decompose _fetch_and_persist_section

  >>> ROLLBACK POINT C: revert RF-L18 commit <<<
```

**Dependency chain**: RF-L18 depends on RF-L16 (the new public checkpoint methods are used by the decomposed sub-methods). All Phase 1 tasks are independent of each other and of Phase 2/3.

---

## Phase 1: Low-Risk Independent Refactors

### RF-L17: Add `clear_all_tasks` to CacheProvider protocol

**Smell**: SM-S3-006 (Protocol Gap, MEDIUM)
**Classification**: Module-level -- protocol definition incomplete

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py`: `CacheProvider` protocol has no `clear_all_tasks` method
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py:478-493`: Uses `getattr(self._hot, "clear_all_tasks", None)` and `getattr(self._cold, "clear_all_tasks", None)` duck-typing
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:762`: `def clear_all_tasks(self) -> int`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:826`: `def clear_all_tasks(self) -> int`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py`: Has `clear()` but no `clear_all_tasks()`

**After State:**
- `protocols/cache.py`: `CacheProvider` protocol includes `def clear_all_tasks(self) -> int` with docstring
- `backends/memory.py`: New method `def clear_all_tasks(self) -> int` that calls `self.clear()` and returns count of cleared entries
- `tiered.py:478-493`: Replace `getattr` calls with direct `self._hot.clear_all_tasks()` and `self._cold.clear_all_tasks()`

**Invariants:**
- Redis and S3 backends already implement `clear_all_tasks() -> int` -- no changes needed
- `TieredCacheProvider.clear_all_tasks()` still returns `dict[str, int]` (wraps individual `int` returns)
- Memory backend `clear_all_tasks()` returns the count of entries cleared (simple + versioned)
- Existing error handling in `tiered.py` (try/except around each tier) preserved

**Verification:**
1. `grep -r "getattr.*clear_all_tasks" src/` returns zero matches
2. `python -c "from autom8_asana.protocols.cache import CacheProvider; print('clear_all_tasks' in dir(CacheProvider))"` returns True
3. Run: `pytest tests/ -k "clear" --no-header -q` (if tests exist for clear operations)
4. Type check: `mypy src/autom8_asana/protocols/cache.py src/autom8_asana/cache/tiered.py src/autom8_asana/cache/backends/memory.py`

**Rollback**: Revert single commit.

**Risk**: LOW. All backends already implement the method. Adding to protocol is purely definitional.

---

### RF-L19: Add DegradedModeMixin to memory backend

**Smell**: SM-S3-003 (Incomplete Pattern Adoption, MEDIUM)
**Classification**: Module-level -- inconsistent mixin adoption

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py:32`: `class EnhancedInMemoryCacheProvider:` (no mixin)
- Redis, S3, AsyncS3 all inherit `DegradedModeMixin`
- Monitoring code checking for mixin attributes would get `AttributeError` on memory backend

**After State:**
- `memory.py:32`: `class EnhancedInMemoryCacheProvider(DegradedModeMixin):`
- `memory.py` `__init__`: Add three attributes:
  ```python
  self._degraded = False
  self._last_reconnect_attempt = 0.0
  self._reconnect_interval = 30.0
  ```
- Import added: `from autom8_asana.cache.errors import DegradedModeMixin`

**Invariants:**
- `is_healthy()` still returns `True` always (memory backend never enters degraded mode)
- No calls to `enter_degraded_mode()` added -- memory backend does not degrade
- Mixin attributes present for uniform introspection by monitoring code
- All existing tests pass without modification

**Verification:**
1. `python -c "from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider; c = EnhancedInMemoryCacheProvider(); print(hasattr(c, '_degraded'), hasattr(c, 'enter_degraded_mode'))"` returns `True True`
2. `pytest tests/unit/cache/ -q --no-header`

**Rollback**: Revert single commit.

**Risk**: LOW. Adding a no-op mixin with initialized attributes. No behavioral change.

---

### RF-L20: Extract shared `_wrap_flat_array_to_and_group` validator

**Smell**: SM-L026 (DRY Violation, MEDIUM)
**Classification**: Local -- duplicated logic within one file

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:147-153`: `AggregateRequest.wrap_flat_array` validator on `where`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:157-163`: `AggregateRequest.wrap_having_flat_array` validator on `having`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:208-217`: `RowsRequest.wrap_flat_array` validator on `where`

All three contain identical logic:
```python
if isinstance(v, list):
    if len(v) == 0:
        return None
    return {"and": v}
return v
```

**After State:**
- New module-level function at top of `models.py` (after imports, before classes):
  ```python
  def _wrap_flat_array_to_and_group(v: Any) -> Any:
      """Normalize a bare list of predicates into an AND group.

      Used by Pydantic field validators on ``where`` and ``having`` fields.
      - Bare list -> ``{"and": v}``
      - Empty list -> ``None`` (no filter)
      - Other -> passthrough

      Args:
          v: Raw input value from request body.

      Returns:
          Normalized predicate value.
      """
      if isinstance(v, list):
          if len(v) == 0:
              return None
          return {"and": v}
      return v
  ```
- All three validators become one-line delegations:
  ```python
  @field_validator("where", mode="before")
  @classmethod
  def wrap_flat_array(cls, v: Any) -> Any:
      """Auto-wrap bare list to AND group (FR-001 sugar)."""
      return _wrap_flat_array_to_and_group(v)
  ```

**Invariants:**
- All `mode="before"` decorators preserved
- All `@classmethod` decorators preserved
- Same validation semantics: bare list wraps to `{"and": v}`, empty list becomes `None`, non-list passes through
- Method names unchanged (public API for Pydantic)
- No new files created

**Verification:**
1. `grep -c "_wrap_flat_array_to_and_group" src/autom8_asana/query/models.py` returns 4 (1 def + 3 calls)
2. `pytest tests/ -k "wrap_flat" or tests/ -k "aggregate" or tests/ -k "rows"` -- all pass
3. Manual: `from autom8_asana.query.models import AggregateRequest; AggregateRequest.model_validate({"group_by": ["x"], "aggregations": [{"column": "y", "agg": "sum"}], "where": [{"field": "a", "op": "eq", "value": 1}]})` -- `where` field should be `AndGroup`

**Rollback**: Revert single commit.

**Risk**: LOW. Pure extraction within a single file. Pydantic validators preserved.

---

### RF-L21: Replace stale `SUPPORTED_ENTITY_TYPES` with canonical import

**Smell**: SM-S3-002 (Drift Risk, LOW)
**Classification**: Boundary-level -- data source divergence from canonical module

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py:257`:
  ```python
  SUPPORTED_ENTITY_TYPES = {"unit", "business", "offer", "contact"}
  ```
  Missing `"asset_edit"` (5th entity type in canonical `ENTITY_TYPES`)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_types.py:10-16`:
  ```python
  ENTITY_TYPES: list[str] = ["unit", "business", "offer", "contact", "asset_edit"]
  ```

**After State:**
- `resolver.py:257` area replaced with:
  ```python
  from autom8_asana.core.entity_types import ENTITY_TYPES

  # Fallback set for _get_supported_entity_types() when dynamic discovery fails.
  # Derived from canonical ENTITY_TYPES to prevent drift (was SM-S3-002).
  SUPPORTED_ENTITY_TYPES = set(ENTITY_TYPES)
  ```
- If `ENTITY_TYPES` is already imported elsewhere in the file, reuse that import

**Invariants:**
- `_get_supported_entity_types()` fallback path now returns 5 items instead of 4
- This is a **bug fix** in the fallback path (asset_edit was missing), but the primary discovery path already returns all 5
- The fallback only fires when dynamic discovery fails entirely
- Return type remains `set[str]`

**Verification:**
1. `python -c "from autom8_asana.api.routes.resolver import SUPPORTED_ENTITY_TYPES; print(SUPPORTED_ENTITY_TYPES)"` includes `"asset_edit"`
2. `grep "SUPPORTED_ENTITY_TYPES" src/autom8_asana/api/routes/resolver.py` shows single assignment using `set(ENTITY_TYPES)`
3. `pytest tests/ -k "resolver" -q --no-header`

**Rollback**: Revert single commit.

**Risk**: LOW. The primary path (dynamic discovery) is unchanged. Only the fallback path gains `asset_edit`.

**Note**: This technically fixes a latent bug in the fallback path. The Janitor should verify that `asset_edit` entity type is safe in the resolver context (i.e., the resolver can actually resolve asset_edit entities). If not, add a comment explaining the intentional divergence instead.

---

## Phase 2: SectionPersistence Boundary Repair

### RF-L16: Formalize SectionPersistence checkpoint API

**Smell**: SM-S3-001 + SM-L009 (Encapsulation Violation, HIGH)
**Classification**: Boundary-level -- cross-class private attribute access

**Before State:**
`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` accesses 5 private members of `SectionPersistence`:

1. `self._persistence._make_section_key(project_gid, section_gid)` at line 807
2. `self._persistence._s3_client.put_object_async(...)` at line 813
3. `self._persistence._get_manifest_lock(project_gid)` at line 881
4. `self._persistence._manifest_cache[project_gid]` at line 895
5. `self._persistence._save_manifest_async(manifest)` at line 896

These occur in two methods:
- `_write_checkpoint` (lines 772-861): Writes checkpoint parquet to S3 without marking section COMPLETE
- `_update_checkpoint_metadata` (lines 863-896): Updates manifest SectionInfo with checkpoint progress

**After State:**

Add two new public methods to `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` class `SectionPersistence`:

```python
async def write_checkpoint_async(
    self,
    project_gid: str,
    section_gid: str,
    df: pl.DataFrame,
    *,
    pages_fetched: int,
    rows_fetched: int,
) -> bool:
    """Write a checkpoint parquet to S3 without marking the section complete.

    Unlike write_section_async(), this writes the DataFrame at the section's
    S3 key but does NOT transition the section to COMPLETE status. The section
    remains IN_PROGRESS with updated checkpoint metadata.

    Args:
        project_gid: Asana project GID.
        section_gid: Section GID being checkpointed.
        df: Polars DataFrame with accumulated rows so far.
        pages_fetched: Total API pages fetched to this point.
        rows_fetched: Total rows accumulated to this point.

    Returns:
        True if checkpoint written and metadata updated successfully.
    """
    if self._polars_module is None:
        logger.warning("polars not available, cannot write checkpoint")
        return False

    # Serialize DataFrame to parquet
    buffer = io.BytesIO()
    df.write_parquet(buffer)
    buffer.seek(0)
    parquet_bytes = buffer.read()

    key = self._make_section_key(project_gid, section_gid)
    result = await self._s3_client.put_object_async(
        key=key,
        body=parquet_bytes,
        content_type="application/octet-stream",
        metadata={
            "project-gid": project_gid,
            "section-gid": section_gid,
            "row-count": str(len(df)),
            "checkpoint": "true",
            "pages-fetched": str(pages_fetched),
        },
    )

    if result.success:
        await self.update_checkpoint_metadata_async(
            project_gid, section_gid,
            pages_fetched=pages_fetched,
            rows_fetched=rows_fetched,
        )

    return result.success


async def update_checkpoint_metadata_async(
    self,
    project_gid: str,
    section_gid: str,
    *,
    pages_fetched: int,
    rows_fetched: int,
) -> None:
    """Update manifest SectionInfo with checkpoint progress.

    Uses the per-project manifest lock to safely update checkpoint
    fields without race conditions.

    Args:
        project_gid: Asana project GID.
        section_gid: Section GID being checkpointed.
        pages_fetched: Total pages fetched so far.
        rows_fetched: Total rows accumulated so far.
    """
    lock = self._get_manifest_lock(project_gid)
    async with lock:
        manifest = await self.get_manifest_async(project_gid)
        if manifest is None:
            return

        section_info = manifest.sections.get(section_gid)
        if section_info is None:
            return

        section_info.last_fetched_offset = pages_fetched
        section_info.rows_fetched = rows_fetched
        section_info.chunks_checkpointed += 1

        self._manifest_cache[project_gid] = manifest
        await self._save_manifest_async(manifest)
```

Then update `progressive.py`:

- `_write_checkpoint`: Replace lines 807-824 (S3 key generation + put_object) with:
  ```python
  checkpoint_df = pl.DataFrame(coerced_rows, schema=self._schema.to_polars_schema())
  result_success = await self._persistence.write_checkpoint_async(
      self._project_gid,
      section_gid,
      checkpoint_df,
      pages_fetched=pages_fetched,
      rows_fetched=len(checkpoint_df),
  )
  ```
  The `_update_checkpoint_metadata` call (line 827-829) is removed since it is now handled inside `write_checkpoint_async`.

- `_update_checkpoint_metadata` in `progressive.py`: **Remove entirely** -- this method is now on `SectionPersistence`.

**Invariants:**
- Same S3 key format: `{prefix}{project_gid}/sections/{section_gid}.parquet`
- Same metadata headers on S3 object: `project-gid`, `section-gid`, `row-count`, `checkpoint`, `pages-fetched`
- Same manifest locking behavior (per-project asyncio.Lock)
- Same manifest update semantics (last_fetched_offset, rows_fetched, chunks_checkpointed)
- Section remains IN_PROGRESS after checkpoint (not marked COMPLETE)
- `progressive.py` no longer accesses any `_`-prefixed attributes of `SectionPersistence`

**Verification:**
1. `grep -n "self._persistence._" src/autom8_asana/dataframes/builders/progressive.py` returns zero matches
2. `grep -n "write_checkpoint_async\|update_checkpoint_metadata_async" src/autom8_asana/dataframes/section_persistence.py` shows both new methods
3. `pytest tests/ -k "checkpoint or section_persist" -q --no-header`
4. `mypy src/autom8_asana/dataframes/section_persistence.py src/autom8_asana/dataframes/builders/progressive.py`

**Rollback**: Revert single commit. `progressive.py` methods restored to direct private attribute access.

**Risk**: MEDIUM. Changes two files with a behavioral contract. The S3 write and manifest update must produce identical results. Careful attention to the metadata dict keys and the manifest lock acquire sequence.

---

## Phase 3: Progressive Builder Decomposition

### RF-L18: Decompose `_fetch_and_persist_section`

**Smell**: SM-L008 (Complexity, MEDIUM)
**Classification**: Local -- single method with cyclomatic complexity ~15, 247 lines
**Dependency**: Requires RF-L16 (uses `write_checkpoint_async` from Phase 2)

**Before State:**
`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py:523-770`

Single method `_fetch_and_persist_section` handling:
- Resume detection + checkpoint loading (lines 555-593)
- PageIterator creation + resume skip (lines 596-620)
- First page fetch + size detection (lines 622-638)
- Empty section handling (lines 640-653)
- Small section passthrough (lines 655-657)
- Large section paced iteration with checkpoints (lines 659-695)
- Store population (lines 698-699)
- Task-to-DataFrame conversion (lines 716-725)
- Freshness metadata computation (lines 728-735)
- S3 write + manifest update (lines 738-749)
- Error handling + manifest failure marking (lines 751-770)

**After State:**

The main method becomes a ~50-line orchestrator calling 5 private methods:

```python
async def _fetch_and_persist_section(
    self, section_gid, section, section_index, total_sections
) -> bool:
    """Fetch tasks for a section, build DataFrame, and persist to S3."""
    section_start = time.perf_counter()
    try:
        await self._persistence.update_manifest_section_async(
            self._project_gid, section_gid, SectionStatus.IN_PROGRESS,
        )

        checkpoint_df, resume_offset = await self._load_checkpoint(
            section_gid, section_index,
        )

        iterator = self._client.tasks.list_async(
            section=section_gid, opt_fields=BASE_OPT_FIELDS,
        )

        if resume_offset > 0:
            await self._skip_resumed_pages(iterator, section_gid, resume_offset)

        first_page_tasks = await self._fetch_first_page(section_gid, iterator)

        if not first_page_tasks:
            # Empty section
            from autom8_asana.dataframes.builders.freshness import compute_gid_hash
            await self._persistence.update_manifest_section_async(
                self._project_gid, section_gid, SectionStatus.COMPLETE,
                rows=0, gid_hash=compute_gid_hash([]),
            )
            return True

        is_large = len(first_page_tasks) == 100
        if is_large:
            tasks = await self._fetch_large_section(
                section_gid, iterator, first_page_tasks,
            )
        else:
            tasks = first_page_tasks

        if self._store is not None and tasks:
            await self._populate_store_with_tasks(tasks)

        # ... logging ...

        section_df, gid_hash, watermark = await self._build_section_dataframe(tasks)
        self._section_dfs[section_gid] = section_df

        return await self._persist_section(
            section_gid, section_df, gid_hash, watermark,
        )

    except Exception as e:
        # ... error logging + manifest failure marking ...
        return False
```

**Extracted methods (all private, on same class):**

1. **`_load_checkpoint(section_gid, section_index) -> tuple[pl.DataFrame | None, int]`**
   - Inputs: section_gid, section_index (for logging)
   - Outputs: (checkpoint_df or None, resume_offset)
   - Moves lines 556-593
   - Reads `self._manifest.sections.get(section_gid)` for resume detection
   - Calls `self._persistence.read_section_async()` to load checkpoint

2. **`_skip_resumed_pages(iterator, section_gid, resume_offset) -> None`**
   - Inputs: PageIterator, section_gid, target offset
   - Moves lines 602-620
   - Async iteration to skip past already-fetched pages

3. **`_fetch_first_page(section_gid, iterator) -> list[Task]`**
   - Inputs: section_gid, PageIterator
   - Output: up to 100 tasks from first page
   - Moves lines 622-638
   - Logs `large_section_detected` with pacing status

4. **`_fetch_large_section(section_gid, iterator, first_page_tasks) -> list[Task]`**
   - Inputs: section_gid, PageIterator, first page tasks
   - Output: all tasks (first page + remaining pages)
   - Moves lines 660-695
   - Handles pacing pauses and checkpoint writes
   - Calls `self._write_checkpoint()` (which now delegates to `SectionPersistence.write_checkpoint_async` per RF-L16)

5. **`_build_section_dataframe(tasks) -> tuple[pl.DataFrame, str, datetime | None]`**
   - Inputs: list of Task objects
   - Output: (DataFrame, gid_hash, watermark)
   - Moves lines 716-735
   - task_to_dict, extract_rows, coerce_rows_to_schema, DataFrame construction
   - Computes gid_hash and watermark from section data

6. **`_persist_section(section_gid, section_df, gid_hash, watermark) -> bool`**
   - Inputs: section_gid, DataFrame, gid_hash, watermark
   - Output: success boolean
   - Moves lines 741-749
   - Delegates to `self._persistence.write_section_async()`

**Invariants:**
- Same fetch order: resume detection -> skip -> first page -> remaining pages
- Same checkpointing cadence: every `CHECKPOINT_EVERY_N_PAGES` pages
- Same pacing cadence: pause every `PACE_PAGES_PER_PAUSE` pages
- Same error handling: outer try/except catches all exceptions, marks section FAILED
- Same empty section handling: 0-row COMPLETE with empty gid_hash
- Same store population: `_populate_store_with_tasks` called after all tasks fetched
- All existing logging messages preserved (same event names, same extra fields)
- Method signature of `_fetch_and_persist_section` unchanged

**Verification:**
1. Line count of `_fetch_and_persist_section` < 60 lines
2. `grep -c "async def _load_checkpoint\|async def _skip_resumed_pages\|async def _fetch_first_page\|async def _fetch_large_section\|async def _build_section_dataframe\|async def _persist_section" src/autom8_asana/dataframes/builders/progressive.py` returns 6
3. `pytest tests/ -k "progressive or section" -q --no-header` -- all pass
4. `pytest tests/ -k "fetch_and_persist" -q --no-header` -- if integration tests exist
5. Verify total line count of progressive.py is similar (extraction adds method signatures but removes nesting)

**Rollback**: Revert single commit. Original monolithic method restored.

**Risk**: MEDIUM. This is the largest refactoring in the sprint. The decomposition must preserve exact control flow ordering, especially:
- Resume offset skip must complete before first page fetch
- Store population must happen before DataFrame construction (for cascade resolution)
- Checkpoint writes must happen at the same page boundaries
- The outer try/except must still catch errors from all sub-methods

---

## Risk Matrix

| RF | Phase | Blast Radius | Files Changed | Failure Detection | Rollback Cost |
|----|-------|-------------|---------------|-------------------|---------------|
| RF-L17 | 1 | 3 files (protocol, memory, tiered) | 3 | Type checker + unit tests | Single commit revert |
| RF-L19 | 1 | 1 file (memory backend) | 1 | Attribute introspection test | Single commit revert |
| RF-L20 | 1 | 1 file (query/models.py) | 1 | Pydantic validation tests | Single commit revert |
| RF-L21 | 1 | 1 file (resolver.py) | 1 | Entity type set assertion | Single commit revert |
| RF-L16 | 2 | 2 files (section_persistence, progressive) | 2 | Integration tests + grep for private access | Single commit revert |
| RF-L18 | 3 | 1 file (progressive.py) | 1 | Integration tests + line count check | Single commit revert |

---

## Commit Conventions

Each RF task gets exactly one commit. Commit message format:

```
refactor(<scope>): <description>

<body explaining what changed and why>

Addresses: SM-<id>
```

Scopes:
- RF-L17: `cache` -- "add clear_all_tasks to CacheProvider protocol"
- RF-L19: `cache` -- "add DegradedModeMixin to memory backend"
- RF-L20: `query` -- "extract shared wrap_flat_array validator in query models"
- RF-L21: `resolver` -- "replace stale SUPPORTED_ENTITY_TYPES with canonical import"
- RF-L16: `persistence` -- "formalize SectionPersistence checkpoint API"
- RF-L18: `builders` -- "decompose _fetch_and_persist_section into focused methods"

---

## Janitor Notes

1. **Phase 1 tasks can be done in any order.** If one fails review, the others are unaffected.
2. **RF-L17 and RF-L19 both touch memory.py.** If done in the same commit session, combine the import and class changes. If separate commits, ensure no merge conflict on the class declaration line. Recommended: do RF-L19 first (adds mixin to class), then RF-L17 (adds method to class).
3. **RF-L16 must be complete and passing before starting RF-L18.** The decomposed `_write_checkpoint` in RF-L18 depends on the public API from RF-L16.
4. **RF-L18 is the most judgment-intensive task.** The method boundaries described above are prescriptive. If a sub-method requires more than the specified inputs, that is a sign the contract needs updating -- pause and verify rather than adding extra parameters.
5. **RF-L21 note on asset_edit**: Verify that the resolver can actually handle `asset_edit` entities before including it in the fallback set. If the resolver has no schema/project registered for `asset_edit`, the dynamic discovery path already excludes it and the fallback should match. In that case, use `set(ENTITY_TYPES)` but add a comment noting the fallback may include unsupported types that the dynamic path correctly filters.
6. **Test commands**: Run `pytest tests/ -x -q --no-header` after each commit. If no tests exist for a specific path, note it in the commit body as a gap for future work.
7. **Type checking**: Run `mypy` on changed files after each commit if the project has mypy configured.

---

## Verification Attestation

| # | File | Read | Line Ranges Verified |
|---|------|------|---------------------|
| 1 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` | Yes | Full file (1-240) |
| 2 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` | Yes | Lines 470-499 |
| 3 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py` | Yes | Full file (1-433) |
| 4 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py` | Yes | Full file (1-249) |
| 5 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py` | Yes | Lines 1-40, 250-310 |
| 6 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes | Full file (1-902) |
| 7 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Yes | Lines 1-40, 520-910 |
| 8 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_types.py` | Yes | Full file (1-23) |
| 9 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/errors.py` | Yes | Full file (1-167) |
| 10 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Yes | Line 762 (grep) |
| 11 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Yes | Line 826 (grep) |

All before-state references verified against actual file contents via Read tool. No findings are based on assumptions.
