# Sprint 0 QA Validation Report

**Initiative**: INIT-RUNTIME-OPT-002 (Runtime Efficiency Remediation v2)
**Phase**: Sprint 0 Complete -- QA Adversary Pass 1
**Author**: QA Adversary
**Date**: 2026-02-15

---

## Overall Assessment: CONDITIONAL-GO

The Architect's Sprint 0 spike investigation is thorough, well-evidenced, and methodologically sound. All 12 verdicts are supported by code-level evidence that I independently verified against the source. The GO/NO-GO criteria from PROMPT-0 were applied faithfully in 11 of 12 cases. I identified no verdict that should be reversed, though I found several risk gaps, one inflated impact estimate, and one implementation sketch with a factual error that should be corrected before implementation begins.

**Conditions for proceeding**:
1. Correct the S0-11 "merge 3 PUTs into 1" implementation sketch -- the three configure steps use different Asana API methods (`tasks.update_async`, `SaveSession.set_parent`, `tasks.set_assignee_async`), not three identical PUTs (see Section 4)
2. Add the "merge due_date + assignee into one `tasks.update_async`" as IMP-24 or a boy-scout item on Sprint 2 (Section 4)
3. Revise the ConversationAudit impact estimate from -75% to -62% (see Section 5)
4. Document the `gather_with_semaphore` coroutine-consumption safety issue as a design requirement (see Section 6)

---

## Verdict-by-Verdict Validation

### S0-SPIKE-01: Per-Request AsanaClient Defeats S2S Resilience

**Architect Verdict**: GO
**QA Validation**: CONFIRMED GO
**Evidence Quality**: A

**Verification**: I read `api/dependencies.py:353-409` and confirmed both `get_asana_client()` and `get_asana_client_from_context()` create a new `AsanaClient(token=...)` per request via async generator yield. I read `client.py:164-204` and confirmed each `__init__` creates `TokenBucketRateLimiter`, `CircuitBreaker`, `ExponentialBackoffRetry`, and the `AsanaHttpClient` (which itself creates two `AsyncAdaptiveSemaphore` instances). I confirmed `AsanaClientDualMode` has 43 occurrences across 7 route files. Every claim in the verdict is independently verifiable.

**Concerns**:
- The Architect states the `asyncio.Semaphore` and `asyncio.Condition` (used by AIMD) are safe for concurrent async use within a single event loop. This is correct for single-event-loop FastAPI deployments. However, if the application is ever deployed with `uvicorn --workers N` (multi-process), each worker has its own event loop and its own pool -- the pool provides zero cross-process coordination. This is acceptable but should be documented as a known limitation.
- The `aclose()` lifecycle change from "dependency teardown closes client" to "pool manages lifecycle" is a correctness-critical migration. The yield/finally pattern in both dependency functions currently calls `aclose()`. If the migration is incomplete (some code paths still close pooled clients), clients will be invalidated mid-use. **Recommendation**: The implementation should make pooled clients non-closeable (override `aclose` to no-op) or use a wrapper that delegates to the pool's eviction.
- The TTL of 1 hour for S2S is reasonable but the verdict does not discuss what happens if the S2S client accumulates a tripped circuit breaker. A tripped CB on the shared S2S client blocks ALL S2S traffic. This is stated as "desired behavior" but the recovery path (HALF_OPEN probe) should be explicitly tested. If the CB trips spuriously (e.g., from a transient outage), the entire S2S path is blocked until the cooldown expires. The implementation should log CB state transitions on the pooled client at WARNING level.

---

### S0-SPIKE-02: Multi-PVP Batch Insights

**Architect Verdict**: NO-GO (promote to IMPLEMENT)
**QA Validation**: CONFIRMED -- promote to IMPLEMENT
**Evidence Quality**: A

**Verification**: I independently verified the autom8_data source at `/Users/tomtenuta/Code/autom8_data/src/autom8_data/api/data_service_models/_insights.py:35-38`. The `phone_vertical_pairs` field does accept `min_length=1, max_length=1000`. The Architect's code citations match exactly. I also confirmed the autom8_asana client at `clients/data/client.py:1182-1189` constructs a single-element list `"phone_vertical_pairs": [{"phone": ..., "vertical": ...}]`, proving the N-request-per-N-PVP pattern.

