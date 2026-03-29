"""Goal model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Goal resource models for Tier 2 clients (Goal, GoalMetric, GoalMembership).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class GoalMetric(AsanaResource):
    """Metric for tracking goal progress.

    Goals can have numeric metrics with current and target values.

    Example:
        >>> metric = GoalMetric.model_validate(api_response)
        >>> if metric.target_number_value:
        ...     progress = metric.current_number_value / metric.target_number_value
    """

    resource_type: str | None = Field(default="goal_metric")
    resource_subtype: str | None = Field(
        default=None,
        description="Metric type (number, percentage, currency)",
    )

    # Metric configuration
    unit: str | None = Field(default=None, description="Unit of measurement")
    precision: int | None = Field(default=None, ge=0, description="Decimal precision")
    currency_code: str | None = Field(
        default=None,
        description="ISO 4217 currency code for currency-type metrics (e.g., USD, EUR).",
    )

    # Values
    current_number_value: float | None = Field(
        default=None,
        description="Current metric value representing progress toward the goal.",
    )
    target_number_value: float | None = Field(
        default=None,
        description="Target value that indicates the goal is achieved.",
    )
    initial_number_value: float | None = Field(
        default=None,
        description="Starting baseline value when the goal was created.",
    )

    # Progress
    progress_source: str | None = Field(
        default=None,
        description="How progress is calculated (manual, subgoal_progress, etc.)",
    )


class Goal(AsanaResource):
    """Asana Goal resource model.

    Goals track high-level objectives. They can be hierarchical
    (goals can have subgoals) and time-bound.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> goal = Goal.model_validate(api_response)
        >>> print(f"Goal: {goal.name} ({goal.status})")
    """

    # Core identification
    resource_type: str | None = Field(default="goal")

    # Basic goal fields
    name: str | None = Field(
        default=None,
        description="Display name of the goal.",
    )
    notes: str | None = Field(
        default=None,
        description="Plain-text description body of the goal.",
    )
    html_notes: str | None = Field(
        default=None,
        description="HTML-formatted description body of the goal.",
    )

    # Status
    status: str | None = Field(
        default=None,
        description="Goal status (on_track, at_risk, off_track, achieved, partial, missed, dropped)",
    )
    is_workspace_level: bool | None = Field(
        default=None,
        description="True if the goal is scoped to the entire workspace rather than a team.",
    )

    # Time period
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    time_period: NameGid | None = Field(
        default=None, description="Associated time period"
    )

    # Relationships
    owner: NameGid | None = Field(
        default=None,
        description="User who owns the goal.",
    )
    workspace: NameGid | None = Field(
        default=None,
        description="Workspace the goal belongs to.",
    )
    team: NameGid | None = Field(
        default=None,
        description="Team the goal is scoped to, if team-level.",
    )

    # Followers and likes
    followers: list[NameGid] | None = Field(
        default=None,
        description="Users following the goal for status update notifications.",
    )
    liked: bool | None = Field(
        default=None,
        description="True if the authenticated user has liked the goal.",
    )
    likes: list[NameGid] | None = Field(
        default=None,
        description="Users who have liked the goal.",
    )
    num_likes: int | None = Field(
        default=None,
        ge=0,
        description="Number of likes on the goal.",
    )

    # Metric tracking
    metric: GoalMetric | None = Field(
        default=None,
        description="Numeric metric tracking progress toward the goal.",
    )
    current_status_update: NameGid | None = Field(
        default=None,
        description="Most recent status update posted to the goal.",
    )

    # URLs
    permalink_url: str | None = Field(
        default=None,
        description="Permanent URL to the goal in the Asana web app.",
    )


class GoalMembership(AsanaResource):
    """Membership of a user or team in a goal.

    Example:
        >>> membership = GoalMembership.model_validate(api_response)
        >>> print(f"{membership.member.name} is {membership.role} of goal")
    """

    resource_type: str | None = Field(default="goal_membership")

    member: NameGid | None = Field(
        default=None,
        description="User or team that is a member of the goal.",
    )
    goal: NameGid | None = Field(
        default=None,
        description="Goal this membership belongs to.",
    )
    role: str | None = Field(
        default=None, description="Member role (owner, editor, commenter)"
    )
