"""Batch automation workflows for autom8_asana.

Per TDD-CONV-AUDIT-001 Section 2.1: Provides the WorkflowAction ABC,
WorkflowResult/WorkflowItemError dataclasses, and WorkflowRegistry for
generalized batch workflow dispatch alongside the existing per-task
ActionExecutor pipeline.

Per ADR-bridge-intermediate-base-class: BridgeWorkflowAction and
BridgeOutcome added in sprint-3 for Data Attachment Bridge workflows.
"""

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.bridge_base import (
    BridgeOutcome,
    BridgeWorkflowAction,
)
from autom8_asana.automation.workflows.protocols import DataSource, FormatEngine
from autom8_asana.automation.workflows.registry import WorkflowRegistry

__all__ = [
    "BridgeOutcome",
    "BridgeWorkflowAction",
    "DataSource",
    "FormatEngine",
    "WorkflowAction",
    "WorkflowItemError",
    "WorkflowResult",
    "WorkflowRegistry",
]
