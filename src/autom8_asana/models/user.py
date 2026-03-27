"""User model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class User(AsanaResource):
    """Asana User resource model.

    Represents an Asana user account. Can be the current authenticated user
    or any user in accessible workspaces.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> user = User.model_validate(api_response)
        >>> print(f"User: {user.name} ({user.email})")
    """

    # Core identification
    resource_type: str | None = Field(default="user")

    # Basic user fields
    name: str | None = Field(
        default=None,
        description="Display name of the user.",
    )
    email: str | None = Field(
        default=None,
        description="Email address of the user.",
    )

    # Profile
    photo: dict[str, Any] | None = Field(
        default=None,
        description="Photo URLs in various sizes (image_21x21, image_27x27, etc.)",
    )

    # Workspace memberships
    workspaces: list[NameGid] | None = Field(
        default=None,
        description="Workspaces the user belongs to.",
    )
