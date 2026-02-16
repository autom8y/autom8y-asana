# Sprint 0 Consolidated Verdicts: All 12 Spikes

**Initiative**: INIT-RUNTIME-OPT-002 (Runtime Efficiency Remediation v2)
**Phase**: Sprint 0 Complete
**Author**: Architect
**Date**: 2026-02-15

---

## Section 1: Executive Summary

| Metric | Count |
|--------|-------|
| Total spikes investigated | 12 |
| **GO** | 4 |
| **CONDITIONAL-GO** | 2 |
| **NO-GO** | 6 |
| Promoted to IMPLEMENT | 5 (4 GO + 1 NO-GO/promote) |

### Promoted Findings

5 spikes produced actionable results that should be implemented:

1. **S0-SPIKE-01** (GO): Client pool for S2S resilience -- all resilience primitives are non-functional today
2. **S0-SPIKE-02** (NO-GO/promote): Multi-PVP batch already supported by autom8_data -- trivial client-side refactor
3. **S0-SPIKE-03** (GO): Sequential section reads -- plain `for/await` loop, safe to parallelize with `gather_with_semaphore(5)`
4. **S0-SPIKE-04** (GO): Checkpoint re-extraction -- 4.5x amplification on 30k-task sections, delta approach eliminates waste
5. **S0-SPIKE-05** (GO): Business double-fetch -- detection fields are strict subset of full fields, eliminates 1 API call per resolution

Plus 2 CONDITIONAL-GO findings with lower net impact:

6. **S0-SPIKE-06** (CONDITIONAL-GO): Pydantic round-trip -- `from_attributes=True` as Phase 1, `model_construct` for read-only holders as Phase 2
7. **S0-SPIKE-10** (CONDITIONAL-GO): TaskRow triple pass -- low net impact because the progressive builder already bypasses TaskRow

### Demoted Findings (NO-GO)

5 spikes are definitively not worth pursuing:

1. **S0-SPIKE-07**: Duplicate section listing -- maximum 2 calls per project per transition; IMP-07 already eliminates the source of duplication
2. **S0-SPIKE-08**: S3 batch GET sequential -- cold path fires only on Redis misses (rare); synchronous protocol prevents clean parallelization
3. **S0-SPIKE-09**: Sequential task upgrades -- dead code with zero production callers
4. **S0-SPIKE-11**: Batch API for configure steps -- only 3 of 5-8 calls are independent; simpler to merge PUTs than use batch API
5. **S0-SPIKE-12**: BaseHTTPMiddleware overhead -- ~0.06ms per request (<0.01% of real endpoints); refactoring cost exceeds benefit

### Net Impact on Initiative Scope

- Original scope: 18 IMPLEMENT findings + 12 SPIKE investigations
- After Sprint 0: **23 IMPLEMENT findings** (18 original + 5 promoted) + 2 CONDITIONAL-GO deferred
- The 5 promoted findings add ~6-8 API calls saved per transition plus structural correctness improvements (client pool, checkpoint efficiency)

---

## Section 2: Full Verdict Table

