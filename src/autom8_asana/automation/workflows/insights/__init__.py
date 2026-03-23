"""Insights export bridge -- daily HTML report for Offer tasks.

Per ADR-bridge-format-engine: Instance-specific code for the Insights
bridge lives in this subdirectory, separate from platform-level files.
"""

from autom8_asana.automation.workflows.insights.workflow import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_ROW_LIMITS,
    EXPORT_ENABLED_ENV_VAR,
    OFFER_PROJECT_GID,
    TABLE_NAMES,
    TOTAL_TABLE_COUNT,
    WORKFLOW_VERSION,
    InsightsExportWorkflow,
)

__all__ = [
    "DEFAULT_ATTACHMENT_PATTERN",
    "DEFAULT_MAX_CONCURRENCY",
    "DEFAULT_ROW_LIMITS",
    "EXPORT_ENABLED_ENV_VAR",
    "InsightsExportWorkflow",
    "OFFER_PROJECT_GID",
    "TABLE_NAMES",
    "TOTAL_TABLE_COUNT",
    "WORKFLOW_VERSION",
]
