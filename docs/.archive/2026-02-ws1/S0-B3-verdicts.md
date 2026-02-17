# Sprint 0, Batch 3: Cache/Storage & Dataframes -- Spike Verdicts

**Initiative**: INIT-RUNTIME-OPT-002 (Runtime Efficiency Remediation v2)
**Phase**: Sprint 0 (Spike Investigation)
**Author**: Architect
**Date**: 2026-02-15

---

## S0-SPIKE-03: Sequential Section Reads During Merge

**Verdict**: GO

### Evidence

#### (a) How are sections read? What async pattern is used?

`read_all_sections_async` in `section_persistence.py:585-620` reads all complete sections for a project. The code is:

```python
async def read_all_sections_async(
    self,
    project_gid: str,
) -> list[pl.DataFrame]:
    manifest = await self.get_manifest_async(project_gid)
    if manifest is None:
        return []

    complete_sections = manifest.get_complete_section_gids()
    if not complete_sections:
        return []

    dfs = []
    for section_gid in complete_sections:
        df = await self.read_section_async(project_gid, section_gid)
        if df is not None:
            dfs.append(df)

    return dfs
```

**This is a plain sequential `for` loop with `await` inside.** There is no `asyncio.gather`, no semaphore, no concurrent execution. Each section is read one at a time, waiting for the previous to complete before starting the next.

#### (b) What determines section count per project?

Section count is determined by the Asana project structure. From production context in the prompt: **20+ sections per project is common for the largest projects.** The manifest tracks all sections; only `COMPLETE` sections are read by this method.

#### (c) Per-section read cost (the full read path)

Each `read_section_async` (line 568-583) delegates to `self._storage.load_section(project_gid, section_gid)`, which is `S3DataFrameStorage.load_section` (storage.py:999-1016):

```python
async def load_section(self, project_gid, section_gid):
    data = await self._get_object(self._section_key(project_gid, section_gid))
    if data is None:
        return None
    return self._deserialize_parquet(data)
```

The `_get_object` method (storage.py:481-550) makes an S3 GET request via `asyncio.to_thread()` wrapped in a `RetryOrchestrator`:

```python
async def _get_object(self, key: str) -> bytes | None:
    ...
    def _do_get() -> bytes:
        response = client.get_object(Bucket=..., Key=key)
        body_bytes = response["Body"].read()
        return body_bytes

    data = await self._retry.execute_with_retry_async(
        lambda: asyncio.to_thread(_do_get),
        operation_name=f"s3_get:{key}",
    )
    ...
```

**Per-section cost**: One S3 GET request (30-200ms depending on object size and network) + parquet deserialization (~5-20ms). The S3 GET is the dominant cost. For 20 sections sequentially: 20 x 100ms = ~2 seconds of wall-clock time waiting on S3 I/O.

#### (d) Is there shared mutable state between section reads?

**No.** Each `read_section_async` call:
1. Receives `project_gid` and `section_gid` (immutable strings)
2. Calls `_storage.load_section()` which creates an independent S3 GET
3. Returns an independent `pl.DataFrame`

The only shared state is:
- `self._storage` (the S3DataFrameStorage instance) -- thread-safe by design. Uses a single boto3 client with internal connection pooling, and all operations go through `asyncio.to_thread()` which dispatches to the thread pool. Thread safety is explicitly documented (storage.py:272-275).
- `self._manifest_cache` -- read-only during `read_all_sections_async` (the manifest is read once upfront and not modified).

**There is zero shared mutable state between section reads. Parallelization is safe.**

#### (e) Is there already an asyncio.gather or similar pattern?

**No.** Confirmed by code inspection -- the method uses a plain `for` loop. No `asyncio.gather`, no `asyncio.create_task`, no `gather_with_limit`, no concurrent pattern of any kind.

### Quantitative Assessment

| Sections | Sequential (100ms/section) | Parallel gather(5) | Speedup |
|----------|---------------------------|---------------------|---------|
| 5 | 500ms | ~100ms | 5x |
| 10 | 1000ms | ~200ms | 5x |
| 20 | 2000ms | ~400ms | 5x |
| 30 | 3000ms | ~600ms | 5x |

The semaphore bound of 5 limits concurrent S3 GETs to avoid S3 throttling or exhausting the thread pool. With `asyncio.to_thread()` dispatching to the default thread pool (typically 8 workers), 5 concurrent S3 requests is conservative and safe.

