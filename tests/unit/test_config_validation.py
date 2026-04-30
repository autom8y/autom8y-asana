"""Tests for configuration validation.

Includes FR-DET-007: Tests for ASANA_PROJECT_* environment variable validation.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from autom8_asana.config import (
    GID_PATTERN,
    AsanaConfig,
    ConcurrencyConfig,
    ConnectionPoolConfig,
    RateLimitConfig,
    RetryConfig,
    TimeoutConfig,
    validate_project_env_vars,
)
from autom8_asana.errors import ConfigurationError


class TestRateLimitConfig:
    """Tests for RateLimitConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = RateLimitConfig()

        assert config.max_requests == 1500
        assert config.window_seconds == 60

    def test_accepts_valid_values(self) -> None:
        """Accepts valid custom values."""
        config = RateLimitConfig(max_requests=1000, window_seconds=30)

        assert config.max_requests == 1000
        assert config.window_seconds == 30

    @pytest.mark.parametrize(
        ("field", "value", "must_contain"),
        [
            ("max_requests", 0, ("max_requests", "positive")),
            ("max_requests", -10, ("max_requests",)),
            ("window_seconds", 0, ("window_seconds", "positive")),
            ("window_seconds", -5, ("window_seconds",)),
        ],
        ids=[
            "rejects_zero_max_requests",
            "rejects_negative_max_requests",
            "rejects_zero_window_seconds",
            "rejects_negative_window_seconds",
        ],
    )
    def test_rejects_invalid_field(
        self, field: str, value: int | float, must_contain: tuple[str, ...]
    ) -> None:
        """Rejects invalid value for the named field."""
        with pytest.raises(ConfigurationError) as exc_info:
            RateLimitConfig(**{field: value})
        for token in must_contain:
            assert token in str(exc_info.value)


class TestRetryConfig:
    """Tests for RetryConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = RetryConfig()

        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert 429 in config.retryable_status_codes

    def test_accepts_valid_values(self) -> None:
        """Accepts valid custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_accepts_zero_max_retries(self) -> None:
        """Zero max_retries is valid (disables retries)."""
        config = RetryConfig(max_retries=0)

        assert config.max_retries == 0

    def test_accepts_zero_base_delay(self) -> None:
        """Zero base_delay is valid (no initial delay)."""
        config = RetryConfig(base_delay=0)

        assert config.base_delay == 0

    @pytest.mark.parametrize(
        ("field", "value", "must_contain"),
        [
            ("max_retries", -1, ("max_retries", "non-negative")),
            ("base_delay", -0.1, ("base_delay", "non-negative")),
            ("max_delay", 0, ("max_delay", "positive")),
            ("max_delay", -10.0, ("max_delay",)),
        ],
        ids=[
            "rejects_negative_max_retries",
            "rejects_negative_base_delay",
            "rejects_zero_max_delay",
            "rejects_negative_max_delay",
        ],
    )
    def test_rejects_invalid_field(
        self, field: str, value: int | float, must_contain: tuple[str, ...]
    ) -> None:
        """Rejects invalid value for the named field."""
        with pytest.raises(ConfigurationError) as exc_info:
            RetryConfig(**{field: value})
        for token in must_contain:
            assert token in str(exc_info.value)

    def test_rejects_exponential_base_less_than_one(self) -> None:
        """Rejects exponential_base less than 1."""
        with pytest.raises(ConfigurationError) as exc_info:
            RetryConfig(exponential_base=0.5)

        assert "exponential_base" in str(exc_info.value)
        assert "at least 1" in str(exc_info.value)

    def test_accepts_exponential_base_of_one(self) -> None:
        """Accepts exponential_base of exactly 1 (linear backoff)."""
        config = RetryConfig(exponential_base=1.0)

        assert config.exponential_base == 1.0


class TestConcurrencyConfig:
    """Tests for ConcurrencyConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = ConcurrencyConfig()

        assert config.read_limit == 50
        assert config.write_limit == 15

    def test_accepts_valid_values(self) -> None:
        """Accepts valid custom values."""
        config = ConcurrencyConfig(read_limit=100, write_limit=25)

        assert config.read_limit == 100
        assert config.write_limit == 25

    @pytest.mark.parametrize(
        ("field", "value", "must_contain"),
        [
            ("read_limit", 0, ("read_limit", "positive")),
            ("read_limit", -5, ("read_limit",)),
            ("write_limit", 0, ("write_limit", "positive")),
            ("write_limit", -10, ("write_limit",)),
        ],
        ids=[
            "rejects_zero_read_limit",
            "rejects_negative_read_limit",
            "rejects_zero_write_limit",
            "rejects_negative_write_limit",
        ],
    )
    def test_rejects_invalid_field(
        self, field: str, value: int | float, must_contain: tuple[str, ...]
    ) -> None:
        """Rejects invalid value for the named field."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConcurrencyConfig(**{field: value})
        for token in must_contain:
            assert token in str(exc_info.value)


