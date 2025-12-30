"""Configuration for autom8_data client.

Per TDD-INSIGHTS-001 Section 7: Configuration dataclasses for DataServiceClient.
Per FR-001.2: Constructor accepts base_url with env default.
Per ADR-INS-004: Includes cache_ttl for insights cache.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from autom8_asana.exceptions import ConfigurationError

__all__ = [
    "TimeoutConfig",
    "ConnectionPoolConfig",
    "RetryConfig",
    "CircuitBreakerConfig",
    "DataServiceConfig",
]


@dataclass(frozen=True)
class TimeoutConfig:
    """HTTP timeout configuration for autom8_data client.

    Per TDD-INSIGHTS-001 Section 7.1: Default values optimized for
    analytics queries which may take longer than typical API calls.

    Attributes:
        connect: Timeout for establishing connection (seconds).
        read: Timeout for reading response (seconds).
        write: Timeout for sending request body (seconds).
        pool: Timeout for acquiring connection from pool (seconds).
    """

    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 5.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.connect <= 0:
            raise ConfigurationError(
                f"connect timeout must be positive, got {self.connect}"
            )
        if self.read <= 0:
            raise ConfigurationError(
                f"read timeout must be positive, got {self.read}"
            )
        if self.write <= 0:
            raise ConfigurationError(
                f"write timeout must be positive, got {self.write}"
            )
        if self.pool <= 0:
            raise ConfigurationError(
                f"pool timeout must be positive, got {self.pool}"
            )


@dataclass(frozen=True)
class ConnectionPoolConfig:
    """HTTP connection pool configuration for autom8_data client.

    Per TDD-INSIGHTS-001 Section 7.1: Connection pool settings for
    persistent connections to autom8_data satellite.

    Attributes:
        max_connections: Maximum total connections in pool.
        max_keepalive_connections: Maximum idle connections to keep.
        keepalive_expiry: Seconds before closing idle connections.
    """

    max_connections: int = 10
    max_keepalive_connections: int = 5
    keepalive_expiry: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_connections <= 0:
            raise ConfigurationError(
                f"max_connections must be positive, got {self.max_connections}"
            )
        if self.max_keepalive_connections <= 0:
            raise ConfigurationError(
                f"max_keepalive_connections must be positive, "
                f"got {self.max_keepalive_connections}"
            )
        if self.keepalive_expiry <= 0:
            raise ConfigurationError(
                f"keepalive_expiry must be positive, got {self.keepalive_expiry}"
            )


@dataclass(frozen=True)
class RetryConfig:
    """Retry configuration for insights API.

    Per TDD-INSIGHTS-001 Section 7.1 and NFR-002: 2 retries with
    exponential backoff for transient failures.

    Attributes:
        max_retries: Maximum retry attempts (default 2 per NFR-002).
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap in seconds.
        exponential_base: Multiplier for exponential backoff.
        jitter: Add random jitter to delays to prevent thundering herd.
        retryable_status_codes: HTTP status codes that trigger retry.
            Per Section 11.1: 429, 502, 503, 504 are retryable.
    """

    max_retries: int = 2
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 502, 503, 504})
    )

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_retries < 0:
            raise ConfigurationError(
                f"max_retries must be non-negative, got {self.max_retries}"
            )
        if self.base_delay < 0:
            raise ConfigurationError(
                f"base_delay must be non-negative, got {self.base_delay}"
            )
        if self.max_delay <= 0:
            raise ConfigurationError(
                f"max_delay must be positive, got {self.max_delay}"
            )
        if self.exponential_base < 1:
            raise ConfigurationError(
                f"exponential_base must be at least 1, got {self.exponential_base}"
            )


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration for cascade failure prevention.

    Per TDD-INSIGHTS-001 Section 7.1 and NFR-002: 5 failures in 60s
    triggers open state to prevent cascading failures.

    Per ADR-INS-005: Composed with existing CircuitBreaker from transport layer.

    Attributes:
        enabled: Whether circuit breaker is active (default True for data service).
        failure_threshold: Consecutive failures before opening circuit.
        recovery_timeout: Seconds to wait before half-open probe.
        half_open_max_calls: Successful probes required to close circuit.
    """

    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.failure_threshold < 1:
            raise ConfigurationError(
                f"failure_threshold must be at least 1, got {self.failure_threshold}"
            )
        if self.recovery_timeout <= 0:
            raise ConfigurationError(
                f"recovery_timeout must be positive, got {self.recovery_timeout}"
            )
        if self.half_open_max_calls < 1:
            raise ConfigurationError(
                f"half_open_max_calls must be at least 1, got {self.half_open_max_calls}"
            )


