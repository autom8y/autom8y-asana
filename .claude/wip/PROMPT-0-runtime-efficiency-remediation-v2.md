# PROMPT-0: Runtime Efficiency Remediation v2

## Initiative: INIT-RUNTIME-OPT-002

**Predecessor**: INIT-RUNTIME-REM-001 (shipped 6 commits: TTL fix, hierarchy traversal dedup, business cache, DRY section extraction, parallel freshness fetch, DEF-001 shadowing fix)

**Scope**: 30 findings (18 IMPLEMENT + 12 SPIKE) from a 5-domain first-principles architectural audit with adversarial strawman/steelman validation. 53 candidates evaluated; 23 rejected.

**Workflow**: Pythia-orchestrated 10x-dev. Pythia determines sprint structure via /zero consultation.

---

## Production Context (User-Confirmed)

| Dimension | Value | Impact |
|-----------|-------|--------|
| S2S vs PAT traffic | **>80% bot PAT (S2S)** | A1-01 is HIGH severity: resilience primitives non-functional for dominant traffic |
| Largest projects | **5000+ tasks, 20+ sections common** | Checkpoint/parallelization findings have real-world impact |
| Lifecycle transitions | **200+ per day** | API savings compound: 10 saved calls/transition = 2000/day |
| ConversationAudit | **Weekly, 200+ active holders** | ~200 API calls saved per weekly run |
| Test baseline | **8781+ tests** (pre-existing failures: test_adversarial_pacing, test_paced_fetch, test_cache_errors_logged_as_warnings) |

---

## Architectural Decisions (User-Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Client pool strategy** (A1-01) | Token-keyed pool with TTL eviction | S2S requests share one client (real rate limiting, CB, AIMD). User-PAT gets per-user clients. |
| **Concurrency pattern** | DRY utility: `gather_with_semaphore` in `core/concurrency.py` | Combines local Semaphore (sized per-callsite: 8-20) + transport AIMD. return_exceptions=True + structured logging. All 5 parallelization sites use it. |
| **Cross-service scope** | autom8_data changes ARE in scope | Multi-PVP batch endpoint modification feasible if spike confirms |
| **Template caching** | YAML config with runtime fallback | `template_section_gid` in lifecycle_stages.yaml; fall back to runtime discovery if absent |
| **Pydantic transforms** | `model_construct` acceptable for internal transforms | When data was already validated (Task -> ContactHolder), skip re-validation |
| **Boy Scout scope** | Fix + refactor touched modules | When modifying a file, refactor the entire module for consistency. Separate commit for boy-scout cleanup. |
| **QA gates** | After Sprint 0 (spikes) + after final sprint | 2 QA-adversary passes total |
| **Test strategy** | Targeted runs during sprints; full suite at QA gates | Run tests in modified modules during implementation |
| **Commit granularity** | Logical grouping: related findings per commit | Group findings touching same module. Cohesive changesets. |

---

## Sprint 0: Spikes (All 12, Time-Boxed)

Each spike produces a GO/NO-GO verdict with evidence. GO findings promote to IMPLEMENT in subsequent sprints.

### S0-SPIKE-01: Per-Request AsanaClient Defeats S2S Resilience (A1-01) — Score 72

**Files**: `api/dependencies.py:353-409`, `client.py:91-270`
**Question**: With >80% S2S traffic, the rate limiter, circuit breaker, and AIMD semaphore are created and destroyed per-request — they never accumulate state.
**Spike Goal**: Prototype token-keyed `ClientPool` with TTL eviction. Measure: (a) object creation overhead, (b) 429 rate under concurrent S2S load, (c) circuit breaker effectiveness with shared vs per-request client.
**GO criteria**: Shared client reduces 429s OR improves circuit breaker trip time by >50%.
**NO-GO criteria**: Token rotation or resource leak issues make pool management infeasible.

### S0-SPIKE-02: Multi-PVP Batch Insights to autom8_data (A1-08) — Score 58

**Files**: `clients/data/client.py:908-1059`
**Question**: `get_insights_batch_async` sends 1 HTTP request per PVP. The request body already has `phone_vertical_pairs` as a list field.
**Spike Goal**: (a) Check if autom8_data `/api/v1/data-service/insights` already supports multi-PVP in a single request. (b) If not, design the contract change. (c) Estimate savings for typical batch of 50 PVPs.
**GO criteria**: autom8_data supports (or can trivially support) multi-PVP; 50 HTTP calls -> 1.
**NO-GO criteria**: Response format cannot be keyed by PVP; requires major autom8_data refactor.

