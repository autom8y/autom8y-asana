"""Version comparison utilities for cache staleness detection."""

from __future__ import annotations

from datetime import datetime, timezone


def compare_versions(
    cached_version: datetime | str,
    current_version: datetime | str,
) -> int:
    """Compare two versions (modified_at timestamps).

    Used for staleness detection. Versions are typically the
    `modified_at` field from Asana resources.

    Args:
        cached_version: Version stored in cache.
        current_version: Current version from source.

    Returns:
        -1 if cached < current (stale)
         0 if cached == current (current)
         1 if cached > current (should not normally happen)

    Example:
        >>> from datetime import datetime, timezone
        >>> v1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        >>> v2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
        >>> compare_versions(v1, v2)
        -1
        >>> compare_versions(v2, v1)
        1
        >>> compare_versions(v1, v1)
        0
    """
    cached = parse_version(cached_version)
    current = parse_version(current_version)

    if cached < current:
        return -1
    elif cached > current:
        return 1
    else:
        return 0


def is_stale(
    cached_version: datetime | str,
    current_version: datetime | str,
) -> bool:
    """Check if cached version is stale compared to current.

    Args:
        cached_version: Version stored in cache.
        current_version: Current version from source.

    Returns:
        True if cached version is older than current (stale).
    """
    return compare_versions(cached_version, current_version) < 0


def is_current(
    cached_version: datetime | str,
    current_version: datetime | str,
) -> bool:
    """Check if cached version is current (not stale).

    Args:
        cached_version: Version stored in cache.
        current_version: Current version from source.

    Returns:
        True if cached version is >= current version.
    """
    return compare_versions(cached_version, current_version) >= 0


def parse_version(version: datetime | str) -> datetime:
    """Parse version to datetime for comparison.

    Handles both datetime objects and ISO format strings.
    Ensures timezone-aware datetimes for consistent comparison.

    Args:
        version: Version as datetime or ISO string.

    Returns:
        Timezone-aware datetime (UTC if no timezone specified).

    Raises:
        ValueError: If string cannot be parsed as datetime.
    """
    if isinstance(version, datetime):
        if version.tzinfo is None:
            return version.replace(tzinfo=timezone.utc)
        return version

    # Parse string version
    return _parse_iso_datetime(version)


def format_version(version: datetime) -> str:
    """Format datetime as ISO string for storage.

    Args:
        version: Datetime to format.

    Returns:
        ISO 8601 formatted string.

    Example:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        >>> format_version(dt)
        '2025-01-15T10:30:00+00:00'
    """
    if version.tzinfo is None:
        version = version.replace(tzinfo=timezone.utc)
    return version.isoformat()


def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO format datetime string.

    Handles common ISO formats including those with and without
    timezone information, and the 'Z' suffix for UTC.

    Args:
        value: ISO format datetime string.

    Returns:
        Timezone-aware datetime (UTC if no timezone in string).

    Raises:
        ValueError: If string cannot be parsed.
    """
    # Handle Z suffix (common in Asana API responses)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    # Fallback for edge cases with various formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue

    raise ValueError(f"Unable to parse datetime: {value}")


def version_to_timestamp(version: datetime | str) -> float:
    """Convert version to Unix timestamp for numeric comparison.

    Args:
        version: Version as datetime or ISO string.

    Returns:
        Unix timestamp as float.
    """
    dt = parse_version(version)
    return dt.timestamp()
