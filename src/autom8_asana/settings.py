"""Pydantic Settings for autom8_asana SDK.

Provides unified configuration via environment variables with type validation.
Replaces scattered os.environ.get() calls with a centralized, type-safe
configuration layer.

Environment Variables:
    ASANA_PAT: Personal Access Token for Asana API
    ASANA_WORKSPACE_GID: Default workspace GID
    ASANA_BASE_URL: API base URL (default: https://app.asana.com/api/1.0)
    ASANA_STRICT_CONFIG: Enable strict validation mode
    ASANA_ENVIRONMENT: Environment hint (development, production, staging)
    ASANA_CACHE_ENABLED: Master cache enable/disable
    ASANA_CACHE_PROVIDER: Explicit cache provider selection
    ASANA_CACHE_TTL_DEFAULT: Default cache TTL in seconds
    ASANA_CACHE_MEMORY_MAX_SIZE: Max entries in in-memory cache (default: 10000)
    ASANA_CACHE_S3_BUCKET: S3 bucket name for cache storage
    ASANA_CACHE_S3_PREFIX: S3 key prefix (default: asana-cache)
    ASANA_CACHE_S3_REGION: AWS region (default: us-east-1)
    ASANA_CACHE_S3_ENDPOINT_URL: Custom S3 endpoint (for LocalStack)
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
from functools import lru_cache
from typing import Literal

import warnings

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AsanaSettings(BaseSettings):
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

    pat: str | None = Field(default=None, description="Asana Personal Access Token")
    workspace_gid: str | None = Field(
        default=None, description="Default workspace GID"
    )
    base_url: str = Field(
        default="https://app.asana.com/api/1.0",
        description="Asana API base URL",
    )
    strict_config: bool = Field(
        default=False, description="Enable strict configuration validation"
    )


class CacheSettings(BaseSettings):
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
        import logging

        if v is None:
            return 300
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                logging.getLogger(__name__).warning(
                    "Invalid ASANA_CACHE_TTL_DEFAULT '%s', using default 300", v
                )
                return 300
        return 300


class RedisSettings(BaseSettings):
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
    password: str | None = Field(default=None, description="Redis password")
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


class EnvironmentSettings(BaseSettings):
    """Environment detection settings.

    Environment Variables:
        ASANA_ENVIRONMENT: Environment name (development, production, staging, test)

    Attributes:
        environment: Current deployment environment
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "production", "staging", "test"] = Field(
        default="development", description="Deployment environment"
    )

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(
        cls, v: str | None
    ) -> Literal["development", "production", "staging", "test"]:
        """Normalize environment name to lowercase and validate."""
        if v is None or v == "":
            return "development"
        normalized = v.lower()
        if normalized not in ("development", "production", "staging", "test"):
            # Fall back to development for unknown values
            return "development"
        return normalized  # type: ignore[return-value]


class S3Settings(BaseSettings):
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


class ProjectOverrideSettings(BaseSettings):
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
    def validate_project_overrides(self) -> "ProjectOverrideSettings":
        """Validate all ASANA_PROJECT_* env vars at startup.

        Scans environment for ASANA_PROJECT_* variables and validates
        that non-empty values are valid GID format (10+ digit numeric string).

        In strict mode (ASANA_STRICT_CONFIG=true), raises ValueError on invalid.
        In default mode, logs warnings but continues.

        Raises:
            ValueError: If ASANA_STRICT_CONFIG=true and any ASANA_PROJECT_*
                        has invalid GID format.
        """
        import logging
        import re

        logger = logging.getLogger(__name__)
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


class Settings(BaseSettings):
    """Combined settings container for autom8_asana SDK.

    Aggregates all configuration subsections into a single object.
    Use get_settings() for singleton access.

    Attributes:
        asana: Core Asana API settings
        cache: Cache configuration
        redis: Redis connection settings
        s3: S3 cache backend settings
        env: Environment detection settings
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

    # Subsettings - initialized lazily to allow environment override
    asana: AsanaSettings = Field(default_factory=AsanaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    env: EnvironmentSettings = Field(default_factory=EnvironmentSettings)
    # Validation-only settings (triggers validation at startup)
    project_overrides: ProjectOverrideSettings = Field(
        default_factory=ProjectOverrideSettings
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.environment in ("production", "staging")

    @property
    def redis_available(self) -> bool:
        """Check if Redis is configured."""
        return self.redis.host is not None and self.redis.host != ""


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