| Spike ID | Title | Score | Verdict | Batch | Key Evidence | Action |
|----------|-------|-------|---------|-------|-------------|--------|
| S0-01 | Per-Request AsanaClient Defeats S2S Resilience | 72 | **GO** | B1 | All 6 resilience primitives (rate limiter, circuit breaker, AIMD x2) reset per request. >80% S2S traffic shares one PAT. Token-keyed pool is thread-safe. | Promote to IMP-19 |
| S0-02 | Multi-PVP Batch Insights | 58 | **NO-GO/promote** | B1 | autom8_data already accepts 1-1000 PVPs per request. autom8_asana client sends 1 PVP per HTTP call -- trivial refactor. | Promote to IMP-20 (score 72) |
| S0-03 | Sequential Section Reads During Merge | 55 | **GO** | B3 | Plain sequential `for/await` loop. Each section is independent S3 GET via `asyncio.to_thread()`. Zero shared mutable state. 5x speedup for 20-section projects. | Promote to IMP-21 |
| S0-04 | Checkpoint Re-Extraction Amplification | 55 | **GO** | B3 | Checkpoints re-extract ALL accumulated tasks. 4.5x amplification for 6-checkpoint sections (135k vs 30k extractions). Delta approach safe -- no ordering dependencies. ~9.5s saved. | Promote to IMP-22 |
| S0-05 | Business Double-Fetch in Upward Traversal | 55 | **GO** | B2 | Detection fields (4) are strict subset of full fields (16). Extra `custom_fields.*` adds <1% payload overhead on non-Business parents. Saves exactly 1 API call per Business resolution. | Promote to IMP-23 |
| S0-06 | Pydantic model_dump/model_validate Round-Trip | 52 | **CONDITIONAL-GO** | B2 | 20 call sites. Task model_validator (`_capture_custom_fields_snapshot`) does deepcopy -- must not skip for saveable objects. Phase 1: `from_attributes=True` (safe). Phase 2: `model_construct` for read-only holders only. | Deferred (Phase 1 low-risk, Phase 2 needs profiling) |
| S0-07 | Duplicate Section Listing Across Lifecycle | 52 | **NO-GO** | B4 | Maximum 2 calls per project per transition (template discovery + placement). Cascade calls target different projects. IMP-07 eliminates template discovery call. | No action |
| S0-08 | S3 Batch GET Is Sequential | 52 | **NO-GO** | B3 | Cold path fires only on Redis misses (rare in steady state). CacheProvider protocol is synchronous -- parallelization requires protocol-breaking changes or local threading hacks. | No action |
| S0-09 | Sequential Task Upgrades in Batch Path | 48 | **NO-GO** | B3 | `get_batch_with_upgrade_async` has ZERO callers in production code. Dead code. | No action |
| S0-10 | TaskRow Triple Type Pass | 48 | **CONDITIONAL-GO** | B3 | TaskRow adds ~100-130us/row via model_validate + model_dump. But progressive builder (high-volume path) already bypasses TaskRow via DataFrameViewPlugin. Base builder handles small datasets. Low net impact. | Deferred (low priority) |
| S0-11 | Batch API for Independent Configure Steps | 42 | **NO-GO** | B4 | Only 3 of 5-8 configure calls are independent. Those 3 PUTs can be merged into 1 regular PUT (simpler than batch API). Ordering dependencies prevent batching the rest. | No action |
| S0-12 | BaseHTTPMiddleware Overhead | 35 | **NO-GO** | B1 | ~0.06ms per request. 2 of 5 middleware use BaseHTTPMiddleware. For real endpoints (50-5000ms), overhead is <0.01%. Refactoring cost exceeds benefit. | No action |

---

## Section 3: Promoted to IMPLEMENT

### IMP-19: Token-Keyed Client Pool for S2S Resilience (from S0-SPIKE-01)

**Score**: 72
**Implementation sketch**:
- `ClientPool` keyed by token hash, stored on `app.state`
- S2S: single long-lived client (TTL 1hr), user-PAT: per-token client (TTL 5min)
- Modify `get_asana_client_from_context()` to look up pool, create on miss
- Remove yield/finally teardown (pool manages lifecycle)
- Max size 100, LRU + TTL eviction

**Suggested sprint grouping**: Sprint 1 (Foundation). This is the highest-severity finding -- all resilience primitives are non-functional for >80% of traffic. Pairs with IMP-10 (timeout config) since both touch the transport/client layer.

**Affected files**: `api/dependencies.py`, `api/main.py` or `api/lifespan.py`, new `api/client_pool.py`

**Dependencies**: None. Foundational change that other findings build on.

### IMP-20: Multi-PVP Batch Insights Client Refactor (from S0-SPIKE-02)

