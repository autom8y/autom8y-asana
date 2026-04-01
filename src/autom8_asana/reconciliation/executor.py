"""Reconciliation executor -- handles Asana API calls for section moves.

Per REVIEW-reconciliation-deep-audit TC-4 / P1-D: Separates execution
from processing. When dry_run=True, logs planned actions without executing.
When dry_run=False, performs actual Asana API calls for section moves.

Per ADR-reconciliation-executor-materialization: MATERIALIZE -- wire
executor to existing task_service.move_to_section for live execution.

Module: src/autom8_asana/reconciliation/executor.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.clients.asana import AsanaClient
    from autom8_asana.reconciliation.processor import ReconciliationAction
    from autom8_asana.services.task_service import TaskService

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
    task_service: TaskService | None = None,
    client: AsanaClient | None = None,
    project_gid: str | None = None,
    section_name_to_gid: dict[str, str] | None = None,
) -> ExecutionResult:
    """Execute reconciliation actions (section moves) against Asana.

    Per REVIEW-reconciliation-deep-audit:
    - dry_run=True: Log planned actions, do not execute
    - dry_run=False: Perform actual Asana API calls

    Per ADR-reconciliation-executor-materialization:
    - Live execution requires task_service, client, project_gid, and
      section_name_to_gid to be injected.
    - Section names from ReconciliationAction.target_section are resolved
      to GIDs via section_name_to_gid mapping before calling
      task_service.move_to_section.

    Args:
        actions: List of ReconciliationAction objects to execute.
        dry_run: If True, log but do not execute.
        task_service: TaskService instance for Asana API calls.
            Required when dry_run=False.
        client: Authenticated AsanaClient for API requests.
            Required when dry_run=False.
        project_gid: Asana project GID containing the target sections.
            Required when dry_run=False.
        section_name_to_gid: Mapping of section name -> section GID
            for resolving ReconciliationAction.target_section to a GID.
            Required when dry_run=False.

    Returns:
        ExecutionResult with success/failure counts.

    Raises:
        RuntimeError: If dry_run=False and required dependencies are missing.
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

    # Live execution path -- validate injected dependencies
    if (
        task_service is None
        or client is None
        or project_gid is None
        or section_name_to_gid is None
    ):
        missing = [
            name
            for name, val in [
                ("task_service", task_service),
                ("client", client),
                ("project_gid", project_gid),
                ("section_name_to_gid", section_name_to_gid),
            ]
            if val is None
        ]
        raise RuntimeError(
            f"Live execution (dry_run=False) requires: {', '.join(missing)}. "
            "Inject via execute_actions(..., task_service=ts, client=c, "
            "project_gid=pg, section_name_to_gid=mapping)."
        )

    for action in actions:
        target_section_gid = section_name_to_gid.get(action.target_section or "")
        if target_section_gid is None:
            error_msg = (
                f"Cannot resolve section name {action.target_section!r} "
                f"to GID for unit {action.unit_gid}"
            )
            logger.error(
                "reconciliation_executor_section_resolve_error",
                extra={
                    "unit_gid": action.unit_gid,
                    "target_section": action.target_section,
                    "reason": "section_name_to_gid lookup failed",
                },
            )
            result.errors.append(error_msg)
            result.failed += 1
            continue

        logger.info(
            "reconciliation_executor_attempting",
            extra={
                "unit_gid": action.unit_gid,
                "target_section": action.target_section,
                "target_section_gid": target_section_gid,
                "project_gid": project_gid,
            },
        )
        try:
            await task_service.move_to_section(
                client,
                gid=action.unit_gid,
                section_gid=target_section_gid,
                project_gid=project_gid,
            )
            result.succeeded += 1
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
