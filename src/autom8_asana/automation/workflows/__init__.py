"""Batch automation workflows for autom8_asana.

Per TDD-CONV-AUDIT-001 Section 2.1: Provides the WorkflowAction ABC,
WorkflowResult/WorkflowItemError dataclasses, and WorkflowRegistry for
generalized batch workflow dispatch alongside the existing per-task
ActionExecutor pipeline.
"""

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.registry import WorkflowRegistry

__all__ = [
    "WorkflowAction",
    "WorkflowItemError",
    "WorkflowResult",
    "WorkflowRegistry",
]
