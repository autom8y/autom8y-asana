"""Tests for Pydantic Settings module.

Verifies:
- Loading from environment variables with correct prefixes
- Default values
- Singleton behavior
- Reset functionality for testing
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


class TestAsanaSettings:
    """Tests for AsanaSettings configuration."""

    def test_default_values(self) -> None:
        """Test default values when no env vars set."""
        from autom8_asana.settings import AsanaSettings

        with patch.dict(os.environ, {}, clear=True):
            settings = AsanaSettings()

        assert settings.pat is None
        assert settings.workspace_gid is None
        assert settings.base_url == "https://app.asana.com/api/1.0"
        assert settings.strict_config is False

    def test_loads_from_env_vars(self) -> None:
        """Test loading values from environment variables."""
        from autom8_asana.settings import AsanaSettings

        env = {
            "ASANA_PAT": "test_token_123",
            "ASANA_WORKSPACE_GID": "1234567890123456",
            "ASANA_BASE_URL": "https://custom.api.com/v1",
            "ASANA_STRICT_CONFIG": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = AsanaSettings()

        assert settings.pat is not None
        assert settings.pat.get_secret_value() == "test_token_123"
        assert settings.workspace_gid == "1234567890123456"
        assert settings.base_url == "https://custom.api.com/v1"
        assert settings.strict_config is True

    def test_strict_config_false_values(self) -> None:
        """Test strict_config with various false representations."""
        from autom8_asana.settings import AsanaSettings

        for value in ["false", "False", "FALSE", "0", "no"]:
            with patch.dict(os.environ, {"ASANA_STRICT_CONFIG": value}, clear=True):
                settings = AsanaSettings()
                assert settings.strict_config is False, f"Failed for value: {value}"


class TestCacheSettings:
    """Tests for CacheSettings configuration."""

    def test_default_values(self) -> None:
        """Test default cache settings."""
        from autom8_asana.settings import CacheSettings

        with patch.dict(os.environ, {}, clear=True):
            settings = CacheSettings()

        assert settings.enabled is True
        assert settings.provider is None
        assert settings.ttl_default == 300

    def test_loads_from_env_vars(self) -> None:
        """Test loading cache settings from environment."""
        from autom8_asana.settings import CacheSettings

        env = {
            "ASANA_CACHE_ENABLED": "false",
            "ASANA_CACHE_PROVIDER": "redis",
            "ASANA_CACHE_TTL_DEFAULT": "600",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = CacheSettings()

        assert settings.enabled is False
        assert settings.provider == "redis"
        assert settings.ttl_default == 600

    def test_provider_normalization(self) -> None:
        """Test provider name is normalized to lowercase."""
        from autom8_asana.settings import CacheSettings

        for value in ["REDIS", "Redis", "MEMORY", "Tiered"]:
            with patch.dict(os.environ, {"ASANA_CACHE_PROVIDER": value}, clear=True):
                settings = CacheSettings()
                assert settings.provider == value.lower()

    def test_empty_provider_becomes_none(self) -> None:
        """Test empty provider string becomes None."""
        from autom8_asana.settings import CacheSettings

        with patch.dict(os.environ, {"ASANA_CACHE_PROVIDER": ""}, clear=True):
            settings = CacheSettings()
            assert settings.provider is None


class TestRedisSettings:
    """Tests for RedisSettings configuration."""

    def test_default_values(self) -> None:
        """Test default Redis settings."""
        from autom8_asana.settings import RedisSettings

        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

        assert settings.host is None
        assert settings.port == 6379
        assert settings.password is None
        assert settings.ssl is True

    def test_loads_from_env_vars(self) -> None:
        """Test loading Redis settings from environment."""
        from autom8_asana.settings import RedisSettings

        env = {
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "secret123",
            "REDIS_SSL": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

        assert settings.host == "redis.example.com"
        assert settings.port == 6380
        assert settings.password is not None
        assert settings.password.get_secret_value() == "secret123"
        assert settings.ssl is False

    def test_ssl_parsing_variants(self) -> None:
        """Test SSL setting parses various true/false representations."""
        from autom8_asana.settings import RedisSettings

        true_values = ["true", "True", "TRUE", "1", "yes"]
        for value in true_values:
            with patch.dict(os.environ, {"REDIS_SSL": value}, clear=True):
                settings = RedisSettings()
                assert settings.ssl is True, f"Failed for value: {value}"

        false_values = ["false", "False", "FALSE", "0", "no"]
        for value in false_values:
            with patch.dict(os.environ, {"REDIS_SSL": value}, clear=True):
                settings = RedisSettings()
                assert settings.ssl is False, f"Failed for value: {value}"


class TestEnvironmentSettings:
    """Tests for EnvironmentSettings configuration."""

    def test_default_environment(self) -> None:
        """Test default environment is development."""
        from autom8_asana.settings import EnvironmentSettings

        with patch.dict(os.environ, {}, clear=True):
            settings = EnvironmentSettings()

        assert settings.environment == "development"

    def test_valid_environments(self) -> None:
        """Test valid environment values are accepted."""
        from autom8_asana.settings import EnvironmentSettings

        for env_value in ["development", "production", "staging", "test"]:
            with patch.dict(os.environ, {"ASANA_ENVIRONMENT": env_value}, clear=True):
                settings = EnvironmentSettings()
                assert settings.environment == env_value

    def test_environment_normalization(self) -> None:
        """Test environment names are normalized to lowercase."""
        from autom8_asana.settings import EnvironmentSettings

        for env_value in ["PRODUCTION", "Production", "STAGING", "Test"]:
            with patch.dict(os.environ, {"ASANA_ENVIRONMENT": env_value}, clear=True):
                settings = EnvironmentSettings()
                assert settings.environment == env_value.lower()

    def test_unknown_environment_defaults_to_development(self) -> None:
        """Test unknown environment values fall back to development."""
        from autom8_asana.settings import EnvironmentSettings

        with patch.dict(os.environ, {"ASANA_ENVIRONMENT": "unknown"}, clear=True):
            settings = EnvironmentSettings()
            assert settings.environment == "development"


class TestSettings:
    """Tests for combined Settings container."""

    def test_aggregates_subsettings(self) -> None:
        """Test Settings contains all subsetting objects."""
        from autom8_asana.settings import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert hasattr(settings, "asana")
        assert hasattr(settings, "cache")
        assert hasattr(settings, "redis")
        assert hasattr(settings, "env")

    def test_is_production_property(self) -> None:
        """Test is_production returns True for production/staging."""
        from autom8_asana.settings import Settings

        with patch.dict(os.environ, {"AUTOM8Y_ENV": "production"}, clear=True):
            settings = Settings()
            assert settings.is_production is True

        with patch.dict(os.environ, {"AUTOM8Y_ENV": "staging"}, clear=True):
            settings = Settings()
            assert settings.is_production is True

        with patch.dict(os.environ, {"AUTOM8Y_ENV": "local"}, clear=True):
            settings = Settings()
            assert settings.is_production is False

    def test_redis_available_property(self) -> None:
        """Test redis_available checks for host configuration."""
        from autom8_asana.settings import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.redis_available is False

        with patch.dict(os.environ, {"REDIS_HOST": "localhost"}, clear=True):
            settings = Settings()
            assert settings.redis_available is True


class TestSingleton:
    """Tests for singleton pattern and reset functionality."""

    def test_get_settings_returns_same_instance(self) -> None:
        """Test get_settings returns the same instance on repeated calls."""
        from autom8_asana.settings import get_settings, reset_settings

        reset_settings()  # Ensure clean state

        with patch.dict(os.environ, {}, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()

        assert settings1 is settings2

    def test_reset_settings_clears_cache(self) -> None:
        """Test reset_settings forces re-creation on next call."""
        from autom8_asana.settings import get_settings, reset_settings

        reset_settings()

        with patch.dict(os.environ, {"ASANA_CACHE_ENABLED": "false"}, clear=True):
            settings1 = get_settings()
            assert settings1.cache.enabled is False

        reset_settings()

        with patch.dict(os.environ, {"ASANA_CACHE_ENABLED": "true"}, clear=True):
            settings2 = get_settings()
            assert settings2.cache.enabled is True

        assert settings1 is not settings2

    def test_reset_settings_picks_up_env_changes(self) -> None:
        """Test that reset allows picking up changed env vars."""
        from autom8_asana.settings import get_settings, reset_settings

        reset_settings()

        with patch.dict(os.environ, {"ASANA_PAT": "token_a"}, clear=True):
            settings = get_settings()
            assert settings.asana.pat is not None
            assert settings.asana.pat.get_secret_value() == "token_a"

        # Change env and reset
        reset_settings()
        with patch.dict(os.environ, {"ASANA_PAT": "token_b"}, clear=True):
            settings = get_settings()
            assert settings.asana.pat is not None
            assert settings.asana.pat.get_secret_value() == "token_b"


class TestS3Settings:
    """Tests for S3Settings configuration."""

    def test_default_values(self) -> None:
        """Test default S3 settings."""
        from autom8_asana.settings import S3Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = S3Settings()

        assert settings.bucket == ""
        assert settings.prefix == "asana-cache"
        assert settings.region == "us-east-1"
        assert settings.endpoint_url is None

    def test_loads_from_env_vars(self) -> None:
        """Test loading S3 settings from environment."""
        from autom8_asana.settings import S3Settings

        env = {
            "ASANA_CACHE_S3_BUCKET": "my-cache-bucket",
            "ASANA_CACHE_S3_PREFIX": "custom-prefix",
            "ASANA_CACHE_S3_REGION": "eu-west-1",
            "ASANA_CACHE_S3_ENDPOINT_URL": "http://localhost:4566",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = S3Settings()

        assert settings.bucket == "my-cache-bucket"
        assert settings.prefix == "custom-prefix"
        assert settings.region == "eu-west-1"
        assert settings.endpoint_url == "http://localhost:4566"

    def test_accessible_from_main_settings(self) -> None:
        """Test S3 settings are accessible from main Settings container."""
        from autom8_asana.settings import Settings

        env = {
            "ASANA_CACHE_S3_BUCKET": "test-bucket",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.s3.bucket == "test-bucket"
        assert settings.s3.prefix == "asana-cache"


class TestCacheSettingsExtensions:
    """Tests for CacheSettings extension fields."""

    def test_memory_max_size_default(self) -> None:
        """Test default memory_max_size value."""
        from autom8_asana.settings import CacheSettings

        with patch.dict(os.environ, {}, clear=True):
            settings = CacheSettings()

        assert settings.memory_max_size == 10000

    def test_memory_max_size_from_env(self) -> None:
        """Test memory_max_size loads from environment."""
        from autom8_asana.settings import CacheSettings

        env = {"ASANA_CACHE_MEMORY_MAX_SIZE": "50000"}
        with patch.dict(os.environ, env, clear=True):
            settings = CacheSettings()

        assert settings.memory_max_size == 50000


class TestRedisSettingsExtensions:
    """Tests for RedisSettings extension fields."""

    def test_timeout_defaults(self) -> None:
        """Test default timeout values."""
        from autom8_asana.settings import RedisSettings

        with patch.dict(os.environ, {}, clear=True):
            settings = RedisSettings()

        assert settings.socket_timeout == 2.0
        assert settings.connect_timeout == 5.0

    def test_timeouts_from_env(self) -> None:
        """Test timeout values load from environment."""
        from autom8_asana.settings import RedisSettings

        env = {
            "REDIS_SOCKET_TIMEOUT": "3.5",
            "REDIS_CONNECT_TIMEOUT": "10.0",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = RedisSettings()

        assert settings.socket_timeout == 3.5
        assert settings.connect_timeout == 10.0


class TestProjectOverrideSettings:
    """Tests for ProjectOverrideSettings validation."""

    def test_valid_gids_pass_validation(self) -> None:
        """Test valid ASANA_PROJECT_* GIDs pass validation."""
        from autom8_asana.settings import ProjectOverrideSettings

        env = {
            "ASANA_PROJECT_SALES": "1234567890123456",
            "ASANA_PROJECT_ONBOARDING": "9876543210987654",
        }
        with patch.dict(os.environ, env, clear=True):
            # Should not raise
            settings = ProjectOverrideSettings()
            assert settings is not None

    def test_empty_values_allowed(self) -> None:
        """Test empty ASANA_PROJECT_* values are allowed."""
        from autom8_asana.settings import ProjectOverrideSettings

        env = {
            "ASANA_PROJECT_EMPTY": "",
            "ASANA_PROJECT_WHITESPACE": "   ",
        }
        with patch.dict(os.environ, env, clear=True):
            # Should not raise - empty values use class defaults
            settings = ProjectOverrideSettings()
            assert settings is not None

    def test_invalid_gid_warns_in_default_mode(self) -> None:
        """Test invalid ASANA_PROJECT_* GID logs warning in default mode."""
        from unittest.mock import MagicMock

        from autom8_asana.settings import ProjectOverrideSettings

        env = {
            "ASANA_PROJECT_INVALID": "not-a-gid",
        }
        # Patch get_logger to capture warning calls directly, avoiding
        # structlog configuration pollution from test ordering in full suite
        mock_logger = MagicMock()
        with (
            patch.dict(os.environ, env, clear=True),
            patch("autom8y_log.get_logger", return_value=mock_logger),
        ):
            # Should NOT raise in default (non-strict) mode
            settings = ProjectOverrideSettings()
            assert settings is not None

        # Verify warning was emitted with the expected content
        warning_calls = mock_logger.warning.call_args_list
        warning_messages = [str(call[0][0]) for call in warning_calls]
        combined = " ".join(warning_messages)
        assert "Invalid GID format" in combined
        assert "ASANA_PROJECT_INVALID" in combined

    def test_invalid_gid_raises_in_strict_mode(self) -> None:
        """Test invalid ASANA_PROJECT_* GID raises ValueError in strict mode."""
        from pydantic import ValidationError

        from autom8_asana.settings import ProjectOverrideSettings

        env = {
            "ASANA_STRICT_CONFIG": "true",
            "ASANA_PROJECT_INVALID": "not-a-gid",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                ProjectOverrideSettings()

        assert "Invalid GID format" in str(exc_info.value)
        assert "ASANA_PROJECT_INVALID" in str(exc_info.value)

    def test_short_gid_raises_in_strict_mode(self) -> None:
        """Test GID with less than 10 digits raises ValueError in strict mode."""
        from pydantic import ValidationError

        from autom8_asana.settings import ProjectOverrideSettings

        env = {
            "ASANA_STRICT_CONFIG": "true",
            "ASANA_PROJECT_SHORT": "123456789",  # 9 digits
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                ProjectOverrideSettings()

        assert "Invalid GID format" in str(exc_info.value)

    def test_non_numeric_gid_raises_in_strict_mode(self) -> None:
        """Test non-numeric GID raises ValueError in strict mode."""
        from pydantic import ValidationError

        from autom8_asana.settings import ProjectOverrideSettings

        env = {
            "ASANA_STRICT_CONFIG": "true",
            "ASANA_PROJECT_ALPHA": "12345abc90",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                ProjectOverrideSettings()

        assert "Invalid GID format" in str(exc_info.value)

    def test_validation_triggered_by_main_settings_in_strict_mode(self) -> None:
        """Test project override validation is triggered by main Settings in strict mode."""
        from pydantic import ValidationError

        from autom8_asana.settings import Settings

        env = {
            "ASANA_STRICT_CONFIG": "true",
            "ASANA_PROJECT_BAD": "invalid",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

        assert "Invalid GID format" in str(exc_info.value)

    def test_validation_warns_by_main_settings_in_default_mode(self) -> None:
        """Test project override validation only warns in default mode."""
        from autom8_asana.settings import Settings

        env = {
            "ASANA_PROJECT_BAD": "invalid",
        }
        with patch.dict(os.environ, env, clear=True):
            # Should NOT raise - only warn
            settings = Settings()
            assert settings is not None


class TestIntegration:
    """Integration tests for settings with multiple components."""

    def test_full_configuration(self) -> None:
        """Test loading a complete configuration from environment."""
        from autom8_asana.settings import Settings

        env = {
            "ASANA_PAT": "xoxp-test-token",
            "ASANA_WORKSPACE_GID": "9876543210",
            "AUTOM8Y_ENV": "production",
            "ASANA_CACHE_ENABLED": "true",
            "ASANA_CACHE_PROVIDER": "redis",
            "ASANA_CACHE_TTL_DEFAULT": "900",
            "ASANA_CACHE_MEMORY_MAX_SIZE": "20000",
            "ASANA_CACHE_S3_BUCKET": "my-cache-bucket",
            "REDIS_HOST": "redis.prod.example.com",
            "REDIS_PORT": "6380",
            "REDIS_SSL": "true",
            "REDIS_SOCKET_TIMEOUT": "3.0",
            "REDIS_CONNECT_TIMEOUT": "8.0",
        }

        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.asana.pat is not None
        assert settings.asana.pat.get_secret_value() == "xoxp-test-token"
        assert settings.asana.workspace_gid == "9876543210"
        assert settings.autom8y_env == "production"
        assert settings.is_production is True
        assert settings.cache.enabled is True
        assert settings.cache.provider == "redis"
        assert settings.cache.ttl_default == 900
        assert settings.cache.memory_max_size == 20000
        assert settings.s3.bucket == "my-cache-bucket"
        assert settings.redis.host == "redis.prod.example.com"
        assert settings.redis.port == 6380
        assert settings.redis.ssl is True
        assert settings.redis.socket_timeout == 3.0
        assert settings.redis.connect_timeout == 8.0
        assert settings.redis_available is True
