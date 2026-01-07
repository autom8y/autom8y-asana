# TDD: Watermark-Based Task Filtering for Incremental Resume

**TDD ID**: TDD-DATAFRAME-BUILDER-WATERMARK-001
**Version**: 1.0
**Date**: 2026-01-07
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: DataFrame Builder Consolidation Sprint (T1.0)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Architecture Decision](#architecture-decision)
5. [Interface Contracts](#interface-contracts)
6. [Watermark Schema](#watermark-schema)
7. [Filter Algorithm](#filter-algorithm)
8. [Merge Strategy](#merge-strategy)
9. [Parallel Fetch Integration](#parallel-fetch-integration)
10. [Edge Cases](#edge-cases)
11. [Implementation Phases](#implementation-phases)
12. [Risk Assessment](#risk-assessment)
13. [ADRs](#adrs)

---

## Overview

This TDD specifies the watermark-based task filtering mechanism that enables incremental resume with parallel fetch in the unified DataFrame builder. The design consolidates capabilities from:

- **ProjectDataFrameBuilder** (`project.py`): Parallel section fetch via `build_with_parallel_fetch_async()`
- **ProgressiveProjectBuilder** (`progressive.py`): S3 persistence, section-level manifest, resume capability

The key insight: tasks cached in the DataFrame already have watermarks (`modified_at`). On resume, we fetch all tasks from sections, but only perform expensive DataFrame row extraction on tasks that are either new or changed since last cached.

### Solution Summary

| Component | Purpose |
|-----------|---------|
| `TaskWatermarkIndex` | In-DataFrame tracking of GID + modified_at for cached tasks |
| `IncrementalFilter` | Determines which tasks need processing vs skip |
| `DeltaMerger` | Merges incremental results with existing cached DataFrame |
| `SectionWatermarkTracker` | Per-section watermark for parallel coordination |

---

## Problem Statement

### Current State

Two builders exist with complementary but non-overlapping capabilities:

| Capability | ProjectDataFrameBuilder | ProgressiveProjectBuilder |
|------------|-------------------------|---------------------------|
| Parallel section fetch | Yes (`build_with_parallel_fetch_async`) | Yes (`gather_with_limit`) |
| S3 persistence | Yes (via `DataFramePersistence`) | Yes (via `SectionPersistence`) |
| Section manifest tracking | No | Yes (`SectionManifest`) |
| Resume from partial build | No | Yes (incomplete section tracking) |
| Task-level incremental | No (fetches all, caches rows) | No (fetches all, rebuilds all) |
| UnifiedTaskStore integration | Yes (mandatory) | Yes (optional) |

**Gap**: Neither builder can:
1. Resume a partial build AND skip re-processing unchanged tasks
2. Leverage existing cached task data to avoid redundant extraction

### Why This Matters

For large projects (10K+ tasks):
- Full rebuild: ~10 minutes (API fetch + extraction)
- Resume from section: ~5 minutes (API fetch remaining sections + extraction)
- **Target with watermarks**: ~1-2 minutes (API fetch + skip unchanged extraction)

---

## Goals and Non-Goals

### Goals

| ID | Goal | Rationale |
|----|------|-----------|
| G1 | Task-level watermark tracking in DataFrame | Enable skip of unchanged task extraction |
| G2 | Incremental extraction on resume | Only process tasks where `modified_at` > cached watermark |
| G3 | Parallel section fetch with watermark awareness | Each section filters independently |
| G4 | Merge strategy for incremental + cached | Consistent DataFrame output |
| G5 | Handle deleted tasks | Detect and remove stale cached rows |

### Non-Goals

| ID | Non-Goal | Reason |
|----|----------|--------|
| NG1 | Real-time sync | Batch-oriented, not event-driven |
| NG2 | Cross-project watermarks | Project-scoped only |
| NG3 | Row-level versioning | Task-level is sufficient |
| NG4 | Conflict resolution beyond "fresh wins" | No merge conflicts expected |

---

## Architecture Decision

### ADR-001: Watermark Storage Location

**Context**: Where to store per-task watermarks for incremental processing?

**Options Considered**:

1. **In the Polars DataFrame itself** (as `_modified_at` column)
   - Pros: Self-contained, always in sync with data, no extra storage
   - Cons: Column must be preserved through all transformations

2. **Separate watermark manifest in S3**
   - Pros: Independent of DataFrame schema
   - Cons: Extra S3 read/write, sync issues

3. **UnifiedTaskStore metadata**
   - Pros: Already tracking version/modified_at per task
   - Cons: Need to query store for every task on filter

**Decision**: **Option 1 - In DataFrame with `_modified_at` column**

The DataFrame already contains task data. Adding `_modified_at` as a reserved column (prefixed with `_` to indicate internal use) keeps watermarks in sync with cached rows. On incremental processing:
- Load existing DataFrame from S3
- Build index: `{gid: modified_at}` from `gid` and `_modified_at` columns
- Filter incoming tasks against this index

**Consequences**:
- Schema must include `_modified_at: Datetime` column
- Existing DataFrames without this column need migration (add column with None)
- Column preserved through `concat()` operations

---

## Interface Contracts

### 5.1 Unified Builder Interface

```python
class UnifiedProjectBuilder:
    """Consolidated builder with parallel fetch and incremental resume.

    Combines ProjectDataFrameBuilder parallel fetch with
    ProgressiveProjectBuilder resume capability, adding watermark-based
    task filtering for incremental extraction.
    """

    async def build_with_parallel_fetch_async(
        self,
        client: AsanaClient,
        *,
        resume: bool = True,
        incremental: bool = True,
        max_concurrent_sections: int = 8,
    ) -> BuildResult:
        """Build DataFrame with parallel fetch and optional incremental resume.

        Args:
            client: AsanaClient for API calls.
            resume: If True, check for existing manifest and resume.
            incremental: If True, skip extraction for unchanged tasks.
            max_concurrent_sections: Concurrency limit for section fetch.

        Returns:
            BuildResult with DataFrame and metrics.

        Behavior:
            1. Load existing DataFrame from S3 (if resume=True)
            2. Build watermark index from existing DataFrame
            3. Enumerate sections, check manifest for incomplete
            4. Parallel fetch tasks from incomplete sections
            5. For each fetched task:
               - If not in watermark index: PROCESS (new task)
               - If modified_at > cached watermark: PROCESS (changed)
               - If modified_at <= cached watermark: SKIP (unchanged)
            6. Merge processed rows with existing unchanged rows
            7. Persist updated DataFrame and manifest
        """
        ...
```

### 5.2 Build Result

```python
@dataclass
class BuildResult:
    """Result of unified project build with incremental metrics."""

    df: pl.DataFrame
    watermark: datetime
    total_rows: int

    # Section-level metrics
    sections_fetched: int
    sections_resumed: int

    # Task-level metrics (new with watermark filtering)
    tasks_fetched: int       # Total tasks returned from API
    tasks_processed: int     # Tasks that needed extraction
    tasks_skipped: int       # Tasks skipped (unchanged)
    tasks_deleted: int       # Tasks removed (no longer in fetch)

    # Performance metrics
    fetch_time_ms: float
    filter_time_ms: float    # Time spent in watermark filtering
    extract_time_ms: float   # Time spent in row extraction
    merge_time_ms: float     # Time spent merging results
    total_time_ms: float
```

### 5.3 Incremental Filter Interface

```python
@dataclass
class TaskFilterResult:
    """Result of filtering tasks against watermark index."""

    to_process: list[dict[str, Any]]   # Tasks needing extraction
    to_skip: list[str]                  # GIDs of unchanged tasks
    to_delete: list[str]               # GIDs no longer present in fetch

    @property
    def process_count(self) -> int:
        return len(self.to_process)

    @property
    def skip_count(self) -> int:
        return len(self.to_skip)


class IncrementalFilter:
    """Filters fetched tasks against cached watermarks."""

    def __init__(self, watermark_index: dict[str, datetime]) -> None:
        """Initialize with watermark index from existing DataFrame.

        Args:
            watermark_index: Mapping of task GID to cached modified_at.
        """
        self._index = watermark_index

    @classmethod
    def from_dataframe(cls, df: pl.DataFrame) -> "IncrementalFilter":
        """Build filter from existing DataFrame.

        Extracts gid and _modified_at columns to build watermark index.
        """
        if df.is_empty() or "_modified_at" not in df.columns:
            return cls({})

        index = {}
        for row in df.select(["gid", "_modified_at"]).iter_rows():
            gid, modified_at = row
            if gid and modified_at:
                index[gid] = modified_at
        return cls(index)

    def filter(
        self,
        fetched_tasks: list[dict[str, Any]],
    ) -> TaskFilterResult:
        """Filter tasks based on watermark comparison.

        Args:
            fetched_tasks: Tasks fetched from API with modified_at.

        Returns:
            TaskFilterResult with categorized tasks.
        """
        to_process = []
        to_skip = []
        fetched_gids = set()

        for task in fetched_tasks:
            gid = task.get("gid")
            if not gid:
                continue

            fetched_gids.add(gid)
            modified_at = self._parse_modified_at(task.get("modified_at"))
            cached_watermark = self._index.get(gid)

            if cached_watermark is None:
                # New task - not in cache
                to_process.append(task)
            elif modified_at is None:
                # No modified_at on task - process to be safe
                to_process.append(task)
            elif modified_at > cached_watermark:
                # Changed since cached
                to_process.append(task)
            else:
                # Unchanged - skip extraction
                to_skip.append(gid)

        # Detect deleted tasks (in cache but not in fetch)
        cached_gids = set(self._index.keys())
        to_delete = list(cached_gids - fetched_gids)

        return TaskFilterResult(
            to_process=to_process,
            to_skip=to_skip,
            to_delete=to_delete,
        )

    def _parse_modified_at(self, value: str | None) -> datetime | None:
        """Parse modified_at string to datetime."""
        if not value:
            return None
        # Handle Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
```

---

## Watermark Schema

### 6.1 DataFrame Schema Extension

Add reserved `_modified_at` column to all DataFrames:

```python
# In DataFrameSchema or column definitions
WATERMARK_COLUMN = ColumnDef(
    name="_modified_at",
    dtype="Datetime",
    source="modified_at",
    description="Task modification timestamp for incremental processing",
)
```

**Column Behavior**:
- Always populated from task's `modified_at` field
- Preserved through all DataFrame operations
- Used only for watermark filtering, not exposed in API responses
- Nullable (for legacy DataFrames during migration)

### 6.2 Section Watermark in Manifest

Extend `SectionInfo` to track per-section watermark:

```python
class SectionInfo(BaseModel):
    """Information about a single section."""

    status: SectionStatus = SectionStatus.PENDING
    rows: int = 0
    written_at: datetime | None = None
    error: str | None = None

    # NEW: Watermark tracking
    max_modified_at: datetime | None = None  # Latest modified_at in section
```

This enables:
- Quick staleness check per section
- Potential future optimization: skip entire section if no tasks modified

### 6.3 Storage Layout

```
dataframes/
└── {project_gid}/
    ├── manifest.json          # Section status + per-section watermarks
    ├── sections/
    │   ├── {section_gid}.parquet  # Section DataFrame with _modified_at
    │   └── ...
    ├── dataframe.parquet      # Merged DataFrame with _modified_at
    ├── watermark.json         # Global build watermark
    └── gid_lookup_index.json
```

---

## Filter Algorithm

### 7.1 Pseudocode

```
FUNCTION build_incremental(project_gid, sections_to_fetch):
    # Step 1: Load existing state
    existing_df = load_dataframe_from_s3(project_gid)
    watermark_filter = IncrementalFilter.from_dataframe(existing_df)

    # Step 2: Parallel fetch all tasks from sections
    all_fetched_tasks = []
    PARALLEL FOR section_gid IN sections_to_fetch:
        tasks = fetch_tasks_for_section(section_gid)
        all_fetched_tasks.extend(tasks)

    # Step 3: Filter tasks
    filter_result = watermark_filter.filter(all_fetched_tasks)

    # Step 4: Process only changed/new tasks
    new_rows = []
    FOR task IN filter_result.to_process:
        row = extract_dataframe_row(task)  # Expensive operation
        new_rows.append(row)

    # Step 5: Build result DataFrame
    new_df = DataFrame(new_rows)

    # Step 6: Get unchanged rows from existing DataFrame
    unchanged_df = existing_df.filter(
        col("gid").is_in(filter_result.to_skip)
    )

    # Step 7: Merge
    merged_df = concat([unchanged_df, new_df])

    # Step 8: Handle deletions (rows in cache but not in fetch)
    IF filter_result.to_delete:
        merged_df = merged_df.filter(
            ~col("gid").is_in(filter_result.to_delete)
        )

    RETURN merged_df
```

### 7.2 Filter Decision Matrix

| Condition | Action | Rationale |
|-----------|--------|-----------|
| GID not in cache | PROCESS | New task |
| GID in cache, `modified_at` > cached | PROCESS | Task changed |
| GID in cache, `modified_at` <= cached | SKIP | Unchanged, use cached row |
| GID in cache, `modified_at` is None | PROCESS | Can't determine, be safe |
| GID in cache, not in fetched | DELETE | Task removed from project/section |

---

## Merge Strategy

### 8.1 Delta Merge Implementation

```python
class DeltaMerger:
    """Merges incremental results with cached DataFrame."""

    def merge(
        self,
        existing_df: pl.DataFrame,
        new_rows: list[dict[str, Any]],
        skipped_gids: list[str],
        deleted_gids: list[str],
        schema: DataFrameSchema,
    ) -> pl.DataFrame:
        """Merge incremental extraction with existing cache.

        Args:
            existing_df: Existing cached DataFrame.
            new_rows: Newly extracted rows for changed/new tasks.
            skipped_gids: GIDs of unchanged tasks (keep from existing).
            deleted_gids: GIDs to remove (no longer in project).
            schema: DataFrame schema for type enforcement.

        Returns:
            Merged DataFrame with all current tasks.
        """
        # 1. Filter existing to unchanged rows only
        unchanged_df = existing_df.filter(
            pl.col("gid").is_in(skipped_gids)
        )

        # 2. Build DataFrame from new rows
        if new_rows:
            new_df = pl.DataFrame(
                new_rows,
                schema=schema.to_polars_schema()
            )
        else:
            new_df = pl.DataFrame(schema=schema.to_polars_schema())

        # 3. Concatenate unchanged + new
        merged = pl.concat([unchanged_df, new_df], how="diagonal_relaxed")

        # 4. Remove deleted (already not in new_rows, but be explicit)
        if deleted_gids:
            merged = merged.filter(~pl.col("gid").is_in(deleted_gids))

        # 5. Deduplicate by GID (new wins over old if any duplicates)
        merged = merged.unique(subset=["gid"], keep="last")

        return merged
```

### 8.2 Schema Change Handling

When schema version changes between runs:

```python
def handle_schema_migration(
    existing_df: pl.DataFrame,
    current_schema: DataFrameSchema,
) -> pl.DataFrame | None:
    """Check schema compatibility and migrate if possible.

    Returns:
        Migrated DataFrame, or None if incompatible (force rebuild).
    """
    existing_columns = set(existing_df.columns)
    required_columns = {col.name for col in current_schema.columns}

    # New columns added - can migrate by adding nulls
    new_columns = required_columns - existing_columns
    if new_columns:
        for col_name in new_columns:
            col_def = current_schema.get_column(col_name)
            existing_df = existing_df.with_columns(
                pl.lit(None).alias(col_name).cast(col_def.polars_dtype)
            )

    # Columns removed - just drop them
    removed_columns = existing_columns - required_columns
    if removed_columns:
        existing_df = existing_df.drop(list(removed_columns))

    # Check _modified_at column exists (required for watermark)
    if "_modified_at" not in existing_df.columns:
        # Add with None - will cause all tasks to be reprocessed
        existing_df = existing_df.with_columns(
            pl.lit(None).alias("_modified_at").cast(pl.Datetime)
        )

    return existing_df
```

---

## Parallel Fetch Integration

### 9.1 Per-Section Watermark Filtering

Each section operates independently during parallel fetch:

```python
async def fetch_and_filter_section_async(
    section_gid: str,
    watermark_filter: IncrementalFilter,
    client: AsanaClient,
) -> SectionResult:
    """Fetch section tasks and apply watermark filter.

    Runs in parallel with other sections.
    """
    # 1. Fetch all tasks for section
    tasks = await client.tasks.list_async(
        section=section_gid,
        opt_fields=_BASE_OPT_FIELDS,
    ).collect()

    # 2. Filter against global watermark index
    # Note: Filter is read-only, safe for concurrent access
    filter_result = watermark_filter.filter(tasks)

    # 3. Extract rows only for tasks needing processing
    rows = []
    for task in filter_result.to_process:
        row = await extract_row_async(task)
        rows.append(row)

    return SectionResult(
        section_gid=section_gid,
        rows=rows,
        skipped_gids=filter_result.to_skip,
        # Note: deleted_gids tracked globally, not per-section
    )
```

### 9.2 Race Condition Mitigation

**Concern**: Multiple sections writing results concurrently.

**Solution**: Sections produce results, main coordinator does the merge:

```python
async def build_with_parallel_fetch_async(...) -> BuildResult:
    # 1. Load existing DataFrame once (before parallel work)
    existing_df = await load_from_s3_async(project_gid)
    watermark_filter = IncrementalFilter.from_dataframe(existing_df)

    # 2. Parallel fetch and filter (sections don't write to shared state)
    section_tasks = [
        fetch_and_filter_section_async(gid, watermark_filter, client)
        for gid in sections_to_fetch
    ]
    section_results = await gather_with_limit(
        section_tasks,
        max_concurrent=max_concurrent_sections
    )

    # 3. Aggregate results (single-threaded, no races)
    all_new_rows = []
    all_skipped_gids = []
    for result in section_results:
        all_new_rows.extend(result.rows)
        all_skipped_gids.extend(result.skipped_gids)

    # 4. Compute deleted GIDs
    all_fetched_gids = set(row["gid"] for row in all_new_rows) | set(all_skipped_gids)
    cached_gids = set(existing_df["gid"].to_list())
    deleted_gids = list(cached_gids - all_fetched_gids)

    # 5. Merge (single-threaded)
    merged_df = merger.merge(
        existing_df=existing_df,
        new_rows=all_new_rows,
        skipped_gids=all_skipped_gids,
        deleted_gids=deleted_gids,
        schema=schema,
    )

    # 6. Persist (atomic write)
    await persist_async(project_gid, merged_df)

    return BuildResult(...)
```

### 9.3 Concurrency Safety

| Component | Thread Safety | Notes |
|-----------|---------------|-------|
| `IncrementalFilter` | Read-only, safe | Shared across section workers |
| `DataFrameViewPlugin` | Thread-safe | Per-call extraction |
| `UnifiedTaskStore` | Thread-safe | Concurrent get/put supported |
| `DeltaMerger` | Single-threaded | Called after all sections complete |
| S3 writes | Atomic per-key | Final write after merge |

---

## Edge Cases

### 10.1 Deleted Tasks

**Scenario**: Task was in project, now removed (via archive, delete, or section move).

**Detection**: Task GID in cached DataFrame but not in fresh API fetch.

**Handling**:
```python
# In filter
cached_gids = set(watermark_index.keys())
fetched_gids = set(task["gid"] for task in fetched_tasks)
deleted_gids = cached_gids - fetched_gids

# In merge
merged_df = merged_df.filter(~pl.col("gid").is_in(deleted_gids))
```

**Edge Case**: Task moved to different section within same project.
- Handled correctly: Will appear in new section's fetch, treated as "unchanged" if not modified.

### 10.2 Schema Changes Between Runs

**Scenario**: Schema version changes (new column added, column removed).

**Detection**: Compare cached DataFrame columns with current schema.

**Handling**:

| Change Type | Action |
|-------------|--------|
| Column added | Add column with null values, reprocess all tasks |
| Column removed | Drop column, no reprocessing needed |
| Column type changed | Force full rebuild (incompatible) |
| `_modified_at` missing | Add null column, all tasks will be reprocessed |

### 10.3 Clock Skew

**Scenario**: Task's `modified_at` is earlier than cached watermark due to clock issues.

**Detection**: `modified_at < cached_watermark` but task has actually changed.

**Mitigation**:
- Trust Asana's `modified_at` as authoritative
- If suspected, user can force full rebuild with `incremental=False`

### 10.4 Partial Build Failure

**Scenario**: Build fails after processing some sections, before persist.

**Recovery**:
- Manifest tracks incomplete sections
- On resume, incomplete sections refetch all tasks
- Filter still works: unchanged tasks skip extraction

### 10.5 Empty Sections

**Scenario**: Section has no tasks.

**Handling**:
- Mark section as complete with 0 rows
- No contribution to merged DataFrame
- Previous tasks from this section are marked deleted

### 10.6 Very Large Projects

**Scenario**: Project with 50K+ tasks.

**Considerations**:
- Watermark index is O(n) memory: 50K * (GID + datetime) ~ 5MB
- Filter operation is O(n) per section
- Merge is O(n) for concat

**Optimization**: If memory pressure, could use bloom filter for "definitely not in cache" check before exact lookup.

---

## Implementation Phases

### Phase 1: Watermark Column in DataFrame

**Tasks**:
1. Add `_modified_at` column to DataFrameSchema
2. Update `DataFrameViewPlugin._extract_row_async` to populate column
3. Ensure column preserved through concat/merge operations
4. Migration: Add null column to existing DataFrames on load

**Validation**:
- [ ] New builds include `_modified_at` column
- [ ] Existing DataFrames load without error (null watermarks)

### Phase 2: IncrementalFilter Implementation

**Tasks**:
1. Implement `IncrementalFilter` class
2. Add `from_dataframe` factory method
3. Implement `filter` method with decision matrix
4. Unit tests for all filter conditions

**Validation**:
- [ ] Filter correctly categorizes new/changed/unchanged/deleted
- [ ] Performance: <10ms for 10K task filter

### Phase 3: DeltaMerger Implementation

**Tasks**:
1. Implement `DeltaMerger.merge` method
2. Handle schema migration cases
3. Ensure deduplication by GID
4. Integration tests for merge scenarios

**Validation**:
- [ ] Merge produces correct DataFrame
- [ ] Unchanged rows preserved exactly
- [ ] Deleted rows removed

### Phase 4: Unified Builder Integration

**Tasks**:
1. Create `UnifiedProjectBuilder` combining both builders
2. Integrate filter and merger into parallel fetch flow
3. Update metrics to include incremental stats
4. End-to-end tests

**Validation**:
- [ ] Incremental build skips unchanged task extraction
- [ ] Performance improvement measured (target: 50%+ reduction)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Watermark index memory overhead | Low | Medium | Bounded by project size; could use bloom filter |
| Clock skew causes missed updates | Low | Medium | Trust Asana timestamps; force rebuild option |
| Schema migration complexity | Medium | High | Clear migration path; force rebuild on type changes |
| Parallel merge race conditions | Low | High | Coordinator pattern; sections produce, main merges |
| Deleted task detection false positives | Low | Medium | Only delete if not in current fetch |

---

## ADRs

### ADR-001: Watermark Storage in DataFrame

**Status**: Accepted

**Context**: Need to track per-task modification timestamps for incremental filtering.

**Decision**: Store `_modified_at` as reserved column in DataFrame.

**Consequences**:
- Self-contained tracking without external state
- Must handle legacy DataFrames without column
- Column must survive all transformations

### ADR-002: Global Filter with Per-Section Fetch

**Status**: Accepted

**Context**: Sections fetch in parallel but filter needs holistic view.

**Decision**:
- Build watermark index from full existing DataFrame (global)
- Share read-only filter across parallel section workers
- Aggregate results before merge (coordinator pattern)

**Consequences**:
- Thread-safe parallel fetching
- No per-section watermark optimization (acceptable trade-off)
- Clear single point of merge

### ADR-003: Deleted Task Detection via Fetch Absence

**Status**: Accepted

**Context**: How to detect tasks removed from project?

**Decision**: Task is deleted if GID in cache but not in fresh API fetch.

**Consequences**:
- Simple detection logic
- Requires fetching all sections to detect deletions
- Edge case: task moved between sections handled correctly

---

## Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Resume build time (10K tasks) | ~5 min | <2 min | Timer logs |
| Unchanged task extraction | 0% skip | 80%+ skip | Metric: tasks_skipped |
| Memory overhead | N/A | <10MB for 50K tasks | Heap profiling |
| Test coverage | N/A | 90%+ for new code | pytest-cov |

---

## Appendix: Code Location Reference

| Component | Proposed Location |
|-----------|-------------------|
| `IncrementalFilter` | `src/autom8_asana/dataframes/builders/incremental_filter.py` |
| `DeltaMerger` | `src/autom8_asana/dataframes/builders/delta_merger.py` |
| `UnifiedProjectBuilder` | `src/autom8_asana/dataframes/builders/unified.py` |
| Watermark column addition | `src/autom8_asana/dataframes/views/dataframe_view.py` |

---

## References

- `src/autom8_asana/dataframes/builders/project.py` - ProjectDataFrameBuilder
- `src/autom8_asana/dataframes/builders/progressive.py` - ProgressiveProjectBuilder
- `src/autom8_asana/cache/unified.py` - UnifiedTaskStore
- `src/autom8_asana/dataframes/section_persistence.py` - SectionPersistence
- `src/autom8_asana/cache/entry.py` - CacheEntry with version tracking
