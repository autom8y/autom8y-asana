"""API configuration via pydantic-settings.

This module provides environment-based configuration for the API layer.
All settings are loaded from environment variables with the ASANA_API_ prefix.

Environment Variables:
    ASANA_API_CORS_ALLOWED_ORIGINS: Comma-separated list of allowed origins
    ASANA_API_RATE_LIMIT_RPM: Rate limit in requests per minute (default: 100)
    ASANA_API_LOG_LEVEL: Logging level (default: INFO)
    ASANA_API_DEBUG: Enable debug mode (default: false)

S2S Authentication Variables (per TDD-S2S-001):
    AUTH_JWKS_URL: JWKS endpoint (default: https://auth.api.autom8y.io/.well-known/jwks.json)
    AUTH_ISSUER: Expected JWT issuer (default: auth.api.autom8y.io)
    AUTH_DEV_MODE: Bypass JWT validation in development (default: false)
    AUTH_JWKS_CACHE_TTL: JWKS cache TTL in seconds (default: 300)
    ASANA_PAT: Bot PAT for S2S requests (required for S2S mode, from Secrets Manager)

Per TDD-ASANA-SATELLITE (FR-SVC-004, NFR-SCALE-001):
- CORS middleware with configurable origins
- Service-level rate limiting via SlowAPI

Per TDD-S2S-001:
- Dual-mode authentication (JWT + PAT)
- JWT validation via autom8y-auth SDK
- Bot PAT activation from environment
"""

from functools import lru_cache

from autom8y_config import Autom8yBaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class ApiSettings(Autom8yBaseSettings):
    """API configuration settings.

    All settings are loaded from environment variables with ASANA_API_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASANA_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # CORS configuration
    cors_allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins",
    )

    # Rate limiting
    rate_limit_rpm: int = Field(
        default=100,
        ge=1,
        description="Rate limit in requests per minute per client",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Debug mode
    debug: bool = Field(
        default=False,
        description="Enable debug mode (more verbose logging, stack traces)",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string to list.

        Returns:
            List of allowed origins, or empty list if not configured.
        """
        if not self.cors_allowed_origins:
            return []
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> ApiSettings:
    """Get cached API settings singleton.

    Not registered with SystemContext.reset_all() because ApiSettings
    only contains ASANA_API_* prefixed vars (CORS, rate limit, log level, debug)
    which no test suite modifies. Investigated 2026-02-27 (CACHE-REMEDIATION
    spike, F-5) and confirmed not a problem. If future tests modify ASANA_API_*
    env vars, register get_settings.cache_clear with SystemContext.

    Returns:
        ApiSettings instance loaded from environment.
    """
    return ApiSettings()


__all__ = [
    "ApiSettings",
    "get_settings",
]
