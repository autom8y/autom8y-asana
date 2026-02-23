"""Stateless freshness evaluation policy.

Per TDD-CROSS-TIER-FRESHNESS-001: FreshnessPolicy classifies cache entries
into three states (FRESH, APPROACHING_STALE, STALE) using EntityRegistry
TTLs. The policy is a pure evaluator with no side effects.

Usage:
    from autom8_asana.cache.freshness_policy import FreshnessPolicy
    from autom8_asana.cache.models.freshness_unified import FreshnessState

    policy = FreshnessPolicy()
    classification = policy.evaluate(entry, entity_type="unit")
    if classification == FreshnessState.STALE:
        trigger_refresh()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.cache.models.entry import CacheEntry
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp
    from autom8_asana.cache.models.freshness_unified import FreshnessState

# Threshold: entry is "approaching stale" when age exceeds
# this fraction of the entity's TTL. 0.75 means at 75% of TTL,
# the entry transitions from FRESH to APPROACHING_STALE.
_DEFAULT_APPROACHING_THRESHOLD = 0.75


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Stateless evaluator for freshness classification.

    Uses EntityRegistry TTLs to classify cache entries into
    three freshness states. The approaching_threshold controls
    when entries transition from FRESH to APPROACHING_STALE.

    Thread Safety: Frozen and stateless. Safe for concurrent use.

    Attributes:
        approaching_threshold: Fraction of TTL at which an entry
            transitions from FRESH to APPROACHING_STALE.
            Default 0.75 (75% of TTL).

    Example:
        >>> from autom8_asana.cache.freshness_policy import FreshnessPolicy
        >>> policy = FreshnessPolicy()
        >>> classification = policy.evaluate(entry)
    """

    approaching_threshold: float = _DEFAULT_APPROACHING_THRESHOLD

    def evaluate(
        self,
        entry: CacheEntry,
        entity_type: str | None = None,
        now: datetime | None = None,
    ) -> FreshnessState:
        """Classify an entry's freshness.

        Decision tree:
        1. If entry has no freshness stamp -> STALE (legacy entry)
        2. If stamp has a staleness_hint -> STALE (soft-invalidated)
        3. If stamp age > entity TTL -> STALE
        4. If stamp age > entity TTL * approaching_threshold -> APPROACHING_STALE
        5. Otherwise -> FRESH

        Args:
            entry: Cache entry to evaluate.
            entity_type: Entity type name for TTL lookup. If None,
                falls back to the entry's metadata or DEFAULT_TTL.
            now: Current time for age calculation. Defaults to UTC now.

        Returns:
            FreshnessState enum value.
        """
        from autom8_asana.cache.models.freshness_unified import FreshnessState

        stamp = entry.freshness_stamp
        if stamp is None:
            return FreshnessState.STALE

        if stamp.is_soft_invalidated():
            return FreshnessState.STALE

        ttl = self._get_ttl(entry, entity_type)
        age = stamp.age_seconds(now)

        if age > ttl:
            return FreshnessState.STALE

        if age > ttl * self.approaching_threshold:
            return FreshnessState.APPROACHING_STALE

        return FreshnessState.FRESH

    def evaluate_stamp(
        self,
        stamp: FreshnessStamp,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> FreshnessState:
        """Classify freshness from a stamp and explicit TTL.

        Lower-level method for callers that already know the TTL.
        Used by DataFrameCache for aggregate freshness evaluation
        where the TTL comes from the entity type, not the CacheEntry.

        Args:
            stamp: Freshness stamp to evaluate.
            ttl_seconds: TTL in seconds.
            now: Current time. Defaults to UTC now.

        Returns:
            FreshnessState enum value.
        """
        from autom8_asana.cache.models.freshness_unified import FreshnessState

        if stamp.is_soft_invalidated():
            return FreshnessState.STALE

        age = stamp.age_seconds(now)

        if age > ttl_seconds:
            return FreshnessState.STALE

        if age > ttl_seconds * self.approaching_threshold:
            return FreshnessState.APPROACHING_STALE

        return FreshnessState.FRESH

    def _get_ttl(self, entry: CacheEntry, entity_type: str | None) -> int:
        """Resolve TTL from EntityRegistry.

        Falls back through: explicit entity_type -> entry metadata
        -> DEFAULT_TTL.

        Args:
            entry: Cache entry (may have metadata hints).
            entity_type: Explicit entity type name.

        Returns:
            TTL in seconds.
        """
        from autom8_asana.config import DEFAULT_TTL
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()

        # Try explicit entity_type parameter
        if entity_type:
            return registry.get_entity_ttl(entity_type, default=DEFAULT_TTL)

        # Try entry metadata
        et_from_meta = entry.metadata.get("entity_type")
        if et_from_meta:
            return registry.get_entity_ttl(et_from_meta, default=DEFAULT_TTL)

        # Fallback
        return entry.ttl or DEFAULT_TTL