### S0-SPIKE-03: Sequential Section Reads During Merge (C2-003) — Score 55

**Files**: `dataframes/section_persistence.py:585-620`
**Spike Goal**: Measure real-world section counts and parquet sizes for 5 largest projects. Prototype `asyncio.gather` with Semaphore(5) for `read_all_sections_async`. Measure wall-clock and memory impact.
**GO criteria**: >3x wall-clock improvement for projects with 10+ sections, no memory spike >2x baseline.

### S0-SPIKE-04: Checkpoint Re-Extraction Amplification (D3-002) — Score 55

**Files**: `dataframes/builders/progressive.py:980-1048`
**Question**: Checkpoints re-extract ALL accumulated tasks. For 30k tasks over 6 checkpoints: 105k extractions vs 30k.
**Spike Goal**: Profile `_write_checkpoint` on a real 5000+ task section. Measure: (a) extraction time, (b) CPU attribution, (c) feasibility of incremental delta approach.
**GO criteria**: Checkpoint extraction is >20% of total build time for 5000+ task sections.

### S0-SPIKE-05: Business Double-Fetch in Upward Traversal (R4-009) — Score 55

**Files**: `models/business/hydration.py:684-716`
**Question**: Detection fetch uses `_DETECTION_OPT_FIELDS`, then re-fetches with `_BUSINESS_FULL_OPT_FIELDS` when Business is found.
**Spike Goal**: (a) Compare field sets — can detection work with full fields? (b) Measure if always fetching full fields at every level costs more than the 1 saved call.
**GO criteria**: Full-field-set at detection level adds <10% overhead to non-Business parents AND saves 1 call for Business.

### S0-SPIKE-06: Pydantic model_dump/model_validate Round-Trip (R4-001) — Score 52

**Files**: `models/business/holder_factory.py:308`, `models/business/business.py:582-616`
**Question**: Every holder population does `child_class.model_validate(task.model_dump())` — serialize then re-validate.
**Spike Goal**: Benchmark 3 approaches for 50-entity hydration: (a) current pattern, (b) `model_construct(**task.__dict__)`, (c) `model_validate(task, from_attributes=True)`. Decision: model_construct is acceptable for internal transforms.
**GO criteria**: Alternative is >3x faster AND passes all existing tests.

### S0-SPIKE-07: Duplicate Section Listing Across Lifecycle (A5-F01) — Score 52

**Files**: `automation/pipeline.py:691-696`, `lifecycle/creation.py:547-558`, `lifecycle/sections.py:181-183`, `lifecycle/reopen.py:177-180`
**Spike Goal**: Verify whether SectionsClient cache deduplicates these calls. Instrument section list calls with counters during a lifecycle transition. Measure actual API calls vs cache hits.
**GO criteria**: >2 cache misses per transition for the same project's sections.

### S0-SPIKE-08: S3 Batch GET Is Sequential (C2-006) — Score 52

**Files**: `cache/backends/s3.py:541-570`
**Spike Goal**: Measure cold-start frequency (how often does full S3 batch path execute vs Redis hot tier?). If frequent, prototype ThreadPoolExecutor(5) for S3 batch.
**GO criteria**: Cold-start S3 batch path executes >5 times/day AND >10 keys per batch on average.

### S0-SPIKE-09: Sequential Task Upgrades in Batch Path (C2-005) — Score 48

**Files**: `cache/providers/unified.py:330-386`
**Spike Goal**: Add telemetry to `get_batch_with_upgrade_async` to measure: (a) how often the upgrade path fires, (b) how many GIDs need upgrading per batch.
**GO criteria**: Upgrade path fires >50 times/day with >3 GIDs per batch on average.

### S0-SPIKE-10: TaskRow Triple Type Pass (D3-006) — Score 48

**Files**: `dataframes/extractors/base.py:132-198`, `dataframes/models/task_row.py:53-62`, `dataframes/builders/base.py:467,376-377`
**Spike Goal**: Profile Pydantic v2 `model_validate` + `model_dump` overhead for UnitRow (23 fields) at 2600 iterations. Compare: (a) current pipeline, (b) skip TaskRow, pass dicts directly with coercion only.
**GO criteria**: TaskRow validation accounts for >50ms per 2600-task build.

### S0-SPIKE-11: Batch API for Independent Configure Steps (A5-F11) — Score 42

**Files**: `automation/pipeline.py:316-454`, `lifecycle/creation.py:353-481`, `batch/client.py`
**Spike Goal**: Verify Asana batch API supports mixing section moves + task updates + assignee sets in a single batch. Check ordering guarantees.
**GO criteria**: Asana batch API executes mixed operations correctly; saves 2+ API calls per creation.