class TestTimeoutConfig:
    """Tests for TimeoutConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = TimeoutConfig()

        assert config.connect == 5.0
        assert config.read == 30.0
        assert config.write == 30.0
        assert config.pool == 10.0

    def test_accepts_valid_values(self) -> None:
        """Accepts valid custom values."""
        config = TimeoutConfig(
            connect=10.0,
            read=60.0,
            write=60.0,
            pool=20.0,
        )

        assert config.connect == 10.0
        assert config.read == 60.0
        assert config.write == 60.0
        assert config.pool == 20.0

    @pytest.mark.parametrize(
        ("field", "value", "must_contain"),
        [
            ("connect", 0, ("connect", "positive")),
            ("connect", -1.0, ("connect",)),
            ("read", 0, ("read", "positive")),
            ("read", -5.0, ("read",)),
            ("write", 0, ("write", "positive")),
            ("write", -10.0, ("write",)),
            ("pool", 0, ("pool", "positive")),
            ("pool", -2.0, ("pool",)),
        ],
        ids=[
            "rejects_zero_connect",
            "rejects_negative_connect",
            "rejects_zero_read",
            "rejects_negative_read",
            "rejects_zero_write",
            "rejects_negative_write",
            "rejects_zero_pool",
            "rejects_negative_pool",
        ],
    )
    def test_rejects_invalid_field(
        self, field: str, value: int | float, must_contain: tuple[str, ...]
    ) -> None:
        """Rejects invalid value for the named field."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(**{field: value})
        for token in must_contain:
            assert token in str(exc_info.value)


class TestConnectionPoolConfig:
    """Tests for ConnectionPoolConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = ConnectionPoolConfig()

        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.keepalive_expiry == 30.0

    def test_accepts_valid_values(self) -> None:
        """Accepts valid custom values."""
        config = ConnectionPoolConfig(
            max_connections=200,
            max_keepalive_connections=50,
            keepalive_expiry=60.0,
        )

        assert config.max_connections == 200
        assert config.max_keepalive_connections == 50
        assert config.keepalive_expiry == 60.0

    @pytest.mark.parametrize(
        ("field", "value", "must_contain"),
        [
            ("max_connections", 0, ("max_connections", "positive")),
            ("max_connections", -10, ("max_connections",)),
            ("max_keepalive_connections", 0, ("max_keepalive_connections", "positive")),
            ("max_keepalive_connections", -5, ("max_keepalive_connections",)),
            ("keepalive_expiry", 0, ("keepalive_expiry", "positive")),
            ("keepalive_expiry", -15.0, ("keepalive_expiry",)),
        ],
        ids=[
            "rejects_zero_max_connections",
            "rejects_negative_max_connections",
            "rejects_zero_max_keepalive_connections",
            "rejects_negative_max_keepalive_connections",
            "rejects_zero_keepalive_expiry",
            "rejects_negative_keepalive_expiry",
        ],
    )
    def test_rejects_invalid_field(
        self, field: str, value: int | float, must_contain: tuple[str, ...]
    ) -> None:
        """Rejects invalid value for the named field."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(**{field: value})
        for token in must_contain:
            assert token in str(exc_info.value)


