"""Goal model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Goal resource models for Tier 2 clients (Goal, GoalMetric, GoalMembership).
"""

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource
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
    precision: int | None = Field(default=None, description="Decimal precision")
    currency_code: str | None = None

    # Values
    current_number_value: float | None = None
    target_number_value: float | None = None
    initial_number_value: float | None = None

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
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status
    status: str | None = Field(
        default=None,
        description="Goal status (on_track, at_risk, off_track, achieved, partial, missed, dropped)",
    )
    is_workspace_level: bool | None = None

    # Time period
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    time_period: NameGid | None = Field(
        default=None, description="Associated time period"
    )

    # Relationships
    owner: NameGid | None = None
    workspace: NameGid | None = None
    team: NameGid | None = None

    # Followers and likes
    followers: list[NameGid] | None = None
    liked: bool | None = None
    likes: list[NameGid] | None = None
    num_likes: int | None = None

    # Metric tracking
    metric: GoalMetric | None = None
    current_status_update: NameGid | None = None

    # URLs
    permalink_url: str | None = None


class GoalMembership(AsanaResource):
    """Membership of a user or team in a goal.

    Example:
        >>> membership = GoalMembership.model_validate(api_response)
        >>> print(f"{membership.member.name} is {membership.role} of goal")
    """

    resource_type: str | None = Field(default="goal_membership")

    member: NameGid | None = None
    goal: NameGid | None = None
    role: str | None = Field(
        default=None, description="Member role (owner, editor, commenter)"
    )