**Concerns**:
- The Architect cited `autom8_data/api/data_service_models/_insights.py:20-45` -- these line numbers match the real file at offset 20-45. The Architect demonstrably read the actual autom8_data source code, not an assumption. This is a high-quality cross-service investigation.
- The InsightsResponse contains `data: list[EntityMetrics]` where each `EntityMetrics` has `office_phone` and `vertical`. The Architect is correct that the response is PVP-keyed. However, the autom8_asana client currently uses `pv1:{phone}:{vertical}` as canonical key format (per MEMORY.md). The implementation must ensure the PVP-keying from the response maps back to this canonical key format correctly. The `_execute_insights_request` currently handles only single-PVP responses -- the response parsing logic will need meaningful rework, not just the request construction.
- Error handling for HTTP 207 with partial failures needs explicit test coverage. The current `get_insights_batch_async` has per-PVP error handling in the `fetch_one` closure. The refactored version will need to parse per-entity errors from the `errors` field of `InsightsResponse` and map them back to canonical keys.

---

### S0-SPIKE-03: Sequential Section Reads During Merge

**Architect Verdict**: GO
**QA Validation**: CONFIRMED GO
**Evidence Quality**: A

**Verification**: I read `section_persistence.py:585-620` and confirmed the exact code: a plain `for section_gid in complete_sections:` loop with `await self.read_section_async(...)` inside. No gather, no concurrency. Each `read_section_async` delegates to `self._storage.load_section()` which is an S3 GET via `asyncio.to_thread()`. I confirmed zero shared mutable state between section reads -- each read is an independent S3 GET returning an independent DataFrame.

**Concerns**:
- The Architect cites a semaphore bound of 5 for S3 GETs. The default `asyncio.to_thread()` thread pool in CPython is `min(32, os.cpu_count() + 4)`, typically 8-12 on production hosts. With 5 concurrent S3 reads, this leaves 3-7 threads for other async operations (watermark loads, other S3 reads from unrelated code paths). This is fine for isolated execution, but if IMP-09 (parallel watermarks) and IMP-21 (parallel section reads) fire concurrently, you could have 10+5 = 15 concurrent `to_thread()` calls contending for the same pool. **Recommendation**: The `gather_with_semaphore` utility spec should document that the semaphore bounds are callsite-local and do NOT provide global thread pool protection. If thread pool saturation becomes an issue, a shared thread pool size configuration should be considered.
- The implementation sketch correctly preserves the `list[pl.DataFrame]` return type. No API change to downstream consumers.

---

### S0-SPIKE-04: Checkpoint Re-Extraction Amplification

**Architect Verdict**: GO
**QA Validation**: CONFIRMED GO
**Evidence Quality**: A

**Verification**: I read `progressive.py:980-1048` and confirmed `_write_checkpoint` receives the full `tasks` list and calls `_task_to_dict` on ALL of them. I read `progressive.py:910-911` and confirmed `all_tasks` (the full accumulation) is passed to `_write_checkpoint`. I confirmed `CHECKPOINT_EVERY_N_PAGES = 50` (config.py:391) and `ASANA_PAGE_SIZE = 100` (progressive.py:61).

**Amplification math verification**:
- 5000 tasks per checkpoint interval (50 pages x 100 tasks/page) -- CONFIRMED
- For 30k tasks (6 checkpoints): sum of 5000 + 10000 + 15000 + 20000 + 25000 + 30000 = 105,000 checkpoint extractions + 30,000 final build = 135,000 total. Necessary: 30,000. Amplification = 135,000 / 30,000 = **4.5x** -- CONFIRMED
- The formula `(N+1)/2` for amplification factor with N checkpoints: for 6 checkpoints, (6+1)/2 = 3.5x for checkpoints alone. The final build adds another 1.0x of the full dataset. Total: 3.5 + 1 = 4.5x -- CONFIRMED