### If GO -- Implementation Sketch

Replace the sequential loop in `read_all_sections_async` with `gather_with_semaphore` (the DRY utility from the prompt):

```python
async def read_all_sections_async(self, project_gid: str) -> list[pl.DataFrame]:
    manifest = await self.get_manifest_async(project_gid)
    if manifest is None:
        return []

    complete_sections = manifest.get_complete_section_gids()
    if not complete_sections:
        return []

    # Parallel section reads with bounded concurrency
    results = await gather_with_semaphore(
        [self.read_section_async(project_gid, gid) for gid in complete_sections],
        concurrency=5,
        return_exceptions=True,
        label="read_all_sections",
    )

    dfs = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("section_read_failed", error=str(result))
        elif result is not None:
            dfs.append(result)

    logger.info(
        "read_all_sections_completed",
        extra={
            "project_gid": project_gid,
            "sections_read": len(dfs),
            "total_complete": len(complete_sections),
        },
    )
    return dfs
```

Key design points:
1. Use `gather_with_semaphore` (from `core/concurrency.py`) with `concurrency=5`
2. `return_exceptions=True` preserves the existing graceful degradation -- if one section fails, others still succeed
3. Filter results: skip exceptions and None values (same as current behavior)
4. The downstream consumer (`merge_sections_to_dataframe_async` at line 624) receives the same `list[pl.DataFrame]` -- no API change

### Risks

- **Low**: S3 throttling with 5 concurrent GETs. S3 supports thousands of GET requests per second per prefix partition. 5 concurrent is negligible.
- **Low**: Thread pool saturation. The default `asyncio.to_thread()` pool has 8+ workers. 5 concurrent section reads leave headroom for other async operations.
- **Negligible**: Memory. All sections were already loaded into memory sequentially; parallel loading has the same peak memory (all DataFrames in `dfs` list).

### Affected Files

- `src/autom8_asana/dataframes/section_persistence.py` (primary change: `read_all_sections_async`)
- `src/autom8_asana/core/concurrency.py` (new DRY utility, shared across IMP-03/05/08/09/11)
- `tests/unit/dataframes/test_section_persistence.py` (update tests for parallel behavior)

---

## S0-SPIKE-04: Checkpoint Re-Extraction Amplification

**Verdict**: GO

### Evidence

#### (a) What does _write_checkpoint extract?

`_write_checkpoint` in `progressive.py:980-1048` performs:

```python
async def _write_checkpoint(self, section_gid, tasks, pages_fetched):
    task_dicts = [self._task_to_dict(task) for task in tasks]   # Step 1
    rows = await self._extract_rows(task_dicts)                  # Step 2
    coerced_rows = coerce_rows_to_schema(rows, self._schema)    # Step 3
    checkpoint_df = pl.DataFrame(                                # Step 4
        coerced_rows, schema=self._schema.to_polars_schema()
    )
    success = await self._persistence.write_checkpoint_async(...)  # Step 5 (S3 write)
```

It receives the **entire `tasks` list** (all accumulated tasks so far), converts ALL of them to dicts, extracts ALL rows, coerces ALL rows, and builds a complete DataFrame.

#### (b) Does it re-extract ALL accumulated tasks or only new ones?

**ALL accumulated tasks.** The `tasks` parameter is `all_tasks` from `_fetch_large_section` (line 911):

```python
# Checkpoint: persist every N pages
if pages_fetched % CHECKPOINT_EVERY_N_PAGES == 0:
    await self._write_checkpoint(section_gid, all_tasks, pages_fetched)
```

And `all_tasks` starts with `first_page_tasks` and grows with each page:

```python
all_tasks: list[Task] = list(first_page_tasks)
async for task in iterator:
    all_tasks.append(task)
```

So at checkpoint N, `all_tasks` contains tasks from pages 1 through N*50. Every checkpoint re-processes the entire accumulation.

#### (c) Extraction cost per task

The extraction pipeline has three stages:

**Stage 1: `_task_to_dict(task)`** (line 1050-1077):
- Calls `task.model_dump()` -- Pydantic serialization of ~12 fields
- Cost: ~20-50 microseconds per task (Pydantic v2 model_dump for Task model)

