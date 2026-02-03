# TDD: Large Section Resilience

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-large-section-resilience |
| **PRD** | PRD-large-section-resilience |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Architect |

---

## 1. Problem Recap

The CONTACTS section contains approximately 25,000 tasks (~250 API pages at 100 tasks/page). The current progressive builder calls `PageIterator.collect()`, which drains all pages as fast as the rate limiter allows. Asana classifies this rapid-sequential pattern as "exceptionally expensive" and returns a cost-based HTTP 429 that does not resolve on retry because the *pattern* is the trigger, not momentary overload. The result is an infinite retry loop that leaves the section permanently stuck in `in_progress` with 18 rows instead of ~25,000.

### What We Need

1. **Paced ingestion**: Introduce deliberate pauses between page batches to avoid triggering cost-based 429s.
2. **Checkpoint writes**: Periodically persist accumulated data to S3 so that interrupted fetches are not lost.
3. **Resume capability**: On restart, detect partial checkpoints and avoid re-fetching from scratch (best-effort; see ADR-LSR-003 for offset limitations).
4. **Zero overhead for small sections**: Sections with fewer than 100 tasks must execute with no additional latency.

---

## 2. Design Overview

The design modifies a single method -- `ProgressiveProjectBuilder._fetch_and_persist_section()` -- with supporting changes to `SectionInfo` (3 new fields) and `config.py` (3 new constants). No changes to `PageIterator`, transport layer, or hierarchy warmer.

### 2.1 Key Decisions Summary

| ID | Decision | Rationale | ADR |
|----|----------|-----------|-----|
| **D1** | Pacing lives in the builder, not `PageIterator` | `PageIterator` is a generic pagination abstraction; pacing is a builder-level ingestion concern | ADR-LSR-001 |
| **D2** | Single parquet per section with periodic overwrite checkpoints | S3 `PutObject` is atomic; overwriting avoids partial-file cleanup | ADR-LSR-002 |
| **D3** | Extend `SectionInfo` with `last_fetched_offset`, `rows_fetched`, `chunks_checkpointed` | Checkpoint tracking within existing manifest; no new persistence artifact | ADR-LSR-003 |
| **D4** | First-page heuristic for large section detection | Zero extra API calls; if first page returns 100 tasks (full page), activate pacing | ADR-LSR-004 |
| **D5** | Defer exclusive section mode | Running large sections in isolation is out of scope | -- |

### 2.2 High-Level Flow

```
_fetch_and_persist_section(section_gid)
  |
  |-- Mark section IN_PROGRESS in manifest
  |
  |-- Create PageIterator for section
  |-- Fetch first page via __anext__()
  |
  |-- [First page < 100 tasks?]
  |     YES --> Process single page (existing path), mark COMPLETE, return
  |     NO  --> Activate pacing mode
  |
  |-- PACING LOOP (async for over remaining pages):
  |     |-- Accumulate tasks into running list
  |     |-- Every pace_pages_per_pause pages: asyncio.sleep(pace_delay_seconds)
  |     |-- Every checkpoint_every_n_pages pages: checkpoint write to S3
  |     |     |-- Convert accumulated tasks to DataFrame
  |     |     |-- write_section_async() (atomic S3 PutObject overwrite)
  |     |     |-- Update SectionInfo checkpoint metadata in manifest
  |
  |-- Final write: full accumulated data to S3
  |-- Mark section COMPLETE
```

---

## 3. Detailed Design

### 3.1 Paced Iteration (FR-001)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py`
**Method**: `_fetch_and_persist_section()`
**Lines replaced**: 429-432 (the `.collect()` call)

#### Current Code

```python
tasks: list[Task] = await self._client.tasks.list_async(
    section=section_gid,
    opt_fields=BASE_OPT_FIELDS,
).collect()
```

#### New Code (pseudocode)