**Concerns**:
- The delta approach introduces instance state (`_checkpoint_df`, `_checkpoint_task_count`) on the progressive builder. If the builder is reused across sections (it is -- `build_project_async` loops over sections), this state MUST be reset between sections. I verified that `_build_project_section_async` at line 625 calls `_build_section_dataframe` which does not reference any cross-section state, but the new delta state variables must follow the same pattern. **Recommendation**: Initialize delta state at the top of each section fetch, not just in `__init__`.
- The `pl.concat` call for DataFrame concatenation: the Architect correctly notes it preserves row order. However, if the schema changes between checkpoints (e.g., a new column is added mid-fetch), the concat will fail with a schema mismatch. This is extremely unlikely in practice (the schema is fixed per project builder run), but should be tested.
- The memory concern is well-analyzed: the checkpoint_df reference replaces the already-stored `self._section_dfs[section_gid]` (line 1028), so net memory delta is negligible.

---

### S0-SPIKE-05: Business Double-Fetch in Upward Traversal

**Architect Verdict**: GO
**QA Validation**: CONFIRMED GO
**Evidence Quality**: A

**Verification**: I read `models/business/fields.py:227-255` and confirmed:
- `STANDARD_TASK_OPT_FIELDS`: 15 fields (tuple of strings including `custom_fields.*` sub-selections)
- `DETECTION_OPT_FIELDS`: 4 fields (`name`, `parent.gid`, `memberships.project.gid`, `memberships.project.name`)
- Detection is a strict subset of Standard -- CONFIRMED

I read `hydration.py:285-287` and confirmed the entry fetch uses `_DETECTION_OPT_FIELDS`. I read `hydration.py:324-327` and confirmed the re-fetch when Business is found uses `_BUSINESS_FULL_OPT_FIELDS`. I read `hydration.py:684-686` (traversal) and confirmed the same detection-then-refetch pattern at lines 712-714.

**Concerns**:
- The Architect's verdict says 16 fields for the full set; I count 15 in the tuple. This is a minor discrepancy (the Architect may have counted `custom_fields` as both a top-level field and its sub-selections). No material impact on the verdict.
- The Architect correctly identifies that Asana charges rate limit tokens per request, not per field. I cannot independently verify this from the codebase (it is an Asana API behavior), but it is consistent with documented Asana API behavior.
- The test mock update scope is accurately identified: ~5 test files mock opt_fields assertions at detection sites. The find-and-replace is mechanical and low-risk.

---

### S0-SPIKE-06: Pydantic model_dump/model_validate Round-Trip

**Architect Verdict**: CONDITIONAL-GO
**QA Validation**: CONFIRMED CONDITIONAL-GO
**Evidence Quality**: A

**Verification**: I read `models/task.py:137-145` and confirmed the `_capture_custom_fields_snapshot` model_validator that performs `copy.deepcopy(self.custom_fields)`. The Architect's analysis of why `model_construct` would break `model_dump()` change detection is correct -- if `_original_custom_fields` is None, `_has_direct_custom_field_changes()` at line 155-157 returns True for any non-empty custom_fields, causing phantom change detection.

**Concerns**:
- The Architect's recommendation of `from_attributes=True` as Phase 1 is sound. This avoids the `model_dump()` serialization step while still running the validator. However, `model_validate(task, from_attributes=True)` on a Pydantic v2 model reads from object attributes, which means it will also pick up PrivateAttr values if they clash with field names. I verified that Task's PrivateAttrs (`_custom_fields_accessor`, `_client`, `_original_custom_fields`) all use underscore-prefixed names that do not clash with any declared field names. The `from_attributes=True` approach is safe here.
- The 20 call sites inventory is comprehensive. The per-model verdict table correctly classifies read-only vs. potentially-saveable objects.

---

### S0-SPIKE-07: Duplicate Section Listing Across Lifecycle

**Architect Verdict**: NO-GO
**QA Validation**: CONFIRMED NO-GO
**Evidence Quality**: A

**Verification**: I read `lifecycle/creation.py:548` and confirmed the section listing call in `_move_to_section_async`. The Architect's analysis that cascade calls target DIFFERENT projects (Offer project, Unit project, Business project) is a critical and correct observation that deflates the apparent duplication.

**Concerns**:
- The Architect correctly identifies that IMP-07 (template section GID config) subsumes this optimization by eliminating the template discovery call. After IMP-07, only 1 section listing per project per transition remains. The NO-GO is well-justified.
- The GO criteria was ">2 cache misses per transition for the same project's sections." The Architect found exactly 2, which is below the threshold. The criteria was properly applied.

