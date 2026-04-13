"""Project model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
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
    resource_type: str | None = Field(
        default="project",
        description="Asana resource type name. Always 'project' for project resources.",
    )

    # Basic project fields
    name: str | None = Field(
        default=None,
        description="Display name of the project.",
    )
    notes: str | None = Field(
        default=None,
        description="Plain-text description body of the project.",
    )
    html_notes: str | None = Field(
        default=None,
        description="HTML-formatted description body of the project.",
    )

    # Status
    archived: bool | None = Field(
        default=None,
        description="True if the project has been archived.",
    )
    public: bool | None = Field(
        default=None,
        description="True if the project is visible to all workspace members.",
    )
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
    owner: NameGid | None = Field(
        default=None,
        description="User who owns the project.",
    )
    team: NameGid | None = Field(
        default=None,
        description="Team the project is assigned to.",
    )
    workspace: NameGid | None = Field(
        default=None,
        description="Workspace the project belongs to.",
    )
    current_status: NameGid | None = Field(
        default=None,
        description="Most recent status update posted to the project (deprecated, use current_status_update).",
    )
    current_status_update: NameGid | None = Field(
        default=None,
        description="Most recent status update object posted to the project.",
    )

    # Collections
    members: list[NameGid] | None = Field(
        default=None,
        description="Users who are members of the project.",
    )
    followers: list[NameGid] | None = Field(
        default=None,
        description="Users following the project for change notifications.",
    )
    custom_fields: list[dict[str, Any]] | None = Field(
        default=None,
        description="Custom field values set on this project.",
    )
    custom_field_settings: list[dict[str, Any]] | None = Field(
        default=None,
        description="Configuration of custom fields enabled on this project.",
    )

    # Project properties
    default_view: str | None = Field(
        default=None,
        description="Default view (list, board, calendar, timeline)",
    )
    default_access_level: str | None = Field(
        default=None,
        description="Default access for new members (admin, editor, commenter, viewer)",
    )
    minimum_access_level_for_customization: str | None = Field(
        default=None,
        description="Minimum access level required to customize the project.",
    )
    minimum_access_level_for_sharing: str | None = Field(
        default=None,
        description="Minimum access level required to share the project.",
    )
    is_template: bool | None = Field(
        default=None,
        description="True if this project is a template.",
    )
    completed: bool | None = Field(
        default=None,
        description="True if the project is marked complete.",
    )
    completed_at: str | None = Field(
        default=None,
        description="Datetime the project was completed (ISO 8601). Null if incomplete.",
    )
    completed_by: NameGid | None = Field(
        default=None,
        description="User who completed the project.",
    )
    created_from_template: NameGid | None = Field(
        default=None,
        description="Template project this was created from, if any.",
    )

    # Layout-specific
    icon: str | None = Field(
        default=None,
        description="Icon identifier for the project.",
    )
    permalink_url: str | None = Field(
        default=None,
        description="Permanent URL to the project in the Asana web app.",
    )

    # Privacy
    privacy_setting: str | None = Field(
        default=None,
        description="Privacy setting (public_to_workspace, private_to_team, private)",
    )

    # Tasks attribute for DataFrame building (populated externally)
    tasks: list[Any] | None = Field(
        default=None,
        exclude=True,
        description="Task list populated externally for DataFrame building. Excluded from serialization.",
    )
