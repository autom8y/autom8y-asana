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

import asyncio
import json
import traceback
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for insights export workflow.

    Args:
        event: EventBridge event (can contain override params).
        context: Lambda context with timeout info.

    Returns:
        Dict with execution result summary.
    """
    return asyncio.run(_handler_async(event, context))


async def _handler_async(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Async implementation of the Lambda handler."""
    try:
        return await _execute(event)
    except Exception as exc:
        logger.error(
            "lambda_insights_export_error",
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            ),
        }


async def _execute(event: dict[str, Any]) -> dict[str, Any]:
    """Execute the workflow with client initialization and cleanup."""
    from autom8_asana.automation.workflows.insights_export import (
        DEFAULT_ATTACHMENT_PATTERN,
        DEFAULT_MAX_CONCURRENCY,
        DEFAULT_ROW_LIMITS,
        InsightsExportWorkflow,
    )
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient

    logger.info("lambda_insights_export_started", lambda_event=event)

    # Build params from event or defaults
    params = {
        "workflow_id": "insights-export",
        "max_concurrency": event.get("max_concurrency", DEFAULT_MAX_CONCURRENCY),
        "attachment_pattern": event.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        ),
        "row_limits": event.get("row_limits", DEFAULT_ROW_LIMITS),
    }

    # Initialize clients
    asana_client = AsanaClient()
    async with DataServiceClient() as data_client:
        workflow = InsightsExportWorkflow(
            asana_client=asana_client,
            data_client=data_client,
            attachments_client=asana_client.attachments,
        )

        # Pre-flight validation
        validation_errors = await workflow.validate_async()
        if validation_errors:
            logger.error(
                "lambda_insights_export_validation_failed",
                errors=validation_errors,
            )
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "status": "skipped",
                        "reason": "validation_failed",
                        "errors": validation_errors,
                    }
                ),
            }

        # Execute workflow
        result = await workflow.execute_async(params)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "completed",
                    "workflow_id": result.workflow_id,
                    "total": result.total,
                    "succeeded": result.succeeded,
                    "failed": result.failed,
                    "skipped": result.skipped,
                    "duration_seconds": round(result.duration_seconds, 2),
                    "failure_rate": round(result.failure_rate, 4),
                    "total_tables_succeeded": result.metadata.get(
                        "total_tables_succeeded", 0
                    ),
                    "total_tables_failed": result.metadata.get(
                        "total_tables_failed", 0
                    ),
                }
            ),
        }
