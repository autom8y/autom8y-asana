"""Pydantic Settings for autom8_asana SDK.

Provides unified configuration via environment variables with type validation.
Replaces scattered os.environ.get() calls with a centralized, type-safe
configuration layer.

Environment Variables:
    ASANA_PAT: Personal Access Token for Asana API
    ASANA_WORKSPACE_GID: Default workspace GID
    ASANA_BASE_URL: API base URL (default: https://app.asana.com/api/1.0)
    ASANA_STRICT_CONFIG: Enable strict validation mode
    ASANA_CACHE_ENABLED: Master cache enable/disable
    ASANA_CACHE_PROVIDER: Explicit cache provider selection
    ASANA_CACHE_TTL_DEFAULT: Default cache TTL in seconds
    ASANA_CACHE_MEMORY_MAX_SIZE: Max entries in in-memory cache (default: 10000)
    ASANA_CACHE_S3_BUCKET: S3 bucket name for cache storage
    ASANA_CACHE_S3_PREFIX: S3 key prefix (default: asana-cache)
    ASANA_CACHE_S3_REGION: AWS region (default: us-east-1)
    ASANA_CACHE_S3_ENDPOINT_URL: Custom S3 endpoint (for LocalStack)
    ASANA_CACHE_TTL_USER: User metadata cache TTL (default: 3600)
    ASANA_CACHE_TTL_CUSTOM_FIELD: Custom field cache TTL (default: 1800)
    ASANA_CACHE_TTL_SECTION: Section cache TTL (default: 1800)
    ASANA_CACHE_TTL_PROJECT: Project cache TTL (default: 900)
    ASANA_CACHE_TTL_DETECTION: Detection result cache TTL (default: 300)
    ASANA_CACHE_TTL_DYNAMIC_INDEX: Dynamic index cache TTL (default: 3600)
    ASANA_CACHE_MODIFICATION_CHECK_TTL: Batch modification check TTL (default: 25.0)
    ASANA_CACHE_COALESCE_WINDOW_MS: Freshness coalescing window in ms (default: 50)
    ASANA_CACHE_MAX_BATCH_SIZE: Max entries per batch freshness check (default: 100)
    ASANA_CACHE_DYNAMIC_INDEX_MAX_PER_ENTITY: Max dynamic indexes per entity (default: 5)
    ASANA_CACHE_REDIS_MAX_CONNECTIONS: Redis adapter max connections (default: 20)
    ASANA_CACHE_DF_COALESCER_MAX_WAIT: DataFrame coalescer max wait secs (default: 60.0)
    ASANA_CACHE_DF_CB_FAILURE_THRESHOLD: DataFrame circuit breaker failures (default: 3)
    ASANA_CACHE_DF_CB_RESET_TIMEOUT: DataFrame circuit breaker reset secs (default: 60)
    ASANA_CACHE_DF_CB_SUCCESS_THRESHOLD: DataFrame circuit breaker successes (default: 1)
    AUTOM8_DATA_URL: Base URL for autom8_data service (default: http://localhost:8000)
    AUTOM8_DATA_CACHE_TTL: Cache TTL in seconds for data service insights (default: 300)
    AUTOM8_DATA_INSIGHTS_ENABLED: Emergency kill switch for insights integration (default: true)
    CLOUDWATCH_NAMESPACE: CloudWatch metric namespace (default: autom8/lambda)
    ENVIRONMENT: Deployment environment for metrics dimensions (default: staging)
    DATAFRAME_CACHE_BYPASS: Bypass DataFrame cache for testing (default: false)
    CONTAINER_MEMORY_MB: Explicit container memory limit override in MB (default: None)
    SECTION_FRESHNESS_PROBE: Enable section freshness probing (default: 1)
    API_HOST: Host for ECS uvicorn server (default: 0.0.0.0)
    API_PORT: Port for ECS uvicorn server (default: 8000)
    ASANA_PACING_PAGES_PER_PAUSE: Pages fetched before pausing (default: 25)
    ASANA_PACING_DELAY_SECONDS: Seconds to sleep between page batches (default: 2.0)
    ASANA_PACING_CHECKPOINT_EVERY_N_PAGES: Pages between checkpoint writes (default: 50)
    ASANA_PACING_HIERARCHY_THRESHOLD: Parent GIDs above which batched pacing activates (default: 100)
    ASANA_PACING_HIERARCHY_BATCH_SIZE: Parent GIDs per batch (default: 50)
    ASANA_PACING_HIERARCHY_BATCH_DELAY: Seconds between hierarchy batches (default: 1.0)
    ASANA_S3_RETRY_MAX_ATTEMPTS: S3 retry max attempts (default: 3)
    ASANA_S3_RETRY_BASE_DELAY: S3 retry base delay in seconds (default: 0.5)
    ASANA_S3_RETRY_MAX_DELAY: S3 retry max delay in seconds (default: 10.0)
    ASANA_S3_BUDGET_PER_SUBSYSTEM_MAX: S3 retry budget per subsystem (default: 20)
    ASANA_S3_BUDGET_GLOBAL_MAX: S3 retry budget global max (default: 50)
    ASANA_S3_BUDGET_WINDOW_SECONDS: S3 retry budget window in seconds (default: 60.0)
    ASANA_S3_CB_FAILURE_THRESHOLD: S3 circuit breaker failure threshold (default: 5)
    ASANA_S3_CB_RECOVERY_TIMEOUT: S3 circuit breaker recovery timeout (default: 60.0)
    ASANA_S3_CB_HALF_OPEN_MAX_PROBES: S3 circuit breaker half-open probes (default: 2)
    REDIS_HOST: Redis host for cache
    REDIS_PORT: Redis port (default: 6379)
    REDIS_PASSWORD: Redis password (optional)
    REDIS_SSL: Enable Redis SSL (default: true)
    REDIS_SOCKET_TIMEOUT: Redis socket timeout in seconds (default: 2.0)
    REDIS_CONNECT_TIMEOUT: Redis connection timeout in seconds (default: 5.0)

Example:
    >>> from autom8_asana.settings import get_settings
    >>> settings = get_settings()
    >>> print(settings.asana.pat)  # From ASANA_PAT env var
    >>> print(settings.cache.enabled)  # From ASANA_CACHE_ENABLED

    >>> # Reset for testing
    >>> from autom8_asana.settings import reset_settings
    >>> reset_settings()
"""

