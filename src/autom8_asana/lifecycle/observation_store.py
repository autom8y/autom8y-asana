"""Parquet-backed store for stage transition records.

Per ADR-omniscience-lifecycle-observation Decision 1:
- Follows the TimelineStore pattern from query/timeline_provider.py
- Entity-type-partitioned files at ~/.autom8/stage_transitions/{entity_type}.parquet
- Denormalized schema: one row per transition record
- Computed duration_days column materialized at load time
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.lifecycle.observation import StageTransitionRecord

logger = get_logger(__name__)

# Parquet schema for stage transition records
_PARQUET_SCHEMA = {
    "entity_gid": pl.Utf8,
    "entity_type": pl.Utf8,
    "business_gid": pl.Utf8,
    "from_stage": pl.Utf8,
    "to_stage": pl.Utf8,
    "pipeline_stage_num": pl.Int64,
    "transition_type": pl.Utf8,
    "entered_at": pl.Datetime("us", "UTC"),
    "exited_at": pl.Datetime("us", "UTC"),
    "automation_result_id": pl.Utf8,
    "duration_ms": pl.Float64,
}

# Default storage directory
_DEFAULT_BASE_DIR = Path.home() / ".autom8" / "stage_transitions"


class StageTransitionStore:
    """Parquet-backed persistence for stage transition records.

    Follows the TimelineStore pattern: one parquet file per entity type,
    denormalized rows, append-only. Thread-safe for single-writer use
    (the StageTransitionEmitter serializes via asyncio.to_thread).

    Attributes:
        base_dir: Directory for parquet files. Defaults to ~/.autom8/stage_transitions/.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or _DEFAULT_BASE_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _parquet_path(self, entity_type: str) -> Path:
        """Return the parquet file path for an entity type."""
        return self._base_dir / f"{entity_type.lower()}.parquet"

    def append(self, record: StageTransitionRecord) -> None:
        """Append a single transition record to the entity-type partition.

        If the parquet file exists, reads existing data, concatenates the
        new record, and writes back. Otherwise creates a new file.

        Args:
            record: The transition record to persist.
        """
        path = self._parquet_path(record.entity_type)
        new_row = self._record_to_dataframe(record)

        if path.exists():
            existing = pl.read_parquet(path)
            combined = pl.concat([existing, new_row], how="diagonal_relaxed")
        else:
            combined = new_row

        combined.write_parquet(path)
        logger.debug(
            "stage_transition_stored",
            entity_type=record.entity_type,
            path=str(path),
            total_rows=len(combined),
        )

    def load(self, entity_type: str) -> pl.DataFrame:
        """Load all transition records for an entity type.

        Materializes the computed duration_days column at load time:
        duration_days = (exited_at - entered_at) in days as Float64.

        Args:
            entity_type: Entity type name (e.g., "Process").

        Returns:
            DataFrame with all transition records plus computed duration_days.
            Empty DataFrame with correct schema if no file exists.
        """
        path = self._parquet_path(entity_type)
        if not path.exists():
            return self._empty_dataframe()

        df = pl.read_parquet(path)

        # Materialize computed duration_days column
        df = df.with_columns(
            ((pl.col("exited_at") - pl.col("entered_at")).dt.total_days().cast(pl.Float64)).alias(
                "duration_days"
            )
        )

        return df

    def _record_to_dataframe(self, record: StageTransitionRecord) -> pl.DataFrame:
        """Convert a single record to a 1-row DataFrame with correct schema."""
        row = asdict(record)
        return pl.DataFrame([row], schema=_PARQUET_SCHEMA)  # type: ignore[arg-type]

    def _empty_dataframe(self) -> pl.DataFrame:
        """Return an empty DataFrame with the correct schema plus duration_days."""
        schema = {**_PARQUET_SCHEMA, "duration_days": pl.Float64}
        return pl.DataFrame(schema=schema)  # type: ignore[arg-type]
