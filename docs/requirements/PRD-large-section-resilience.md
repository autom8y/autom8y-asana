# PRD: Large Section Resilience

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-large-section-resilience |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Requirements Analyst |
| **Impact** | high |
| **Impact Categories** | data_model |

---

## Overview

The CONTACTS section in Asana contains approximately 25,000 tasks. The current progressive builder fetches all tasks for a section via `PageIterator.collect()`, which drains every API page as fast as the rate limiter allows. For large sections (~250 pages at 100 tasks/page with full `opt_fields`), this request pattern triggers Asana's cost-based HTTP 429 ("exceptionally expensive" classification). Unlike transient 429s, this cost-based 429 persists across retries because the *pattern* of rapid sequential requests is the trigger, not momentary overload. The result is an infinite retry loop on every Lambda invocation, leaving the section permanently stuck in `in_progress` with 18 rows instead of ~25,000.

This PRD specifies paced ingestion with periodic checkpoint writes so that large sections complete without triggering cost-based 429s, and interrupted fetches can resume from the last checkpoint rather than restarting from scratch.

---

## Background

### Current Behavior

The progressive builder at `src/autom8_asana/dataframes/builders/progressive.py` (lines 429-432) fetches section tasks like this:

```python
tasks: list[Task] = await self._client.tasks.list_async(
    section=section_gid,
    opt_fields=BASE_OPT_FIELDS,
).collect()
```

`PageIterator.collect()` calls `__anext__()` in a tight loop, issuing one API request per page (~100 tasks) with no inter-page delay beyond what the rate limiter imposes. For a section with ~250 pages, this produces ~250 requests in rapid succession. The Asana API classifies this pattern as "exceptionally expensive" and returns HTTP 429 with a `Retry-After` that does not resolve because the pattern itself is the problem.

### Why This Matters

- **Data loss**: The contact entity DataFrame has 18 rows instead of ~25,000, making all contact-based queries and metrics incorrect.
- **Wasted compute**: Every Lambda invocation retries the same failing fetch, burning compute time and API quota on a request that will never succeed under the current pattern.
- **Cascading staleness**: The CONTACTS manifest is stuck in `in_progress`, preventing freshness probes from ever running on that section.

### Design Decisions (Pre-Approved Constraints)

The following decisions were approved before requirements gathering and are **non-negotiable constraints** for this PRD:

| ID | Decision | Rationale |
|----|----------|-----------|
| **D1** | Pacing lives in the progressive builder, NOT in `PageIterator` | `PageIterator` is a generic pagination abstraction used across the codebase. Pacing is a builder-level concern for large section ingestion. |
| **D2** | Single parquet file per section with periodic overwrite checkpoints | S3 `PutObject` is atomic. Overwriting the same key with accumulated data avoids partial-file cleanup. |
| **D3** | Extend `SectionInfo` with 3 new Pydantic fields: `last_fetched_offset`, `rows_fetched`, `chunks_checkpointed` | Enables checkpoint/resume tracking in the existing manifest without a new persistence artifact. |
| **D4** | First-page heuristic for large section detection: if first page returns exactly 100 results (full page), activate pacing | Avoids a separate metadata lookup. Sections with fewer than 100 tasks complete in one page and need no pacing. |
| **D5** | Exclusive section mode deferred to future work | Running large sections in isolation (pausing other section fetches) is out of scope for this initiative. |

### Hard Constraint

Full `opt_fields` are **non-negotiable**. A reduced-field two-phase fetch (fetch GIDs first, then details) is explicitly excluded. The existing `BASE_OPT_FIELDS` must be used on every request.

---

## Stakeholders

| Stakeholder | Interest | Priority |
|-------------|----------|----------|
| **Data consumers** (n8n workflows, dashboards) | Complete contact data (all ~25k rows) | Primary |
| **Platform operations** | Lambda invocations complete within timeout; no infinite retry loops | Primary |
| **Existing entity owners** (offer, business, etc.) | Zero regression for sections with <100 tasks | Primary |

