"""Cross-entity join models and execution for /rows enrichment.

Implements lookup-based column enrichment: given primary entity rows,
load a related entity DataFrame and append selected columns via
a shared column join.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autom8_asana.query.errors import JoinError


class JoinSpec(BaseModel):
    """Specification for a cross-entity join on /rows.

    Supports two sources:
    - "entity" (default): Join with another Asana entity DataFrame.
    - "data-service": Join with data from autom8y-data analytics API.

    Example (entity join):
        {"entity_type": "business", "select": ["booking_type"], "on": "office_phone"}

    Example (data-service join):
        {
            "source": "data-service",
            "entity_type": "spend",
            "factory": "spend",
            "period": "T30",
            "select": ["spend", "cps", "leads"]
        }
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str
    select: list[str] = Field(min_length=1, max_length=10)
    on: str | None = None  # Explicit join key; defaults to relationship default

    # Cross-service extension (Phase 1)
    source: Literal["entity", "data-service"] = "entity"
    factory: str | None = None  # DataServiceClient factory name
    period: str = "LIFETIME"  # T7, T30, LIFETIME, etc.

    @model_validator(mode="after")
    def validate_source_params(self) -> JoinSpec:
        """Ensure factory is provided for data-service joins and absent for entity joins."""
        if self.source == "data-service" and self.factory is None:
            raise ValueError("factory is required when source='data-service'")
        if self.source == "entity" and self.factory is not None:
            raise ValueError("factory is only valid when source='data-service'")
        return self

    @field_validator("select")
    @classmethod
    def validate_select_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("select must contain at least one column")
        return v


# Guard: maximum join depth (hops through relationships)
MAX_JOIN_DEPTH: int = 1


@dataclass
class JoinResult:
    """Result of a join operation.

    Attributes:
        df: The enriched DataFrame with join columns appended.
        join_key: The column used for joining.
        matched_count: Number of primary rows that found a match.
        unmatched_count: Number of primary rows with no match (null join cols).
    """

    df: pl.DataFrame
    join_key: str
    matched_count: int
    unmatched_count: int


def execute_join(
    primary_df: pl.DataFrame,
    target_df: pl.DataFrame,
    join_key: str,
    select_columns: list[str],
    target_entity_type: str,
) -> JoinResult:
    """Execute a left join to enrich primary rows with target columns.

    The join works as follows:
    1. Validate that join_key exists in both DataFrames.
    2. Select only join_key + requested columns from target DataFrame.
    3. Deduplicate target on join_key (take first occurrence).
    4. Left join primary onto deduplicated target.
    5. Return enriched DataFrame with matched/unmatched counts.

    Args:
        primary_df: The filtered primary entity DataFrame.
        target_df: The full target entity DataFrame.
        join_key: Column name present in both DataFrames.
        select_columns: Columns to select from target (will be prefixed).
        target_entity_type: For column name prefixing.

    Returns:
        JoinResult with enriched DataFrame.

    Raises:
        JoinError: If join_key missing from either DataFrame.
    """
    # 1. Validate join key exists in both DataFrames
    if join_key not in primary_df.columns:
        raise JoinError(
            f"Join key '{join_key}' not found in primary entity DataFrame. "
            f"Available: {sorted(primary_df.columns)}"
        )
    if join_key not in target_df.columns:
        raise JoinError(
            f"Join key '{join_key}' not found in target entity '{target_entity_type}' "
            f"DataFrame. Available: {sorted(target_df.columns)}"
        )

    # 2. Select join key + requested columns from target
    target_cols = [join_key] + [c for c in select_columns if c != join_key]
    available_target = set(target_df.columns)
    missing = [c for c in select_columns if c not in available_target]
    if missing:
        raise JoinError(
            f"Columns {missing} not found in target entity '{target_entity_type}'. "
            f"Available: {sorted(available_target)}"
        )

    target_subset = target_df.select(target_cols)

    # 3. Deduplicate target on join key (take first match)
    # Multiple target rows may share the same join key value.
    # We take the first occurrence to avoid row multiplication.
    target_deduped = target_subset.unique(subset=[join_key], keep="first")

    # 4. Filter out null join keys (they can never match)
    target_deduped = target_deduped.filter(pl.col(join_key).is_not_null())

    # 5. Rename target columns to avoid collision (prefix with entity type)
    rename_map = {
        col: f"{target_entity_type}_{col}" for col in select_columns if col != join_key
    }
    target_renamed = target_deduped.rename(rename_map)
    renamed_cols = list(rename_map.values())

    # 6. Left join
    enriched = primary_df.join(
        target_renamed,
        on=join_key,
        how="left",
    )

    # 7. Compute match statistics
    if renamed_cols:
        first_join_col = renamed_cols[0]
        matched_count = enriched.filter(pl.col(first_join_col).is_not_null()).height
    else:
        matched_count = enriched.height

    unmatched_count = enriched.height - matched_count

    return JoinResult(
        df=enriched,
        join_key=join_key,
        matched_count=matched_count,
        unmatched_count=unmatched_count,
    )