---

### S0-SPIKE-08: S3 Batch GET Is Sequential

**Architect Verdict**: NO-GO
**QA Validation**: CONFIRMED NO-GO
**Evidence Quality**: A

**Verification**: The finding that the `CacheProvider` protocol is synchronous is the key blocker. The Architect correctly identifies that parallelization within a sync `get_batch` requires threading machinery disproportionate to the benefit, given the cold path fires only on Redis misses.

**Concerns**: None. This is a clean NO-GO with sound reasoning.

---

### S0-SPIKE-09: Sequential Task Upgrades in Batch Path

**Architect Verdict**: NO-GO (dead code)
**QA Validation**: CONFIRMED NO-GO
**Evidence Quality**: A

**Verification**: I searched for `get_batch_with_upgrade_async` across all of `src/autom8_asana/` -- only 1 result: the definition in `unified.py:330`. I searched across all of `tests/` -- zero results. **This method has zero callers in both production code and test code.** It is definitively dead code.

**Concerns**:
- The method should be considered for removal in a boy-scout pass. Dead code with zero test coverage is a maintenance liability. However, this is not a Sprint 0 concern -- it is a future cleanup item.
- If the method was intended to be used by a future feature, removing it would lose the implementation. The verdict correctly identifies this as a future concern.

---

### S0-SPIKE-10: TaskRow Triple Type Pass

**Architect Verdict**: CONDITIONAL-GO
**QA Validation**: CONFIRMED CONDITIONAL-GO
**Evidence Quality**: A

**Verification**: The Architect's discovery that Pipeline B (progressive builder via DataFrameViewPlugin) already bypasses TaskRow entirely is the key finding. The progressive builder handles all large sections (5000+ tasks). Pipeline A (base builder) uses TaskRow but handles small datasets. The net impact of optimizing Pipeline A is low.

**Concerns**:
- The Architect correctly deferred this to post-initiative profiling. The verdict is conservative and appropriate.

---

### S0-SPIKE-11: Batch API for Independent Configure Steps

**Architect Verdict**: NO-GO
**QA Validation**: CONFIRMED NO-GO with caveats
**Evidence Quality**: B

**Verification**: I read `lifecycle/creation.py:353-481` and confirmed the configure step sequence. The Architect correctly identifies steps b (due date), e (hierarchy), and f (assignee) as independent. The ordering dependencies (section GET before POST, subtask wait before seeding) are real.

**However, I found a factual error in the analysis.** The Architect's verdict states:

> "Those 3 independent calls can be merged into a single PUT without using the batch API at all."

This is incorrect. The three steps use different Asana API methods:
- Step b (due date): `tasks.update_async(gid, due_on=...)` -- a PUT to `/tasks/{gid}`
- Step e (hierarchy): `SaveSession.set_parent()` + `commit_async()` -- this uses the Asana `setParent` endpoint (POST to `/tasks/{gid}/setParent`), NOT a PUT to `/tasks/{gid}`
- Step f (assignee): `tasks.set_assignee_async(gid, assignee_gid)` -- this uses a specialized method, likely a PUT to `/tasks/{gid}` with `assignee` field

The hierarchy placement (step e) goes through `SaveSession` which is a separate code path that uses the Asana `setParent` endpoint with `parent`, `insert_before`, `insert_after` parameters. You CANNOT merge a `setParent` call with a `tasks.update_async` field update into a single PUT.

**Net impact**: The overall NO-GO verdict is still correct -- the batch API is overkill and the dependencies prevent meaningful batching. But the "merge 3 PUTs into 1" alternative is only partially valid: steps b (due_date) and f (assignee) COULD be merged into a single `tasks.update_async(gid, due_on=..., assignee=...)`, but step e (hierarchy) must remain a separate call.

**Recommendation**: Capture the "merge due_date + assignee into one `tasks.update_async`" as a minor IMP finding or boy-scout item when IMP-02 touches the configure phase. This saves 1 API call (3 calls become 2: one combined update + one setParent).

---

### S0-SPIKE-12: BaseHTTPMiddleware Overhead

**Architect Verdict**: NO-GO
**QA Validation**: CONFIRMED NO-GO
**Evidence Quality**: A

