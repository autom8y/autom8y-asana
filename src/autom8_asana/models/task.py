"""Task model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
Complex nested structures (memberships, custom_fields, external) remain as dicts.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, PrivateAttr

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor


class Task(AsanaResource):
    """Asana Task resource model.

    Uses NameGid for typed resource references (assignee, projects, etc.).
    Custom fields and complex nested structures remain as dicts.

    Unknown fields from API responses are silently ignored (per ADR-0005).

    Example:
        >>> from autom8_asana.models import Task
        >>> task = Task.model_validate(api_response)
        >>> if task.assignee:
        ...     print(f"Assigned to {task.assignee.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="task")

    # Basic task fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status fields
    completed: bool | None = None
    completed_at: str | None = None
    completed_by: NameGid | None = None  # Changed from dict

    # Due dates
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    due_at: str | None = Field(default=None, description="Due datetime (ISO 8601)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    start_at: str | None = Field(default=None, description="Start datetime (ISO 8601)")

    # Relationships - typed with NameGid
    assignee: NameGid | None = None  # Changed from dict
    assignee_section: NameGid | None = None  # Changed from dict
    assignee_status: str | None = Field(
        default=None,
        description="Scheduling status (inbox, today, upcoming, later)",
    )
    projects: list[NameGid] | None = None  # Changed from list[dict]
    parent: NameGid | None = None  # Changed from dict
    workspace: NameGid | None = None  # Changed from dict
    memberships: list[dict[str, Any]] | None = None  # Keep as dict (complex structure)
    followers: list[NameGid] | None = None  # Changed from list[dict]
    tags: list[NameGid] | None = None  # Changed from list[dict]

    # Hierarchy and dependencies
    num_subtasks: int | None = None
    num_hearts: int | None = Field(default=None, description="Deprecated: use num_likes")
    num_likes: int | None = None
    is_rendered_as_separator: bool | None = None

    # Custom fields - remain as dict (complex structure)
    custom_fields: list[dict[str, Any]] | None = None

    # Metadata
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
    modified_at: str | None = Field(default=None, description="Modified datetime (ISO 8601)")
    created_by: NameGid | None = None  # Changed from dict

    # Approval fields
    approval_status: str | None = Field(
        default=None,
        description="Approval status (pending, approved, rejected, changes_requested)",
    )

    # External data - remains as dict (arbitrary structure)
    external: dict[str, Any] | None = Field(
        default=None,
        description="External data (id and data fields for integrations)",
    )

    # Visibility and access
    resource_subtype: str | None = Field(
        default=None,
        description="Subtype (default_task, milestone, section, approval)",
    )

    # Permalink
    permalink_url: str | None = None

    # Liked status
    liked: bool | None = None
    hearted: bool | None = Field(default=None, description="Deprecated: use liked")
    hearts: list[dict[str, Any]] | None = Field(
        default=None,
        description="Deprecated: use likes",
    )
    likes: list[dict[str, Any]] | None = None  # Keep as dict (user refs with extra data)

    # Actual time tracking
    actual_time_minutes: float | None = None

    # Private accessor instance (not serialized)
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)

    def get_custom_fields(self) -> CustomFieldAccessor:
        """Get custom fields accessor for fluent API.

        Returns a CustomFieldAccessor that provides set/get/remove methods
        with automatic name->GID resolution. The accessor tracks modifications
        for change detection.

        Example:
            accessor = task.get_custom_fields()
            accessor.set("Priority", "High")
            value = accessor.get("Status")

        Returns:
            CustomFieldAccessor instance (cached for this task).
        """
        if self._custom_fields_accessor is None:
            self._custom_fields_accessor = CustomFieldAccessor(self.custom_fields)
        return self._custom_fields_accessor

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to include custom field modifications.

        If the custom fields accessor has pending changes, the serialized
        output will use the accessor's to_list() format instead of the
        original custom_fields data.

        Args:
            **kwargs: Arguments passed to parent model_dump().

        Returns:
            Dict representation of the task.
        """
        data = super().model_dump(**kwargs)
        # If accessor exists and has changes, use its output
        if (
            self._custom_fields_accessor is not None
            and self._custom_fields_accessor.has_changes()
        ):
            data["custom_fields"] = self._custom_fields_accessor.to_list()
        return data