### S0-SPIKE-12: BaseHTTPMiddleware Overhead (A1-10) — Score 35

**Files**: `api/middleware.py:63-165`, `api/main.py:130-163`
**Spike Goal**: Instrument middleware stack with timing. Measure per-request overhead for health checks vs normal endpoints.
**GO criteria**: Middleware overhead is >5% of health check response time.

---

## IMPLEMENT Findings (18 Total)

### Tier 1: High Impact (Score >= 65)

#### IMP-01: ContactHolder parent_gid Passthrough (A5-F06) — Score 72

**Files**: `automation/workflows/conversation_audit.py:485-513, :349, :386`
**Fix**: Add `parent_gid: str | None = None` parameter to `_resolve_office_phone`. Pass from `_process_holder` (which already has it). Skip `tasks.get_async` when provided.
**Savings**: ~200 API calls per weekly audit run.

#### IMP-02: AutoCascadeSeeder/FieldSeeder Double-Fetch (A5-F10) — Score 68

**Files**: `lifecycle/seeding.py:105-113`, `automation/seeding.py:447-457`
**Fix**: `AutoCascadeSeeder.seed_async` fetches target task, then calls `FieldSeeder.write_fields_async` which fetches it again. Pass already-fetched `target_task` data as optional parameter to `write_fields_async`.
**Savings**: 2-3 API calls per lifecycle transition.

#### IMP-03: Sequential warm_cache_async (A1-02) — Score 68

**Files**: `client.py:875-910`
**Fix**: Accept `max_concurrency: int = 20`. Collect uncached GIDs, then `gather_with_semaphore(tasks, semaphore=Semaphore(max_concurrency))`. Transport AIMD provides secondary throttle.
**Savings**: 10x wall-time for cache warming (100 GIDs: 10s -> 1s).

#### IMP-04: Redis set_versioned Extra Round-Trips (C2-007) — Score 65

**Files**: `cache/backends/redis.py:451-471`
**Fix**: Move metadata HSET and EXPIRE into the existing pipeline. 2-line change. `set_batch` already does this correctly — align `_do_set_versioned` with it.
**Savings**: 1-2 fewer Redis round-trips per versioned write. Trivial fix.

#### IMP-05: Sequential Init Action Execution (A5-F02) — Score 65

**Files**: `lifecycle/engine.py:748-774`
**Fix**: Pre-resolve shared entities (business, context), then `gather_with_semaphore` independent actions. PlayCreation and EntityCreation are independent and make 5-7 API calls each.
**Savings**: 3-5s wall-clock per lifecycle transition.

### Tier 2: Medium Impact (Score 55-64)

#### IMP-06: Double Watermark Read in ProgressiveTier (C2-002) — Score 58

**Files**: `cache/dataframe/tiers/progressive.py:134-179`, `dataframes/storage.py:779-824`
**Fix**: Extend `load_dataframe` to return watermark metadata (or add `load_dataframe_with_metadata` variant). Eliminate separate `load_json` call for schema_version.
**Savings**: 33% fewer S3 GETs on cold-cache path.

#### IMP-07: Template Discovery Section Listing (A5-F04) — Score 58

**Files**: `automation/templates.py:100-161`, `lifecycle/creation.py:148-152,268-272`
**Fix**: Add optional `template_section_gid` to lifecycle YAML config. If present, skip `find_template_section_async`. Fall back to runtime discovery if absent.
**Savings**: 2-3 API calls per lifecycle transition.

#### IMP-08: Parallel apply_deltas_async (D3-005) — Score 58

**Files**: `dataframes/builders/freshness.py:231-284`
**Fix**: Replace sequential `for result in stale_results` with `gather_with_semaphore`. Each delta is independent (different sections, different S3 keys).
**Savings**: 1-5s when delta application triggers with multiple stale sections.

#### IMP-09: Sequential Watermark Loading at Startup (C2-001) — Score 72

**Files**: `dataframes/storage.py:891-914`
**Fix**: Replace sequential `for project_gid in project_gids` with `gather_with_semaphore(Semaphore(10))`. Watermark reads are idempotent and read-only.
**Savings**: Startup latency 10x reduction (50 projects: 5s -> 500ms).

#### IMP-10: Timeout Config (A1-09) — Score 55

**Files**: `transport/config_translator.py:76-83`, `config.py:213-242`
**Fix**: Pass all 4 timeout values (connect=5s, read=30s, write=30s, pool=10s) to the underlying httpx client. DataServiceClient already does this correctly.
**Savings**: Faster failure detection under degraded conditions (30s -> 5s for connect failures).