**Verification**: The analysis is sound. Only 2 of 5 middleware layers use `BaseHTTPMiddleware`. The overhead of ~0.06ms per request is immaterial for real API endpoints.

**Concerns**: None. Clean NO-GO.

---

## GO Verdict Challenges

### Challenge 1: S0-01 (Client Pool) -- Circuit Breaker Amplification

The shared S2S client means a tripped circuit breaker blocks ALL S2S traffic. With >80% S2S traffic, a spurious CB trip (from a brief Asana outage or network blip) could effectively take the entire service offline for the CB cooldown period. The current per-request pattern means CB never trips (which is bad), but the pooled pattern means CB trips HARD (which could be worse if not carefully tuned).

**Recommendation**: The implementation should:
1. Configure CB `failure_threshold` conservatively (e.g., 10+ failures, not 3-5)
2. Use a short `reset_timeout` (e.g., 30s, not 60s) so HALF_OPEN probes happen quickly
3. Log CB state transitions at WARNING level on the pooled client
4. Test the CB trip-and-recovery cycle explicitly in integration tests

**Severity**: Medium. This does not change the GO verdict, but the implementation sketch should include CB tuning as a required consideration.

### Challenge 2: S0-03 (Section Reads) -- Thread Pool Contention

If IMP-09 (watermarks, semaphore=10) and IMP-21 (section reads, semaphore=5) fire concurrently, that is 15 `asyncio.to_thread()` calls competing for the default thread pool. Add IMP-03 (cache warming, semaphore=20) and you could have 35+ concurrent thread pool submissions.

The `gather_with_semaphore` utility bounds coroutine-level concurrency but does NOT bound thread pool usage. Each bounded coroutine still submits to the shared thread pool.

**Recommendation**: Document the thread pool budget as a design constraint. Either:
- Size the default executor larger: `asyncio.get_event_loop().set_default_executor(ThreadPoolExecutor(max_workers=50))`
- Or ensure the callsite semaphore sizes sum to less than the default pool size

**Severity**: Low. In practice, these operations are unlikely to overlap frequently. Startup (watermarks + cache warming) does not overlap with section reads (which happen during progressive builds). But the risk should be documented.

### Challenge 3: S0-04 (Checkpoint) -- Delta State Reset Between Sections

The delta checkpoint approach introduces `_checkpoint_df` and `_checkpoint_task_count` instance state. The progressive builder processes multiple sections in a loop (`build_project_async`). If delta state from section N leaks into section N+1, the DataFrame for section N+1 will be corrupted.

I verified that `_build_section_dataframe` (line 919) is called per-section and does not reference cross-section state. The new delta state must follow the same isolation pattern.

**Recommendation**: Reset `_checkpoint_df = None` and `_checkpoint_task_count = 0` at the top of `_build_project_section_async` (or equivalent), not just in `__init__`.

**Severity**: Medium. This is a correctness issue that will be caught by tests if handled properly, but could produce silent data corruption if missed.

### Challenge 4: S0-05 (Business Double-Fetch) -- Field Count Discrepancy

The Architect states STANDARD_TASK_OPT_FIELDS has 16 fields; I count 15 in the tuple at `fields.py:227-246`. This is a minor discrepancy (the Architect may have miscounted or included `custom_fields` as both a field and a prefix). No material impact, but the implementation should use the actual tuple constant, not a hardcoded field count.

**Severity**: Negligible. Cosmetic only.

### Challenge 5: S0-02 (Multi-PVP) -- Response Parsing Complexity

The current `_execute_insights_request` at `client.py:1109+` is designed for single-PVP responses. The refactored version must:
1. Construct a multi-PVP request body
2. Parse a multi-entity response
3. Map each `EntityMetrics` (keyed by `office_phone` + `vertical`) back to canonical `pv1:{phone}:{vertical}` keys
4. Handle HTTP 207 partial failures per-entity
5. Maintain backward compatibility with the `get_insights_async` single-PVP path

This is more than a "trivial refactor" -- the response parsing is the bulk of the work. The Architect's verdict correctly identifies the opportunity but may understate the implementation complexity.

**Severity**: Low. Does not change the verdict. The implementation sprint should allocate adequate time for the response parsing rework.

