"""Task TTL resolution based on entity type detection.

Per FR-TTL-001 through FR-TTL-007: Entity-type-specific TTL configuration.
Per ADR-0059: Extracted from tasks.py for SRP compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig

__all__ = ["TaskTTLResolver", "TTLResolverProtocol"]


class TTLResolverProtocol(Protocol):
    """Protocol for TTL resolution strategies."""

    def resolve(self, data: dict[str, Any]) -> int:
        """Resolve TTL for given entity data.

        Args:
            data: Entity data dict from API.

        Returns:
            TTL in seconds.
        """
        ...


class TaskTTLResolver:
    """Resolves cache TTL based on entity type detection.

    Per FR-TTL-001 through FR-TTL-007.

    Priority:
    1. CacheConfig.get_entity_ttl() if available
    2. Detection-based defaults
    3. 300s default for unknown types

    TTL Values:
    - Business: 3600s (1 hour)
    - Contact/Unit: 900s (15 minutes)
    - Offer: 180s (3 minutes)
    - Process: 60s (1 minute)
    - Generic: 300s (5 minutes)

    Thread Safety: Stateless after initialization - safe for concurrent use.
    """

    def __init__(self, config: "AsanaConfig") -> None:
        """Initialize with SDK configuration.

        Args:
            config: SDK configuration with optional cache settings.
        """
        self._config = config

    def resolve(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on entity type detection.

        Per FR-TTL-001 through FR-TTL-007: Different TTLs for
        Business (3600s), Contact/Unit (900s), Offer (180s),
        Process (60s), and generic tasks (300s).

        Priority:
        1. CacheConfig.get_entity_ttl() if CacheConfig is available
        2. Detection-based defaults (hardcoded fallback)
        3. 300s default for unknown entity types

        Args:
            data: Task data dict from API.

        Returns:
            TTL in seconds.
        """
        entity_type = self._detect_entity_type(data)

        # Priority 1: Use CacheConfig.get_entity_ttl() if available (FR-TTL-006)
        if hasattr(self._config, "cache") and self._config.cache is not None:
            cache_config = self._config.cache
            if hasattr(cache_config, "get_entity_ttl"):
                if entity_type:
                    return cache_config.get_entity_ttl(entity_type)
                # No entity type detected - use default TTL
                if hasattr(cache_config, "ttl") and cache_config._ttl is not None:
                    return cache_config.ttl.default_ttl
                return 300

        # Priority 2: Fallback to canonical defaults (when CacheConfig unavailable)
        # Import here to avoid circular import at module load
        from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL

        if entity_type and entity_type.lower() in DEFAULT_ENTITY_TTLS:
            return DEFAULT_ENTITY_TTLS[entity_type.lower()]

        # FR-TTL-005: Default TTL for generic tasks
        return DEFAULT_TTL

    def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
        """Detect entity type from task data."""
        # Per TDD-registry-consolidation: Import from package to ensure bootstrap runs
        from autom8_asana.models.business import detect_entity_type_from_dict

        return detect_entity_type_from_dict(data)
