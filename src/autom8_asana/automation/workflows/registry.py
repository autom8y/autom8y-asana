"""Registry for discovering and dispatching batch workflows.

Per TDD-CONV-AUDIT-001 Section 3.2: Simple dictionary-based registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.automation.workflows.base import WorkflowAction

logger = get_logger(__name__)

__all__ = ["WorkflowRegistry"]


class WorkflowRegistry:
    """Registry of available WorkflowAction implementations.

    Workflows are registered at application startup and looked up by
    workflow_id when the scheduler encounters action.type == "workflow".
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowAction] = {}

    def register(self, workflow: WorkflowAction) -> None:
        """Register a workflow for scheduler dispatch.

        Args:
            workflow: WorkflowAction implementation.

        Raises:
            ValueError: If workflow_id is already registered.
        """
        wid = workflow.workflow_id
        if wid in self._workflows:
            raise ValueError(
                f"Workflow '{wid}' is already registered. "
                f"Duplicate registration is not allowed."
            )
        self._workflows[wid] = workflow
        logger.info("workflow_registered", workflow_id=wid)

    def get(self, workflow_id: str) -> WorkflowAction | None:
        """Look up a workflow by ID.

        Args:
            workflow_id: The workflow_id to look up.

        Returns:
            WorkflowAction instance, or None if not found.
        """
        return self._workflows.get(workflow_id)

    def list_ids(self) -> list[str]:
        """List all registered workflow IDs.

        Returns:
            Sorted list of registered workflow_id strings.
        """
        return sorted(self._workflows.keys())
