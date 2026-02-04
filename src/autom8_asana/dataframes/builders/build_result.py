"""Partial failure signaling for DataFrame builds.

Per TDD-PARTIAL-FAILURE-SIGNALING-001 (C2):
Provides structured per-section outcomes and aggregate build status
classification, making section-level failures visible and actionable
instead of being silently swallowed.

Components:
- SectionOutcome: Three-state enum for individual section results.
- SectionResult: Frozen dataclass capturing per-section outcome, timing,
  row count, and error detail.
- BuildStatus: Three-state enum for aggregate build classification.
- BuildResult: Frozen dataclass aggregating all section results with
  status classification and backward-compatible bridge to
  ProgressiveBuildResult.
- BuildQuality: Metadata about build quality for cache entries.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl


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


class BuildStatus(str, Enum):
    """Overall outcome of a DataFrame build.

    Per ADR-C2-001: Three states mapping to three consumer actions:
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

    Per TDD-PARTIAL-FAILURE-SIGNALING-001: Captures the full picture of
    a build -- overall status, per-section results, the produced DataFrame
    (if any), timing, and freshness.

    Replaces ProgressiveBuildResult with strictly more information.
    The happy path (all sections succeed) produces BuildStatus.SUCCESS
    with the same DataFrame as before.

    Construction: Use the ``from_section_results`` factory for automatic
    status classification, or construct directly for tests.

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

    def to_legacy(self) -> Any:
        """Convert to legacy ProgressiveBuildResult for backward compatibility.

        Returns:
            ProgressiveBuildResult with equivalent aggregate metrics.
        """
        import polars as pl

        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveBuildResult,
        )

        return ProgressiveBuildResult(
            df=self.dataframe if self.dataframe is not None else pl.DataFrame(),
            watermark=self.watermark,
            total_rows=self.total_rows,
            sections_fetched=self.sections_succeeded,
            sections_resumed=self.sections_resumed,
            fetch_time_ms=self.fetch_time_ms,
            total_time_ms=self.total_time_ms,
            sections_probed=self.sections_probed,
            sections_delta_updated=self.sections_delta_updated,
        )

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
        )


@dataclass(frozen=True, slots=True)
class BuildQuality:
    """Metadata about the build that produced a cached DataFrame.

    Per ADR-C2-004: Attached to DataFrameCache.CacheEntry to enable
    consumers to make informed serving decisions.

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

    @classmethod
    def from_build_result(cls, result: BuildResult) -> BuildQuality:
        """Create BuildQuality from a BuildResult.

        Args:
            result: The build result to extract quality metadata from.

        Returns:
            BuildQuality with summarized metrics.
        """
        return cls(
            status=result.status.value,
            sections_total=len(result.sections),
            sections_succeeded=result.sections_succeeded,
            sections_failed=result.sections_failed,
            failed_section_gids=tuple(result.failed_section_gids),
            error_summary=result.error_summary or None,
        )
