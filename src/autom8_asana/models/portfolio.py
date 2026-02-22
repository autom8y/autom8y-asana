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
    name: str | None = None
    color: str | None = Field(
        default=None,
        description="Portfolio color (dark-pink, dark-green, etc.)",
    )

    # Status
    public: bool | None = None

    # Relationships
    owner: NameGid | None = None
    workspace: NameGid | None = None

    # Members
    members: list[NameGid] | None = None

    # Custom fields (complex structure)
    custom_fields: list[dict[str, Any]] | None = None
    custom_field_settings: list[dict[str, Any]] | None = None

    # Current status
    current_status_update: NameGid | None = None

    # Dates
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )

    # URLs
    permalink_url: str | None = None
