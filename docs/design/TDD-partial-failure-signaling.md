# TDD: Progressive Build Partial Failure Signaling

**TDD ID**: TDD-PARTIAL-FAILURE-SIGNALING-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: Architectural Opportunities Initiative, C2 (Wave 2)
**Spike References**: S0-006 (Concurrent Build Frequency Analysis)
**Depends On**: TDD-CACHE-INVALIDATION-001 (Sprint 1, C1 exceptions), TDD-CROSS-TIER-FRESHNESS-001 (Sprint 2, A2 FreshnessStamp)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Design: SectionResult](#component-design-sectionresult)
6. [Component Design: BuildResult](#component-design-buildresult)
7. [Integration: ProgressiveProjectBuilder](#integration-progressiveprojectbuilder)
8. [Integration: DataFrameCache](#integration-dataframecache)
9. [Integration: Callers and Consumers](#integration-callers-and-consumers)
10. [Backward Compatibility](#backward-compatibility)
11. [Data Flow Diagrams](#data-flow-diagrams)
12. [Non-Functional Considerations](#non-functional-considerations)
13. [Test Strategy](#test-strategy)
14. [Risk Assessment](#risk-assessment)
15. [ADRs](#adrs)
16. [Success Criteria](#success-criteria)

---

## Overview

Currently, `ProgressiveProjectBuilder.build_progressive_async()` returns a `ProgressiveBuildResult` that reports aggregate metrics (sections_fetched, sections_resumed, total_rows) but provides **no per-section failure detail**. When `_fetch_and_persist_section()` returns `False`, the section is silently excluded from the merged DataFrame. The caller receives a DataFrame that looks correct but may be missing entire sections of data -- with no structured signal to distinguish "this project has 500 tasks" from "this project has 500 tasks but 200 more failed to load."

This TDD introduces `SectionResult` (per-section outcome) and `BuildResult` (aggregate build outcome with status classification) to make partial failures visible and actionable. Consumers -- the `DataFrameCache`, startup preload, SWR refresh, and query service -- can then make informed decisions: serve partial data with a warning, reject and trigger retry, or log for operator investigation.

### Solution Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| `SectionResult` | `dataframes/builders/build_result.py` | Per-section outcome: status, error, row count, timing |
| `BuildResult` | `dataframes/builders/build_result.py` | Aggregate build outcome with status classification and section-level detail |
| `BuildStatus` | `dataframes/builders/build_result.py` | Three-state enum: SUCCESS, PARTIAL, FAILURE |
| `ProgressiveProjectBuilder` changes | `dataframes/builders/progressive.py` | Produces `BuildResult` instead of `ProgressiveBuildResult` |
| `DataFrameCache.put_async` changes | `cache/dataframe_cache.py` | Accepts optional `BuildResult` for quality metadata on cache entries |
| Consumer integration | Various callers | React to BuildStatus for serve/reject/retry decisions |

---

## Problem Statement

### Current State

The `_fetch_and_persist_section()` method in `ProgressiveProjectBuilder` catches all exceptions, logs the failure, marks the section as `FAILED` in the manifest, and returns `False`. The caller (`build_progressive_async`) counts successes with `sum(1 for r in results if r)` but does not record which sections failed, why they failed, or how much data was lost.

```python
# Current code in progressive.py line 449
sections_fetched = sum(1 for r in results if r)
```

The `ProgressiveBuildResult` dataclass has no field for per-section errors or a status classification:

```python
@dataclass
class ProgressiveBuildResult:
    df: pl.DataFrame
    watermark: datetime
    total_rows: int
    sections_fetched: int
    sections_resumed: int
    fetch_time_ms: float
    total_time_ms: float
    sections_probed: int = 0
    sections_delta_updated: int = 0
```

### The Three Gaps

**Gap PF1: No per-section error detail.** When a section fails, the only record is a log line (`section_fetch_failed`) and a `FAILED` status in the S3 manifest. The build result does not carry the error. Callers cannot programmatically determine what failed or assess data completeness.

**Gap PF2: No build status classification.** A build that produces a DataFrame is treated identically whether 0 sections or 5 sections failed. There is no structured signal to distinguish a clean build from a partial build. The consumer (DataFrameCache, query service) has no way to attach a data-quality warning.

**Gap PF3: No aggregate freshness from partial builds.** Per TDD-CROSS-TIER-FRESHNESS-001, `DataFrameCache.put_async()` will accept optional `section_stamps` to compute aggregate freshness. But if some sections failed, the aggregate freshness should reflect the gap -- a DataFrame missing 3 of 10 sections is less reliable than one with all 10, regardless of individual section freshness.

### Why Now

The C1 exception hierarchy (Sprint 1) provides structured error types that enable meaningful error classification in `SectionResult`. The A2 cross-tier freshness TDD (Sprint 2) adds `FreshnessStamp` to cache entries. BuildResult integrates with both: it classifies errors using the exception hierarchy and carries freshness stamps for successful sections. Building C2 now means freshness and failure signaling are designed together rather than retrofitted.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Gap Addressed |
|----|------|---------------|
| G1 | Every section produces a `SectionResult` with status, error detail, row count, and timing | PF1 |
| G2 | `BuildResult` classifies the build as SUCCESS, PARTIAL, or FAILURE based on section outcomes | PF2 |
| G3 | `BuildResult` carries per-section results enabling callers to inspect which sections failed and why | PF1 |
| G4 | `BuildResult` computes aggregate `FreshnessStamp` from successful sections, excluding failed ones | PF3 |
| G5 | `DataFrameCache` stores build quality metadata so downstream consumers can serve partial data with appropriate warnings | PF2 |
| G6 | Happy path (all sections succeed) is indistinguishable in behavior from today | All |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Automatic retry of failed sections within the same build | Retry logic belongs to a future retry orchestrator (C3). BuildResult provides the information; retry policy is a separate concern. |
| NG2 | Circuit breaker integration for partial failures | The existing `CircuitBreaker` in DataFrameCache operates at the project level. Per-section circuit breaking is overengineered for current load. |
| NG3 | API-level partial failure headers | Surfacing build quality to external consumers via HTTP headers is a separate concern layered on top of this plumbing. |
| NG4 | Replace `ProgressiveBuildResult` in a single PR | The migration from `ProgressiveBuildResult` to `BuildResult` can be phased. Both can coexist during migration. |
| NG5 | Per-section retry budgets or backoff | Belongs to C3 (Unified Retry Orchestrator). |

---

## Proposed Architecture

### System Context

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                BUILD RESULT LAYER                        │
                    │                                                          │
                    │  ┌──────────────┐    ┌───────────────┐                   │
                    │  │ SectionResult│    │  BuildResult   │                   │
                    │  │ (dataclass)  │    │  (dataclass)   │                   │
                    │  │              │    │                │                   │
                    │  │ section_gid  │    │ status         │                   │
                    │  │ status       │    │ sections[]     │                   │
                    │  │ error        │◄───│ dataframe      │                   │
                    │  │ row_count    │    │ watermark      │                   │
                    │  │ fetch_time   │    │ freshness_stamp│                   │
                    │  └──────────────┘    │ timing         │                   │
                    │                      └───────┬───────┘                   │
                    │                              │                           │
                    └──────────────────────────────┼───────────────────────────┘
                                                   │
                           ┌───────────────────────┼───────────────────┐
                           │                       │                   │
                           ▼                       ▼                   ▼
                ┌──────────────────┐   ┌──────────────────┐  ┌───────────────┐
                │ Progressive      │   │ DataFrameCache   │  │ Startup       │
                │ ProjectBuilder   │   │                  │  │ Preload /     │
                │                  │   │ put_async() with │  │ SWR Refresh   │
                │ Produces         │   │ build quality    │  │               │
                │ BuildResult      │   │ metadata         │  │ Reacts to     │
                │ from sections    │   │                  │  │ BuildStatus   │
                └──────────────────┘   └──────────────────┘  └───────────────┘
```

### Key Design Decisions Summary

1. **Separate module** -- `BuildResult` and `SectionResult` live in `dataframes/builders/build_result.py`, not in `progressive.py`. This allows other builder implementations to produce the same result types.
2. **BuildStatus is a three-state enum** -- SUCCESS (all sections OK), PARTIAL (some failed, DataFrame produced), FAILURE (no sections succeeded or no DataFrame produced). Three states map to three consumer actions: serve, serve-with-warning, reject.
3. **SectionResult is a frozen dataclass** -- Immutable after creation. Thread-safe for async code. Contains only metadata, not the section DataFrame itself (which is in S3 or in-memory via the builder).
4. **BuildResult replaces ProgressiveBuildResult** -- BuildResult is a strict superset. It contains all fields from ProgressiveBuildResult plus per-section results and status classification. Migration is additive.
5. **FreshnessStamp integration is optional** -- BuildResult computes an aggregate FreshnessStamp from successful sections when the A2 infrastructure is available. Without it, the stamp is None (backward compatible).

---

## Component Design: SectionResult

### Dataclass Definition

```python
# src/autom8_asana/dataframes/builders/build_result.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl
    from autom8_asana.cache.freshness_stamp import FreshnessStamp


class SectionOutcome(str, Enum):
    """Outcome of fetching and persisting a single section.

    Three terminal states for a section fetch:
    - SUCCESS: Tasks fetched, DataFrame built, persisted to S3.
    - ERROR: Fetch or persistence failed. Error details in SectionResult.
    - SKIPPED: Section was skipped (e.g., resumed from manifest, or
      empty section detected during probe).
    """

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class SectionResult:
    """Outcome of processing a single section during a build.

    Frozen for thread safety in async contexts. Created once per
    section during the build and collected into BuildResult.

    Attributes:
        section_gid: Asana section GID.
        outcome: Terminal outcome (SUCCESS, ERROR, SKIPPED).
        row_count: Number of rows produced (0 for ERROR/SKIPPED).
        fetch_time_ms: Wall-clock time for this section's fetch
            and persistence, in milliseconds.
        error_message: Human-readable error description if ERROR.
            None for SUCCESS/SKIPPED.
        error_type: Exception class name if ERROR (e.g.,
            "AsanaAPIError", "S3TransportError"). Enables
            programmatic classification without coupling to
            exception types.
        watermark: Section-level watermark (max modified_at) if
            SUCCESS. None otherwise.
        resumed: True if this section was loaded from S3 manifest
            (not fetched from API). Always has outcome=SKIPPED.

    Example:
        >>> result = SectionResult(
        ...     section_gid="12345",
        ...     outcome=SectionOutcome.SUCCESS,
        ...     row_count=42,
        ...     fetch_time_ms=1250.5,
        ...     watermark=datetime(2026, 2, 4, tzinfo=UTC),
        ... )
        >>> result.is_success
        True
    """

    section_gid: str
    outcome: SectionOutcome
    row_count: int = 0
    fetch_time_ms: float = 0.0
    error_message: str | None = None
    error_type: str | None = None
    watermark: datetime | None = None
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """True if the section was successfully fetched and persisted."""
        return self.outcome == SectionOutcome.SUCCESS

    @property
    def is_error(self) -> bool:
        """True if the section failed."""
        return self.outcome == SectionOutcome.ERROR
```

### Design Rationale

**Why `error_type` as string instead of the exception instance?** Frozen dataclasses should not hold mutable references. Exception objects carry tracebacks and chain references that complicate serialization and increase memory pressure. The class name as a string is sufficient for programmatic classification (e.g., `if result.error_type == "S3TransportError": retry`). The full exception is logged at the point of failure.

**Why `resumed` flag instead of a fourth SectionOutcome?** Resumed sections are logically "skipped" from the fetch perspective -- no API call was made. But the caller may want to distinguish "skipped because resumed from S3" from "skipped because empty." The `resumed` flag on the SKIPPED outcome provides this distinction without inflating the enum.

**Why `frozen=True` and `slots=True`?** SectionResults are created during concurrent section fetches and collected into a list. Immutability prevents accidental mutation after creation. Slots reduce per-instance memory by ~40 bytes (relevant when there are 30+ sections).

---

## Component Design: BuildResult

### Dataclass Definition

```python
class BuildStatus(str, Enum):
    """Overall outcome of a DataFrame build.

    Three states mapping to three consumer actions:
    - SUCCESS: All sections completed. Serve without concern.
    - PARTIAL: Some sections failed but a DataFrame was produced
      from the successful ones. Serve with data-quality warning.
    - FAILURE: No usable DataFrame produced. Reject and signal
      upstream to retry or serve LKG.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


@dataclass(frozen=True)
class BuildResult:
    """Aggregate result of a DataFrame build operation.

    Captures the full picture of a build: overall status, per-section
    results, the produced DataFrame (if any), timing, and freshness.

    Replaces ProgressiveBuildResult with strictly more information.
    The happy path (all sections succeed) produces BuildStatus.SUCCESS
    with the same DataFrame as before.

    Construction: Use the class methods `success()`, `partial()`,
    and `failure()` for clarity, or construct directly.

    Attributes:
        status: Overall build outcome (SUCCESS, PARTIAL, FAILURE).
        sections: Per-section results, one per section in the project.
        dataframe: Merged DataFrame from successful sections.
            None only for FAILURE status.
        watermark: Build timestamp.
        project_gid: Asana project GID.
        entity_type: Entity type (e.g., "offer", "contact").
        total_time_ms: Total build wall-clock time in milliseconds.
        fetch_time_ms: Time spent fetching from API in milliseconds.
        sections_probed: Number of sections checked for freshness.
        sections_delta_updated: Number of sections updated via delta merge.
        freshness_stamp: Aggregate FreshnessStamp from successful
            sections (per TDD-CROSS-TIER-FRESHNESS-001). None if
            freshness infrastructure is not available.

    Example:
        >>> result = BuildResult(
        ...     status=BuildStatus.PARTIAL,
        ...     sections=[sec1_ok, sec2_fail, sec3_ok],
        ...     dataframe=merged_df,
        ...     watermark=datetime.now(UTC),
        ...     project_gid="123",
        ...     entity_type="offer",
        ...     total_time_ms=5400.0,
        ...     fetch_time_ms=4200.0,
        ... )
        >>> result.sections_succeeded
        2
        >>> result.sections_failed
        1
        >>> result.failed_section_gids
        ['sec2_gid']
    """

    status: BuildStatus
    sections: tuple[SectionResult, ...]
    dataframe: pl.DataFrame | None
    watermark: datetime
    project_gid: str
    entity_type: str
    total_time_ms: float
    fetch_time_ms: float
    sections_probed: int = 0
    sections_delta_updated: int = 0
    freshness_stamp: FreshnessStamp | None = None

    @property
    def sections_succeeded(self) -> int:
        """Count of sections with SUCCESS outcome."""
        return sum(1 for s in self.sections if s.outcome == SectionOutcome.SUCCESS)

    @property
    def sections_failed(self) -> int:
        """Count of sections with ERROR outcome."""
        return sum(1 for s in self.sections if s.outcome == SectionOutcome.ERROR)

    @property
    def sections_skipped(self) -> int:
        """Count of sections with SKIPPED outcome (includes resumed)."""
        return sum(1 for s in self.sections if s.outcome == SectionOutcome.SKIPPED)

    @property
    def sections_resumed(self) -> int:
        """Count of sections loaded from S3 manifest (not re-fetched)."""
        return sum(1 for s in self.sections if s.resumed)

    @property
    def total_rows(self) -> int:
        """Total rows across all successful sections."""
        return sum(s.row_count for s in self.sections if s.is_success)

    @property
    def failed_section_gids(self) -> list[str]:
        """GIDs of sections that failed."""
        return [s.section_gid for s in self.sections if s.is_error]

    @property
    def error_summary(self) -> dict[str, int]:
        """Count of failures by error_type.

        Useful for log aggregation and alerting. For example:
        {"AsanaAPIError": 2, "S3TransportError": 1}
        """
        counts: dict[str, int] = {}
        for s in self.sections:
            if s.is_error and s.error_type:
                counts[s.error_type] = counts.get(s.error_type, 0) + 1
        return counts

    @property
    def is_usable(self) -> bool:
        """True if a DataFrame was produced (SUCCESS or PARTIAL)."""
        return self.dataframe is not None and self.status != BuildStatus.FAILURE

    @classmethod
    def from_section_results(
        cls,
        section_results: list[SectionResult],
        dataframe: pl.DataFrame | None,
        watermark: datetime,
        project_gid: str,
        entity_type: str,
        total_time_ms: float,
        fetch_time_ms: float,
        *,
        sections_probed: int = 0,
        sections_delta_updated: int = 0,
        freshness_stamp: FreshnessStamp | None = None,
    ) -> BuildResult:
        """Construct BuildResult from a list of SectionResults.

        Automatically classifies BuildStatus based on section outcomes:
        - All SUCCESS/SKIPPED -> SUCCESS
        - Mix of SUCCESS and ERROR -> PARTIAL
        - All ERROR or no DataFrame -> FAILURE

        Args:
            section_results: Per-section outcomes.
            dataframe: Merged DataFrame (None if build failed entirely).
            watermark: Build timestamp.
            project_gid: Project GID.
            entity_type: Entity type.
            total_time_ms: Total build time.
            fetch_time_ms: Fetch time.
            sections_probed: Freshness probe count.
            sections_delta_updated: Delta-updated section count.
            freshness_stamp: Aggregate freshness stamp.

        Returns:
            BuildResult with classified status.
        """
        has_success = any(
            s.outcome == SectionOutcome.SUCCESS for s in section_results
        )
        has_error = any(
            s.outcome == SectionOutcome.ERROR for s in section_results
        )

        if dataframe is None or (not has_success and has_error):
            status = BuildStatus.FAILURE
        elif has_error:
            status = BuildStatus.PARTIAL
        else:
            status = BuildStatus.SUCCESS

        return cls(
            status=status,
            sections=tuple(section_results),
            dataframe=dataframe,
            watermark=watermark,
            project_gid=project_gid,
            entity_type=entity_type,
            total_time_ms=total_time_ms,
            fetch_time_ms=fetch_time_ms,
            sections_probed=sections_probed,
            sections_delta_updated=sections_delta_updated,
            freshness_stamp=freshness_stamp,
        )
```

### Status Classification Logic

The `from_section_results` factory classifies the build:

```
Section outcomes        DataFrame present?    Status
---------------------------------------------------------
All SUCCESS/SKIPPED     Yes                   SUCCESS
Mix SUCCESS + ERROR     Yes                   PARTIAL
All ERROR               No                    FAILURE
No sections             Yes (empty DF)        SUCCESS
Only SKIPPED (resume)   Yes (from S3)         SUCCESS
```

Corner case: A build where all sections are SKIPPED (fully resumed from manifest) is SUCCESS because the DataFrame was produced from S3 data. A build where all sections fail but some were resumed produces PARTIAL -- the resumed data is valid but incomplete if the failed sections have changed since the manifest was written.

### Design Rationale

**Why `frozen=True` for BuildResult?** BuildResult is created once at the end of a build and passed to consumers. Immutability prevents accidental mutation in the async pipeline between builder and cache. The DataFrame inside is a Polars DataFrame which is itself immutable.

**Why `tuple[SectionResult, ...]` instead of `list`?** Tuples are immutable, consistent with the frozen dataclass. Lists inside frozen dataclasses are a mutability escape hatch that should be avoided.

**Why `from_section_results` instead of separate constructors?** The status classification logic is non-trivial (see table above). Centralizing it in a factory method prevents callers from constructing inconsistent states (e.g., `status=SUCCESS` with failed sections). Direct construction is still available for tests.

**Why not include the section DataFrames in SectionResult?** Section DataFrames are large (potentially thousands of rows each). Including them in SectionResult would prevent garbage collection after merge. The builder holds section DataFrames in `self._section_dfs` during the build and releases them after merge. SectionResult carries only metadata.

---

## Integration: ProgressiveProjectBuilder

### Changes to `build_progressive_async`

The builder's main method changes from returning `ProgressiveBuildResult` to returning `BuildResult`. The key modification is in step 4 (fetch sections) where individual section results are captured instead of just a boolean.

```python
async def build_progressive_async(
    self,
    resume: bool = True,
) -> BuildResult:
    """Build DataFrame with progressive section writes to S3.

    Returns:
        BuildResult with classified status and per-section detail.
    """
    start_time = time.perf_counter()

    await self._ensure_dataframe_view()

    # Step 1: Get section list
    sections = await self._list_sections()
    section_gids = [s.gid for s in sections]

    if not sections:
        return BuildResult(
            status=BuildStatus.SUCCESS,
            sections=(),
            dataframe=pl.DataFrame(schema=self._schema.to_polars_schema()),
            watermark=datetime.now(UTC),
            project_gid=self._project_gid,
            entity_type=self._entity_type,
            total_time_ms=(time.perf_counter() - start_time) * 1000,
            fetch_time_ms=0.0,
        )

    # Step 2: Check resume and probe freshness
    resume_result = await self._check_resume_and_probe(section_gids, resume)

    # Step 3: Ensure manifest exists
    await self._ensure_manifest(resume_result.manifest, sections, section_gids)

    # Collect SectionResults for resumed sections
    section_results: list[SectionResult] = []
    for gid in section_gids:
        if gid not in resume_result.sections_to_fetch:
            section_results.append(SectionResult(
                section_gid=gid,
                outcome=SectionOutcome.SKIPPED,
                resumed=True,
            ))

    # Step 4: Fetch and persist incomplete sections
    fetch_time = 0.0
    if resume_result.sections_to_fetch:
        fetch_start = time.perf_counter()
        section_map = {s.gid: s for s in sections}
        fetch_tasks = [
            self._fetch_and_persist_section_with_result(
                section_gid,
                section_map.get(section_gid),
                idx,
                len(resume_result.sections_to_fetch),
            )
            for idx, section_gid in enumerate(resume_result.sections_to_fetch)
        ]

        fetch_results = await gather_with_limit(
            fetch_tasks,
            max_concurrent=self._max_concurrent,
        )
        section_results.extend(fetch_results)
        fetch_time = (time.perf_counter() - fetch_start) * 1000

    # Step 5: Merge sections
    merged_df = await self._merge_section_dataframes()
    total_time = (time.perf_counter() - start_time) * 1000

    # Step 6: Write final artifacts (only if we have data)
    if len(merged_df) > 0:
        index_data = self._build_index_data(merged_df)
        await self._persistence.write_final_artifacts_async(
            self._project_gid,
            merged_df,
            datetime.now(UTC),
            index_data=index_data,
            entity_type=self._entity_type,
        )

    # Release in-memory section DataFrames
    self._section_dfs.clear()

    return BuildResult.from_section_results(
        section_results=section_results,
        dataframe=merged_df,
        watermark=datetime.now(UTC),
        project_gid=self._project_gid,
        entity_type=self._entity_type,
        total_time_ms=total_time,
        fetch_time_ms=fetch_time,
        sections_probed=resume_result.sections_probed,
        sections_delta_updated=resume_result.sections_delta_updated,
    )
```

### Changes to `_fetch_and_persist_section`

A new wrapper method produces a `SectionResult` instead of returning a boolean:

```python
async def _fetch_and_persist_section_with_result(
    self,
    section_gid: str,
    section: Section | None,
    section_index: int,
    total_sections: int,
) -> SectionResult:
    """Fetch, build, and persist a section, returning a SectionResult.

    Delegates to the existing _fetch_and_persist_section logic but
    captures the outcome as a structured SectionResult instead of
    a boolean.

    Args:
        section_gid: Section GID to fetch.
        section: Section object (may be None).
        section_index: Index for progress logging.
        total_sections: Total sections being fetched.

    Returns:
        SectionResult with outcome, row count, timing, and error detail.
    """
    section_start = time.perf_counter()

    try:
        success = await self._fetch_and_persist_section(
            section_gid, section, section_index, total_sections
        )

        fetch_time_ms = (time.perf_counter() - section_start) * 1000

        if success:
            # Get row count from in-memory section DF
            row_count = 0
            section_df = self._section_dfs.get(section_gid)
            if section_df is not None:
                row_count = len(section_df)

            # Get watermark from manifest
            watermark = None
            if self._manifest is not None:
                info = self._manifest.sections.get(section_gid)
                if info is not None:
                    watermark = info.watermark

            return SectionResult(
                section_gid=section_gid,
                outcome=SectionOutcome.SUCCESS,
                row_count=row_count,
                fetch_time_ms=fetch_time_ms,
                watermark=watermark,
            )
        else:
            # _fetch_and_persist_section returned False
            # Error was logged and manifest updated inside the method
            error_msg = None
            if self._manifest is not None:
                info = self._manifest.sections.get(section_gid)
                if info is not None and info.error:
                    error_msg = info.error

            return SectionResult(
                section_gid=section_gid,
                outcome=SectionOutcome.ERROR,
                fetch_time_ms=fetch_time_ms,
                error_message=error_msg or "Section fetch returned False",
                error_type="UnknownError",
            )

    except Exception as e:
        fetch_time_ms = (time.perf_counter() - section_start) * 1000
        return SectionResult(
            section_gid=section_gid,
            outcome=SectionOutcome.ERROR,
            fetch_time_ms=fetch_time_ms,
            error_message=str(e),
            error_type=type(e).__name__,
        )
```

### Backward Compatibility: ProgressiveBuildResult

The existing `ProgressiveBuildResult` is not removed immediately. A `to_legacy()` method on BuildResult provides backward compatibility for callers that have not migrated:

```python
def to_legacy(self) -> ProgressiveBuildResult:
    """Convert to legacy ProgressiveBuildResult for backward compatibility.

    Returns:
        ProgressiveBuildResult with equivalent aggregate metrics.
    """
    return ProgressiveBuildResult(
        df=self.dataframe if self.dataframe is not None
           else pl.DataFrame(),
        watermark=self.watermark,
        total_rows=self.total_rows,
        sections_fetched=self.sections_succeeded,
        sections_resumed=self.sections_resumed,
        fetch_time_ms=self.fetch_time_ms,
        total_time_ms=self.total_time_ms,
        sections_probed=self.sections_probed,
        sections_delta_updated=self.sections_delta_updated,
    )
```

---

## Integration: DataFrameCache

### Build Quality Metadata on Cache Entries

When `DataFrameCache.put_async()` receives a BuildResult (directly or as metadata), the cache entry records the build quality. This allows `get_async()` consumers to know whether the cached DataFrame was produced from a clean or partial build.

The `CacheEntry` in `dataframe_cache.py` gains an optional `build_quality` field:

```python
@dataclass
class BuildQuality:
    """Metadata about the build that produced a cached DataFrame.

    Attached to DataFrameCache.CacheEntry to enable consumers to
    make informed serving decisions.

    Attributes:
        status: Build status (success, partial, failure).
        sections_total: Total sections in the project.
        sections_succeeded: Sections that produced data.
        sections_failed: Sections that failed.
        failed_section_gids: GIDs of failed sections.
        error_summary: Count of failures by error type.
    """

    status: str  # BuildStatus.value
    sections_total: int
    sections_succeeded: int
    sections_failed: int
    failed_section_gids: tuple[str, ...] = ()
    error_summary: dict[str, int] | None = None


@dataclass
class CacheEntry:
    """Single DataFrame cache entry with metadata."""

    project_gid: str
    entity_type: str
    dataframe: pl.DataFrame
    watermark: datetime
    created_at: datetime
    schema_version: str
    row_count: int = field(init=False)
    freshness_stamp: FreshnessStamp | None = None  # Per A2 TDD
    build_quality: BuildQuality | None = None       # NEW

    def __post_init__(self) -> None:
        self.row_count = len(self.dataframe)
```

### put_async with BuildResult

```python
async def put_async(
    self,
    project_gid: str,
    entity_type: str,
    dataframe: pl.DataFrame,
    watermark: datetime,
    section_stamps: list[FreshnessStamp] | None = None,
    build_result: BuildResult | None = None,  # NEW
) -> None:
    """Store DataFrame in both tiers.

    Args:
        project_gid: Asana project GID.
        entity_type: Entity type.
        dataframe: Polars DataFrame to cache.
        watermark: Freshness watermark.
        section_stamps: Per-section freshness stamps (per A2 TDD).
        build_result: Optional build result for quality metadata.
    """
    # ... existing schema version lookup ...

    build_quality = None
    if build_result is not None:
        build_quality = BuildQuality(
            status=build_result.status.value,
            sections_total=len(build_result.sections),
            sections_succeeded=build_result.sections_succeeded,
            sections_failed=build_result.sections_failed,
            failed_section_gids=tuple(build_result.failed_section_gids),
            error_summary=build_result.error_summary or None,
        )

    entry = CacheEntry(
        project_gid=project_gid,
        entity_type=entity_type,
        dataframe=dataframe,
        watermark=watermark,
        created_at=datetime.now(UTC),
        schema_version=schema_version,
        freshness_stamp=aggregate_stamp,
        build_quality=build_quality,
    )

    # ... rest unchanged ...
```

### Serving Partial Data

The `get_async` path does not change behavior. BuildQuality is informational metadata that flows through the `FreshnessInfo` side-channel:

```python
@dataclass
class FreshnessInfo:
    """Freshness metadata for a cache serve operation."""

    freshness: str
    data_age_seconds: float
    staleness_ratio: float
    build_status: str | None = None   # NEW: "success", "partial", "failure"
    sections_failed: int = 0          # NEW
```

The `_build_freshness_info` method populates these fields when build_quality is present on the entry.

---

## Integration: Callers and Consumers

### Startup Preload (`api/main.py`)

The startup preload loop currently ignores partial failures. With BuildResult, it can log a warning and continue:

```python
result = await builder.build_progressive_async()

if result.status == BuildStatus.PARTIAL:
    logger.warning(
        "preload_partial_build",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "sections_failed": result.sections_failed,
            "failed_sections": result.failed_section_gids,
            "error_summary": result.error_summary,
        },
    )
    # Still cache the partial DataFrame -- better than nothing
    await dataframe_cache.put_async(
        project_gid, entity_type, result.dataframe, result.watermark,
        build_result=result,
    )
elif result.status == BuildStatus.FAILURE:
    logger.error(
        "preload_build_failed",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "error_summary": result.error_summary,
        },
    )
    # Do not cache -- let API requests trigger a fresh build
elif result.status == BuildStatus.SUCCESS:
    await dataframe_cache.put_async(
        project_gid, entity_type, result.dataframe, result.watermark,
        build_result=result,
    )
```

### SWR Background Refresh

Same pattern: partial data is cached with quality metadata; total failure triggers circuit breaker.

### Query Service / Universal Strategy

When `DataFrameCache.get_async()` returns an entry with `build_quality.status == "partial"`, the FreshnessInfo side-channel carries `build_status="partial"` and `sections_failed=N`. The query response can include a warning header in a future iteration (NG3).

---

## Backward Compatibility

### Compatibility Matrix

| Component | Behavior Before | Behavior After | Breaking? |
|-----------|----------------|----------------|-----------|
| `build_progressive_async` return type | `ProgressiveBuildResult` | `BuildResult` | Yes (type change) |
| `ProgressiveBuildResult` | Used by all callers | Available via `BuildResult.to_legacy()` | No (bridge) |
| `_fetch_and_persist_section` | Returns `bool` | Returns `bool` (unchanged) | No |
| `_fetch_and_persist_section_with_result` | N/A (new) | Returns `SectionResult` | No (additive) |
| `DataFrameCache.put_async` signature | `(project_gid, entity_type, df, watermark)` | Adds optional `build_result` kwarg | No |
| `DataFrameCache.CacheEntry` | No build_quality | Optional `build_quality` field | No |
| `FreshnessInfo` | No build_status | Optional `build_status` and `sections_failed` | No |
| `build_project_progressive_async` function | Returns `ProgressiveBuildResult` | Returns `BuildResult` | Yes (type change) |

### Migration Path

**Phase 1: Introduce types (this sprint).** Add `SectionResult`, `BuildResult`, `BuildStatus`, `BuildQuality` to `dataframes/builders/build_result.py`. All new types. No existing code changes.

**Phase 2: Builder produces BuildResult (this sprint).** Modify `ProgressiveProjectBuilder.build_progressive_async()` to return `BuildResult`. Add `_fetch_and_persist_section_with_result` wrapper. The existing `_fetch_and_persist_section` method is unchanged. Update `build_project_progressive_async` convenience function.

**Phase 3: Callers migrate (this sprint).** Update callers one at a time:
- `api/main.py` preload -- use BuildResult directly
- SWR refresh callback -- use BuildResult
- `DataFrameCache.put_async` -- accept optional build_result

**Phase 4: Deprecate ProgressiveBuildResult (future).** Once all callers use BuildResult, deprecate ProgressiveBuildResult. The `to_legacy()` bridge enables gradual migration.

---

## Data Flow Diagrams

### Sequence: Full Build with Partial Failure

```
Builder            Section S1       Section S2       Section S3       DataFrameCache
  |                    |                |                |                   |
  | fetch S1           |                |                |                   |
  |------------------->|                |                |                   |
  |  SectionResult     |                |                |                   |
  |  (SUCCESS, 42 rows)|                |                |                   |
  |<-------------------|                |                |                   |
  |                    |                |                |                   |
  | fetch S2           |                |                |                   |
  |------------------------------------>|                |                   |
  |  SectionResult     |                |                |                   |
  |  (ERROR,           |                |                |                   |
  |   "AsanaAPIError", |                |                |                   |
  |   "429 Too Many")  |                |                |                   |
  |<------------------------------------|                |                   |
  |                    |                |                |                   |
  | fetch S3           |                |                |                   |
  |----------------------------------------------------->|                   |
  |  SectionResult     |                |                |                   |
  |  (SUCCESS, 28 rows)|                |                |                   |
  |<-----------------------------------------------------|                   |
  |                    |                |                |                   |
  | merge S1+S3 -> DataFrame (70 rows, S2 missing)      |                   |
  |                    |                |                |                   |
  | BuildResult(PARTIAL, [S1_ok, S2_err, S3_ok], df)     |                   |
  |                    |                |                |                   |
  | put_async(df, build_result=...)     |                |                   |
  |--------------------------------------------------------------------->    |
  |                    |                |                | CacheEntry with   |
  |                    |                |                | build_quality:    |
  |                    |                |                |   status="partial"|
  |                    |                |                |   failed=1        |
  |                    |                |                |   failed_gids=    |
  |                    |                |                |     ["S2"]        |
```

### Sequence: Full Build All Succeed (Happy Path)

```
Builder            Section S1       Section S2       DataFrameCache
  |                    |                |                   |
  | fetch S1, S2       |                |                   |
  |------------------->|                |                   |
  |------------------------------------>|                   |
  |  SUCCESS, 42       |  SUCCESS, 28   |                   |
  |<-------------------|                |                   |
  |<------------------------------------|                   |
  |                    |                |                   |
  | merge S1+S2 -> DataFrame (70 rows)  |                   |
  |                    |                |                   |
  | BuildResult(SUCCESS, [S1_ok, S2_ok], df)               |
  |                    |                |                   |
  | put_async(df, build_result=...)     |                   |
  |--------------------------------------------------------------------->   |
  |                    |                |  CacheEntry with  |
  |                    |                |  build_quality:   |
  |                    |                |    status="success"|
```

### Sequence: Consumer Reads Partial Data

```
Consumer         DataFrameCache         FreshnessInfo
  |                    |                      |
  | get_async()        |                      |
  |-------------------->                      |
  |  CacheEntry        |                      |
  |  (build_quality:   |                      |
  |   status="partial",|                      |
  |   sections_failed=1)|                     |
  |<--------------------|                     |
  |                    |                      |
  | get_freshness_info()|                     |
  |-------------------->                      |
  |  FreshnessInfo     |                      |
  |  (build_status=    |                      |
  |   "partial",       |                      |
  |   sections_failed=1)|                     |
  |<--------------------|                     |
  |                    |                      |
  | decision: serve with warning             |
```

---

## Non-Functional Considerations

### Performance

| Concern | Approach | Target |
|---------|----------|--------|
| SectionResult construction | Frozen dataclass with slots; one per section | < 1us per result |
| BuildResult construction | `from_section_results` iterates sections once | O(n) where n = section count (typically 5-40) |
| BuildResult.error_summary | Computed property, iterates sections | O(n), called infrequently (logging/alerting) |
| Memory overhead | SectionResult ~120 bytes per instance (slots) | < 5KB for 40 sections |
| Happy path overhead | One additional list + tuple conversion | Negligible (< 0.1ms) |

**Performance constraint from requirements**: BuildResult construction must be O(sections), not O(tasks). This is satisfied because SectionResult carries `row_count` (an integer) rather than the task list. The section DataFrame is never stored in the result.

### Memory Impact

BuildResult holds a reference to the merged DataFrame (same as ProgressiveBuildResult). The per-section SectionResults add approximately 120 bytes each (section_gid string + enum + int + float + optional strings, with slots). For a project with 40 sections, this is ~5KB -- negligible compared to the DataFrame payload (typically 1-50MB).

### Thread Safety

Both `SectionResult` and `BuildResult` are frozen dataclasses. They are immutable after construction and safe for concurrent access in async code. The `sections` field uses `tuple` (immutable) rather than `list`.

### Observability

New structured log events:

| Event | Level | Fields |
|-------|-------|--------|
| `build_result_classified` | INFO | project_gid, entity_type, status, sections_succeeded, sections_failed, total_rows |
| `build_partial_failure` | WARNING | project_gid, entity_type, failed_section_gids, error_summary |
| `build_total_failure` | ERROR | project_gid, entity_type, error_summary |
| `cache_put_with_quality` | DEBUG | project_gid, entity_type, build_status, sections_failed |

---

## Test Strategy

### Unit Tests: SectionResult

| Test | Validates |
|------|-----------|
| `test_section_result_success` | SUCCESS outcome with row count and timing |
| `test_section_result_error` | ERROR outcome with error_message and error_type |
| `test_section_result_skipped` | SKIPPED outcome with resumed=True |
| `test_section_result_is_success_property` | `is_success` returns True only for SUCCESS |
| `test_section_result_is_error_property` | `is_error` returns True only for ERROR |
| `test_section_result_frozen` | Cannot mutate fields after creation |
| `test_section_result_slots` | Instance has `__slots__` (memory efficient) |

### Unit Tests: BuildResult

| Test | Validates |
|------|-----------|
| `test_build_result_success_status` | All SUCCESS sections -> BuildStatus.SUCCESS |
| `test_build_result_partial_status` | Mix of SUCCESS and ERROR -> BuildStatus.PARTIAL |
| `test_build_result_failure_status` | All ERROR sections -> BuildStatus.FAILURE |
| `test_build_result_no_sections` | Empty sections list -> SUCCESS (empty DataFrame) |
| `test_build_result_only_skipped` | All SKIPPED (resumed) -> SUCCESS |
| `test_build_result_skipped_plus_error` | SKIPPED + ERROR without SUCCESS -> FAILURE |
| `test_build_result_none_dataframe` | None DataFrame -> FAILURE regardless of sections |
| `test_build_result_sections_succeeded` | `sections_succeeded` counts correctly |
| `test_build_result_sections_failed` | `sections_failed` counts correctly |
| `test_build_result_sections_resumed` | `sections_resumed` counts resumed flag |
| `test_build_result_total_rows` | `total_rows` sums only SUCCESS sections |
| `test_build_result_failed_section_gids` | Returns GIDs of ERROR sections |
| `test_build_result_error_summary` | Groups errors by type correctly |
| `test_build_result_is_usable` | True for SUCCESS and PARTIAL, False for FAILURE |
| `test_build_result_to_legacy` | Converts to ProgressiveBuildResult correctly |
| `test_build_result_from_section_results` | Factory classifies status correctly |
| `test_build_result_frozen` | Cannot mutate fields |

### Unit Tests: Builder Integration

| Test | Validates |
|------|-----------|
| `test_builder_all_sections_succeed` | BuildResult.status == SUCCESS |
| `test_builder_one_section_fails` | BuildResult.status == PARTIAL, failed_section_gids has 1 entry |
| `test_builder_all_sections_fail` | BuildResult.status == FAILURE, dataframe is empty |
| `test_builder_resumed_sections_skipped` | Resumed sections produce SKIPPED SectionResults |
| `test_builder_section_result_has_timing` | fetch_time_ms > 0 for fetched sections |
| `test_builder_section_result_has_row_count` | row_count matches section DataFrame length |
| `test_builder_section_result_has_error_type` | error_type captures exception class name |
| `test_builder_empty_project` | BuildResult.status == SUCCESS, empty tuple |

### Unit Tests: DataFrameCache Integration

| Test | Validates |
|------|-----------|
| `test_put_async_with_build_result` | CacheEntry has build_quality metadata |
| `test_put_async_without_build_result` | CacheEntry has build_quality=None (backward compat) |
| `test_freshness_info_includes_build_status` | FreshnessInfo carries build_status and sections_failed |
| `test_build_quality_partial` | build_quality.status == "partial" with correct counts |

### Integration Tests

| Test | Validates |
|------|-----------|
| `test_partial_build_cached_and_served` | Partial build -> cache put -> cache get -> FreshnessInfo shows partial |
| `test_partial_build_with_freshness_stamp` | Partial build freshness stamp excludes failed sections |
| `test_full_build_matches_legacy_behavior` | BuildResult with all SUCCESS produces same DataFrame as ProgressiveBuildResult |

### Test File Organization

```
tests/
  unit/
    dataframes/
      builders/
        test_build_result.py           # SectionResult + BuildResult unit tests
        test_progressive_build_result.py # Builder integration tests
    cache/
      test_dataframe_cache_quality.py  # DataFrameCache build quality tests
  integration/
    dataframes/
      test_partial_build_flow.py       # End-to-end partial build flow
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Return type change breaks callers** | High | Medium (compile-time error, not silent) | Phase migration: introduce BuildResult, update callers one at a time, provide `to_legacy()` bridge. All callers are internal (no public API). |
| **Partial data served as complete** | Low | High (incorrect query results) | BuildQuality metadata on CacheEntry ensures consumers can detect partial data. FreshnessInfo carries `build_status`. |
| **Performance regression from SectionResult construction** | Very Low | Low (< 0.1ms overhead) | Frozen dataclass with slots. Construction cost is O(1) per section. Validated via test assertions. |
| **Memory leak from BuildResult holding DataFrame reference** | Very Low | Medium (DataFrame not GC'd) | Same pattern as ProgressiveBuildResult (holds `df`). Builder clears `_section_dfs` after merge. BuildResult is short-lived: created at build end, consumed by cache put, then dropped. |
| **Classification logic edge case** | Low | Medium (wrong BuildStatus) | Comprehensive test matrix covering all outcome combinations (see test strategy). Factory method centralizes logic. |
| **Inconsistency between manifest FAILED status and SectionResult** | Low | Low (cosmetic) | SectionResult is derived from the same exception that updates the manifest. Both record the error. |

---

## ADRs

### ADR-C2-001: Three-State BuildStatus (Not Two or Five)

**Status**: Proposed

**Context**: How many states should BuildStatus have? Two (success/failure) or more?

**Decision**: Three states: SUCCESS, PARTIAL, FAILURE.

**Alternatives Considered**:
1. **Two states (SUCCESS/FAILURE)**: Simpler but collapses two distinct scenarios. A build that produced 90% of the data is fundamentally different from a build that produced 0%. Consumers need to distinguish these to make serving decisions.
2. **Five states (matching FreshnessStatus)**: Overspecified. The build outcome space is smaller than the freshness space. Adding DEGRADED, TIMEOUT, etc. would require consumers to handle states they cannot act on differently.
3. **Numeric completeness score (0.0-1.0)**: Tempting but misleading. A build missing 1 of 10 sections is not "90% complete" if the missing section contains 80% of the tasks. Row-count-based completeness would be more accurate but requires the caller to know the expected total, which is not available.

**Rationale**: Three states map to three consumer actions: serve normally (SUCCESS), serve with warning (PARTIAL), reject/retry (FAILURE). This matches the pattern established by FreshnessClassification in TDD-CROSS-TIER-FRESHNESS-001 (FRESH, APPROACHING_STALE, STALE).

**Consequences**: Consumers implement a three-way switch. If finer granularity is needed, the per-section SectionResults provide full detail.

### ADR-C2-002: SectionResult per Section (Not Just Failed Sections)

**Status**: Proposed

**Context**: Should BuildResult carry results for all sections or only the failed ones?

**Decision**: All sections. Every section gets a SectionResult.

**Alternatives Considered**:
1. **Only failed sections**: Smaller payload. But consumers lose visibility into successful sections -- they cannot verify completeness (e.g., "I expected 10 sections, I see 7 successes and 3 failures" vs. "I see 3 failures but have no idea how many succeeded").
2. **Summary counts only**: Even smaller. But consumers cannot inspect individual section errors for retry decisions (e.g., "retry the section that got a 429, skip the one that got a 403").

**Rationale**: Section counts are small (typically 5-40). The per-instance overhead is ~120 bytes. The information value of knowing which sections succeeded vs. failed vs. were resumed is high for observability and debugging. The cost is negligible.

**Consequences**: BuildResult.sections is always the same length as the project's section count. Consumers can iterate over sections to build detailed reports.

### ADR-C2-003: Wrapper Method Instead of Rewriting _fetch_and_persist_section

**Status**: Proposed

**Context**: Should we modify `_fetch_and_persist_section` to return `SectionResult` directly, or wrap it?

**Decision**: Add `_fetch_and_persist_section_with_result` as a wrapper around the existing `_fetch_and_persist_section`.

**Alternatives Considered**:
1. **Modify `_fetch_and_persist_section` return type**: Changes the internal contract. The method is called from `build_progressive_async` via `gather_with_limit`. Changing its return type from `bool` to `SectionResult` would require updating all callers simultaneously and changes the error handling flow.
2. **Replace `_fetch_and_persist_section` entirely**: Larger diff, higher risk. The method has 5 phases with careful error handling. Rewriting it to produce SectionResult directly risks introducing bugs in the error paths.

**Rationale**: The wrapper pattern is lower risk and lower diff size. The existing method is well-tested and handles edge cases (checkpoints, large sections, store population). The wrapper captures the outcome and timing without modifying the internal logic. If the wrapper proves correct, the underlying method can be refactored to produce SectionResult directly in a future PR.

**Consequences**: Slight indirection (one extra method call per section). The wrapper's try/except catches any exception that escapes `_fetch_and_persist_section` (which should not happen given its internal try/except, but defense in depth).

### ADR-C2-004: BuildQuality as Optional Field on CacheEntry

**Status**: Proposed

**Context**: How should DataFrameCache record build quality?

**Decision**: Optional `build_quality: BuildQuality | None` field on the existing `CacheEntry` dataclass.

**Alternatives Considered**:
1. **Separate metadata store**: Store build quality alongside the entry in a separate dict. More complex, two data structures to keep in sync.
2. **Encode in existing metadata dict**: Less structured, harder to type-check, prone to key name collisions.
3. **Always-present with defaults**: Every CacheEntry would claim "success" even if build quality was not tracked. Semantically dishonest for legacy entries.

**Rationale**: Same pattern used by `freshness_stamp` in TDD-CROSS-TIER-FRESHNESS-001. Optional with None default means legacy entries are unaffected. The type system enforces structure. BuildQuality is a small frozen dataclass (~100 bytes) that travels with the entry through tiers.

**Consequences**: Consumers must check for None before accessing build_quality fields. CacheEntry serialization must handle the optional nested dataclass (same pattern as freshness_stamp serialization).

---

## Success Criteria

### Quantitative

| Metric | Baseline | Target | How Measured |
|--------|----------|--------|-------------|
| Section failure visibility | 0% (failures logged but not structured) | 100% of section failures captured in BuildResult | Count SectionResults with ERROR outcome vs. `section_fetch_failed` log events |
| Build status classification accuracy | N/A | 100% correct classification per test matrix | Unit tests covering all outcome combinations |
| Happy path performance overhead | 0ms | < 1ms additional per build | Benchmark SectionResult/BuildResult construction |
| Backward compatibility test failures | 0 | 0 | Full test suite passes (existing tests + to_legacy() bridge) |
| Build quality metadata coverage | 0% (no quality on cache entries) | 100% of new builds carry BuildQuality | Count CacheEntries with `build_quality is not None` |

### Qualitative

| Criterion | Validation |
|-----------|-----------|
| Consumer can determine data completeness | `BuildResult.sections_failed > 0` signals incomplete data |
| Operator can diagnose partial failures | `BuildResult.error_summary` groups errors by type; `failed_section_gids` identifies affected sections |
| Partial data is served with appropriate signal | FreshnessInfo.build_status == "partial" flows to API layer |
| Happy path behavior is unchanged | BuildResult.status == SUCCESS produces identical DataFrame to ProgressiveBuildResult |
| Design is observable | All status transitions emit structured log events |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-partial-failure-signaling.md` | Yes (written by architect) |
| Spike S0-006 (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-006-concurrent-build-analysis.md` | Read |
| Architectural opportunities (input) | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/architectural-opportunities.md` | Read |
| ProgressiveProjectBuilder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Read |
| SectionPersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Read |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| SectionFreshnessProber | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/freshness.py` | Read |
| Exception hierarchy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py` | Read |
| ParallelSectionFetcher | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py` | Read |
| DataFramePersistence | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/persistence.py` | Read |
| A2 Cross-Tier Freshness TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cross-tier-freshness.md` | Read |
| Sprint 1 TDD (structure ref) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-invalidation-pipeline.md` | Read |
| Cache integration | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py` | Read |
