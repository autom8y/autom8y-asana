"""Reconciliation executor -- handles Asana API calls for section moves.

Per REVIEW-reconciliation-deep-audit TC-4 / P1-D: Separates execution
from processing. When dry_run=True, logs planned actions without executing.
When dry_run=False, performs actual Asana API calls for section moves.

Module: src/autom8_asana/reconciliation/executor.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.reconciliation.processor import ReconciliationAction

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing reconciliation actions.

    Tracks successes, failures, and skipped actions for each
    individual Asana API call.
    """

    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_attempted(self) -> int:
        """Total number of actions attempted."""
        return self.succeeded + self.failed


async def execute_actions(
    actions: list[ReconciliationAction],
    *,
    dry_run: bool = True,
) -> ExecutionResult:
    """Execute reconciliation actions (section moves) against Asana.

    Per REVIEW-reconciliation-deep-audit:
    - dry_run=True: Log planned actions, do not execute
    - dry_run=False: Perform actual Asana API calls

    Args:
        actions: List of ReconciliationAction objects to execute.
        dry_run: If True, log but do not execute.

    Returns:
        ExecutionResult with success/failure counts.
    """
    result = ExecutionResult()

    if not actions:
        logger.info(
            "reconciliation_executor_no_actions",
            extra={"reason": "empty action list"},
        )
        return result

    if dry_run:
        for action in actions:
            logger.info(
                "reconciliation_executor_dry_run",
                extra={
                    "unit_gid": action.unit_gid,
                    "phone": action.phone,
                    "current_section": action.current_section,
                    "target_section": action.target_section,
                    "reason": action.reason,
                },
            )
            result.skipped += 1
        return result

    # Live execution path
    for action in actions:
        logger.info(
            "reconciliation_executor_attempting",
            extra={
                "unit_gid": action.unit_gid,
                "target_section": action.target_section,
            },
        )
        try:
            # TODO: Wire up actual Asana API call via task_service.move_to_section_async
            # For now, log the planned action. The actual implementation
            # requires injecting an authenticated Asana client.
            logger.warning(
                "reconciliation_executor_not_implemented",
                extra={
                    "unit_gid": action.unit_gid,
                    "target_section": action.target_section,
                    "reason": "live execution not yet wired to Asana API",
                },
            )
            result.skipped += 1
        except Exception as e:
            error_msg = f"Failed to move {action.unit_gid}: {e}"
            logger.error(
                "reconciliation_executor_error",
                extra={
                    "unit_gid": action.unit_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            result.errors.append(error_msg)
            result.failed += 1

    return result
