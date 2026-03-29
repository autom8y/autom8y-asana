"""Reconciliation shadow-mode runner for the cache warmer Lambda.

Thin orchestration wrapper that wires engine -> executor -> report
after cache warming completes. Runs in shadow mode only (dry_run=True,
not configurable) behind a feature flag. Non-blocking -- must never
crash the cache warmer.

Pattern precedent: push_orchestrator.py in the same directory.

Per architectural decision FLAG-1: these functions remain in
lambda_handlers/ (not services/) to avoid a circular dependency -- the
service modules already own the implementation being called here.
"""

from __future__ import annotations

from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)

__all__ = ["_run_reconciliation_shadow"]

# Both entity types must be present to run reconciliation.
_REQUIRED_ENTITIES = frozenset({"unit", "offer"})


async def _run_reconciliation_shadow(
    *,
    completed_entities: list[str],
    get_project_gid: Any,  # Callable that resolves entity_type -> project GID
    cache: Any,  # DataFrameCache instance
    invocation_id: str | None,
) -> None:
    """Run reconciliation in shadow mode after cache warming.

    Retrieves unit and offer DataFrames from cache, runs the
    reconciliation engine in dry_run mode, executes actions (also
    dry_run), and emits a structured report.

    This function is non-blocking: all errors are caught and logged so
    that reconciliation failures never affect the cache warmer result.

    Args:
        completed_entities: Entity types that were successfully warmed.
        get_project_gid: Callable(entity_type) -> project_gid or None.
        cache: DataFrameCache instance for retrieving warmed DataFrames.
        invocation_id: Lambda invocation ID for log correlation.
    """
    import os

    if os.environ.get("ASANA_RECONCILIATION_SHADOW_ENABLED", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        return

    try:
        # ---------------------------------------------------------------
        # Entity guard: both unit AND offer must be warmed
        # ---------------------------------------------------------------
        completed_set = set(completed_entities)
        missing = _REQUIRED_ENTITIES - completed_set
        if missing:
            logger.info(
                "reconciliation_shadow_skipped",
                extra={
                    "reason": "missing required entities",
                    "missing": sorted(missing),
                    "completed": sorted(completed_set),
                    "invocation_id": invocation_id,
                },
            )
            return

        # ---------------------------------------------------------------
        # Retrieve DataFrames from cache
        # ---------------------------------------------------------------
        unit_project_gid = get_project_gid("unit")
        offer_project_gid = get_project_gid("offer")

        unit_entry = await cache.get_async(unit_project_gid, "unit")
        if unit_entry is None or unit_entry.dataframe is None:
            logger.info(
                "reconciliation_shadow_skipped",
                extra={
                    "reason": "unit DataFrame not available",
                    "invocation_id": invocation_id,
                },
            )
            return

        offer_entry = await cache.get_async(offer_project_gid, "offer")
        if offer_entry is None or offer_entry.dataframe is None:
            logger.info(
                "reconciliation_shadow_skipped",
                extra={
                    "reason": "offer DataFrame not available",
                    "invocation_id": invocation_id,
                },
            )
            return

        unit_df = unit_entry.dataframe
        offer_df = offer_entry.dataframe

        # ---------------------------------------------------------------
        # Run reconciliation engine (sync call)
        # ---------------------------------------------------------------
        from autom8_asana.reconciliation.engine import (
            ReconciliationConfig,
            run_reconciliation,
        )

        config = ReconciliationConfig(dry_run=True)  # SHADOW MODE: always dry_run
        result = run_reconciliation(unit_df, offer_df, config=config)

        # ---------------------------------------------------------------
        # Execute actions (async, also dry_run)
        # ---------------------------------------------------------------
        from autom8_asana.reconciliation.executor import execute_actions

        await execute_actions(result.processor_result.actions, dry_run=True)

        # ---------------------------------------------------------------
        # Emit report
        # ---------------------------------------------------------------
        from autom8_asana.reconciliation.report import (
            build_report,
            emit_report_metrics,
        )

        report = build_report(result.processor_result)
        emit_report_metrics(report)

        # ---------------------------------------------------------------
        # Log completion
        # ---------------------------------------------------------------
        logger.info(
            "reconciliation_shadow_complete",
            extra={
                "actions_planned": result.actions_planned,
                "total_scanned": result.total_scanned,
                "excluded_count": result.excluded_count,
                "invocation_id": invocation_id,
            },
        )

    except Exception as exc:  # BROAD-CATCH: isolation -- never crash the cache warmer
        logger.warning(
            "reconciliation_shadow_error",
            extra={
                "error": str(exc),
                "error_type": type(exc).__name__,
                "invocation_id": invocation_id,
            },
        )