```python
from autom8_asana.config import (
    PACE_PAGES_PER_PAUSE,
    PACE_DELAY_SECONDS,
    CHECKPOINT_EVERY_N_PAGES,
)

iterator = self._client.tasks.list_async(
    section=section_gid,
    opt_fields=BASE_OPT_FIELDS,
)

# Fetch first page to determine section size
first_page_tasks: list[Task] = []
async for task in iterator:
    first_page_tasks.append(task)
    if len(first_page_tasks) >= 100:
        break  # First page consumed; check if pacing needed

is_large_section = len(first_page_tasks) == 100

logger.info(
    "large_section_detected",
    extra={
        "section_gid": section_gid,
        "first_page_count": len(first_page_tasks),
        "pacing_enabled": is_large_section,
    },
)

if not is_large_section:
    # Small section: process immediately (existing path)
    tasks = first_page_tasks
    # ... existing task-to-row conversion and write ...
    return True

# Large section: paced iteration with checkpoints
all_tasks: list[Task] = list(first_page_tasks)
pages_fetched = 1
current_page_task_count = 0

async for task in iterator:
    all_tasks.append(task)
    current_page_task_count += 1

    # Detect page boundary (every 100 tasks = 1 page)
    if current_page_task_count >= 100:
        pages_fetched += 1
        current_page_task_count = 0

        # Pacing: pause every N pages
        if pages_fetched % PACE_PAGES_PER_PAUSE == 0:
            logger.info(
                "section_pace_pause",
                extra={
                    "section_gid": section_gid,
                    "pages_fetched": pages_fetched,
                    "rows_so_far": len(all_tasks),
                    "pause_seconds": PACE_DELAY_SECONDS,
                },
            )
            await asyncio.sleep(PACE_DELAY_SECONDS)

        # Checkpoint: persist every N pages
        if pages_fetched % CHECKPOINT_EVERY_N_PAGES == 0:
            await self._write_checkpoint(
                section_gid, all_tasks, pages_fetched
            )

# Account for final partial page
if current_page_task_count > 0:
    pages_fetched += 1

tasks = all_tasks
# ... continue with existing task-to-row conversion and final write ...
```

#### Page Boundary Detection