#### IMP-11: Parallel Project Enumeration (A5-F09) — Score 55

**Files**: `automation/workflows/pipeline_transition.py:226-326`
**Fix**: Replace sequential `for project_gid in project_gids` with `gather_with_semaphore(return_exceptions=True)`. Error handling is already per-project.
**Savings**: 3-5s wall-clock per pipeline transition execution.

### Tier 3: Lower Impact / DRY / Micro-Optimization (Score < 55)

#### IMP-12: Play Dependency N+1 Fix (A5-F12) — Score 48

**Files**: `lifecycle/init_actions.py:190-213`
**Fix**: Expand opt_fields to include `dependencies.memberships.project.gid`. Eliminate per-dependency task fetch loop.
**Savings**: 0-1 API calls per play creation.

#### IMP-13: Subtask Count Combine (A5-F05) — Score 45

**Files**: `automation/pipeline.py:316-319`, `lifecycle/creation.py:163-166,281-283`
**Fix**: Include subtask metadata in template discovery fetch (add `num_subtasks` to opt_fields). Or cache subtask count per template GID for Lambda invocation duration.
**Savings**: 1 API call per entity creation.

#### IMP-14: CustomFieldAccessor O(N) -> O(1) (R4-006) — Score 42

**Files**: `models/custom_field_accessor.py:91-112`
**Fix**: Add `_gid_to_field: dict[str, dict]` index in `_build_index()`. Change `get()` to use dict lookup instead of linear scan over `_data` list.
**Savings**: Eliminates O(N) scan per field access. ~50-200us per multi-field entity.

#### IMP-15: Double _task_to_dict Conversion (D3-001) — Score 42

**Files**: `dataframes/builders/progressive.py:635-652,:919-948,:1003-1008`
**Fix**: Compute `task_dicts` once before store population + DataFrame build. Pass pre-computed dicts to both `_populate_store_with_tasks` and `_build_section_dataframe`.
**Savings**: 5-200ms per section (CPU). Eliminates triple Pydantic model_dump at checkpoint.

#### IMP-16: HolderFactory Import Guard (R4-003) — Score 38

**Files**: `models/business/holder_factory.py:270-293`
**Fix**: Check `self.__class__.CHILD_TYPE is not Task` before dynamic import. Skip `importlib.import_module` when class already resolved.
**Savings**: ~10-20us per hydration. Makes lazy-load intent explicit.

#### IMP-17: Search Column Index Dedup (R4-002) — Score 35

**Files**: `search/service.py:555,678,649-658`
**Fix**: Compute `_build_column_index(df)` once in `find_async()`, pass to both `_build_filter_expr` and `_extract_hits`.
**Savings**: Microseconds per search. Code correctness.

#### IMP-18: CF Extraction DRY Consolidation (D3-009) — Score 30

**Files**: `dataframes/views/dataframe_view.py:471-517,742-792`, `dataframes/views/cascade_view.py:441-542`
**Fix**: Extract shared `extract_cf_value(cf_dict)` utility from duplicated `_extract_cf_value` / `_extract_field_value` methods in both view plugins.
**Savings**: Zero performance. Reduces bug surface area (percentage "0%" fix had to be applied twice).

---

## DRY Concurrency Primitive

### `core/concurrency.py` — `gather_with_semaphore`

All 5+ parallelization sites (IMP-03, IMP-05, IMP-08, IMP-09, IMP-11) should use a shared utility:

```python
async def gather_with_semaphore(
    coros: Iterable[Coroutine],
    *,
    concurrency: int = 10,
    return_exceptions: bool = True,
    label: str = "gather",
) -> list[Any]:
    """Execute coroutines with bounded concurrency.

    Combines local Semaphore with transport-layer AIMD for two-level throttling.
    Logs summary metrics via structured logging.
    """
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(coro):
        async with sem:
            return await coro

    results = await asyncio.gather(
        *[_bounded(c) for c in coros],
        return_exceptions=return_exceptions,
    )
    # Structured logging: succeeded/failed/total
    ...
    return results
```

Sized per-callsite: cache warming (20), watermarks (10), deltas (5), init actions (4), project enumeration (5).

---

## Boy Scout Scope

When modifying a file for a finding, refactor the entire module for consistency:
- Type hints, import ordering, docstring consistency
- Adjacent code smells in the same class/function
- Separate commit per finding + boy-scout cleanup within the same logical grouping
- Do NOT boy-scout files that are not touched by a finding

---

## Key File Index