**Stage 2: `_extract_rows(task_dicts)`** (line 1079-1093):
- Delegates to `DataFrameViewPlugin._extract_rows_async` which uses `gather_with_limit` with concurrent extraction
- Each row extraction iterates over schema columns (12-23 depending on entity type)
- Cost: ~40 microseconds per task for column extraction (no I/O in checkpoint context since tasks are local dicts)

**Stage 3: `coerce_rows_to_schema(rows, schema)`**:
- Type coercion for each field in each row
- Cost: ~10-20 microseconds per task

**Total per task: ~70-110 microseconds.** Dominated by dict operations and Pydantic serialization.

#### (d) Quantitative amplification analysis

Configuration (from config.py):
- `CHECKPOINT_EVERY_N_PAGES = 50`
- `ASANA_PAGE_SIZE = 100`
- Tasks per checkpoint interval: 50 pages x 100 tasks = 5000 tasks

For a 5000-task section (1 checkpoint at page 50, then final build):

| Operation | Tasks re-extracted | Cost (at ~90us/task) |
|-----------|-------------------|---------------------|
| Checkpoint at page 50 | 5000 | 450ms |
| Final `_build_section_dataframe` | 5000 | 450ms |
| **Total extractions** | **10,000** | **900ms** |
| **Necessary extractions** | **5,000** | **450ms** |
| **Waste** | **5,000 (100%)** | **450ms** |

For a larger section (30k tasks, 6 checkpoints per the prompt):

| Checkpoint # | Pages | Total tasks | Extraction cost |
|-------------|-------|-------------|-----------------|
| CP1 (page 50) | 50 | 5,000 | 450ms |
| CP2 (page 100) | 100 | 10,000 | 900ms |
| CP3 (page 150) | 150 | 15,000 | 1,350ms |
| CP4 (page 200) | 200 | 20,000 | 1,800ms |
| CP5 (page 250) | 250 | 25,000 | 2,250ms |
| CP6 (page 300) | 300 | 30,000 | 2,700ms |
| Final build | - | 30,000 | 2,700ms |
| **Total** | | **135,000** | **~12,150ms** |
| **Necessary** | | **30,000** | **2,700ms** |
| **Amplification** | | **4.5x** | **~9.5 seconds wasted** |

The amplification factor is `sum(k for k in range(1, N+1)) / N` where N is the checkpoint count, which equals `(N+1)/2`. For 6 checkpoints: 3.5x amplification on extraction alone. The final build adds another full extraction pass.

#### (e) How often are checkpoints written?

Checkpoints fire every 50 pages (CHECKPOINT_EVERY_N_PAGES=50). With ASANA_PAGE_SIZE=100, that is every 5000 tasks. For the confirmed production context of "5000+ tasks, 20+ sections," a single large section triggers 1+ checkpoints. Larger sections (30k tasks) trigger 6 checkpoints with severe amplification.

#### (f) Can deltas replace full re-extraction?

**Yes.** The key insight is that `_write_checkpoint` builds a complete DataFrame from scratch each time. A delta approach would:

1. Maintain `self._last_checkpoint_index = 0` tracking where the last checkpoint ended
2. At checkpoint time, only extract tasks from `tasks[self._last_checkpoint_index:]`
3. Build the new-rows DataFrame and concatenate with the previous checkpoint DataFrame (already stored in `self._section_dfs[section_gid]`)
4. Update `self._last_checkpoint_index = len(tasks)`

There are **no ordering dependencies** between rows. Each task extracts independently. The final DataFrame is a vertical concatenation of rows -- order is preserved by appending new rows after existing ones.

There is **no accumulated state** in the extraction: `_task_to_dict`, `_extract_rows`, and `coerce_rows_to_schema` are all pure functions of their input task. No task's extraction depends on any other task's extraction result.

### If GO -- Implementation Sketch

```
Delta checkpoint approach:

1. Add instance state:
   - self._checkpoint_df: pl.DataFrame | None = None
   - self._checkpoint_task_count: int = 0

2. Modify _write_checkpoint:
   - Only extract tasks[self._checkpoint_task_count:]
   - Build delta_df from new tasks only
   - Concatenate: checkpoint_df = pl.concat([self._checkpoint_df, delta_df])
     (or just delta_df if first checkpoint)
   - Store: self._checkpoint_df = checkpoint_df
   - Update: self._checkpoint_task_count = len(tasks)
   - Write checkpoint_df to S3 (same as before)

3. Modify _build_section_dataframe:
   - If self._checkpoint_df exists and self._checkpoint_task_count < len(tasks):
     Extract only tasks[self._checkpoint_task_count:]
     Concatenate with checkpoint_df
   - Else: full extraction (same as current)

4. Key invariant: final DataFrame is identical to current behavior
   (same rows, same order, same types)
```

