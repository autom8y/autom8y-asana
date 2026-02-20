"""Lambda handler for insights export workflow.

Per TDD-EXPORT-001 Section 3.4: Entry point for scheduled Lambda execution.
Triggered by EventBridge rule on configured schedule (6:00 AM ET daily).

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    AUTOM8_DATA_URL: Base URL for autom8_data
    AUTOM8_DATA_API_KEY: API key for autom8_data
    AUTOM8_EXPORT_ENABLED: Feature flag (default: enabled)
"""

from __future__ import annotations

from typing import Any

from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)


def _create_workflow(asana_client: Any, data_client: Any) -> Any:
    """Deferred workflow construction for cold-start optimization."""
    from autom8_asana.automation.workflows.insights_export import (
        InsightsExportWorkflow,
    )

    return InsightsExportWorkflow(
        asana_client=asana_client,
        data_client=data_client,
        attachments_client=asana_client.attachments,
    )


_config = WorkflowHandlerConfig(
    workflow_factory=_create_workflow,
    workflow_id="insights-export",
    log_prefix="lambda_insights_export",
    default_params={
        "max_concurrency": 5,
        "attachment_pattern": "insights_export_*.html",
        "row_limits": {"APPOINTMENTS": 250, "LEADS": 250},
    },
    response_metadata_keys=("total_tables_succeeded", "total_tables_failed"),
)

handler = create_workflow_handler(_config)