---

## User Stories

### US-001: Paced Ingestion of Large Sections

**As a** data pipeline operator
**I want** the progressive builder to pace API requests when fetching large sections
**So that** sections with thousands of tasks complete without triggering Asana's cost-based HTTP 429

**Acceptance Criteria**:
- [ ] When the first page of a section returns exactly 100 tasks (full page), pacing mode activates
- [ ] In pacing mode, the builder pauses for a configurable delay (`pace_delay_seconds`, default 2.0s) every `pace_pages_per_pause` pages (default 25)
- [ ] The pacing loop uses `async for` over `PageIterator` instead of `.collect()`
- [ ] The CONTACTS section (~25,000 tasks, ~250 pages) completes without any cost-based 429 errors
- [ ] Total fetch time for CONTACTS increases by at most `ceil(250/25) * 2.0 = 20 seconds` of deliberate delay

### US-002: Checkpoint Writes During Fetch

**As a** data pipeline operator
**I want** the builder to write accumulated data to S3 at regular intervals during a large section fetch
**So that** if the Lambda times out or is interrupted, previously fetched data is recoverable

**Acceptance Criteria**:
- [ ] Every `checkpoint_every_n_pages` pages (default 50), the builder writes the accumulated DataFrame to S3 as a single parquet file at the section's existing S3 key
- [ ] The checkpoint write uses S3 `PutObject` (atomic overwrite), not multipart upload
- [ ] The manifest's `SectionInfo` is updated with `last_fetched_offset`, `rows_fetched`, and `chunks_checkpointed` after each checkpoint
- [ ] If the fetch completes fully, the final write replaces the last checkpoint with the complete section data
- [ ] Checkpoint writes do not hold the manifest lock longer than a single read-modify-write cycle

### US-003: Resume from Checkpoint

**As a** data pipeline operator
**I want** a resumed build to detect an incomplete checkpoint and continue fetching from where it left off
**So that** interrupted large section fetches do not restart from page 1

**Acceptance Criteria**:
- [ ] On resume, if a section's `SectionInfo` has `last_fetched_offset > 0` and status is `IN_PROGRESS`, the builder reads the existing checkpoint parquet from S3
- [ ] The builder resumes fetching from `last_fetched_offset` (page offset) by advancing the `PageIterator` past already-fetched pages
- [ ] Resumed rows are appended to the checkpoint DataFrame before the next checkpoint write
- [ ] If the checkpoint parquet is missing or corrupt on resume, the builder falls back to a full re-fetch of that section (logs a warning, does not fail the build)
- [ ] After successful resume completion, the section is marked `COMPLETE` with final row count

### US-004: Large Section Detection Heuristic

**As a** data pipeline operator
**I want** the system to automatically detect large sections without prior configuration
**So that** pacing activates only when needed, with zero overhead for small sections

**Acceptance Criteria**:
- [ ] The builder fetches the first page of every section using `PageIterator.__anext__()`
- [ ] If the first page contains exactly 100 tasks (indicating more pages exist), pacing mode activates for the remainder of that section
- [ ] If the first page contains fewer than 100 tasks, the section is processed immediately with no pacing delay and no checkpoint writes
- [ ] The heuristic adds zero additional API calls (it uses the first page that would be fetched anyway)

### US-005: Backward Compatibility

**As an** existing entity owner (offers, businesses, etc.)
**I want** the pacing changes to have zero impact on sections with fewer than 100 tasks
**So that** existing build performance is not degraded

**Acceptance Criteria**:
- [ ] Sections with fewer than 100 tasks follow the existing single-page fetch path with no `asyncio.sleep` calls
- [ ] Existing manifests without the new `SectionInfo` fields (`last_fetched_offset`, `rows_fetched`, `chunks_checkpointed`) parse successfully using Pydantic defaults (all default to 0)
- [ ] The `SectionManifest.version` field is NOT incremented (additive Pydantic fields with defaults are backward compatible)
- [ ] No changes to `PageIterator`, transport layer, or hierarchy warmer