**Score**: 72 (upgraded from 58)
**Implementation sketch**:
- Refactor `get_insights_batch_async()` to collect all PVPs into a single request body
- Send one HTTP POST with up to 1000 PVPs (autom8_data already supports this)
- Parse response by `(office_phone, vertical)` key
- Handle HTTP 207 partial failures (already supported by autom8_data)

**Suggested sprint grouping**: Sprint 2. Pairs with other data-service client work. Independent of all other findings.

**Affected files**: `clients/data/client.py`

**Dependencies**: None. Self-contained client-side refactor.

### IMP-21: Parallel Section Reads with gather_with_semaphore (from S0-SPIKE-03)

**Score**: 55
**Implementation sketch**:
- Replace sequential `for` loop in `read_all_sections_async` with `gather_with_semaphore(5)`
- `return_exceptions=True` for graceful degradation
- Filter results (skip exceptions and None)
- Depends on `core/concurrency.py` DRY utility

**Suggested sprint grouping**: Sprint 1 or 2. Pairs with IMP-08 (parallel deltas) and IMP-09 (parallel watermarks) since all use `gather_with_semaphore` and touch the dataframes layer.

**Affected files**: `dataframes/section_persistence.py`, `core/concurrency.py` (shared)

**Dependencies**: Requires `gather_with_semaphore` utility (shared with IMP-03, IMP-05, IMP-08, IMP-09, IMP-11).

### IMP-22: Delta Checkpoint Extraction (from S0-SPIKE-04)

**Score**: 55
**Implementation sketch**:
- Add `_checkpoint_df` and `_checkpoint_task_count` instance state to progressive builder
- `_write_checkpoint`: extract only `tasks[checkpoint_task_count:]`, build delta_df, concatenate with previous checkpoint_df
- `_build_section_dataframe`: if checkpoint_df exists, extract only remaining delta and concatenate
- Key invariant: final DataFrame identical to current behavior

**Suggested sprint grouping**: Sprint 2. Pairs with IMP-15 (double _task_to_dict) since both modify `progressive.py` checkpoint/build paths.

**Affected files**: `dataframes/builders/progressive.py`

**Dependencies**: None. Self-contained optimization within progressive builder.

### IMP-23: Unified Field Set for Business Detection (from S0-SPIKE-05)

**Score**: 55
**Implementation sketch**:
- Change detection fetch to use `STANDARD_TASK_OPT_FIELDS` instead of `DETECTION_OPT_FIELDS` in `hydration.py`
- Eliminate re-fetch when Business is found (already have full fields)
- Update api_calls accounting
- Remove `_DETECTION_OPT_FIELDS` alias from `hydration.py`

**Suggested sprint grouping**: Sprint 2. Pairs with S0-06 (Pydantic round-trip) since both modify the business model layer.

**Affected files**: `models/business/hydration.py`, test mocks in `tests/unit/models/business/`

**Dependencies**: None. Self-contained optimization within hydration module.

---

## Section 4: Revised Impact Estimates

### API Calls per Lifecycle Transition

| Source | Before | After | Delta |
|--------|--------|-------|-------|
| Original IMP findings (IMP-01 through IMP-18) | ~25 | ~13 | -12 |
| IMP-19 (client pool) | -- | -- | No API call change; resilience improvement |
| IMP-23 (business double-fetch) | -- | -- | -1 per Business resolution |
| S0-07 (section dedup) | -- | -- | 0 (NO-GO; addressed by IMP-07) |
| S0-11 (batch configure) | -- | -- | 0 (NO-GO) |
| **Revised total** | **~25** | **~12** | **-52%** |

### API Calls per ConversationAudit Run

| Source | Before | After | Delta |
|--------|--------|-------|-------|
| Original estimate | ~400+ | ~200 | -200 |
| IMP-23 (business double-fetch) | -- | -- | -200 (1 call saved per resolution x 200 holders) |
| **Revised total** | **~400+** | **~100** | **-75%** |

