# Sprint Execution Guide: INIT-RUNTIME-OPT-002

**Initiative**: Runtime Efficiency Remediation v2
**Scope**: 23 IMPLEMENT findings across 4 sprints, 11 PE invocations, 2 QA gates
**Author**: Architect
**Date**: 2026-02-15

---

## Section 0: QA Condition Resolutions

### R1 (REQUIRED): S0-11 "Merge 3 PUTs" Correction

The S0-11 verdict incorrectly stated that 3 independent configure PUTs could merge into 1. Corrected:

- **due_date** (`tasks.update_async(gid, due_on=...)`) and **assignee** (`tasks.set_assignee_async(gid, ...)`) CAN merge into a single `tasks.update_async(gid, due_on=..., assignee=...)`.
- **hierarchy** uses `SaveSession.set_parent()` which calls the `setParent` endpoint (POST `/tasks/{gid}/setParent`). This CANNOT merge with a PUT to `/tasks/{gid}`.
- Net saving: 1 API call (3 becomes 2: one combined update + one setParent).
- **Action**: Captured as boy-scout item in PE-2b when IMP-02/IMP-07 touch the configure phase.

### R2 (REQUIRED): gather_with_semaphore Design Requirements

**Signature**:
```python
async def gather_with_semaphore(
    coros: Iterable[Coroutine],
    *,
    concurrency: int = 10,
    return_exceptions: bool = True,
    label: str = "gather",
) -> list[Any]
```

**Requirements**:
- Inputs MUST be unawaited coroutine objects (not tasks, not futures). The utility eagerly wraps each in `_bounded()` and passes to `asyncio.gather`.
- Generator inputs: the list comprehension `[_bounded(c) for c in coros]` eagerly consumes generators. This is intentional -- all coroutine wrappers are created upfront.
- Semaphore bounds are **callsite-local** -- they do NOT bound global thread pool usage. If IMP-09 (sem=10) and IMP-21 (sem=5) fire concurrently, the thread pool sees 15 concurrent `to_thread()` calls, not 10 or 5.
- The utility does NOT replace transport-level AIMD. It provides application-level concurrency bounds above the transport layer.
- Log summary at completion: `{label}_completed`, `succeeded`, `failed`, `total`, `elapsed_ms`.

**Required test cases** (in `tests/unit/core/test_concurrency.py`):
1. Empty coros list returns `[]`
2. All-exceptions case: every coro raises, returns list of exceptions
3. Mixed success/failure with `return_exceptions=True`
4. Generator input consumed eagerly (pass a generator expression, verify all items executed)
5. Large input (100+ items) completes without deadlock
6. Label appears in structured log output
7. Concurrency bound respected: with `concurrency=2` and 10 coros, at most 2 run simultaneously

### R3 (RECOMMENDED): Corrected Impact Estimates

| Metric | Original | Corrected | Reason |
|--------|----------|-----------|--------|
| ConversationAudit | -75% | -62% | IMP-01 + IMP-23 are additive but not all 200 holders trigger business double-fetch |
| Startup latency | 17x | 5.5x | Watermark loading (500ms) and section merge (400ms) are sequential, not pipelined |
| All others | unchanged | unchanged | -- |

### R4 (RECOMMENDED): IMP-19 Additional Requirements

- **CircuitBreaker tuning**: `failure_threshold >= 10` (not 3-5), `reset_timeout = 30s` (short recovery). Log state transitions (CLOSED->OPEN, OPEN->HALF_OPEN, HALF_OPEN->CLOSED) at WARNING level.
- **`aclose()` safety**: Pooled clients MUST have `aclose()` as a no-op (or delegate to pool eviction). The current dependency teardown calls `aclose()` in `finally` (dependencies.py:377-379). If migration is incomplete, clients get invalidated mid-use.
- **Pool metrics**: Track `pool.hits`, `pool.misses`, `pool.evictions` via structured logging on each `get_or_create` call.
- **Max pool size**: 100, LRU + TTL eviction (1hr S2S, 5min PAT).

