"""Lambda handler for conversation audit workflow.

Per TDD-CONV-AUDIT-001 Section 8: Entry point for scheduled Lambda execution.
Triggered by EventBridge rule on configured schedule.

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    AUTOM8_DATA_URL: Base URL for autom8_data
    AUTOM8_DATA_API_KEY: API key for autom8_data
    AUTOM8_AUDIT_ENABLED: Feature flag (default: "true")
"""

from __future__ import annotations

from typing import Any

import autom8_asana.models.business  # noqa: F401 - bootstrap side effect
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)


def _create_workflow(asana_client: Any, data_client: Any) -> Any:
    """Deferred workflow construction for cold-start optimization."""
    from autom8_asana.automation.workflows.conversation_audit import (
        ConversationAuditWorkflow,
    )

    return ConversationAuditWorkflow(
        asana_client=asana_client,
        data_client=data_client,
        attachments_client=asana_client.attachments,
    )


_config = WorkflowHandlerConfig(
    workflow_factory=_create_workflow,
    workflow_id="conversation-audit",
    log_prefix="lambda_conversation_audit",
    default_params={
        "max_concurrency": 5,
        "attachment_pattern": "conversations_*.csv",
        "date_range_days": 30,
    },
    response_metadata_keys=("truncated_count",),
)

handler = create_workflow_handler(_config)