### Startup Latency (50 projects)

| Source | Before | After |
|--------|--------|-------|
| Original estimate (IMP-09 watermarks) | ~5s | ~500ms |
| IMP-21 (parallel section reads) | Additional cold-path benefit | ~200ms further reduction on section merge |
| **Revised total** | **~5s** | **~300ms** |

### Progressive Builder (30k tasks, 6 checkpoints)

| Source | Before | After |
|--------|--------|-------|
| IMP-22 (delta checkpoints) | ~12.15s extraction | ~2.7s extraction |
| IMP-15 (double _task_to_dict) | Stacks with IMP-22 | Additional 200-400ms saved |
| **Revised total** | **~12.15s** | **~2.3s (5.3x improvement)** |

### Client Resilience (new metric from IMP-19)

| Metric | Before (per-request client) | After (pooled client) |
|--------|---------------------------|----------------------|
| Rate limiter effectiveness | Non-functional (resets per request) | Functional (shared token bucket) |
| Circuit breaker effectiveness | Non-functional (failure_count always 0) | Functional (trips on sustained failures) |
| AIMD concurrency control | Non-functional (window always at ceiling) | Functional (adapts to 429 signals) |
| httpx connection pooling | Defeated (new client per request) | Effective (reused across requests) |

### Multi-PVP Batch (new metric from IMP-20)

| Metric | Before | After |
|--------|--------|-------|
| HTTP calls per 50-PVP batch | 50 | 1 |
| Wall-clock per batch | ~5s | ~100ms |
| Improvement | -- | **50x** |

### Cumulative Impact Summary (Revised)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| API calls per lifecycle transition | ~25 | ~12 | **-52%** (was -48%) |
| API calls per ConversationAudit run | ~400+ | ~100 | **-75%** (was -50%) |
| Startup latency (50 projects) | ~5s | ~300ms | **17x** (was 10x) |
| Cache warming (100 GIDs) | ~10s | ~1s | **10x** (unchanged) |
| Lifecycle transition wall-clock | ~15s | ~5-8s | **2-3x** (unchanged) |
| Redis write round-trips | 3-4 per write | 1-2 per write | **-50%** (unchanged) |
| Cold-cache S3 GETs (ProgressiveTier) | 3 per read | 2 per read | **-33%** (unchanged) |
| Multi-PVP batch HTTP calls | 50 per batch | 1 per batch | **50x** (new) |
| Progressive builder extraction (30k) | ~12.15s | ~2.3s | **5.3x** (new) |
| Client resilience primitives | Non-functional | Functional | **Qualitative** (new) |

---

## Section 5: Implementation Sprint Recommendations

### Sprint 1: Foundation + DRY Utility + Highest Impact

**Theme**: Establish shared infrastructure and fix the highest-severity issues.

| Finding | Files | Notes |
|---------|-------|-------|
| **DRY utility**: `gather_with_semaphore` | `core/concurrency.py` (new) | Prerequisite for 6+ parallelization findings |
| **IMP-19**: Client pool | `api/dependencies.py`, `api/client_pool.py` (new), `api/main.py` | Highest severity: all resilience non-functional |
| **IMP-04**: Redis pipeline fix | `cache/backends/redis.py` | Trivial 2-line fix; ship early |
| **IMP-10**: Timeout config | `transport/config_translator.py`, `config.py` | Small, pairs with client pool work |
| **IMP-09**: Parallel watermark loading | `dataframes/storage.py` | Uses `gather_with_semaphore`; high startup impact |
| **IMP-03**: Parallel cache warming | `client.py` | Uses `gather_with_semaphore`; 10x improvement |

**Parallelization note**: IMP-04 and IMP-10 touch independent files and can be done concurrently. IMP-09 and IMP-03 both depend on the DRY utility being available.

