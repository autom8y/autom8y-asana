"""Shared datetime parsing utilities for cache subsystems."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso_datetime(
    value: str | None, *, default_now: bool = True
) -> datetime | None:
    """Parse ISO datetime string with Z-suffix handling.

    Args:
        value: ISO format datetime string, or None.
        default_now: If True, return datetime.now(UTC) when value is
            None/unparseable. If False, return None.

    Returns:
        Timezone-aware UTC datetime, or None/now per default_now flag.
    """
    if not value:
        return datetime.now(UTC) if default_now else None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return datetime.now(UTC) if default_now else None
