"""Local parquet cache for computed SectionTimeline data.

TimelineStore manages serialization and deserialization of SectionTimeline
objects to/from denormalized parquet files. This enables offline temporal
queries without requiring live Asana API access for story fetching.

Parquet schema (denormalized):
    offer_gid       str
    office_phone    str (nullable)
    offer_id        str (nullable)
    section_name    str
    classification  str (nullable)
    entered_at      datetime[us, UTC]
    exited_at       datetime[us, UTC] (nullable)
    task_created_at datetime[us, UTC] (nullable)
    story_count     int
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from autom8_asana.models.business.section_timeline import SectionTimeline

_DEFAULT_CACHE_DIR = Path.home() / ".autom8" / "timelines"


@dataclass
class TimelineStore:
    """Manages local parquet cache for computed SectionTimeline data.

    Each project's timelines are stored in a single parquet file keyed
    by project GID. Intervals are flattened into a denormalized table
    for efficient storage and loading.

    Attributes:
        cache_dir: Directory for parquet files. Defaults to ~/.autom8/timelines/.
    """

    cache_dir: Path = field(default_factory=lambda: _DEFAULT_CACHE_DIR)

    def _parquet_path(self, project_gid: str) -> Path:
        """Resolve the parquet file path for a project."""
        return self.cache_dir / f"{project_gid}.parquet"

    def save(self, project_gid: str, timelines: list[SectionTimeline]) -> Path:
        """Serialize timelines to a denormalized parquet file.

        Each SectionInterval becomes one row, with parent timeline fields
        repeated for denormalization.

        Args:
            project_gid: Asana project GID (used as filename).
            timelines: List of SectionTimeline objects to persist.

        Returns:
            Path to the written parquet file.
        """
        rows: list[dict[str, object]] = []
        for tl in timelines:
            for interval in tl.intervals:
                rows.append(
                    {
                        "offer_gid": tl.offer_gid,
                        "office_phone": tl.office_phone,
                        "offer_id": tl.offer_id,
                        "section_name": interval.section_name,
                        "classification": (
                            interval.classification.value
                            if interval.classification is not None
                            else None
                        ),
                        "entered_at": interval.entered_at,
                        "exited_at": interval.exited_at,
                        "task_created_at": tl.task_created_at,
                        "story_count": tl.story_count,
                    }
                )

        # Handle empty timelines: write an empty DataFrame with correct schema
        if not rows:
            df = pl.DataFrame(
                schema={
                    "offer_gid": pl.Utf8,
                    "office_phone": pl.Utf8,
                    "offer_id": pl.Utf8,
                    "section_name": pl.Utf8,
                    "classification": pl.Utf8,
                    "entered_at": pl.Datetime("us", "UTC"),
                    "exited_at": pl.Datetime("us", "UTC"),
                    "task_created_at": pl.Datetime("us", "UTC"),
                    "story_count": pl.Int64,
                }
            )
        else:
            df = pl.DataFrame(rows)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._parquet_path(project_gid)
        df.write_parquet(path)
        return path

    def load(self, project_gid: str) -> list[SectionTimeline] | None:
        """Load cached timelines from parquet, reconstructing domain objects.

        Returns None if no cache file exists for the project.

        Args:
            project_gid: Asana project GID.

        Returns:
            List of SectionTimeline objects, or None if not cached.
        """
        path = self._parquet_path(project_gid)
        if not path.exists():
            return None

        df = pl.read_parquet(path)
        return _reconstruct_timelines(df)

    def age(self, project_gid: str) -> timedelta | None:
        """Return age of cached timeline data, or None if not cached.

        Age is measured from the parquet file's modification time.

        Args:
            project_gid: Asana project GID.

        Returns:
            timedelta since the cache was last written, or None.
        """
        path = self._parquet_path(project_gid)
        if not path.exists():
            return None
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        now = datetime.now(tz=UTC)
        return now - mtime


def _reconstruct_timelines(df: pl.DataFrame) -> list[SectionTimeline]:
    """Reconstruct SectionTimeline objects from a denormalized parquet DataFrame.

    Groups rows by offer_gid and rebuilds interval tuples in chronological
    order (by entered_at).
    """
    from autom8_asana.models.business.activity import AccountActivity
    from autom8_asana.models.business.section_timeline import (
        SectionInterval,
        SectionTimeline,
    )

    if df.is_empty():
        return []

    timelines: list[SectionTimeline] = []

    for offer_gid, group in df.group_by("offer_gid"):
        # group_by returns tuple keys in polars
        gid_str = offer_gid[0] if isinstance(offer_gid, tuple) else offer_gid
        group_sorted = group.sort("entered_at")

        # Extract timeline-level fields from first row
        first = group_sorted.row(0, named=True)
        office_phone = first["office_phone"]
        offer_id = first["offer_id"]
        task_created_at = first["task_created_at"]
        story_count = first["story_count"]

        # Build intervals
        intervals: list[SectionInterval] = []
        for row in group_sorted.iter_rows(named=True):
            classification_str = row["classification"]
            classification = (
                AccountActivity(classification_str) if classification_str is not None else None
            )
            intervals.append(
                SectionInterval(
                    section_name=row["section_name"],
                    classification=classification,
                    entered_at=row["entered_at"],
                    exited_at=row["exited_at"],
                )
            )

        timelines.append(
            SectionTimeline(
                offer_gid=str(gid_str),
                office_phone=office_phone,
                offer_id=offer_id,
                intervals=tuple(intervals),
                task_created_at=task_created_at,
                story_count=story_count,
            )
        )

    return timelines
