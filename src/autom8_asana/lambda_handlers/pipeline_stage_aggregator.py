"""Pipeline stage aggregation for the cache warmer Lambda.

Post-warm aggregation step that scans all 9 pipeline DataFrames from
cache and produces a per-(office_phone, vertical) summary showing the
latest active process for each unit.

The summary is ephemeral -- computed fresh each warm cycle and consumed
by reconciliation and status push within the same invocation. It is NOT
written to cache (per ADR-pipeline-stage-aggregation, Option C).

Pattern precedent: push_orchestrator.py, reconciliation_runner.py in
the same directory.

Per architectural decision FLAG-1: this function remains in
lambda_handlers/ (not services/) to avoid a circular dependency -- the
service modules already own the implementation being called here.
"""

from __future__ import annotations

from typing import Any

import polars as pl
from autom8y_log import get_logger

logger = get_logger(__name__)

__all__ = ["_aggregate_pipeline_stages"]

# Prefix used to identify pipeline entity types in completed_entities.
_PIPELINE_ENTITY_PREFIX = "process_"


def _derive_pipeline_type(entity_name: str) -> str:
    """Derive pipeline_type from entity name.

    Strips the 'process_' prefix to produce the pipeline type string.
    E.g., 'process_sales' -> 'sales', 'process_onboarding' -> 'onboarding'.

    Args:
        entity_name: Entity type name (e.g., "process_sales").

    Returns:
        Pipeline type string (e.g., "sales").
    """
    return entity_name[len(_PIPELINE_ENTITY_PREFIX) :]


async def _aggregate_pipeline_stages(
    *,
    completed_entities: list[str],
    cache: Any,
    invocation_id: str | None,
) -> pl.DataFrame | None:
    """Aggregate pipeline stages from warmed pipeline DataFrames.

    Scans all pipeline entity DataFrames that completed warming, adds a
    pipeline_type discriminator column, concatenates them, filters to
    active tasks (is_completed=False), groups by (office_phone, vertical),
    and selects the row with the most recent ``created`` timestamp per
    group -- the "latest active process" per the R3 decision.

    This function is non-blocking: all errors are caught and logged so
    that aggregation failures never affect the cache warmer result.

    Args:
        completed_entities: Entity types that were successfully warmed.
        cache: DataFrameCache instance for retrieving warmed DataFrames.
        invocation_id: Lambda invocation ID for log correlation.

    Returns:
        A pipeline_summary DataFrame with columns:
            - office_phone (Utf8)
            - vertical (Utf8)
            - latest_process_type (Utf8)
            - latest_process_section (Utf8)
            - latest_created (Datetime)
        Returns None if no pipeline data was warmed or no active
        processes were found.
    """
    try:
        # ---------------------------------------------------------------
        # Step 1: Identify which pipeline entities completed warming
        # ---------------------------------------------------------------
        pipeline_entities = [
            name for name in completed_entities if name.startswith(_PIPELINE_ENTITY_PREFIX)
        ]

        if not pipeline_entities:
            return None

        logger.info(
            "pipeline_stage_aggregation_start",
            extra={
                "pipeline_count": len(pipeline_entities),
                "pipeline_entities": sorted(pipeline_entities),
                "invocation_id": invocation_id,
            },
        )

        # ---------------------------------------------------------------
        # Step 2: Retrieve each pipeline DF from cache and add
        #         pipeline_type discriminator column.
        # ---------------------------------------------------------------
        from autom8_asana.core.entity_registry import get_registry

        entity_registry = get_registry()
        frames: list[pl.DataFrame] = []

        for entity_name in pipeline_entities:
            desc = entity_registry.get(entity_name)
            if desc is None or desc.primary_project_gid is None:
                logger.warning(
                    "pipeline_entity_not_registered",
                    extra={
                        "entity_name": entity_name,
                        "invocation_id": invocation_id,
                    },
                )
                continue

            entry = await cache.get_async(desc.primary_project_gid, entity_name)
            if entry is None or entry.dataframe is None:
                continue

            df = entry.dataframe

            # Step 3: Add pipeline_type discriminator column
            pipeline_type = _derive_pipeline_type(entity_name)
            df = df.with_columns(pl.lit(pipeline_type).alias("pipeline_type"))

            frames.append(df)

        if not frames:
            return None

        # ---------------------------------------------------------------
        # Step 4: Concatenate all pipeline DFs
        # ---------------------------------------------------------------
        combined = pl.concat(frames, how="diagonal_relaxed")

        # ---------------------------------------------------------------
        # Step 5: Filter to active tasks only (is_completed == False)
        # ---------------------------------------------------------------
        active = combined.filter(pl.col("is_completed") == False)  # noqa: E712

        if active.is_empty():
            logger.info(
                "pipeline_stage_aggregation_complete",
                extra={
                    "total_processes": len(combined),
                    "unique_units": 0,
                    "summary_rows": 0,
                    "invocation_id": invocation_id,
                },
            )
            return None

        # ---------------------------------------------------------------
        # Step 6: Group by (office_phone, vertical) and find the row
        #         with the most recent 'created' timestamp per group.
        # ---------------------------------------------------------------
        # Drop rows with null grouping keys -- cannot join without them.
        active = active.filter(
            pl.col("office_phone").is_not_null() & pl.col("vertical").is_not_null()
        )

        if active.is_empty():
            return None

        # Sort descending by created, then take first per group
        summary = (
            active.sort("created", descending=True)
            .group_by(["office_phone", "vertical"])
            .first()
            .select(
                pl.col("office_phone"),
                pl.col("vertical"),
                pl.col("pipeline_type").alias("latest_process_type"),
                pl.col("section").alias("latest_process_section"),
                pl.col("created").alias("latest_created"),
            )
        )

        # ---------------------------------------------------------------
        # Step 7: Log completion
        # ---------------------------------------------------------------
        total_processes = len(combined)
        unique_units = len(summary)

        logger.info(
            "pipeline_stage_aggregation_complete",
            extra={
                "total_processes": total_processes,
                "unique_units": unique_units,
                "summary_rows": unique_units,
                "invocation_id": invocation_id,
            },
        )

        # ---------------------------------------------------------------
        # Step 8: Return the summary DF
        # ---------------------------------------------------------------
        return summary

    except (
        Exception  # noqa: BLE001
    ) as exc:  # BROAD-CATCH: isolation -- never crash the cache warmer
        logger.warning(
            "pipeline_stage_aggregation_error",
            extra={
                "error": str(exc),
                "error_type": type(exc).__name__,
                "invocation_id": invocation_id,
            },
        )
        return None
