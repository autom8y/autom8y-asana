"""Service token auth provider for cross-service JWT exchange.

Wraps autom8y_core.TokenManager to satisfy the AuthProvider protocol,
enabling DataServiceClient to authenticate with data-service using the
standard SERVICE_API_KEY → JWT exchange flow.

Used by:
- API DI factory (dependencies.py) for cross-service enrichment joins
- CLI data client factory (__main__.py) for --enrich / data-service joins
"""

from __future__ import annotations

import os


class ServiceTokenAuthProvider:
    """AuthProvider that exchanges SERVICE_API_KEY for JWT via TokenManager.

    Satisfies ``protocols.auth.AuthProvider`` protocol. TokenManager handles
    caching, refresh, retry, and backoff internally.

    Args:
        service_key: Platform service key. Defaults to SERVICE_API_KEY env var.
        auth_url: Auth service URL for JWT exchange.
    """

    def __init__(
        self,
        service_key: str | None = None,
        auth_url: str = "https://auth.api.autom8y.io",
    ) -> None:
        from autom8y_core import Config, TokenManager

        key = service_key or os.environ.get("SERVICE_API_KEY", "")
        if not key:
            raise ValueError(
                "SERVICE_API_KEY is required for data-service authentication. "
                "Set it in the environment or pass service_key explicitly."
            )

        config = Config(
            service_key=key,
            auth_url=auth_url,
            service_name="autom8y-asana",
        )
        self._manager = TokenManager(config)

    def get_secret(self, key: str) -> str:
        """Return JWT token (key parameter ignored — single-service auth)."""
        return self._manager.get_token()

    def close(self) -> None:
        """Release TokenManager resources."""
        self._manager.close()