class TestAsanaConfig:
    """Tests for main AsanaConfig."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = AsanaConfig()

        assert config.base_url == "https://app.asana.com/api/1.0"
        assert config.token_key == "ASANA_PAT"
        assert isinstance(config.rate_limit, RateLimitConfig)
        assert isinstance(config.retry, RetryConfig)
        assert isinstance(config.concurrency, ConcurrencyConfig)
        assert isinstance(config.timeout, TimeoutConfig)
        assert isinstance(config.connection_pool, ConnectionPoolConfig)

    def test_accepts_custom_subconfigs(self) -> None:
        """Accepts custom nested configurations."""
        config = AsanaConfig(
            rate_limit=RateLimitConfig(max_requests=1000),
            retry=RetryConfig(max_retries=5),
            concurrency=ConcurrencyConfig(read_limit=100),
            timeout=TimeoutConfig(connect=10.0),
            connection_pool=ConnectionPoolConfig(max_connections=200),
        )

        assert config.rate_limit.max_requests == 1000
        assert config.retry.max_retries == 5
        assert config.concurrency.read_limit == 100
        assert config.timeout.connect == 10.0
        assert config.connection_pool.max_connections == 200

    def test_accepts_custom_base_url(self) -> None:
        """Accepts custom base_url."""
        config = AsanaConfig(base_url="https://custom.asana.com/api/1.0")

        assert config.base_url == "https://custom.asana.com/api/1.0"

    def test_accepts_custom_token_key(self) -> None:
        """Accepts custom token_key."""
        config = AsanaConfig(token_key="CUSTOM_ASANA_TOKEN")

        assert config.token_key == "CUSTOM_ASANA_TOKEN"


# --- Test: GID_PATTERN (FR-DET-007) ---


class TestGidPattern:
    """Tests for GID validation pattern.

    Per FR-DET-007: Validate ASANA_PROJECT_* environment variables.
    """

    @pytest.mark.parametrize(
        "gid",
        [
            "1234567890",  # 10 digits
            "1234567890123456",  # 16 digits (typical)
            "12345678901234567890",  # 20 digits
            "0000000000",  # All zeros (valid format)
        ],
    )
    def test_valid_gids_match(self, gid: str) -> None:
        """Valid GID formats match pattern."""
        assert GID_PATTERN.match(gid) is not None

    @pytest.mark.parametrize(
        "invalid_gid",
        [
            "123456789",  # 9 digits (too short)
            "abc1234567890",  # Letters
            "1234-5678-90",  # Dashes
            "12345 67890",  # Spaces
            "",  # Empty
            "not-a-gid",  # Text
            "1.234567890",  # Decimal
        ],
    )
    def test_invalid_gids_do_not_match(self, invalid_gid: str) -> None:
        """Invalid GID formats do not match pattern."""
        assert GID_PATTERN.match(invalid_gid) is None


# --- Test: validate_project_env_vars (FR-DET-007) ---


class TestValidateProjectEnvVars:
    """Tests for validate_project_env_vars function.

    Per FR-DET-007: Startup validation for ASANA_PROJECT_* env vars.
    """

    def test_no_asana_project_vars_returns_empty(self) -> None:
        """No ASANA_PROJECT_* vars returns empty warnings."""
        with patch.dict(os.environ, {}, clear=True):
            warnings = validate_project_env_vars()

        assert warnings == []

    def test_valid_gids_return_empty(self) -> None:
        """Valid GIDs return no warnings."""
        env = {
            "ASANA_PROJECT_BUSINESS": "1234567890123456",
            "ASANA_PROJECT_CONTACT": "9876543210123456",
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert warnings == []

    def test_empty_values_allowed(self) -> None:
        """Empty values are allowed (use class defaults)."""
        env = {
            "ASANA_PROJECT_BUSINESS": "",
            "ASANA_PROJECT_CONTACT": "   ",  # Whitespace only
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert warnings == []

    def test_invalid_gid_flagged(self) -> None:
        """Invalid GID format is flagged with warning."""
        env = {
            "ASANA_PROJECT_BUSINESS": "not-a-valid-gid",
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert len(warnings) == 1
        assert "ASANA_PROJECT_BUSINESS" in warnings[0]
        assert "not-a-valid-gid" in warnings[0]
        assert "Invalid GID format" in warnings[0]

    def test_multiple_invalid_gids_all_flagged(self) -> None:
        """Multiple invalid GIDs are all flagged."""
        env = {
            "ASANA_PROJECT_BUSINESS": "invalid1",
            "ASANA_PROJECT_CONTACT": "1234567890123456",  # Valid
            "ASANA_PROJECT_UNIT": "invalid2",
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert len(warnings) == 2
        # Check both invalid vars are reported
        warning_text = " ".join(warnings)
        assert "ASANA_PROJECT_BUSINESS" in warning_text
        assert "ASANA_PROJECT_UNIT" in warning_text

    def test_non_asana_project_vars_ignored(self) -> None:
        """Non-ASANA_PROJECT_* vars are ignored."""
        env = {
            "ASANA_PAT": "not-a-gid",  # Not ASANA_PROJECT_*
            "ASANA_WORKSPACE": "also-not-a-gid",
            "OTHER_VAR": "whatever",
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert warnings == []

    def test_strict_mode_raises_on_invalid(self) -> None:
        """Strict mode raises ConfigurationError on invalid GIDs."""
        env = {
            "ASANA_PROJECT_BUSINESS": "invalid-gid",
        }

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_project_env_vars(strict=True)

        assert "Invalid ASANA_PROJECT_* environment variables" in str(exc_info.value)

    def test_strict_mode_no_raise_when_valid(self) -> None:
        """Strict mode does not raise when all GIDs are valid."""
        env = {
            "ASANA_PROJECT_BUSINESS": "1234567890123456",
        }

        with patch.dict(os.environ, env, clear=True):
            # Should not raise
            warnings = validate_project_env_vars(strict=True)

        assert warnings == []

    def test_whitespace_trimmed_before_validation(self) -> None:
        """Whitespace is trimmed before validation."""
        env = {
            "ASANA_PROJECT_BUSINESS": "  1234567890123456  ",  # Valid with whitespace
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert warnings == []

    def test_short_gid_flagged(self) -> None:
        """GIDs shorter than 10 digits are flagged."""
        env = {
            "ASANA_PROJECT_BUSINESS": "123456789",  # 9 digits
        }

        with patch.dict(os.environ, env, clear=True):
            warnings = validate_project_env_vars()

        assert len(warnings) == 1
        assert "123456789" in warnings[0]


# --- Test: CacheConfig Entity TTL (FR-TTL-001 through FR-TTL-007) ---


class TestCacheConfigEntityTTL:
    """Tests for CacheConfig entity-type-specific TTL configuration.

    Per FR-TTL-001 through FR-TTL-007 and ADR-0126.
    """

    def test_default_entity_ttls_are_set(self) -> None:
        """Default entity TTLs are populated on init."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig()

        assert config.entity_ttls == {
            "business": 3600,
            "contact": 900,
            "unit": 900,
            "offer": 180,
            "process": 60,
            "location": 3600,
            "hours": 3600,
        }

    def test_get_entity_ttl_returns_configured_value(self) -> None:
        """get_entity_ttl returns configured TTL for known entities."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig()

        assert config.get_entity_ttl("business") == 3600
        assert config.get_entity_ttl("contact") == 900
        assert config.get_entity_ttl("unit") == 900
        assert config.get_entity_ttl("offer") == 180
        assert config.get_entity_ttl("process") == 60
        assert config.get_entity_ttl("location") == 3600
        assert config.get_entity_ttl("hours") == 3600

    def test_get_entity_ttl_is_case_insensitive(self) -> None:
        """get_entity_ttl normalizes entity type to lowercase."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig()

        assert config.get_entity_ttl("Business") == 3600
        assert config.get_entity_ttl("CONTACT") == 900
        assert config.get_entity_ttl("Process") == 60
        assert config.get_entity_ttl("oFfEr") == 180

    def test_get_entity_ttl_returns_default_for_unknown(self) -> None:
        """get_entity_ttl returns default TTL for unknown entity types."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig()

        # Unknown entity type falls back to 300 (hardcoded default)
        assert config.get_entity_ttl("unknown") == 300
        assert config.get_entity_ttl("task") == 300
        assert config.get_entity_ttl("something_else") == 300

    def test_get_entity_ttl_uses_ttl_settings_default(self) -> None:
        """get_entity_ttl uses TTLSettings.default_ttl for unknown entities."""
        from autom8_asana.cache.models.settings import TTLSettings
        from autom8_asana.config import CacheConfig

        config = CacheConfig()
        config._ttl = TTLSettings(default_ttl=600)

        # Unknown entity type uses TTLSettings.default_ttl
        assert config.get_entity_ttl("unknown") == 600

    def test_custom_entity_ttls_override_defaults(self) -> None:
        """Custom entity_ttls dict overrides default values."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig(
            entity_ttls={
                "business": 7200,  # Custom 2 hours
                "contact": 1800,  # Custom 30 minutes
                "custom_entity": 120,  # Completely custom
            }
        )

        assert config.get_entity_ttl("business") == 7200
        assert config.get_entity_ttl("contact") == 1800
        assert config.get_entity_ttl("custom_entity") == 120
        # Non-configured entity falls back
        assert config.get_entity_ttl("unit") == 300  # Not in custom dict

    def test_entity_ttls_from_env_preserves_defaults(self) -> None:
        """CacheConfig.from_env() preserves default entity_ttls."""
        from autom8_asana.config import CacheConfig

        with patch.dict(os.environ, {"ASANA_CACHE_ENABLED": "true"}, clear=True):
            config = CacheConfig.from_env()

        # Entity TTLs should be default values
        assert config.entity_ttls["business"] == 3600
        assert config.entity_ttls["process"] == 60

    def test_dataframe_caching_default_enabled(self) -> None:
        """DataFrame caching is enabled by default (FR-DF-001)."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig()
        assert config.dataframe_caching is True

    def test_dataframe_caching_can_be_disabled(self) -> None:
        """DataFrame caching can be disabled via config."""
        from autom8_asana.config import CacheConfig

        config = CacheConfig(dataframe_caching=False)
        assert config.dataframe_caching is False