from __future__ import annotations

import os
from typing import Any

from autom8y_config import Autom8yBaseSettings, Autom8yEnvironment
from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import SettingsConfigDict


class AsanaSettings(Autom8yBaseSettings):
    """Core Asana API settings.

    Environment Variables:
        ASANA_PAT: Personal Access Token (optional for provider-based auth)
        ASANA_WORKSPACE_GID: Default workspace GID
        ASANA_BASE_URL: API base URL
        ASANA_STRICT_CONFIG: Enable strict validation mode

    Attributes:
        pat: Personal Access Token (optional, may use auth provider instead)
        workspace_gid: Default workspace GID for operations
        base_url: Asana API base URL
        strict_config: If True, raise on invalid ASANA_PROJECT_* vars
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_",
        extra="ignore",
        case_sensitive=False,
    )

    pat: SecretStr | None = Field(
        default=None, description="Asana Personal Access Token"
    )
    workspace_gid: str | None = Field(default=None, description="Default workspace GID")
    base_url: str = Field(
        default="https://app.asana.com/api/1.0",
        description="Asana API base URL",
    )
    strict_config: bool = Field(
        default=False, description="Enable strict configuration validation"
    )


class CacheSettings(Autom8yBaseSettings):
    """Cache configuration settings.

    Environment Variables:
        ASANA_CACHE_ENABLED: Master enable/disable ("true"/"false")
        ASANA_CACHE_PROVIDER: Explicit provider ("memory", "redis", "tiered", "none")
        ASANA_CACHE_TTL_DEFAULT: Default TTL in seconds
        ASANA_CACHE_MEMORY_MAX_SIZE: Maximum entries in in-memory cache

    Attributes:
        enabled: Whether caching is enabled
        provider: Explicit cache provider name (None for auto-detect)
        ttl_default: Default TTL in seconds for cache entries
        memory_max_size: Maximum entries in in-memory cache
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_CACHE_",
        extra="ignore",
        case_sensitive=False,
    )

    enabled: bool = Field(default=True, description="Enable caching")
    provider: str | None = Field(
        default=None, description="Cache provider (memory, redis, tiered, none)"
    )
    ttl_default: int = Field(default=300, description="Default TTL in seconds")
    memory_max_size: int = Field(
        default=10000, description="Maximum entries in in-memory cache"
    )
    dataframe_heap_percent: float = Field(
        default=0.3,
        description="Max fraction of container memory for DataFrame cache (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    dataframe_max_entries: int = Field(
        default=100,
        description="Max DataFrame entries in memory tier",
        ge=1,
    )

    # --- Entity-specific cache TTLs ---
    # Per I12: Extracted from scattered module-level constants
    ttl_user: int = Field(
        default=3600,
        description="Cache TTL for user metadata in seconds (1 hour)",
        ge=0,
    )
    ttl_custom_field: int = Field(
        default=1800,
        description="Cache TTL for custom field metadata in seconds (30 min)",
        ge=0,
    )
    ttl_section: int = Field(
        default=1800,
        description="Cache TTL for section data in seconds (30 min)",
        ge=0,
    )
    ttl_project: int = Field(
        default=900,
        description="Cache TTL for project data in seconds (15 min)",
        ge=0,
    )
    ttl_detection: int = Field(
        default=300,
        description="Cache TTL for entity detection results in seconds (5 min)",
        ge=0,
    )
    ttl_dynamic_index: int = Field(
        default=3600,
        description="Cache TTL for dynamic resolution indexes in seconds (1 hour)",
        ge=0,
    )

    # --- Cache operational constants ---
    modification_check_ttl: float = Field(
        default=25.0,
        description="TTL for in-memory batch modification check cache in seconds",
        ge=0.0,
    )
    coalesce_window_ms: int = Field(
        default=50,
        description="Freshness coordinator coalescing window in milliseconds",
        ge=0,
    )
    max_batch_size: int = Field(
        default=100,
        description="Maximum entries per batch freshness check",
        ge=1,
    )
    dynamic_index_max_per_entity: int = Field(
        default=5,
        description="Maximum dynamic indexes kept per entity type (LRU eviction)",
        ge=1,
    )
    redis_max_connections: int = Field(
        default=20,
        description="Maximum connections in Redis adapter connection pool",
        ge=1,
    )

    # --- DataFrame cache factory constants ---
    df_coalescer_max_wait: float = Field(
        default=60.0,
        description="Maximum seconds waiters will wait for DataFrame coalescer",
        gt=0.0,
    )
    df_cb_failure_threshold: int = Field(
        default=3,
        description="DataFrame cache circuit breaker failure threshold",
        ge=1,
    )
    df_cb_reset_timeout: int = Field(
        default=60,
        description="DataFrame cache circuit breaker reset timeout in seconds",
        ge=1,
    )
    df_cb_success_threshold: int = Field(
        default=1,
        description="DataFrame cache circuit breaker success threshold to close",
        ge=1,
    )

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, v: str | None) -> str | None:
        """Normalize provider name to lowercase."""
        if v is None or v == "":
            return None
        return v.lower()

    @field_validator("ttl_default", mode="before")
    @classmethod
    def parse_ttl_with_fallback(cls, v: str | int | None) -> int:
        """Parse TTL with fallback to default on invalid values.

        Maintains backward compatibility with the old behavior where
        invalid ASANA_CACHE_TTL_DEFAULT values would log a warning
        and fall back to 300.
        """
        from autom8y_log import get_logger

        if v is None:
            return 300
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                get_logger(__name__).warning(
                    "invalid_cache_ttl_default",
                    invalid_value=str(v),
                    default_used=300,
                )
                return 300
        return 300


