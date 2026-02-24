"""Insights provider protocol for analytics data retrieval.

Decouples the domain model (Business) from the client layer (DataServiceClient).
Business.get_insights_async accepts any InsightsProvider instead of requiring
a concrete DataServiceClient import.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from datetime import date

    from autom8_asana.clients.data.models import InsightsResponse


class InsightsProvider(Protocol):
    """Protocol for fetching analytics insights.

    Any object that implements get_insights_async with this signature
    satisfies the protocol via structural typing. DataServiceClient
    is the primary implementation.

    Example:
        async def fetch(provider: InsightsProvider) -> None:
            response = await provider.get_insights_async(
                factory="account",
                office_phone="+17705753103",
                vertical="chiropractic",
            )
    """

    async def get_insights_async(
        self,
        factory: str,
        office_phone: str,
        vertical: str,
        *,
        period: str = "lifetime",
        start_date: date | None = None,
        end_date: date | None = None,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        groups: list[str] | None = None,
        break_down: list[str] | None = None,
        refresh: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> InsightsResponse:
        """Fetch analytics insights for a business.

        Args:
            factory: InsightsFactory name (e.g., "account", "ads").
            office_phone: E.164 formatted phone number.
            vertical: Business vertical (e.g., "chiropractic", "dental").
            period: Time period preset (default: "lifetime").
            start_date: Custom start date (overrides period).
            end_date: Custom end date (overrides period).
            metrics: Override default metrics.
            dimensions: Override default dimensions.
            groups: Additional grouping columns.
            break_down: Break down results by columns.
            refresh: Force cache refresh.
            filters: Additional factory-specific filters.

        Returns:
            InsightsResponse with data, metadata, and DataFrame methods.
        """
        ...
