"""Workspace model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
"""

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource


class Workspace(AsanaResource):
    """Asana Workspace resource model.

    Workspaces are the highest-level organizational unit in Asana.
    Organizations are a type of workspace with additional features.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> ws = Workspace.model_validate(api_response)
        >>> print(f"Workspace: {ws.name} (org: {ws.is_organization})")
    """

    # Core identification
    resource_type: str | None = Field(default="workspace")

    # Basic workspace fields
    name: str | None = None
    is_organization: bool | None = Field(
        default=None,
        description="True if this workspace is an organization",
    )

    # Email domains (for organizations)
    email_domains: list[str] | None = Field(
        default=None,
        description="Email domains associated with the organization",
    )
