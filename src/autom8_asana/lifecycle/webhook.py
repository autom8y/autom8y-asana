# src/autom8_asana/lifecycle/webhook.py

from __future__ import annotations

from typing import Any

from autom8y_log import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class AsanaWebhookPayload(BaseModel):
    """Payload from Asana Rule webhook."""

    model_config = ConfigDict(extra="forbid")

    task_gid: str
    task_name: str | None = None
    project_gid: str | None = None
    section_name: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class WebhookResponse(BaseModel):
    """Response to Asana webhook."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    message: str = ""


@router.post(
    "/asana",
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def handle_asana_webhook(
    payload: AsanaWebhookPayload,
    request: Request,
) -> WebhookResponse:
    """Receive Asana Rule webhook and dispatch to automation.

    This endpoint receives webhook POST from Asana Rules when:
    - A task moves between sections (CONVERTED, DID NOT CONVERT)
    - A tag is added to a task (route_*, request_*, play_*)

    The full task object is in the payload (custom fields, section,
    projects). Subtasks, dependencies, and stories require separate
    API calls.

    Args:
        payload: Parsed webhook payload.
        request: FastAPI request (for accessing app state).

    Returns:
        WebhookResponse indicating acceptance.
    """
    logger.info(
        "webhook_received",
        task_gid=payload.task_gid,
        section=payload.section_name,
        tags=payload.tags,
    )

    # Get dispatch from app state
    dispatch = request.app.state.automation_dispatch

    # Build trigger from payload
    trigger: dict[str, Any] = {
        "id": f"webhook_{payload.task_gid}_{payload.section_name}",
        "task_gid": payload.task_gid,
    }

    if payload.section_name:
        trigger["type"] = "section_changed"
        trigger["section_name"] = payload.section_name
    elif payload.tags:
        trigger["type"] = "tag_added"
        trigger["tag_name"] = payload.tags[0] if payload.tags else ""

    result = await dispatch.dispatch_async(trigger)

    return WebhookResponse(
        accepted=True,
        message=f"Dispatched: {result.get('success', False)}",
    )