class RedisSettings(Autom8yBaseSettings):
    """Redis connection settings.

    Environment Variables:
        REDIS_HOST: Redis host (required for Redis cache)
        REDIS_PORT: Redis port (default: 6379)
        REDIS_PASSWORD: Redis password (optional)
        REDIS_SSL: Enable SSL/TLS (default: true)
        REDIS_SOCKET_TIMEOUT: Socket timeout in seconds (default: 2.0)
        REDIS_CONNECT_TIMEOUT: Connection timeout in seconds (default: 5.0)

    Note: These use REDIS_ prefix (not ASANA_) for compatibility
    with standard Redis environment variable conventions.

    Attributes:
        host: Redis server hostname
        port: Redis server port
        password: Redis authentication password
        ssl: Enable SSL/TLS connection
        socket_timeout: Redis socket timeout in seconds
        connect_timeout: Redis connection timeout in seconds
    """

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        extra="ignore",
        case_sensitive=False,
    )

    host: str | None = Field(default=None, description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: SecretStr | None = Field(default=None, description="Redis password")
    ssl: bool = Field(default=True, description="Enable Redis SSL/TLS")
    socket_timeout: float = Field(
        default=2.0, description="Redis socket timeout in seconds"
    )
    connect_timeout: float = Field(
        default=5.0, description="Redis connection timeout in seconds"
    )

    @field_validator("ssl", mode="before")
    @classmethod
    def parse_ssl(cls, v: str | bool | None) -> bool:
        """Parse SSL value from string or bool."""
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)