### R5 (RECOMMENDED): IMP-22 Additional Requirements

- Reset `_checkpoint_df = None` and `_checkpoint_task_count = 0` at the top of each section build (not just `__init__`). The progressive builder loops over sections in `build_project_async` -- delta state MUST NOT leak between sections.
- Add comparison test: run both full-extraction and delta paths on a synthetic 10k-task section with 2 checkpoints, assert DataFrames are identical (schema + data + row order via `pl.testing.assert_frame_equal`).

---

## Section 1: Sprint 1 -- Foundation (6 findings, 3 PE invocations)

### PE-1a: gather_with_semaphore Utility (PREREQUISITE)

**Must complete before PE-1b and PE-1c begin.**

**Create**: `src/autom8_asana/core/concurrency.py` -- single module, single function. Implementation: `asyncio.Semaphore(concurrency)` wrapping each coro in `_bounded()`, passed to `asyncio.gather`. Early return `[]` if no tasks. Log `{label}_completed` with `succeeded`, `failed`, `total`, `elapsed_ms` via `structlog`. Use `time.perf_counter()` for elapsed. Imports: `asyncio`, `time`, `collections.abc.Coroutine/Iterable`, `typing.Any`, `structlog`. See R2 above for complete signature and all behavioral requirements.

**Create**: `tests/unit/core/test_concurrency.py` with all 7 test cases from R2.

**Update**: `src/autom8_asana/core/__init__.py` -- add `gather_with_semaphore` to exports.

**Commit**: `perf(core): add gather_with_semaphore concurrency utility`
**Test**: `.venv/bin/pytest tests/unit/core/test_concurrency.py -x -q --timeout=60`

---

### PE-1b: IMP-19 (Client Pool) + IMP-10 (Timeout Config)

**PARALLEL with PE-1c** (no shared files).

#### IMP-10: Pass All 4 Timeout Values

**File**: `src/autom8_asana/transport/config_translator.py` (line 76-83)

The `HttpClientConfig` in `autom8y_http` only accepts a single `timeout: float`. The `TimeoutConfig` dataclass (config.py:213-227) defines connect=5, read=30, write=30, pool=10. Currently only `timeout.read` is passed (line 78).

**Change**: The `HttpClientConfig` only accepts a single `timeout: float`. Change line 78 from `timeout=asana_config.timeout.read` (30s) to `timeout=asana_config.timeout.connect` (5s) for faster failure detection. If `Autom8yHttpClient` accepts an `httpx.Timeout` object directly, construct `httpx.Timeout(connect=5, read=30, write=30, pool=10)` instead.

**Tests**: `tests/unit/transport/test_config_translator.py`

#### IMP-19: Token-Keyed ClientPool

**Create**: `src/autom8_asana/api/client_pool.py` -- `ClientPool` class with: `_pool: dict[str, tuple[AsanaClient, float, float]]` (token_hash -> client, last_access, created_at), `_lock: asyncio.Lock`, `_max_size=100`, `_s2s_ttl=3600`, `_pat_ttl=300`, `_stats` (hits/misses/evictions). Method `get_or_create(token, is_s2s) -> AsanaClient`: hash token, lock, check pool + TTL, create on miss, LRU evict if over max_size, log pool.hit/miss. Method `close_all()` for lifespan shutdown. Override `aclose()` to no-op on returned clients (per R4). CB tuning per R4: `failure_threshold >= 10`, `reset_timeout = 30s`, log state transitions at WARNING.

**Modify**: `src/autom8_asana/api/dependencies.py` (lines 382-409) -- change `get_asana_client_from_context` from async generator (yield/finally) to regular async function that calls `request.app.state.client_pool.get_or_create(auth_context.asana_pat, is_s2s=auth_context.auth_mode == "jwt")`. Also update `get_asana_client` (lines 353-379) with same pattern or deprecate.

**Modify**: `src/autom8_asana/api/main.py` (or lifespan) -- init `app.state.client_pool = ClientPool()` on startup, `close_all()` on shutdown.

