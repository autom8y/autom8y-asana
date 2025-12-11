"""Configuration dataclasses for autom8_asana SDK."""

from __future__ import annotations

from dataclasses import dataclass, field

from autom8_asana.exceptions import ConfigurationError

__all__ = [
    "RateLimitConfig",
    "RetryConfig",
    "ConcurrencyConfig",
    "TimeoutConfig",
    "ConnectionPoolConfig",
    "CircuitBreakerConfig",
    "AsanaConfig",
]


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting configuration.

    Default: 1500 requests per 60 seconds (Asana's limit).
    """
    max_requests: int = 1500
    window_seconds: int = 60

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_requests <= 0:
            raise ConfigurationError(
                f"max_requests must be positive, got {self.max_requests}"
            )
        if self.window_seconds <= 0:
            raise ConfigurationError(
                f"window_seconds must be positive, got {self.window_seconds}"
            )


@dataclass(frozen=True)
class RetryConfig:
    """Retry behavior configuration.

    Attributes:
        max_retries: Maximum retry attempts (default 3)
        base_delay: Initial delay in seconds (default 0.1)
        max_delay: Maximum delay cap in seconds (default 60)
        exponential_base: Multiplier for exponential backoff (default 2)
        jitter: Add random jitter to delays (default True)
        retryable_status_codes: HTTP status codes that trigger retry
    """
    max_retries: int = 3
    base_delay: float = 0.1
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 503, 504})
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
class ConcurrencyConfig:
    """Concurrency limits for API requests.

    Separate limits for read (GET) and write (POST/PUT/DELETE) operations.
    """
    read_limit: int = 50   # Concurrent GET requests
    write_limit: int = 15  # Concurrent mutation requests

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.read_limit <= 0:
            raise ConfigurationError(
                f"read_limit must be positive, got {self.read_limit}"
            )
        if self.write_limit <= 0:
            raise ConfigurationError(
                f"write_limit must be positive, got {self.write_limit}"
            )


@dataclass(frozen=True)
class TimeoutConfig:
    """HTTP timeout configuration.

    Attributes:
        connect: Timeout for establishing connection
        read: Timeout for reading response
        write: Timeout for sending request body
        pool: Timeout for acquiring connection from pool
    """
    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 10.0

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
    """HTTP connection pool configuration."""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_connections <= 0:
            raise ConfigurationError(
                f"max_connections must be positive, got {self.max_connections}"
            )
        if self.max_keepalive_connections <= 0:
            raise ConfigurationError(
                f"max_keepalive_connections must be positive, got {self.max_keepalive_connections}"
            )
        if self.keepalive_expiry <= 0:
            raise ConfigurationError(
                f"keepalive_expiry must be positive, got {self.keepalive_expiry}"
            )


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Per ADR-0048: Opt-in pattern for cascading failure prevention.

    Attributes:
        enabled: Whether circuit breaker is active (default False for backward compat)
        failure_threshold: Consecutive failures before opening circuit
        recovery_timeout: Seconds to wait before half-open probe
        half_open_max_calls: Successful probes required to close circuit
    """
    enabled: bool = False  # Opt-in for backward compatibility
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds before half-open probe
    half_open_max_calls: int = 1  # Probes before closing

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
class AsanaConfig:
    """Main configuration for AsanaClient.

    Example:
        config = AsanaConfig(
            rate_limit=RateLimitConfig(max_requests=1000),
            retry=RetryConfig(max_retries=5),
        )
        client = AsanaClient(config=config)
    """
    base_url: str = "https://app.asana.com/api/1.0"
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    # Auth key names (used with AuthProvider.get_secret)
    token_key: str = "ASANA_PAT"
