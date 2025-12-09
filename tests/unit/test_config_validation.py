"""Tests for configuration validation."""

from __future__ import annotations

import pytest

from autom8_asana.config import (
    AsanaConfig,
    ConcurrencyConfig,
    ConnectionPoolConfig,
    RateLimitConfig,
    RetryConfig,
    TimeoutConfig,
)
from autom8_asana.exceptions import ConfigurationError


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

    def test_rejects_zero_max_requests(self) -> None:
        """Rejects max_requests of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            RateLimitConfig(max_requests=0)

        assert "max_requests" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_max_requests(self) -> None:
        """Rejects negative max_requests."""
        with pytest.raises(ConfigurationError) as exc_info:
            RateLimitConfig(max_requests=-10)

        assert "max_requests" in str(exc_info.value)

    def test_rejects_zero_window_seconds(self) -> None:
        """Rejects window_seconds of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            RateLimitConfig(window_seconds=0)

        assert "window_seconds" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_window_seconds(self) -> None:
        """Rejects negative window_seconds."""
        with pytest.raises(ConfigurationError) as exc_info:
            RateLimitConfig(window_seconds=-5)

        assert "window_seconds" in str(exc_info.value)


class TestRetryConfig:
    """Tests for RetryConfig validation."""

    def test_default_values_are_valid(self) -> None:
        """Default configuration is valid."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 0.1
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

    def test_rejects_negative_max_retries(self) -> None:
        """Rejects negative max_retries."""
        with pytest.raises(ConfigurationError) as exc_info:
            RetryConfig(max_retries=-1)

        assert "max_retries" in str(exc_info.value)
        assert "non-negative" in str(exc_info.value)

    def test_accepts_zero_base_delay(self) -> None:
        """Zero base_delay is valid (no initial delay)."""
        config = RetryConfig(base_delay=0)

        assert config.base_delay == 0

    def test_rejects_negative_base_delay(self) -> None:
        """Rejects negative base_delay."""
        with pytest.raises(ConfigurationError) as exc_info:
            RetryConfig(base_delay=-0.1)

        assert "base_delay" in str(exc_info.value)
        assert "non-negative" in str(exc_info.value)

    def test_rejects_zero_max_delay(self) -> None:
        """Rejects max_delay of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            RetryConfig(max_delay=0)

        assert "max_delay" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_max_delay(self) -> None:
        """Rejects negative max_delay."""
        with pytest.raises(ConfigurationError) as exc_info:
            RetryConfig(max_delay=-10.0)

        assert "max_delay" in str(exc_info.value)

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

    def test_rejects_zero_read_limit(self) -> None:
        """Rejects read_limit of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConcurrencyConfig(read_limit=0)

        assert "read_limit" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_read_limit(self) -> None:
        """Rejects negative read_limit."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConcurrencyConfig(read_limit=-5)

        assert "read_limit" in str(exc_info.value)

    def test_rejects_zero_write_limit(self) -> None:
        """Rejects write_limit of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConcurrencyConfig(write_limit=0)

        assert "write_limit" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_write_limit(self) -> None:
        """Rejects negative write_limit."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConcurrencyConfig(write_limit=-10)

        assert "write_limit" in str(exc_info.value)


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

    def test_rejects_zero_connect(self) -> None:
        """Rejects connect timeout of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(connect=0)

        assert "connect" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_connect(self) -> None:
        """Rejects negative connect timeout."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(connect=-1.0)

        assert "connect" in str(exc_info.value)

    def test_rejects_zero_read(self) -> None:
        """Rejects read timeout of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(read=0)

        assert "read" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_read(self) -> None:
        """Rejects negative read timeout."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(read=-5.0)

        assert "read" in str(exc_info.value)

    def test_rejects_zero_write(self) -> None:
        """Rejects write timeout of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(write=0)

        assert "write" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_write(self) -> None:
        """Rejects negative write timeout."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(write=-10.0)

        assert "write" in str(exc_info.value)

    def test_rejects_zero_pool(self) -> None:
        """Rejects pool timeout of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(pool=0)

        assert "pool" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_pool(self) -> None:
        """Rejects negative pool timeout."""
        with pytest.raises(ConfigurationError) as exc_info:
            TimeoutConfig(pool=-2.0)

        assert "pool" in str(exc_info.value)


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

    def test_rejects_zero_max_connections(self) -> None:
        """Rejects max_connections of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(max_connections=0)

        assert "max_connections" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_max_connections(self) -> None:
        """Rejects negative max_connections."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(max_connections=-10)

        assert "max_connections" in str(exc_info.value)

    def test_rejects_zero_max_keepalive_connections(self) -> None:
        """Rejects max_keepalive_connections of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(max_keepalive_connections=0)

        assert "max_keepalive_connections" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_max_keepalive_connections(self) -> None:
        """Rejects negative max_keepalive_connections."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(max_keepalive_connections=-5)

        assert "max_keepalive_connections" in str(exc_info.value)

    def test_rejects_zero_keepalive_expiry(self) -> None:
        """Rejects keepalive_expiry of zero."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(keepalive_expiry=0)

        assert "keepalive_expiry" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_negative_keepalive_expiry(self) -> None:
        """Rejects negative keepalive_expiry."""
        with pytest.raises(ConfigurationError) as exc_info:
            ConnectionPoolConfig(keepalive_expiry=-15.0)

        assert "keepalive_expiry" in str(exc_info.value)


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