This reduces extraction from O(N*C) to O(N) where C is checkpoint count, eliminating ~4.5x amplification for 6-checkpoint sections.

### Risks

- **Low**: DataFrame concatenation order must preserve task order. `pl.concat` preserves row order by default. Verify with tests.
- **Low**: Memory. The delta approach stores an additional reference to the checkpoint DataFrame. But `self._section_dfs[section_gid]` already stores this (line 1028), so the memory overhead is a single reference assignment.
- **Medium**: If task extraction has side effects (e.g., populating a shared resolver cache), extracting only deltas could miss cache warming for earlier tasks. **Mitigated**: `_extract_rows` in the progressive builder goes through `DataFrameViewPlugin._extract_rows_async` which processes each task independently. The `_populate_store_with_tasks` call happens separately before any checkpoint (line 635-636).

### Affected Files

- `src/autom8_asana/dataframes/builders/progressive.py` (modify `_write_checkpoint`, `_build_section_dataframe`, add delta tracking state)
- `tests/unit/dataframes/builders/test_progressive.py` (add delta checkpoint tests, verify concatenation order)

---

## S0-SPIKE-08: S3 Batch GET Is Sequential

**Verdict**: NO-GO

### Evidence

#### (a) How does S3 `get_batch` work? Is it truly sequential?

`S3CacheProvider.get_batch` (s3.py:541-570) is a synchronous method that loops over keys:

```python
def get_batch(self, keys, entry_type):
    result = {}
    if not keys:
        return result
    if self._degraded:
        return {key: None for key in keys}

    for key in keys:
        result[key] = self.get_versioned(key, entry_type)
    return result
```

Each `get_versioned` call makes one synchronous S3 GET request via boto3. **Yes, it is truly sequential.**

#### (b) How often does the cold-start S3 path execute?

The S3 `get_batch` is called from `TieredCacheProvider.get_batch` (tiered.py:276-339) ONLY when the Redis hot tier has misses:

```python
def get_batch(self, keys, entry_type):
    # Check hot tier first
    result = self._hot.get_batch(keys, entry_type)

    if not self.s3_enabled or self._cold is None:
        return result

    # Find keys that missed in hot tier
    missed_keys = [k for k, v in result.items() if v is None]
    if not missed_keys:
        return result

    # Check cold tier for missed keys
    cold_results = self._cold.get_batch(missed_keys, entry_type)
    ...
```

**The S3 path only fires when Redis misses occur.** Redis misses happen:
1. **Cold start**: After container restart, before cache warming populates Redis
2. **TTL expiration**: When Redis entries expire before S3 entries
3. **Eviction**: When Redis memory pressure evicts entries

In steady-state production, the Redis hot tier serves the vast majority of reads. S3 is the durability tier, accessed mainly during cold starts.

#### (c) Critical architectural observation: the entire call chain is synchronous

This is the key finding that changes the analysis. `TieredCacheProvider.get_batch` is a **synchronous method** (tiered.py:276). It calls `self._hot.get_batch()` (sync) and `self._cold.get_batch()` (sync). The callers -- `UnifiedTaskStore.get_batch_async` (unified.py:190) -- call `self.cache.get_batch(gids, EntryType.TASK)` directly without `await`, meaning the sync S3 calls **block the event loop**.

Parallelizing S3 GETs within `get_batch` using a `ThreadPoolExecutor` would require either:
1. Making `get_batch` async (breaking the `CacheProvider` protocol signature used by both Redis and S3)
2. Using `asyncio.to_thread()` which requires being called from an async context (but `get_batch` is sync)
3. Using a `concurrent.futures.ThreadPoolExecutor` directly within the sync method

Option 3 is the only viable one that preserves the sync interface, but:
- Introduces thread pool management inside a cache backend
- Creates a thread pool per S3CacheProvider instance
- The current S3 client is documented as thread-safe (s3.py:74-78), but concurrent S3 GETs from a shared boto3 client can hit connection pool limits
- Adds complexity for a path that fires infrequently