**Tests**: `tests/unit/api/test_client_pool.py` -- pool hit, miss, TTL eviction, LRU eviction, `close_all()`, `aclose()` no-op, CB logging.

**Commits**:
1. `perf(transport): use connect timeout for faster failure detection (IMP-10)`
2. `perf(api): add token-keyed ClientPool for S2S resilience (IMP-19)`

**Test**: `.venv/bin/pytest tests/unit/transport/test_config_translator.py tests/unit/api/test_client_pool.py tests/unit/api/test_dependencies.py -x -q --timeout=60`

---

### PE-1c: IMP-04 (Redis Pipeline) + IMP-09 (Parallel Watermarks) + IMP-03 (Parallel Cache Warming)

**PARALLEL with PE-1b** (no shared files).

#### IMP-04: Redis Pipeline Fix

**File**: `src/autom8_asana/cache/backends/redis.py` (lines 451-471, method `_do_set_versioned`)

Lines 459-463 use a pipeline for HSET+EXPIRE, but lines 466-469 make 2 separate round-trips for metadata (standalone `conn.hset` and `conn.expire`).

**Change**: Move the metadata HSET (line 467) and EXPIRE (line 469) into the existing `pipe` before `pipe.execute()` (line 463). Delete the standalone calls at lines 466-469. This consolidates 3-4 Redis round-trips into 1 pipeline execution.

**Tests**: `.venv/bin/pytest tests/unit/cache/backends/test_redis.py -x -q --timeout=60`

#### IMP-09: Parallel Watermark Loading

**File**: `src/autom8_asana/dataframes/storage.py` (lines 891-914, method `load_all_watermarks`)

Replace sequential loop (lines 908-911) with `gather_with_semaphore(concurrency=10, label="load_all_watermarks")`. Each coro returns `(gid, watermark)` tuple. Filter exceptions (log warning) and None watermarks from results.

**Tests**: `.venv/bin/pytest tests/unit/dataframes/test_storage.py -x -q --timeout=60`

#### IMP-03: Parallel Cache Warming

**File**: `src/autom8_asana/client.py` (lines 875-910, method `warm_cache_async`)

Split into 2 phases: (1) filter already-cached GIDs (keep existing cache check loop for `skipped` count), (2) `gather_with_semaphore(concurrency=20, label="warm_cache")` for uncached GIDs. Each coro uses the existing `match entry_type` dispatch (lines 889-903). Count exceptions as `failed`, successes as `warmed`.

**Tests**: `.venv/bin/pytest tests/unit/test_client.py -x -q --timeout=60`

**Commits**:
1. `perf(cache): move metadata writes into Redis pipeline (IMP-04)`
2. `perf(storage): parallelize watermark loading at startup (IMP-09)`
3. `perf(client): parallelize cache warming with gather_with_semaphore (IMP-03)`

---

## Section 2: Sprint 2 -- Lifecycle + Dataframes (7 findings, 3 PE invocations)

### PE-2a: IMP-01 (Parent GID Passthrough) + IMP-02 (Seeder Double-Fetch)

**PARALLEL with PE-2b.**

#### IMP-01: ContactHolder parent_gid Passthrough

**File**: `src/autom8_asana/automation/workflows/conversation_audit.py`

`_process_holder` (line 344) already receives `parent_gid: str | None = None` (line 351). But `_resolve_office_phone` (line 485) ignores it -- always fetches holder_task to get `parent.gid` (lines 499-502).

**Change**: Add `parent_gid: str | None = None` parameter to `_resolve_office_phone` (line 485). When `parent_gid` is provided, skip the holder fetch (lines 499-502) and use it directly with `ResolutionContext`. When None, fall back to existing fetch logic. Update call site at line 386: `await self._resolve_office_phone(holder_gid, parent_gid=parent_gid)`.

**Tests**: `.venv/bin/pytest tests/unit/automation/workflows/test_conversation_audit.py -x -q --timeout=60`

#### IMP-02: Seeder Double-Fetch

