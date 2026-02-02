"""Unit tests for ConfigTranslator.

Per TDD-ASANA-HTTP-MIGRATION-001: Tests configuration translation
between autom8_asana domain config and autom8y-http platform config.
"""

from __future__ import annotations

from autom8_asana.config import (
    AsanaConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
    RetryConfig,
)
from autom8_asana.transport.config_translator import ConfigTranslator


class TestToHttpClientConfig:
    """Test HttpClientConfig translation."""

    def test_translates_base_url(self):
        """Base URL is preserved."""
        config = AsanaConfig(base_url="https://custom.api.asana.com/v1")
        result = ConfigTranslator.to_http_client_config(config)
        assert result.base_url == "https://custom.api.asana.com/v1"

    def test_translates_default_base_url(self):
        """Default base URL is used when not specified."""
        config = AsanaConfig()
        result = ConfigTranslator.to_http_client_config(config)
        assert result.base_url == "https://app.asana.com/api/1.0"

    def test_translates_timeout_from_read_timeout(self):
        """Timeout uses read timeout value."""
        from autom8_asana.config import TimeoutConfig

        config = AsanaConfig(timeout=TimeoutConfig(read=45.0))
        result = ConfigTranslator.to_http_client_config(config)
        assert result.timeout == 45.0

    def test_translates_max_connections(self):
        """Max connections is preserved."""
        from autom8_asana.config import ConnectionPoolConfig

        config = AsanaConfig(connection_pool=ConnectionPoolConfig(max_connections=50))
        result = ConfigTranslator.to_http_client_config(config)
        assert result.max_connections == 50

    def test_disables_internal_rate_limiting(self):
        """Rate limiting is disabled (we inject our own)."""
        config = AsanaConfig()
        result = ConfigTranslator.to_http_client_config(config)
        assert result.enable_rate_limiting is False

    def test_disables_internal_retry(self):
        """Retry is disabled (we inject our own)."""
        config = AsanaConfig()
        result = ConfigTranslator.to_http_client_config(config)
        assert result.enable_retry is False

    def test_disables_internal_circuit_breaker(self):
        """Circuit breaker is disabled (we inject our own)."""
        config = AsanaConfig()
        result = ConfigTranslator.to_http_client_config(config)
        assert result.enable_circuit_breaker is False


class TestToRateLimiterConfig:
    """Test RateLimiterConfig translation."""

    def test_translates_max_tokens(self):
        """Max tokens uses max_requests."""
        config = AsanaConfig(rate_limit=RateLimitConfig(max_requests=1200))
        result = ConfigTranslator.to_rate_limiter_config(config)
        assert result.max_tokens == 1200

    def test_translates_refill_period(self):
        """Refill period uses window_seconds."""
        config = AsanaConfig(rate_limit=RateLimitConfig(window_seconds=120))
        result = ConfigTranslator.to_rate_limiter_config(config)
        assert result.refill_period == 120.0

    def test_default_values(self):
        """Default rate limit values are preserved."""
        config = AsanaConfig()
        result = ConfigTranslator.to_rate_limiter_config(config)
        assert result.max_tokens == 1500
        assert result.refill_period == 60.0


class TestToRetryConfig:
    """Test RetryConfig translation."""

    def test_translates_max_retries(self):
        """Max retries is preserved."""
        config = AsanaConfig(retry=RetryConfig(max_retries=5))
        result = ConfigTranslator.to_retry_config(config)
        assert result.max_retries == 5

    def test_translates_base_delay(self):
        """Base delay is preserved."""
        config = AsanaConfig(retry=RetryConfig(base_delay=0.5))
        result = ConfigTranslator.to_retry_config(config)
        assert result.base_delay == 0.5

    def test_translates_max_delay(self):
        """Max delay is preserved."""
        config = AsanaConfig(retry=RetryConfig(max_delay=30.0))
        result = ConfigTranslator.to_retry_config(config)
        assert result.max_delay == 30.0

    def test_translates_exponential_base(self):
        """Exponential base is preserved."""
        config = AsanaConfig(retry=RetryConfig(exponential_base=3.0))
        result = ConfigTranslator.to_retry_config(config)
        assert result.exponential_base == 3.0

    def test_translates_jitter(self):
        """Jitter flag is preserved."""
        config = AsanaConfig(retry=RetryConfig(jitter=False))
        result = ConfigTranslator.to_retry_config(config)
        assert result.jitter is False

    def test_translates_retryable_status_codes(self):
        """Retryable status codes are preserved."""
        codes = frozenset({429, 500, 503})
        config = AsanaConfig(retry=RetryConfig(retryable_status_codes=codes))
        result = ConfigTranslator.to_retry_config(config)
        assert result.retryable_status_codes == codes

    def test_default_values(self):
        """Default retry values are preserved."""
        config = AsanaConfig()
        result = ConfigTranslator.to_retry_config(config)
        assert result.max_retries == 5
        assert result.base_delay == 0.5
        assert result.max_delay == 60.0
        assert result.jitter is True


class TestToCircuitBreakerConfig:
    """Test CircuitBreakerConfig translation."""

    def test_translates_enabled(self):
        """Enabled flag is preserved."""
        config = AsanaConfig(circuit_breaker=CircuitBreakerConfig(enabled=True))
        result = ConfigTranslator.to_circuit_breaker_config(config)
        assert result.enabled is True

    def test_translates_failure_threshold(self):
        """Failure threshold is preserved."""
        config = AsanaConfig(circuit_breaker=CircuitBreakerConfig(failure_threshold=10))
        result = ConfigTranslator.to_circuit_breaker_config(config)
        assert result.failure_threshold == 10

    def test_translates_recovery_timeout(self):
        """Recovery timeout is preserved."""
        config = AsanaConfig(
            circuit_breaker=CircuitBreakerConfig(recovery_timeout=120.0)
        )
        result = ConfigTranslator.to_circuit_breaker_config(config)
        assert result.recovery_timeout == 120.0

    def test_translates_half_open_max_calls(self):
        """Half-open max calls is preserved."""
        config = AsanaConfig(
            circuit_breaker=CircuitBreakerConfig(half_open_max_calls=3)
        )
        result = ConfigTranslator.to_circuit_breaker_config(config)
        assert result.half_open_max_calls == 3

    def test_default_values(self):
        """Default circuit breaker values are preserved."""
        config = AsanaConfig()
        result = ConfigTranslator.to_circuit_breaker_config(config)
        assert result.enabled is False  # Opt-in
        assert result.failure_threshold == 5
        assert result.recovery_timeout == 60.0
        assert result.half_open_max_calls == 1
