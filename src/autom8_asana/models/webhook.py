"""Webhook model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per ADR-0008: Webhook signature verification is handled by WebhooksClient.
"""

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class WebhookFilter(AsanaResource):
    """Filter for webhook events.

    Determines which events trigger the webhook.

    Example:
        >>> filter = WebhookFilter.model_validate({
        ...     "gid": "1",
        ...     "resource_type": "task",
        ...     "action": "changed",
        ...     "fields": ["completed"]
        ... })
    """

    resource_type: str | None = Field(
        default=None, description="Resource type to filter (task, project, etc.)"
    )
    resource_subtype: str | None = None
    action: str | None = Field(
        default=None, description="Action to filter (changed, added, removed, etc.)"
    )
    fields: list[str] | None = Field(
        default=None, description="Fields that trigger the webhook"
    )


class Webhook(AsanaResource):
    """Asana Webhook resource model.

    Webhooks receive notifications when resources change.
    The target URL receives POST requests with event data.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> webhook = Webhook.model_validate(api_response)
        >>> print(f"Webhook {webhook.gid} -> {webhook.target}")
    """

    # Core identification
    resource_type: str | None = Field(default="webhook")

    # Webhook configuration
    target: str | None = Field(
        default=None, description="URL to receive webhook events"
    )
    active: bool | None = Field(default=None, description="Whether the webhook is active")

    # Resource being watched
    resource: NameGid | None = Field(
        default=None, description="Resource being watched"
    )

    # Filters
    filters: list[WebhookFilter] | None = Field(
        default=None, description="Event filters"
    )

    # Timestamps
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )
    last_failure_at: str | None = Field(
        default=None, description="Last failure datetime"
    )
    last_failure_content: str | None = Field(
        default=None, description="Last failure message"
    )
    last_success_at: str | None = Field(
        default=None, description="Last success datetime"
    )
