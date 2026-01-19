"""Delta merger for incremental DataFrame updates.

Per TDD-DATAFRAME-BUILDER-WATERMARK-001 Phase 3: Provides DeltaMerger for
merging incremental extraction results with cached DataFrame.

The merger implements the delta merge strategy:
1. Keep unchanged rows from existing DataFrame
2. Add newly extracted rows for changed/new tasks
3. Remove rows for deleted tasks
4. Deduplicate by GID (new rows win)

This enables efficient DataFrame updates without full rebuild.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.builders.fields import (
    WATERMARK_COLUMN_NAME,
    coerce_rows_to_schema,
)

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

logger = get_logger(__name__)


class DeltaMerger:
    """Merges incremental results with cached DataFrame.

    Per TDD Section 8.1: Implements delta merge for combining:
    - Unchanged rows from existing cache (identified by skipped_gids)
    - Newly extracted rows for changed/new tasks
    - Removal of deleted tasks

    The merger handles schema migration for backwards compatibility
    when the DataFrame schema evolves between runs.

    Example:
        >>> merger = DeltaMerger()
        >>> merged_df = merger.merge(
        ...     existing_df=cached_df,
        ...     new_rows=extracted_rows,
        ...     skipped_gids=["gid1", "gid2"],
        ...     deleted_gids=["gid3"],
        ...     schema=schema,
        ... )
    """

    def merge(
        self,
        existing_df: pl.DataFrame,
        new_rows: list[dict[str, Any]],
        skipped_gids: list[str],
        deleted_gids: list[str],
        schema: DataFrameSchema,
    ) -> pl.DataFrame:
        """Merge incremental extraction with existing cache.

        Per TDD Section 8.1: Delta merge strategy:
        1. Filter existing to unchanged rows only (from skipped_gids)
        2. Build DataFrame from new rows
        3. Concatenate unchanged + new
        4. Remove deleted GIDs
        5. Deduplicate by GID (new wins over old if duplicates)

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
        if skipped_gids:
            unchanged_df = existing_df.filter(pl.col("gid").is_in(skipped_gids))
        else:
            unchanged_df = pl.DataFrame(schema=schema.to_polars_schema())

        logger.debug(
            "delta_merger_unchanged_filtered",
            extra={
                "skipped_count": len(skipped_gids),
                "unchanged_rows": len(unchanged_df),
            },
        )

        # 2. Build DataFrame from new rows
        if new_rows:
            coerced_rows = coerce_rows_to_schema(new_rows, schema)
            new_df = pl.DataFrame(
                coerced_rows,
                schema=schema.to_polars_schema(),
            )
        else:
            new_df = pl.DataFrame(schema=schema.to_polars_schema())

        logger.debug(
            "delta_merger_new_rows_built",
            extra={"new_row_count": len(new_df)},
        )

        # 3. Concatenate unchanged + new
        # Use diagonal_relaxed to handle any minor schema differences
        if unchanged_df.is_empty() and new_df.is_empty():
            merged = pl.DataFrame(schema=schema.to_polars_schema())
        elif unchanged_df.is_empty():
            merged = new_df
        elif new_df.is_empty():
            merged = unchanged_df
        else:
            merged = pl.concat([unchanged_df, new_df], how="diagonal_relaxed")

        # 4. Remove deleted (already not in new_rows, but be explicit)
        if deleted_gids:
            pre_delete_count = len(merged)
            merged = merged.filter(~pl.col("gid").is_in(deleted_gids))
            logger.debug(
                "delta_merger_deleted_removed",
                extra={
                    "deleted_gids": len(deleted_gids),
                    "rows_removed": pre_delete_count - len(merged),
                },
            )

        # 5. Deduplicate by GID (new wins over old if any duplicates)
        # Using keep="last" ensures newly extracted rows take precedence
        pre_dedup_count = len(merged)
        merged = merged.unique(subset=["gid"], keep="last")
        if pre_dedup_count != len(merged):
            logger.debug(
                "delta_merger_deduplicated",
                extra={
                    "pre_dedup_count": pre_dedup_count,
                    "post_dedup_count": len(merged),
                    "duplicates_removed": pre_dedup_count - len(merged),
                },
            )

        logger.info(
            "delta_merger_completed",
            extra={
                "unchanged_count": len(skipped_gids),
                "new_count": len(new_rows),
                "deleted_count": len(deleted_gids),
                "final_row_count": len(merged),
            },
        )

        return merged