**File 1**: `src/autom8_asana/lifecycle/seeding.py` (lines 104-113)
**File 2**: `src/autom8_asana/automation/seeding.py` (lines 446-457)

Both `AutoCascadeSeeder.seed_async` and `FieldSeeder.write_fields_async` independently fetch the target task with custom_fields opt_fields.

**Change in `lifecycle/seeding.py`**: Add optional `target_task: Task | None = None` parameter to `seed_async`. If provided, skip the fetch at lines 105-113.

**Change in `automation/seeding.py`**: Add optional `target_task: Task | None = None` parameter to `write_fields_async`. If provided, skip the fetch at lines 449-457.

**Change in callers**: When `AutoCascadeSeeder.seed_async` fetches the target, pass the fetched task to `FieldSeeder.write_fields_async` to avoid re-fetch.

**Tests**: `.venv/bin/pytest tests/unit/lifecycle/test_seeding.py tests/unit/automation/test_seeding.py -x -q --timeout=60`

**Commits**:
1. `perf(audit): pass parent_gid to skip holder fetch in conversation audit (IMP-01)`
2. `perf(lifecycle): eliminate seeder double-fetch via task passthrough (IMP-02)`

---

### PE-2b: IMP-05 (Parallel Init Actions) + IMP-07 (Template Config) + IMP-11 (Parallel Project Enum)

**PARALLEL with PE-2a.**

#### IMP-05: Parallel Init Actions

**File**: `src/autom8_asana/lifecycle/engine.py` (lines 738-774, `InitActionExecutor.execute_actions_async`)

Current: sequential `for action_config in actions` loop (line 749).

**Change**: Extract the per-action try/except body (lines 761-773) into `_execute_one(action_config, created_entity_gid, ctx, source_process) -> ActionResult` helper. Replace sequential loop with `gather_with_semaphore(concurrency=4, label="init_actions")`. Map exceptions to `ActionResult(success=False, error=str(e))`.

**Tests**: `.venv/bin/pytest tests/unit/lifecycle/test_engine.py -x -q --timeout=60`

#### IMP-07: Template Section GID Config

**File 1**: `src/autom8_asana/automation/templates.py` (lines 80-83)
**File 2**: Lifecycle YAML config files

**Change**: Add optional `template_section_gid: str | None` parameter to `find_template_section_async` and `find_template_task_async`. If provided, skip the sections listing (lines 81-83) and return the section directly via `client.sections.get_async(template_section_gid)`.

Add `template_section_gid` field to lifecycle YAML config schema (in the lifecycle stages config). Fall back to runtime discovery if absent.

**Tests**: `.venv/bin/pytest tests/unit/automation/test_templates.py -x -q --timeout=60`

#### IMP-11: Parallel Project Enumeration

**File**: `src/autom8_asana/automation/workflows/pipeline_transition.py` (lines 226-326, `_enumerate_processes_async`)

Current: sequential `for project_gid in project_gids` loop (line 244).

**Change**: Extract per-project body (lines 245-324) into `_enumerate_one(project_gid) -> list[tuple[Process, str]]`. Replace sequential loop with `gather_with_semaphore(concurrency=5, label="enumerate_processes")`. Extend `processes` list with successful results, log exceptions.

**Tests**: `.venv/bin/pytest tests/unit/automation/workflows/test_pipeline_transition.py -x -q --timeout=60`

**Boy-scout item (from R1)**: When touching configure phase in `lifecycle/creation.py`, merge the due_date and assignee PUTs into a single `tasks.update_async(gid, due_on=..., assignee=...)` call. Saves 1 API call per lifecycle creation (3 calls become 2).

**Commits**:
1. `perf(lifecycle): parallelize init action execution (IMP-05)`
2. `perf(automation): add template_section_gid config to skip discovery (IMP-07)`
3. `perf(automation): parallelize project enumeration in pipeline transition (IMP-11)`

---

### PE-2c: IMP-22 (Delta Checkpoints) + IMP-15 (Double Task-to-Dict)

**After PE-2a/PE-2b** (same file, avoids merge conflicts).