class S3Settings(Autom8yBaseSettings):
    """S3 cache backend configuration.

    Environment Variables:
        ASANA_CACHE_S3_BUCKET: S3 bucket name for cache storage
        ASANA_CACHE_S3_PREFIX: Key prefix for cached objects (default: asana-cache)
        ASANA_CACHE_S3_REGION: AWS region (default: us-east-1)
        ASANA_CACHE_S3_ENDPOINT_URL: Custom endpoint for LocalStack or S3-compatible storage

    Attributes:
        bucket: S3 bucket name for cache storage
        prefix: Key prefix for cached objects
        region: AWS region for S3 bucket
        endpoint_url: Custom S3 endpoint (for LocalStack or S3-compatible storage)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_CACHE_S3_",
        extra="ignore",
        case_sensitive=False,
    )

    bucket: str = Field(default="", description="S3 bucket name for cache storage")
    prefix: str = Field(
        default="asana-cache", description="Key prefix for cached objects"
    )
    region: str = Field(default="us-east-1", description="AWS region for S3 bucket")
    endpoint_url: str | None = Field(
        default=None, description="Custom S3 endpoint (for LocalStack)"
    )


class PacingSettings(Autom8yBaseSettings):
    """Pacing configuration for large section and hierarchy fetches.

    Per TDD-large-section-resilience / FR-004 and ADR-hierarchy-backpressure-hardening.

    Environment Variables:
        ASANA_PACING_PAGES_PER_PAUSE: Pages before pausing (default: 25)
        ASANA_PACING_DELAY_SECONDS: Sleep between page batches (default: 2.0)
        ASANA_PACING_CHECKPOINT_EVERY_N_PAGES: Pages between checkpoint writes (default: 50)
        ASANA_PACING_HIERARCHY_THRESHOLD: Parent count threshold for batching (default: 100)
        ASANA_PACING_HIERARCHY_BATCH_SIZE: Parents per batch (default: 50)
        ASANA_PACING_HIERARCHY_BATCH_DELAY: Sleep between hierarchy batches (default: 1.0)

    Attributes:
        pages_per_pause: Pages to fetch before pausing.
        delay_seconds: Seconds to sleep between page batches.
        checkpoint_every_n_pages: Pages between checkpoint writes to S3.
        hierarchy_threshold: Parent GIDs above which batched pacing activates.
        hierarchy_batch_size: Parent GIDs to fetch per batch when pacing.
        hierarchy_batch_delay: Seconds to sleep between hierarchy batches.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_PACING_",
        extra="ignore",
        case_sensitive=False,
    )

    pages_per_pause: int = Field(
        default=25,
        description="Pages to fetch before pausing (must be >= 1)",
        ge=1,
    )
    delay_seconds: float = Field(
        default=2.0,
        description="Seconds to sleep between page batches",
        ge=0.0,
    )
    checkpoint_every_n_pages: int = Field(
        default=50,
        description="Pages between checkpoint writes to S3 (must be >= 1)",
        ge=1,
    )
    hierarchy_threshold: int = Field(
        default=100,
        description="Parent GID count above which batched pacing activates",
        ge=1,
    )
    hierarchy_batch_size: int = Field(
        default=50,
        description="Parent GIDs to fetch per batch when pacing is active",
        ge=1,
    )
    hierarchy_batch_delay: float = Field(
        default=1.0,
        description="Seconds to sleep between hierarchy parent fetch batches",
        ge=0.0,
    )


