"""Team model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Team resource model for Tier 2 clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class TeamMembership(AsanaResource):
    """Membership of a user in a team.

    Returned when adding a user to a team.

    Example:
        >>> membership = TeamMembership.model_validate(api_response)
        >>> print(f"User {membership.user.name} in team {membership.team.name}")
    """

    resource_type: str | None = Field(default="team_membership")

    user: NameGid | None = None
    team: NameGid | None = None
    is_guest: bool | None = Field(
        default=None, description="Whether the user is a guest in the team"
    )
    is_limited_access: bool | None = Field(
        default=None, description="Whether the user has limited access"
    )


class Team(AsanaResource):
    """Asana Team resource model.

    Teams are groups of users within an organization workspace.
    Projects can be assigned to teams.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> team = Team.model_validate(api_response)
        >>> print(f"Team: {team.name} in {team.organization.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="team")

    # Basic team fields
    name: str | None = None
    description: str | None = None
    html_description: str | None = None

    # Relationships
    organization: NameGid | None = Field(
        default=None, description="Organization workspace"
    )

    # Visibility
    visibility: str | None = Field(
        default=None,
        description="Team visibility (secret, request_to_join, public)",
    )

    # Settings
    permalink_url: str | None = None
    edit_team_name_or_description_access_level: str | None = None
    edit_team_visibility_or_trash_team_access_level: str | None = None
    member_invite_management_access_level: str | None = None
    guest_invite_management_access_level: str | None = None
    join_request_management_access_level: str | None = None
    team_member_removal_access_level: str | None = None