---

## Functional Requirements

### FR-001: Paced Page Iteration

Replace the `.collect()` call in `_fetch_and_persist_section` with an `async for` loop over `PageIterator` that introduces deliberate pauses for large sections.

**Algorithm**:
1. Call `PageIterator.__anext__()` to fetch the first page.
2. If the first page has exactly 100 items, activate pacing mode.
3. In pacing mode, iterate remaining pages via `async for`. Every `pace_pages_per_pause` pages, call `asyncio.sleep(pace_delay_seconds)`.
4. If the first page has fewer than 100 items, return immediately (single-page section).

**Location**: `src/autom8_asana/dataframes/builders/progressive.py`, within `_fetch_and_persist_section`.

**Priority**: MUST

### FR-002: Checkpoint Write to S3

During paced iteration, periodically write the accumulated tasks as a parquet file to S3 at the section's existing key.

**Algorithm**:
1. Maintain a running list of task dicts as pages are fetched.
2. Every `checkpoint_every_n_pages` pages, convert accumulated tasks to a DataFrame, write to S3 via `SectionPersistence.write_section_async` (which already handles parquet serialization and manifest update).
3. After writing, update `SectionInfo` with checkpoint metadata.

**Interaction with existing write**: The final section write (after all pages) uses the same `write_section_async` method. The checkpoint writes are intermediate overwrites of the same S3 key.

**Priority**: MUST

### FR-003: SectionInfo Schema Extension

Add three fields to the `SectionInfo` Pydantic model:

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `last_fetched_offset` | `int` | `0` | Number of pages fetched so far (for resume) |
| `rows_fetched` | `int` | `0` | Number of task rows accumulated so far |
| `chunks_checkpointed` | `int` | `0` | Number of checkpoint writes completed |

All fields have defaults, ensuring existing manifests without these fields parse without error (Pydantic fills defaults).

**Location**: `src/autom8_asana/dataframes/section_persistence.py`, class `SectionInfo`.

**Priority**: MUST

### FR-004: Pacing Configuration

Add three configuration values. These do NOT need to be environment variables for the initial implementation; module-level constants in `config.py` are sufficient.

| Config | Type | Default | Constraints |
|--------|------|---------|-------------|
| `PACE_PAGES_PER_PAUSE` | `int` | `25` | Must be >= 1 |
| `PACE_DELAY_SECONDS` | `float` | `2.0` | Must be >= 0.0 |
| `CHECKPOINT_EVERY_N_PAGES` | `int` | `50` | Must be >= 1; should be a multiple of `PACE_PAGES_PER_PAUSE` |

**Location**: `src/autom8_asana/config.py`.

**Priority**: MUST

### FR-005: Resume from Checkpoint

On build resume, detect sections with `SectionInfo.last_fetched_offset > 0` and status `IN_PROGRESS`:

1. Read the existing checkpoint parquet from S3 via `SectionPersistence.read_section_async`.
2. If successful, begin `PageIterator` iteration, skipping the first `last_fetched_offset` pages by calling `__anext__()` that many times without processing.
3. Append new tasks to the checkpoint DataFrame.
4. Continue pacing and checkpointing as normal.
5. If the checkpoint parquet is missing or corrupt, log a warning and re-fetch from scratch.

**Location**: `src/autom8_asana/dataframes/builders/progressive.py`, within `_fetch_and_persist_section`.

**Priority**: SHOULD

### FR-006: Logging and Observability

Each paced fetch logs structured events:

| Event | Fields | When |
|-------|--------|------|
| `large_section_detected` | `section_gid`, `first_page_count`, `pacing_enabled` | After first-page heuristic |
| `section_pace_pause` | `section_gid`, `pages_fetched`, `rows_so_far`, `pause_seconds` | Before each pacing sleep |
| `section_checkpoint_written` | `section_gid`, `pages_fetched`, `rows_checkpointed`, `s3_key` | After each checkpoint write |
| `section_checkpoint_resumed` | `section_gid`, `resumed_offset`, `resumed_rows`, `checkpoint_rows` | On successful resume from checkpoint |
| `section_checkpoint_resume_failed` | `section_gid`, `error`, `fallback` | On failed resume (falling back to fresh fetch) |

