"""Post-build cascade validation for progressive builder.

Per TDD-CASCADE-FAILURE-FIXES-001 Fix 3: Validates cascade-critical fields
after section merge and re-resolves from live store when stale values detected.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.providers.unified import UnifiedTaskStore
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin

logger = get_logger(__name__)


@dataclass
class CascadeValidationResult:
    """Result of cascade validation pass."""

    rows_checked: int = 0
    rows_stale: int = 0
    rows_corrected: int = 0
    sections_affected: set[str] = field(default_factory=set)
    duration_ms: float = 0.0


async def validate_cascade_fields_async(
    merged_df: pl.DataFrame,
    store: UnifiedTaskStore,
    cascade_plugin: CascadeViewPlugin,
    project_gid: str,
    entity_type: str,
    *,
    schema: DataFrameSchema | None = None,
) -> tuple[pl.DataFrame, CascadeValidationResult]:
    """Validate and correct cascade-critical fields in merged DataFrame.

    For each row where a cascade-critical field is None, checks whether
    the hierarchy index has an ancestor that should provide the value.
    If the live store can resolve the value, updates the row.

    Args:
        merged_df: Merged DataFrame from all sections.
        store: UnifiedTaskStore for parent chain lookups.
        cascade_plugin: CascadeViewPlugin for field resolution.
        project_gid: Project GID for logging.
        entity_type: Entity type for logging.
        schema: Optional DataFrameSchema. When provided, cascade columns
            are derived dynamically via ``schema.get_cascade_columns()``.
            When None, no fields are validated (safe degradation).

    Returns:
        Tuple of (corrected DataFrame, validation result).
        DataFrame is the same object if no corrections needed.
    """
    start = time.perf_counter()
    result = CascadeValidationResult()

    if "gid" not in merged_df.columns:
        result.duration_ms = (time.perf_counter() - start) * 1000
        return merged_df, result

    hierarchy = store.get_hierarchy_index()
    corrections: dict[int, dict[str, Any]] = {}  # row_index -> {col: value}

    cascade_fields = schema.get_cascade_columns() if schema is not None else []
    for col_name, cascade_field_name in cascade_fields:
        if col_name not in merged_df.columns:
            continue

        # Find rows where the cascade field is null
        null_mask = merged_df[col_name].is_null()
        null_indices = null_mask.arg_true().to_list()

        for row_idx in null_indices:
            result.rows_checked += 1
            gid = merged_df["gid"][row_idx]

            if gid is None:
                continue

            # Check if hierarchy index has ancestors for this task
            ancestor_gids = hierarchy.get_ancestor_chain(str(gid), max_depth=5)
            if not ancestor_gids:
                continue

            # Try to resolve the cascade field from live store
            parent_chain = await store.get_parent_chain_async(str(gid))
            if not parent_chain:
                continue

            # Search parent chain for field value using cascade plugin
            for parent_data in parent_chain:
                value = cascade_plugin._get_custom_field_value_from_dict(
                    parent_data, cascade_field_name
                )
                if value is not None:
                    result.rows_stale += 1
                    if row_idx not in corrections:
                        corrections[row_idx] = {}
                    corrections[row_idx][col_name] = value

                    # Track affected section for re-persistence
                    if "section_gid" in merged_df.columns:
                        section_gid = merged_df["section_gid"][row_idx]
                        if section_gid is not None:
                            result.sections_affected.add(str(section_gid))
                    break

    # Apply corrections if any
    if corrections:
        # Build correction series for each column
        for col_name, _ in cascade_fields:
            if col_name not in merged_df.columns:
                continue

            col_corrections = {
                idx: vals[col_name]
                for idx, vals in corrections.items()
                if col_name in vals
            }
            if col_corrections:
                # Create updated column
                values = merged_df[col_name].to_list()
                for idx, val in col_corrections.items():
                    values[idx] = val
                    result.rows_corrected += 1
                merged_df = merged_df.with_columns(
                    pl.Series(col_name, values).cast(merged_df[col_name].dtype)
                )

    result.duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "cascade_validation_complete",
        extra={
            "project_gid": project_gid,
            "entity_type": entity_type,
            "rows_checked": result.rows_checked,
            "rows_stale": result.rows_stale,
            "rows_corrected": result.rows_corrected,
            "sections_affected": list(result.sections_affected),
            "duration_ms": round(result.duration_ms, 2),
        },
    )

    return merged_df, result