**Logical commit grouping**:
1. `core/concurrency.py` + tests (shared utility)
2. `api/client_pool.py` + `api/dependencies.py` + `api/main.py` (IMP-19)
3. `cache/backends/redis.py` (IMP-04)
4. `transport/config_translator.py` + `config.py` (IMP-10)
5. `dataframes/storage.py` (IMP-09)
6. `client.py` (IMP-03)

### Sprint 2: Lifecycle + Dataframes

**Theme**: Reduce API calls per lifecycle transition and optimize progressive builder.

| Finding | Files | Notes |
|---------|-------|-------|
| **IMP-01**: ContactHolder parent_gid passthrough | `automation/workflows/conversation_audit.py` | ~200 calls saved per audit |
| **IMP-02**: Seeder double-fetch | `lifecycle/seeding.py`, `automation/seeding.py` | 2-3 calls per transition |
| **IMP-05**: Parallel init actions | `lifecycle/engine.py` | Uses `gather_with_semaphore`; 3-5s savings |
| **IMP-07**: Template section GID config | `automation/templates.py`, `lifecycle/creation.py` | 2-3 calls per transition |
| **IMP-11**: Parallel project enumeration | `automation/workflows/pipeline_transition.py` | Uses `gather_with_semaphore`; 3-5s savings |
| **IMP-22**: Delta checkpoint extraction | `dataframes/builders/progressive.py` | 5.3x improvement on large sections |
| **IMP-15**: Double _task_to_dict | `dataframes/builders/progressive.py` | Same file as IMP-22; commit together |

**Logical commit grouping**:
1. `automation/workflows/conversation_audit.py` (IMP-01)
2. `lifecycle/seeding.py` + `automation/seeding.py` (IMP-02)
3. `lifecycle/engine.py` (IMP-05)
4. `automation/templates.py` + `lifecycle/creation.py` (IMP-07)
5. `automation/workflows/pipeline_transition.py` (IMP-11)
6. `dataframes/builders/progressive.py` (IMP-22 + IMP-15 together)

### Sprint 3: Data Service + Models + Cleanup

**Theme**: Cross-service optimization, model layer improvements, and remaining findings.

| Finding | Files | Notes |
|---------|-------|-------|
| **IMP-20**: Multi-PVP batch | `clients/data/client.py` | 50x HTTP reduction for batch insights |
| **IMP-23**: Business double-fetch | `models/business/hydration.py` | 1 call saved per resolution; many test mock updates |
| **IMP-08**: Parallel deltas | `dataframes/builders/freshness.py` | Uses `gather_with_semaphore` |
| **IMP-21**: Parallel section reads | `dataframes/section_persistence.py` | Uses `gather_with_semaphore` |
| **IMP-06**: Double watermark read | `cache/dataframe/tiers/progressive.py`, `dataframes/storage.py` | 33% fewer S3 GETs |
| **IMP-12**: Play dependency N+1 | `lifecycle/init_actions.py` | Small opt_fields expansion |
| **IMP-13**: Subtask count combine | `automation/pipeline.py`, `lifecycle/creation.py` | 1 call per creation |

### Sprint 4: Micro-Optimizations + DRY

**Theme**: Low-impact correctness and cleanup findings.

| Finding | Files | Notes |
|---------|-------|-------|
| **IMP-14**: CustomFieldAccessor O(1) | `models/custom_field_accessor.py` | Dict index for GID lookup |
| **IMP-16**: HolderFactory import guard | `models/business/holder_factory.py` | Skip importlib when resolved |
| **IMP-17**: Search column index dedup | `search/service.py` | Microseconds; code correctness |
| **IMP-18**: CF extraction DRY | `dataframes/views/dataframe_view.py`, `dataframes/views/cascade_view.py` | Zero perf; reduces bug surface |
| **S0-06 Phase 1**: from_attributes=True | `models/business/` (multiple) | Low-risk Pydantic optimization |

### QA Gates

