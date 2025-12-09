"""Project model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Project(AsanaResource):
    """Asana Project resource model.

    Uses NameGid for typed resource references (owner, team, workspace).
    Custom fields and complex nested structures remain as dicts.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> project = Project.model_validate(api_response)
        >>> if project.owner:
        ...     print(f"Owned by {project.owner.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="project")

    # Basic project fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status
    archived: bool | None = None
    public: bool | None = None
    color: str | None = Field(
        default=None,
        description="Color of the project (dark-pink, dark-green, etc.)",
    )

    # Dates
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
    modified_at: str | None = Field(default=None, description="Modified datetime (ISO 8601)")
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    due_at: str | None = Field(default=None, description="Due datetime (ISO 8601)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")

    # Relationships - typed with NameGid
    owner: NameGid | None = None
    team: NameGid | None = None
    workspace: NameGid | None = None
    current_status: NameGid | None = None
    current_status_update: NameGid | None = None

    # Collections
    members: list[NameGid] | None = None
    followers: list[NameGid] | None = None
    custom_fields: list[dict[str, Any]] | None = None  # Complex structure
    custom_field_settings: list[dict[str, Any]] | None = None  # Complex structure

    # Project properties
    default_view: str | None = Field(
        default=None,
        description="Default view (list, board, calendar, timeline)",
    )
    default_access_level: str | None = Field(
        default=None,
        description="Default access for new members (admin, editor, commenter, viewer)",
    )
    minimum_access_level_for_customization: str | None = None
    minimum_access_level_for_sharing: str | None = None
    is_template: bool | None = None
    completed: bool | None = None
    completed_at: str | None = None
    completed_by: NameGid | None = None
    created_from_template: NameGid | None = None

    # Layout-specific
    icon: str | None = None
    permalink_url: str | None = None

    # Privacy
    privacy_setting: str | None = Field(
        default=None,
        description="Privacy setting (public_to_workspace, private_to_team, private)",
    )
