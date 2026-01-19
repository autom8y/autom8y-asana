"""Incremental filter for watermark-based task filtering.

Per TDD-DATAFRAME-BUILDER-WATERMARK-001 Phase 2: Provides IncrementalFilter
for determining which tasks need processing vs skip based on cached watermarks.

The filter compares fetched task modified_at timestamps against cached watermarks
to categorize tasks as:
- PROCESS: New tasks or tasks modified since cached
- SKIP: Unchanged tasks (use cached row)
- DELETE: Tasks removed from project/section

This enables incremental resume with parallel fetch, avoiding redundant
extraction of unchanged tasks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.dataframes.builders.fields import WATERMARK_COLUMN_NAME

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)


@dataclass
class TaskFilterResult:
    """Result of filtering tasks against watermark index.

    Per TDD Section 5.3: Categorizes tasks for incremental processing.

    Attributes:
        to_process: Tasks needing extraction (new or changed).
        to_skip: GIDs of unchanged tasks (use cached row).
        to_delete: GIDs no longer present in fetch (removed from project).
    """

    to_process: list[dict[str, Any]]
    to_skip: list[str]
    to_delete: list[str]

    @property
    def process_count(self) -> int:
        """Number of tasks requiring extraction."""
        return len(self.to_process)

    @property
    def skip_count(self) -> int:
        """Number of unchanged tasks being skipped."""
        return len(self.to_skip)

    @property
    def delete_count(self) -> int:
        """Number of tasks to be removed from cache."""
        return len(self.to_delete)


class IncrementalFilter:
    """Filters fetched tasks against cached watermarks.

    Per TDD Section 5.3 and 7.2: Implements the filter decision matrix:

    | Condition                           | Action  |
    |-------------------------------------|---------|
    | GID not in cache                    | PROCESS |
    | GID in cache, modified_at > cached  | PROCESS |
    | GID in cache, modified_at <= cached | SKIP    |
    | GID in cache, modified_at is None   | PROCESS |
    | GID in cache, not in fetched        | DELETE  |

    The filter is read-only and thread-safe, suitable for concurrent
    access during parallel section fetch.

    Example:
        >>> filter = IncrementalFilter.from_dataframe(existing_df)
        >>> result = filter.filter(fetched_tasks)
        >>> print(f"Process: {result.process_count}, Skip: {result.skip_count}")
    """

    def __init__(self, watermark_index: dict[str, datetime]) -> None:
        """Initialize with watermark index from existing DataFrame.

        Args:
            watermark_index: Mapping of task GID to cached modified_at datetime.
                All datetimes should be timezone-aware (UTC).
        """
        self._index = watermark_index

    @classmethod
    def from_dataframe(cls, df: pl.DataFrame) -> IncrementalFilter:
        """Build filter from existing DataFrame.

        Extracts gid and _modified_at columns to build watermark index.
        Per TDD Section 5.3: Handles empty DataFrames and missing columns.

        Args:
            df: Existing cached DataFrame with gid and _modified_at columns.

        Returns:
            IncrementalFilter with watermark index from DataFrame.
        """
        if df is None or df.is_empty() or WATERMARK_COLUMN_NAME not in df.columns:
            reason = (
                "none_df"
                if df is None
                else ("empty_df" if df.is_empty() else "missing_watermark_column")
            )
            logger.debug(
                "incremental_filter_empty_index",
                extra={
                    "reason": reason,
                    "columns": df.columns
                    if df is not None and not df.is_empty()
                    else [],
                },
            )
            return cls({})

        index: dict[str, datetime] = {}
        for row in df.select(["gid", WATERMARK_COLUMN_NAME]).iter_rows():
            gid, modified_at = row
            if gid and modified_at:
                index[gid] = modified_at

        logger.debug(
            "incremental_filter_index_built",
            extra={"task_count": len(index)},
        )
        return cls(index)

    @property
    def cached_gids(self) -> set[str]:
        """Set of task GIDs in the watermark index."""
        return set(self._index.keys())

    @property
    def cache_size(self) -> int:
        """Number of tasks in the watermark index."""
        return len(self._index)

    def filter(
        self,
        fetched_tasks: list[dict[str, Any]],
    ) -> TaskFilterResult:
        """Filter tasks based on watermark comparison.

        Per TDD Section 5.3 and 7.2: Applies the filter decision matrix
        to categorize each fetched task.

        Args:
            fetched_tasks: Tasks fetched from API, each with at least
                'gid' and optionally 'modified_at' fields.

        Returns:
            TaskFilterResult with categorized tasks.
        """
        to_process: list[dict[str, Any]] = []
        to_skip: list[str] = []
        fetched_gids: set[str] = set()

        for task in fetched_tasks:
            gid = task.get("gid")
            if not gid:
                logger.warning(
                    "incremental_filter_missing_gid",
                    extra={"task_keys": list(task.keys())},
                )
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
        # Per ADR-003: Task is deleted if GID in cache but not in fresh fetch
        cached_gids = set(self._index.keys())
        to_delete = list(cached_gids - fetched_gids)

        logger.info(
            "incremental_filter_completed",
            extra={
                "fetched_count": len(fetched_tasks),
                "process_count": len(to_process),
                "skip_count": len(to_skip),
                "delete_count": len(to_delete),
                "skip_rate": len(to_skip) / len(fetched_tasks)
                if fetched_tasks
                else 0.0,
            },
        )

        return TaskFilterResult(
            to_process=to_process,
            to_skip=to_skip,
            to_delete=to_delete,
        )

    def _parse_modified_at(self, value: str | datetime | None) -> datetime | None:
        """Parse modified_at value to timezone-aware datetime.

        Handles multiple input formats:
        - ISO 8601 string with Z suffix: "2024-01-15T12:00:00Z"
        - ISO 8601 string with offset: "2024-01-15T12:00:00+00:00"
        - Already a datetime object

        Args:
            value: Raw modified_at value from API or cache.

        Returns:
            Timezone-aware datetime in UTC, or None if unparseable.
        """
        if value is None:
            return None

        # Already a datetime
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value

        # Parse string
        if not isinstance(value, str):
            logger.warning(
                "incremental_filter_unexpected_modified_at_type",
                extra={"type": type(value).__name__},
            )
            return None

        # Handle Z suffix (ISO 8601 UTC shorthand)
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError as e:
            logger.warning(
                "incremental_filter_parse_error",
                extra={"value": value, "error": str(e)},
            )
            return None

    def get_watermark(self, gid: str) -> datetime | None:
        """Get cached watermark for a specific task GID.

        Args:
            gid: Task GID to look up.

        Returns:
            Cached modified_at datetime, or None if not in cache.
        """
        return self._index.get(gid)

    def is_cached(self, gid: str) -> bool:
        """Check if a task GID is in the watermark index.

        Args:
            gid: Task GID to check.

        Returns:
            True if task is in cache, False otherwise.
        """
        return gid in self._index