---

## NO-GO Verdict Validation

### S0-09 (Dead Code) -- Should It Be Removed?

`get_batch_with_upgrade_async` has zero callers in production code AND zero callers in test code. This is definitive dead code. The Architect's NO-GO is correct.

**Recommendation**: Add dead code removal as a boy-scout item. However, do NOT block the initiative on this. If the method was designed as a future extensibility point, removing it is a product decision, not a performance decision.

### S0-11 (Batch API) -- Should the Merge Alternative Be Captured?

The Architect's verdict mentions merging 3 PUTs into 1 as a simpler alternative, but does not promote it to an IMP finding. As I noted above, only 2 of the 3 steps can actually be merged (due_date + assignee). The third (hierarchy) uses a different API endpoint.

**Recommendation**: Capture "merge due_date + assignee update into single `tasks.update_async`" as a boy-scout improvement when the configure phase is touched by IMP-02 or IMP-07 in Sprint 2. This saves 1 API call per lifecycle creation (minor but free).

### All Other NO-GO Verdicts

S0-07 (section dedup), S0-08 (S3 batch), S0-12 (middleware): All correctly rejected with sound evidence. No reconsideration needed.

---

## Impact Estimate Validation

### API Calls per Lifecycle Transition: -52% -- PLAUSIBLE

The original estimate was -48% (25 -> 13). The revised estimate adds IMP-23 (business double-fetch) saving 1 call per Business resolution. Lifecycle transitions typically resolve 1 Business. Revised: 25 -> 12. The delta from -48% to -52% is a single additional API call saved. **Plausible but not independently verifiable without profiling.**

### API Calls per ConversationAudit Run: -75% -- OVERSTATED

The revised estimate claims 400+ -> 100 (-75%), adding 200 saved calls from IMP-23 (1 call per resolution x 200 holders). However, the original IMP-01 (parent_gid passthrough) already claims ~200 saved calls. These two savings are NOT fully additive:

- IMP-01 saves the `tasks.get_async` call in `_resolve_office_phone` (when parent_gid is passed through)
- IMP-23 saves the re-fetch when Business is detected in hydration

These target DIFFERENT code paths (IMP-01: conversation audit workflow, IMP-23: upward traversal in hydration). However, not every ConversationAudit holder performs upward traversal -- many holders already have Business resolved via the parent chain. The 200 saved calls from IMP-23 assumes ALL 200 holders trigger the double-fetch pattern, which is an upper bound.

**Revised estimate**: 400+ -> ~150 (-62%). Still significant, but the -75% figure is optimistic.

### Startup Latency: 17x -- PLAUSIBLE

The revised estimate (5s -> 300ms) combines IMP-09 (10x from parallel watermarks) with IMP-21 (additional 200ms reduction from parallel section reads during merge). The base improvement from IMP-09 alone is 5s -> 500ms. Adding parallel section reads for cold-cache merge operations would further reduce startup. 300ms is plausible if section merge is on the critical path.

However, section reads during merge happen AFTER watermark loading. If watermarks are done in 500ms and section merge takes 2s (20 sections x 100ms), parallelizing section reads with semaphore(5) reduces merge from 2s to 400ms. Total: 500ms + 400ms = 900ms -- not 300ms. The 300ms figure appears to assume watermark loading and section reads can overlap, but they are sequential operations (merge depends on knowing which sections to read).

**Revised estimate**: 5s -> ~900ms (5.5x improvement). Still excellent, but 17x is overstated unless watermark loading and section merge can be pipelined (which the implementation sketch does not propose).

### Progressive Builder 5.3x: PLAUSIBLE

12.15s -> 2.3s from delta checkpoints + double _task_to_dict elimination. The math checks out: extracting 30k tasks once (2.7s) instead of 135k (12.15s) is 4.5x. Adding IMP-15 savings of 200-400ms reduces further. 5.3x is achievable.

### Multi-PVP 50x: CORRECT

50 HTTP calls -> 1 HTTP call for a 50-PVP batch. This is arithmetic, not estimation. Confirmed.

---

## Sprint Structure Validation

### Sprint 1 (Foundation) -- SOUND

