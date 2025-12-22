"""Tests for CacheProviderFactory.

Per TDD-CACHE-INTEGRATION Section 9.1: Unit tests for provider factory.
Covers all provider types, detection chain, and error cases.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from autom8_asana._defaults.cache import InMemoryCacheProvider, NullCacheProvider
from autom8_asana.cache.factory import CacheProviderFactory, create_cache_provider
from autom8_asana.config import CacheConfig
from autom8_asana.exceptions import ConfigurationError


class TestCacheProviderFactoryCreate:
    """Tests for CacheProviderFactory.create()."""

    def test_disabled_config_returns_null_provider(self) -> None:
        """When enabled=False, returns NullCacheProvider."""
        config = CacheConfig(enabled=False)

        provider = CacheProviderFactory.create(config)

        assert isinstance(provider, NullCacheProvider)

    def test_default_config_returns_memory_provider(self) -> None:
        """Default config (enabled=True, provider=None) returns InMemory."""
        config = CacheConfig(enabled=True, provider=None)

        with patch.dict(os.environ, {"ASANA_ENVIRONMENT": "development"}, clear=False):
            provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)

    def test_explicit_memory_provider(self) -> None:
        """Explicit provider='memory' returns InMemoryCacheProvider."""
        config = CacheConfig(enabled=True, provider="memory")

        provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)

    def test_explicit_none_provider(self) -> None:
        """Explicit provider='none' returns NullCacheProvider."""
        config = CacheConfig(enabled=True, provider="none")

        provider = CacheProviderFactory.create(config)

        assert isinstance(provider, NullCacheProvider)

    def test_explicit_null_provider(self) -> None:
        """Explicit provider='null' returns NullCacheProvider."""
        config = CacheConfig(enabled=True, provider="null")

        provider = CacheProviderFactory.create(config)

        assert isinstance(provider, NullCacheProvider)

    def test_provider_name_case_insensitive(self) -> None:
        """Provider name is case insensitive."""
        config_upper = CacheConfig(enabled=True, provider="MEMORY")
        config_mixed = CacheConfig(enabled=True, provider="MeMoRy")

        provider_upper = CacheProviderFactory.create(config_upper)
        provider_mixed = CacheProviderFactory.create(config_mixed)

        assert isinstance(provider_upper, InMemoryCacheProvider)
        assert isinstance(provider_mixed, InMemoryCacheProvider)

    def test_redis_without_host_raises_error(self) -> None:
        """Redis provider without REDIS_HOST raises ConfigurationError."""
        config = CacheConfig(enabled=True, provider="redis")

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                CacheProviderFactory.create(config)

        assert "REDIS_HOST" in str(exc_info.value)
        assert "redis" in str(exc_info.value).lower()

    def test_tiered_without_host_raises_error(self) -> None:
        """Tiered provider without REDIS_HOST raises ConfigurationError."""
        config = CacheConfig(enabled=True, provider="tiered")

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                CacheProviderFactory.create(config)

        assert "REDIS_HOST" in str(exc_info.value)
        assert "tiered" in str(exc_info.value).lower()

    def test_unknown_provider_raises_error(self) -> None:
        """Unknown provider name raises ConfigurationError."""
        config = CacheConfig(enabled=True, provider="unknown_provider")

        with pytest.raises(ConfigurationError) as exc_info:
            CacheProviderFactory.create(config)

        assert "unknown_provider" in str(exc_info.value)
        assert "Valid options" in str(exc_info.value)

    def test_memory_provider_uses_config_ttl(self) -> None:
        """Memory provider uses TTL from config."""
        config = CacheConfig(enabled=True, provider="memory")
        config._ttl = config.ttl  # Access to set default_ttl
        config.ttl.default_ttl = 600

        provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)
        assert provider._default_ttl == 600


class TestCacheProviderFactoryAutoDetect:
    """Tests for CacheProviderFactory._auto_detect()."""

    def test_development_env_uses_memory(self) -> None:
        """Development environment uses InMemoryCacheProvider."""
        config = CacheConfig(enabled=True, provider=None)

        with patch.dict(
            os.environ,
            {"ASANA_ENVIRONMENT": "development"},
            clear=True,
        ):
            provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)

    def test_test_env_uses_memory(self) -> None:
        """Test environment uses InMemoryCacheProvider."""
        config = CacheConfig(enabled=True, provider=None)

        with patch.dict(
            os.environ,
            {"ASANA_ENVIRONMENT": "test"},
            clear=True,
        ):
            provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)

    def test_no_env_defaults_to_development_memory(self) -> None:
        """No environment variable defaults to InMemoryCacheProvider."""
        config = CacheConfig(enabled=True, provider=None)

        with patch.dict(os.environ, {}, clear=True):
            provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)

    def test_production_without_redis_falls_back_to_memory(self) -> None:
        """Production without REDIS_HOST falls back to InMemory with warning."""
        config = CacheConfig(enabled=True, provider=None)

        with patch.dict(
            os.environ,
            {"ASANA_ENVIRONMENT": "production"},
            clear=True,
        ):
            provider = CacheProviderFactory.create(config)

        # Should fall back to memory without raising
        assert isinstance(provider, InMemoryCacheProvider)

    def test_staging_without_redis_falls_back_to_memory(self) -> None:
        """Staging without REDIS_HOST falls back to InMemory."""
        config = CacheConfig(enabled=True, provider=None)

        with patch.dict(
            os.environ,
            {"ASANA_ENVIRONMENT": "staging"},
            clear=True,
        ):
            provider = CacheProviderFactory.create(config)

        assert isinstance(provider, InMemoryCacheProvider)


class TestCreateCacheProviderFunction:
    """Tests for create_cache_provider() convenience function."""

    def test_explicit_provider_takes_precedence(self) -> None:
        """Explicit provider overrides config settings."""
        config = CacheConfig(enabled=True, provider="memory")
        explicit_provider = NullCacheProvider()

        result = create_cache_provider(config, explicit_provider=explicit_provider)

        assert result is explicit_provider

    def test_none_explicit_uses_factory(self) -> None:
        """None explicit_provider delegates to factory."""
        config = CacheConfig(enabled=True, provider="none")

        result = create_cache_provider(config, explicit_provider=None)

        assert isinstance(result, NullCacheProvider)

    def test_disabled_config_with_explicit_uses_explicit(self) -> None:
        """Even with disabled config, explicit provider wins."""
        config = CacheConfig(enabled=False)
        explicit_provider = InMemoryCacheProvider()

        result = create_cache_provider(config, explicit_provider=explicit_provider)

        assert result is explicit_provider


class TestCacheConfigFromEnv:
    """Tests for CacheConfig.from_env()."""

    def test_default_values_when_no_env(self) -> None:
        """Default values when no environment variables set."""
        with patch.dict(os.environ, {}, clear=True):
            config = CacheConfig.from_env()

        assert config.enabled is True
        assert config.provider is None
        assert config.ttl.default_ttl == 300

    def test_cache_enabled_false(self) -> None:
        """ASANA_CACHE_ENABLED=false disables caching."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_ENABLED": "false"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.enabled is False

    def test_cache_enabled_zero(self) -> None:
        """ASANA_CACHE_ENABLED=0 disables caching."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_ENABLED": "0"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.enabled is False

    def test_cache_enabled_no(self) -> None:
        """ASANA_CACHE_ENABLED=no disables caching."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_ENABLED": "no"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.enabled is False

    def test_cache_enabled_true(self) -> None:
        """ASANA_CACHE_ENABLED=true enables caching."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_ENABLED": "true"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.enabled is True

    def test_cache_provider_from_env(self) -> None:
        """ASANA_CACHE_PROVIDER sets provider."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_PROVIDER": "memory"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.provider == "memory"

    def test_cache_provider_lowercased(self) -> None:
        """ASANA_CACHE_PROVIDER is lowercased."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_PROVIDER": "MEMORY"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.provider == "memory"

    def test_cache_ttl_from_env(self) -> None:
        """ASANA_CACHE_TTL_DEFAULT sets default TTL."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_TTL_DEFAULT": "600"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.ttl.default_ttl == 600

    def test_invalid_ttl_uses_default(self) -> None:
        """Invalid ASANA_CACHE_TTL_DEFAULT falls back to 300."""
        with patch.dict(
            os.environ,
            {"ASANA_CACHE_TTL_DEFAULT": "not_a_number"},
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.ttl.default_ttl == 300

    def test_combined_env_vars(self) -> None:
        """Multiple environment variables work together."""
        with patch.dict(
            os.environ,
            {
                "ASANA_CACHE_ENABLED": "true",
                "ASANA_CACHE_PROVIDER": "memory",
                "ASANA_CACHE_TTL_DEFAULT": "900",
            },
            clear=True,
        ):
            config = CacheConfig.from_env()

        assert config.enabled is True
        assert config.provider == "memory"
        assert config.ttl.default_ttl == 900


class TestCacheConfigDefaults:
    """Tests for CacheConfig default values and properties."""

    def test_default_enabled(self) -> None:
        """Default enabled is True."""
        config = CacheConfig()
        assert config.enabled is True

    def test_default_provider_is_none(self) -> None:
        """Default provider is None (auto-detect)."""
        config = CacheConfig()
        assert config.provider is None

    def test_default_dataframe_caching(self) -> None:
        """Default dataframe_caching is True."""
        config = CacheConfig()
        assert config.dataframe_caching is True

    def test_ttl_lazy_loaded(self) -> None:
        """TTL settings are lazy-loaded."""
        config = CacheConfig()
        # Access triggers lazy load
        ttl = config.ttl
        assert ttl.default_ttl == 300

    def test_overflow_lazy_loaded(self) -> None:
        """Overflow settings are lazy-loaded."""
        config = CacheConfig()
        # Access triggers lazy load
        overflow = config.overflow
        assert overflow.subtasks == 40

    def test_freshness_lazy_loaded(self) -> None:
        """Freshness mode is lazy-loaded."""
        from autom8_asana.cache.freshness import Freshness

        config = CacheConfig()
        # Access triggers lazy load
        freshness = config.freshness
        assert freshness == Freshness.EVENTUAL

    def test_ttl_setter(self) -> None:
        """TTL can be set."""
        from autom8_asana.cache.settings import TTLSettings

        config = CacheConfig()
        new_ttl = TTLSettings(default_ttl=600)
        config.ttl = new_ttl
        assert config.ttl.default_ttl == 600

    def test_overflow_setter(self) -> None:
        """Overflow can be set."""
        from autom8_asana.cache.settings import OverflowSettings

        config = CacheConfig()
        new_overflow = OverflowSettings(subtasks=100)
        config.overflow = new_overflow
        assert config.overflow.subtasks == 100

    def test_freshness_setter(self) -> None:
        """Freshness can be set."""
        from autom8_asana.cache.freshness import Freshness

        config = CacheConfig()
        config.freshness = Freshness.STRICT
        assert config.freshness == Freshness.STRICT