#### IMP-22: Delta Checkpoint Extraction

**File**: `src/autom8_asana/dataframes/builders/progressive.py`

**Add instance state**: `self._checkpoint_df: pl.DataFrame | None = None` and `self._checkpoint_task_count: int = 0`.

**Reset at section start** (per R5): Set both to `None`/`0` at top of `_build_project_section_async` (around line 575).

**Modify `_write_checkpoint`** (lines 980-1048): Extract only `tasks[self._checkpoint_task_count:]` (new tasks since last checkpoint). Build `delta_df` from new tasks only. Concatenate: `pl.concat([self._checkpoint_df, delta_df])` (or just `delta_df` if first checkpoint). Update `self._checkpoint_df` and `self._checkpoint_task_count = len(tasks)`. S3 write uses the full `checkpoint_df` (same as before).

**Modify `_build_section_dataframe`** (lines 919-948): Three branches: (1) if checkpoint exists and more tasks remain: extract delta, concatenate with checkpoint; (2) if checkpoint exists and no new tasks: use checkpoint directly; (3) no checkpoint: full extraction (current behavior).

#### IMP-15: Double Task-to-Dict Elimination

**Same file**: `src/autom8_asana/dataframes/builders/progressive.py`

Currently, `_write_checkpoint` (line 1003) and `_build_section_dataframe` (line 934) both call `_task_to_dict` on the full task list. With IMP-22's delta approach, each task is now converted at most once (either during a checkpoint or during the final delta build). This is automatically resolved by IMP-22.

Verify that `_populate_store_with_tasks` (called at line 636 before DataFrame build) does NOT also call `_task_to_dict`. If it does, pre-compute task_dicts once and pass to both.

**Comparison test** (per R5): Add test that runs both full-extraction and delta paths on a synthetic section, asserts `pl.testing.assert_frame_equal(full_df, delta_df)`.

**Tests**: `.venv/bin/pytest tests/unit/dataframes/builders/test_progressive.py -x -q --timeout=60`

**Commits**:
1. `perf(dataframes): delta checkpoint extraction to eliminate re-extraction amplification (IMP-22 + IMP-15)`

---

## Section 3: Sprint 3 -- Data Service + Models (7 findings, 3 PE invocations)

### PE-3a: IMP-20 (Multi-PVP Batch)

**PARALLEL with PE-3b.**

**File**: `src/autom8_asana/clients/data/client.py`

**Modify `get_insights_batch_async`** (lines 908-960): Replace per-PVP `fetch_one` loop with single HTTP POST containing all PVPs.

**Modify `_execute_insights_request`** (lines 1170-1209): Change `phone_vertical_pairs` from single-element list (line 1184) to full list: `[{"phone": pvp.office_phone, "vertical": pvp.vertical} for pvp in pvp_list]`.

**Response parsing**: Index `data: list[EntityMetrics]` by canonical key `pv1:{phone}:{vertical}` (each `EntityMetrics` has `office_phone` and `vertical` fields). Map back to `BatchInsightsResult`. Parse `errors` field for HTTP 207 partial failures. Chunk into groups of 1000 if `len(pairs) > 1000`.

**Tests**: `.venv/bin/pytest tests/unit/clients/data/test_client.py tests/unit/clients/data/test_contract_alignment.py -x -q --timeout=60`

**Commit**: `perf(data-client): send all PVPs in single request for batch insights (IMP-20)`

---

### PE-3b: IMP-23 (Business Double-Fetch) + IMP-08 (Parallel Deltas) + IMP-21 (Parallel Section Reads)

**PARALLEL with PE-3a.**

#### IMP-23: Unified Field Set for Business Detection

**File**: `src/autom8_asana/models/business/hydration.py`

5 changes: (1) Line 287: `_DETECTION_OPT_FIELDS` -> `_BUSINESS_FULL_OPT_FIELDS`. (2) Line 686: same replacement in traversal. (3) Lines 321-328: remove re-fetch, use `entry_task` directly. Lines 707-715: remove re-fetch, use `parent_task` directly. (4) Update `api_calls` accounting (-1 when Business found). (5) Remove `_DETECTION_OPT_FIELDS` alias from hydration.py.

