"""Story model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Story resource model for Tier 2 clients (comments and activity).
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
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
    target: NameGid | None = Field(
        default=None, description="Task this story is on"
    )
    created_by: NameGid | None = None

    # Timestamps
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )

    # Editing
    is_editable: bool | None = None
    is_edited: bool | None = None
    is_pinned: bool | None = None

    # Reactions
    liked: bool | None = None
    likes: list[NameGid] | None = None
    num_likes: int | None = None

    # Sticker (for sticker stories)
    sticker_name: str | None = None

    # For system stories, these track what changed
    new_text_value: str | None = None
    old_text_value: str | None = None
    new_name: str | None = None
    old_name: str | None = None
    new_number_value: float | None = None
    old_number_value: float | None = None
    new_enum_value: NameGid | None = None
    old_enum_value: NameGid | None = None
    new_dates: dict[str, Any] | None = None
    old_dates: dict[str, Any] | None = None
    new_resource_subtype: str | None = None
    old_resource_subtype: str | None = None
    assignee: NameGid | None = None
    follower: NameGid | None = None
    new_section: NameGid | None = None
    old_section: NameGid | None = None
    new_approval_status: str | None = None
    old_approval_status: str | None = None
    duplicate_of: NameGid | None = None
    duplicated_from: NameGid | None = None
    task: NameGid | None = None  # For dependency stories
    dependency: NameGid | None = None
    project: NameGid | None = None  # For project stories
    tag: NameGid | None = None  # For tag stories
    custom_field: NameGid | None = None  # For custom field stories