class RateLimitSettings(Autom8yBaseSettings):
    """Rate limiting configuration for Asana API requests.

    Environment Variables:
        ASANA_RATELIMIT_MAX_REQUESTS: Maximum requests per window (default: 1500)
        ASANA_RATELIMIT_WINDOW_SECONDS: Rate limit window in seconds (default: 60)

    Attributes:
        max_requests: Maximum requests per rate limit window.
        window_seconds: Rate limit window duration in seconds.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_RATELIMIT_",
        extra="ignore",
        case_sensitive=False,
    )

    max_requests: int = Field(
        default=1500,
        description="Maximum requests per window (Asana API limit)",
        ge=1,
    )
    window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
        ge=1,
    )


class S3RetrySettings(Autom8yBaseSettings):
    """S3 storage retry, budget, and circuit breaker configuration.

    Per dataframes/storage.py: Controls resilience for S3 DataFrame persistence.

    Environment Variables:
        ASANA_S3_RETRY_MAX_ATTEMPTS: Max retry attempts (default: 3)
        ASANA_S3_RETRY_BASE_DELAY: Base delay for exponential backoff (default: 0.5)
        ASANA_S3_RETRY_MAX_DELAY: Max delay cap in seconds (default: 10.0)
        ASANA_S3_BUDGET_PER_SUBSYSTEM_MAX: Per-subsystem retry budget (default: 20)
        ASANA_S3_BUDGET_GLOBAL_MAX: Global retry budget (default: 50)
        ASANA_S3_BUDGET_WINDOW_SECONDS: Budget window in seconds (default: 60.0)
        ASANA_S3_CB_FAILURE_THRESHOLD: Failures before opening circuit (default: 5)
        ASANA_S3_CB_RECOVERY_TIMEOUT: Recovery timeout in seconds (default: 60.0)
        ASANA_S3_CB_HALF_OPEN_MAX_PROBES: Half-open probes before closing (default: 2)

    Attributes:
        retry_max_attempts: Maximum retry attempts for S3 operations.
        retry_base_delay: Base delay for exponential backoff in seconds.
        retry_max_delay: Maximum delay cap in seconds.
        budget_per_subsystem_max: Per-subsystem retry budget.
        budget_global_max: Global retry budget across all subsystems.
        budget_window_seconds: Budget window in seconds.
        cb_failure_threshold: Consecutive failures before opening circuit.
        cb_recovery_timeout: Seconds to wait before half-open probe.
        cb_half_open_max_probes: Successful probes before closing circuit.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_S3_",
        extra="ignore",
        case_sensitive=False,
    )

    retry_max_attempts: int = Field(
        default=3,
        description="Maximum retry attempts for S3 operations",
        ge=1,
    )
    retry_base_delay: float = Field(
        default=0.5,
        description="Base delay for exponential backoff in seconds",
        ge=0.0,
    )
    retry_max_delay: float = Field(
        default=10.0,
        description="Maximum delay cap in seconds",
        gt=0.0,
    )
    budget_per_subsystem_max: int = Field(
        default=20,
        description="Per-subsystem retry budget",
        ge=1,
    )
    budget_global_max: int = Field(
        default=50,
        description="Global retry budget across all subsystems",
        ge=1,
    )
    budget_window_seconds: float = Field(
        default=60.0,
        description="Budget window in seconds",
        gt=0.0,
    )
    cb_failure_threshold: int = Field(
        default=5,
        description="Consecutive failures before opening circuit",
        ge=1,
    )
    cb_recovery_timeout: float = Field(
        default=60.0,
        description="Seconds to wait before half-open probe",
        gt=0.0,
    )
    cb_half_open_max_probes: int = Field(
        default=2,
        description="Successful probes required to close circuit",
        ge=1,
    )