**Test mock updates**: Update opt_fields assertions in:
- `tests/unit/models/business/test_hydration.py`
- `tests/unit/models/business/test_hydration_combined.py`
- `tests/unit/models/business/test_hydration_fields.py`
- `tests/unit/models/business/test_upward_traversal.py`

**Tests**: `.venv/bin/pytest tests/unit/models/business/ -x -q --timeout=60`

#### IMP-08: Parallel Delta Application

**File**: `src/autom8_asana/dataframes/builders/freshness.py` (lines 231-284, `apply_deltas_async`)

Replace sequential loop (lines 256-273) with `gather_with_semaphore(concurrency=5, label="apply_deltas")` over `self._apply_section_delta(result, view)` coros. Count successes as `updated_count`, log exceptions.

**Tests**: `.venv/bin/pytest tests/unit/dataframes/builders/test_freshness.py -x -q --timeout=60`

#### IMP-21: Parallel Section Reads

**File**: `src/autom8_asana/dataframes/section_persistence.py` (lines 585-620, `read_all_sections_async`)

Replace sequential loop (lines 605-609) with `gather_with_semaphore(concurrency=5, label="read_all_sections")` over `self.read_section_async(project_gid, gid)` coros. Filter exceptions (log warning) and None results from output list.

**Tests**: `.venv/bin/pytest tests/unit/dataframes/test_section_persistence.py -x -q --timeout=60`

**Commits**:
1. `perf(models): unify detection field set to eliminate business double-fetch (IMP-23)`
2. `perf(dataframes): parallelize delta application with gather_with_semaphore (IMP-08)`
3. `perf(dataframes): parallelize section reads with gather_with_semaphore (IMP-21)`

---

### PE-3c: IMP-06 (Double Watermark Read) + IMP-12 (Play Dependency N+1) + IMP-13 (Subtask Count Combine)

**After PE-3b** (IMP-06 shares `storage.py` with IMP-09 from Sprint 1, different methods).

#### IMP-06: Double Watermark Read

**File**: `src/autom8_asana/cache/dataframe/tiers/progressive.py` (lines 134-184)

Current code: loads DataFrame via `storage.load_dataframe` (line 136), then separately loads `watermark.json` via `storage.load_json` (line 172) for `schema_version`.

**Change**: Extend `load_dataframe` to also return schema_version metadata (or add `load_dataframe_with_metadata` variant in `storage.py`). The watermark JSON already contains `schema_version` -- read it during the same S3 access path.

Alternatively, include `schema_version` in the parquet metadata (written during `save_section`) and extract it from the DataFrame metadata after `load_dataframe`, eliminating the separate JSON GET entirely.

**Tests**: `.venv/bin/pytest tests/unit/cache/dataframe/tiers/test_progressive.py -x -q --timeout=60`

#### IMP-12: Play Dependency N+1

**File**: `src/autom8_asana/lifecycle/init_actions.py` (lines 185-214)

Current: Fetches dependencies with `opt_fields=["dependencies", "dependencies.gid"]` (line 194), then for each dependency, fetches the task to check project membership (lines 202-203).

**Change**: Expand opt_fields (line 194) to `["dependencies", "dependencies.gid", "dependencies.memberships", "dependencies.memberships.project.gid"]`. Check project membership directly from `dep.memberships` instead of fetching each dependency individually. Remove the inner `client.tasks.get_async(dep_gid, ...)` call (lines 202-203).

**Tests**: `.venv/bin/pytest tests/unit/lifecycle/test_init_actions.py -x -q --timeout=60`

#### IMP-13: Subtask Count Combine

**File 1**: `src/autom8_asana/automation/pipeline.py` (lines 315-319)
**File 2**: `src/autom8_asana/lifecycle/creation.py`

Current: Template subtask count is fetched separately via `tasks.subtasks_async(template_task.gid, opt_fields=["gid"]).collect()` (pipeline.py:316-318).