def handle_schema_migration(
    existing_df: pl.DataFrame,
    current_schema: DataFrameSchema,
) -> pl.DataFrame | None:
    """Check schema compatibility and migrate if possible.

    Per TDD Section 8.2: Handles schema evolution between runs:
    - New columns added: Add with null values
    - Columns removed: Drop them
    - Ensure _modified_at column exists for watermark

    Args:
        existing_df: Existing DataFrame from cache.
        current_schema: Current DataFrameSchema to migrate to.

    Returns:
        Migrated DataFrame if compatible, or None if incompatible
        (requiring force rebuild due to type changes).
    """
    existing_columns = set(existing_df.columns)
    required_columns = {col.name for col in current_schema.columns}

    # New columns added - can migrate by adding nulls
    new_columns = required_columns - existing_columns
    if new_columns:
        for col_name in new_columns:
            col_def = current_schema.get_column(col_name)
            if col_def is None:
                continue
            try:
                polars_dtype = col_def.get_polars_dtype()
                existing_df = existing_df.with_columns(
                    pl.lit(None).alias(col_name).cast(polars_dtype)
                )
                logger.debug(
                    "schema_migration_column_added",
                    extra={"column": col_name, "dtype": col_def.dtype},
                )
            except Exception as e:
                logger.warning(
                    "schema_migration_column_add_failed",
                    extra={"column": col_name, "error": str(e)},
                )
                # Can't migrate - force rebuild
                return None

    # Columns removed - just drop them
    removed_columns = existing_columns - required_columns
    # Don't remove internal columns like _modified_at
    removed_columns = {c for c in removed_columns if not c.startswith("_")}
    if removed_columns:
        existing_df = existing_df.drop(list(removed_columns))
        logger.debug(
            "schema_migration_columns_dropped",
            extra={"columns": list(removed_columns)},
        )

    # Check _modified_at column exists (required for watermark)
    if WATERMARK_COLUMN_NAME not in existing_df.columns:
        # Add with None - will cause all tasks to be reprocessed
        existing_df = existing_df.with_columns(
            pl.lit(None).alias(WATERMARK_COLUMN_NAME).cast(pl.Datetime("us", "UTC"))
        )
        logger.info(
            "schema_migration_watermark_added",
            extra={
                "column": WATERMARK_COLUMN_NAME,
                "impact": "all_tasks_will_reprocess",
            },
        )

    return existing_df


def validate_schema_compatibility(
    existing_df: pl.DataFrame,
    current_schema: DataFrameSchema,
) -> tuple[bool, list[str]]:
    """Validate if existing DataFrame is compatible with current schema.

    Checks for incompatible changes that require a full rebuild:
    - Column type changes (e.g., Utf8 -> Int64)

    Args:
        existing_df: Existing DataFrame from cache.
        current_schema: Current DataFrameSchema.

    Returns:
        Tuple of (is_compatible, list of incompatibility reasons).
    """
    issues: list[str] = []

    for col_def in current_schema.columns:
        if col_def.name not in existing_df.columns:
            # New column - can be migrated
            continue

        existing_dtype = existing_df[col_def.name].dtype
        try:
            expected_dtype = col_def.get_polars_dtype()
            # Compare dtype names since instances may differ
            if str(existing_dtype) != str(expected_dtype):
                issues.append(
                    f"Column '{col_def.name}' type changed: "
                    f"{existing_dtype} -> {expected_dtype}"
                )
        except ValueError:
            issues.append(f"Column '{col_def.name}' has unknown dtype: {col_def.dtype}")

    is_compatible = len(issues) == 0
    if not is_compatible:
        logger.warning(
            "schema_compatibility_check_failed",
            extra={"issues": issues},
        )

    return is_compatible, issues