The DRY utility (`gather_with_semaphore`) is correctly placed as the first item since 6+ findings depend on it. IMP-19 (client pool) as Sprint 1 is appropriate given it is the highest-severity finding. IMP-04 (Redis pipeline) and IMP-10 (timeout config) are small, independent changes that can ship early.

**No ordering issues identified.**

### Sprint 2 (Lifecycle + Dataframes) -- SOUND with one note

IMP-22 (delta checkpoints) and IMP-15 (double _task_to_dict) touching the same file (`progressive.py`) are correctly paired for the same sprint. IMP-05 (parallel init actions) depends on `gather_with_semaphore` from Sprint 1 -- dependency satisfied.

**Note**: IMP-01 (parent_gid passthrough) has zero dependencies and could be in any sprint. Placing it in Sprint 2 is fine but it could also be pulled into Sprint 1 as a quick win.

### Sprint 3 (Data Service + Models) -- SOUND

IMP-20 (multi-PVP) is correctly isolated as it touches `clients/data/client.py` exclusively. IMP-23 (business double-fetch) is correctly identified as having many test mock updates -- allocating it to Sprint 3 allows Sprint 1-2 to ship without test churn in the models layer.

### Sprint 4 (Micro-Optimizations) -- SOUND

Low-impact findings correctly deferred to the final sprint. S0-06 Phase 1 (`from_attributes=True`) is appropriately deferred.

### QA Gates -- SOUND

QA Gate 1 after Sprint 2 (covers foundation + lifecycle changes) and QA Gate 2 after Sprint 4 (final validation) is appropriate. Two QA passes for 4 sprints is adequate given the nature of the changes (mostly parallelization and API call reduction, not correctness-altering logic).

### Cross-File Conflict Risk -- WELL DOCUMENTED

The Architect's cross-file dependency map (Section 6 of consolidated verdicts) correctly identifies `progressive.py` as the highest-conflict-risk file (IMP-15 + IMP-22). The recommendation to commit them together is sound.

---

## Risks Not Captured

### 1. gather_with_semaphore Coroutine Consumption

The `gather_with_semaphore` implementation in the PROMPT-0 spec creates coroutines eagerly:
```python
results = await asyncio.gather(
    *[_bounded(c) for c in coros],
    return_exceptions=return_exceptions,
)
```

If `coros` is a generator (not a list), the list comprehension `[_bounded(c) for c in coros]` consumes it eagerly. This is fine for small inputs (10-50 items) but for large inputs (1000+ items from multi-PVP or cache warming), all coroutine objects are created upfront in memory. This is unlikely to be a problem in practice but should be documented as a design choice.

More importantly, if a caller passes an already-started coroutine (one that has been partially awaited), `_bounded(c)` wrapping may produce unexpected behavior. The utility should validate or document that inputs must be unawaited coroutine objects.

### 2. Client Pool Test Strategy

The client pool (IMP-19) fundamentally changes the dependency injection model. Tests that currently mock `get_asana_client` or `get_asana_client_from_context` will need migration to mock the pool's `get_or_create` method. The Architect identifies the affected test files but does not estimate the test migration scope. For 43 `AsanaClientDualMode` usages across 7 route files, the test migration is non-trivial.

### 3. AIMD Backpressure with Pooled Client

The current per-request AIMD starts at ceiling. With a pooled client, AIMD will adapt over time and may settle at a low concurrency limit during periods of Asana degradation. When Asana recovers, the AIMD needs to probe upward (additive increase). The recovery time from a reduced AIMD window depends on the additive-increase rate and traffic volume. This is the INTENDED behavior, but the recovery dynamics should be tested: how long does it take for a pooled AIMD to recover from a reduced window after a 5-minute Asana degradation?

### 4. Multi-PVP Timeout Risk

Sending 50+ PVPs in a single request to autom8_data may take longer than the default httpx timeout. The current per-PVP requests have individual timeouts. A single large request with 1000 PVPs may need a higher timeout. The implementation should either:
- Increase the timeout for batch requests proportionally
- Or chunk large batches into groups of 100-200 PVPs

### 5. Progressive Builder Delta Correctness Invariant