**Change**: Include `num_subtasks` in the template task fetch opt_fields (when template is discovered). Cache the count per template GID for the Lambda invocation duration. Alternatively, add `num_subtasks` to the template discovery fetch so it is available without an extra API call.

**Tests**: `.venv/bin/pytest tests/unit/automation/test_pipeline.py tests/unit/lifecycle/test_creation.py -x -q --timeout=60`

**Commits**:
1. `perf(cache): eliminate double watermark read in ProgressiveTier (IMP-06)`
2. `perf(lifecycle): expand opt_fields to eliminate play dependency N+1 (IMP-12)`
3. `perf(automation): combine subtask count with template fetch (IMP-13)`

---

## Section 4: Sprint 4 -- Micro + DRY (5 findings, 2 PE invocations)

### PE-4a: IMP-14 (O(1) Accessor) + IMP-16 (Import Guard) + IMP-17 (Search Index Dedup)

**PARALLEL with PE-4b.**

#### IMP-14: CustomFieldAccessor O(1) Lookup

**File**: `src/autom8_asana/models/custom_field_accessor.py`

**Change `_build_index`** (lines 63-70): Add `self._gid_to_field: dict[str, dict]` that maps each field's GID to its dict. Build alongside existing `_name_to_gid` in the same loop.

**Change `get`** (lines 91-112): Replace linear scan `for field in self._data` (lines 108-110) with `self._gid_to_field.get(gid)` dict lookup. O(N) becomes O(1).

**Tests**: `.venv/bin/pytest tests/unit/models/test_custom_field_accessor.py -x -q --timeout=60`

#### IMP-16: HolderFactory Import Guard

**File**: `src/autom8_asana/models/business/holder_factory.py` (lines 269-296)

**Change**: At top of `_populate_children` (line 269), check `self.__class__.CHILD_TYPE is not Task` before calling `importlib.import_module`. If already resolved (not the stub `Task`), skip the import. This makes all calls after the first a no-op for the import path.

**Tests**: `.venv/bin/pytest tests/unit/models/business/test_holder_factory.py -x -q --timeout=60`

#### IMP-17: Search Column Index Dedup

**File**: `src/autom8_asana/search/service.py`

`_build_column_index(df)` is called twice: once in `_build_filter_expr` (line 555) and once in `_extract_hits` (line 678).

**Change**: Compute `col_index = self._build_column_index(df)` once in the caller (`find_async`). Add `col_index: dict[str, str] | None = None` parameter to both `_build_filter_expr` and `_extract_hits`. Pass the pre-computed index to both instead of recomputing.

**Tests**: `.venv/bin/pytest tests/unit/search/test_service.py -x -q --timeout=60`

**Commits**:
1. `perf(models): O(1) GID lookup in CustomFieldAccessor (IMP-14)`
2. `perf(models): skip importlib when CHILD_TYPE already resolved (IMP-16)`
3. `refactor(search): compute column index once per search (IMP-17)`

---

### PE-4b: IMP-18 (CF Extraction DRY) + S0-06-Phase1 (from_attributes=True)

**PARALLEL with PE-4a.**

#### IMP-18: CF Extraction DRY

**File 1**: `src/autom8_asana/dataframes/views/dataframe_view.py` (lines 471-517, `_extract_custom_field_value_from_dict`)
**File 2**: `src/autom8_asana/dataframes/views/cascade_view.py` (lines 441-467, `_get_custom_field_value_from_dict` + lines 469-542, `_extract_field_value`)

These two methods duplicate the same custom field extraction logic (name normalization, dict iteration, value priority ordering).

**Change**: Extract shared `extract_cf_value(cf_data: dict) -> Any` utility (in `dataframes/views/cf_utils.py` or at top of `dataframe_view.py`). Priority: number_value > text_value > enum_value.name > multi_enum_values > display_value. Both `_extract_custom_field_value_from_dict` (dataframe_view.py) and `_get_custom_field_value_from_dict` (cascade_view.py) delegate to this shared utility for per-field extraction.