#### (d) Batch size and frequency analysis

The callers of `TieredCacheProvider.get_batch`:
- `UnifiedTaskStore.get_batch_async` -- called for task batches
- `staleness.py:109` -- called for freshness checks
- `autom8_adapter.py:272` -- called for entity resolution
- `unified.py:736,777` -- called for parent chains and entity lists

Typical batch sizes for S3 misses after Redis check:
- Parent chain lookups: 1-5 GIDs (most cached in Redis from hierarchy warming)
- Batch task lookups: 10-50 GIDs (but most are Redis hits)
- Cold-start scenario: potentially 100+ GIDs (but this is a one-time startup cost)

For the S3 path to fire with significant batch sizes, you need a cold start or mass TTL expiration. Both are infrequent events.

#### (e) Comparison with DataFrameStorage pattern

The `S3DataFrameStorage` (storage.py) correctly uses `asyncio.to_thread()` for S3 operations, enabling concurrent async access. The `S3CacheProvider` (cache/backends/s3.py) uses raw synchronous boto3. Aligning these would be a larger refactoring of the CacheProvider protocol -- a worthwhile architectural improvement but beyond the scope of a single parallelization fix.

### Verdict Rationale: NO-GO

Three factors drive the NO-GO:

1. **Frequency**: The S3 cold path fires only on Redis misses, which are rare in steady state. Cold starts happen at container restart; the prompt's threshold of ">5 times/day" likely fails for the cache batch path specifically (as opposed to the DataFrame S3 path which uses a separate storage layer).

2. **Architectural mismatch**: The `CacheProvider` protocol is synchronous. Parallelizing S3 GETs within a sync `get_batch` requires threading machinery that adds complexity disproportionate to the infrequent execution.

3. **Low impact at point of use**: When the S3 path does fire (cold start), it is a one-time cost that is dominated by the overall cache warming process (IMP-03 already addresses cache warming parallelization at the higher level). Parallelizing the S3 batch GET saves seconds during a startup that takes minutes.

If cold-start performance becomes critical, the right fix is a protocol-level migration to async CacheProvider (a larger initiative), not a local threading hack in S3CacheProvider.

### Risks (if this were pursued)

1. **Protocol breakage**: Making `get_batch` async would require changing the CacheProvider protocol and all implementations
2. **Thread pool proliferation**: Adding ThreadPoolExecutor to S3CacheProvider creates lifecycle management burden
3. **Connection pool limits**: Concurrent boto3 GETs may exhaust the default connection pool (10 connections)

### Affected Files

N/A -- NO-GO, no changes recommended.

---

## S0-SPIKE-09: Sequential Task Upgrades in Batch Path

**Verdict**: NO-GO

### Evidence

#### (a) What triggers an upgrade? What does "upgrade" mean?

`get_batch_with_upgrade_async` (unified.py:330-386) fetches tasks from cache and then "upgrades" any that are insufficient for the requested `CompletenessLevel`:

```python
async def get_batch_with_upgrade_async(self, gids, required_level, tasks_client):
    # Check cache
    cached = await self.get_batch_async(gids, required_level=required_level)

    # Identify misses
    insufficient_gids = [gid for gid, data in cached.items() if data is None]

    if not insufficient_gids or tasks_client is None:
        return cached

    # Batch upgrade
    opt_fields = get_fields_for_level(required_level)
    for gid in insufficient_gids:
        task = await tasks_client.get_async(gid, opt_fields=opt_fields, raw=True)
        if task:
            await self.put_async(task, opt_fields=opt_fields)
            upgraded[gid] = task
```

An "upgrade" means: the cached entry exists but was stored with a lower completeness level (e.g., MINIMAL when STANDARD is required), OR the entry is missing entirely. The upgrade fetches the task from Asana API with the expanded field set and stores it in cache.

The sequential loop makes one API call per insufficient GID. **Yes, this is sequential.**

#### (b) How many GIDs typically need upgrading?

The completeness system has three levels (from `cache/models/completeness.py`):
- `MINIMAL`: gid, name, resource_subtype (5 fields)
- `STANDARD`: all MINIMAL + custom_fields, parent, memberships, etc. (25 fields)
- `FULL`: all STANDARD + assignee, followers, etc. (35+ fields)

