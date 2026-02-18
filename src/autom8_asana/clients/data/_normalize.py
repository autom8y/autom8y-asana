"""Period normalization for DataServiceClient.

Private module providing a pure function for mapping autom8_asana period
values to autom8_data's expected format. Zero dependency on instance state.

This function is NOT part of the public API.
"""

from __future__ import annotations


def normalize_period(insights_period: str | None) -> str:
    """Normalize insights_period to autom8_data's period format.

    Maps autom8_asana's period values to autom8_data's expected format:
    - "lifetime" -> "LIFETIME"
    - "t7", "l7" -> "T7"
    - "t14", "l14" -> "T14"
    - "t30", "l30" -> "T30"
    - "quarter" -> "QUARTER"
    - "month" -> "MONTH"
    - "week" -> "WEEK"

    Args:
        insights_period: Period value from InsightsRequest.

    Returns:
        Normalized period string for autom8_data API.

    Note:
        autom8_data supports T7, T14, T30, LIFETIME, QUARTER, MONTH, WEEK.
        Other period values default to T30 for backward compatibility.
    """
    if insights_period is None:
        return "LIFETIME"

    period_lower = insights_period.lower()

    # Handle lifetime case-insensitively
    if period_lower == "lifetime":
        return "LIFETIME"

    # Map trailing/last day periods to autom8_data format
    if period_lower in ("t7", "l7"):
        return "T7"
    elif period_lower in ("t14", "l14"):
        return "T14"
    elif period_lower in ("t30", "l30"):
        return "T30"
    elif period_lower == "quarter":
        return "QUARTER"
    elif period_lower == "month":
        return "MONTH"
    elif period_lower == "week":
        return "WEEK"

    # Default to T30 for other values (backward compatibility)
    return "T30"
