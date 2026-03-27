"""Story model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Story resource model for Tier 2 clients (comments and activity).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class Story(AsanaResource):
    """Asana Story resource model.

    Stories are activity entries on tasks. They can be comments
    (created by users) or system-generated (tracking changes).

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> story = Story.model_validate(api_response)
        >>> if story.resource_subtype == "comment_added":
        ...     print(f"{story.created_by.name}: {story.text}")
    """

    # Core identification
    resource_type: str | None = Field(default="story")
    resource_subtype: str | None = Field(
        default=None,
        description="Story type (comment_added, assigned, due_date_changed, etc.)",
    )

    # Content
    text: str | None = Field(default=None, description="Story text content")
    html_text: str | None = Field(default=None, description="HTML formatted text")

    # Relationships
    target: NameGid | None = Field(default=None, description="Task this story is on")
    created_by: NameGid | None = Field(
        default=None,
        description="User who created this story entry.",
    )

    # Timestamps
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )

    # Editing
    is_editable: bool | None = Field(
        default=None,
        description="True if the authenticated user can edit this story.",
    )
    is_edited: bool | None = Field(
        default=None,
        description="True if the story text has been edited after creation.",
    )
    is_pinned: bool | None = Field(
        default=None,
        description="True if the story is pinned to the top of the task activity feed.",
    )

    # Reactions
    liked: bool | None = Field(
        default=None,
        description="True if the authenticated user has liked this story.",
    )
    likes: list[NameGid] | None = Field(
        default=None,
        description="Users who have liked this story.",
    )
    num_likes: int | None = Field(
        default=None,
        description="Number of likes on this story.",
    )

    # Sticker (for sticker stories)
    sticker_name: str | None = Field(
        default=None,
        description="Sticker identifier for sticker-type stories.",
    )

    # For system stories, these track what changed
    new_text_value: str | None = Field(
        default=None,
        description="New text value after a custom field text change.",
    )
    old_text_value: str | None = Field(
        default=None,
        description="Previous text value before a custom field text change.",
    )
    new_name: str | None = Field(
        default=None,
        description="New task name after a rename.",
    )
    old_name: str | None = Field(
        default=None,
        description="Previous task name before a rename.",
    )
    new_number_value: float | None = Field(
        default=None,
        description="New numeric value after a custom field number change.",
    )
    old_number_value: float | None = Field(
        default=None,
        description="Previous numeric value before a custom field number change.",
    )
    new_enum_value: NameGid | None = Field(
        default=None,
        description="New enum option after a custom field enum change.",
    )
    old_enum_value: NameGid | None = Field(
        default=None,
        description="Previous enum option before a custom field enum change.",
    )
    new_dates: dict[str, Any] | None = Field(
        default=None,
        description="New date values after a date change (contains due_on, due_at, start_on, start_at).",
    )
    old_dates: dict[str, Any] | None = Field(
        default=None,
        description="Previous date values before a date change.",
    )
    new_resource_subtype: str | None = Field(
        default=None,
        description="New resource subtype after a subtype change (e.g., default_task to milestone).",
    )
    old_resource_subtype: str | None = Field(
        default=None,
        description="Previous resource subtype before a subtype change.",
    )
    assignee: NameGid | None = Field(
        default=None,
        description="User involved in an assignment change story.",
    )
    follower: NameGid | None = Field(
        default=None,
        description="User involved in a follower add/remove story.",
    )
    new_section: NameGid | None = Field(
        default=None,
        description="Section the task was moved to.",
    )
    old_section: NameGid | None = Field(
        default=None,
        description="Section the task was moved from.",
    )
    new_approval_status: str | None = Field(
        default=None,
        description="New approval status after a status change.",
    )
    old_approval_status: str | None = Field(
        default=None,
        description="Previous approval status before a status change.",
    )
    duplicate_of: NameGid | None = Field(
        default=None,
        description="Task this task was marked as a duplicate of.",
    )
    duplicated_from: NameGid | None = Field(
        default=None,
        description="Task this task was duplicated from.",
    )
    task: NameGid | None = Field(
        default=None,
        description="Related task in dependency stories.",
    )
    dependency: NameGid | None = Field(
        default=None,
        description="Dependency task in dependency add/remove stories.",
    )
    project: NameGid | None = Field(
        default=None,
        description="Project involved in project add/remove stories.",
    )
    tag: NameGid | None = Field(
        default=None,
        description="Tag involved in tag add/remove stories.",
    )
    custom_field: NameGid | None = Field(
        default=None,
        description="Custom field whose value changed in this story.",
    )
