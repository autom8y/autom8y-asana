"""Cache freshness modes for controlling validation behavior."""

from __future__ import annotations

from enum import Enum


class Freshness(str, Enum):
    """Cache freshness modes for controlling staleness validation.

    Determines how cache operations validate data freshness before
    returning cached entries.

    Attributes:
        STRICT: Always validate version against source before returning.
            Guarantees up-to-date data at cost of additional API call.
        EVENTUAL: Return cached data if within TTL without validation.
            Faster but may return slightly stale data.

    Example:
        >>> from autom8_asana.cache import Freshness
        >>> # Use EVENTUAL for read-heavy operations where slight staleness is OK
        >>> cache.get_versioned("12345", EntryType.TASK, Freshness.EVENTUAL)
        >>> # Use STRICT when data must be current
        >>> cache.get_versioned("12345", EntryType.TASK, Freshness.STRICT)
    """

    STRICT = "strict"
    EVENTUAL = "eventual"