@dataclass
class DataServiceConfig:
    """Configuration for DataServiceClient.

    Per TDD-INSIGHTS-001 Section 7.1: Main configuration dataclass for
    autom8_data satellite client.

    Per FR-001.2: base_url defaults from AUTOM8_DATA_URL env var.
    Per ADR-INS-004: cache_ttl for client-side insights caching.

    Environment Variables:
        AUTOM8_DATA_URL: Base URL for autom8_data service.
            Default: "http://localhost:8000"
        AUTOM8_DATA_API_KEY: API key environment variable name.
            Used with AuthProvider.get_secret().
        AUTOM8_DATA_CACHE_TTL: Cache TTL in seconds for insights.
            Default: 300 (5 minutes for live analytics).

    Attributes:
        base_url: Base URL for autom8_data API.
        token_key: Environment variable name for API key.
        timeout: HTTP timeout settings.
        connection_pool: Connection pool settings.
        retry: Retry behavior settings.
        circuit_breaker: Circuit breaker settings.
        cache_ttl: Client-side cache TTL in seconds (per ADR-INS-004).
        max_batch_size: Maximum PhoneVerticalPairs per batch request.

    Example:
        >>> config = DataServiceConfig.from_env()
        >>> async with DataServiceClient(config=config) as client:
        ...     response = await client.get_insights_async(...)

        # Custom configuration
        >>> config = DataServiceConfig(
        ...     base_url="https://data.example.com",
        ...     timeout=TimeoutConfig(read=60.0),
        ...     cache_ttl=600,  # 10 minutes
        ... )
    """

    base_url: str = field(
        default_factory=lambda: os.environ.get(
            "AUTOM8_DATA_URL", "http://localhost:8000"
        )
    )
    token_key: str = "AUTOM8_DATA_API_KEY"

    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    # Per ADR-INS-004: Client-side cache TTL for insights
    cache_ttl: int = 300  # 5 minutes default for live analytics

    # Per FR-006.4: Maximum batch size
    max_batch_size: int = 50

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.base_url:
            raise ConfigurationError("base_url must not be empty")
        if not self.token_key:
            raise ConfigurationError("token_key must not be empty")
        if self.cache_ttl < 0:
            raise ConfigurationError(
                f"cache_ttl must be non-negative, got {self.cache_ttl}"
            )
        if self.max_batch_size < 1:
            raise ConfigurationError(
                f"max_batch_size must be at least 1, got {self.max_batch_size}"
            )

    @classmethod
    def from_env(cls) -> "DataServiceConfig":
        """Create config from environment variables.

        Per FR-001.2: Reads AUTOM8_DATA_* environment variables.

        Environment Variables:
            AUTOM8_DATA_URL: Base URL (default: "http://localhost:8000")
            AUTOM8_DATA_API_KEY: Token key name (used as-is, not resolved)
            AUTOM8_DATA_CACHE_TTL: Cache TTL in seconds (default: 300)

        Returns:
            DataServiceConfig populated from environment.

        Example:
            >>> import os
            >>> os.environ["AUTOM8_DATA_URL"] = "https://data.prod.example.com"
            >>> os.environ["AUTOM8_DATA_CACHE_TTL"] = "600"
            >>> config = DataServiceConfig.from_env()
            >>> config.base_url
            'https://data.prod.example.com'
            >>> config.cache_ttl
            600
        """
        # Parse cache TTL with fallback
        cache_ttl_str = os.environ.get("AUTOM8_DATA_CACHE_TTL", "300")
        try:
            cache_ttl = int(cache_ttl_str)
        except ValueError:
            cache_ttl = 300  # Default on invalid input

        return cls(
            base_url=os.environ.get("AUTOM8_DATA_URL", "http://localhost:8000"),
            cache_ttl=cache_ttl,
        )