class DataServiceSettings(Autom8yBaseSettings):
    """autom8_data satellite service configuration.

    Environment Variables:
        AUTOM8_DATA_URL: Base URL for autom8_data API (default: http://localhost:8000)
        AUTOM8_DATA_CACHE_TTL: Client-side cache TTL in seconds (default: 300)
        AUTOM8_DATA_INSIGHTS_ENABLED: Emergency kill switch (default: true)

    Attributes:
        url: Base URL for autom8_data service.
        cache_ttl: Client-side cache TTL in seconds.
        insights_enabled: Whether insights integration is enabled.
            Set to false to disable without code deployment.
    """

    model_config = SettingsConfigDict(
        env_prefix="AUTOM8_DATA_",
        extra="ignore",
        case_sensitive=False,
    )

    # Override autom8y_env with explicit alias so AUTOM8Y_ENV is read directly,
    # bypassing the AUTOM8_DATA_ prefix. Required for the production URL guard
    # to correctly identify the environment.
    autom8y_env: Autom8yEnvironment = Field(
        default=Autom8yEnvironment.LOCAL,
        validation_alias=AliasChoices("AUTOM8Y_ENV", "ASANA_ENVIRONMENT"),
    )

    url: str = Field(
        default="http://localhost:8000",
        description="Base URL for autom8_data API",
    )
    cache_ttl: int = Field(
        default=300,
        description="Client-side cache TTL in seconds for insights",
        ge=0,
    )
    insights_enabled: bool = Field(
        default=True,
        description="Emergency kill switch for insights integration (default on)",
    )


class ObservabilitySettings(Autom8yBaseSettings):
    """Observability and environment settings for Lambda handlers.

    Environment Variables:
        CLOUDWATCH_NAMESPACE: CloudWatch metric namespace (default: autom8/lambda)
        ENVIRONMENT: Deployment environment for metric dimensions (default: staging)

    Attributes:
        cloudwatch_namespace: CloudWatch metric namespace.
        environment: Deployment environment label for metric dimensions.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    cloudwatch_namespace: str = Field(
        default="autom8/lambda",
        description="CloudWatch metric namespace",
    )
    environment: str = Field(
        default="staging",
        description="Deployment environment label for metric dimensions",
    )


class RuntimeSettings(Autom8yBaseSettings):
    """Runtime and operational feature flag settings.

    Environment Variables:
        DATAFRAME_CACHE_BYPASS: Bypass DataFrame cache (default: false)
        CONTAINER_MEMORY_MB: Override container memory limit in MB (default: None)
        SECTION_FRESHNESS_PROBE: Enable section freshness probing (default: 1)
        SECTION_CASCADE_VALIDATION: Enable post-build cascade validation (default: 1)
        API_HOST: ECS uvicorn bind host (default: 0.0.0.0)
        API_PORT: ECS uvicorn bind port (default: 8000)

    Attributes:
        dataframe_cache_bypass: If true, skip DataFrame cache lookup.
        container_memory_mb: Explicit container memory cap in MB (None = auto-detect).
        section_freshness_probe: Enabled when "1" (any non-"0" value).
        section_cascade_validation: Enabled when not "0" (default "1").
        api_host: Host for ECS uvicorn server.
        api_port: Port for ECS uvicorn server.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    dataframe_cache_bypass: bool = Field(
        default=False,
        description="Bypass DataFrame cache for testing",
    )
    container_memory_mb: int | None = Field(
        default=None,
        description="Explicit container memory limit in MB (None = auto-detect from cgroup)",
    )
    section_freshness_probe: str = Field(
        default="1",
        description="Enable section freshness probing (set to '0' to disable)",
    )
    section_cascade_validation: str = Field(
        default="1",
        description="Enable post-build cascade validation (set to '0' to disable)",
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="Bind host for ECS uvicorn server",
    )
    api_port: int = Field(
        default=8000,
        description="Bind port for ECS uvicorn server",
    )