`PageIterator.__anext__()` yields one task at a time from an internal buffer of 100 items. When the buffer empties, it fetches the next page. Since each API page returns exactly 100 tasks (Asana's default page size for tasks with `opt_fields`), counting every 100th yielded task corresponds to a page boundary.

**Edge case**: The last page of a section will typically have fewer than 100 tasks. The `current_page_task_count` counter handles this -- the partial page is counted as a page only after the iterator is exhausted.

**Edge case**: A section with exactly 100 tasks will activate pacing, but the iterator will exhaust immediately after the first page with no actual pauses taken. This is harmless.

### 3.2 Checkpoint Write (FR-002)

**New private method on `ProgressiveProjectBuilder`**:

```python
async def _write_checkpoint(
    self,
    section_gid: str,
    tasks: list[Task],
    pages_fetched: int,
) -> bool:
    """Write accumulated tasks as a checkpoint parquet to S3.

    Converts accumulated tasks to a DataFrame and writes to the
    section's existing S3 key (atomic overwrite via PutObject).
    Updates manifest with checkpoint metadata.

    Args:
        section_gid: Section GID being fetched.
        tasks: All accumulated tasks so far.
        pages_fetched: Number of pages consumed so far.

    Returns:
        True if checkpoint written successfully.
    """
    try:
        task_dicts = [self._task_to_dict(task) for task in tasks]
        rows = await self._extract_rows(task_dicts)
        coerced_rows = coerce_rows_to_schema(rows, self._schema)
        checkpoint_df = pl.DataFrame(
            coerced_rows, schema=self._schema.to_polars_schema()
        )

        # Write to S3 at the section's key (atomic overwrite)
        # NOTE: We call the underlying S3 write directly, NOT
        # write_section_async(), because that method marks
        # the section COMPLETE. For checkpoints we need the
        # section to remain IN_PROGRESS.
        key = self._persistence._make_section_key(
            self._project_gid, section_gid
        )
        buffer = io.BytesIO()
        checkpoint_df.write_parquet(buffer)
        buffer.seek(0)
        parquet_bytes = buffer.read()

        result = await self._persistence._s3_client.put_object_async(
            key=key,
            body=parquet_bytes,
            content_type="application/octet-stream",
            metadata={
                "project-gid": self._project_gid,
                "section-gid": section_gid,
                "row-count": str(len(checkpoint_df)),
                "checkpoint": "true",
                "pages-fetched": str(pages_fetched),
            },
        )

        if result.success:
            # Update manifest with checkpoint metadata
            await self._update_checkpoint_metadata(
                section_gid, pages_fetched, len(checkpoint_df)
            )
            logger.info(
                "section_checkpoint_written",
                extra={
                    "section_gid": section_gid,
                    "pages_fetched": pages_fetched,
                    "rows_checkpointed": len(checkpoint_df),
                    "s3_key": key,
                },
            )
            # Store in memory for fallback
            self._section_dfs[section_gid] = checkpoint_df
        else:
            logger.warning(
                "section_checkpoint_write_failed",
                extra={
                    "section_gid": section_gid,
                    "error": result.error,
                },
            )

        return result.success

    except Exception as e:
        logger.warning(
            "section_checkpoint_failed",
            extra={
                "section_gid": section_gid,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return False
```

#### Why Not Use `write_section_async()`?

`SectionPersistence.write_section_async()` marks the section as `COMPLETE` after a successful write (line 603). Checkpoint writes must keep the section in `IN_PROGRESS` status. Rather than adding a `checkpoint=True` flag to `write_section_async()` (which would complicate its contract for all callers), the builder writes directly to S3 using the persistence layer's S3 client and updates the manifest separately.

**Alternative considered**: Add a `checkpoint_write_section_async()` method to `SectionPersistence`. This is cleaner from an encapsulation standpoint but introduces a new public API on `SectionPersistence` for a single caller. The private access pattern is acceptable because `ProgressiveProjectBuilder` already has a tight coupling to `SectionPersistence` (it calls `update_manifest_section_async`, `write_section_async`, `merge_sections_to_dataframe_async`).

**ADR-LSR-002** documents this decision.

### 3.3 Checkpoint Metadata Update

**New private method on `ProgressiveProjectBuilder`**:

```python
async def _update_checkpoint_metadata(
    self,
    section_gid: str,
    pages_fetched: int,
    rows_fetched: int,
) -> None:
    """Update manifest SectionInfo with checkpoint progress.

    Uses the per-project manifest lock via update_manifest_section_async
    to safely update checkpoint fields without race conditions.

    Args:
        section_gid: Section GID being checkpointed.
        pages_fetched: Total pages fetched so far.
        rows_fetched: Total rows accumulated so far.
    """
    lock = self._persistence._get_manifest_lock(self._project_gid)
    async with lock:
        manifest = await self._persistence.get_manifest_async(
            self._project_gid
        )
        if manifest is None:
            return

        section_info = manifest.sections.get(section_gid)
        if section_info is None:
            return

        section_info.last_fetched_offset = pages_fetched
        section_info.rows_fetched = rows_fetched
        section_info.chunks_checkpointed += 1

        self._persistence._manifest_cache[self._project_gid] = manifest
        await self._persistence._save_manifest_async(manifest)
```

### 3.4 SectionInfo Schema Extension (FR-003)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py`
**Class**: `SectionInfo` (line 80)

Add three fields with defaults:

```python
class SectionInfo(BaseModel):
    """Information about a single section."""

    status: SectionStatus = SectionStatus.PENDING
    rows: int = 0
    written_at: datetime | None = None
    error: str | None = None
    watermark: datetime | None = None
    gid_hash: str | None = None
    name: str | None = None

    # Checkpoint tracking fields (D3)
    last_fetched_offset: int = 0    # Pages fetched so far
    rows_fetched: int = 0           # Task rows accumulated so far
    chunks_checkpointed: int = 0    # Checkpoint writes completed

    model_config = {"use_enum_values": True}
```

**Backward compatibility**: All three fields have `int` defaults of `0`. Existing manifests in S3 without these fields will parse correctly via Pydantic's `model_validate()` -- missing fields receive their default values. No manifest version bump is needed.

**Manifest version note**: `SectionManifest.version` stays at `1`. Additive Pydantic fields with defaults are backward compatible by definition. A version bump would force unnecessary cache invalidation across all entity types.

### 3.5 Resume from Checkpoint (FR-005)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py`
**Method**: `_fetch_and_persist_section()` -- new resume path at the top of the method

```python
# Check for checkpoint resume
section_info = None
if manifest is not None:
    section_info = manifest.sections.get(section_gid)

checkpoint_df: pl.DataFrame | None = None
resume_offset = 0

if (
    section_info is not None
    and section_info.status == SectionStatus.IN_PROGRESS
    and section_info.rows_fetched > 0
):
    # Attempt to read existing checkpoint
    try:
        checkpoint_df = await self._persistence.read_section_async(
            self._project_gid, section_gid
        )
        if checkpoint_df is not None:
            resume_offset = section_info.last_fetched_offset
            logger.info(
                "section_checkpoint_resumed",
                extra={
                    "section_gid": section_gid,
                    "resumed_offset": resume_offset,
                    "resumed_rows": section_info.rows_fetched,
                    "checkpoint_rows": len(checkpoint_df),
                },
            )
    except Exception as e:
        logger.warning(
            "section_checkpoint_resume_failed",
            extra={
                "section_gid": section_gid,
                "error": str(e),
                "fallback": "full_refetch",
            },
        )
        checkpoint_df = None
        resume_offset = 0
```

#### Resume Strategy: Skip Pages, Not Offsets

Asana's pagination offsets are opaque tokens, not numeric cursors. They are also short-lived and cannot be reused across API sessions. Therefore, resume cannot "seek" to a specific offset.

Instead, when `resume_offset > 0`:

1. Create a fresh `PageIterator`.
2. Consume (and discard) the first `resume_offset` pages by calling `__anext__()` in a tight loop, counting every 100 tasks as one page.
3. Begin accumulating from page `resume_offset + 1` onward.
4. Prepend the checkpoint DataFrame's rows to the new rows before the final write.

```python
if resume_offset > 0:
    # Skip past already-fetched pages
    skip_count = 0
    skip_task_count = 0
    async for task in iterator:
        skip_task_count += 1
        if skip_task_count >= 100:
            skip_count += 1
            skip_task_count = 0
            if skip_count >= resume_offset:
                break

    logger.info(
        "section_resume_pages_skipped",
        extra={
            "section_gid": section_gid,
            "pages_skipped": skip_count,
            "target_offset": resume_offset,
        },
    )
```

**Trade-off**: Skipping pages still makes API requests (we fetch and discard). This consumes API quota but avoids the complexity of storing and reusing opaque offset tokens. For a 250-page section where the Lambda timed out at page 200, resume would re-fetch pages 1-200 (discarding them) and then accumulate pages 201-250. This is suboptimal but simple and correct.

**Why this is acceptable**: The checkpoint parquet is the primary value -- it ensures data is not lost between Lambda invocations. Even if resume re-fetches everything, the checkpoint means we have a valid parquet in S3 that the merge step can use. The resume-skip path is a best-effort optimization that saves DataFrame construction and S3 write time for the skipped pages.

**ADR-LSR-003** documents this trade-off.

### 3.6 Configuration (FR-004)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py`

Add three module-level constants after the `DataFrameConfig` class:

```python
# --- Large Section Pacing Configuration ---
# Per TDD-large-section-resilience / FR-004
#
# These control paced ingestion for sections with 100+ tasks.
# Module-level constants are sufficient; environment variable
# overrides can be added later if production tuning is needed.

PACE_PAGES_PER_PAUSE: int = 25
"""Number of pages to fetch before pausing. Must be >= 1."""

PACE_DELAY_SECONDS: float = 2.0
"""Seconds to sleep between page batches. Must be >= 0.0."""

CHECKPOINT_EVERY_N_PAGES: int = 50
"""Pages between checkpoint writes to S3. Must be >= 1.
Should be a multiple of PACE_PAGES_PER_PAUSE for predictable behavior."""
```

**Why module-level constants instead of `DataFrameConfig` fields**: `DataFrameConfig` is a frozen dataclass that flows through `AsanaConfig` and is set at client initialization. The pacing constants are operational tuning knobs that do not need to participate in the config hierarchy. Module-level constants are simpler to import and modify. If production tuning reveals a need for runtime adjustment, they can be promoted to environment-variable-backed settings later.

### 3.7 Manifest Access for Resume

The `_fetch_and_persist_section()` method currently does not have access to the manifest. It receives `section_gid`, `section`, `section_index`, and `total_sections`. For the resume path, it needs the manifest to check `SectionInfo.rows_fetched`.

**Solution**: Store the manifest as `self._manifest` on the builder instance during `build_progressive_async()` (after Step 2/3 where the manifest is created or loaded). The `_fetch_and_persist_section()` method then reads `self._manifest.sections.get(section_gid)`.

```python
# In build_progressive_async(), after manifest creation/loading:
self._manifest = manifest
```

This is a minimal change. The manifest is already in scope during `build_progressive_async()` -- we are simply making it available to the section-level method.

---

## 4. Interface Changes

### 4.1 New Methods on `ProgressiveProjectBuilder`

| Method | Visibility | Purpose |
|--------|-----------|---------|
| `_write_checkpoint(section_gid, tasks, pages_fetched)` | Private | Persist accumulated tasks as checkpoint parquet |
| `_update_checkpoint_metadata(section_gid, pages_fetched, rows_fetched)` | Private | Update manifest SectionInfo with checkpoint progress |

### 4.2 Modified Methods

| Method | Change |
|--------|--------|
| `_fetch_and_persist_section()` | Replace `.collect()` with paced `async for` loop; add checkpoint writes; add resume detection |
| `build_progressive_async()` | Store manifest as `self._manifest` for section-level access |

### 4.3 New Instance Attribute

| Attribute | Type | Purpose |
|-----------|------|---------|
| `self._manifest` | `SectionManifest \| None` | Manifest reference for section-level resume checks |

### 4.4 No Changes to Public API

- No new public methods on `SectionPersistence`.
- No changes to `PageIterator`.
- No changes to `ProgressiveBuildResult` (existing fields capture all needed metrics).
- No changes to any API routes.

---

## 5. Data Model Changes

### 5.1 SectionInfo Extension

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `last_fetched_offset` | `int` | `0` | Number of pages fetched at last checkpoint |
| `rows_fetched` | `int` | `0` | Number of task rows accumulated at last checkpoint |
| `chunks_checkpointed` | `int` | `0` | Number of checkpoint writes completed |

**Schema compatibility**: All fields use `int` type with `0` default. Pydantic `model_validate()` fills missing fields from defaults. No manifest version bump required.

### 5.2 S3 Key Layout (unchanged)

Checkpoint writes use the same S3 key as the final section write:

```
dataframes/{project_gid}/sections/{section_gid}.parquet
```

This means each checkpoint overwrites the previous one. The final write after all pages are fetched replaces the last checkpoint with complete data. There is no accumulation of checkpoint files on S3.

---

## 6. Sequence Diagrams

### 6.1 Large Section Fetch (Happy Path)

```
Builder                    PageIterator           S3 (via Persistence)    Manifest
  |                             |                        |                   |
  |-- list_async(section) ----->|                        |                   |
  |                             |                        |                   |
  |<-- task 1..100 (page 1) ---|                        |                   |
  |   [100 tasks = large]       |                        |                   |
  |                             |                        |                   |
  |   PACING LOOP:              |                        |                   |
  |<-- task 101..200 (p2) -----|                        |                   |
  |   ...                       |                        |                   |
  |<-- task 2401..2500 (p25) --|                        |                   |
  |   [25 pages: PAUSE]         |                        |                   |
  |   asyncio.sleep(2.0)        |                        |                   |
  |                             |                        |                   |
  |   ... pages 26-50 ...       |                        |                   |
  |   [50 pages: CHECKPOINT]    |                        |                   |
  |   convert tasks -> df       |                        |                   |
  |   -------------------------------- PutObject ------->|                   |
  |   -------------------------------------------------------- update ----->|
  |                             |                        |                   |
  |   ... pages 51-250 ...      |                        |                   |
  |   [checkpoints at 100, 150, 200, 250]                |                   |
  |                             |                        |                   |
  |   FINAL WRITE:              |                        |                   |
  |   convert all 25k tasks     |                        |                   |
  |   -------------------------------- PutObject ------->|                   |
  |   -------------------------------------------------- mark COMPLETE ---->|
```

### 6.2 Resume After Lambda Timeout

```
Builder (new invocation)                    S3                    Manifest
  |                                          |                       |
  |-- get_manifest_async() ------------------------------------------------>|
  |<-- manifest (section IN_PROGRESS, rows_fetched=10000, offset=100) ------|
  |                                          |                       |
  |-- read_section_async(section_gid) ------>|                       |
  |<-- checkpoint_df (10000 rows) ----------|                       |
  |                                          |                       |
  |-- Create new PageIterator               |                       |
  |-- Skip pages 1..100 (discard tasks)     |                       |
  |-- Accumulate pages 101..250             |                       |
  |   [with pacing + checkpoints]            |                       |
  |                                          |                       |
  |-- Merge checkpoint_df + new tasks        |                       |
  |-- Final write (25000 rows) ------------>|                       |
  |-- Mark COMPLETE ------------------------------------------------>|
```

---

## 7. Error Handling

### 7.1 S3 Checkpoint Write Failure

If `PutObject` fails during a checkpoint:
- Log warning with error details.
- Continue fetching -- the running task list is still in memory.
- The next checkpoint will include all data since the last successful checkpoint.
- If the Lambda completes, the final write replaces everything.
- If the Lambda times out, resume uses the last successful checkpoint.

### 7.2 Checkpoint Resume Failure

If the checkpoint parquet is missing or corrupt on resume:
- Log warning.
- Set `resume_offset = 0` and `checkpoint_df = None`.
- Re-fetch the entire section from scratch.
- This is the safe fallback -- no data loss, just wasted API calls.

### 7.3 Lambda Timeout During Paced Fetch

The most recent successful checkpoint parquet survives in S3. On the next invocation:
- The manifest shows the section as `IN_PROGRESS` with `rows_fetched > 0`.
- The builder reads the checkpoint and attempts resume.
- If resume fails, it falls back to full re-fetch.

### 7.4 Rate Limiter Interaction

The existing `RateLimitConfig` rate limiter and the pacing delay are complementary:
- The rate limiter prevents exceeding Asana's global request rate.
- The pacing delay prevents the request *pattern* from being classified as "exceptionally expensive."
- Both operate independently. The pacing `asyncio.sleep()` runs between page-batch processing. The rate limiter runs within `PageIterator._fetch_page()`.

### 7.5 Concurrent Section Checkpoint Contention

Multiple sections fetching in parallel (up to `max_concurrent_sections = 8`) each have independent pacing loops. Manifest updates use the per-project `asyncio.Lock` (existing mechanism at line 323 of `section_persistence.py`). Checkpoint metadata updates go through this same lock, so there is no race condition on manifest writes.

---

## 8. Performance Analysis

### 8.1 Time Budget for CONTACTS (~250 pages)

| Component | Estimate | Notes |
|-----------|----------|-------|
| API fetch (250 pages x ~0.5s/page) | ~125s | Unchanged from current |
| Pacing pauses (10 pauses x 2.0s) | ~20s | ceil(250/25) = 10 pauses |
| Checkpoint writes (5 writes x ~0.5s) | ~2.5s | 10MB parquet each |
| Task-to-row conversion at checkpoints | ~2.5s | 5 conversions of growing lists |
| **Total** | **~150s** | Well within 900s Lambda timeout |

### 8.2 Memory Budget

| Component | Estimate |
|-----------|----------|
| 25,000 task dicts (~2KB each) | ~50MB |
| DataFrame at checkpoint (growing) | ~10-50MB |
| Parquet serialization buffer | ~10MB (transient) |
| **Peak** | **~110MB** |

Peak memory of ~110MB is well within the 1024MB Lambda allocation. The parquet buffer is garbage-collected after each checkpoint write.

### 8.3 Small Section Impact

Sections with fewer than 100 tasks:
- First page fetched (same as before).
- Heuristic check: `len(first_page_tasks) < 100` -- no pacing activated.
- Proceeds through existing single-page path.
- **Added latency: 0**. One additional branch check per section.

---

## 9. Test Strategy

### 9.1 Unit Tests

**File**: `tests/unit/dataframes/builders/test_paced_fetch.py`

| Test | Description | Mock |
|------|-------------|------|
| `test_small_section_no_pacing` | Section with 50 tasks: no `asyncio.sleep` calls, no checkpoint writes | `PageIterator` returns 50 tasks in one page |
| `test_large_section_pacing_activated` | Section with 100 tasks on first page activates pacing | `PageIterator` returns 100 then 50 |
| `test_pacing_sleep_intervals` | 75 pages, `pace_pages_per_pause=25`: verify 3 `asyncio.sleep` calls | Mock `asyncio.sleep` |
| `test_checkpoint_write_at_intervals` | 120 pages, `checkpoint_every_n_pages=50`: verify 2 checkpoint writes (at 50 and 100) | Mock S3 write |
| `test_checkpoint_metadata_updated` | After checkpoint, `SectionInfo.chunks_checkpointed` increments | Mock manifest |
| `test_empty_section_no_pacing` | 0 tasks: no pacing, no checkpoint, marked COMPLETE with 0 rows | `PageIterator` returns empty |
| `test_exactly_100_tasks_pacing_harmless` | 100 tasks exactly: pacing activates, iterator exhausts on second page, no sleep called | `PageIterator` returns 100 then stops |
| `test_final_write_replaces_checkpoint` | After 250 pages, final write has all 25,000 rows | Mock S3 write, verify row count |

### 9.2 Resume Tests

**File**: `tests/unit/dataframes/builders/test_checkpoint_resume.py`

| Test | Description |
|------|-------------|
| `test_resume_from_checkpoint` | Manifest has `IN_PROGRESS` + `rows_fetched=5000` + `offset=50`. Checkpoint parquet exists. Verify pages 1-50 skipped, final df has checkpoint rows + new rows. |
| `test_resume_missing_checkpoint` | Manifest has `rows_fetched=5000` but parquet missing. Verify warning logged, full re-fetch. |
| `test_resume_corrupt_checkpoint` | Parquet exists but is corrupt. Verify warning logged, full re-fetch. |
| `test_no_resume_for_pending_section` | Section status is `PENDING` (not `IN_PROGRESS`). No resume attempt. |

### 9.3 Backward Compatibility Tests

**File**: `tests/unit/dataframes/test_section_info_compat.py`

| Test | Description |
|------|-------------|
| `test_section_info_defaults` | `SectionInfo()` has `last_fetched_offset=0`, `rows_fetched=0`, `chunks_checkpointed=0` |
| `test_section_info_from_legacy_dict` | Dict without new fields parses successfully with defaults |
| `test_manifest_mixed_section_infos` | Manifest with mix of old and new SectionInfo entries parses correctly |

### 9.4 Integration Test

**File**: `tests/integration/dataframes/test_large_section_e2e.py`

| Test | Description |
|------|-------------|
| `test_large_section_end_to_end` | Mock 250-page Asana API, run `build_progressive_async`, verify: no 429 errors, 5 checkpoint writes, final df has 25,000 rows |
| `test_large_section_resume_e2e` | Same as above but interrupt at checkpoint 3 (mock Lambda timeout), resume, verify final df has 25,000 rows |

---

## 10. Migration and Compatibility

### 10.1 Manifest Compatibility

- **Existing manifests**: Parse correctly. New `SectionInfo` fields default to `0`.
- **No version bump**: `SectionManifest.version` remains `1`.
- **No cache invalidation**: No `schema_version` change needed.

### 10.2 Deployment

- **Zero downtime**: The change is additive. The pacing logic only activates for sections returning 100+ tasks on the first page.
- **Rollback safe**: Reverting removes pacing. Sections revert to `.collect()` behavior. The only risk is that CONTACTS will again trigger cost-based 429s, which is the current (broken) state.
- **No infrastructure changes**: No new S3 keys, no new environment variables, no new Lambda configuration.

### 10.3 Feature Flags

None needed. The first-page heuristic is the implicit feature gate: pacing activates only when warranted by section size. There is no flag to force-enable or force-disable pacing beyond changing the module-level constants.

---

## 11. Architecture Decision Records

### ADR-LSR-001: Pacing in Builder, Not PageIterator

**Context**: The `PageIterator` is a generic pagination abstraction used across the codebase (tasks, sections, custom fields). Adding pacing to `PageIterator` would affect all callers, most of which do not need it.

**Decision**: Pacing logic lives entirely in `ProgressiveProjectBuilder._fetch_and_persist_section()`. The builder uses `async for` over `PageIterator` and introduces its own page-counting and sleep logic.

**Rationale**: Single Responsibility. `PageIterator` pages; the builder decides when to pause. This also means `PageIterator` remains testable as a pure pagination primitive without timing concerns.

**Consequences**: The builder contains more logic (~60 lines of pacing loop). If a second consumer needs pacing, it must reimplement it. This is acceptable because pacing is specific to the large-section ingestion use case.

---

### ADR-LSR-002: Direct S3 Write for Checkpoints

**Context**: `SectionPersistence.write_section_async()` marks the section as `COMPLETE` after writing. Checkpoints need to write to S3 but keep the section `IN_PROGRESS`.

**Decision**: The builder writes checkpoint parquets directly via `self._persistence._s3_client.put_object_async()`, bypassing `write_section_async()`. Manifest metadata is updated separately via a dedicated `_update_checkpoint_metadata()` method that acquires the manifest lock.

**Alternatives considered**:
1. **Add `checkpoint` parameter to `write_section_async()`**: Rejected. Changes the public contract for all callers to support a single-caller use case.
2. **Add `checkpoint_write_section_async()` to `SectionPersistence`**: Viable but adds a public method used by exactly one caller. Not worth the API surface increase.
3. **Write to a separate checkpoint key**: Rejected. D2 specifies single parquet per section with overwrite checkpoints. Separate keys would require cleanup logic.

**Rationale**: The builder already has intimate knowledge of the persistence layer's internal structure (S3 key format, manifest lock, etc.). Accessing private members for checkpoint writes is an acceptable trade-off given the tight coupling.

**Consequences**: Builder depends on internal `SectionPersistence` implementation details (`_s3_client`, `_make_section_key`, `_get_manifest_lock`, `_manifest_cache`, `_save_manifest_async`). Changes to these internals will require updating the builder's checkpoint logic. This is documented and the coupling is limited to two methods.

---

### ADR-LSR-003: Checkpoint-First Resume Strategy

**Context**: Asana's pagination offsets are opaque, short-lived tokens. They cannot be stored and reused across Lambda invocations. True "seek to offset" resume is not possible.

**Decision**: On resume, the builder:
1. Reads the checkpoint parquet (preserved data from last successful write).
2. Creates a fresh `PageIterator` and skips pages by consuming and discarding tasks.
3. Merges new tasks with checkpoint data.

The `last_fetched_offset` field tracks pages (not Asana offset tokens). It is used to know how many pages to skip on resume.

**Alternatives considered**:
1. **Store Asana offset token in manifest**: Rejected. Offset tokens are opaque and short-lived. They may expire between Lambda invocations.
2. **Full re-fetch on resume (no skip)**: Simpler but wastes more API calls. The page-skip approach is only marginally more complex and saves DataFrame construction + S3 write overhead for skipped pages.
3. **Skip nothing, re-fetch everything, rely on checkpoint as safety net only**: Viable. If the page-skip approach proves unreliable (e.g., section content changes between invocations causing row mismatches), this is the fallback.

**Rationale**: The primary value of checkpoints is data persistence across Lambda invocations, not API call savings. The resume-skip is a best-effort optimization. If it fails, the builder falls back to full re-fetch with the checkpoint's data discarded.

**Consequences**: Resume is imperfect. If section content changes between the checkpoint and resume (tasks added/removed), the skipped pages may not align with the original fetch. This is acceptable for point-in-time snapshots -- freshness probes detect structural changes on the next full build cycle.

---

### ADR-LSR-004: First-Page Heuristic for Large Section Detection

**Context**: The builder needs to know whether a section is "large" (needs pacing) before starting the pacing loop. Options include: task count metadata lookup, configuration-based section lists, or runtime heuristics.

**Decision**: Use the first page as a heuristic. If the first page returns exactly 100 tasks (a full page), the section likely has more pages and pacing activates. If it returns fewer than 100 tasks, the section fits in one page and no pacing is needed.

**Alternatives considered**:
1. **Separate metadata API call**: Rejected per D4. Adds an extra API call per section.
2. **Configuration-based list of large sections**: Rejected. Requires maintenance as sections grow/shrink. Not zero-configuration.
3. **Task count from section metadata**: Asana does not provide a task count on the section object. Would require a separate `GET /sections/{gid}/tasks?limit=1` call.

**Rationale**: Zero extra API calls. The first page is fetched anyway. The heuristic has a false positive rate of exactly one case: a section with exactly 100 tasks triggers pacing unnecessarily, but this is harmless (the iterator exhausts immediately with no sleep calls).

**Consequences**: Sections with exactly 100 tasks unnecessarily enter the pacing code path. No performance impact since the pacing loop exits immediately. Sections with 101+ tasks always get pacing, which is the correct behavior.

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Pacing delay too conservative (adds unnecessary latency) | Medium | Low | Constants are trivially tunable. Start at 2s, reduce based on production telemetry. |
| Pacing delay too aggressive (still triggers 429) | Low | High | Conservative default (2s per 25 pages). If 429s persist, increase delay or reduce pages-per-pause. Structured logging enables rapid diagnosis. |
| Checkpoint S3 write interrupted mid-PutObject | Very Low | Low | S3 PutObject is atomic. Partial writes are not visible. Previous checkpoint survives. |
| Resume page-skip misaligns with changed section content | Medium | Low | Acceptable for point-in-time snapshots. Freshness probes correct on next cycle. |
| Builder's private access to `SectionPersistence` internals breaks on refactor | Low | Medium | Documented in ADR-LSR-002. Covered by tests that exercise the full checkpoint path. |
| Memory spike from accumulating 25k tasks + DataFrame | Very Low | Low | ~110MB peak, well within 1024MB Lambda. CloudWatch memory monitoring. |

---

## 13. Attestation Table

| File | Absolute Path | Read |
|------|---------------|------|
| Progressive Builder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Yes |
| Section Persistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes |
| Config | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Yes |
| PageIterator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/common.py` | Yes |
| Fields (BASE_OPT_FIELDS) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/fields.py` | Yes |
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-large-section-resilience.md` | Yes |
| Existing TDD (format ref) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-query-engine-foundation.md` | Yes |