| File | Findings | Lines |
|------|----------|-------|
| `client.py` | IMP-03 | 1045 |
| `cache/backends/redis.py` | IMP-04 | 788 |
| `cache/backends/s3.py` | S0-08 | 875 |
| `cache/providers/unified.py` | S0-09 | 908 |
| `cache/dataframe/tiers/progressive.py` | IMP-06 | ~300 |
| `dataframes/storage.py` | IMP-09 | 1107 |
| `dataframes/builders/progressive.py` | IMP-15, S0-04 | 1224 |
| `dataframes/builders/freshness.py` | IMP-08 | ~400 |
| `dataframes/section_persistence.py` | S0-03 | 905 |
| `dataframes/views/dataframe_view.py` | IMP-18 | 939 |
| `dataframes/views/cascade_view.py` | IMP-18 | ~550 |
| `dataframes/extractors/base.py` | S0-10 | 793 |
| `dataframes/models/task_row.py` | S0-10 | ~80 |
| `models/business/holder_factory.py` | IMP-16, S0-06 | ~310 |
| `models/business/business.py` | S0-06 | 813 |
| `models/business/hydration.py` | S0-05 | 818 |
| `models/custom_field_accessor.py` | IMP-14 | ~120 |
| `search/service.py` | IMP-17 | 743 |
| `api/dependencies.py` | S0-01 | ~420 |
| `api/middleware.py` | S0-12 | ~165 |
| `transport/config_translator.py` | IMP-10 | ~90 |
| `config.py` | IMP-10 | 725 |
| `automation/pipeline.py` | IMP-13 | 1083 |
| `automation/seeding.py` | IMP-02 | 923 |
| `automation/templates.py` | IMP-07 | ~165 |
| `automation/workflows/conversation_audit.py` | IMP-01 | ~530 |
| `automation/workflows/insights_export.py` | (boy scout only) | 899 |
| `automation/workflows/pipeline_transition.py` | IMP-11 | ~330 |
| `lifecycle/engine.py` | IMP-05 | 875 |
| `lifecycle/creation.py` | IMP-02, IMP-07, IMP-13 | 789 |
| `lifecycle/init_actions.py` | IMP-12 | ~220 |
| `lifecycle/seeding.py` | IMP-02 | ~190 |
| `clients/data/client.py` | S0-02 | 1812 |
| `batch/client.py` | S0-11 | ~200 |

---

## Constraints

- **Test baseline**: 8781+ tests. Pre-existing failures excluded: `test_adversarial_pacing.py`, `test_paced_fetch.py`, `test_parallel_fetch.py::test_cache_errors_logged_as_warnings`
- **Pytest path**: `.venv/bin/pytest tests/ -x -q --timeout=60` (NOT `uv run`)
- **Exception narrowing**: When narrowing catches, always check test mocks (`side_effect = Exception(...)` -> use `ConnectionError`)
- **Error tuples**: Defined in `core/exceptions.py`: `CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `SERIALIZATION_ERRORS`
- **Singleton resets**: Root conftest resets 4 registries: ProjectTypeRegistry, WorkspaceProjectRegistry, SchemaRegistry, EntityProjectRegistry
- **Prior shipped work** (do NOT re-implement):
  - TTL constant fix in sections.py
  - Hierarchy traversal dedup in strategies.py
  - Business dedup cache in insights_export.py
  - DRY section extraction consolidation in activity.py
  - Parallel freshness fetch with Semaphore(8) in freshness.py
  - DEF-001 variable shadowing fix in freshness.py

---

## Estimated Cumulative Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| API calls per lifecycle transition | ~25 | ~13 | **-48%** |
| API calls per ConversationAudit run | ~400+ | ~200 | **-50%** |
| Startup latency (50 projects) | ~5s | ~500ms | **10x** |
| Cache warming (100 GIDs) | ~10s | ~1s | **10x** |
| Lifecycle transition wall-clock | ~15s | ~5-8s | **2-3x** |
| Redis write round-trips | 3-4 per write | 1-2 per write | **-50%** |
| Cold-cache S3 GETs (ProgressiveTier) | 3 per read | 2 per read | **-33%** |

---

## Non-Prescriptive Note

This document defines WHAT to optimize and WHY. Sprint structure, phasing, and implementation sequencing are determined by Pythia via /zero consultation. The architect agents are empowered to:
- Re-score findings based on deeper analysis
- Merge or split findings as implementation reveals shared refactoring opportunities
- Promote SPIKE findings to IMPLEMENT (or demote) based on Sprint 0 evidence
- Apply Boy Scout principles to refactor touched modules beyond the minimum fix
