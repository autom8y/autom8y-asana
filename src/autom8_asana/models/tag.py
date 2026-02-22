"""Tag model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Tag resource model for Tier 2 clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class Tag(AsanaResource):
    """Asana Tag resource model.

    Tags are labels that can be applied to tasks for organization.
    Tags belong to a workspace and can be applied across projects.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> tag = Tag.model_validate(api_response)
        >>> print(f"Tag: {tag.name} (color: {tag.color})")
    """

    # Core identification
    resource_type: str | None = Field(default="tag")

    # Basic tag fields
    name: str | None = None
    color: str | None = Field(
        default=None,
        description="Tag color (dark-pink, dark-green, dark-blue, etc.)",
    )
    notes: str | None = None

    # Relationships
    workspace: NameGid | None = None

    # Followers
    followers: list[NameGid] | None = None

    # Timestamps
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )

    # URL
    permalink_url: str | None = None