Per architectural decision: 2 QA-adversary passes total.
- **QA Gate 1**: After Sprint 2 (covers foundation + lifecycle changes)
- **QA Gate 2**: After Sprint 4 (final validation, full suite)

---

## Section 6: Risks and Open Questions

### Risks Discovered During Investigation

1. **IMP-19 (Client Pool) -- Token rotation**: If the bot PAT rotates via Lambda extension secret refresh, pooled clients hold the old token until TTL eviction. **Mitigation**: 1-hour TTL provides natural rotation; `pool.invalidate_all()` available for immediate rotation.

2. **IMP-22 (Delta Checkpoints) -- DataFrame concatenation order**: Delta approach relies on `pl.concat` preserving row order. This is the default behavior, but must be explicitly verified in tests.

3. **IMP-23 (Business Double-Fetch) -- Test mock updates**: ~5 test files mock `opt_fields=DETECTION_OPT_FIELDS` at detection call sites. All must be updated to `STANDARD_TASK_OPT_FIELDS`. Risk of test-only regressions if mocks are missed.

4. **S0-06 Phase 2 (model_construct) -- Change detection breakage**: `model_construct` skips `_capture_custom_fields_snapshot` validator. If any downstream code calls `model_dump()` or `save_async()` on a constructed entity, it produces incorrect change detection. **Mitigation**: Phase 2 is deferred; only apply to definitively read-only holders.

5. **gather_with_semaphore adoption risk**: 6+ findings depend on this shared utility. A bug in the utility propagates to all consumers. **Mitigation**: Comprehensive unit tests for the utility itself, including edge cases (empty list, all-exceptions, partial failures).

### Unresolved Questions

1. **S0-06 Phase 1 vs Phase 2 prioritization**: `from_attributes=True` provides moderate speedup with no validator concerns. `model_construct` provides maximum speedup but requires careful auditing of all code paths that touch constructed entities. **Recommendation**: Ship Phase 1 in Sprint 4; defer Phase 2 to post-initiative profiling.

2. **S0-10 (TaskRow) production usage**: The CONDITIONAL-GO verdict hinges on whether the base builder path handles large datasets in production. If all large sections use the progressive builder (which bypasses TaskRow), this optimization has near-zero impact. **Recommendation**: Defer unless profiling reveals base builder as a bottleneck.

3. **IMP-19 pool sizing**: Max pool size of 100 is conservative. If user PAT diversity is higher than expected (e.g., >100 concurrent unique PATs), the LRU eviction may cause excessive churn. **Recommendation**: Add metrics to track pool hit rate and size.

### Dependencies Between Promoted Findings and Existing IMP Findings

| Promoted | Depends On | Reason |
|----------|-----------|--------|
| IMP-21 (parallel sections) | `gather_with_semaphore` (DRY utility) | Uses the shared concurrency primitive |
| IMP-22 (delta checkpoints) | None | Self-contained in progressive builder |
| IMP-23 (business double-fetch) | None | Self-contained in hydration module |
| IMP-22 + IMP-15 | Same file (`progressive.py`) | Should be implemented and committed together to avoid merge conflicts |
| IMP-19 + IMP-10 | Logical pairing | Both touch transport/client layer; test together |

### Cross-File Dependency Map

Files touched by multiple findings (merge conflict risk):

| File | Findings | Sprint |
|------|----------|--------|
| `dataframes/builders/progressive.py` | IMP-15, IMP-22 | Sprint 2 (commit together) |
| `lifecycle/creation.py` | IMP-02, IMP-07, IMP-13 | Sprint 2-3 (different methods, low conflict) |
| `automation/pipeline.py` | IMP-13 | Sprint 3 |
| `dataframes/storage.py` | IMP-06, IMP-09 | Sprint 1 + 3 (different methods) |
| `models/business/holder_factory.py` | IMP-16, S0-06 | Sprint 4 (commit together) |
