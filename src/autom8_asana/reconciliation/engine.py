"""Reconciliation engine -- orchestrates the reconciliation pipeline.

Instantiates ReconciliationBatchProcessor, runs the pipeline, and
returns a structured result object for downstream consumption.

Module: src/autom8_asana/reconciliation/engine.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autom8y_log import get_logger

from autom8_asana.reconciliation.processor import (
    ProcessorResult,
    ReconciliationBatchProcessor,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class ReconciliationConfig:
    """Configuration for a reconciliation run.

    Attributes:
        dry_run: If True, compute actions but do not execute.
        max_actions: Maximum number of actions to execute per run.
            0 means unlimited. Defaults to 0.
    """

    dry_run: bool = True
    max_actions: int = 0


@dataclass
class ReconciliationResult:
    """Top-level result from a reconciliation pipeline run.

    Wraps the processor result and adds engine-level metadata
    (config used, execution status, etc.).
    """

    processor_result: ProcessorResult = field(default_factory=ProcessorResult)
    config: ReconciliationConfig = field(default_factory=ReconciliationConfig)
    executed: bool = False
    execution_errors: list[str] = field(default_factory=list)

    @property
    def actions_planned(self) -> int:
        """Number of reconciliation actions identified."""
        return len(self.processor_result.actions)

    @property
    def total_scanned(self) -> int:
        """Total number of units scanned."""
        return self.processor_result.total_scanned

    @property
    def excluded_count(self) -> int:
        """Number of units excluded from processing."""
        return self.processor_result.excluded_count


def run_reconciliation(
    unit_df: Any,
    offer_df: Any,
    *,
    config: ReconciliationConfig | None = None,
) -> ReconciliationResult:
    """Run the reconciliation pipeline.

    Orchestrates the full pipeline: processor instantiation, batch
    processing, optional execution, and result reporting.

    Args:
        unit_df: Polars DataFrame of unit tasks.
        offer_df: Polars DataFrame of offer tasks.
        config: Pipeline configuration. Defaults to dry_run=True.

    Returns:
        ReconciliationResult with processor output and execution status.
    """
    if config is None:
        config = ReconciliationConfig()

    result = ReconciliationResult(config=config)

    logger.info(
        "reconciliation_engine_start",
        extra={
            "dry_run": config.dry_run,
            "max_actions": config.max_actions,
            "unit_df_rows": len(unit_df) if hasattr(unit_df, "__len__") else "unknown",
            "offer_df_rows": len(offer_df) if hasattr(offer_df, "__len__") else "unknown",
        },
    )

    try:
        processor = ReconciliationBatchProcessor(
            unit_df,
            offer_df,
            dry_run=config.dry_run,
        )
        result.processor_result = processor.process()
    except Exception:
        logger.exception(
            "reconciliation_engine_processor_error",
            extra={"dry_run": config.dry_run},
        )
        raise

    # Execution phase (when not dry_run) is handled by executor module
    if not config.dry_run and result.actions_planned > 0:
        logger.info(
            "reconciliation_engine_execution_skipped",
            extra={
                "reason": "executor not invoked from engine -- use executor.execute_actions()",
                "actions_planned": result.actions_planned,
            },
        )

    logger.info(
        "reconciliation_engine_complete",
        extra={
            "total_scanned": result.total_scanned,
            "excluded_count": result.excluded_count,
            "actions_planned": result.actions_planned,
            "dry_run": config.dry_run,
        },
    )

    return result
