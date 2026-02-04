"""Freshness metadata for cache entries.

Per TDD-CROSS-TIER-FRESHNESS-001: FreshnessStamp carries verification
provenance through all cache tiers, enabling consumers to determine
data age without requiring an API call.

The stamp is a frozen dataclass that travels with CacheEntry through
Redis, S3, and tiered promotion. FreshnessPolicy uses stamps to
classify entries as FRESH, APPROACHING_STALE, or STALE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class VerificationSource(str, Enum):
    """How the data was verified as fresh.

    Tracking the source of a freshness verification allows
    downstream consumers to weight freshness differently.
    An API_FETCH is a strong signal; a MUTATION_EVENT is
    an inference (we know the mutation happened, so the data
    we just wrote must be current).
    """

    API_FETCH = "api_fetch"
    BATCH_CHECK = "batch_check"
    MUTATION_EVENT = "mutation_event"
    CACHE_WARM = "cache_warm"
    PROMOTION = "promotion"
    UNKNOWN = "unknown"


class FreshnessClassification(str, Enum):
    """Result of evaluating a FreshnessStamp against policy.

    Three-state classification enables graduated responses:
    - FRESH: Serve without concern
    - APPROACHING_STALE: Serve, but consider background refresh
    - STALE: Serve with degradation warning, or reject
    """

    FRESH = "fresh"
    APPROACHING_STALE = "approaching_stale"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class FreshnessStamp:
    """Freshness metadata attached to a cached entry.

    Frozen for thread safety and to maintain CacheEntry immutability.
    Created at cache-write time and propagated through tiers.

    Attributes:
        last_verified_at: UTC timestamp when data was last confirmed
            as current (from API fetch, batch check, or mutation event).
        source: How the freshness was established. Enables consumers
            to weight freshness signals differently.
        staleness_hint: If not None, indicates this entry has been
            soft-invalidated. The hint is a human-readable reason
            (e.g., "mutation:task:update:1234567890"). Entries with
            a staleness_hint are candidates for background refresh
            but can still be served.

    Example:
        >>> stamp = FreshnessStamp(
        ...     last_verified_at=datetime.now(UTC),
        ...     source=VerificationSource.API_FETCH,
        ... )
        >>> stamp.age_seconds()
        0.001
    """

    last_verified_at: datetime
    source: VerificationSource = VerificationSource.UNKNOWN
    staleness_hint: str | None = None

    def age_seconds(self, now: datetime | None = None) -> float:
        """Seconds since last verification.

        Args:
            now: Current time for comparison. Defaults to UTC now.

        Returns:
            Age in seconds as a float.
        """
        now = now or datetime.now(UTC)
        verified = self.last_verified_at
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return (now - verified).total_seconds()

    def is_soft_invalidated(self) -> bool:
        """True if this entry was soft-invalidated (stale but available)."""
        return self.staleness_hint is not None

    def with_staleness_hint(self, hint: str) -> FreshnessStamp:
        """Create a new stamp with a staleness hint applied.

        Does not mutate -- returns a new frozen instance.

        Args:
            hint: Reason for soft invalidation.

        Returns:
            New FreshnessStamp with the hint set.
        """
        return FreshnessStamp(
            last_verified_at=self.last_verified_at,
            source=self.source,
            staleness_hint=hint,
        )

    @classmethod
    def now(
        cls,
        source: VerificationSource = VerificationSource.UNKNOWN,
    ) -> FreshnessStamp:
        """Create a stamp verified at the current moment.

        Convenience factory for the common case of "data is fresh
        as of right now."

        Args:
            source: How freshness was established.

        Returns:
            New FreshnessStamp with last_verified_at=now.
        """
        return cls(
            last_verified_at=datetime.now(UTC),
            source=source,
        )
