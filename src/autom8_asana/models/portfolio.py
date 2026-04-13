"""Portfolio model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0004: Portfolio resource model for Tier 2 clients.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class Portfolio(AsanaResource):
    """Asana Portfolio resource model.

    Portfolios are collections of projects for high-level tracking.
    They provide rollup status and visibility across multiple projects.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> portfolio = Portfolio.model_validate(api_response)
        >>> print(f"Portfolio: {portfolio.name} by {portfolio.owner.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="portfolio")

    # Basic portfolio fields
    name: str | None = Field(
        default=None,
        description="Display name of the portfolio.",
    )
    color: str | None = Field(
        default=None,
        description="Portfolio color (dark-pink, dark-green, etc.)",
    )

    # Status
    public: bool | None = Field(
        default=None,
        description="True if the portfolio is visible to all workspace members.",
    )

    # Relationships
    owner: NameGid | None = Field(
        default=None,
        description="User who owns the portfolio.",
    )
    workspace: NameGid | None = Field(
        default=None,
        description="Workspace the portfolio belongs to.",
    )

    # Members
    members: list[NameGid] | None = Field(
        default=None,
        description="Users who are members of the portfolio.",
    )

    # Custom fields (complex structure)
    custom_fields: list[dict[str, Any]] | None = Field(
        default=None,
        description="Custom field values set on the portfolio.",
    )
    custom_field_settings: list[dict[str, Any]] | None = Field(
        default=None,
        description="Configuration of custom fields enabled on the portfolio.",
    )

    # Current status
    current_status_update: NameGid | None = Field(
        default=None,
        description="Most recent status update posted to the portfolio.",
    )

    # Dates
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")

    # URLs
    permalink_url: str | None = Field(
        default=None,
        description="Permanent URL to the portfolio in the Asana web app.",
    )
