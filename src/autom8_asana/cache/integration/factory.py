"""Cache provider factory with environment-aware selection.

Per TDD-CACHE-INTEGRATION Section 4.2: Environment-aware provider instantiation.
Per ADR-0123: Detection chain priority for provider selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.settings import get_settings

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.cache.models.freshness_unified import FreshnessIntent
    from autom8_asana.cache.providers.unified import UnifiedTaskStore
    from autom8_asana.config import CacheConfig
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)


class CacheProviderFactory:
    """Factory for creating cache providers based on configuration.

    Per ADR-0123, selection priority:
        1. Explicit cache_provider parameter (handled in AsanaClient)
        2. CacheConfig.enabled=False -> NullCacheProvider
        3. CacheConfig.provider setting (if not None)
        4. Environment-based auto-detection (AUTOM8Y_ENV)
        5. InMemoryCacheProvider fallback

    Environment Detection (per FR-DEFAULT-005, FR-DEFAULT-006):
        - AUTOM8Y_ENV=production/staging: Prefer Redis if REDIS_HOST configured
        - AUTOM8Y_ENV=local/test or not set: Use InMemory

    Example:
        >>> from autom8_asana.config import CacheConfig
        >>> config = CacheConfig(enabled=True, provider="memory")
        >>> provider = CacheProviderFactory.create(config)
        >>> # provider is InMemoryCacheProvider
    """

    @staticmethod
    def create(config: CacheConfig) -> CacheProvider:
        """Create a cache provider based on configuration.

        Per FR-DEFAULT-002: Priority order for provider selection.

        Args:
            config: CacheConfig with provider settings.

        Returns:
            Configured CacheProvider instance.

        Raises:
            ConfigurationError: If explicit provider requires
                configuration that is missing (e.g., redis without REDIS_HOST).
        """
        from autom8_asana._defaults.cache import NullCacheProvider

        # FR-DEFAULT-004: Master enable/disable switch
        if not config.enabled:
            logger.debug("Cache disabled via config.enabled=False")
            return NullCacheProvider()

        # FR-DEFAULT-003: Explicit provider selection
        if config.provider:
            return CacheProviderFactory._create_explicit(config.provider, config)

        # FR-DEFAULT-005, FR-DEFAULT-006: Environment-based auto-detection
        return CacheProviderFactory._auto_detect(config)

    @staticmethod
    def _create_explicit(provider_name: str, config: CacheConfig) -> CacheProvider:
        """Create explicitly specified provider.

        Args:
            provider_name: Provider name ("memory", "redis", "tiered", "none").
            config: CacheConfig for TTL and other settings.

        Returns:
            Configured CacheProvider.

        Raises:
            ConfigurationError: If provider requires missing configuration.
        """
        from autom8_asana._defaults.cache import (
            InMemoryCacheProvider,
            NullCacheProvider,
        )
        from autom8_asana.errors import ConfigurationError

        provider_name = provider_name.lower()

        if provider_name in ("none", "null"):
            logger.debug("using_null_cache_provider", provider_name=provider_name)
            return NullCacheProvider()

        if provider_name == "memory":
            settings = get_settings()
            logger.debug(
                "using_inmemory_cache_provider",
                default_ttl=config.ttl.default_ttl,
                max_size=settings.cache.memory_max_size,
            )
            return InMemoryCacheProvider(
                default_ttl=config.ttl.default_ttl,
                max_size=settings.cache.memory_max_size,
            )

        if provider_name == "redis":
            settings = get_settings()
            if not settings.redis_available:
                raise ConfigurationError(
                    "ASANA_CACHE_PROVIDER=redis requires REDIS_HOST environment variable"
                )
            return CacheProviderFactory._create_redis_provider(config)

        if provider_name == "tiered":
            settings = get_settings()
            if not settings.redis_available:
                raise ConfigurationError(
                    "ASANA_CACHE_PROVIDER=tiered requires REDIS_HOST environment variable"
                )
            return CacheProviderFactory._create_tiered_provider(config)

        raise ConfigurationError(
            f"Unknown cache provider: '{provider_name}'. Valid options: memory, redis, tiered, none"
        )

    @staticmethod
    def _auto_detect(config: CacheConfig) -> CacheProvider:
        """Auto-detect provider based on environment.

        Per FR-DEFAULT-005: Production/staging prefers Redis if available.
        Per FR-DEFAULT-006: Development/test uses InMemory.

        Args:
            config: CacheConfig for TTL and other settings.

        Returns:
            Appropriate CacheProvider for the environment.
        """
        from autom8_asana._defaults.cache import InMemoryCacheProvider

        settings = get_settings()
        redis_available = settings.redis_available
        max_size = settings.cache.memory_max_size

        if settings.is_production:
            if redis_available:
                logger.info(
                    "Production environment with Redis configured, using RedisCacheProvider"
                )
                return CacheProviderFactory._create_redis_provider(config)
            else:
                logger.warning(
                    "Production environment without REDIS_HOST configured. "
                    "Using InMemoryCacheProvider as fallback. "
                    "Set REDIS_HOST for production-grade caching or "
                    "ASANA_CACHE_PROVIDER=none to disable caching."
                )
                return InMemoryCacheProvider(
                    default_ttl=config.ttl.default_ttl,
                    max_size=max_size,
                )
        else:
            # Development/test: use in-memory
            logger.debug(
                "dev_using_inmemory_cache_provider",
                default_ttl=config.ttl.default_ttl,
                max_size=max_size,
            )
            return InMemoryCacheProvider(
                default_ttl=config.ttl.default_ttl,
                max_size=max_size,
            )

    @staticmethod
    def _create_redis_provider(config: CacheConfig) -> CacheProvider:
        """Create Redis cache provider from environment.

        Uses REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL
        environment variables via existing autom8_adapter.

        Args:
            config: CacheConfig for TTL settings.

        Returns:
            RedisCacheProvider instance.
        """
        from autom8_asana.cache.integration.autom8_adapter import (
            create_autom8_cache_provider,
        )

        logger.info("Creating Redis cache provider from environment")
        return create_autom8_cache_provider()

    @staticmethod
    def _create_tiered_provider(config: CacheConfig) -> CacheProvider:
        """Create tiered cache provider (Redis hot + S3 cold).

        Uses existing TieredCacheProvider infrastructure.
        For Phase 1, tiered maps to Redis (S3 cold tier is Phase 3).

        Args:
            config: CacheConfig for TTL settings.

        Returns:
            TieredCacheProvider instance (currently Redis-only).
        """
        # For Phase 1, tiered maps to Redis (S3 cold tier is Phase 3)
        logger.info("Creating tiered cache provider (Redis-only for Phase 1)")
        return CacheProviderFactory._create_redis_provider(config)

    @staticmethod
    def create_unified_store(
        config: CacheConfig,
        batch_client: BatchClient | None = None,
        freshness_mode: FreshnessIntent | None = None,
    ) -> UnifiedTaskStore:
        """Create unified task store with environment-aware provider selection.

        Uses the same detection chain as create() for provider selection.

        Args:
            config: CacheConfig with provider settings.
            batch_client: Optional BatchClient for freshness checks.
            freshness_mode: Default freshness mode.

        Returns:
            UnifiedTaskStore configured for the environment.
        """
        from autom8_asana.cache.models.freshness_unified import FreshnessIntent
        from autom8_asana.cache.providers.unified import UnifiedTaskStore

        # Use same provider selection logic as create()
        cache_provider = CacheProviderFactory.create(config)

        # Default to EVENTUAL if not specified
        if freshness_mode is None:
            freshness_mode = FreshnessIntent.EVENTUAL

        # Create and return unified store
        return UnifiedTaskStore(
            cache=cache_provider,
            batch_client=batch_client,
            freshness_mode=freshness_mode,
        )


def create_cache_provider(
    config: CacheConfig,
    explicit_provider: CacheProvider | None = None,
) -> CacheProvider:
    """Create cache provider using detection chain.

    Convenience function that handles explicit provider override.
    Per ADR-0123: Priority order:
    1. Explicit provider parameter (always wins)
    2. Factory-based selection from config

    Args:
        config: CacheConfig with provider settings.
        explicit_provider: Optional explicit provider (overrides config).

    Returns:
        CacheProvider instance.

    Example:
        >>> from autom8_asana.config import CacheConfig
        >>> config = CacheConfig(enabled=True)
        >>> provider = create_cache_provider(config)
    """
    if explicit_provider is not None:
        logger.debug(
            "using_explicit_cache_provider",
            provider_type=type(explicit_provider).__name__,
        )
        return explicit_provider

    return CacheProviderFactory.create(config)