**Tests**: `.venv/bin/pytest tests/unit/dataframes/views/ -x -q --timeout=60`

#### S0-06 Phase 1: from_attributes=True

**Files** (20 call sites across the business model layer):
- `models/business/holder_factory.py` (line 308)
- `models/business/business.py` (lines 220, 582-616)
- `models/business/hydration.py` (lines 338, 716, 782, 808)
- `models/business/unit.py` (lines 327, 332)
- `models/business/location.py` (lines 221, 226)
- `models/business/asset_edit.py` (lines 537, 646, 664, 708)
- `models/business/base.py` (line 129)

**Change**: At all 20 sites, replace `ChildClass.model_validate(task.model_dump())` with `ChildClass.model_validate(task, from_attributes=True)`. This eliminates `model_dump()` serialization while still running `_capture_custom_fields_snapshot` validator. Safe for all sites (validated in S0-06 investigation).

**Tests**: `.venv/bin/pytest tests/unit/models/business/ -x -q --timeout=60`

**Commits**:
1. `refactor(dataframes): extract shared CF value extraction utility (IMP-18)`
2. `perf(models): use from_attributes=True for model conversion (S0-06-Phase1)`

---

## Section 5: QA Gate Specifications

### QA Gate 1 (After Sprint 2)

- **Scope**: All Sprint 1 + Sprint 2 commits
- **Test command**: `.venv/bin/pytest tests/ -x -q --timeout=60`
- **Focus areas**:
  - `gather_with_semaphore` consumers: verify concurrency bounds, exception handling, log output
  - Client pool lifecycle: pool hit/miss/eviction, `aclose()` no-op, CB tuning
  - Delta checkpoint correctness: comparison test (full vs delta path), section isolation
  - Seeder passthrough: verify no double-fetch in lifecycle tests
- **Expected**: 8781+ tests pass (pre-existing failures excluded: `test_adversarial_pacing`, `test_paced_fetch`, `test_cache_errors_logged_as_warnings`)
- **Deliverable**: QA validation report with GO/CONDITIONAL-GO/NO-GO

### QA Gate 2 (After Sprint 4)

- **Scope**: All Sprint 3 + Sprint 4 commits (cumulative with Sprints 1-2)
- **Test command**: `.venv/bin/pytest tests/ -x -q --timeout=60`
- **Focus areas**:
  - Multi-PVP response parsing: canonical key mapping, partial failure handling, chunking
  - Business model test mocks: all opt_fields assertions updated for IMP-23
  - `from_attributes=True` correctness: verify `_capture_custom_fields_snapshot` still fires
  - DRY utility adoption consistency: CF extraction produces identical results
- **Expected**: 8781+ tests pass
- **Deliverable**: Final GO/NO-GO release recommendation

---

## Section 6: Handoff Contracts

### Principal-Engineer -> Main Agent (per invocation)

1. Committed code (all tests passing for the modified modules)
2. Specific test commands run and output summary
3. Any escalation notes (design deviations, unexpected complexity, test failures)

### Main Agent -> QA Adversary (at each gate)

1. Git diff since last gate: `git diff <last-gate-hash>..HEAD`
2. Test results: full suite output (`.venv/bin/pytest tests/ -x -q --timeout=60`)
3. Implementation notes: any deviations from this guide
4. List of all PE invocations completed since last gate

### Failure Recovery

| Scenario | Recovery |
|----------|----------|
| PE fails on a finding | Main agent re-consults Pythia with failure reason. Pythia may re-invoke PE with guidance or escalate to architect. |
| Design flaw discovered during implementation | PE escalates to main agent. Architect invoked for targeted revision of the specific finding. |
| Test infrastructure issue (unrelated failure) | Main agent fixes infrastructure issue, re-invokes PE for the failing finding only. |
| Finding proves more complex than sketched | PE completes what is feasible, documents the gap. Architect revises the sketch for a follow-up invocation. |
| QA gate finds regression | Architect reviews regression, determines root cause. PE invoked to fix. Gate is re-run. |
