"""Reconciliation reporting and metric emission.

Per REVIEW-reconciliation-deep-audit TC-4 / P1-A:
- Emits ReconciliationExcludedCount metric
- Computes exclusion_rate = excluded_count / total_scanned
- Warns when exclusion rate exceeds 50% (anomaly signal)

Module: src/autom8_asana/reconciliation/report.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.reconciliation.processor import ProcessorResult

logger = get_logger(__name__)

# Threshold above which exclusion rate is considered anomalous.
# Per REVIEW-reconciliation-deep-audit TC-4: 756 phantom exclusions
# in the smoke test produced a ~100% exclusion rate. A healthy pipeline
# should exclude <50% of units.
_EXCLUSION_RATE_WARNING_THRESHOLD = 0.50


@dataclass(frozen=True)
class ReconciliationReport:
    """Structured report from a reconciliation run.

    Immutable snapshot of processor results with computed metrics
    for observability and alerting.
    """

    total_scanned: int
    excluded_count: int
    no_op_count: int
    error_count: int
    actions_planned: int
    skipped_no_section: int
    exclusion_rate: float
    is_anomalous: bool

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for structured logging."""
        return {
            "total_scanned": self.total_scanned,
            "excluded_count": self.excluded_count,
            "no_op_count": self.no_op_count,
            "error_count": self.error_count,
            "actions_planned": self.actions_planned,
            "skipped_no_section": self.skipped_no_section,
            "exclusion_rate": round(self.exclusion_rate, 4),
            "is_anomalous": self.is_anomalous,
        }


def build_report(result: ProcessorResult) -> ReconciliationReport:
    """Build a structured report from processor results.

    Computes exclusion rate and anomaly flags for downstream
    metric emission and alerting.

    Args:
        result: ProcessorResult from a completed processor run.

    Returns:
        Immutable ReconciliationReport snapshot.
    """
    total = result.total_scanned
    excluded = result.excluded_count
    exclusion_rate = excluded / total if total > 0 else 0.0
    is_anomalous = exclusion_rate > _EXCLUSION_RATE_WARNING_THRESHOLD

    return ReconciliationReport(
        total_scanned=total,
        excluded_count=excluded,
        no_op_count=result.no_op_count,
        error_count=result.error_count,
        actions_planned=len(result.actions),
        skipped_no_section=result.skipped_no_section,
        exclusion_rate=exclusion_rate,
        is_anomalous=is_anomalous,
    )


def emit_report_metrics(report: ReconciliationReport) -> None:
    """Emit reconciliation metrics to structured logs.

    Per REVIEW-reconciliation-deep-audit TC-4 / P1-A:
    - ReconciliationExcludedCount: number of units excluded
    - ReconciliationExclusionRate: ratio of excluded to total
    - Anomaly warning when exclusion rate > 50%

    Args:
        report: ReconciliationReport to emit metrics for.
    """
    # P1-A: Emit ReconciliationExcludedCount
    logger.info(
        "reconciliation_excluded_count",
        extra={
            "metric_name": "ReconciliationExcludedCount",
            "metric_value": report.excluded_count,
            "total_scanned": report.total_scanned,
            "exclusion_rate": round(report.exclusion_rate, 4),
        },
    )

    # Emit full report summary
    logger.info(
        "reconciliation_report",
        extra=report.to_dict(),
    )

    # Anomaly warning
    if report.is_anomalous:
        logger.warning(
            "reconciliation_exclusion_rate_anomaly",
            extra={
                "exclusion_rate": round(report.exclusion_rate, 4),
                "threshold": _EXCLUSION_RATE_WARNING_THRESHOLD,
                "excluded_count": report.excluded_count,
                "total_scanned": report.total_scanned,
                "skipped_no_section": report.skipped_no_section,
                "reason": (
                    f"Exclusion rate {report.exclusion_rate:.1%} exceeds "
                    f"{_EXCLUSION_RATE_WARNING_THRESHOLD:.0%} threshold"
                ),
            },
        )