**Priority**: SHOULD

---

## Non-Functional Requirements

### NFR-001: Memory

- 25,000 tasks at approximately 2KB per task-dict = ~50MB of in-memory task data.
- The Lambda function runs with 1024MB memory. 50MB is well within budget.
- Checkpoint writes do NOT release memory (the running list is retained for continued accumulation). Peak memory is the full section's data.
- DataFrame construction from the accumulated list is a one-time allocation at checkpoint time, garbage-collected after the parquet serialization buffer is released.

**Target**: Peak memory for CONTACTS section fetch stays below 200MB (including DataFrame + parquet buffer overhead).

**Priority**: MUST

### NFR-002: Execution Time

- Without pacing: ~250 pages at ~0.5s per page = ~125 seconds (but triggers 429).
- With pacing: ~125 seconds fetch time + `ceil(250/25) * 2.0` = 20 seconds pacing delay = ~145 seconds.
- With checkpoints: 5 checkpoint writes at ~0.5s each = ~2.5 seconds overhead.
- **Total expected**: ~150 seconds for CONTACTS section, well within 900-second Lambda timeout.

**Target**: CONTACTS section completes in under 300 seconds (2x safety margin over estimate).

**Priority**: MUST

### NFR-003: Checkpoint I/O Overhead

- Each checkpoint write is a single S3 `PutObject` operation.
- At 50 pages per checkpoint and ~100 tasks per page, each checkpoint writes ~5,000 rows.
- 5,000 rows * ~2KB = ~10MB parquet file per checkpoint.
- 5 checkpoints for a 250-page section = 5 S3 writes totaling ~50MB.
- S3 `PutObject` for 10MB files typically completes in <500ms.

**Target**: Total checkpoint I/O overhead under 5 seconds for a 250-page section.

**Priority**: SHOULD

### NFR-004: Backward Compatibility

