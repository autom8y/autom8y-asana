"""Configuration translation layer for autom8y-http platform SDK.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-003: Translates AsanaConfig to autom8y-http
configuration classes.

This module provides a single translation layer between the autom8_asana domain
configuration (AsanaConfig and its nested dataclasses) and the platform SDK
configuration classes (HttpClientConfig, RateLimiterConfig, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_http import (
    CircuitBreakerConfig as PlatformCircuitBreakerConfig,
)
from autom8y_http import (
    HttpClientConfig,
)
from autom8y_http import (
    RateLimiterConfig as PlatformRateLimiterConfig,
)
from autom8y_http import (
    RetryConfig as PlatformRetryConfig,
)

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig

__all__ = ["ConfigTranslator"]


class ConfigTranslator:
    """Translates AsanaConfig to autom8y-http configuration.

    Per TDD-ASANA-HTTP-MIGRATION-001/FR-003: Provides bidirectional configuration
    mapping between autom8_asana domain config and platform SDK config.

    This is a stateless utility class with static methods. All translations
    are pure functions with no side effects.

    Example:
        >>> from autom8_asana.config import AsanaConfig
        >>> asana_config = AsanaConfig(
        ...     rate_limit=RateLimitConfig(max_requests=1200, window_seconds=60),
        ... )
        >>> rate_config = ConfigTranslator.to_rate_limiter_config(asana_config)
        >>> rate_config.max_tokens
        1200
    """

    @staticmethod
    def to_http_client_config(asana_config: AsanaConfig) -> HttpClientConfig:
        """Translate AsanaConfig to HttpClientConfig.

        Per TDD-ASANA-HTTP-MIGRATION-001: Maps domain config to platform HTTP client config.

        Note: Policy toggles (enable_rate_limiting, enable_retry, enable_circuit_breaker)
        are set to False because we inject our own shared instances externally.

        Args:
            asana_config: Asana SDK configuration.

        Returns:
            HttpClientConfig for Autom8yHttpClient.

        Mapping:
            - base_url: asana_config.base_url
            - timeout: asana_config.timeout.read (use read timeout as primary)
            - max_connections: asana_config.connection_pool.max_connections
            - enable_rate_limiting: False (we inject shared limiter)
            - enable_retry: False (we inject shared retry policy)
            - enable_circuit_breaker: False (we inject shared circuit breaker)
        """
        return HttpClientConfig(
            base_url=asana_config.base_url,
            timeout=asana_config.timeout.read,
            max_connections=asana_config.connection_pool.max_connections,
            enable_rate_limiting=False,  # We inject our own shared limiter
            enable_retry=False,  # We inject our own shared retry policy
            enable_circuit_breaker=False,  # We inject our own shared circuit breaker
        )

    @staticmethod
    def to_rate_limiter_config(asana_config: AsanaConfig) -> PlatformRateLimiterConfig:
        """Translate AsanaConfig to RateLimiterConfig.

        Per TDD-ASANA-HTTP-MIGRATION-001/FR-002: Maps domain rate limit config to
        platform token bucket config.

        Args:
            asana_config: Asana SDK configuration.

        Returns:
            RateLimiterConfig for TokenBucketRateLimiter.

        Mapping:
            - max_tokens: asana_config.rate_limit.max_requests
            - refill_period: asana_config.rate_limit.window_seconds
        """
        return PlatformRateLimiterConfig(
            max_tokens=asana_config.rate_limit.max_requests,
            refill_period=float(asana_config.rate_limit.window_seconds),
        )

    @staticmethod
    def to_retry_config(asana_config: AsanaConfig) -> PlatformRetryConfig:
        """Translate AsanaConfig to RetryConfig.

        Per TDD-ASANA-HTTP-MIGRATION-001/FR-003: Maps domain retry config to
        platform exponential backoff config.

        Args:
            asana_config: Asana SDK configuration.

        Returns:
            RetryConfig for ExponentialBackoffRetry.

        Mapping:
            - max_retries: asana_config.retry.max_retries
            - base_delay: asana_config.retry.base_delay
            - max_delay: asana_config.retry.max_delay
            - exponential_base: asana_config.retry.exponential_base
            - jitter: asana_config.retry.jitter
            - retryable_status_codes: asana_config.retry.retryable_status_codes
        """
        return PlatformRetryConfig(
            max_retries=asana_config.retry.max_retries,
            base_delay=asana_config.retry.base_delay,
            max_delay=asana_config.retry.max_delay,
            exponential_base=asana_config.retry.exponential_base,
            jitter=asana_config.retry.jitter,
            retryable_status_codes=asana_config.retry.retryable_status_codes,
        )

    @staticmethod
    def to_circuit_breaker_config(
        asana_config: AsanaConfig,
    ) -> PlatformCircuitBreakerConfig:
        """Translate AsanaConfig to CircuitBreakerConfig.

        Per TDD-ASANA-HTTP-MIGRATION-001/FR-004: Maps domain circuit breaker config
        to platform circuit breaker config.

        Args:
            asana_config: Asana SDK configuration.

        Returns:
            CircuitBreakerConfig for CircuitBreaker.

        Mapping:
            - enabled: asana_config.circuit_breaker.enabled
            - failure_threshold: asana_config.circuit_breaker.failure_threshold
            - recovery_timeout: asana_config.circuit_breaker.recovery_timeout
            - half_open_max_calls: asana_config.circuit_breaker.half_open_max_calls
        """
        return PlatformCircuitBreakerConfig(
            enabled=asana_config.circuit_breaker.enabled,
            failure_threshold=asana_config.circuit_breaker.failure_threshold,
            recovery_timeout=asana_config.circuit_breaker.recovery_timeout,
            half_open_max_calls=asana_config.circuit_breaker.half_open_max_calls,
        )