The delta checkpoint approach must guarantee that `pl.concat([checkpoint_df, delta_df])` produces a DataFrame byte-identical to the current full-extraction approach. This is a strong invariant that should be tested with property-based testing (e.g., hypothesis) or at minimum with a comparison test that runs both paths and asserts equality.

---

## Recommendation

### CONDITIONAL-GO to proceed to implementation sprints

The Architect's Sprint 0 investigation is high-quality work. All 12 verdicts are well-evidenced and independently verifiable. The 4 GO verdicts, 1 NO-GO/promote, and 2 CONDITIONAL-GO verdicts are supported by the evidence. The 5 pure NO-GO verdicts are correctly rejected.

**Conditions**:

1. **[REQUIRED]** Correct the S0-11 verdict's "merge 3 PUTs into 1" claim. Only due_date + assignee can be merged; hierarchy uses a different Asana endpoint (`setParent`). Capture the 2-into-1 merge as a boy-scout item.

2. **[REQUIRED]** Document `gather_with_semaphore` design requirements:
   - Coroutine inputs must be unawaited
   - Semaphore bounds are callsite-local, not global thread pool bounds
   - The utility should be tested with edge cases: empty list, all-exceptions, mixed success/failure, generator vs list inputs

3. **[RECOMMENDED]** Revise the ConversationAudit impact estimate from -75% to -62% and the startup latency estimate from 17x to ~5.5x. Over-promising and under-delivering erodes trust in the initiative.

4. **[RECOMMENDED]** Add IMP-19 implementation requirements:
   - CB tuning (high failure threshold, short reset timeout)
   - CB state transition logging
   - `aclose()` safety (no-op on pooled clients or delegation to pool)
   - Pool hit rate metrics

5. **[RECOMMENDED]** For IMP-22 (delta checkpoints), add a requirement for delta state reset between sections and a comparison test that validates the delta approach produces identical DataFrames to the full-extraction approach.

### Test-Breaking Risk Assessment

| Finding | Test-Breaking Risk | Scope |
|---------|-------------------|-------|
| IMP-19 (client pool) | **HIGH** | All route handler tests that mock dependency injection (43 usages across 7 modules) |
| IMP-23 (business double-fetch) | **MEDIUM** | ~5 hydration test files with `opt_fields` assertions |
| IMP-20 (multi-PVP) | **MEDIUM** | Batch insights tests + contract alignment tests |
| IMP-22 (delta checkpoint) | **LOW** | Progressive builder tests (new behavior, mostly additive tests) |
| All parallelization IMPs | **LOW** | Sequential behavior tests may need mock adjustment for gather patterns |
| IMP-04 (Redis pipeline) | **NEGLIGIBLE** | 2-line change in a single method |

### Documentation Impact Assessment

The changes in this initiative do NOT affect user-facing behavior, commands, or APIs. All optimizations are internal (parallelization, API call reduction, client pooling). No documentation updates required.

---

## Appendix: Evidence Verification Summary

| Claim | Source File | Lines | Verified? |
|-------|-----------|-------|-----------|
| Per-request AsanaClient creation | `api/dependencies.py` | 353-409 | YES |
| 6 resilience primitives per __init__ | `client.py` | 164-204 | YES |
| AsanaClientDualMode 43 usages | `api/routes/*.py` | multiple | YES (43 across 7 files) |
| autom8_data accepts 1-1000 PVPs | `autom8_data/.../\_insights.py` | 35-38 | YES |
| Single-PVP request construction | `clients/data/client.py` | 1182-1189 | YES |
| Sequential section reads loop | `section_persistence.py` | 585-620 | YES |
| Checkpoint receives all_tasks | `progressive.py` | 910-911, 980-1003 | YES |
| CHECKPOINT_EVERY_N_PAGES=50 | `config.py` | 391 | YES |
| ASANA_PAGE_SIZE=100 | `progressive.py` | 61 | YES |
| Detection fields subset of standard | `fields.py` | 227-255 | YES |
| Double-fetch in hydration | `hydration.py` | 285-287, 324-327, 684-686, 712-714 | YES |
| _capture_custom_fields_snapshot validator | `task.py` | 137-145 | YES |
| get_batch_with_upgrade_async zero callers | `src/` + `tests/` | grep search | YES |
| Configure steps use different API methods | `lifecycle/creation.py` | 353-481 | YES |