Upgrade fires when a caller requests STANDARD but the cached entry is MINIMAL (or missing). In practice:
- After a fresh cache warming (IMP-03), entries are stored at STANDARD level. **No upgrades needed.**
- After a partial cache warming or degraded fetch, some entries may be MINIMAL. **Upgrades possible.**
- After TTL expiration, entries are missing. **Upgrade = fresh fetch.**

#### (c) Critical finding: this method has ZERO callers outside its own file

Searching for `get_batch_with_upgrade_async` across the entire `src/autom8_asana` directory reveals **only one file**: `cache/providers/unified.py` itself, where it is defined. There are no callers in any route handler, workflow, builder, or service module.

This method is currently **dead code** -- defined as part of the UnifiedTaskStore API but not wired into any production path.

#### (d) Can upgrades be parallelized safely?

In principle, yes. Each upgrade is an independent API call + cache put. No shared mutable state between GIDs (cache puts are key-isolated). However, since the method has no callers, optimizing it delivers zero production value.

#### (e) How often does the upgrade path fire in practice?

**Never.** The method has zero callers in production code.

### Verdict Rationale: NO-GO

`get_batch_with_upgrade_async` is dead code. It has zero callers in the production codebase. Optimizing a method that is never invoked delivers no performance improvement.

If this method is wired into a production path in the future, parallelization would be straightforward (replace the `for` loop with `gather_with_semaphore`). But that is a future concern, not a current optimization target.

### Risks (if this were pursued)

1. **Wasted effort**: Optimizing dead code has zero ROI
2. **Test maintenance**: Adding tests for a method with no callers increases maintenance burden

### Affected Files

N/A -- NO-GO, no changes recommended.

---

## S0-SPIKE-10: TaskRow Triple Type Pass

**Verdict**: CONDITIONAL-GO

### Evidence

#### (a) The full pipeline: dict -> TaskRow -> dict -> DataFrame

There are **two distinct extraction pipelines** in the codebase, and they have different characteristics:

**Pipeline A: Base builder path** (`builders/base.py:441-467`):
```
Task (model)
  --> extractor.extract(task)         # Iterates schema columns
    --> _create_row(data)             # Calls TaskRow.model_validate(data)
      --> row.to_dict()               # Calls model_dump() + Decimal conversion
        --> [returned as dict]
  --> coerce_rows_to_schema(rows)     # Schema coercion
  --> pl.DataFrame(rows, schema=...)  # Polars construction
```

This is the "triple type pass": dict (extracted columns) -> TaskRow (Pydantic model) -> dict (model_dump) -> DataFrame.

**Pipeline B: Progressive builder + DataFrameViewPlugin path** (`progressive.py:1079-1093`, `views/dataframe_view.py:246-278`):
```
Task (model)
  --> _task_to_dict(task)              # model_dump() to get raw dict
  --> DataFrameViewPlugin._extract_rows_async(task_dicts)
    --> _extract_row_async(task_data)  # Iterates schema columns directly
      --> [returns dict directly]      # NO TaskRow construction
  --> coerce_rows_to_schema(rows)
  --> pl.DataFrame(rows, schema=...)
```

**Pipeline B does NOT use TaskRow at all.** The `DataFrameViewPlugin._extract_rows_async` returns dicts directly without constructing a TaskRow model. This is the path used by the progressive builder (which handles the large 5000+ task sections).

#### (b) TaskRow field counts

- `TaskRow`: 12 fields (gid, name, type, date, created, due_on, is_completed, completed_at, url, last_modified, section, tags)
- `UnitRow(TaskRow)`: 12 base + 11 extra = 23 fields
- `ContactRow(TaskRow)`: 12 base + 13 extra = 25 fields

All fields use standard Python types (str, bool, datetime, date, Decimal, list[str]). No complex nested models.

#### (c) What validation does TaskRow perform?

TaskRow model configuration (`task_row.py:37`):
```python
model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
```

- **`frozen=True`**: Immutable after construction (hashable). This is a correctness constraint.
- **`extra="forbid"`**: Rejects unknown fields. This catches schema drift bugs early.
- **`strict=True`**: No implicit type coercion. A string "true" will NOT be coerced to `bool True`. Values must be the correct type.

There are **no custom validators** on TaskRow or its subclasses. No `@field_validator`, no `@model_validator`. The validation is purely Pydantic's built-in type checking and the three ConfigDict flags above.