- Existing manifests without `last_fetched_offset`, `rows_fetched`, `chunks_checkpointed` fields MUST parse successfully via Pydantic defaults.
- No manifest version bump required (additive fields with defaults are backward compatible per Pydantic's model validation).
- Sections with fewer than 100 tasks MUST execute with zero additional latency (no sleep calls, no checkpoint writes).

**Priority**: MUST

---

## Edge Cases

### EC-001: First Page Returns Exactly 100 Tasks but Section Has Exactly 100

If a section has exactly 100 tasks, the first page returns 100 items and the heuristic activates pacing. The second `__anext__()` call raises `StopAsyncIteration`. This is harmless: the pacing loop simply exits after one page with no pauses taken. The small overhead is a single unnecessary `asyncio.sleep` check (a branch, not an actual sleep).

**Expected behavior**: Section completes normally with 100 rows. No checkpoint writes occur (checkpoint threshold of 50 pages is not reached).

### EC-002: Lambda Timeout During Paced Fetch

If the Lambda times out mid-fetch, the most recent checkpoint parquet is available in S3 with the data fetched up to the last checkpoint boundary.

**Expected behavior**: On the next invocation, the builder detects `SectionInfo.status == IN_PROGRESS` with `last_fetched_offset > 0`, reads the checkpoint, and resumes from the offset. If the checkpoint is also corrupt or the parquet write was interrupted mid-PutObject (unlikely given S3 atomicity), the builder falls back to a full re-fetch.

### EC-003: Section Deleted or Reorganized Between Checkpoints

If tasks are moved out of a section between checkpoint writes, the accumulated data may contain tasks no longer in that section.

**Expected behavior**: This is acceptable. The final merge produces a point-in-time snapshot. Freshness probes on the next build cycle will detect the structural change (via `gid_hash` mismatch) and trigger a full re-fetch.

### EC-004: Rate Limiter and Pacing Interaction

The existing rate limiter (`RateLimitConfig`) already enforces a global request budget. The pacing delay is *additional* to the rate limiter's delays.

**Expected behavior**: Both mechanisms operate independently. The rate limiter prevents exceeding Asana's global rate limit. The pacing delay prevents the request *pattern* from being classified as exceptionally expensive. They are complementary, not conflicting.

### EC-005: Empty Section with Pacing

If a section returns 0 tasks on the first page, no pacing or checkpoint logic is invoked.

**Expected behavior**: Section is marked `COMPLETE` with `rows=0`, identical to current behavior.

### EC-006: Concurrent Large Sections

If multiple sections qualify as "large" (unlikely given current data model where only CONTACTS exceeds 100 tasks), they would all pace independently in their respective coroutines.

**Expected behavior**: The `max_concurrent_sections` limit (default 8) bounds parallelism. Pacing delays within each coroutine reduce the aggregate request rate, which actually helps avoid rate limit pressure. No special coordination is needed.

### EC-007: Checkpoint Parquet Schema Drift

If the schema version changes between a checkpoint write and the resume attempt, the checkpoint parquet may have incompatible columns.

**Expected behavior**: The progressive builder already checks `manifest.is_schema_compatible()` at the build level and forces a full rebuild on schema mismatch. This check happens before any section-level resume, so schema drift is handled by the existing mechanism.

### EC-008: S3 Write Failure During Checkpoint

If a checkpoint `PutObject` fails, the previous checkpoint (or no checkpoint if this was the first) remains on S3.

**Expected behavior**: The builder logs the failure, updates `SectionInfo` with the error, and continues fetching. The next checkpoint attempt will include all data accumulated since the failed write. If the section completes, the final write replaces everything. If the Lambda times out, resume will use the last successful checkpoint.

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Contact row count** | Matches Asana section task count (~25,000) | Compare `len(df)` from progressive build result to Asana API `GET /sections/{gid}/tasks?limit=1` total count |
| **No cost-based 429** | Zero 429 errors during CONTACTS fetch | Structured log search for `section_gid=CONTACTS_GID` and `status_code=429` |
| **Lambda completion** | Build completes within 900s timeout | CloudWatch Lambda duration metric |
| **Small section zero overhead** | Sections with <100 tasks show no latency increase | Compare fetch_time_ms for small sections before and after deployment |
| **Checkpoint frequency** | 5 checkpoints for a 250-page section | Structured log count for `section_checkpoint_written` events per build |
| **Resume correctness** | Resumed build produces same row count as fresh build | Integration test: interrupt at checkpoint N, resume, compare final row count |

---

## Scope Boundary

### In Scope

| Component | File | Change |
|-----------|------|--------|
| Progressive builder | `src/autom8_asana/dataframes/builders/progressive.py` | Replace `.collect()` with paced `async for` loop + checkpoint writes (~100 LOC) |
| Section persistence | `src/autom8_asana/dataframes/section_persistence.py` | Extend `SectionInfo` with 3 fields + add checkpoint update method (~20 LOC) |
| Configuration | `src/autom8_asana/config.py` | Add 3 pacing constants (~10 LOC) |
| Builder tests | `tests/` | Tests for paced fetch, checkpoint writes, resume logic (~150 LOC) |
| Persistence tests | `tests/` | Tests for SectionInfo extension, backward compat (~50 LOC) |

### Out of Scope

| Item | Reason |
|------|--------|
| `PageIterator` (`models/common.py`) | Generic pagination abstraction; no changes needed. Pacing is a builder concern (D1). |
| Transport layer (`asana_http.py`) | No changes to HTTP client or retry logic. |
| Hierarchy warmer | Not affected by section-level pacing. |
| Exclusive section mode | Deferred per D5. Running large sections in isolation is a future optimization. |
| Dynamic concurrency adjustment | Reducing `max_concurrent_sections` when a large section is detected is deferred. |
| Reduced-field two-phase fetch | Explicitly excluded. Full `opt_fields` is non-negotiable. |
| Environment variable configuration | Module-level constants are sufficient for initial implementation. Environment variable overrides can be added later if tuning is needed in production. |

---

## Verification Plan

The following 6-step verification plan validates the implementation end-to-end:

### Step 1: Unit Test -- Pacing Activation Heuristic

Verify that the first-page heuristic correctly activates pacing for full pages and skips it for partial pages.

- Mock `PageIterator` to return exactly 100 items on the first page -> pacing activates.
- Mock `PageIterator` to return 50 items on the first page -> pacing does not activate.
- Mock `PageIterator` to return 0 items -> section marked complete with 0 rows.

### Step 2: Unit Test -- Paced Iteration with Delays

Verify that `asyncio.sleep` is called at the correct intervals during paced iteration.

- Mock `PageIterator` with 75 pages (100 items each).
- With `pace_pages_per_pause=25`, verify 3 sleep calls (after pages 25, 50, 75).
- Verify total task count matches 75 * 100 = 7,500.

### Step 3: Unit Test -- Checkpoint Writes

Verify that checkpoint writes occur at the configured interval.

- Mock `PageIterator` with 120 pages.
- With `checkpoint_every_n_pages=50`, verify 2 checkpoint writes (at pages 50 and 100).
- Verify the final write after page 120 contains all data.
- Verify `SectionInfo.chunks_checkpointed` is updated after each checkpoint.

### Step 4: Unit Test -- Resume from Checkpoint

Verify that a resumed build reads the checkpoint and continues from the offset.

- Create a checkpoint parquet with 5,000 rows and `last_fetched_offset=50`.
- Mock `PageIterator` to return pages 51-120.
- Verify the final DataFrame has 5,000 (checkpoint) + 7,000 (new) = 12,000 rows.
- Verify `PageIterator.__anext__()` is called 50 times to skip past already-fetched pages.

### Step 5: Unit Test -- Backward Compatibility

Verify that existing manifests without new fields parse correctly.

- Create a `SectionInfo` from a dict without `last_fetched_offset`, `rows_fetched`, `chunks_checkpointed`.
- Verify all three fields default to 0.
- Verify `SectionManifest` with mixed old/new `SectionInfo` entries parses correctly.

### Step 6: Integration Test -- End-to-End Large Section

Verify the complete flow with a simulated large section.

- Mock Asana API to return 250 pages of 100 tasks each.
- Run `build_progressive_async` with pacing enabled.
- Verify: no 429 errors, 5 checkpoint writes, final DataFrame has 25,000 rows.
- Interrupt at checkpoint 3, resume, verify final DataFrame still has 25,000 rows.

---

## Risk Factors

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pacing delay values are too aggressive or too conservative | Medium | Medium | Config values are module-level constants, trivially tunable. Start conservative (2s delay) and reduce if needed. |
| Asana changes their cost-based 429 classification | Low | High | The pacing approach is generic (reduce request density). Even if the threshold changes, the mitigation direction is correct. |
| Checkpoint parquet write fails silently | Low | Medium | S3 `PutObject` returns success/failure. Existing `write_section_async` already logs failures and updates manifest status. |
| Resume page-skip logic drifts if section content changes | Medium | Low | Acceptable for point-in-time snapshots. Freshness probes detect structural changes on next full build. |
| Memory spike from accumulating 25k task dicts | Low | Low | 50MB is well within 1024MB Lambda. Monitor via CloudWatch. |

---

## Attestation Table

| File | Absolute Path | Read |
|------|---------------|------|
| Progressive Builder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Yes |
| Section Persistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes |
| Config | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Yes |
| PageIterator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/common.py` | Yes (grep) |
| Reference PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-query-service.md` | Yes |
| Agent Config | `/Users/tomtenuta/Code/autom8_asana/.claude/agents/requirements-analyst.md` | Yes |
