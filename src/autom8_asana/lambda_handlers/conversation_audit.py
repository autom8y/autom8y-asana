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

import asyncio
import json
import traceback
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for conversation audit workflow.

    Args:
        event: EventBridge event (can contain override params).
        context: Lambda context with timeout info.

    Returns:
        Dict with execution result summary.
    """
    return asyncio.run(_handler_async(event, context))


async def _handler_async(
    event: dict[str, Any], context: Any
) -> dict[str, Any]:
    """Async implementation of the Lambda handler."""
    try:
        return await _execute(event)
    except Exception as exc:
        logger.error(
            "lambda_conversation_audit_error",
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__,
            }),
        }


async def _execute(event: dict[str, Any]) -> dict[str, Any]:
    """Execute the workflow with client initialization and cleanup."""
    from autom8_asana.automation.workflows.conversation_audit import (
        DEFAULT_ATTACHMENT_PATTERN,
        DEFAULT_DATE_RANGE_DAYS,
        DEFAULT_MAX_CONCURRENCY,
        ConversationAuditWorkflow,
    )
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient

    logger.info("lambda_conversation_audit_started", event=event)

    # Build params from event or defaults
    params = {
        "workflow_id": "conversation-audit",
        "max_concurrency": event.get("max_concurrency", DEFAULT_MAX_CONCURRENCY),
        "attachment_pattern": event.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        ),
        "date_range_days": event.get("date_range_days", DEFAULT_DATE_RANGE_DAYS),
    }

    # Initialize clients
    asana_client = AsanaClient()
    async with DataServiceClient() as data_client:
        workflow = ConversationAuditWorkflow(
            asana_client=asana_client,
            data_client=data_client,
            attachments_client=asana_client.attachments,
        )

        # Pre-flight validation
        validation_errors = await workflow.validate_async()
        if validation_errors:
            logger.error(
                "lambda_validation_failed",
                errors=validation_errors,
            )
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "skipped",
                    "reason": "validation_failed",
                    "errors": validation_errors,
                }),
            }

        # Execute workflow
        result = await workflow.execute_async(params)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "completed",
                "workflow_id": result.workflow_id,
                "total": result.total,
                "succeeded": result.succeeded,
                "failed": result.failed,
                "skipped": result.skipped,
                "duration_seconds": round(result.duration_seconds, 2),
                "failure_rate": round(result.failure_rate, 4),
                "truncated_count": result.metadata.get("truncated_count", 0),
            }),
        }