#### (d) Where the TaskRow path actually executes

The base builder's `_extract_row` (base.py:465-467) is called from `_build_eager` and `_build_lazy` (base.py:375-393). These are used by:
- `DataFrameProjectBuilder.build_async()` -- the synchronous/non-progressive path
- Any builder subclass that calls the base `build()` method

The progressive builder's `_build_section_dataframe` and `_write_checkpoint` use Pipeline B (DataFrameViewPlugin), which **skips TaskRow entirely**.

#### (e) Estimated cost at scale

For Pipeline A (base builder with TaskRow):
- `model_validate` for UnitRow (23 fields, strict mode): ~50-80 microseconds per row (Pydantic v2)
- `model_dump` (via `to_dict()`): ~20-40 microseconds per row
- `_convert_decimals` recursive dict walk: ~5-10 microseconds per row
- **Total TaskRow overhead per row**: ~75-130 microseconds
- **At 2600 iterations**: 195-338ms

For Pipeline B (DataFrameViewPlugin, no TaskRow):
- Direct dict construction: ~0 microseconds (just dict assignment)
- **Total TaskRow overhead**: 0ms
- Already the optimized path

#### (f) Context from B2 verdict on S0-SPIKE-06

The B2 verdict established that `model_validate(task.model_dump())` costs ~50-80 microseconds per object in Pydantic v2. The same analysis applies here: `TaskRow.model_validate(data)` + `row.to_dict()` (which calls `model_dump()`) adds ~100-130 microseconds per row.

### Per-Pipeline Verdict

| Pipeline | TaskRow overhead | Fix feasibility | Verdict |
|----------|-----------------|-----------------|---------|
| **A (base builder)** | 195-338ms for 2600 tasks | Remove TaskRow, return dict directly | CONDITIONAL-GO |
| **B (progressive builder)** | 0ms (already optimized) | N/A | Already optimal |

### Verdict Rationale: CONDITIONAL-GO

**Condition**: Only worth implementing for Pipeline A (base builder) if that path is exercised for large datasets (>1000 tasks). The progressive builder (Pipeline B) already skips TaskRow.

The question is: does Pipeline A ever handle 2600+ tasks in production?
- `_build_eager` is used for datasets <= 100 tasks (per ADR-0031, base.py:366)
- `_build_lazy` is used for datasets > 100 tasks

For small datasets (<=100 tasks), the TaskRow overhead is 7.5-13ms -- negligible. For large datasets via `_build_lazy`, the overhead could be meaningful but the progressive builder (Pipeline B) is the primary path for large sections.

**The optimization is valid but low-impact because the high-volume path (progressive builder) already bypasses TaskRow.** The base builder path handles smaller datasets where 100-300ms of Pydantic overhead is not a bottleneck.

If pursued, the implementation should:
1. Replace `TaskRow.model_validate(data)` with direct dict return in `_create_row`
2. Move the `strict=True` / `extra="forbid"` validation to a debug-only assertion
3. Handle `frozen=True` immutability by making dicts (they are not mutated after creation)
4. Maintain `_convert_decimals` for Polars Decimal compatibility

### If CONDITIONAL-GO -- Implementation Sketch

**Approach: Add a bypass mode to _create_row**

```python
# In BaseExtractor.extract():
def extract(self, task, project_gid=None) -> dict[str, Any]:
    data = {}
    for col in self._schema.columns:
        try:
            value = self._extract_column(task, col, project_gid)
            data[col.name] = value
        except Exception as e:
            data[col.name] = None

    # Return dict directly instead of TaskRow -> dict round-trip
    return self._finalize_row(data)

def _finalize_row(self, data: dict[str, Any]) -> dict[str, Any]:
    """Finalize row dict with Decimal conversion for Polars."""
    return TaskRow._convert_decimals(data)
```

This eliminates the model_validate + model_dump round-trip while keeping the Decimal conversion for Polars compatibility.

**However**, this changes the return type of `extract()` from `TaskRow` to `dict`. Callers that depend on `TaskRow` attributes (e.g., `row.gid`, `row.is_completed`) would break. Need to audit all callers.

**Safer approach**: Keep TaskRow construction but use `model_construct` (skip validation) in production, with a debug-mode flag that enables full validation:

```python
def _create_row(self, data):
    if settings.DEBUG:
        return UnitRow.model_validate(data)
    return UnitRow.model_construct(**data)
```

### Risks

- **Medium**: Removing TaskRow validation loses the `strict=True` / `extra="forbid"` safety net. Schema drift bugs would silently produce wrong data instead of raising ValidationError. Mitigated by: keeping validation in tests, adding schema-level assertions.
- **Low**: `_convert_decimals` must still be applied regardless of TaskRow presence. Easy to factor out.
- **Low-to-None**: Impact is limited because the progressive builder (the high-volume path) already bypasses TaskRow.

### Affected Files

- `src/autom8_asana/dataframes/extractors/base.py` (modify `extract`/`extract_async` return path)
- `src/autom8_asana/dataframes/extractors/unit.py` (modify `_create_row`)
- `src/autom8_asana/dataframes/extractors/contact.py` (modify `_create_row`)
- `src/autom8_asana/dataframes/extractors/default.py` (modify `_create_row`)
- `src/autom8_asana/dataframes/builders/base.py` (modify `_extract_row` / `_extract_row_async` to handle dict return)
- `src/autom8_asana/dataframes/models/task_row.py` (potentially retain as debug-only validator)
- Test files for extractors and builders

---

## Summary Table

| Spike | Verdict | Score | Rationale |
|-------|---------|-------|-----------|
| S0-SPIKE-03 | **GO** | 55 | Section reads are plainly sequential with no gather pattern. Each section is an independent S3 GET via `asyncio.to_thread()`. No shared mutable state. Parallelization with `gather_with_semaphore(5)` yields ~5x speedup for 20-section projects. |
| S0-SPIKE-04 | **GO** | 55 | Checkpoints re-extract ALL accumulated tasks every time. For 30k tasks with 6 checkpoints, this produces 4.5x amplification (135k extractions vs 30k necessary). Delta approach is safe -- no ordering dependencies, no accumulated state in extraction. Saves ~9.5 seconds on large sections. |
| S0-SPIKE-08 | **NO-GO** | 52 | S3 batch GET fires only on Redis cache misses (rare in steady state). The entire CacheProvider protocol is synchronous -- parallelization requires either protocol-breaking async migration or local threading hacks. Cold-start S3 cost is dominated by overall cache warming (addressed by IMP-03). |
| S0-SPIKE-09 | **NO-GO** | 48 | `get_batch_with_upgrade_async` has **zero callers** in the production codebase. It is dead code. Optimizing it delivers zero performance improvement. |
| S0-SPIKE-10 | **CONDITIONAL-GO** | 48 | TaskRow construction adds ~100-130us per row via model_validate + model_dump round-trip. However, the high-volume progressive builder path (Pipeline B) **already bypasses TaskRow** entirely via DataFrameViewPlugin. The base builder path (Pipeline A) uses TaskRow but only handles small datasets (<=100 tasks for eager mode). Net impact is low. Worth pursuing only if the base builder handles large datasets in production. |

---

## Cross-Batch Summary (All 12 Spikes)

| Batch | Spike | Verdict | Promote to IMPLEMENT? |
|-------|-------|---------|-----------------------|
| B1 | S0-SPIKE-01 (AsanaClient pool) | GO | Yes (high priority) |
| B1 | S0-SPIKE-02 (Multi-PVP batch) | NO-GO/promote | Yes (already supported server-side) |
| B1 | S0-SPIKE-12 (Middleware overhead) | NO-GO | No |
| B2 | S0-SPIKE-05 (Business double-fetch) | GO | Yes |
| B2 | S0-SPIKE-06 (Pydantic round-trip) | CONDITIONAL-GO | Yes (Phase 1: from_attributes) |
| B3 | S0-SPIKE-03 (Sequential section reads) | GO | Yes |
| B3 | S0-SPIKE-04 (Checkpoint amplification) | GO | Yes |
| B3 | S0-SPIKE-08 (S3 batch GET) | NO-GO | No |
| B3 | S0-SPIKE-09 (Sequential upgrades) | NO-GO | No (dead code) |
| B3 | S0-SPIKE-10 (TaskRow triple pass) | CONDITIONAL-GO | Low priority (high-volume path already optimized) |

**Remaining spikes not yet investigated**: S0-SPIKE-07 (duplicate section listing), S0-SPIKE-11 (Asana batch API).