class WebhookSettings(Autom8yBaseSettings):
    """Webhook configuration settings.

    Environment Variables:
        WEBHOOK_INBOUND_TOKEN: Shared secret for inbound webhook auth.

    Attributes:
        inbound_token: Shared secret for URL token verification.
            When empty (default), the webhook endpoint returns 503.
    """

    model_config = SettingsConfigDict(
        env_prefix="WEBHOOK_",
        extra="ignore",
        case_sensitive=False,
    )

    inbound_token: str = Field(
        default="",
        description="Shared secret for inbound webhook URL token verification",
    )


class ProjectOverrideSettings(Autom8yBaseSettings):
    """Validation-only settings for ASANA_PROJECT_* env vars.

    These are validated at startup but not stored as explicit fields
    because they use dynamic key names that cannot be known at class
    definition time.

    This class provides startup validation for all ASANA_PROJECT_*
    environment variables, ensuring GID format is correct (10+ digit
    numeric string).

    Validation respects ASANA_STRICT_CONFIG:
    - strict=True: Raise ValueError on invalid GID
    - strict=False: Log warning only (default)

    Per ADR-SDK-005: Dynamic env var handling cannot use Pydantic Settings
    for storage but can use model_validator for validation at startup.
    """

    model_config = SettingsConfigDict(extra="ignore")

    @model_validator(mode="after")
    def validate_project_overrides(self) -> ProjectOverrideSettings:
        """Validate all ASANA_PROJECT_* env vars at startup.

        Scans environment for ASANA_PROJECT_* variables and validates
        that non-empty values are valid GID format (10+ digit numeric string).

        In strict mode (ASANA_STRICT_CONFIG=true), raises ValueError on invalid.
        In default mode, logs warnings but continues.

        Raises:
            ValueError: If ASANA_STRICT_CONFIG=true and any ASANA_PROJECT_*
                        has invalid GID format.
        """
        import re

        from autom8y_log import get_logger

        logger = get_logger(__name__)
        gid_pattern = re.compile(r"^\d{10,}$")

        # Check strict mode from environment (can't access other settings during validation)
        strict_config = os.environ.get("ASANA_STRICT_CONFIG", "").lower() in (
            "true",
            "1",
            "yes",
        )

        invalid_vars: list[str] = []

        for key, value in os.environ.items():
            if not key.startswith("ASANA_PROJECT_"):
                continue
            if not value.strip():
                continue
            if not gid_pattern.match(value.strip()):
                msg = (
                    f"Invalid GID format for {key}: '{value}' "
                    "(expected numeric string, 10+ digits)"
                )
                invalid_vars.append(msg)
                logger.warning(msg)

        if strict_config and invalid_vars:
            raise ValueError(
                f"Invalid ASANA_PROJECT_* environment variables: {invalid_vars}"
            )

        return self


