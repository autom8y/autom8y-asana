"""Lambda handler for payment reconciliation workflow.

Per TDD-data-attachment-bridge-platform Section 7.
Entry point: autom8_asana.lambda_handlers.payment_reconciliation.handler
Trigger: EventBridge weekly, Monday 8:00 AM ET

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    AUTOM8Y_DATA_URL: Base URL for autom8_data
    AUTOM8Y_DATA_API_KEY: API key for autom8_data
    AUTOM8_RECONCILIATION_ENABLED: Feature flag (default: enabled)
"""

from __future__ import annotations

from typing import Any

from autom8_asana.models.business._bootstrap import bootstrap

bootstrap()

# ruff: noqa: E402
from autom8_asana.automation.workflows.payment_reconciliation import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MAX_CONCURRENCY,
)
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)


def _create_workflow(asana_client: Any, data_client: Any) -> Any:
    """Deferred workflow construction for cold-start optimization."""
    from autom8_asana.automation.workflows.payment_reconciliation import (
        PaymentReconciliationWorkflow,
    )

    return PaymentReconciliationWorkflow(
        asana_client=asana_client,
        data_client=data_client,
        attachments_client=asana_client.attachments,
    )


_config = WorkflowHandlerConfig(
    workflow_factory=_create_workflow,
    workflow_id="payment-reconciliation",
    log_prefix="lambda_payment_reconciliation",
    default_params={
        "max_concurrency": DEFAULT_MAX_CONCURRENCY,
        "attachment_pattern": DEFAULT_ATTACHMENT_PATTERN,
        "lookback_days": DEFAULT_LOOKBACK_DAYS,
    },
    response_metadata_keys=("total_excel_rows",),
    dms_namespace="Autom8y/AsanaReconciliation",
)

handler = create_workflow_handler(_config)