class Settings(Autom8yBaseSettings):
    """Combined settings container for autom8_asana SDK.

    Aggregates all configuration subsections into a single object.
    Use get_settings() for singleton access.

    Attributes:
        asana: Core Asana API settings
        cache: Cache configuration
        redis: Redis connection settings
        s3: S3 cache backend settings
        pacing: Pacing configuration for large section fetches
        s3_retry: S3 retry and circuit breaker configuration
        webhook: Webhook configuration
        data_service: autom8_data satellite service configuration
        observability: CloudWatch namespace and environment label
        runtime: Runtime feature flags and operational settings
        project_overrides: Validation-only for ASANA_PROJECT_* env vars

    Example:
        >>> settings = get_settings()
        >>> if settings.cache.enabled:
        ...     print(f"Cache TTL: {settings.cache.ttl_default}")
        >>> if settings.redis.host:
        ...     print(f"Redis at {settings.redis.host}:{settings.redis.port}")
        >>> if settings.s3.bucket:
        ...     print(f"S3 bucket: {settings.s3.bucket}")
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
    )

    # SDK-standard environment field. AliasChoices: AUTOM8Y_ENV takes
    # precedence; ASANA_ENVIRONMENT for backward compat.
    autom8y_env: Autom8yEnvironment = Field(
        default=Autom8yEnvironment.LOCAL,
        validation_alias=AliasChoices("AUTOM8Y_ENV", "ASANA_ENVIRONMENT"),
    )

    # Subsettings - initialized lazily to allow environment override
    asana: AsanaSettings = Field(default_factory=AsanaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    pacing: PacingSettings = Field(default_factory=PacingSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    s3_retry: S3RetrySettings = Field(default_factory=S3RetrySettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    data_service: DataServiceSettings = Field(default_factory=DataServiceSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    # Validation-only settings (triggers validation at startup)
    project_overrides: ProjectOverrideSettings = Field(
        default_factory=ProjectOverrideSettings
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production or staging environment."""
        return self.autom8y_env in (
            Autom8yEnvironment.PRODUCTION,
            Autom8yEnvironment.STAGING,
        )

    @property
    def redis_available(self) -> bool:
        """Check if Redis is configured."""
        return self.redis.host is not None and self.redis.host != ""

    def model_post_init(self, __context: Any) -> None:
        """Run SDK production URL guard and check nested URL fields.

        Calls super() for the SDK's _guard_production_urls() which checks
        all top-level fields with "url" in the name.  Then performs additional
        checks on nested URL fields and os.environ-sourced URLs (AUTH_JWKS_URL)
        that the SDK guard cannot reach.

        Uses the explicit-only pattern: only fires when AUTOM8Y_ENV or
        ASANA_ENVIRONMENT is explicitly set in os.environ.

        See TDD-LOCAL-DEV-ENV.md Section 6.3, Section 10 (HAZ-1).
        """
        super().model_post_init(__context)

        # Nested URL guard: check fields the SDK guard cannot reach
        if not self._env_var_explicitly_set():
            return
        if self.autom8y_env not in (
            Autom8yEnvironment.LOCAL,
            Autom8yEnvironment.TEST,
        ):
            return

        _prod_domain = "autom8y.io"
        env = self.autom8y_env.value

        # Check data_service.url (nested field)
        data_url = self.data_service.url
        if data_url and _prod_domain in str(data_url):
            raise ValueError(
                f"FATAL: Production URL detected in {env} environment: "
                f"AUTOM8_DATA_URL={data_url}. "
                f"Override in docker-compose.override.yml or .env."
            )

        # Check AUTH_JWKS_URL from environment (not in Settings model --
        # consumed directly by autom8y-auth SDK and health routes)
        jwks_url = os.environ.get("AUTH_JWKS_URL", "")
        if jwks_url and _prod_domain in jwks_url:
            raise ValueError(
                f"FATAL: Production URL detected in {env} environment: "
                f"AUTH_JWKS_URL={jwks_url}. "
                f"Override in docker-compose.override.yml or .env."
            )


# Module-level singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get singleton Settings instance.

    Creates the settings instance on first call, then returns cached copy.
    Use reset_settings() to clear the cache (e.g., for testing).

    Returns:
        Settings instance populated from environment variables.

    Example:
        >>> settings = get_settings()
        >>> print(settings.asana.base_url)
        https://app.asana.com/api/1.0
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton.

    Clears the cached settings instance, forcing get_settings() to
    re-read from environment variables on next call.

    Use this in tests to ensure clean state between test cases.

    Example:
        >>> import os
        >>> os.environ["ASANA_CACHE_ENABLED"] = "false"
        >>> reset_settings()
        >>> settings = get_settings()
        >>> assert settings.cache.enabled is False
    """
    global _settings
    _settings = None
    Autom8yBaseSettings.reset_resolver()


# Self-register for SystemContext.reset_all()
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(reset_settings)
